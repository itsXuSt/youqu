# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
# SPDX-License-Identifier: GPL-2.0-only
"""YAML test index management CLI."""

from pathlib import Path


def _find_yaml_dir():
    """Find yaml directory from CWD or common locations."""
    cwd = Path.cwd()
    if (cwd / "yaml").is_dir() and (cwd / "pytest.ini").exists():
        return cwd / "yaml"
    if (cwd / "autotest" / "yaml").is_dir():
        return cwd / "autotest" / "yaml"
    return None


def run(args):
    yaml_dir = _find_yaml_dir()
    if not yaml_dir:
        print("Error: No YAML test directory found. Run from autotest/ or project root.")
        return

    from src.yaml_test.index import YamlIndex

    idx = YamlIndex(yaml_dir)

    if getattr(args, "rebuild", False):
        tests = idx.rebuild()
        print(f"Index rebuilt: {len(tests)} test(s) indexed.")
        stats = idx.get_stats()
        if stats:
            print(f"  Modules: {list(stats.get('modules', {}).keys())}")
            print(f"  Tags: {list(stats.get('tags', {}).keys())}")
        return

    # --list (default when no action specified)
    app = getattr(args, "app", "") or ""
    module = getattr(args, "module", "") or ""
    tag = getattr(args, "tag", "") or ""
    tags_list = [t.strip() for t in tag.split(",") if t.strip()] if tag else None

    tests = idx.query(app=app or None, module=module or None, tags=tags_list)
    if not tests:
        print("No tests found.")
        return

    print(f"Tests: {len(tests)}")
    for t in tests:
        tags_str = ",".join(t.get("tags", []))
        mod_str = t.get("module", "") or "uncategorized"
        feat_str = f" ({t['feature']})" if t.get("feature") else ""
        desc_preview = ""
        if t.get("description"):
            first_line = t["description"].strip().split("\n")[0][:60]
            desc_preview = f" [{first_line}]"
        print(f"  {t['id']:30s} {mod_str}/{feat_str} [{tags_str}]{desc_preview}")

    stats = idx.get_stats()
    if stats:
        print(f"\nModules: {dict(stats.get('modules', {}))}")
        print(f"Tags: {dict(stats.get('tags', {}))}")
