# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Load and validate Web spec suite YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from web_spec.kind import WebSpecFileKind, detect_web_spec_kind, is_suite_file
from web_spec.loader import SpecValidationError, load_spec
from web_spec.models import ActionSpec, TeardownSpec, TestSpec


class SuiteSpec(BaseModel):
    """Parsed Web spec suite."""

    model_config = ConfigDict(extra="allow")

    @field_validator("timeout", mode="before")
    @classmethod
    def _normalize_timeout(cls, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(value)

    id: str
    name: str = ""
    module: str = ""
    tags: list[str] = Field(default_factory=list)
    timeout: int | None = None
    fast_fail: bool = False
    setup: list[ActionSpec] = Field(default_factory=list)
    specs: list[TestSpec] = Field(default_factory=list)
    teardown: TeardownSpec | None = None
    source: str = ""


def load_suite(path: str | Path, require_suite_name: bool = True) -> SuiteSpec:
    """Load one suite YAML file and referenced Web specs."""
    suite_path = Path(path)
    if not suite_path.exists():
        raise FileNotFoundError(f"suite 文件不存在: {suite_path}")
    if not suite_path.is_file():
        raise SpecValidationError(f"suite 路径不是文件: {suite_path}")

    raw_text = suite_path.read_text(encoding="utf-8")
    try:
        raw_data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise SpecValidationError(f"[{suite_path}] YAML 解析失败: {exc}") from exc
    if raw_data is None:
        raise SpecValidationError(f"[{suite_path}] suite 文件为空")
    if not isinstance(raw_data, dict):
        raise SpecValidationError(f"[{suite_path}] suite 根节点必须是 mapping")

    kind = detect_web_spec_kind(raw_data)
    if kind == WebSpecFileKind.CASE:
        raise SpecValidationError(f"[{suite_path}] 检测到普通 Web Spec，请使用 youqu web-spec run 执行")
    if kind == WebSpecFileKind.INVALID:
        raise SpecValidationError(f"[{suite_path}] 同一个 YAML 不能同时包含 specs 和 steps")
    if kind != WebSpecFileKind.SUITE:
        raise SpecValidationError(f"[{suite_path}] 缺少必填字段: specs")
    if require_suite_name and not is_suite_file(suite_path):
        raise SpecValidationError(
            f"[{suite_path}] suite 文件名必须是 suite.yaml、suite.yml、*.suite.yaml 或 *.suite.yml"
        )

    return _parse_suite(raw_data, suite_path)


def _parse_suite(raw: dict[str, Any], suite_path: Path) -> SuiteSpec:
    data = dict(raw)
    data.setdefault("id", _default_suite_id(suite_path))
    data.setdefault("name", data["id"])
    data["source"] = str(suite_path)

    specs = data.get("specs")
    if not isinstance(specs, list) or not specs:
        raise SpecValidationError(f"[{suite_path}] specs 必须是非空列表")
    data["specs"] = [_load_suite_spec(item, suite_path) for item in specs]

    teardown = data.get("teardown")
    if isinstance(teardown, list):
        data["teardown"] = {"steps": teardown}

    try:
        return SuiteSpec.model_validate(data)
    except ValidationError as exc:
        raise SpecValidationError(f"[{suite_path}] suite 校验失败: {exc}") from exc


def _load_suite_spec(item: Any, suite_path: Path) -> TestSpec:
    if isinstance(item, str):
        spec_path = suite_path.parent / item
    elif isinstance(item, dict) and isinstance(item.get("path"), str):
        spec_path = suite_path.parent / item["path"]
    else:
        raise SpecValidationError(f"[{suite_path}] specs 项必须是路径字符串或包含 path 的 mapping")
    try:
        return load_spec(spec_path)
    except (FileNotFoundError, SpecValidationError) as exc:
        raise SpecValidationError(f"[{suite_path}] 加载 suite spec 失败: {exc}") from exc


def _default_suite_id(path: Path) -> str:
    stem = path.stem
    if stem.endswith(".suite"):
        return stem[:-6]
    if stem == "suite":
        return path.parent.name or stem
    return stem
