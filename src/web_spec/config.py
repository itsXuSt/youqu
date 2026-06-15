# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Configuration loading for Web spec execution."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ViewportConfig:
    """Browser viewport configuration."""

    width: int = 1280
    height: int = 720


@dataclass
class WebSpecConfig:
    """Minimal configuration needed by the Web spec runner."""

    base_url: str = ""
    entry_route: str = "/"
    headless: bool = True
    viewport: ViewportConfig = field(default_factory=ViewportConfig)
    browser: str = "chromium"
    assertion_timeout_ms: int = 30000
    retry_interval_ms: int = 500
    screenshot_on_step: bool = True
    report_dir: str = "report/web_spec"
    auto_wait: str = "interactive"
    settle_ms: int = 300


_DEFAULTS = WebSpecConfig()


def load_web_spec_config(
    config_path: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> WebSpecConfig:
    """Load Web spec config from defaults, ini, env config and CLI overrides."""
    merged: dict[str, Any] = _config_to_dict(_DEFAULTS)
    merged.update(_load_global_ini_section())

    env_path = os.environ.get("YOUQU_WEB_SPEC_CONFIG", "")
    if env_path:
        merged.update(_load_yaml_config(Path(env_path)))

    if config_path:
        merged.update(_load_yaml_config(Path(config_path)))

    if overrides:
        merged.update({k: v for k, v in overrides.items() if v is not None})

    return _build_config(merged)


def _load_global_ini_section() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    ini_path = root / "setting" / "globalconfig.ini"
    if not ini_path.exists():
        return {}

    parser = configparser.ConfigParser()
    parser.read(ini_path, encoding="utf-8")
    if not parser.has_section("web_spec"):
        return {}
    return dict(parser.items("web_spec"))


def _load_yaml_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Web spec config not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Web spec config root must be a mapping: {path}")

    if "web_spec" in raw and isinstance(raw["web_spec"], dict):
        return _normalize_config_dict(raw["web_spec"])
    return _normalize_config_dict(raw)


def _normalize_config_dict(raw: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    data.update(raw)

    target = raw.get("target") if isinstance(raw.get("target"), dict) else {}
    engine = raw.get("engine") if isinstance(raw.get("engine"), dict) else {}
    paths = raw.get("paths") if isinstance(raw.get("paths"), dict) else {}

    if "base_url" in target:
        data["base_url"] = target["base_url"]
    if "headless" in target:
        data["headless"] = target["headless"]
    if "viewport" in target:
        data["viewport"] = target["viewport"]
    for key in (
        "entry_route",
        "assertion_timeout_ms",
        "retry_interval_ms",
        "screenshot_on_step",
        "auto_wait",
        "settle_ms",
    ):
        if key in engine:
            data[key] = engine[key]
    if "assertion_retry_interval_ms" in engine:
        data["retry_interval_ms"] = engine["assertion_retry_interval_ms"]
    if "report_dir" in paths:
        data["report_dir"] = paths["report_dir"]
    if "logs_dir" in paths:
        data.setdefault("report_dir", paths["logs_dir"])

    for key in ("target", "engine", "paths", "ai", "backend", "cases_dir", "proj_description"):
        data.pop(key, None)
    return data


def _build_config(raw: dict[str, Any]) -> WebSpecConfig:
    data = {str(k).lower(): v for k, v in raw.items()}
    viewport = data.get("viewport", {}) or {}
    if isinstance(viewport, str):
        width, height = _parse_viewport(viewport)
    elif isinstance(viewport, dict):
        width = int(viewport.get("width", 1280))
        height = int(viewport.get("height", 720))
    else:
        width, height = 1280, 720

    retry_interval = data.get("retry_interval_ms", data.get("assertion_retry_interval_ms", 500))
    return WebSpecConfig(
        base_url=str(data.get("base_url", "") or ""),
        entry_route=str(data.get("entry_route", "/") or "/"),
        headless=_as_bool(data.get("headless", True)),
        viewport=ViewportConfig(width=width, height=height),
        browser=str(data.get("browser", "chromium") or "chromium"),
        assertion_timeout_ms=int(data.get("assertion_timeout_ms", 30000)),
        retry_interval_ms=int(retry_interval),
        screenshot_on_step=_as_bool(data.get("screenshot_on_step", True)),
        report_dir=str(data.get("report_dir", "report/web_spec") or "report/web_spec"),
        auto_wait=str(data.get("auto_wait", "interactive") or "interactive"),
        settle_ms=int(data.get("settle_ms", 300)),
    )


def _parse_viewport(value: str) -> tuple[int, int]:
    normalized = value.lower().replace("*", "x")
    if "x" not in normalized:
        return 1280, 720
    width, height = normalized.split("x", 1)
    return int(width.strip()), int(height.strip())


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    return bool(value)


def _config_to_dict(config: WebSpecConfig) -> dict[str, Any]:
    return {
        "base_url": config.base_url,
        "entry_route": config.entry_route,
        "headless": config.headless,
        "viewport": {"width": config.viewport.width, "height": config.viewport.height},
        "browser": config.browser,
        "assertion_timeout_ms": config.assertion_timeout_ms,
        "retry_interval_ms": config.retry_interval_ms,
        "screenshot_on_step": config.screenshot_on_step,
        "report_dir": config.report_dir,
        "auto_wait": config.auto_wait,
        "settle_ms": config.settle_ms,
    }
