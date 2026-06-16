# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for WebSpecRunner suite execution."""

from web_spec.config import WebSpecConfig
from web_spec.models import TestSpec
from web_spec.result import RunRecord, RunStatus, StepRecord
from web_spec.runner import WebSpecRunner
from web_spec.suite import SuiteSpec


def _spec(spec_id, **kwargs):
    data = {
        "id": spec_id,
        "title": spec_id,
        "steps": [{
            "description": "检查",
            "assertions": [{"type": "visible", "locator": {"strategy": "text", "value": "ok"}}],
        }],
    }
    data.update(kwargs)
    return TestSpec.model_validate(data)


class FakePage:
    def __init__(self):
        self.closed = False
        self.urls = []
        self.cookies_cleared = False
        self.context = self
        self.screenshots = []
        self.waits = []

    def goto(self, url, wait_until=None):
        self.urls.append(url)

    def close(self):
        self.closed = True

    def clear_cookies(self):
        self.cookies_cleared = True

    def screenshot(self, path):
        self.screenshots.append(path)

    def wait_for_timeout(self, timeout_ms):
        self.waits.append(timeout_ms)


class FakeContext:
    def __init__(self):
        self.pages = []

    def new_page(self):
        page = FakePage()
        self.pages.append(page)
        return page

    def close(self):
        pass


def test_run_suite_uses_one_shared_page_for_all_specs(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    context = FakeContext()
    runner._context = context
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: None)
    used_pages = []

    def fake_execute_step(page, spec, step, execution, spec_dir, step_index=1, total_steps=1):
        used_pages.append((spec.id, page))
        return StepRecord(order=step.order, description=step.description)

    monkeypatch.setattr(runner, "_execute_step", fake_execute_step)
    suite_spec = SuiteSpec(id="suite", name="Suite", specs=[_spec("first"), _spec("second")])

    suite = runner.run_suite(suite_spec, report_dir=tmp_path)

    assert suite.passed == 2
    assert len(context.pages) == 1
    assert [item[0] for item in used_pages] == ["first", "second"]
    assert used_pages[0][1] is context.pages[0]
    assert used_pages[1][1] is context.pages[0]
    assert context.pages[0].closed is True


def test_run_suite_navigates_only_once_at_start(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    context = FakeContext()
    runner._context = context
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: None)
    monkeypatch.setattr(
        runner,
        "_execute_step",
        lambda page, spec, step, execution, spec_dir, step_index=1, total_steps=1: StepRecord(
            order=step.order,
            description=step.description,
        ),
    )
    suite_spec = SuiteSpec(
        id="suite",
        name="Suite",
        specs=[_spec("first", entry_page="/start"), _spec("second", entry_page="/other")],
    )

    runner.run_suite(suite_spec, report_dir=tmp_path)

    assert context.pages[0].urls == ["http://example.test/start"]


def test_run_suite_skips_spec_teardown_until_suite_teardown(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    context = FakeContext()
    runner._context = context
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: None)
    monkeypatch.setattr(
        runner,
        "_execute_step",
        lambda page, spec, step, execution, spec_dir, step_index=1, total_steps=1: StepRecord(
            order=step.order,
            description=step.description,
        ),
    )
    suite_spec = SuiteSpec(
        id="suite",
        name="Suite",
        specs=[_spec("first", teardown={"reset_page_state": True}), _spec("second")],
    )

    runner.run_suite(suite_spec, report_dir=tmp_path)

    assert context.pages[0].cookies_cleared is False


def test_run_suite_setup_uses_shared_page(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    context = FakeContext()
    runner._context = context
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: None)
    lifecycle_pages = []
    step_pages = []

    def fake_lifecycle(page, actions, execution):
        lifecycle_pages.append(page)
        return None

    def fake_execute_step(page, spec, step, execution, spec_dir, step_index=1, total_steps=1):
        step_pages.append(page)
        return StepRecord(order=step.order, description=step.description)

    monkeypatch.setattr(runner, "_execute_lifecycle_actions", fake_lifecycle)
    monkeypatch.setattr(runner, "_execute_step", fake_execute_step)
    suite_spec = SuiteSpec.model_validate({
        "id": "suite",
        "name": "Suite",
        "setup": [{"type": "wait_for", "timeout_ms": 1}],
        "specs": [_spec("first")],
    })

    runner.run_suite(suite_spec, report_dir=tmp_path)

    assert lifecycle_pages == [context.pages[0]]
    assert step_pages == [context.pages[0]]


