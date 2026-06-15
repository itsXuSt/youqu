# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Deterministic Playwright runner for Web specs."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from web_spec import action_executor, assertion_executor
from web_spec.config import WebSpecConfig
from web_spec.models import ExecutionSpec, SettleSpec, TestSpec
from web_spec.reporter import save_spec_report, save_suite_summary
from web_spec.result import (
    ActionRecord,
    AssertionRecord,
    LocatorInfo,
    RunRecord,
    RunStatus,
    StepRecord,
    StepStatus,
    SuiteRecord,
)
from web_spec.tui import RunnerEvent, RunnerEventHandler


class WebSpecRunner:
    """Run Web specs through Playwright sync API."""

    def __init__(self, config: WebSpecConfig, reporter: RunnerEventHandler | None = None):
        self.config = config
        self._reporter = reporter
        self._pw = None
        self._browser = None
        self._context = None

    def run_all(self, specs: list[TestSpec], report_dir: str | Path | None = None) -> SuiteRecord:
        suite = SuiteRecord()
        out_dir = Path(report_dir or _timestamp_dir(self.config.report_dir))
        out_dir.mkdir(parents=True, exist_ok=True)
        self._emit("suite_start", total_specs=len(specs), report_dir=str(out_dir))
        try:
            self._start_browser()
            for index, spec in enumerate(specs, start=1):
                record = self.run_spec(spec, out_dir, spec_index=index, total_specs=len(specs))
                suite.specs.append(record)
                save_spec_report(record)
        except EnvironmentError as exc:
            for spec in specs:
                record = RunRecord(
                    spec_id=spec.id,
                    spec_title=spec.title,
                    status=RunStatus.BLOCKED_ENV,
                    error=str(exc),
                    report_dir=str(out_dir / _safe_id(spec.id)),
                )
                Path(record.report_dir).mkdir(parents=True, exist_ok=True)
                record.finalize()
                suite.specs.append(record)
                save_spec_report(record)
        finally:
            self._stop_browser()
            suite.finalize()
            save_suite_summary(suite, out_dir)
            self._emit(
                "suite_end",
                total=suite.total,
                passed=suite.passed,
                failed=suite.failed,
                blocked=suite.blocked,
                cancelled=suite.cancelled,
                duration_seconds=suite.duration_seconds,
                report_dir=str(out_dir),
            )
        return suite

    def run_spec(
        self,
        spec: TestSpec,
        report_root: str | Path | None = None,
        spec_index: int = 1,
        total_specs: int = 1,
    ) -> RunRecord:
        own_browser = self._pw is None
        out_root = Path(report_root or _timestamp_dir(self.config.report_dir))
        spec_dir = out_root / _safe_id(spec.id)
        spec_dir.mkdir(parents=True, exist_ok=True)
        record = RunRecord(spec_id=spec.id, spec_title=spec.title, report_dir=str(spec_dir))
        execution = spec.execution or self._default_execution()
        self._emit(
            "spec_start",
            index=spec_index,
            total=total_specs,
            spec_id=spec.id,
            title=spec.title,
            total_steps=len(spec.steps),
            report_dir=str(spec_dir),
        )
        page = None
        try:
            if own_browser:
                self._start_browser()
            if self._context is None:
                raise EnvironmentError("浏览器上下文未初始化")
            page = self._context.new_page()
            page.goto(self._entry_url(spec), wait_until="domcontentloaded")

            for action in spec.setup:
                setup_result = action_executor.execute(page, action, execution)
                if not setup_result.success:
                    record.status = RunStatus.FAILED_SCRIPT
                    record.error = f"setup action '{setup_result.type}' failed: {setup_result.error}"
                    return record

            for step_index, step in enumerate(spec.steps, start=1):
                step_record = self._execute_step(page, spec, step, execution, spec_dir, step_index, len(spec.steps))
                record.steps.append(step_record)
                if step_record.status == StepStatus.FAILED:
                    for skipped in spec.steps[step_index:]:
                        record.steps.append(StepRecord(
                            order=skipped.order,
                            description=skipped.description,
                            status=StepStatus.SKIPPED,
                        ))
                    break
        except EnvironmentError:
            raise
        except Exception as exc:
            record.status = RunStatus.FAILED_SCRIPT
            record.error = f"执行异常: {exc}"
        finally:
            if page is not None:
                self._run_teardown(page, spec, execution, record)
                page.close()
            if own_browser:
                self._stop_browser()
            record.finalize()
            self._emit(
                "spec_end",
                spec_id=record.spec_id,
                title=record.spec_title,
                status=record.status.value,
                duration_seconds=record.duration_seconds,
                report_dir=record.report_dir,
                error=record.error,
            )
        return record

    def _execute_step(
        self,
        page: Any,
        spec: TestSpec,
        step,
        execution: ExecutionSpec,
        spec_dir: Path,
        step_index: int = 1,
        total_steps: int = 1,
    ) -> StepRecord:
        start = time.monotonic()
        step_record = StepRecord(order=step.order, description=step.description)
        self._emit(
            "step_start",
            spec_id=spec.id,
            step_index=step_index,
            total_steps=total_steps,
            order=step.order,
            description=step.description,
        )
        for action_index, action in enumerate(step.actions, start=1):
            self._emit(
                "action_start",
                spec_id=spec.id,
                step_order=step.order,
                action_index=action_index,
                total_actions=len(step.actions),
                action_type=action.type.value,
                locator=_locator_payload(action.locator),
            )
            result = action_executor.execute(page, action, execution)
            step_record.actions.append(ActionRecord(
                type=result.type,
                success=result.success,
                error=result.error,
                locator=_locator_info(result),
                duration_ms=result.duration_ms,
            ))
            self._emit(
                "action_end",
                spec_id=spec.id,
                step_order=step.order,
                action_index=action_index,
                action_type=result.type,
                success=result.success,
                error=result.error,
                locator=_record_locator_payload(_locator_info(result), fallback=action.locator),
                duration_ms=result.duration_ms,
            )
            if not result.success:
                step_record.status = StepStatus.FAILED
                break

        if step_record.status != StepStatus.FAILED:
            for assertion_index, assertion in enumerate(step.assertions, start=1):
                self._emit(
                    "assertion_start",
                    spec_id=spec.id,
                    step_order=step.order,
                    assertion_index=assertion_index,
                    total_assertions=len(step.assertions),
                    assertion_type=assertion.type.value,
                    expected=assertion.expected,
                    locator=_locator_payload(assertion.locator),
                )
                result = assertion_executor.execute(page, assertion, execution)
                step_record.assertions.append(AssertionRecord(
                    type=result.type,
                    success=result.success,
                    expected=result.expected,
                    actual=result.actual,
                    error=result.error,
                    locator=_locator_info(result),
                    duration_ms=result.duration_ms,
                    retry_count=result.retry_count,
                ))
                self._emit(
                    "assertion_end",
                    spec_id=spec.id,
                    step_order=step.order,
                    assertion_index=assertion_index,
                    assertion_type=result.type,
                    success=result.success,
                    expected=result.expected,
                    actual=result.actual,
                    error=result.error,
                    locator=_record_locator_payload(_locator_info(result), fallback=assertion.locator),
                    duration_ms=result.duration_ms,
                    retry_count=result.retry_count,
                )
                if not result.success:
                    step_record.status = StepStatus.FAILED
                    break

        if self.config.screenshot_on_step:
            try:
                screenshot_path = spec_dir / f"step_{step.order}.png"
                page.screenshot(path=str(screenshot_path))
                step_record.screenshot_path = str(screenshot_path)
                self._emit("screenshot_saved", spec_id=spec.id, step_order=step.order, path=str(screenshot_path))
            except Exception:
                pass
        step_record.duration_ms = int((time.monotonic() - start) * 1000)
        self._emit(
            "step_end",
            spec_id=spec.id,
            step_index=step_index,
            total_steps=total_steps,
            order=step.order,
            description=step.description,
            status=step_record.status.value,
            duration_ms=step_record.duration_ms,
            error=_step_error(step_record),
        )
        return step_record

    def _run_teardown(
        self,
        page: Any,
        spec: TestSpec,
        execution: ExecutionSpec,
        record: RunRecord,
    ) -> None:
        teardown = spec.teardown
        if teardown:
            for action in teardown.steps:
                result = action_executor.execute(page, action, execution)
                if not result.success and record.status == RunStatus.PASSED:
                    record.status = RunStatus.FAILED_SCRIPT
                    record.error = f"teardown action '{result.type}' failed: {result.error}"
            if teardown.reset_page_state:
                try:
                    page.context.clear_cookies()
                except Exception:
                    pass
            if teardown.restore_entry_page:
                try:
                    page.goto(self._entry_url(spec), wait_until="domcontentloaded")
                except Exception:
                    pass

    def _emit(self, kind: str, **payload: Any) -> None:
        if self._reporter is None:
            return
        try:
            self._reporter(RunnerEvent(kind=kind, payload=payload))
        except Exception:
            pass

    def _start_browser(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise EnvironmentError("Web spec 需要安装 Playwright：pip install 'youqu-framework[webui]'") from exc

        try:
            self._pw = sync_playwright().start()
            browser_launcher = getattr(self._pw, self.config.browser, None)
            if browser_launcher is None:
                raise EnvironmentError(f"不支持的浏览器类型: {self.config.browser}")
            self._browser = browser_launcher.launch(headless=self.config.headless)
            self._context = self._browser.new_context(
                viewport={"width": self.config.viewport.width, "height": self.config.viewport.height}
            )
        except EnvironmentError:
            self._stop_browser()
            raise
        except Exception as exc:
            self._stop_browser()
            raise EnvironmentError(f"Playwright 浏览器启动失败: {exc}") from exc

    def _stop_browser(self) -> None:
        if self._context is not None:
            self._context.close()
            self._context = None
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._pw is not None:
            self._pw.stop()
            self._pw = None

    def _default_execution(self) -> ExecutionSpec:
        return ExecutionSpec(
            auto_wait=self.config.auto_wait,
            settle_after_action=SettleSpec(network_idle=False, settle_ms=self.config.settle_ms),
            assertion_timeout_ms=self.config.assertion_timeout_ms,
            assertion_retry=True,
            assertion_retry_interval_ms=self.config.retry_interval_ms,
        )

    def _entry_url(self, spec: TestSpec) -> str:
        if spec.entry_url:
            return spec.entry_url
        route = spec.entry_page or self.config.entry_route
        if self.config.base_url:
            return urljoin(self.config.base_url.rstrip("/") + "/", route.lstrip("/"))
        return route


def _locator_info(result: Any) -> LocatorInfo | None:
    if not result.locator_strategy:
        return None
    return LocatorInfo(
        strategy=result.locator_strategy,
        value=result.locator_value or "",
        match_count=result.locator_match_count,
        stability=result.locator_stability or "stable_bem",
    )


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in value)


def _timestamp_dir(base: str | Path) -> Path:
    return Path(base) / time.strftime("%Y%m%d_%H%M%S")


def _locator_payload(locator: Any) -> dict | None:
    if locator is None:
        return None
    return {
        "strategy": locator.strategy.value,
        "value": locator.value,
        "match_count": None,
        "stability": locator.stability,
    }


def _record_locator_payload(locator: Any, fallback: Any = None) -> dict | None:
    if locator is None:
        return _locator_payload(fallback)
    return {
        "strategy": locator.strategy,
        "value": locator.value,
        "match_count": locator.match_count,
        "stability": locator.stability,
    }


def _step_error(step_record: StepRecord) -> str | None:
    for action in step_record.actions:
        if not action.success:
            return action.error
    for assertion in step_record.assertions:
        if not assertion.success:
            return assertion.error
    return None
