# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Web spec index for list/query/statistics."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class WebSpecIndex:
    """Manage index.yaml for Web spec files."""

    def __init__(self, spec_dir: Path):
        self.spec_dir = Path(spec_dir)
        self.index_file = self.spec_dir / "index.yaml"

    def load(self) -> list[dict[str, Any]]:
        if not self.index_file.exists():
            return self.rebuild()
        raw = yaml.safe_load(self.index_file.read_text(encoding="utf-8")) or {}
        return raw.get("specs", [])

    def rebuild(self) -> list[dict[str, Any]]:
        specs = []
        for spec_file in sorted(self.spec_dir.rglob("*.y*ml")):
            if spec_file.name == "index.yaml":
                continue
            try:
                raw = yaml.safe_load(spec_file.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
            if not isinstance(raw, dict):
                continue
            spec_id = str(raw.get("id") or spec_file.stem)
            specs.append({
                "id": spec_id,
                "file": str(spec_file.relative_to(self.spec_dir)),
                "name": raw.get("title") or raw.get("name") or "",
                "description": raw.get("description", ""),
                "module": raw.get("module", ""),
                "feature": raw.get("feature", ""),
                "tags": raw.get("tags", []),
                "priority": raw.get("priority", ""),
            })

        data = {
            "version": 1,
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
