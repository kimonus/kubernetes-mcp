"""Fail-closed, stateless MCP diagnostic endpoint.

This initial implementation is intended for local testing, not public deployment.
"""
import hmac
import json
import os
import re
import socket
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from src.diagnostics import TOOL_SCHEMAS, call_diagnostic
from src.metadata import SERVER_INSTRUCTIONS, server_info, tool_metadata

MAX_REQUEST = 32 * 1024
MAX_OUTPUT = 64 * 1024
MAX_API_JSON = 4 * 1024 * 1024
REQUEST_DEADLINE_SECONDS = 30
NAME = re.compile(r"^[a-z0-9](?:[-a-z0-9.]*[a-z0-9])?$")
PROTOCOL = "2025-03-26"
TOOLS = {
    "list_pods": {"namespace": "string"},
    "describe_pod": {"namespace": "string", "pod": "string"},
    "get_pod_events": {"namespace": "string", "pod": "string"},
    "get_pod_logs": {"namespace": "string", "pod": "string", "container": "string"},
    "get_previous_logs": {"namespace": "string", "pod": "string", "container": "string"},
    "list_namespaces": {},
    "list_all_pods": {},
    "list_namespace_events": {"namespace": "string"},
}
TOOLS.update({name: {} for name in TOOL_SCHEMAS})


class InvalidInput(ValueError):
    pass


class OversizeResponse(InvalidInput):
    pass


class LogText(str):
    truncated: bool

    def __new__(cls, value, truncated):
        obj = super().__new__(cls, value)
        obj.truncated = truncated
        return obj


def validate(args, fields, namespaces):
    if not isinstance(args, dict) or set(args) != set(fields):
        raise InvalidInput("Invalid arguments")
    for value in args.values():
        if not isinstance(value, str) or len(value) > 253 or not NAME.fullmatch(value):
            raise InvalidInput("Invalid resource name")
    if "namespace" in args and "*" not in namespaces and args["namespace"] not in namespaces:
        raise InvalidInput("Namespace not allowed")


def pod_summary(pod):
    metadata = pod.get("metadata") or {}
    status = pod.get("status") or {}
    containers = (status.get("initContainerStatuses") or []) + (status.get("containerStatuses") or [])
    def container_summary(container):
        state = container.get("state") or {}
        selected_state = {}
        for phase in ("waiting", "running", "terminated"):
            value = state.get(phase)
            if isinstance(value, dict):
                selected_state[phase] = {k: value[k] for k in ("reason", "exitCode", "startedAt", "finishedAt")
                                         if k in value}
        previous = (container.get("lastState") or {}).get("terminated") or {}
        return {**{k: container.get(k) for k in ("name", "ready", "restartCount")}, "state": selected_state,
                "lastTermination": {k: previous[k] for k in ("reason", "exitCode", "startedAt", "finishedAt") if k in previous}}
    declared = [c.get("name") for kind in ("initContainers", "containers")
                for c in ((pod.get("spec") or {}).get(kind) or []) if isinstance(c.get("name"), str)]
    return {"name": metadata.get("name"), "namespace": metadata.get("namespace"),
            "phase": status.get("phase"), "conditions": [
                {k: c.get(k) for k in ("type", "status", "reason")}
                for c in (status.get("conditions") or [])],
            "containerNames": declared, "containers": [container_summary(c) for c in containers]}


class Kubernetes:
    def __init__(self, host, token, ca):
        self.base = host.rstrip("/")
        self.token = token
        self.context = ssl.create_default_context(cafile=ca)

    def get(self, path, query=None, raw=False):
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        token = self.token() if callable(self.token) else self.token
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect,
                                           urllib.request.HTTPSHandler(context=self.context))
        with opener.open(req, timeout=5) as response:
            limit = MAX_OUTPUT if raw else MAX_API_JSON
            data = response.read(limit + 1)
        if raw:
            return LogText(data[:limit].decode("utf-8", errors="replace"), len(data) > limit)
        if len(data) > limit:
            raise OversizeResponse("Kubernetes response exceeds size limit")
        return json.loads(data)


