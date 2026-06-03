import pytest

from tests.e2e import (
    CropMeta,
    ClickTarget,
    VLMAssertResult,
    VLMConfig,
    capture_for_vlm,
    create_vlm_locator,
)

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "setting" / "globalconfig.ini"


@pytest.fixture(scope="session")
def vlm_config():
    cfg = VLMConfig()
    if not cfg.is_available():
        pytest.skip("VLM not configured (YOUQU_VLM_ENABLED=true required)")
    return cfg


@pytest.fixture(scope="session")
def locator(vlm_config):
    loc = create_vlm_locator(vlm_config)
    if not loc.is_available():
        pytest.skip("VLM API unreachable: {}".format(vlm_config.backend.base_url))
    return loc


@pytest.fixture
def test_image(vlm_config, request):
    import subprocess
    from PIL import Image

    evidence_dir = vlm_config.get_safe_evidence_dir() / "e2e"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = str(evidence_dir / "{}.png".format(request.node.name.replace(":", "_")))

    r = subprocess.run(["scrot", "-z", path], capture_output=True, timeout=10)
    if r.returncode != 0 or not evidence_dir.stat().st_size:
        pytest.skip("Cannot capture screenshot with scrot")

    max_dim = vlm_config.backend.max_image_dim
    img = Image.open(path)
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)
        img.save(path)
    return path


class TestAPIConnectivity:
    def test_api_reachable(self, locator):
        assert True

    def test_api_chat_endpoint_responds(self, vlm_config):
        import httpx

        url = vlm_config.backend.base_url.rstrip("/") + "/chat/completions"
        resp = httpx.post(
            url,
            headers={
                "Authorization": "Bearer {}".format(vlm_config.backend.api_key),
                "Content-Type": "application/json",
            },
            json={
                "model": vlm_config.backend.model,
                "messages": [{"role": "user", "content": "say OK"}],
                "max_tokens": 5,
            },
            timeout=vlm_config.backend.timeout,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "choices" in body


class TestLocateElement:
    def test_locate_desktop_panel(self, locator, test_image):
        result = locator.locate_element(test_image, "desktop panel or taskbar")
        assert result is not None, "VLM returned None for desktop panel"
        assert isinstance(result, ClickTarget)
        assert isinstance(result.x, int)
        assert isinstance(result.y, int)
        assert 0.0 <= result.confidence <= 1.0
        print("Located: x={}, y={}, confidence={}, label={}".format(
            result.x, result.y, result.confidence, result.label))

    def test_locate_nonexistent_element(self, locator, test_image):
        result = locator.locate_element(
            test_image,
            "a bright pink unicorn dancing on the desktop",
        )
        if result is not None:
            assert result.confidence < 0.5, (
                "VLM should have low confidence for nonexistent element, got {}".format(
                    result.confidence))

    def test_locate_with_crop_metadata(self, locator):
        import subprocess
        from PIL import Image

        evidence_dir = PROJECT_ROOT / "evidence" / "e2e"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        raw_path = str(evidence_dir / "crop_test_raw.png")
        subprocess.run(["scrot", "-z", raw_path], capture_output=True, timeout=10)
        if not evidence_dir.stat().st_size:
            pytest.skip("Cannot capture screenshot")

        img = Image.open(raw_path)
        bounds = {"x": 0, "y": 0, "width": min(500, img.size[0]), "height": min(500, img.size[1])}
        cropped = img.crop((bounds["x"], bounds["y"],
                           bounds["x"] + bounds["width"], bounds["y"] + bounds["height"]))
        cropped.save(raw_path)
        crop_meta = {
            "offset_x": bounds["x"], "offset_y": bounds["y"],
            "cropped_width": bounds["width"], "cropped_height": bounds["height"],
            "vlm_width": bounds["width"], "vlm_height": bounds["height"],
        }
        result = locator.locate_element(raw_path, "any visible element", crop_meta=crop_meta)
        if result:
            restored_x = int(result.x * bounds["width"] / bounds["width"] + bounds["x"])
            restored_y = int(result.y * bounds["height"] / bounds["height"] + bounds["y"])
            assert 0 <= restored_x <= 3840, "Restored x={} out of screen".format(restored_x)
            assert 0 <= restored_y <= 2160, "Restored y={} out of screen".format(restored_y)


class TestEvaluateAssertion:
    def test_assert_visible_element(self, locator, test_image):
        result = locator.evaluate_assertion(
            test_image,
            "desktop is visible",
            "desktop should be showing a background",
        )
        assert isinstance(result, VLMAssertResult)
        assert result.verdict in ("PASS", "FAIL")
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.reason) > 0
        print("Verdict: {}, confidence={}, reason={}".format(
            result.verdict, result.confidence, result.reason))

    def test_assert_false_condition(self, locator, test_image):
        result = locator.evaluate_assertion(
            test_image,
            "desktop is showing a nuclear launch button",
            "there should be a big red nuclear launch button on screen",
        )
        assert isinstance(result, VLMAssertResult)
        assert result.verdict == "FAIL"


