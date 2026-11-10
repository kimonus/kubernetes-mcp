"""Exercise the Kubernetes HTTP client against a disposable local TLS endpoint."""
import json
import os
import ssl
import subprocess
import tempfile
import threading
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.server import MAX_API_JSON, InvalidInput, Kubernetes, call_tool


class APIHandler(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.requests.append((self.path, self.headers.get("Authorization")))
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
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-keyout", key, "-out", cert, "-subj", "/CN=localhost",
                        "-addext", "subjectAltName=DNS:localhost"], check=True, capture_output=True)
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


if __name__ == "__main__":
    unittest.main()
