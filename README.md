# i-am-not-an-agent-browsing-extension

Stealth-hardened browser automation with zero-click install. Undetectable by websites.

A Chrome extension + local relay server that lets CLIs and LLMs control the browser through standard HTTP -- no CDP, no WebDriver, no Playwright at runtime.

## Install with your AI assistant

Paste this into Claude, Cursor, Copilot, or any AI coding assistant:

> Install and run browser-relay from https://github.com/rakoivun/i-am-not-an-agent-browsing-extension

The assistant will clone the repo, install dependencies, and run `browser-relay start`.
No manual steps. No clicking through Chrome settings. The AI does it all.

## Quick start (zero-click install)

```bash
git clone https://github.com/rakoivun/i-am-not-an-agent-browsing-extension.git
cd i-am-not-an-agent-browsing-extension
uv sync && uv run playwright install chromium
uv run browser-relay start
```

One command launches everything: relay server + Chrome + extension auto-loaded. Done.

```bash
# In another terminal:
uv run browser-relay navigate "https://example.com"
uv run browser-relay snapshot
uv run browser-relay click "#login-button"
uv run browser-relay type-text "#email" "user@example.com" --clear
```

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

No automation protocol touches the browser. The extension uses standard
`fetch()` to localhost -- same as any other Chrome extension.

## Why other tools get detected

| Tool | Problem |
|------|---------|
| Playwright / Puppeteer | Attach CDP, set `navigator.webdriver = true` |
| Selenium | WebDriver protocol, detectable flags |
| Patchright | Patches CDP leaks but CDP is still connected |
| Playwriter | Chrome Web Store install but uses CDP internally |
| Nodriver | Custom CDP, no webdriver flag, but CDP artifacts remain |
| browser-ctl | Same relay pattern but no stealth hardening, manual install |

## What makes this different

**Zero-click install.** No chrome://extensions, no Developer mode toggles, no
manual steps. `browser-relay start` launches Chrome for Testing (official
Google build, identical to Chrome) with `--load-extension` -- done.

**Stealth-hardened.** Active countermeasures against bot detection:

| Detection vector | How we handle it |
|-----------------|-----------------|
| `navigator.webdriver` | `false` -- no automation protocol attached |
| `Sec-CH-UA` header | Overridden to include "Google Chrome" via `declarativeNetRequest` |
| `navigator.userAgentData.brands` | Patched in MAIN world at `document_start` before page JS runs |
| `fn.toString()` introspection | All patched functions return `[native code]` |
| `Object.getOwnPropertyDescriptor` | Trapped to return native-looking descriptors |
| `Function.prototype.toString` | Itself spoofed to prevent recursive detection |
| User agent string | Standard `Chrome/145.0.0.0` |
| TLS fingerprint | Identical (same BoringSSL binary as Chrome) |
| Chrome flags | Only `--load-extension` + `--user-data-dir` (not detectable) |
| CDP / DevTools | Not connected. Zero CDP. |

**AI-native.** Give this README URL to any AI assistant and it can install,
start, and use the tool without human intervention.

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

## HTTP API

The relay server exposes a simple REST API on `localhost:18321`. Any
language or tool can send commands -- not just the Python CLI.

```bash
# Send a command
curl -X POST http://localhost:18321/command \
  -H "Content-Type: application/json" \
  -d '{"action": "navigate", "params": {"url": "https://example.com"}}'

# Poll for the result
curl http://localhost:18321/result?timeout=10

# Check status
curl http://localhost:18321/status
```

Actions: `navigate`, `click`, `type`, `snapshot`, `scroll`, `get_text`,
`evaluate`, `wait`, `select`, `ping`, `fingerprint`, `tab_info`.

## Architecture

- **`extension/`** -- Manifest V3 Chrome extension. Background service worker
  polls the relay for commands. Content script executes DOM actions. Stealth
  script patches fingerprints in the page's MAIN world.
- **`src/browser_relay/relay/`** -- Flask server with in-memory command/result
  queue.
- **`src/browser_relay/cli/`** -- Typer CLI. `start` handles everything:
  extension install, relay server, Chrome launch, connectivity check.
- **`src/browser_relay/chrome.py`** -- Chrome for Testing discovery and launch
  with clean flags and crash-state patching.

## Alternative: use your own Chrome

For absolute stealth (your own TLS stack), load the extension manually:

```bash
uv run browser-relay install   # copies extension to ~/.browser-relay/extension/
uv run browser-relay server    # starts relay only
```

Then in Chrome: `chrome://extensions` > Developer mode > Load unpacked >
select `~/.browser-relay/extension/`. One-time step, persists across restarts.

## Tests

```bash
uv run pytest -v    # 44 tests
```

Bug policy: every bug gets a failing test first, then the fix. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
