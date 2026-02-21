"""Find and launch Chrome for Testing (or Playwright's Chromium) with extension loaded."""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

PROFILE_DIR = Path.home() / ".browser-relay" / "chrome-profile"

_PLAYWRIGHT_CHROMIUM_GLOBS = {
    "win32": [
        Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright" / "chromium-*" / "chrome-win64" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright" / "chromium-*" / "chrome-win" / "chrome.exe",
    ],
    "darwin": [
        Path.home() / "Library" / "Caches" / "ms-playwright" / "chromium-*" / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
    ],
    "linux": [
        Path.home() / ".cache" / "ms-playwright" / "chromium-*" / "chrome-linux" / "chrome",
    ],
}

_SYSTEM_CHROME_PATHS = {
    "win32": [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ],
    "darwin": [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ],
    "linux": [
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/google-chrome-stable"),
        Path("/usr/bin/chromium-browser"),
        Path("/usr/bin/chromium"),
    ],
}


def _glob_resolve(pattern: Path) -> Path | None:
    """Resolve a glob pattern to the first matching path."""
    parts = pattern.parts
    glob_idx = next((i for i, p in enumerate(parts) if "*" in p), None)
    if glob_idx is None:
        return pattern if pattern.exists() else None

    base = Path(*parts[:glob_idx]) if glob_idx > 0 else Path(".")
    remaining_glob = str(Path(*parts[glob_idx:]))

    matches = sorted(base.glob(remaining_glob), reverse=True)
    return matches[0] if matches else None


def find_chrome_for_testing() -> Path | None:
    """Find Playwright's Chromium (Chrome for Testing) binary."""
    plat = sys.platform
    patterns = _PLAYWRIGHT_CHROMIUM_GLOBS.get(plat, [])
    for pattern in patterns:
        resolved = _glob_resolve(pattern)
        if resolved and resolved.exists():
            return resolved
    return None


def find_system_chrome() -> Path | None:
    """Find the system Chrome installation."""
    plat = sys.platform
    paths = _SYSTEM_CHROME_PATHS.get(plat, [])
    for p in paths:
        if p.exists():
            return p
    return None


def _clear_crash_flag():
    """Mark the Chrome profile as cleanly exited to suppress restore prompts."""
    prefs_path = PROFILE_DIR / "Default" / "Preferences"
    if not prefs_path.exists():
        return
    try:
        data = json.loads(prefs_path.read_text(encoding="utf-8"))
        profile = data.get("profile", {})
        profile["exit_type"] = "Normal"
        profile["exited_cleanly"] = True
        data["profile"] = profile
        prefs_path.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def launch_chrome(extension_dir: Path, chrome_path: Path | None = None, url: str = "about:blank") -> subprocess.Popen:
    """Launch Chrome with the extension loaded. Returns the process handle."""
    if chrome_path is None:
        chrome_path = find_chrome_for_testing()
    if chrome_path is None:
        raise FileNotFoundError(
            "Chrome for Testing not found. Install Playwright Chromium with: "
            "uv run playwright install chromium"
        )

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _clear_crash_flag()

    args = [
        str(chrome_path),
        f"--load-extension={extension_dir}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        url,
    ]

    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc
