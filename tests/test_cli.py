"""Tests for the CLI app (Typer commands)."""

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
