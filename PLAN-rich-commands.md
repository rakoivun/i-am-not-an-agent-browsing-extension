# Plan: Rich Command Set for browser-relay

**Goal:** Match and exceed browser-ctl's command richness while keeping our
zero-click install and stealth hardening advantages.

## Gap analysis: what browser-ctl has that we lack

### Tier 1 -- Essential for LLM agents (do first)
| Feature | browser-ctl | browser-relay (current) |
|---------|:-----------:|:-----------------------:|
| Element refs (e0, e1, e2...) in snapshot | Yes | No (CSS selectors only) |
| Click/type by element ref | Yes | No |
| Screenshot | Yes (`bctl screenshot`) | No |
| Press key (Enter, Escape, Tab...) | Yes (`bctl press`) | No |
| Tabs: list, switch, new, close | Yes | Partial (tab_info only) |
| Back / forward / reload | Yes | No |
| Wait for element (not just ms) | Yes (`bctl wait .selector`) | Partial (ms only) |
| Hover | Yes | No |
| Select option (dropdowns) | Partial (`doSelect`) | Partial (no CLI command) |

### Tier 2 -- Important for real workflows
| Feature | browser-ctl | browser-relay (current) |
|---------|:-----------:|:-----------------------:|
| Batch / pipe (multi-command) | Yes (`bctl pipe`, `bctl batch`) | No |
| File upload | Yes (`bctl upload`) | No |
| Download file/image | Yes (`bctl download`) | No |
| Dialog handling (alert/confirm) | Yes (`bctl dialog`) | No |
| Double-click | Yes | No |
| Focus | Yes | No |
| Check/uncheck | Yes | No |
| DOM queries (html, attr, count) | Yes | No |
| Get form value | Yes (`bctl get-value`) | No |

### Tier 3 -- Nice to have
| Feature | browser-ctl | browser-relay (current) |
|---------|:-----------:|:-----------------------:|
| Drag and drop | Yes | No |
| Char-by-char input (rich editors) | Yes (`bctl input-text`) | No |
| Self-test | Yes | No |
| Capabilities endpoint | Yes | No |
| AI skill install (`setup cursor`) | Yes | No |

## Implementation plan

### Phase 1: Element refs + snapshot-first workflow
**Files:** `content.js`, `cli/app.py`

1. Assign element refs (e0, e1, ...) in `doSnapshot()`. Store mapping in a
   module-level `Map<string, Element>`.
2. Update `resolveElement(selector)` to check for `eN` pattern first, look up
   in the ref map, fall back to CSS selector.
3. Snapshot output changes: add `ref` field (e.g. `"ref": "e5"`) to each element.
4. CLI `snapshot` prints compact table: `e0  button  "Sign in"  #login-btn`.

**Why first:** This is THE killer feature for LLM agents. Eliminates CSS
selector guessing. Every subsequent command benefits.

### Phase 2: Screenshot
**Files:** `background.js`, `cli/app.py`

1. `background.js`: handle `screenshot` action using `chrome.tabs.captureVisibleTab()`.
   Returns base64 PNG.
2. CLI: `browser-relay screenshot [path]` -- saves to file or prints base64.
3. Needs `<all_urls>` host permission (already have it).

### Phase 3: Keyboard, hover, focus, navigation
**Files:** `content.js`, `background.js`, `cli/app.py`

1. **`press`** action in content.js: dispatch KeyboardEvent with key name.
   CLI: `browser-relay press Enter`, `browser-relay press Tab`.
2. **`hover`** action: `el.dispatchEvent(new MouseEvent("mouseover", ...))`.
   CLI: `browser-relay hover <selector>`.
3. **`focus`** action: `el.focus()`.
   CLI: `browser-relay focus <selector>`.
4. **`back`/`forward`/`reload`** in background.js (chrome.tabs API).
   CLI: `browser-relay back`, `browser-relay forward`, `browser-relay reload`.

