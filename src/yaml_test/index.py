# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""YAML test case index for querying and statistics."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class YamlIndex:
    """Manages an index of YAML test cases for querying and statistics.

    The index is stored as index.yaml in the same directory as test files,
    containing metadata about all test_*.yaml files (excluding elements.yaml).
    """

    def __init__(self, yaml_dir: Path):
        """Initialize the index manager.

        Args:
            yaml_dir: Directory containing test_*.yaml and elements.yaml files.
        """
        self.yaml_dir = Path(yaml_dir)
        self.index_file = self.yaml_dir / "index.yaml"

    def load(self) -> list[dict]:
        """Load the index.yaml file.

        Auto-rebuilds if the index doesn't exist or is stale.

        Returns:
            List of test case metadata dicts.
        """
        if not self.index_file.exists():
            return self.rebuild()
        raw = yaml.safe_load(self.index_file.read_text(encoding="utf-8")) or {}
        return raw.get("tests", [])

    def rebuild(self) -> list[dict]:
        """Scan test_*.yaml files and rebuild index.yaml.

        Skips elements.yaml as it's not a test file.

        Returns:
            List of test case metadata dicts.
        """
        tests = []

        for yaml_file in sorted(self.yaml_dir.rglob("test_*.yaml")):
            try:
                raw = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
                if not isinstance(raw, dict):
                    continue

                file_id = yaml_file.stem

                test_meta = {
                    "id": file_id,
                    "file": str(yaml_file.relative_to(self.yaml_dir)),
                    "name": raw.get("name", ""),
                    "description": raw.get("description", ""),
                    "module": raw.get("module", ""),
                    "feature": raw.get("feature", ""),
                    "tags": raw.get("tags", []),
                    "app": raw.get("app", ""),
                }
                tests.append(test_meta)
            except yaml.YAMLError:
                continue

        index_data = {
            "version": 1,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "tests": tests,
        }

        self.index_file.write_text(
            yaml.dump(index_data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        return tests

    def query(
        self,
        app: str | None = None,
        module: str | None = None,
        feature: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """Query tests by filters.

        All filters are AND-ed together. Empty/None filters match all.

        Args:
            app: Filter by app name.
            module: Filter by module name.
            feature: Filter by feature name.
            tags: Filter by tags (test must have ALL specified tags).

        Returns:
            List of matching test case metadata dicts.
        """
        tests = self.load()

        if not tests:
            return tests

        result = []
        for test in tests:
            if app and test.get("app") != app:
                continue
            if module and test.get("module") != module:
                continue
            if feature and test.get("feature") != feature:
                continue
            if tags:
                test_tags = test.get("tags", [])
                if not all(t in test_tags for t in tags):
                    continue
            result.append(test)

        return result

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about indexed tests.

        Returns:
            Dict with total count, module counts, and tag counts.
        """
        tests = self.load()

        stats: dict[str, Any] = {
            "total": len(tests),
            "modules": {},
            "tags": {},
        }

        for test in tests:
            module = test.get("module", "")
            if module:
                stats["modules"][module] = stats["modules"].get(module, 0) + 1

            for tag in test.get("tags", []):
                stats["tags"][tag] = stats["tags"].get(tag, 0) + 1

        return stats
