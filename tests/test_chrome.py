"""Tests for Chrome discovery and launcher."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from browser_relay.chrome import (
    PROFILE_DIR,
    find_chrome_for_testing,
    find_system_chrome,
)


class TestFindChrome:
    def test_find_chrome_for_testing_returns_path_or_none(self):
        result = find_chrome_for_testing()
        assert result is None or result.exists()

    def test_find_system_chrome_returns_path_or_none(self):
        result = find_system_chrome()
        assert result is None or result.exists()

    def test_profile_dir_is_under_home(self):
        assert str(Path.home()) in str(PROFILE_DIR)
        assert ".browser-relay" in str(PROFILE_DIR)
