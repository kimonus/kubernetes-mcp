"""Exercise the Kubernetes HTTP client against a disposable local TLS endpoint."""
import json
import os
import ssl
import tempfile
import threading
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from src.server import MAX_API_JSON, InvalidInput, Kubernetes, call_tool


class APIHandler(BaseHTTPRequestHandler):
    requests: ClassVar[list[tuple[str, str | None]]] = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.requests.append((self.path, self.headers.get("Authorization")))
        if self.path.startswith("/timeout"):
            threading.Event().wait(6)
            try:
                self.send_response(200)
                self.end_headers()
            except OSError:
                pass
            return
        if self.path.startswith("/redirect"):
            self.send_response(302)
            self.send_header("Location", "/target")
            self.end_headers()
            return
        if self.path.startswith("/oversize"):
            body = b"x" * (MAX_API_JSON + 1)
        elif self.path.startswith("/denied"):
            self.send_error(403)
            return
        elif self.path.startswith("/malformed"):
            body = b"not json"
        else:
            body = json.dumps({"items": [{"metadata": {"name": "pod"}, "status": {"phase": "Running"},
                                          "spec": {"secret": "must not escape", "large": "x" * 70000}}],
                               "metadata": {}}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class KubernetesHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cert = os.path.join(cls.directory.name, "cert.pem")
        key = os.path.join(cls.directory.name, "key.pem")
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        now = datetime.now(timezone.utc)
        certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                       .public_key(private_key.public_key()).serial_number(x509.random_serial_number())
                       .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
                       .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
                       .sign(private_key, hashes.SHA256()))
        with open(key, "wb") as output:
            output.write(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                   serialization.NoEncryption()))
        with open(cert, "wb") as output:
            output.write(certificate.public_bytes(serialization.Encoding.PEM))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), APIHandler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        cls.server.socket = context.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.client = Kubernetes(f"https://localhost:{cls.server.server_port}", lambda: cls.token, cert)
        cls.token = "first"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.directory.cleanup()

    def setUp(self):
        APIHandler.requests.clear()
        type(self).token = "first"

    def test_real_tls_list_and_rotated_token(self):
        result = call_tool(self.client, {"allowed"}, "list_pods", {"namespace": "allowed"})
        self.assertEqual(result["pods"][0]["phase"], "Running")
        self.assertNotIn("must not escape", json.dumps(result))
        self.assertEqual(APIHandler.requests[-1][1], "Bearer first")
        type(self).token = "second"
        self.client.get("/again")
        self.assertEqual(APIHandler.requests[-1][1], "Bearer second")

    def test_redirect_is_not_followed(self):
        with self.assertRaises(urllib.error.HTTPError):
            self.client.get("/redirect")
        self.assertEqual(len(APIHandler.requests), 1)

    def test_untrusted_certificate_is_rejected(self):
        client = Kubernetes(f"https://localhost:{self.server.server_port}", "token", None)
        with self.assertRaises(urllib.error.URLError):
            client.get("/untrusted")
        self.assertEqual(APIHandler.requests, [])

    def test_oversize_malformed_and_denied(self):
        with self.assertRaises(InvalidInput):
            self.client.get("/oversize")
        with self.assertRaises(ValueError):
            self.client.get("/malformed")
        with self.assertRaises(urllib.error.HTTPError):
            self.client.get("/denied")

    def test_kubernetes_api_read_timeout(self):
        with self.assertRaises((TimeoutError, urllib.error.URLError)):
            self.client.get("/timeout")


if __name__ == "__main__":
    unittest.main()
