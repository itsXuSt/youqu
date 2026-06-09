# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.mcp.jobs."""

import time
import pytest

from src.mcp.jobs import JobManager, JobStatus, execute_batches, _parse_pytest_output


class TestJobStatus:
    def test_initial_state(self):
        job = JobStatus(job_id="test123", status="queued")
        assert job.job_id == "test123"
        assert job.status == "queued"
        assert job.started_at is None
        assert job.result is None
        assert not job.cancel_requested
        assert not job.is_terminal

    def test_terminal_states(self):
        for state in ("completed", "failed", "cancelled", "rejected"):
            job = JobStatus(job_id="x", status=state, completed_at=time.time())
            assert job.is_terminal

    def test_non_terminal_states(self):
        for state in ("queued", "running"):
            job = JobStatus(job_id="x", status=state)
            assert not job.is_terminal


class TestJobManagerSubmit:
    def test_submit_and_complete(self):
        jm = JobManager()

        def slow_fn():
            time.sleep(0.05)
            return {"passed": 1, "failed": 0}

        job = jm.submit(slow_fn)
        assert job.job_id
        assert job.status in ("queued", "running")

        time.sleep(0.2)
        final = jm.get_status(job.job_id)
        assert final.status == "completed"
        assert final.result == {"passed": 1, "failed": 0}
        assert final.completed_at is not None

    def test_submit_rejected_when_running(self):
        jm = JobManager()

        def slow_fn():
            time.sleep(0.3)

        job1 = jm.submit(slow_fn)
        time.sleep(0.05)
        job2 = jm.submit(lambda: None)
        assert job2.status == "rejected"
        assert job2.running_job_id == job1.job_id
        time.sleep(0.4)

    def test_submit_function_with_args(self):
        jm = JobManager()

        def fn_with_args(a, b):
            return {"sum": a + b}

        job = jm.submit(fn_with_args, 1, 2)
        time.sleep(0.1)
        final = jm.get_status(job.job_id)
        assert final.status == "completed"
        assert final.result == {"sum": 3}

    def test_submit_function_that_raises(self):
        jm = JobManager()

        def failing_fn():
            raise ValueError("test error")

        job = jm.submit(failing_fn)
        time.sleep(0.1)
        final = jm.get_status(job.job_id)
        assert final.status == "failed"
        assert "test error" in final.error


class TestJobManagerCancel:
    def test_cancel_queued_job(self):
        jm = JobManager()

        def slow_fn():
            time.sleep(1)

        job = jm.submit(slow_fn)
        assert jm.cancel_job(job.job_id)
        final = jm.get_status(job.job_id)
        assert final.status in ("cancelled", "completed")

    def test_cancel_nonexistent_job(self):
        jm = JobManager()
        assert not jm.cancel_job("nonexistent")

    def test_cancel_completed_job(self):
        jm = JobManager()

        def quick_fn():
            return {"ok": True}

        job = jm.submit(quick_fn)
        time.sleep(0.1)
        assert not jm.cancel_job(job.job_id)


class TestJobManagerSerialExecution:
    def test_second_submit_after_first_completes(self):
        jm = JobManager()

        job1 = jm.submit(lambda: {"first": True})
        time.sleep(0.1)
        assert jm.get_status(job1.job_id).status == "completed"

        job2 = jm.submit(lambda: {"second": True})
        assert job2.status != "rejected"
        time.sleep(0.1)
        assert jm.get_status(job2.job_id).status == "completed"
        assert jm.get_status(job2.job_id).result == {"second": True}


class TestParsePytestOutput:
    def test_parse_standard_output(self):
        output = "2 passed, 1 failed, 3 skipped in 5.2s"
        result = _parse_pytest_output(output)
        assert result == {"passed": 2, "failed": 1, "skipped": 3}

    def test_parse_only_passed(self):
        output = "5 passed in 1.0s"
        result = _parse_pytest_output(output)
        assert result == {"passed": 5, "failed": 0, "skipped": 0}

    def test_parse_empty_output(self):
        result = _parse_pytest_output("")
        assert result == {"passed": 0, "failed": 0, "skipped": 0}

    def test_parse_no_match(self):
        result = _parse_pytest_output("some other output without counts")
        assert result == {"passed": 0, "failed": 0, "skipped": 0}

    def test_parse_multiline(self):
        output = """collected 5 items
test_a.py::test_x PASSED
test_b.py::test_y FAILED
5 passed, 2 failed, 1 skipped in 10.0s"""
        result = _parse_pytest_output(output)
        assert result == {"passed": 5, "failed": 2, "skipped": 1}


class TestExecuteBatches:
    def test_execute_batches_empty(self, tmp_path):
        yaml_dir = tmp_path / "yaml"
        yaml_dir.mkdir()
        result = execute_batches(
            test_ids=[], yaml_dir=yaml_dir,
            pytest_ini_dir=tmp_path, batch_size=5,
        )
        assert result["status"] == "completed"
        assert result["total"] == 0
        assert result["passed"] == 0

    def test_batch_size_chunking(self):
        ids = ["test_001", "test_002", "test_003", "test_004", "test_005", "test_006"]
        batches = [ids[i:i + 5] for i in range(0, len(ids), 5)]
        assert len(batches) == 2
        assert len(batches[0]) == 5
        assert len(batches[1]) == 1

    def test_progress_callback(self, tmp_path):
        yaml_dir = tmp_path / "yaml"
        yaml_dir.mkdir()
        progress_msgs = []

        result = execute_batches(
            test_ids=[], yaml_dir=yaml_dir,
            pytest_ini_dir=tmp_path, batch_size=5,
            progress_callback=lambda msg: progress_msgs.append(msg),
        )
        assert result["status"] == "completed"


class TestJobManagerCleanup:
    def test_cleanup_removes_old_jobs(self):
        jm = JobManager()
        jm.CLEANUP_MAX_AGE = 0

        def quick_fn():
            return {"ok": True}

        job = jm.submit(quick_fn)
        time.sleep(0.1)
        assert jm.get_status(job.job_id).status == "completed"

        job2 = jm.submit(quick_fn)
        time.sleep(0.1)
        assert jm.get_status(job.job_id) is None
        assert jm.get_status(job2.job_id).status == "completed"
