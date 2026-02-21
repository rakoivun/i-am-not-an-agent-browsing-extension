"""CLI for browser-relay -- send commands to Chrome via the relay server."""

import base64
import json
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import httpx
import typer

app = typer.Typer(name="browser-relay", help="Undetectable browser automation via Chrome extension relay.")

RELAY_URL = "http://127.0.0.1:18321"
EXTENSION_DIR = Path(__file__).resolve().parent.parent.parent.parent / "extension"
INSTALL_DIR = Path.home() / ".browser-relay" / "extension"


def _send_command(action: str, params: dict | None = None, timeout: float = 30.0) -> dict:
    """Post a command to the relay and wait for the result."""
    params = params or {}
    with httpx.Client(base_url=RELAY_URL, timeout=5.0) as client:
        resp = client.post("/command", json={"action": action, "params": params})
        resp.raise_for_status()
        cmd_info = resp.json()
        typer.echo(f"Command queued: {cmd_info['id']}")

        result = client.get("/result", params={"timeout": str(timeout)}, timeout=timeout + 5)
        result.raise_for_status()
        return result.json()


def _print_result(data: dict):
    """Pretty-print a command result."""
    if data.get("ok"):
        filtered = {k: v for k, v in data.items() if k != "ok"}
        if filtered:
            typer.echo(json.dumps(filtered, indent=2, ensure_ascii=False))
        else:
            typer.echo("OK")
    else:
        typer.secho(f"Error: {data.get('error', 'unknown')}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


def _target_params(selector_or_ref: str) -> dict:
    """Map a selector/ref argument into relay params."""
    if selector_or_ref.startswith("e") and selector_or_ref[1:].isdigit():
        return {"ref": selector_or_ref}
    return {"selector": selector_or_ref}


def _wait_for_extension(timeout: float = 15.0) -> bool:
    """Poll /status until the extension is connected or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with httpx.Client(base_url=RELAY_URL, timeout=2.0) as client:
                resp = client.get("/status")
                if resp.status_code == 200 and resp.json().get("extension_connected"):
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


@app.command()
def start(
    host: str = typer.Option("127.0.0.1", help="Relay server host"),
    port: int = typer.Option(18321, help="Relay server port"),
    url: str = typer.Option("about:blank", help="Initial URL to open"),
    system_chrome: bool = typer.Option(False, "--system-chrome", help="Use system Chrome (requires manual extension load)"),
):
    """Start relay server + launch Chrome with extension loaded. One command, zero clicks."""
    from browser_relay.chrome import find_chrome_for_testing, find_system_chrome, launch_chrome

    _install_extension()

    if system_chrome:
        chrome_path = find_system_chrome()
        if not chrome_path:
            typer.secho("System Chrome not found.", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        typer.echo(f"Using system Chrome: {chrome_path}")
        typer.echo("NOTE: --load-extension is removed in Chrome 137+.")
        typer.echo("If the extension doesn't load, use manual install: browser-relay install")
    else:
        chrome_path = find_chrome_for_testing()
        if not chrome_path:
            typer.secho("Chrome for Testing not found.", fg=typer.colors.RED, err=True)
            typer.echo("Install it with: uv run playwright install chromium")
            raise typer.Exit(1)
        typer.echo(f"Using Chrome for Testing: {chrome_path}")

    typer.echo(f"Starting relay server on {host}:{port}")
    server_thread = threading.Thread(
        target=_run_relay, args=(host, port), daemon=True
    )
    server_thread.start()
    time.sleep(0.5)

    typer.echo(f"Launching Chrome with extension...")
    proc = launch_chrome(INSTALL_DIR, chrome_path=chrome_path, url=url)
    typer.echo(f"Chrome PID: {proc.pid}")

    typer.echo("Waiting for extension to connect...")
    if _wait_for_extension():
        typer.secho("Extension connected. Ready.", fg=typer.colors.GREEN)
    else:
        typer.secho("Extension did not connect within 15s. Check chrome://extensions", fg=typer.colors.YELLOW)

    typer.echo("Press Ctrl+C to stop.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        typer.echo("Shutting down...")
        proc.terminate()


def _install_extension():
    """Ensure extension files are in INSTALL_DIR."""
    if not EXTENSION_DIR.exists():
        if INSTALL_DIR.exists() and (INSTALL_DIR / "manifest.json").exists():
            return
        typer.secho(f"Extension source not found at {EXTENSION_DIR}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    for f in EXTENSION_DIR.iterdir():
        if f.is_file():
            shutil.copy2(f, INSTALL_DIR / f.name)


def _run_relay(host: str, port: int):
    """Run Flask relay in a thread."""
    from browser_relay.relay.server import app as flask_app
    flask_app.run(host=host, port=port, debug=False, use_reloader=False)


@app.command()
def install():
    """Copy extension files to ~/.browser-relay/extension/ and print setup instructions."""
    _install_extension()
    typer.echo(f"Extension installed to: {INSTALL_DIR}")
    typer.echo("")
    typer.echo("For automatic setup (recommended):")
    typer.echo("  browser-relay start")
    typer.echo("")
    typer.echo("For manual setup with your own Chrome:")
    typer.echo("  1. Open chrome://extensions")
    typer.echo("  2. Enable 'Developer mode' (toggle top-right)")
    typer.echo("  3. Click 'Load unpacked'")
    typer.echo(f"  4. Select: {INSTALL_DIR}")


@app.command()
def server(
    host: str = typer.Option("127.0.0.1", help="Host to bind the relay server"),
    port: int = typer.Option(18321, help="Port for the relay server"),
):
    """Start only the relay server (without launching Chrome)."""
    typer.echo(f"Starting relay server on {host}:{port}")
    typer.echo("Press Ctrl+C to stop.")
    _run_relay(host=host, port=port)


@app.command()
def status():
    """Check relay server and extension connectivity."""
    try:
        with httpx.Client(base_url=RELAY_URL, timeout=3.0) as client:
            resp = client.get("/status")
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        typer.secho("Relay server is not running.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    server_ok = data.get("server") == "ok"
    ext_ok = data.get("extension_connected", False)

    typer.echo(f"Server:    {'connected' if server_ok else 'down'}")
    typer.echo(f"Extension: {'connected' if ext_ok else 'not connected'}")

    if not ext_ok:
        typer.echo("")
        typer.echo("Extension not polling. Make sure:")
        typer.echo("  - Chrome is open")
        typer.echo("  - The extension is loaded (chrome://extensions)")


@app.command()
def navigate(
    url: str = typer.Argument(help="URL to navigate to"),
    timeout: float = typer.Option(30.0, help="Navigation timeout in seconds"),
):
    """Navigate the active tab to a URL."""
    result = _send_command("navigate", {"url": url, "timeout": int(timeout * 1000)}, timeout=timeout)
    _print_result(result)


@app.command()
def click(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
):
    """Click an element on the page."""
    result = _send_command("click", _target_params(selector_or_ref))
    _print_result(result)


@app.command()
def type_text(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
    text: str = typer.Argument(help="Text to type"),
    clear: bool = typer.Option(False, "--clear", help="Clear field before typing"),
):
    """Type text into an input element."""
    params = _target_params(selector_or_ref)
    params.update({"text": text, "clear": clear})
    result = _send_command("type", params)
    _print_result(result)


@app.command()
def snapshot(
    interactive_only: bool = typer.Option(True, "--all/--interactive", help="Show all elements or interactive only"),
    limit: int = typer.Option(200, help="Max elements to return"),
):
    """Get a DOM snapshot of the current page."""
    result = _send_command("snapshot", {"interactive_only": interactive_only, "limit": limit})
    _print_result(result)


@app.command()
def evaluate(
    expression: str = typer.Argument(help="JavaScript expression to evaluate"),
):
    """Evaluate JavaScript on the page."""
    result = _send_command("evaluate", {"expression": expression})
    _print_result(result)


@app.command()
def scroll(
    selector_or_ref: Optional[str] = typer.Option(None, help="CSS selector or ref to scroll into view"),
    y: int = typer.Option(300, help="Pixels to scroll vertically (if no selector)"),
):
    """Scroll the page or an element into view."""
    params = {}
    if selector_or_ref:
        params.update(_target_params(selector_or_ref))
    else:
        params["y"] = y
    result = _send_command("scroll", params)
    _print_result(result)


@app.command()
def get_text(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
):
    """Get text content of an element."""
    result = _send_command("get_text", _target_params(selector_or_ref))
    _print_result(result)


@app.command()
def get_html(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
):
    """Get HTML content of an element."""
    result = _send_command("get_html", _target_params(selector_or_ref))
    _print_result(result)


@app.command()
def get_attr(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
    name: str = typer.Argument(help="Attribute name"),
):
    """Get attribute value of an element."""
    params = _target_params(selector_or_ref)
    params["name"] = name
    result = _send_command("get_attr", params)
    _print_result(result)


@app.command()
def get_value(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
):
    """Get form value of an element."""
    result = _send_command("get_value", _target_params(selector_or_ref))
    _print_result(result)


@app.command()
def count(
    selector: str = typer.Argument(help="CSS selector to count"),
):
    """Count elements matching selector."""
    result = _send_command("count", {"selector": selector})
    _print_result(result)


@app.command()
def hover(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
):
    """Hover on an element."""
    result = _send_command("hover", _target_params(selector_or_ref))
    _print_result(result)


@app.command()
def focus(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
):
    """Focus an element."""
    result = _send_command("focus", _target_params(selector_or_ref))
    _print_result(result)


@app.command()
def press(
    key: str = typer.Argument(help="Key to press, e.g. Enter, Escape, Tab"),
    selector_or_ref: Optional[str] = typer.Option(None, "--target", help="Optional CSS selector or ref target"),
):
    """Press a keyboard key on the active element or a target element."""
    params = {"key": key}
    if selector_or_ref:
        params.update(_target_params(selector_or_ref))
    result = _send_command("press", params)
    _print_result(result)


@app.command()
def dblclick(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
):
    """Double-click an element."""
    result = _send_command("dblclick", _target_params(selector_or_ref))
    _print_result(result)


@app.command()
def check(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
):
    """Check checkbox/radio element."""
    result = _send_command("check", _target_params(selector_or_ref))
    _print_result(result)


@app.command()
def uncheck(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
):
    """Uncheck checkbox element."""
    result = _send_command("uncheck", _target_params(selector_or_ref))
    _print_result(result)


@app.command()
def select_option(
    selector_or_ref: str = typer.Argument(help="CSS selector or snapshot ref (e.g. e3)"),
    value: str = typer.Argument(help="Option value"),
):
    """Select dropdown option by value."""
    params = _target_params(selector_or_ref)
    params["value"] = value
    result = _send_command("select", params)
    _print_result(result)


@app.command()
def wait(
    selector_or_ref: Optional[str] = typer.Argument(None, help="Optional selector/ref to wait for"),
    ms: Optional[int] = typer.Option(None, "--ms", help="Sleep duration in milliseconds"),
    timeout: float = typer.Option(10.0, "--timeout", help="Element wait timeout in seconds"),
):
    """Wait for milliseconds or until an element appears."""
    if selector_or_ref:
        params = _target_params(selector_or_ref)
        params["timeout_ms"] = int(timeout * 1000)
    else:
        params = {"ms": ms or 1000}
    result = _send_command("wait", params, timeout=max(timeout, 1.0) + 1.0)
    _print_result(result)


@app.command()
def screenshot(
    path: Optional[Path] = typer.Argument(None, help="Optional PNG output path"),
):
    """Capture screenshot of active tab."""
    result = _send_command("screenshot")
    _print_result({"ok": result.get("ok"), "captured": result.get("ok", False)})
    if not result.get("ok"):
        return
    data_url = result.get("data_url")
    if not data_url:
        return
    if path is None:
        return
    if "," not in data_url:
        typer.secho("Invalid screenshot payload.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    _, b64_data = data_url.split(",", 1)
    png_bytes = base64.b64decode(b64_data)
    path.write_bytes(png_bytes)
    typer.echo(f"Saved screenshot to: {path}")


@app.command()
def back():
    """Navigate back in tab history."""
    result = _send_command("back")
    _print_result(result)


@app.command()
def forward():
    """Navigate forward in tab history."""
    result = _send_command("forward")
    _print_result(result)


@app.command()
def reload():
    """Reload the active tab."""
    result = _send_command("reload")
    _print_result(result)


@app.command("tabs")
def list_tabs():
    """List tabs in the current browser window."""
    result = _send_command("tabs")
    _print_result(result)


@app.command()
def switch_tab(
    tab_id: int = typer.Argument(help="Tab id to activate"),
):
    """Switch to another tab by id."""
    result = _send_command("switch_tab", {"tab_id": tab_id})
    _print_result(result)


@app.command()
def new_tab(
    url: str = typer.Argument("about:blank", help="Optional URL for the new tab"),
):
    """Open a new tab."""
    result = _send_command("new_tab", {"url": url})
    _print_result(result)


@app.command()
def close_tab(
    tab_id: Optional[int] = typer.Argument(None, help="Optional tab id. Defaults to active tab."),
):
    """Close tab by id or close active tab."""
    params = {}
    if tab_id is not None:
        params["tab_id"] = tab_id
    result = _send_command("close_tab", params)
    _print_result(result)


@app.command()
def ping():
    """Ping the extension to check if it is alive on the current page."""
    result = _send_command("ping")
    _print_result(result)


if __name__ == "__main__":
    app()
