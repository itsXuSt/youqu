# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""YAML schema parsing with Pydantic models and variable substitution.

Schema:
    name: "test title"           # required
    app: "app-name"              # optional
    screenshot: false            # optional, default false
    vars:                        # optional, ${VAR} substitution
      KEY: "value"
    setup:                       # required, list of ActionStep
      - action: session_start
        command: "app ${KEY}"
    steps:                       # required, list of ActionStep
      - action: element_action
        selector: {name: "OK"}
        do: click
    teardown:                    # required, list of ActionStep
      - action: session_stop
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.yaml_test.elements import load_elements, ElementError as ElementLoadError


class Selector(BaseModel):
    """AT-SPI element selector."""

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    role: Optional[str] = None
    accessible_id: Optional[str] = None
    index: Optional[int] = None


class WaitCondition(BaseModel):
    """Conditional wait specification."""

    model_config = ConfigDict(extra="allow")

    selector: Selector
    timeout: int = 5000
    interval: int = 200


class AssertStep(BaseModel):
    """A single assertion within a step."""

    model_config = ConfigDict(extra="allow")

    type: str
    selector: Optional[Selector] = None
    expected: Optional[Any] = None
    value: Optional[Any] = None
    app: Optional[str] = None
    path: Optional[str] = None
    expr: Optional[str] = None
    number: Optional[int] = None


class ActionStep(BaseModel):
    """A single action step in setup/steps/teardown."""

    model_config = ConfigDict(extra="allow")

    action: str
    name: str = ""
    ref: Optional[str] = None
    selector: Optional[Selector] = None
    do: Optional[str] = None
    items: Optional[list] = None
    command: Optional[str] = None
    wait: Optional[float] = None
    wait_after: Optional[int] = None
    wait_for: Optional[WaitCondition] = None
    x: Optional[int] = None
    y: Optional[int] = None
    amount: Optional[int] = None
    keys: Optional[Any] = None
    text: Optional[str] = None
    assert_steps: list[AssertStep] = Field(default_factory=list, alias="assert")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class TestCase(BaseModel):
    """Parsed YAML test case."""

    model_config = ConfigDict(extra="allow")

    name: str
    app: str = ""
    screenshot: bool = False
    vars: dict[str, Any] = Field(default_factory=dict)
    setup: list[ActionStep] = Field(default_factory=list)
    steps: list[ActionStep] = Field(default_factory=list)
    teardown: list[ActionStep] = Field(default_factory=list)
    elements: dict[str, dict[str, Any]] = Field(default_factory=dict)


_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _substitute(value: Any, variables: dict[str, Any]) -> Any:
    """Recursively replace ${VAR} in strings within any data structure."""
    if isinstance(value, str):
        return _VAR_PATTERN.sub(
            lambda m: str(variables.get(m.group(1), m.group(0))), value
        )
    if isinstance(value, dict):
        return {k: _substitute(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, variables) for v in value]
    return value


def parse_testcase(path) -> TestCase:
    """Read and validate a YAML test case file.

    Args:
        path: Path to the .yaml file (str or pathlib.Path).

    Returns:
        Validated TestCase model.

    Raises:
        ValidationError: If schema validation fails.
        yaml.YAMLError: If YAML parsing fails.
        FileNotFoundError: If file doesn't exist.
    """
    file_path = Path(path)
    raw_text = file_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(raw_text)

    if raw_data is None:
        raise ValueError("YAML file is empty")
    if not isinstance(raw_data, dict):
        raise ValueError("YAML root must be a mapping")

    variables = raw_data.get("vars", {}) or {}
    if isinstance(variables, dict):
        substituted = _substitute(raw_data, variables)
    else:
        substituted = raw_data

    testcase = TestCase.model_validate(substituted)

    try:
        testcase.elements = load_elements(file_path)
    except ElementLoadError:
        raise

    return testcase
