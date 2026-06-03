import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestVLMConfigValidation:
    def test_validate_config_path_empty_allowed(self):
        from src.mcp.server import _validate_config_path

        assert _validate_config_path("") == ""

    def test_validate_config_path_within_project(self):
        from src.mcp.server import _validate_config_path, _PROJECT_ROOT

        test_path = str(_PROJECT_ROOT / "apps" / "test" / "ui.ini")
        result = _validate_config_path(test_path)
        assert result == test_path

    def test_validate_config_path_outside_project_rejected(self):
        from src.mcp.server import _validate_config_path

        with pytest.raises(ValueError, match="must be within project directory"):
            _validate_config_path("/etc/passwd")

    def test_validate_config_path_sibling_directory_rejected(self):
        from src.mcp.server import _validate_config_path, _PROJECT_ROOT

        sibling = _PROJECT_ROOT.parent / "{}-evil/config.ini".format(_PROJECT_ROOT.name)
        with pytest.raises(ValueError, match="must be within project directory"):
            _validate_config_path(str(sibling))


class TestAllowedQueryCommands:
    def test_allowed_commands_exact_match(self):
        from src.mcp.server import _ALLOWED_QUERY_COMMANDS

        assert "ps" in _ALLOWED_QUERY_COMMANDS
        assert "gsettings" in _ALLOWED_QUERY_COMMANDS
        assert "dpkg-query" in _ALLOWED_QUERY_COMMANDS

    def test_sibling_command_rejected(self):
        from src.mcp.server import _ALLOWED_QUERY_COMMANDS

        assert "psql" not in _ALLOWED_QUERY_COMMANDS
        assert "ps-evil" not in _ALLOWED_QUERY_COMMANDS


class TestProtectedProcesses:
    def test_critical_processes_protected(self):
        from src.mcp.server import _PROTECTED_PROCESSES

        critical = ["systemd", "Xorg", "Xwayland", "dde-session", "lightdm"]
        for p in critical:
            assert p in _PROTECTED_PROCESSES

    def test_variant_processes_match_prefix(self):
        from src.mcp.server import _PROTECTED_PROCESSES

        import re

        for protected in _PROTECTED_PROCESSES:
            base = protected
            assert re.match(r"^[\w\-.]+$", base)
            assert base in _PROTECTED_PROCESSES

class TestDangerousKeyCombos:
    def test_common_dangerous_combos(self):
        from src.mcp.server import _DANGEROUS_KEY_COMBOS

        must_have = ["alt+f4", "ctrl+alt+del", "ctrl+alt+backspace", "super+l"]
        for combo in must_have:
            assert combo in _DANGEROUS_KEY_COMBOS, f"Missing: {combo}"

    def test_check_dangerous_keys_single(self):
        from src.mcp.server import _check_dangerous_keys

        assert _check_dangerous_keys(["alt", "f4"]) is True
        assert _check_dangerous_keys(["ctrl", "alt", "del"]) is True

    def test_check_dangerous_keys_safe(self):
        from src.mcp.server import _check_dangerous_keys

        assert _check_dangerous_keys(["ctrl", "c"]) is False
        assert _check_dangerous_keys(["Return"]) is False
        assert _check_dangerous_keys(["ctrl", "a"]) is False

    def test_check_dangerous_keys_case_insensitive(self):
        from src.mcp.server import _check_dangerous_keys

        assert _check_dangerous_keys(["Alt", "F4"]) is True
        assert _check_dangerous_keys(["CTRL", "ALT", "DEL"]) is True


class TestScreenshotSaveNoUserPath:
    def test_screenshot_has_no_path_param(self):
        import inspect
        from src.mcp.server import screenshot_save

        sig = inspect.signature(screenshot_save)
        assert "path" not in sig.parameters