def call_tool(kube, namespaces, name, args, cluster_scoped=False):
    if name not in TOOLS:
        raise InvalidInput("Unknown tool")
    if name in TOOL_SCHEMAS:
        return call_diagnostic(kube, namespaces, name, args, cluster_scoped=cluster_scoped)
    cursor = None
    if name in ("list_pods", "list_namespaces", "list_all_pods", "list_namespace_events") and isinstance(args, dict) and "continue" in args:
        args = dict(args)
        cursor = args.pop("continue")
        if not isinstance(cursor, str) or not cursor or len(cursor) > 2048:
            raise InvalidInput("Invalid continuation token")
    filters = {}
    if name == "list_namespace_events" and isinstance(args, dict):
        args = dict(args)
        for key in ("reason", "type"):
            if key in args:
                value = args.pop(key)
                if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
                    raise InvalidInput("Invalid event filter")
                if key == "type" and value not in ("Normal", "Warning"):
                    raise InvalidInput("Invalid event type")
                filters[key] = value
    validate(args, TOOLS[name], namespaces)
    if name == "list_namespaces":
        if "*" not in namespaces:
            if cursor:
                raise InvalidInput("Continuation not supported for configured namespaces")
            return {"namespaces": [{"name": n} for n in sorted(namespaces)], "continue": None}
        query: dict[str, str | int] = {"limit": 25}
        if cursor:
            query["continue"] = cursor
        page = kube.get("/api/v1/namespaces", query)
        return {"namespaces": [{"name": (n.get("metadata") or {}).get("name"),
                               "phase": (n.get("status") or {}).get("phase")} for n in page.get("items", [])],
                "continue": (page.get("metadata") or {}).get("continue") or None}
    if name == "list_all_pods":
        if "*" not in namespaces:
            raise InvalidInput("Cross-namespace discovery requires all-namespaces access")
        query = {"limit": 1}
        if cursor:
            query["continue"] = cursor
        page = kube.get("/api/v1/pods", query)
        return {"pods": [pod_summary(p) for p in page.get("items", [])],
                "continue": (page.get("metadata") or {}).get("continue") or None}
    ns = urllib.parse.quote(args["namespace"], safe="")
    root = "/api/v1/namespaces/" + ns
    if name == "list_namespace_events":
        query = {"limit": 20}
        if cursor:
            query["continue"] = cursor
        if filters:
            query["fieldSelector"] = ",".join(k + "=" + v for k, v in sorted(filters.items()))
        page = kube.get(root + "/events", query)
        return {"events": [{k: e.get(k) for k in ("type", "reason", "message", "count", "lastTimestamp", "involvedObject")}
                           for e in page.get("items", [])], "continue": (page.get("metadata") or {}).get("continue") or None}
    if name == "list_pods":
        # Keep the query stable across Kubernetes continuation tokens.
        query = {"limit": 1}
        if cursor:
            query["continue"] = cursor
        result = kube.get(root + "/pods", query)
        def summarize(page):
            next_cursor = page.get("metadata", {}).get("continue") or None
            return {"pods": [pod_summary(p) for p in page.get("items", [])],
                    "truncated": bool(next_cursor), "continue": next_cursor}
        return summarize(result)
    pod = urllib.parse.quote(args["pod"], safe="")
    if name == "describe_pod":
        return pod_summary(kube.get(root + "/pods/" + pod))
    if name == "get_pod_events":
        # Verify UID to avoid returning events for a replaced pod of the same name.
        obj = kube.get(root + "/pods/" + pod)
        uid = obj.get("metadata", {}).get("uid")
        if not uid:
            raise InvalidInput("Pod identity unavailable")
        events = kube.get(root + "/events", {"fieldSelector": "involvedObject.uid=" + uid, "limit": 100})
        return {"events": [{k: e.get(k) for k in ("type", "reason", "message", "count", "lastTimestamp")}
                           for e in events.get("items", [])],
                "truncated": bool(events.get("metadata", {}).get("continue"))}
    query = {"container": args["container"], "tailLines": 200, "sinceSeconds": 3600,
             "timestamps": "true", "limitBytes": MAX_OUTPUT}
    if name == "get_previous_logs":
        query["previous"] = "true"
    try:
        logs = kube.get(root + "/pods/" + pod + "/log", query, raw=True)
    except urllib.error.HTTPError as exc:
        if name == "get_previous_logs" and exc.code == 400:
            exc.close()
            return {"available": False}
        raise
    # Kubernetes may return slightly less than limitBytes, so upstream truncation is unknown.
    return {"available": True, "untrusted_log_text": str(logs),
            "truncated": True if getattr(logs, "truncated", False) else None,
            "upstream_limit_bytes": MAX_OUTPUT}


def schema(fields: dict[str, str]) -> dict[str, Any]:
    return {"type": "object", "properties": {k: {"type": v} for k, v in fields.items()},
            "required": list(fields), "additionalProperties": False}


