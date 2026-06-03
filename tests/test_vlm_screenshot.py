import sys
from unittest.mock import MagicMock, patch

import pytest

_ss = sys.modules["src.vlm.screenshot"]
_ss_cap_orig = _ss.capture_screen


def _mock_capture(fn):
    _ss.capture_screen = fn
    return lambda: setattr(_ss, "capture_screen", _ss_cap_orig)


class TestCropMeta:
    def test_default_values(self):
        m = _ss.CropMeta()
        assert m.offset_x == 0
        assert m.offset_y == 0
        assert m.orig_width == 0
        assert m.orig_height == 0
        assert m.cropped_width == 0
        assert m.cropped_height == 0
        assert m.vlm_width == 0
        assert m.vlm_height == 0

    def test_custom_values(self):
        m = _ss.CropMeta(offset_x=100, offset_y=200, orig_width=1920, orig_height=1080,
                         cropped_width=800, cropped_height=600, vlm_width=800, vlm_height=600)
        assert m.offset_x == 100
        assert m.vlm_width == 800

    def test_coordinate_restore_full_screen(self):
        m = _ss.CropMeta(offset_x=0, offset_y=0, cropped_width=1920, cropped_height=1080,
                         vlm_width=960, vlm_height=540)
        vlm_x, vlm_y = 480, 270
        screen_x = int(vlm_x * m.cropped_width / m.vlm_width + m.offset_x)
        screen_y = int(vlm_y * m.cropped_height / m.vlm_height + m.offset_y)
        assert screen_x == 960
        assert screen_y == 540

    def test_coordinate_restore_with_offset(self):
        m = _ss.CropMeta(offset_x=100, offset_y=50, cropped_width=800, cropped_height=600,
                         vlm_width=400, vlm_height=300)
        vlm_x, vlm_y = 200, 150
        screen_x = int(vlm_x * m.cropped_width / m.vlm_width + m.offset_x)
        screen_y = int(vlm_y * m.cropped_height / m.vlm_height + m.offset_y)
        assert screen_x == 500
        assert screen_y == 350

    def test_coordinate_restore_fractional_rounds_down(self):
        m = _ss.CropMeta(offset_x=0, offset_y=0, cropped_width=1000, cropped_height=1000,
                         vlm_width=333, vlm_height=333)
        vlm_x = 167
        screen_x = int(vlm_x * m.cropped_width / m.vlm_width + m.offset_x)
        assert screen_x == int(167 * 1000 / 333)


class TestCaptureForVlm:
    def test_empty_capture_returns_empty(self):
        restore = _mock_capture(lambda: b"")
        try:
            data, meta = _ss.capture_for_vlm()
        finally:
            restore()
        assert data == b""
        assert meta.orig_width == 0
        assert meta.orig_height == 0

    def test_no_bounds_no_resize(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        restore = _mock_capture(lambda: raw)
        try:
            data, meta = _ss.capture_for_vlm(max_dim=500)
        finally:
            restore()
        assert meta.orig_width == 100
        assert meta.orig_height == 100
        assert meta.cropped_width == 100
        assert meta.vlm_width == 100

    def test_with_bounds_crop(self):
        from PIL import Image

        img = Image.new("RGB", (200, 200), color="blue")
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        restore = _mock_capture(lambda: raw)
        try:
            data, meta = _ss.capture_for_vlm(
                bounds={"x": 50, "y": 50, "width": 100, "height": 100}, max_dim=500)
        finally:
            restore()
        assert meta.offset_x == 50
        assert meta.offset_y == 50
        assert meta.cropped_width == 100
        assert meta.cropped_height == 100
        assert meta.orig_width == 200

    def test_resize_when_exceeds_max_dim(self):
        from PIL import Image

        img = Image.new("RGB", (300, 200), color="green")
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        restore = _mock_capture(lambda: raw)
        try:
            data, meta = _ss.capture_for_vlm(max_dim=150)
        finally:
            restore()
        assert meta.orig_width == 300
        assert meta.orig_height == 200
        assert meta.vlm_width == 150
        assert meta.vlm_height == 100

    def test_output_path_saves_file(self, tmp_path):
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="yellow")
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        restore = _mock_capture(lambda: raw)
        try:
            data, meta = _ss.capture_for_vlm(output_path=str(tmp_path / "output.png"))
        finally:
            restore()
        assert (tmp_path / "output.png").exists()

    def test_bounds_clamped_to_image_size(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="white")
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        restore = _mock_capture(lambda: raw)
        try:
            data, meta = _ss.capture_for_vlm(
                bounds={"x": -10, "y": -10, "width": 200, "height": 200}, max_dim=500)
        finally:
            restore()
        assert meta.offset_x == 0
        assert meta.offset_y == 0
        assert meta.cropped_width == 100
        assert meta.cropped_height == 100

    def test_tall_image_resize_by_width(self):
        from PIL import Image

        img = Image.new("RGB", (200, 400), color="purple")
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        restore = _mock_capture(lambda: raw)
        try:
            data, meta = _ss.capture_for_vlm(max_dim=100)
        finally:
            restore()
        assert meta.vlm_width == 50
        assert meta.vlm_height == 100


class TestCaptureToJpeg:
    def test_empty_capture(self):
        restore = _mock_capture(lambda: b"")
        try:
            result = _ss.capture_to_jpeg()
        finally:
            restore()
        assert result == b""

    def test_valid_capture_produces_jpeg(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        restore = _mock_capture(lambda: raw)
        try:
            result = _ss.capture_to_jpeg()
        finally:
            restore()
        assert result[:2] == b"\xff\xd8"

    def test_rgba_converted_to_rgb(self):
        from PIL import Image

        img = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        restore = _mock_capture(lambda: raw)
        try:
            result = _ss.capture_to_jpeg()
        finally:
            restore()
        assert len(result) > 0
        assert result[:2] == b"\xff\xd8"

    def test_max_dim_resize(self):
        from PIL import Image

        img = Image.new("RGB", (300, 200), color="green")
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        restore = _mock_capture(lambda: raw)
        try:
            result = _ss.capture_to_jpeg(max_dim=150)
        finally:
            restore()
        assert len(result) > 0
        assert result[:2] == b"\xff\xd8"


class TestIsAvailable:
    def test_true_when_capture_returns_data(self):
        restore = _mock_capture(lambda: b"\x89PNGfake")
        try:
            assert _ss.is_available() is True
        finally:
            restore()

    def test_false_when_capture_empty(self):
        restore = _mock_capture(lambda: b"")
        try:
            assert _ss.is_available() is False
        finally:
            restore()

    def test_false_when_capture_raises(self):
        def _raise():
            raise RuntimeError("no display")

        restore = _mock_capture(_raise)
        try:
            assert _ss.is_available() is False
        finally:
            restore()
