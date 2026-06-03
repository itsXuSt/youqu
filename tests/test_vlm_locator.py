import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestExtractJSON:
    def test_plain_json(self):
        from src.vlm.vlm_locator import _extract_json

        assert _extract_json('{"x": 100, "y": 200}') == {"x": 100, "y": 200}

    def test_json_with_whitespace(self):
        from src.vlm.vlm_locator import _extract_json

        assert _extract_json('  {"x": 100}  ') == {"x": 100}

    def test_empty_string(self):
        from src.vlm.vlm_locator import _extract_json

        assert _extract_json("") is None

    def test_none_input(self):
        from src.vlm.vlm_locator import _extract_json

        assert _extract_json(None) is None

    def test_code_block_json(self):
        from src.vlm.vlm_locator import _extract_json

        input_str = '```json\n{"x": 100, "y": 200}\n```'
        assert _extract_json(input_str) == {"x": 100, "y": 200}

    def test_code_block_without_lang(self):
        from src.vlm.vlm_locator import _extract_json

        input_str = '```\n{"x": 100}\n```'
        assert _extract_json(input_str) == {"x": 100}

    def test_code_block_with_think_tag(self):
        from src.vlm.vlm_locator import _extract_json

        input_str = '<thinkthinking>analyzing...</thinkthinking>\n{"x": 100}'
        assert _extract_json(input_str) is None

    def test_json_list_returns_first(self):
        from src.vlm.vlm_locator import _extract_json

        assert _extract_json('[{"x": 1}, {"y": 2}]') == {"x": 1}

    def test_empty_list(self):
        from src.vlm.vlm_locator import _extract_json

        assert _extract_json('[]') == []

    def test_nested_code_block(self):
        from src.vlm.vlm_locator import _extract_json

        input_str = 'Here is the result:\n```json\n{"confidence": 0.95, "label": "button"}\n```\nDone.'
        result = _extract_json(input_str)
        assert result is None  # prefix text causes json.loads to fail

    def test_multiple_code_blocks(self):
        from src.vlm.vlm_locator import _extract_json

        input_str = '```python\nx = 1\n```\n```json\n{"x": 42}\n```'
        result = _extract_json(input_str)
        assert result is None  # simple alternation parser only handles single block

    def test_json_with_newlines(self):
        from src.vlm.vlm_locator import _extract_json

        input_str = '{\n  "x": 100,\n  "y": 200\n}'
        assert _extract_json(input_str) == {"x": 100, "y": 200}


class TestClickTarget:
    def test_creation_with_required(self):
        from src.vlm.vlm_locator import ClickTarget

        t = ClickTarget(x=100, y=200)
        assert t.x == 100
        assert t.y == 200
        assert t.confidence == 1.0
        assert t.label == ""

    def test_creation_with_all_fields(self):
        from src.vlm.vlm_locator import ClickTarget

        t = ClickTarget(x=50, y=75, confidence=0.85, label="close button")
        assert t.confidence == 0.85
        assert t.label == "close button"


class TestVLMAssertResult:
    def test_creation_pass(self):
        from src.vlm.vlm_locator import VLMAssertResult

        r = VLMAssertResult(verdict="PASS", confidence=0.9, reason="button visible")
        assert r.verdict == "PASS"

    def test_creation_with_defaults(self):
        from src.vlm.vlm_locator import VLMAssertResult

        r = VLMAssertResult(verdict="FAIL", confidence=0.5)
        assert r.reason == ""


class TestEncodeImage:
    def test_file_not_found(self, monkeypatch, tmp_path):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)
        with pytest.raises(FileNotFoundError, match="Image not found"):
            locator._encode_image(str(tmp_path / "nonexistent.png"))

    def test_file_too_large(self, monkeypatch, tmp_path):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        large_file = tmp_path / "large.png"
        large_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (21 * 1024 * 1024))
        with pytest.raises(ValueError, match="too large"):
            locator._encode_image(str(large_file))

    def test_valid_image(self, monkeypatch, tmp_path):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        result = locator._encode_image(str(img_file))
        assert isinstance(result, str)
        assert len(result) > 0


