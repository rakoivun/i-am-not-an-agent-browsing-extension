"""Tests for the CLI app (Typer commands)."""

import base64
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from browser_relay.cli.app import INSTALL_DIR, app

runner = CliRunner()


class TestInstall:
    def test_install_copies_files(self, tmp_path):
        target = tmp_path / "ext"
        with patch("browser_relay.cli.app.INSTALL_DIR", target):
            result = runner.invoke(app, ["install"])
        assert result.exit_code == 0
        assert "Extension installed" in result.output
        assert (target / "manifest.json").exists()
        assert (target / "background.js").exists()
        assert (target / "content.js").exists()

    def test_install_prints_instructions(self, tmp_path):
        target = tmp_path / "ext"
        with patch("browser_relay.cli.app.INSTALL_DIR", target):
            result = runner.invoke(app, ["install"])
        assert "chrome://extensions" in result.output
        assert "Developer mode" in result.output
        assert "Load unpacked" in result.output


class TestStatus:
    def test_status_server_down(self, monkeypatch):
        monkeypatch.setattr("browser_relay.cli.app.RELAY_URL", "http://127.0.0.1:19999")
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "not running" in result.output


class TestPing:
    def test_ping_server_down(self, monkeypatch):
        monkeypatch.setattr("browser_relay.cli.app.RELAY_URL", "http://127.0.0.1:19999")
        result = runner.invoke(app, ["ping"])
        assert result.exit_code != 0


class TestRichCommands:
    def test_click_uses_ref_for_snapshot_ids(self):
        with patch("browser_relay.cli.app._send_command", return_value={"ok": True}) as mocked_send:
            result = runner.invoke(app, ["click", "e3"])
        assert result.exit_code == 0
        mocked_send.assert_called_once_with("click", {"ref": "e3"})

    def test_click_uses_selector_for_css(self):
        with patch("browser_relay.cli.app._send_command", return_value={"ok": True}) as mocked_send:
            result = runner.invoke(app, ["click", "#submit"])
        assert result.exit_code == 0
        mocked_send.assert_called_once_with("click", {"selector": "#submit"})

    def test_wait_selector_uses_timeout_ms(self):
        with patch("browser_relay.cli.app._send_command", return_value={"ok": True}) as mocked_send:
            result = runner.invoke(app, ["wait", "e2", "--timeout", "3"])
        assert result.exit_code == 0
        mocked_send.assert_called_once_with("wait", {"ref": "e2", "timeout_ms": 3000}, timeout=4.0)

    def test_screenshot_saves_png(self, tmp_path):
        out_file = tmp_path / "shot.png"
        payload = base64.b64encode(b"png-bytes").decode("ascii")
        with patch(
            "browser_relay.cli.app._send_command",
            return_value={"ok": True, "data_url": f"data:image/png;base64,{payload}"},
        ):
            result = runner.invoke(app, ["screenshot", str(out_file)])
        assert result.exit_code == 0
        assert out_file.read_bytes() == b"png-bytes"
