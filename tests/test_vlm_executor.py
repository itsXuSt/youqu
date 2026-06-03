import sys
from unittest.mock import MagicMock, patch

import pytest


class TestVLMActionResult:
    def test_success_result(self):
        from src.vlm.vlm_executor import VLMActionResult

        r = VLMActionResult(success=True, x=100, y=200, confidence=0.9)
        assert r.success is True
        assert r.x == 100
        assert r.y == 200
        assert r.confidence == 0.9
        assert r.message == ""
        assert r.screenshot_path == ""

    def test_failure_result(self):
        from src.vlm.vlm_executor import VLMActionResult

        r = VLMActionResult(success=False, message="not found")
        assert r.success is False
        assert r.x is None
        assert r.y is None
        assert r.confidence == 0.0


def _make_executor(tmp_path, mock_locator, threshold=0.5):
    from src.vlm.vlm_executor import VLMExecutor

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    mock_config = MagicMock()
    mock_config.backend.max_image_dim = 2048
    mock_config.fallback.confidence_threshold = threshold
    mock_config.get_safe_evidence_dir.return_value = evidence_dir
    executor = VLMExecutor(mock_locator, mock_config)
    executor._screen_size = (1920, 1080)
    return executor


def _patch_capture():
    _ex = sys.modules["src.vlm.vlm_executor"]
    _ss = sys.modules["src.vlm.screenshot"]
    p = patch.object(_ex, "capture_for_vlm")
    m = p.start()
    m.return_value = (b"fake_png", _ss.CropMeta())
    return p


def _patch_mouse_key():
    mk_cls = MagicMock()
    mk_instance = mk_cls()
    sys.modules["src.mouse_key"].MouseKey = mk_cls
    return mk_cls, mk_instance


class TestClickByDescription:
    def test_locate_success(self, tmp_path):
        from src.vlm.vlm_locator import ClickTarget

        mock_locator = MagicMock()
        mock_locator.locate_element.return_value = ClickTarget(x=100, y=200, confidence=0.9)
        executor = _make_executor(tmp_path, mock_locator)

        cap_patch = _patch_capture()
        _, mock_mk = _patch_mouse_key()
        try:
            result = executor.click_by_description("close button")
        finally:
            cap_patch.stop()

        assert result.success is True
        assert result.x == 100
        assert result.y == 200
        mock_mk.click.assert_called_once_with(100, 200)

    def test_locate_failure(self, tmp_path):
        mock_locator = MagicMock()
        mock_locator.locate_element.return_value = None
        executor = _make_executor(tmp_path, mock_locator)

        cap_patch = _patch_capture()
        try:
            result = executor.click_by_description("missing button")
        finally:
            cap_patch.stop()

        assert result.success is False
        assert "failed to locate" in result.message.lower()

    def test_low_confidence(self, tmp_path):
        from src.vlm.vlm_locator import ClickTarget

        mock_locator = MagicMock()
        mock_locator.locate_element.return_value = ClickTarget(x=100, y=200, confidence=0.4)
        executor = _make_executor(tmp_path, mock_locator, threshold=0.8)

        cap_patch = _patch_capture()
        try:
            result = executor.click_by_description("blurry button")
        finally:
            cap_patch.stop()

        assert result.success is False
        assert "low confidence" in result.message.lower()
        assert result.confidence == 0.4

    def test_out_of_bounds(self, tmp_path):
        from src.vlm.vlm_locator import ClickTarget

        mock_locator = MagicMock()
        mock_locator.locate_element.return_value = ClickTarget(x=5000, y=6000, confidence=0.9)
        executor = _make_executor(tmp_path, mock_locator)

        cap_patch = _patch_capture()
        try:
            result = executor.click_by_description("offscreen button")
        finally:
            cap_patch.stop()

        assert result.success is False
        assert "out of bounds" in result.message.lower()

    def test_negative_coordinates(self, tmp_path):
        from src.vlm.vlm_locator import ClickTarget

        mock_locator = MagicMock()
        mock_locator.locate_element.return_value = ClickTarget(x=-50, y=-100, confidence=0.9)
        executor = _make_executor(tmp_path, mock_locator)

        cap_patch = _patch_capture()
        try:
            result = executor.click_by_description("negative button")
        finally:
            cap_patch.stop()

        assert result.success is False

    def test_save_evidence_false(self, tmp_path):
        mock_locator = MagicMock()
        mock_locator.locate_element.return_value = None
        executor = _make_executor(tmp_path, mock_locator)

        cap_patch = _patch_capture()
        try:
            result = executor.click_by_description("button", save_evidence=False)
        finally:
            cap_patch.stop()

        assert result.screenshot_path == ""


class TestLocateContextMenu:
    def test_returns_locator_result(self, tmp_path):
        from src.vlm.vlm_locator import ClickTarget

        expected = ClickTarget(x=300, y=400, confidence=0.85, label="copy")
        mock_locator = MagicMock()
        mock_locator.locate_element.return_value = expected

        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        mock_config = MagicMock()
        mock_config.backend.max_image_dim = 2048
        mock_config.get_safe_evidence_dir.return_value = evidence_dir
        from src.vlm.vlm_executor import VLMExecutor
        executor = VLMExecutor(mock_locator, mock_config)

        cap_patch = _patch_capture()
        try:
            result = executor.locate_for_context_menu("copy")
        finally:
            cap_patch.stop()

        assert result == expected
        assert mock_locator.locate_element.called

    def test_returns_none_on_failure(self, tmp_path):
        mock_locator = MagicMock()
        mock_locator.locate_element.return_value = None

        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        mock_config = MagicMock()
        mock_config.backend.max_image_dim = 2048
        mock_config.get_safe_evidence_dir.return_value = evidence_dir
        from src.vlm.vlm_executor import VLMExecutor
        executor = VLMExecutor(mock_locator, mock_config)

        cap_patch = _patch_capture()
        try:
            result = executor.locate_for_context_menu("nonexistent")
        finally:
            cap_patch.stop()

        assert result is None


class TestGetScreenSize:
    def test_uses_cache(self, tmp_path):
        from src.vlm.vlm_executor import VLMExecutor

        mock_locator = MagicMock()
        mock_config = MagicMock()
        mock_config.get_safe_evidence_dir.return_value = tmp_path
        executor = VLMExecutor(mock_locator, mock_config)
        executor._screen_size = (800, 600)
        assert executor._get_screen_size() == (800, 600)

    def test_fallback_on_error(self, tmp_path):
        from src.vlm.vlm_executor import VLMExecutor

        mock_locator = MagicMock()
        mock_config = MagicMock()
        mock_config.get_safe_evidence_dir.return_value = tmp_path
        executor = VLMExecutor(mock_locator, mock_config)
        executor._screen_size = None

        mk_cls = MagicMock()
        mk_cls.screen_size.side_effect = Exception("no display")
        sys.modules["src.mouse_key"].MouseKey = mk_cls

        result = executor._get_screen_size()
        assert result == (3840, 2160)