def dispatch(message, kube, namespaces, cluster_scoped=False):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}}
    method, ident = message["method"], message.get("id")
    if "id" not in message:
        return None
    result: Any = None
    if method == "initialize":
        result = {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                  "serverInfo": server_info(), "instructions": SERVER_INSTRUCTIONS}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        definitions = []
        for n, f in TOOLS.items():
            input_schema = TOOL_SCHEMAS[n] if n in TOOL_SCHEMAS else schema(f)
            if n in ("list_pods", "list_namespaces", "list_all_pods", "list_namespace_events"):
                input_schema["properties"]["continue"] = {"type": "string", "maxLength": 2048}
            if n == "list_namespace_events":
                input_schema["properties"].update({"reason": {"type": "string"}, "type": {"type": "string", "enum": ["Normal", "Warning"]}})
            definitions.append({"name": n, "inputSchema": input_schema, **tool_metadata(n)})
        result = {"tools": definitions}
    elif method == "tools/call":
        try:
            params = message.get("params") or {}
            if not isinstance(params, dict):
                raise InvalidInput("Invalid parameters")
            output = call_tool(kube, namespaces, params.get("name"), params.get("arguments", {}), cluster_scoped)
            if "untrusted_log_text" in output:
                original = output["untrusted_log_text"]
                # Account for both JSON encodings, including escapes and the JSON-RPC envelope.
                def fits(candidate):
                    content = json.dumps(candidate, ensure_ascii=True)
                    response = {"jsonrpc": "2.0", "id": ident, "result": {
                        "content": [{"type": "text", "text": content}]}}
                    return len(json.dumps(response).encode()) <= MAX_OUTPUT
                if not fits(output):
                    output["truncated"] = True
                    low, high = 0, len(original)
                    while low < high:
                        middle = (low + high + 1) // 2
                        output["untrusted_log_text"] = original[:middle]
                        if fits(output):
                            low = middle
                        else:
                            high = middle - 1
                    output["untrusted_log_text"] = original[:low]
            content = json.dumps(output, ensure_ascii=True)
            if len(content.encode()) > MAX_OUTPUT:
                raise InvalidInput("Result exceeds size limit")
            result = {"content": [{"type": "text", "text": content}]}
        except (InvalidInput, urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError, AttributeError, OSError):
            result = {"isError": True, "content": [{"type": "text", "text": "Request failed or was denied"}]}
    else:
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": ident, "result": result}


def make_handler(kube, namespaces, token, origins, access=None, cluster_scoped=False):
    slots = threading.BoundedSemaphore(8)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def setup(self):
            super().setup()
            self.connection.settimeout(10)
            def expire():
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            self.deadline = threading.Timer(REQUEST_DEADLINE_SECONDS, expire)
            self.deadline.daemon = True
            self.deadline.start()

        def finish(self):
            self.deadline.cancel()
            super().finish()

        def authorized(self):
            origin = self.headers.get("Origin")
            if origin and origin not in origins:
                self.send_error(403)
                return False
            authorized = False
            if access is not None:
                from src.cloudflare import AccessDenied
                assertions = self.headers.get_all("Cf-Access-Jwt-Assertion", [])
                if len(assertions) == 1:
                    try:
                        access.authenticate(assertions[0])
                        authorized = True
                    except AccessDenied:
                        pass
            else:
                auth = self.headers.get("Authorization", "")
                authorized = hmac.compare_digest(auth.encode("utf-8"), ("Bearer " + token).encode("utf-8"))
            if not authorized:
                self.send_response(401)
                self.send_header("WWW-Authenticate", "Bearer")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return False
            return True

        def do_POST(self):
            if self.path != "/mcp":
                self.send_error(404)
                return
            if not self.authorized():
                return
            if self.headers.get_content_type() != "application/json":
                self.send_error(415)
                return
            version = self.headers.get("MCP-Protocol-Version")
            if version and version != PROTOCOL:
                self.send_error(400)
                return
            if self.headers.get("Transfer-Encoding"):
                self.send_error(400)
                return
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if length < 0 or length > MAX_REQUEST:
                    self.send_error(413)
                    return
                message = json.loads(self.rfile.read(length))
            except (ValueError, UnicodeDecodeError):
                self.send_error(400)
                return
            if not slots.acquire(blocking=False):
                self.send_error(503)
                return
            try:
                result: Any
                if isinstance(message, list):
                    if not message or len(message) > 16:
                        self.send_error(400)
                        return
                    result = []
                    budget = (MAX_OUTPUT - 2048) // len(message)
                    for item in message:
                        response = dispatch(item, kube, namespaces, cluster_scoped)
                        if response is None:
                            continue
                        if len(json.dumps(response).encode()) > budget:
                            response = {"jsonrpc": "2.0", "id": response.get("id"), "error": {
                                "code": -32000, "message": "Response exceeds batch limit"}}
                        result.append(response)
                    if not result:
                        result = None
                else:
                    result = dispatch(message, kube, namespaces, cluster_scoped)
            finally:
                slots.release()
            if result is None:
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            body = json.dumps(result).encode()
            if len(body) > MAX_OUTPUT:
                self.send_error(413)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path != "/mcp":
                self.send_error(404)
                return
            if not self.authorized():
                return
            self.send_response(405)
            self.send_header("Allow", "POST")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_DELETE(self):
            self.do_GET()
    return Handler


class BoundedHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, tls_context=None):
        self.connections = threading.BoundedSemaphore(16)
        self.tls_context = tls_context
        super().__init__(address, handler)

    def handle_error(self, request, client_address):
        # Do not emit client addresses or request details after disconnected clients.
        pass

    def process_request(self, request, client_address):
        if not self.connections.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.connections.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            connection = request
            if self.tls_context is not None:
                try:
                    connection = self.tls_context.wrap_socket(request, server_side=True, do_handshake_on_connect=False)
                    connection.settimeout(10)
                    def expire_handshake():
                        try:
                            connection.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                    timer = threading.Timer(REQUEST_DEADLINE_SECONDS, expire_handshake)
                    timer.daemon = True
                    timer.start()
                    try:
                        connection.do_handshake()
                    finally:
                        timer.cancel()
                except OSError:
                    self.shutdown_request(connection)
                    return
            super().process_request_thread(connection, client_address)
        finally:
            self.connections.release()


def make_tls_context(cert_file, key_file):
    if bool(cert_file) != bool(key_file):
        raise ValueError("Both TLS certificate and key are required")
    if not cert_file:
        return None
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert_file, key_file)
    return context


def main():
    token = os.environ.get("MCP_BEARER_TOKEN", "")
    namespaces = set(filter(None, os.environ.get("MCP_NAMESPACES", "").split(",")))
    mode = os.environ.get("MCP_AUTH_MODE", "")
    cluster_scope = os.environ.get("MCP_CLUSTER_SCOPED_DIAGNOSTICS", "false")
    if cluster_scope not in ("true", "false"):
        raise SystemExit("Invalid cluster diagnostics configuration")
    access = None
    if mode == "cloudflare":
        from src.cloudflare import AccessAuthenticator
        access = AccessAuthenticator(os.environ.get("MCP_ACCESS_ISSUER", ""),
                                     os.environ.get("MCP_ACCESS_AUDIENCE", ""),
                                     set(filter(None, os.environ.get("MCP_ACCESS_EMAILS", "").split(","))))
    elif mode != "bearer" or len(token) < 32:
        raise SystemExit("Set MCP_AUTH_MODE and a valid authentication configuration")
    if not namespaces or ("*" in namespaces and len(namespaces) != 1) or any(n != "*" and not NAME.fullmatch(n) for n in namespaces):
        raise SystemExit("Set explicit MCP_NAMESPACES")
    tls = make_tls_context(os.environ.get("MCP_TLS_CERT_FILE", ""), os.environ.get("MCP_TLS_KEY_FILE", ""))
    if mode == "cloudflare" and tls is None:
        raise SystemExit("Cloudflare authentication requires origin TLS")
    sa = "/var/run/secrets/kubernetes.io/serviceaccount/"
    def kube_token():
        with open(sa + "token", encoding="utf-8") as f:
            return f.read().strip()
    host = "https://" + os.environ["KUBERNETES_SERVICE_HOST"] + ":" + os.environ["KUBERNETES_SERVICE_PORT_HTTPS"]
    kube = Kubernetes(host, kube_token, sa + "ca.crt")
    origins = set(filter(None, os.environ.get("MCP_ALLOWED_ORIGINS", "").split(",")))
    BoundedHTTPServer(("0.0.0.0", 8080), make_handler(kube, namespaces, token, origins, access,
                                                      cluster_scope == "true"), tls).serve_forever()


if __name__ == "__main__":
    main()
