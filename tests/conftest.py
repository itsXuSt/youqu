"""Framework tests conftest - isolated from app test configuration."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_project_root = Path(__file__).resolve().parent.parent
_src_root = _project_root / "src"
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_src_root))


@pytest.fixture
def mock_mouse_key():
    mk = MagicMock()
    mk.screen_size.return_value = (1920, 1080)
    mk.click = MagicMock()
    mk.right_click = MagicMock()
    mk.double_click = MagicMock()
    mk.move_to = MagicMock()
    mk.mouse_scroll = MagicMock()
    mk.input_message = MagicMock()
    mk.press_key = MagicMock()
    mk.hot_key = MagicMock()
    return mk
