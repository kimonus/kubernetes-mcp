"""Optional smoke test with the official Python MCP client installed."""
import asyncio
import threading

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.server import BoundedHTTPServer, make_handler


class FakeKubernetes:
    def get(self, path, query=None, raw=False):
        return {"items": [], "metadata": {}}


async def smoke(port):
    async with (
        httpx2.AsyncClient(headers={"Authorization": "Bearer " + "x" * 32}) as http,
        streamable_http_client(f"http://127.0.0.1:{port}/mcp", http_client=http) as streams,
        ClientSession(streams[0], streams[1]) as session,
    ):
        initialization = await session.initialize()
        assert initialization.serverInfo.name == "kubernetes-mcp"
        tools = await session.list_tools()
        assert {"list_pods", "describe_pod", "get_pod_events", "get_pod_logs", "get_previous_logs",
                "list_namespaces", "list_all_pods", "list_workloads", "diagnose_pod"} <= {t.name for t in tools.tools}
        result = await session.call_tool("list_pods", {"namespace": "allowed"})
        assert not result.is_error


def main():
    server = BoundedHTTPServer(("127.0.0.1", 0), make_handler(FakeKubernetes(), {"allowed"}, "x" * 32, set()))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        asyncio.run(smoke(server.server_port))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
