# browser-relay

Undetectable LLM-orchestrated browser automation via Chrome extension relay.

Zero-click setup. No CDP, no WebDriver, no Playwright at runtime.
Websites cannot detect this.

## How It Works

```
CLI (Typer)  -->  Relay Server (Flask, localhost:18321)  <--  Chrome Extension (polling)
```

1. The relay server queues commands from the CLI.
2. A Chrome extension polls the relay every 500ms for pending commands.
3. The extension executes commands in the page (click, type, snapshot, etc.) via a content script.
4. Results flow back through the relay to the CLI.

No automation protocol is involved at runtime. The extension uses standard
`fetch()` to localhost, indistinguishable from any other Chrome extension.

## Quick Start

```bash
# One command -- starts relay server + launches Chrome with extension loaded
browser-relay start
```

That's it. Chrome opens with the extension already active. No manual steps.

### What `start` does under the hood

1. Copies extension files to `~/.browser-relay/extension/`
2. Starts the Flask relay server on `localhost:18321`
3. Launches **Chrome for Testing** (Playwright's Chromium) with `--load-extension`
4. Waits for the extension to connect (polls `/status`)

Chrome for Testing is an official Google build from the same source code and
CI pipeline as regular Chrome. It has identical TLS fingerprint, user agent,
and behavior. The only difference: it keeps `--load-extension` enabled
(removed from branded Chrome in v137, May 2025).

### Prerequisites

Chrome for Testing must be available on the machine. The easiest way:

```bash
uv run playwright install chromium
```

This downloads Chrome for Testing to `~/.cache/ms-playwright/` (Linux/Mac)
or `%LOCALAPPDATA%\ms-playwright\` (Windows). `browser-relay start`
auto-discovers it.

### Alternative: use your own system Chrome

For maximum stealth (identical TLS at the transport layer), you can load
the extension into your own Chrome manually:

```bash
browser-relay install    # copies extension to ~/.browser-relay/extension/
browser-relay server     # starts relay only (no Chrome launch)
```

Then one-time in Chrome:
1. Open `chrome://extensions`
2. Enable **Developer mode** (toggle, top-right)
3. Click **Load unpacked**
4. Select `~/.browser-relay/extension/`

The extension persists across Chrome restarts. After the one-time load,
just run `browser-relay server` in the future.

## Usage

```bash
# Check connectivity (server + extension)
browser-relay status

# Navigate the active tab
browser-relay navigate "https://example.com"

# Get interactive elements on the page
browser-relay snapshot

# Click an element by CSS selector
browser-relay click "#login-button"

# Type into a field (--clear to empty it first)
browser-relay type-text "#email" "user@example.com" --clear

# Get text content of an element
browser-relay get-text "#result"

# Evaluate JavaScript on the page
browser-relay evaluate "document.title"

# Scroll to an element or by pixels
browser-relay scroll --selector "#section-2"
browser-relay scroll --y 500

# Ping the extension (check it is alive on the current page)
browser-relay ping
```

## Why It Is Undetectable

| Signal | Status |
|--------|--------|
| TLS fingerprint (JA3/JA4) | Identical to Chrome (same binary, same BoringSSL) |
| User agent | Identical to Chrome |
| `navigator.webdriver` | `false` (no automation protocol attached) |
| CDP / DevTools artifacts | None (no CDP connection) |
| WebDriver protocol | Not used |
| Extension visibility | Standard MV3 extension, same as millions of others |

### Background: why not Playwright/Selenium/CDP directly?

- Playwright and Selenium attach automation protocols (CDP/WebDriver) that
  set `navigator.webdriver = true` and leave detectable artifacts.
- Chrome removed `--load-extension` from branded builds in v137 (May 2025)
  to prevent malware abuse.
- Chrome 136+ blocks `--remote-debugging-port` and `--remote-debugging-pipe`
  on the default user profile.
- Chrome for Testing is Google's recommended path for browser automation.
  It is the same Chrome, without auto-update, with automation flags intact.

browser-relay sidesteps all of this: it launches Chrome for Testing as a
normal browser (no automation protocol), loads the extension via
`--load-extension`, and communicates entirely through HTTP polling. The
result is a browser that websites cannot distinguish from a human user.

## File Structure

```
browser-relay/
  extension/
    manifest.json       # MV3 Chrome extension manifest
    background.js       # Service worker: polls relay, dispatches commands
    content.js          # Content script: executes DOM actions on page
  src/browser_relay/
    __init__.py
    chrome.py           # Chrome for Testing discovery and launch
    relay/
      __init__.py
      server.py         # Flask relay server (command/result queue)
    cli/
      __init__.py
      app.py            # Typer CLI (start, install, server, navigate, etc.)
  tests/
    test_relay.py       # Relay server endpoint tests
    test_cli.py         # CLI command tests
  pyproject.toml
  README.md
```

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest -v

# Run a single test
uv run pytest tests/test_relay.py::TestFullCycle -v
```
