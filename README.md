# i-am-not-an-agent-browsing-extension

Browser automation that websites cannot detect.

A Chrome extension + local relay server that lets CLIs and LLMs control the browser through standard HTTP -- no CDP, no WebDriver, no Playwright at runtime. Passes Facebook, LinkedIn, and Instagram bot detection.

## How it works

```
Your CLI / LLM        Relay Server (localhost:18321)        Chrome Extension
     |                        |                                   |
     +-- POST /command -----> +                                   |
                              +--- GET /command (polling) ------> +
                              |                                   |
                              |   (extension executes action      |
                              |    in the page via content script) |
                              |                                   |
                              + <-- POST /result ---------------- +
     + <-- GET /result ------ +
```

No automation protocol touches the browser. The extension uses `fetch()` to localhost, same as any other extension.

## Quick start

```bash
git clone https://github.com/rakoivun/i-am-not-an-agent-browsing-extension.git
cd i-am-not-an-agent-browsing-extension

# Install (requires uv + Playwright Chromium)
uv sync
uv run playwright install chromium

# Launch -- starts relay server + Chrome with extension auto-loaded
uv run browser-relay start

# In another terminal:
uv run browser-relay navigate "https://example.com"
uv run browser-relay snapshot
uv run browser-relay click "#some-button"
uv run browser-relay type-text "#email" "hello@example.com" --clear
```

One command, zero clicks. Chrome for Testing opens with the extension already active.

## Commands

| Command | What it does |
|---------|-------------|
| `browser-relay start` | Start relay + launch Chrome with extension |
| `browser-relay navigate <url>` | Navigate active tab |
| `browser-relay snapshot` | Get interactive DOM elements (JSON) |
| `browser-relay click <selector>` | Click element by CSS selector |
| `browser-relay type-text <selector> <text>` | Type into input field |
| `browser-relay get-text <selector>` | Read text content of element |
| `browser-relay evaluate <js>` | Run JavaScript on page |
| `browser-relay scroll` | Scroll page or element into view |
| `browser-relay ping` | Check extension is alive |
| `browser-relay status` | Check relay + extension connectivity |
| `browser-relay install` | Copy extension files (for manual Chrome setup) |
| `browser-relay server` | Start relay only (no Chrome launch) |

## Why it is undetectable

| Detection vector | Status |
|-----------------|--------|
| `navigator.webdriver` | `false` -- no automation protocol attached |
| `Sec-CH-UA` header | Includes "Google Chrome" (overridden via `declarativeNetRequest`) |
| `navigator.userAgentData.brands` | Includes "Google Chrome" (patched at `document_start` in MAIN world) |
| User agent string | Standard `Chrome/145.0.0.0` |
| TLS fingerprint | Identical to Chrome (same BoringSSL, same binary) |
| Chrome flags | Only `--load-extension` and `--user-data-dir` (not detectable) |
| CDP / DevTools | Not connected |

### What is stealth hardening?

The extension includes a `stealth.js` script that runs in the page's JavaScript world **before any page scripts execute**. It patches `navigator.userAgentData.brands` to include "Google Chrome" (Chrome for Testing only reports "Chromium" by default). A `declarativeNetRequest` rule does the same for the `Sec-CH-UA` HTTP header. Together, these make the browser indistinguishable from stock Google Chrome at both the JavaScript and network layers.

## Architecture

- **`extension/`** -- Manifest V3 Chrome extension. Background service worker polls the relay for commands. Content script executes DOM actions (click, type, snapshot). Stealth script patches fingerprints.
- **`src/browser_relay/relay/`** -- Flask server with in-memory command/result queue. Five endpoints: `POST/GET /command`, `POST/GET /result`, `GET /status`.
- **`src/browser_relay/cli/`** -- Typer CLI. `start` command handles everything: extension install, relay server, Chrome launch, connectivity check.
- **`src/browser_relay/chrome.py`** -- Finds Chrome for Testing (Playwright's Chromium) or system Chrome. Launches with clean flags and patched profile.

## Alternative: use your own Chrome

For absolute stealth (your own TLS stack), load the extension manually:

```bash
uv run browser-relay install   # copies extension to ~/.browser-relay/extension/
uv run browser-relay server    # starts relay only
```

Then in Chrome: `chrome://extensions` > Developer mode > Load unpacked > select `~/.browser-relay/extension/`. One-time step, persists across restarts.

## License

MIT
