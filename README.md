# browser-relay

Undetectable LLM-orchestrated browser automation via Chrome extension relay.

Uses your own Chrome with a manually-loaded extension -- zero automation fingerprint.
No CDP, no WebDriver, no Playwright at runtime. Websites cannot detect this.

## Quick Start

```bash
# Install
uvx browser-relay install

# Start relay server
uvx browser-relay server
```

Then load the extension in Chrome (one-time):

1. Open `chrome://extensions`
2. Enable **Developer mode** (toggle, top-right)
3. Click **Load unpacked**
4. Select `~/.browser-relay/extension/`

## Usage

```bash
# Check connectivity
browser-relay status

# Navigate
browser-relay navigate "https://example.com"

# Get page snapshot
browser-relay snapshot

# Click an element
browser-relay click "#login-button"

# Type into a field
browser-relay type-text "#email" "user@example.com" --clear

# Evaluate JavaScript
browser-relay evaluate "document.title"

# Scroll
browser-relay scroll --selector "#section-2"
```

## Architecture

```
CLI (Typer)  -->  Relay Server (Flask, localhost:18321)  <--  Chrome Extension (polling)
```

The extension polls the relay every 500ms for commands, executes them in the page context,
and posts results back. The CLI sends commands and waits for results.

## How It Stays Undetectable

- Your own Chrome binary = real TLS fingerprint
- No automation protocol (CDP/WebDriver) attached
- `navigator.webdriver` is `false`
- Extension uses standard `fetch()` to localhost
- Indistinguishable from any other Chrome extension
