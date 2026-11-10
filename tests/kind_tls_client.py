"""Verify the origin TLS listener in the disposable Kubernetes deployment."""
import json
import ssl
import sys
import time
import urllib.error
import urllib.request

context = ssl.create_default_context(cafile=sys.argv[1])
request = urllib.request.Request(
    "https://localhost:18082/mcp",
    data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + "x" * 32},
)
for attempt in range(30):
    try:
        with urllib.request.urlopen(request, context=context, timeout=3) as response:
            assert json.load(response)["result"] == {}
        break
    except urllib.error.URLError:
        if attempt == 29:
            raise
        time.sleep(1)