def test_run_suite_fast_fail_marks_remaining_specs_cancelled(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    runner._context = FakeContext()
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: None)

    def fake_run_spec_on_page(page, spec, report_root, spec_index=1, total_specs=1, **kwargs):
        record = RunRecord(
            spec_id=spec.id,
            spec_title=spec.title,
            report_dir=str(tmp_path / spec.id),
            suite_id=kwargs["suite"].suite_id,
            suite_order=spec_index,
        )
        if spec.id == "first":
            record.status = RunStatus.FAILED_PRODUCT
            record.error = "failed"
        record.finalize()
        return record

    monkeypatch.setattr(runner, "_run_spec_on_page", fake_run_spec_on_page)
    suite_spec = SuiteSpec(id="suite", name="Suite", fast_fail=True, specs=[_spec("first"), _spec("second")])

    suite = runner.run_suite(suite_spec, report_dir=tmp_path)

    assert [record.status for record in suite.specs] == [RunStatus.FAILED_PRODUCT, RunStatus.CANCELLED]
    assert "fast_fail" in suite.specs[1].error
    assert suite.specs[1].suite_id == "suite"
    assert suite.specs[1].suite_order == 2
    assert (tmp_path / "summary.json").exists()


def test_run_suite_runs_teardown_after_failed_spec(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    context = FakeContext()
    runner._context = context
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: None)
    lifecycle_pages = []

    def fake_lifecycle(page, teardown, execution):
        lifecycle_pages.append(page)
        return None

    def fake_run_spec_on_page(page, spec, report_root, spec_index=1, total_specs=1, **kwargs):
        record = RunRecord(
            spec_id=spec.id,
            spec_title=spec.title,
            status=RunStatus.FAILED_PRODUCT,
            error="failed",
            report_dir=str(tmp_path / spec.id),
        )
        record.finalize()
        return record

    monkeypatch.setattr(runner, "_run_lifecycle_teardown_on_page", fake_lifecycle)
    monkeypatch.setattr(runner, "_run_spec_on_page", fake_run_spec_on_page)
    suite_spec = SuiteSpec.model_validate({
        "id": "suite",
        "name": "Suite",
        "specs": [_spec("first")],
        "teardown": {"steps": [{"type": "press_key", "key": "Escape"}]},
    })

    suite = runner.run_suite(suite_spec, report_dir=tmp_path)

    assert suite.failed == 1
    assert lifecycle_pages == [context.pages[0]]


def test_run_suite_setup_failure_cancels_all_specs(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    context = FakeContext()
    runner._context = context
    stopped = []
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: stopped.append(True))
    monkeypatch.setattr(runner, "_execute_lifecycle_actions", lambda page, actions, execution: "setup failed")
    suite_spec = SuiteSpec.model_validate({
        "id": "suite",
        "name": "Suite",
        "setup": [{"type": "wait_for", "timeout_ms": 1}],
        "specs": [_spec("first"), _spec("second")],
    })

    suite = runner.run_suite(suite_spec, report_dir=tmp_path)

    assert suite.cancelled == 2
    assert suite.error == "suite setup failed: setup failed"
    assert [record.suite_order for record in suite.specs] == [1, 2]
    assert stopped == [True]
    assert context.pages[0].closed is True
    assert (tmp_path / "summary.json").exists()


def test_run_suite_teardown_resets_page_state(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    context = FakeContext()
    runner._context = context
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: None)
    monkeypatch.setattr(
        runner,
        "_execute_step",
        lambda page, spec, step, execution, spec_dir, step_index=1, total_steps=1: StepRecord(
            order=step.order,
            description=step.description,
        ),
    )
    suite_spec = SuiteSpec.model_validate({
        "id": "suite",
        "name": "Suite",
        "specs": [_spec("first")],
        "teardown": {"reset_page_state": True, "restore_entry_page": True},
    })

    runner.run_suite(suite_spec, report_dir=tmp_path)

    shared_page = context.pages[0]
    assert len(context.pages) == 1
    assert shared_page.cookies_cleared is True
    assert shared_page.urls == ["http://example.test/", "http://example.test/"]
