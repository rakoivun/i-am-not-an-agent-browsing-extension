"""CLI for browser-relay -- send commands to Chrome via the relay server."""

import json
import shutil
import sys
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


@app.command()
def install():
    """Copy extension files to ~/.browser-relay/extension/ and print setup instructions."""
    if not EXTENSION_DIR.exists():
        typer.secho(f"Extension source not found at {EXTENSION_DIR}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    for f in EXTENSION_DIR.iterdir():
        if f.is_file():
            shutil.copy2(f, INSTALL_DIR / f.name)

    typer.echo(f"Extension installed to: {INSTALL_DIR}")
    typer.echo("")
    typer.echo("To load it in Chrome (one-time):")
    typer.echo("  1. Open chrome://extensions")
    typer.echo("  2. Enable 'Developer mode' (toggle top-right)")
    typer.echo("  3. Click 'Load unpacked'")
    typer.echo(f"  4. Select: {INSTALL_DIR}")
    typer.echo("")
    typer.echo("The extension persists across Chrome restarts.")


@app.command()
def server(
    host: str = typer.Option("127.0.0.1", help="Host to bind the relay server"),
    port: int = typer.Option(18321, help="Port for the relay server"),
):
    """Start the relay server."""
    typer.echo(f"Starting relay server on {host}:{port}")
    typer.echo("Press Ctrl+C to stop.")
    from browser_relay.relay.server import run_server
    run_server(host=host, port=port)


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
    selector: str = typer.Argument(help="CSS selector of the element to click"),
):
    """Click an element on the page."""
    result = _send_command("click", {"selector": selector})
    _print_result(result)


@app.command()
def type_text(
    selector: str = typer.Argument(help="CSS selector of the input element"),
    text: str = typer.Argument(help="Text to type"),
    clear: bool = typer.Option(False, "--clear", help="Clear field before typing"),
):
    """Type text into an input element."""
    result = _send_command("type", {"selector": selector, "text": text, "clear": clear})
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
    selector: Optional[str] = typer.Option(None, help="CSS selector to scroll into view"),
    y: int = typer.Option(300, help="Pixels to scroll vertically (if no selector)"),
):
    """Scroll the page or an element into view."""
    params = {}
    if selector:
        params["selector"] = selector
    else:
        params["y"] = y
    result = _send_command("scroll", params)
    _print_result(result)


@app.command()
def get_text(
    selector: str = typer.Argument(help="CSS selector of the element"),
):
    """Get text content of an element."""
    result = _send_command("get_text", {"selector": selector})
    _print_result(result)


@app.command()
def ping():
    """Ping the extension to check if it is alive on the current page."""
    result = _send_command("ping")
    _print_result(result)


if __name__ == "__main__":
    app()
