"""Tests for stealth hardening -- validates extension files are correct.

These tests check the extension's stealth measures without needing a browser.
They parse the JS and JSON files to verify the patches are properly configured.
"""

import json
import re
from pathlib import Path

import pytest

EXTENSION_DIR = Path(__file__).resolve().parent.parent / "extension"


class TestManifestPermissions:
    def test_manifest_has_declarative_net_request(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        assert "declarativeNetRequest" in manifest["permissions"]

    def test_manifest_has_alarms_for_keepalive(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        assert "alarms" in manifest["permissions"]

    def test_stealth_runs_at_document_start_in_main_world(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        stealth_scripts = [
            cs for cs in manifest["content_scripts"]
            if "stealth.js" in cs.get("js", [])
        ]
        assert len(stealth_scripts) == 1
        cs = stealth_scripts[0]
        assert cs["run_at"] == "document_start"
        assert cs["world"] == "MAIN"

    def test_content_script_runs_at_document_idle(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        content_scripts = [
            cs for cs in manifest["content_scripts"]
            if "content.js" in cs.get("js", [])
        ]
        assert len(content_scripts) == 1
        assert content_scripts[0]["run_at"] == "document_idle"

    def test_manifest_has_net_request_rules(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        rules = manifest.get("declarative_net_request", {}).get("rule_resources", [])
        assert len(rules) >= 1
        assert rules[0]["path"] == "rules.json"
        assert rules[0]["enabled"] is True


class TestHeaderRules:
    def test_rules_file_is_valid_json(self):
        rules = json.loads((EXTENSION_DIR / "rules.json").read_text())
        assert isinstance(rules, list)
        assert len(rules) >= 1

    def test_sec_ch_ua_header_includes_google_chrome(self):
        rules = json.loads((EXTENSION_DIR / "rules.json").read_text())
        header_rule = rules[0]
        headers = header_rule["action"]["requestHeaders"]
        sec_ch_ua = next(h for h in headers if h["header"] == "Sec-CH-UA")
        assert "Google Chrome" in sec_ch_ua["value"]
        assert "Chromium" in sec_ch_ua["value"]

    def test_sec_ch_ua_does_not_contain_headless(self):
        rules = json.loads((EXTENSION_DIR / "rules.json").read_text())
        header_rule = rules[0]
        headers = header_rule["action"]["requestHeaders"]
        sec_ch_ua = next(h for h in headers if h["header"] == "Sec-CH-UA")
        assert "HeadlessChrome" not in sec_ch_ua["value"]
        assert "headless" not in sec_ch_ua["value"].lower()

    def test_rule_applies_to_main_frame(self):
        rules = json.loads((EXTENSION_DIR / "rules.json").read_text())
        resource_types = rules[0]["condition"]["resourceTypes"]
        assert "main_frame" in resource_types
        assert "xmlhttprequest" in resource_types


class TestStealthJs:
    @pytest.fixture()
    def stealth_src(self):
        return (EXTENSION_DIR / "stealth.js").read_text()

    def test_patches_navigator_user_agent_data(self, stealth_src):
        assert "navigator.userAgentData" in stealth_src or "userAgentData" in stealth_src

    def test_includes_google_chrome_brand(self, stealth_src):
        assert "Google Chrome" in stealth_src

    def test_includes_chromium_brand(self, stealth_src):
        assert "Chromium" in stealth_src

    def test_does_not_include_headless(self, stealth_src):
        assert "HeadlessChrome" not in stealth_src
        assert "headless" not in stealth_src.lower()

    def test_runs_as_iife(self, stealth_src):
        lines = [l for l in stealth_src.strip().splitlines() if not l.startswith("//")]
        code = "\n".join(lines).strip()
        assert code.startswith("(function")
        assert code.endswith("})();")

    def test_patches_get_high_entropy_values(self, stealth_src):
        assert "getHighEntropyValues" in stealth_src

    def test_sets_prototype_to_navigator_ua_data(self, stealth_src):
        assert "NavigatorUAData.prototype" in stealth_src

    def test_spoofs_tostring_to_native_code(self, stealth_src):
        assert "native code" in stealth_src
        assert "toString" in stealth_src

    def test_spoofs_getter_descriptor(self, stealth_src):
        assert "getOwnPropertyDescriptor" in stealth_src


class TestChromeLauncher:
    def test_no_detectable_flags_in_launch_args(self):
        from browser_relay.chrome import launch_chrome
        import inspect
        source = inspect.getsource(launch_chrome)
        detectable_flags = [
            "--disable-infobars",
            "--disable-session-crashed-bubble",
            "--hide-crash-restore-bubble",
            "--enable-automation",
            "--disable-blink-features=AutomationControlled",
            "--remote-debugging-port",
            "--remote-debugging-pipe",
        ]
        for flag in detectable_flags:
            assert flag not in source, f"Detectable flag found in launch_chrome: {flag}"

    def test_required_flags_present(self):
        from browser_relay.chrome import launch_chrome
        import inspect
        source = inspect.getsource(launch_chrome)
        assert "--load-extension" in source
        assert "--user-data-dir" in source

    def test_crash_flag_is_cleared(self):
        from browser_relay.chrome import _clear_crash_flag, PROFILE_DIR
        prefs_dir = PROFILE_DIR / "Default"
        prefs_dir.mkdir(parents=True, exist_ok=True)
        prefs_path = prefs_dir / "Preferences"
        prefs_path.write_text(json.dumps({
            "profile": {"exit_type": "Crashed", "exited_cleanly": False}
        }))
        _clear_crash_flag()
        data = json.loads(prefs_path.read_text())
        assert data["profile"]["exit_type"] == "Normal"
        assert data["profile"]["exited_cleanly"] is True


class TestBackgroundJs:
    @pytest.fixture()
    def bg_src(self):
        return (EXTENSION_DIR / "background.js").read_text()

    def test_has_keepalive_alarm(self, bg_src):
        assert "chrome.alarms.create" in bg_src

    def test_has_port_keepalive(self, bg_src):
        assert "onConnect" in bg_src
        assert "keepalive" in bg_src

    def test_polls_relay_command_endpoint(self, bg_src):
        assert "/command" in bg_src

    def test_posts_to_relay_result_endpoint(self, bg_src):
        assert "/result" in bg_src
