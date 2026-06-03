#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
# SPDX-FileCopyrightText: 2023 UnionTech Software Technology Co., Ltd.
# SPDX-License-Identifier: GPL-2.0-only
# pylint: disable=all
from __future__ import annotations

import io
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CropMeta:
    """Cropping metadata for coordinate restoration.

    VLM image space → screen space mapping:
        scale_x = crop_width / vlm_width
        screen_x = vlm_x * scale_x + offset_x
    """

    offset_x: int = 0
    offset_y: int = 0
    orig_width: int = 0
    orig_height: int = 0
    cropped_width: int = 0
    cropped_height: int = 0
    vlm_width: int = 0  # Actual image dimensions sent to VLM
    vlm_height: int = 0  # (may differ from cropped if resized)


def capture_screen() -> bytes:
    """Capture screen using pyscreenshot as primary, fallback to grim/scrot."""
    try:
        import pyscreenshot as ImageGrab

        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        pass

    for cmd in [
        ["grim", "-"],
        ["scrot", "-"],
        ["xdg-screenshot", "full", "-"],
    ]:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except Exception:
            continue
    return b""


def capture_to_jpeg(quality: int = 60, max_dim: int = None) -> bytes:  # type: ignore[assignment]
    """Capture screen and convert to JPEG bytes."""
    from PIL import Image

    raw = capture_screen()
    if not raw:
        return b""

    img = Image.open(io.BytesIO(raw))
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if max_dim and max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def is_available() -> bool:
    """Check if screenshot capture is available."""
    try:
        raw = capture_screen()
        return len(raw) > 0
    except Exception:
        return False


def capture_for_vlm(
    bounds: dict = None,  # type: ignore[assignment]
    max_dim: int = 2048,
    output_path: str = None,  # type: ignore[assignment]
) -> tuple:
    """
    Capture screenshot optimized for VLM processing.

    Args:
        bounds: Window bounds {x, y, width, height}, None for fullscreen
        max_dim: Maximum dimension limit for VLM
        output_path: Optional path to save the image

    Returns:
        Tuple of (image_bytes, crop_meta)
    """
    from PIL import Image

    raw = capture_screen()
    if not raw:
        return b"", CropMeta()

    img = Image.open(io.BytesIO(raw))
    orig_w, orig_h = img.size
    meta = CropMeta(orig_width=orig_w, orig_height=orig_h)

    if bounds:
        x1 = max(0, bounds["x"])
        y1 = max(0, bounds["y"])
        x2 = min(orig_w, bounds["x"] + bounds["width"])
        y2 = min(orig_h, bounds["y"] + bounds["height"])

        img = img.crop((x1, y1, x2, y2))
        meta = CropMeta(
            offset_x=x1,
            offset_y=y1,
            orig_width=orig_w,
            orig_height=orig_h,
            cropped_width=x2 - x1,
            cropped_height=y2 - y1,
        )
    else:
        meta.cropped_width = orig_w
        meta.cropped_height = orig_h

    # Actual image dimensions (after resize) sent to VLM
    meta.vlm_width = img.size[0]
    meta.vlm_height = img.size[1]

    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        meta.vlm_width = new_size[0]
        meta.vlm_height = new_size[1]

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    data = buf.getvalue()

    if output_path:
        Path(output_path).write_bytes(data)

    return data, meta