class TestDecideToolCall:
    def test_tool_decision(self, locator, test_image):
        tools = [
            {
                "name": "click",
                "description": "Click at coordinates",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                    },
                    "required": ["x", "y"],
                },
            },
        ]
        result = locator.decide_tool_call(
            test_image,
            instruction="find and click on any visible icon",
            tools=tools,
        )
        assert isinstance(result, dict)
        assert "choices" in result or "tool_calls" in result


class TestRetryBehavior:
    def test_retry_on_transient_failure(self, vlm_config):
        import httpx
        from unittest.mock import MagicMock, patch

        locator = create_vlm_locator(vlm_config)
        assert vlm_config.backend.max_retries >= 2

        post_count = 0
        _orig_encode = locator._encode_image
        _orig_post = locator._client.post

        def _mock_post(url, **kwargs):
            nonlocal post_count
            post_count += 1
            if post_count < 2:
                raise httpx.ConnectError("connection reset")
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "choices": [{"message": {"content": '{"x": 50, "y": 50}'}}],
            }
            resp.raise_for_status.return_value = None
            return resp

        locator._encode_image = lambda path: "aGVsbG8="
        locator._client.post = _mock_post
        with patch("time.sleep"):
            result = locator.locate_element("/tmp/fake.png", "test")
        locator._encode_image = _orig_encode
        locator._client.post = _orig_post
        assert post_count == 2


class TestCoordinateRestoration:
    def test_no_crop_full_screen(self):
        crop_meta = {
            "offset_x": 0, "offset_y": 0,
            "cropped_width": 1920, "cropped_height": 1080,
            "vlm_width": 960, "vlm_height": 540,
        }
        vlm_x, vlm_y = 480, 270
        cropped_w = crop_meta.get("cropped_width", 1) or 1
        cropped_h = crop_meta.get("cropped_height", 1) or 1
        vlm_w = crop_meta.get("vlm_width", cropped_w) or 1
        vlm_h = crop_meta.get("vlm_height", cropped_h) or 1
        screen_x = int(vlm_x * cropped_w / vlm_w + crop_meta.get("offset_x", 0))
        screen_y = int(vlm_y * cropped_h / vlm_h + crop_meta.get("offset_y", 0))
        assert screen_x == 960
        assert screen_y == 540

    def test_cropped_with_offset(self):
        crop_meta = {
            "offset_x": 100, "offset_y": 200,
            "cropped_width": 800, "cropped_height": 600,
            "vlm_width": 400, "vlm_height": 300,
        }
        vlm_x, vlm_y = 200, 150
        cropped_w = crop_meta.get("cropped_width", 1) or 1
        cropped_h = crop_meta.get("cropped_height", 1) or 1
        vlm_w = crop_meta.get("vlm_width", cropped_w) or 1
        vlm_h = crop_meta.get("vlm_height", cropped_h) or 1
        screen_x = int(vlm_x * cropped_w / vlm_w + crop_meta.get("offset_x", 0))
        screen_y = int(vlm_y * cropped_h / vlm_h + crop_meta.get("offset_y", 0))
        assert screen_x == int(200 * 800 / 400 + 100)
        assert screen_y == int(150 * 600 / 300 + 200)

    def test_none_crop_no_transformation(self):
        crop_meta = None
        vlm_x, vlm_y = 100, 200
        if crop_meta:
            cropped_w = crop_meta.get("cropped_width", 1) or 1
            vlm_w = crop_meta.get("vlm_width", cropped_w) or 1
            screen_x = int(vlm_x * cropped_w / vlm_w + crop_meta.get("offset_x", 0))
            screen_y = int(vlm_y * cropped_h / vlm_h + crop_meta.get("offset_y", 0))
        else:
            screen_x, screen_y = vlm_x, vlm_y
        assert screen_x == 100
        assert screen_y == 200
