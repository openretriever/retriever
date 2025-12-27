
import unittest
import tempfile
import os
import json
from pathlib import Path
from retriever.context import MCPConfig

class TestMCPConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "mcp.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_valid_file(self):
        data = {
            "mcpServers": {
                "test": {"command": "echo", "args": ["hello"], "env": {"FOO": "BAR"}}
            }
        }
        with open(self.config_path, "w") as f:
            json.dump(data, f)
            
        config = MCPConfig.load(str(self.config_path))
        self.assertIn("test", config)
        self.assertEqual(config["test"].command, "echo")
        self.assertEqual(config["test"].args, ["hello"])
        self.assertEqual(config["test"].env, {"FOO": "BAR"})

    def test_load_missing_file(self):
        # Should return empty dict, not crash
        config = MCPConfig.load("/non/existent/path.json")
        self.assertEqual(config, {})

    def test_load_invalid_json(self):
        with open(self.config_path, "w") as f:
            f.write("{ invalid json")
            
        # Should catch error and return empty dict (and print error to stdout)
        config = MCPConfig.load(str(self.config_path))
        self.assertEqual(config, {})

if __name__ == "__main__":
    unittest.main()
