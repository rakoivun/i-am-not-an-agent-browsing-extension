"""Relay server -- bridges CLI commands to the Chrome extension via HTTP polling."""

import threading
import time
import uuid

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

_lock = threading.Lock()
_pending_command: dict | None = None
_pending_result: dict | None = None
_last_poll_ts: float = 0.0

DEFAULT_RESULT_TIMEOUT = 30.0
EXTENSION_ALIVE_THRESHOLD = 3.0


@app.get("/command")
def get_command():
    """Extension polls this to get the next command."""
    global _pending_command, _last_poll_ts

    with _lock:
        _last_poll_ts = time.time()
        if _pending_command is None:
            return Response(status=204)
        cmd = _pending_command
        _pending_command = None
    return jsonify(cmd)


@app.post("/command")
def post_command():
    """CLI pushes a command here."""
    global _pending_command, _pending_result

    body = request.get_json(force=True)
    if not body or "action" not in body:
        return jsonify({"error": "Missing 'action' field"}), 400

    body.setdefault("id", str(uuid.uuid4()))
    body.setdefault("params", {})

    with _lock:
        _pending_command = body
        _pending_result = None

    return jsonify({"id": body["id"], "queued": True})


@app.post("/result")
def post_result():
    """Extension pushes command results here."""
    global _pending_result

    body = request.get_json(force=True)
    with _lock:
        _pending_result = body
    return jsonify({"received": True})


@app.get("/result")
def get_result():
    """CLI polls this to get the result of a command."""
    global _pending_result

    timeout = float(request.args.get("timeout", DEFAULT_RESULT_TIMEOUT))
    deadline = time.time() + timeout

    while time.time() < deadline:
        with _lock:
            if _pending_result is not None:
                result = _pending_result
                _pending_result = None
                return jsonify(result)
        time.sleep(0.1)

    return jsonify({"ok": False, "error": "Timeout waiting for result"}), 504


@app.get("/status")
def status():
    """Health check -- reports if the extension has polled recently."""
    with _lock:
        extension_alive = (time.time() - _last_poll_ts) < EXTENSION_ALIVE_THRESHOLD if _last_poll_ts else False
        has_pending = _pending_command is not None

    return jsonify({
        "server": "ok",
        "extension_connected": extension_alive,
        "pending_command": has_pending,
    })


def run_server(host: str = "127.0.0.1", port: int = 18321):
    """Start the relay server (blocking)."""
    app.run(host=host, port=port, debug=False)