class TestLocateElementCropMeta:
    def test_no_crop_meta_passthrough(self):
        from src.vlm.vlm_locator import ClickTarget, OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={
                "choices": [{"message": {"content": '{"x": 100, "y": 200, "confidence": 0.9}'}}]
            }):
                result = locator.locate_element("fake.png", "button")
        assert result.x == 100
        assert result.y == 200

    def test_crop_meta_coordinate_restore(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        crop_meta = {
            "offset_x": 100,
            "offset_y": 50,
            "cropped_width": 800,
            "cropped_height": 600,
            "vlm_width": 800,
            "vlm_height": 600,
        }

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={
                "choices": [{"message": {"content": '{"x": 400, "y": 300, "confidence": 0.9}'}}]
            }):
                result = locator.locate_element("fake.png", "button", crop_meta=crop_meta)
        assert result.x == 500
        assert result.y == 350

    def test_crop_meta_with_resize(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        crop_meta = {
            "offset_x": 0,
            "offset_y": 0,
            "cropped_width": 2560,
            "cropped_height": 1440,
            "vlm_width": 1280,
            "vlm_height": 720,
        }

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={
                "choices": [{"message": {"content": '{"x": 640, "y": 360, "confidence": 0.8}'}}]
            }):
                result = locator.locate_element("fake.png", "center", crop_meta=crop_meta)
        assert result.x == 1280
        assert result.y == 720

    def test_locate_element_api_error(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={"error": "API down"}):
                result = locator.locate_element("fake.png", "button")
        assert result is None

    def test_locate_element_vlm_returns_error(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={
                "choices": [{"message": {"content": '{"error": "cannot identify element"}'}}]
            }):
                result = locator.locate_element("fake.png", "invisible element")
        assert result is None

    def test_locate_element_missing_confidence(self):
        from src.vlm.vlm_locator import ClickTarget, OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={
                "choices": [{"message": {"content": '{"x": 50, "y": 60}'}}]
            }):
                result = locator.locate_element("fake.png", "button")
        assert result.confidence == 0.8


class TestEvaluateAssertion:
    def test_pass_verdict(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={
                "choices": [{"message": {"content": '{"verdict": "pass", "confidence": 0.95, "reason": "button is visible"}'}}]
            }):
                result = locator.evaluate_assertion("fake.png", "button visible", "button should exist")
        assert result.verdict == "PASS"
        assert result.confidence == 0.95

    def test_fail_verdict(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={
                "choices": [{"message": {"content": '{"verdict": "fail", "confidence": 0.8, "reason": "not found"}'}}]
            }):
                result = locator.evaluate_assertion("fake.png", "button visible", "button should exist")
        assert result.verdict == "FAIL"
        assert result.confidence == 0.8

    def test_mixed_case_verdict_normalized(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={
                "choices": [{"message": {"content": '{"verdict": "Pass", "confidence": 0.9, "reason": "ok"}'}}]
            }):
                result = locator.evaluate_assertion("fake.png", "test", "expected")
        assert result.verdict == "PASS"

    def test_missing_verdict_defaults_fail(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={
                "choices": [{"message": {"content": '{"confidence": 0.5, "reason": "unclear"}'}}]
            }):
                result = locator.evaluate_assertion("fake.png", "test", "expected")
        assert result.verdict == "FAIL"

    def test_api_error_returns_none(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={"error": "timeout"}):
                result = locator.evaluate_assertion("fake.png", "test", "expected")
        assert result is None

    def test_invalid_json_returns_none(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator, "_encode_image", return_value="abc"):
            with patch.object(locator, "_call_api", return_value={
                "choices": [{"message": {"content": "not json at all"}}]
            }):
                result = locator.evaluate_assertion("fake.png", "test", "expected")
        assert result is None


class TestCallAPI:
    def test_successful_call(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        mock_config.backend.model = "test-model"
        locator = OpenAICompatLocator(mock_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_response.raise_for_status = MagicMock()

        with patch.object(locator._client, "post", return_value=mock_response):
            result = locator._call_api([{"role": "user", "content": "test"}])
        assert result == {"choices": [{"message": {"content": "ok"}}]}

    def test_http_error_retries(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        mock_config.backend.model = "test-model"
        mock_config.backend.max_retries = 2
        mock_config.backend.retry_delay = 0
        locator = OpenAICompatLocator(mock_config)

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("500")

        with patch.object(locator._client, "post", return_value=mock_resp):
            result = locator._call_api([{"role": "user", "content": "test"}])
        assert "error" in result
        assert "500" in result["error"]

    def test_generic_error_retries(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        mock_config.backend.model = "test-model"
        mock_config.backend.max_retries = 2
        mock_config.backend.retry_delay = 0
        locator = OpenAICompatLocator(mock_config)

        with patch.object(locator._client, "post", side_effect=ConnectionError("refused")):
            result = locator._call_api([{"role": "user", "content": "test"}])
        assert "error" in result
        assert "refused" in result["error"]

    def test_tools_in_payload(self):
        from src.vlm.vlm_locator import OpenAICompatLocator

        mock_config = MagicMock()
        mock_config.backend.timeout = 10
        mock_config.backend.model = "test-model"
        locator = OpenAICompatLocator(mock_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}
        mock_response.raise_for_status = MagicMock()

        tools = [{"type": "function", "function": {"name": "click"}}]
        with patch.object(locator._client, "post", return_value=mock_response) as mock_post:
            locator._call_api([{"role": "user", "content": "test"}], tools=tools)
            payload = mock_post.call_args[1]["json"]
            assert "tools" in payload
            assert payload["tool_choice"] == "auto"


class TestCreateLocator:
    def test_returns_openai_compat(self):
        from src.vlm.vlm_locator import create_vlm_locator, OpenAICompatLocator

        mock_config = MagicMock()
        result = create_vlm_locator(mock_config)
        assert isinstance(result, OpenAICompatLocator)
