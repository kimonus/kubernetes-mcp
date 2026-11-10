"""Run the separate TypeScript MCP client against a local simulated backend."""
import subprocess
import threading

from src.server import BoundedHTTPServer, make_handler


class FakeKubernetes:
    def get(self, path, query=None, raw=False):
        return {"items": [], "metadata": {}}


server = BoundedHTTPServer(("127.0.0.1", 0), make_handler(FakeKubernetes(), {"allowed"}, "x" * 32, set()))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    subprocess.run(["node", "tests/typescript_client_smoke.mjs", f"http://127.0.0.1:{server.server_port}/mcp"],
                   check=True, timeout=20)
finally:
    server.shutdown()
    server.server_close()
    thread.join()
