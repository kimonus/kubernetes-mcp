"""Check all-namespaces mode against the disposable CI deployment."""
import json
import time
import urllib.error
import urllib.request


def call(name, arguments):
    request = urllib.request.Request(
        "http://127.0.0.1:18081/mcp",
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": name, "arguments": arguments}}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + "x" * 32},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.load(response)["result"]


for attempt in range(30):
    try:
        result = call("list_pods", {"namespace": "mcp-denied"})
        break
    except urllib.error.URLError:
        if attempt == 29:
            raise
        time.sleep(1)
assert not result.get("isError")
assert not call("list_pods", {"namespace": "mcp-created-later"}).get("isError")
namespaces = call("list_namespaces", {})
assert not namespaces.get("isError")
assert "mcp-created-later" in {n["name"] for n in json.loads(namespaces["content"][0]["text"])["namespaces"]}
assert not call("list_all_pods", {}).get("isError")
assert not call("list_workloads", {"namespace": "mcp-fixture", "kind": "deployment"}).get("isError")
assert not call("list_services", {"namespace": "mcp-fixture"}).get("isError")
assert not call("list_namespace_events", {"namespace": "mcp-fixture", "type": "Warning"}).get("isError")
metrics = call("list_pod_metrics", {"namespace": "mcp-fixture"})
assert not metrics.get("isError")
assert json.loads(metrics["content"][0]["text"])["available"] is False
