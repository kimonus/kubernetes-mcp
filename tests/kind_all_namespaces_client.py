"""Check all-namespaces mode against the disposable CI deployment."""
import json
import time
import urllib.error
import urllib.request


def list_pods(namespace):
    request = urllib.request.Request(
        "http://127.0.0.1:18081/mcp",
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": "list_pods", "arguments": {"namespace": namespace}}}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + "x" * 32},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.load(response)["result"]


for attempt in range(30):
    try:
        result = list_pods("mcp-denied")
        break
    except urllib.error.URLError:
        if attempt == 29:
            raise
        time.sleep(1)
assert not result.get("isError")
assert not list_pods("mcp-created-later").get("isError")
