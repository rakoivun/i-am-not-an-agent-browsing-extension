"""Tests for the relay server endpoints."""

import json
import threading
import time

import pytest

from browser_relay.relay.server import app


@pytest.fixture()
def client():
    import browser_relay.relay.server as srv
    srv._pending_command = None
    srv._pending_result = None
    srv._last_poll_ts = 0.0

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestGetCommand:
    def test_returns_204_when_no_command(self, client):
        resp = client.get("/command")
        assert resp.status_code == 204

    def test_returns_command_after_post(self, client):
        client.post("/command", json={"action": "click", "params": {"selector": "#btn"}})
        resp = client.get("/command")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["action"] == "click"
        assert data["params"]["selector"] == "#btn"
        assert "id" in data

    def test_command_consumed_after_get(self, client):
        client.post("/command", json={"action": "ping"})
        client.get("/command")
        resp = client.get("/command")
        assert resp.status_code == 204


class TestPostCommand:
    def test_requires_action(self, client):
        resp = client.post("/command", json={"params": {}})
        assert resp.status_code == 400

    def test_auto_assigns_id(self, client):
        resp = client.post("/command", json={"action": "ping"})
        data = resp.get_json()
        assert data["queued"] is True
        assert "id" in data

    def test_preserves_custom_id(self, client):
        resp = client.post("/command", json={"action": "ping", "id": "my-id"})
        data = resp.get_json()
        assert data["id"] == "my-id"


class TestResult:
    def test_post_and_get_result(self, client):
        client.post("/result", json={"id": "abc", "ok": True, "value": 42})
        resp = client.get("/result?timeout=1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["value"] == 42

    def test_get_result_timeout(self, client):
        resp = client.get("/result?timeout=0.3")
        assert resp.status_code == 504
        data = resp.get_json()
        assert data["ok"] is False

    def test_result_consumed_after_get(self, client):
        client.post("/result", json={"id": "x", "ok": True})
        client.get("/result?timeout=1")
        resp = client.get("/result?timeout=0.3")
        assert resp.status_code == 504


class TestStatus:
    def test_status_no_extension(self, client):
        resp = client.get("/status")
        data = resp.get_json()
        assert data["server"] == "ok"
        assert data["extension_connected"] is False

    def test_status_after_extension_poll(self, client):
        client.get("/command")
        resp = client.get("/status")
        data = resp.get_json()
        assert data["extension_connected"] is True


class TestFullCycle:
    def test_command_to_result_cycle(self, client):
        post_resp = client.post("/command", json={"action": "snapshot", "params": {"interactive_only": True}})
        cmd_id = post_resp.get_json()["id"]

        get_resp = client.get("/command")
        cmd = get_resp.get_json()
        assert cmd["id"] == cmd_id
        assert cmd["action"] == "snapshot"

        client.post("/result", json={"id": cmd_id, "ok": True, "elements": []})

        result_resp = client.get("/result?timeout=2")
        result = result_resp.get_json()
        assert result["ok"] is True
        assert result["elements"] == []
