# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Load and validate Web spec YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from web_spec.models import StepSpec, TestSpec


class SpecValidationError(Exception):
    """Raised when a Web spec file cannot be parsed or validated."""


def load_spec(path: str | Path) -> TestSpec:
    """Load one Web spec YAML file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"spec 文件不存在: {file_path}")
    if not file_path.is_file():
        raise SpecValidationError(f"spec 路径不是文件: {file_path}")

    raw_text = file_path.read_text(encoding="utf-8")
    try:
        raw_data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise SpecValidationError(f"[{file_path}] YAML 解析失败: {exc}") from exc
    if raw_data is None:
        raise SpecValidationError(f"[{file_path}] spec 文件为空")
    if not isinstance(raw_data, dict):
        raise SpecValidationError(f"[{file_path}] spec 根节点必须是 mapping")

    return _parse_spec(raw_data, file_path)


def load_spec_dir(dir_path: str | Path) -> list[TestSpec]:
    """Load all .yaml/.yml Web specs from a directory recursively."""
    root = Path(dir_path)
    if not root.exists():
        raise FileNotFoundError(f"spec 目录不存在: {root}")
    if not root.is_dir():
        raise SpecValidationError(f"spec 路径不是目录: {root}")

    specs = []
    files = sorted(
        p for p in root.rglob("*.y*ml")
        if p.is_file() and p.name != "index.yaml"
    )
    for file_path in files:
        specs.append(load_spec(file_path))
    return specs


def load_specs(path: str | Path) -> list[TestSpec]:
    """Load one spec file or all specs in a directory."""
    spec_path = Path(path)
    if spec_path.is_dir():
        return load_spec_dir(spec_path)
    return [load_spec(spec_path)]


def _parse_spec(raw: dict[str, Any], file_path: Path) -> TestSpec:
    raw = dict(raw)
    if "id" not in raw:
        raw["id"] = file_path.stem
    if "title" not in raw and "name" in raw:
        raw["title"] = raw["name"]
    if "title" not in raw:
        raise SpecValidationError(f"[{file_path}] 缺少必填字段: title")
    if "steps" not in raw:
        raise SpecValidationError(f"[{file_path}] 缺少必填字段: steps")
    if not isinstance(raw["steps"], list) or not raw["steps"]:
        raise SpecValidationError(f"[{file_path}] steps 必须是非空列表")

    raw["steps"] = [_normalize_step(step, idx, file_path) for idx, step in enumerate(raw["steps"], 1)]
    raw["source"] = str(file_path)

    try:
        return TestSpec.model_validate(raw)
    except ValidationError as exc:
        raise SpecValidationError(f"[{file_path}] spec 校验失败: {exc}") from exc


def _normalize_step(raw: Any, index: int, file_path: Path) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SpecValidationError(f"[{file_path}] steps[{index}] 必须是 mapping")
    data = dict(raw)
    data.setdefault("order", index)
    data.setdefault("description", data.get("name", f"step {index}"))
    actions = data.get("actions", []) or []
    assertions = data.get("assertions", []) or data.get("assert", []) or []
    if not isinstance(actions, list):
        raise SpecValidationError(f"[{file_path}] steps[{index}].actions 必须是列表")
    if not isinstance(assertions, list):
        raise SpecValidationError(f"[{file_path}] steps[{index}].assertions 必须是列表")
    if not actions and not assertions:
        raise SpecValidationError(
            f"[{file_path}] steps[{index}] 必须包含至少一个 action 或 assertion"
        )
    data["actions"] = actions
    data["assertions"] = assertions
    return data
