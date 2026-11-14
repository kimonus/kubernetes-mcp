import base64
import json
import struct
import unittest
from pathlib import Path

from src.metadata import (
    DESCRIPTION,
    REPOSITORY,
    SERVER_INSTRUCTIONS,
    TITLE,
    VERSION,
    server_info,
    tool_metadata,
)
from src.server import PROTOCOL, TOOLS, dispatch


class MetadataTests(unittest.TestCase):
    def test_identity_and_local_icon(self):
        info = server_info()
        self.assertEqual(info["name"], "kubernetes-mcp")
        self.assertEqual(info["version"], VERSION)
        self.assertEqual(info["title"], TITLE)
        self.assertEqual(info["description"], DESCRIPTION)
        self.assertEqual(info["websiteUrl"], REPOSITORY)
        icon = info["icons"][0]
        self.assertEqual(icon["mimeType"], "image/png")
        self.assertEqual(icon["sizes"], ["128x128"])
        self.assertTrue(icon["src"].startswith("data:image/png;base64,"))
        data = base64.b64decode(icon["src"].split(",", 1)[1], validate=True)
        self.assertEqual(data, (Path(__file__).parent.parent / "src/assets/icon.png").read_bytes())
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", data[16:24]), (128, 128))
        self.assertLess(len(json.dumps(info).encode()), 32768)

    def test_read_only_tool_annotation_and_descriptions(self):
        for name in ("list_pods", "describe_pod", "get_pod_events", "get_pod_logs", "get_previous_logs"):
            metadata = tool_metadata(name)
            self.assertTrue(metadata["description"])
            self.assertTrue(metadata["annotations"]["readOnlyHint"])
            self.assertFalse(metadata["annotations"]["destructiveHint"])
            self.assertTrue(metadata["annotations"]["title"])
        self.assertIn("untrusted", SERVER_INSTRUCTIONS)

    def test_wire_identity_and_tool_definitions(self):
        initialize = dispatch({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, None, {"*"})["result"]
        self.assertEqual(initialize["protocolVersion"], PROTOCOL)
        self.assertEqual(initialize["serverInfo"], server_info())
        self.assertEqual(initialize["instructions"], SERVER_INSTRUCTIONS)
        result = dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, None, {"*"})["result"]
        self.assertEqual({t["name"] for t in result["tools"]}, set(TOOLS))
        for definition in result["tools"]:
            self.assertEqual(definition["inputSchema"]["type"], "object")
            self.assertTrue(definition["description"])
            self.assertTrue(definition["annotations"]["readOnlyHint"])


if __name__ == "__main__":
    unittest.main()
