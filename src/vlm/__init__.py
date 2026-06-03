#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
# SPDX-FileCopyrightText: 2023 UnionTech Software Technology Co., Ltd.
# SPDX-License-Identifier: GPL-2.0-only
# pylint: disable=all
"""VLM (Vision Language Model) module for youqu framework."""
from src.vlm.config import VLMConfig
from src.vlm.screenshot import CropMeta, capture_for_vlm
from src.vlm.vlm_agent import VLMAgent
from src.vlm.vlm_executor import VLMActionResult, VLMExecutor
from src.vlm.vlm_locator import (
    ClickTarget,
    VLMAssertResult,
    VLMLocator,
    create_vlm_locator,
)

__all__ = [
    "VLMConfig",
    "CropMeta",
    "capture_for_vlm",
    "VLMAgent",
    "VLMActionResult",
    "VLMExecutor",
    "ClickTarget",
    "VLMAssertResult",
    "VLMLocator",
    "create_vlm_locator",
]
