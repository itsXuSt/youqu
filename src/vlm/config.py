#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
# SPDX-FileCopyrightText: 2023 UnionTech Software Technology Co., Ltd.
# SPDX-License-Identifier: GPL-2.0-only
# pylint: disable=all

from pathlib import Path

import os

from setting.globalconfig import GetCfg, GlobalConfig

_VLM_CFG_FILE = GlobalConfig.GLOBAL_CONFIG_FILE_PATH
_vlm_cfg = GetCfg(_VLM_CFG_FILE, "vlm")


class VLMBackendConfig:
    """VLM backend API configuration."""

    def __init__(self):
        self.base_url = _vlm_cfg.get("VLM_BASE_URL", default="http://localhost:8000/v1")
        self.model = _vlm_cfg.get("VLM_MODEL", default="Qwen/Qwen2.5-VL-7B-Instruct")
        self.api_key = _vlm_cfg.get("VLM_API_KEY", default="not-needed")
        self.timeout = int(_vlm_cfg.get("VLM_TIMEOUT", default=30))
        self.max_retries = int(_vlm_cfg.get("VLM_MAX_RETRIES", default=3))
        self.retry_delay = int(_vlm_cfg.get("VLM_RETRY_DELAY", default=1))
        self.max_image_dim = int(_vlm_cfg.get("VLM_MAX_IMAGE_DIM", default=2048))


class VLMFallbackConfig:
    """VLM fallback configuration."""

    def __init__(self):
        self.confidence_threshold = float(_vlm_cfg.get("VLM_CONFIDENCE_THRESHOLD", default=0.5))


class VLMConfig:
    """VLM module configuration."""

    def __init__(self):
        self.enabled = _vlm_cfg.get_bool("VLM_ENABLED", default=False) or os.environ.get("YOUQU_VLM_ENABLED", "").lower() in ("1", "true", "yes")
        self.backend = VLMBackendConfig()
        self.fallback = VLMFallbackConfig()
        self.max_iterations = int(_vlm_cfg.get("VLM_MAX_ITERATIONS", default=20))
        self._evidence_dir = None

    @property
    def evidence_dir(self) -> Path:
        if self._evidence_dir is None:
            default_path = str(Path(GlobalConfig.REPORT_PATH) / "vlm_evidence")
            self._evidence_dir = Path(
                _vlm_cfg.get("VLM_EVIDENCE_DIR", default=default_path)
            )
            self._evidence_dir.mkdir(parents=True, exist_ok=True)
        return self._evidence_dir

    def get_safe_evidence_dir(self) -> Path:
        return self.evidence_dir

    def is_available(self) -> bool:
        """Check if VLM is enabled and httpx is available."""
        if not self.enabled:
            return False
        try:
            import httpx  # noqa: F401
            return True
        except ImportError:
            return False
