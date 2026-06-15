# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Execution result data models for Web spec runs."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    """Overall spec status."""

    PASSED = "passed"
    FAILED_PRODUCT = "failed_product"
    FAILED_SCRIPT = "failed_script"
    BLOCKED_ENV = "blocked_env"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Single step status."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class LocatorInfo:
    """Locator metadata captured during execution."""

    strategy: str
    value: str
    match_count: int = 0
    stability: str = "stable_bem"


@dataclass
class ActionRecord:
    """Single action execution record."""

    type: str
    success: bool = True
    error: str | None = None
    locator: LocatorInfo | None = None
    duration_ms: int = 0


@dataclass
class AssertionRecord:
    """Single assertion execution record."""

    type: str
    success: bool = True
    expected: Any = None
    actual: Any = None
    error: str | None = None
    locator: LocatorInfo | None = None
    duration_ms: int = 0
    retry_count: int = 0


@dataclass
class StepRecord:
    """Single step execution record."""

    order: int
    description: str
    status: StepStatus = StepStatus.PASSED
    actions: list[ActionRecord] = field(default_factory=list)
    assertions: list[AssertionRecord] = field(default_factory=list)
    screenshot_path: str | None = None
    duration_ms: int = 0


@dataclass
class RunRecord:
    """Single spec execution record."""

    spec_id: str
    spec_title: str
    status: RunStatus = RunStatus.PASSED
    steps: list[StepRecord] = field(default_factory=list)
    error: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float = 0
    duration_seconds: float = 0
    report_dir: str | None = None

    def finalize(self) -> None:
        self.end_time = time.time()
        self.duration_seconds = round(self.end_time - self.start_time, 2)
        if self.status in (RunStatus.BLOCKED_ENV, RunStatus.CANCELLED):
            return
        if self.error and self.status == RunStatus.PASSED:
            self.status = RunStatus.FAILED_SCRIPT
            return
        if any(step.status == StepStatus.FAILED for step in self.steps):
            self.status = RunStatus.FAILED_PRODUCT


@dataclass
class SuiteRecord:
    """Suite execution record."""

    specs: list[RunRecord] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float = 0
    duration_seconds: float = 0

    def finalize(self) -> None:
        self.end_time = time.time()
        self.duration_seconds = round(self.end_time - self.start_time, 2)

    @property
    def total(self) -> int:
        return len(self.specs)

    @property
    def passed(self) -> int:
        return sum(1 for item in self.specs if item.status == RunStatus.PASSED)

    @property
    def failed(self) -> int:
        return sum(
            1 for item in self.specs
            if item.status in (RunStatus.FAILED_PRODUCT, RunStatus.FAILED_SCRIPT)
        )

    @property
    def blocked(self) -> int:
        return sum(1 for item in self.specs if item.status == RunStatus.BLOCKED_ENV)

    @property
    def cancelled(self) -> int:
        return sum(1 for item in self.specs if item.status == RunStatus.CANCELLED)


def to_dict(value: Any) -> Any:
    """Convert result dataclasses and enums to JSON-serializable objects."""
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {k: to_dict(v) for k, v in asdict(value).items()}
    if isinstance(value, list):
        return [to_dict(v) for v in value]
    if isinstance(value, dict):
        return {k: to_dict(v) for k, v in value.items()}
    return value
