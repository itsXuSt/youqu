# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
# SPDX-License-Identifier: GPL-2.0-only
"""Async job management for YAML test batch execution.

Ported from deepin-mcp orchestration/jobs.py, adapted for YouQu pytest-based execution.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class JobStatus:
    """Status of an async test job."""

    job_id: str
    status: str  # queued | running | completed | failed | cancelled | rejected
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    progress: str | None = None
    result: dict | None = None
    error: str | None = None
    running_job_id: str | None = None
    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _done_event: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_event.is_set()

    @property
    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed", "cancelled", "rejected")


class JobManager:
    """Manages async test execution jobs."""

    MAX_CONCURRENT = 1
    CLEANUP_MAX_AGE = 3600

    def __init__(self) -> None:
        self._jobs: dict[str, JobStatus] = {}
        self._lock = threading.Lock()
        self._running_job_id: str | None = None

    def submit(
        self,
        fn: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> JobStatus:
        with self._lock:
            self._cleanup_unlocked()
            if self._running_job_id is not None:
                running = self._jobs.get(self._running_job_id)
                return JobStatus(
                    job_id="",
                    status="rejected",
                    error="Another job is already running",
                    running_job_id=self._running_job_id,
                )
            job_id = uuid.uuid4().hex[:8]
            job = JobStatus(job_id=job_id, status="queued")
            self._jobs[job_id] = job
            self._running_job_id = job_id

        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, fn, args, kwargs),
            daemon=True,
            name=f"job-{job_id}",
        )
        thread.start()
        return job

    def get_status(self, job_id: str) -> JobStatus | None:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status not in ("queued", "running"):
                return False
            job._cancel_event.set()
            job.status = "cancelled"
            job.completed_at = time.time()
            if self._running_job_id == job_id:
                self._running_job_id = None
        job._done_event.set()
        return True

    def _run_job(self, job_id: str, fn: Callable, args: tuple, kwargs: dict) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status == "cancelled":
                if self._running_job_id == job_id:
                    self._running_job_id = None
                return
            job.status = "running"
            job.started_at = time.time()

        try:
            result = fn(*args, **kwargs)
            with self._lock:
                job.status = "completed"
                job.completed_at = time.time()
                job.result = self._format_result(result)
        except Exception as exc:
            logger.exception("Job %s failed", job_id)
            with self._lock:
                job.status = "failed"
                job.completed_at = time.time()
                job.error = str(exc)
                job.result = {"error": str(exc)}
        finally:
            with self._lock:
                if self._running_job_id == job_id:
                    self._running_job_id = None
            job._done_event.set()

    def _format_result(self, result: Any) -> dict:
        if result is None:
            return {"success": True}
        if isinstance(result, dict):
            return result
        return {"value": str(result)}

    def _cleanup_unlocked(self) -> None:
        now = time.time()
        stale = [
            jid
            for jid, j in self._jobs.items()
            if j.status in ("completed", "failed", "cancelled", "rejected")
            and j.completed_at
            and (now - j.completed_at) > self.CLEANUP_MAX_AGE
        ]
        for jid in stale:
            del self._jobs[jid]

    def update_progress(self, job_id: str, msg: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == "running":
                job.progress = msg


def execute_batches(
    test_ids: list[str],
    yaml_dir: str | Path,
    pytest_ini_dir: str | Path,
    batch_size: int = 5,
    progress_callback: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> dict:
    """Execute YAML test cases in batches via pytest subprocess.

    Args:
        test_ids: List of test IDs (e.g. ['test_play_001', 'test_play_002'])
        yaml_dir: Directory containing YAML test files
        pytest_ini_dir: Directory containing pytest.ini (autotest root)
        batch_size: Max test cases per batch (default 5)
        progress_callback: Called with progress messages
        cancel_event: Set to cancel between batches

    Returns:
        dict with keys: passed, failed, skipped, total, batches[...]
    """
    yaml_dir = Path(yaml_dir)
    pytest_ini_dir = Path(pytest_ini_dir)
    batches = [test_ids[i:i + batch_size] for i in range(0, len(test_ids), batch_size)]
    results: list[dict] = []
    total_passed = 0
    total_failed = 0
    total_skipped = 0

    for idx, batch in enumerate(batches):
        if cancel_event and cancel_event.is_set():
            return {
                "status": "cancelled",
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "total": len(test_ids),
                "completed_batches": idx,
                "total_batches": len(batches),
                "batches": results,
            }

        progress_msg = f"batch {idx+1}/{len(batches)}: running {batch[0]}..{batch[-1]}"
        if progress_callback:
            progress_callback(progress_msg)

        file_paths = [str(yaml_dir / f"{tid}.yaml") for tid in batch]
        cmd = [
            sys.executable, "-m", "pytest",
            "-c", str(pytest_ini_dir / "pytest.ini"),
            "--rootdir", str(pytest_ini_dir),
            "-q", "--tb=short",
            "--alluredir", str(pytest_ini_dir / "report" / f"batch_{idx+1}"),
        ] + file_paths

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            batch_result = _parse_pytest_output(proc.stdout)
        except subprocess.TimeoutExpired:
            batch_result = {"passed": 0, "failed": len(batch), "skipped": 0, "error": "timeout"}

        total_passed += batch_result.get("passed", 0)
        total_failed += batch_result.get("failed", 0)
        total_skipped += batch_result.get("skipped", 0)
        batch_result["batch"] = idx + 1
        results.append(batch_result)

        progress_done = (
            f"batch {idx+1}/{len(batches)} done: "
            f"{batch_result.get('passed',0)}p/{batch_result.get('failed',0)}f/"
            f"{batch_result.get('skipped',0)}s"
        )
        if progress_callback:
            progress_callback(progress_done)

    return {
        "status": "completed",
        "passed": total_passed,
        "failed": total_failed,
        "skipped": total_skipped,
        "total": len(test_ids),
        "completed_batches": len(batches),
        "total_batches": len(batches),
        "batches": results,
    }


def _parse_pytest_output(output: str) -> dict:
    """Parse pytest stdout for pass/fail/skip counts."""
    passed = 0
    failed = 0
    skipped = 0
    for line in output.splitlines():
        line = line.strip()
        import re
        # Primary pattern: "X passed, Y failed, Z skipped"
        m = re.search(r"(\d+)\s+passed", line)
        if m:
            passed = int(m.group(1))
            m2 = re.search(r"(\d+)\s+failed", line)
            if m2:
                failed = int(m2.group(1))
            m3 = re.search(r"(\d+)\s+skipped", line)
            if m3:
                skipped = int(m3.group(1))
    return {"passed": passed, "failed": failed, "skipped": skipped}
