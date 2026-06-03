#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
# SPDX-FileCopyrightText: 2023 UnionTech Software Technology Co., Ltd.
# SPDX-License-Identifier: GPL-2.0-only
# pylint: disable=all
"""VLM executor - execution layer component for VLM-assisted operations."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from src.vlm.screenshot import capture_for_vlm
from src.vlm.vlm_locator import ClickTarget, VLMLocator

if TYPE_CHECKING:
    from src.vlm.config import VLMConfig

logger = logging.getLogger(__name__)


@dataclass
class VLMActionResult:
    """VLM operation result."""

    success: bool
    x: int = None  # type: ignore[assignment]
    y: int = None  # type: ignore[assignment]
    confidence: float = 0.0
    message: str = ""
    screenshot_path: str = ""


class VLMExecutor:
    """VLM-assisted executor for scenarios where AT-SPI cannot locate elements."""

    def __init__(
        self,
        locator: VLMLocator,
        config: "VLMConfig",
    ) -> None:
        self._locator = locator
        self._config = config
        self._evidence_dir = config.get_safe_evidence_dir()
        self._screen_size = None

    def _get_screen_size(self) -> tuple:
        """Get screen dimensions using youqu MouseKey."""
        if self._screen_size:
            return self._screen_size
        try:
            from src.mouse_key import MouseKey

            self._screen_size = MouseKey.screen_size()
            return self._screen_size
        except Exception as e:
            logger.warning("Failed to get screen size: {}".format(e))
        return (3840, 2160)

    def click_by_description(
        self,
        description: str,
        bounds: dict = None,  # type: ignore[assignment]
        save_evidence: bool = True,
    ) -> VLMActionResult:
        """
        Locate and click element through natural language description.

        Args:
            description: Element description, e.g. "main menu button"
            bounds: Optional window bounds for cropping screenshot
            save_evidence: Whether to save screenshot evidence
        """
        from src.mouse_key import MouseKey

        img_path = self._evidence_dir / "vlm_locate.png"
        self._evidence_dir.mkdir(parents=True, exist_ok=True)
        img_bytes, crop_meta = capture_for_vlm(
            bounds=bounds,
            max_dim=self._config.backend.max_image_dim,
            output_path=str(img_path),
        )

        target = self._locator.locate_element(
            img_path,
            description=description,
            crop_meta=crop_meta.__dict__ if crop_meta else None,
        )

        if not target:
            return VLMActionResult(
                success=False,
                message="VLM failed to locate: {}".format(description),
                screenshot_path=str(img_path) if save_evidence else "",
            )

        if target.confidence < self._config.fallback.confidence_threshold:
            return VLMActionResult(
                success=False,
                confidence=target.confidence,
                message="Low confidence: {:.2f}".format(target.confidence),
                screenshot_path=str(img_path) if save_evidence else "",
            )

        screen_width, screen_height = self._get_screen_size()
        if not (0 <= target.x <= screen_width and 0 <= target.y <= screen_height):
            logger.warning(
                "Coordinates out of bounds: ({}), "
                "screen: {}x{}".format(
                    (target.x, target.y), screen_width, screen_height
                )
            )
            return VLMActionResult(
                success=False,
                x=target.x,
                y=target.y,
                confidence=target.confidence,
                message="Coordinates out of bounds: ({})".format(
                    (target.x, target.y)
                ),
                screenshot_path=str(img_path) if save_evidence else "",
            )

        MouseKey().click(target.x, target.y)

        return VLMActionResult(
            success=True,
            x=target.x,
            y=target.y,
            confidence=target.confidence,
            message="Clicked at ({})".format((target.x, target.y)),
            screenshot_path=str(img_path) if save_evidence else "",
        )

    def locate_for_context_menu(
        self,
        description: str,
        screen_bounds: dict = None,  # type: ignore[assignment]
    ) -> ClickTarget:
        """
        Locate context menu item (dedicated method).

        Args:
            description: Menu item description, e.g. "copy", "paste"
            screen_bounds: Screen bounds
        """
        img_path = self._evidence_dir / "vlm_context_menu.png"
        img_bytes, crop_meta = capture_for_vlm(
            bounds=screen_bounds,
            max_dim=self._config.backend.max_image_dim,
            output_path=str(img_path),
        )

        return self._locator.locate_element(
            img_path,
            description="右键菜单中的'{}'选项".format(description),
            crop_meta=crop_meta.__dict__ if crop_meta else None,
        )
