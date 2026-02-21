# Contributing

## Bug policy

Every bug gets a **failing test first**, then the fix. No exceptions.

1. Reproduce the bug
2. Write a test that fails because of the bug
3. Fix the code
4. Verify the test passes
5. Commit test + fix together

If a bug cannot be reproduced with an automated test (e.g., visual-only
Chrome behavior), document it in `tests/manual/` with exact repro steps.

## Test structure

```
tests/
  test_relay.py        # Relay server endpoint tests (unit)
  test_cli.py          # CLI command tests (unit)
  test_stealth.py      # Stealth hardening tests (extension JS validation)
  test_chrome.py       # Chrome launcher tests (unit)
  manual/              # Manual test checklists for things that need a real browser
```

## Running tests

```bash
uv run pytest -v              # all tests
uv run pytest tests/test_relay.py -v   # just relay
uv run pytest -k stealth -v   # just stealth
```

## Test categories

- **Unit tests**: No browser needed. Test relay endpoints, CLI args, Chrome path discovery.
- **Stealth tests**: Validate extension JS files for correctness. Parse and check stealth.js
  patches, rules.json headers, manifest permissions.
- **Integration tests** (future): Require a running Chrome instance. Marked with
  `@pytest.mark.integration`. Not run in CI by default.

## Code style

- Python: snake_case for files, variables, functions.
- JavaScript: camelCase for variables and functions.
- No emojis in source code or docs.
- Comments only for non-obvious intent, not narration.
