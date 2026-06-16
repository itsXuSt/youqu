# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Web spec index for list/query/statistics."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from web_spec.kind import is_config_file, is_legacy_suite_file, is_suite_file
from web_spec.loader import SpecValidationError, load_spec
from web_spec.suite import load_suite


INDEX_VERSION = 7


class WebSpecIndex:
    """Manage index.yaml for Web spec files."""

    def __init__(self, spec_dir: Path):
        self.spec_dir = Path(spec_dir)
        self.index_file = self.spec_dir / "index.yaml"

    def load(self) -> list[dict[str, Any]]:
        if not self.index_file.exists():
            return self.rebuild()
        raw = yaml.safe_load(self.index_file.read_text(encoding="utf-8")) or {}
        if raw.get("version") != INDEX_VERSION:
            return self.rebuild()
        return raw.get("specs", [])

    def rebuild(self) -> list[dict[str, Any]]:
        specs = []
        for spec_file in sorted(self.spec_dir.rglob("*.y*ml")):
            if spec_file.name == "index.yaml" or is_config_file(spec_file) or is_legacy_suite_file(spec_file):
                continue
            if is_suite_file(spec_file):
                try:
                    suite = load_suite(spec_file)
                except (FileNotFoundError, SpecValidationError):
                    continue
                specs.append({
                    "id": suite.id,
                    "file": str(spec_file.relative_to(self.spec_dir)),
                    "name": suite.name,
                    "description": "",
                    "module": suite.module,
                    "feature": "",
                    "tags": suite.tags,
                    "priority": "1",
                    "kind": "suite",
                    "spec_count": len(suite.source_specs),
                    "specs": [
                        {
                            "id": spec.id,
                            "file": _relative_source(spec.source, self.spec_dir) if spec.source else "",
                            "name": spec.title,
                            "module": spec.module,
                            "feature": spec.feature,
                            "tags": spec.tags,
                        }
                        for spec in suite.source_specs
                    ],
                    "source_files": [
                        _relative_source(spec.source, self.spec_dir)
                        for spec in suite.source_specs
                        if spec.source
                    ],
                    "single_case": suite.single_case,
                })
                continue
            try:
                spec = load_spec(spec_file)
            except (FileNotFoundError, SpecValidationError):
                continue
            specs.append({
                "id": spec.id,
                "file": str(spec_file.relative_to(self.spec_dir)),
                "name": spec.title,
                "description": spec.description,
                "module": spec.module,
                "feature": spec.feature,
                "tags": spec.tags,
                "priority": spec.priority,
                "kind": "case",
            })

        data = {
            "version": INDEX_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "specs": specs,
        }
        self.index_file.write_text(
            yaml.dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return specs

    def query(
        self,
        module: str | None = None,
        feature: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        specs = self.load()
        result = []
        for spec in specs:
            if module and spec.get("module") != module:
                continue
            if feature and spec.get("feature") != feature:
                continue
            if tags:
                spec_tags = spec.get("tags", []) or []
                if not all(tag in spec_tags for tag in tags):
                    continue
            result.append(spec)
        return result

    def get_stats(self) -> dict[str, Any]:
        specs = self.load()
        stats: dict[str, Any] = {"total": len(specs), "modules": {}, "tags": {}}
        for spec in specs:
            module = spec.get("module", "")
            if module:
                stats["modules"][module] = stats["modules"].get(module, 0) + 1
            for tag in spec.get("tags", []) or []:
                stats["tags"][tag] = stats["tags"].get(tag, 0) + 1
        return stats


def _relative_source(source: str, root: Path) -> str:
    return str(Path(source).resolve().relative_to(root.resolve()))