### Phase 4: Tabs management
**Files:** `background.js`, `cli/app.py`

1. **`tabs`** action: `chrome.tabs.query({})` -> list all.
   CLI: `browser-relay tabs`.
2. **`switch-tab`** action: `chrome.tabs.update(tabId, {active: true})`.
   CLI: `browser-relay switch-tab <id>`.
3. **`new-tab`** action: `chrome.tabs.create({url})`.
   CLI: `browser-relay new-tab [url]`.
4. **`close-tab`** action: `chrome.tabs.remove(tabId)`.
   CLI: `browser-relay close-tab [id]`.

### Phase 5: Wait for element, dialog, select-option, check/uncheck
**Files:** `content.js`, `background.js`, `cli/app.py`

1. **`wait`** enhancement: if `params.selector` provided, poll until element
   exists (with timeout). Keep ms-only mode for backward compat.
   CLI: `browser-relay wait <selector> [--timeout 10]` or `browser-relay wait --ms 2000`.
2. **`dialog`** in background.js: use `chrome.scripting.executeScript` to
   set up `window.addEventListener("beforeunload", ...)` and
   `window.confirm/alert/prompt` overrides.
   CLI: `browser-relay dialog accept|dismiss [--text val]`.
3. **`select-option`** CLI command: wire up existing `doSelect`.
   CLI: `browser-relay select-option <selector> <value>`.
4. **`check`/`uncheck`**: set `el.checked = true/false` + dispatch events.
   CLI: `browser-relay check <selector>`, `browser-relay uncheck <selector>`.

### Phase 6: DOM queries
**Files:** `content.js`, `cli/app.py`

1. **`get-html`**: `el.innerHTML`.
2. **`get-attr`**: `el.getAttribute(name)`.
3. **`count`**: `document.querySelectorAll(sel).length`.
4. **`get-value`**: `el.value` for form elements.
5. **`dblclick`**: `el.dispatchEvent(new MouseEvent("dblclick", ...))`.
6. **`page-status`**: URL + title (already in ping, but separate command).

### Phase 7: Batch / pipe
**Files:** `cli/app.py`, `relay/server.py`

1. **`pipe`** command: read commands from stdin (one per line), send
   sequentially, output JSONL. Batches consecutive DOM-only ops.
2. **`batch`** command: multiple commands as arguments.
3. Relay server: optional `/batch` endpoint for atomic multi-command.

### Phase 8: File upload/download
**Files:** `content.js`, `background.js`, `cli/app.py`

1. **`upload`**: use `DataTransfer` API to set file on `<input type="file">`.
2. **`download`**: `chrome.downloads.download()` in background.js.
   Needs `downloads` permission in manifest.

## What NOT to copy from browser-ctl

- **CDP fallback for eval:** They use `chrome.debugger` as CSP bypass. This
  attaches CDP and becomes detectable. We stay CDP-free.
- **WebSocket bridge:** They use aiohttp+WebSocket. Our HTTP polling is simpler
  and equally fast for the relay pattern. No benefit to switching.
- **SPA `window.open` interception:** Nice but adds complexity. Defer.

## Test plan

Each phase gets tests:
- Phase 1: test ref assignment, ref resolution, ref invalidation on navigation
- Phase 2: test screenshot returns base64, test file save
- Phase 3: test press dispatches correct KeyboardEvent, test hover/focus
- Phase 4: test tabs list, switch, create, close
- Phase 5: test wait-for-element polling, test dialog handling
- Phase 6: test get-html, get-attr, count, get-value
- Phase 7: test pipe mode, test batch mode
- Phase 8: test upload, test download

## Priority

Phase 1 (element refs) is the single highest-impact change. It transforms the
tool from "needs CSS selector knowledge" to "just use e3." This is what makes
LLM agents effective -- they see the snapshot, pick a ref, done.

Start with Phase 1, then Phase 2 (screenshot), then Phase 3 (keyboard/nav).
These three phases cover 80% of real-world LLM agent needs.
