"""Tests for rich command coverage in extension + CLI."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTENT_JS = (ROOT / "extension" / "content.js").read_text()
BACKGROUND_JS = (ROOT / "extension" / "background.js").read_text()
CLI_APP = (ROOT / "src" / "browser_relay" / "cli" / "app.py").read_text()


def test_content_supports_element_refs():
    assert "const elementRefs = new Map()" in CONTENT_JS
    assert "Element ref not found or stale" in CONTENT_JS
    assert "ref: `e${count}`" in CONTENT_JS


def test_content_has_rich_actions():
    expected_actions = [
        'case "hover"',
        'case "focus"',
        'case "press"',
        'case "dblclick"',
        'case "check"',
        'case "uncheck"',
        'case "get_html"',
        'case "get_attr"',
        'case "get_value"',
        'case "count"',
    ]
    for action in expected_actions:
        assert action in CONTENT_JS


def test_background_has_tabs_and_screenshot_actions():
    expected_actions = [
        'action === "tabs"',
        'action === "new_tab"',
        'action === "switch_tab"',
        'action === "close_tab"',
        'action === "back"',
        'action === "forward"',
        'action === "reload"',
        'action === "screenshot"',
    ]
    for action in expected_actions:
        assert action in BACKGROUND_JS


def test_cli_exposes_rich_commands():
    expected_commands = [
        "def screenshot(",
        '@app.command("tabs")',
        "def list_tabs(",
        "def switch_tab(",
        "def new_tab(",
        "def close_tab(",
        "def press(",
        "def hover(",
        "def focus(",
        "def wait(",
        "def select_option(",
        "def get_html(",
        "def get_attr(",
        "def get_value(",
        "def count(",
    ]
    for command in expected_commands:
        assert command in CLI_APP
