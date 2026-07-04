import json

from retriever.context import MCPConfig


def test_mcp_config_loads_claude_desktop_format(tmp_path):
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "test": {
                        "command": "echo",
                        "args": ["hello"],
                        "env": {"FOO": "BAR"},
                    }
                }
            }
        )
    )

    config = MCPConfig.load(str(config_path))

    assert "test" in config
    assert config["test"].command == "echo"
    assert config["test"].args == ["hello"]
    assert config["test"].env == {"FOO": "BAR"}


def test_mcp_config_missing_file_returns_empty_mapping():
    assert MCPConfig.load("/non/existent/path.json") == {}


def test_mcp_config_invalid_json_returns_empty_mapping(tmp_path):
    config_path = tmp_path / "mcp.json"
    config_path.write_text("{ invalid json")

    assert MCPConfig.load(str(config_path)) == {}
