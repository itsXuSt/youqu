#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
Export xlsx or csv test case file to JSON batches for LLM processing.

Usage:
    python3 export_xlsx.py <input.xlsx|csv> <output_dir> [--batch-size 10]
    python3 export_xlsx.py <input.xlsx|csv> <output_dir> --autotest-root autotest [--batch-size 10]

Output:
    <output_dir>/
        batch_001.json  (cases 1-10)
        batch_002.json  (cases 11-20)
        ...
        batch_summary.json  (classification summary)

    If --autotest-root is provided, also copies to:
    <autotest-root>/module_batches/  (permanent reference for LLM context)

JSON batch format:
    [
        {
            "id": "001",
            "batch_index": 0,        # 0-based position in batch
            "title": "播放音乐",
            "module": "播放控制",
            "priority": "L3",
            "precondition": "已有本地音乐",
            "steps": "1.点击播放按钮\n2.等待播放",
            "expected": "音乐开始播放",
            "case_type": "功能测试",
            "source_row": 3          # original xlsx row number
        },
        ...
    ]
"""

import csv
import json
import os
import re
import shutil
import sys
from collections import defaultdict

# Column headers found in PMS-exported xlsx/csv case design docs
# These are the standard PMS export format
CASE_COLUMNS = [
    "用例编号", "所属产品", "所属模块", "相关需求", "用例标题",
    "前置条件", "步骤", "预期", "用例级别", "用例类型",
    "是否自动化", "标签", "备注", "创建人", "更新时间"
]

# Alternative column mappings (flexible matching)
COLUMN_ALIASES = {
    "id": ["用例编号", "ID", "编号", "序号"],
    "title": ["用例标题", "标题", "用例名称", "测试点"],
    "module": ["所属模块", "模块", "功能模块", "测试模块"],
    "priority": ["用例级别", "优先级", "级别", "重要程度"],
    "precondition": ["前置条件", "前提条件", "预置条件"],
    "steps": ["步骤", "测试步骤", "操作步骤", "用例步骤"],
    "expected": ["预期", "预期结果", "期望结果", "预期输出"],
    "case_type": ["用例类型", "类型", "测试类型"],
    "product": ["所属产品", "产品"],
    "requirement": ["相关需求", "需求"],
}


def read_xlsx(filepath):
    """Read xlsx file, return list of dict rows."""
    try:
        from openpyxl import load_workbook
    except ImportError:
        print("Error: openpyxl not installed. Install with: pip install openpyxl")
        sys.exit(1)

    wb = load_workbook(filepath, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [str(h).strip() if h else "" for h in rows[0]]
    data = []
    for row_idx, row in enumerate(rows[1:], start=2):
        record = {"source_row": row_idx}
        for col_idx, value in enumerate(row):
            if col_idx < len(headers) and headers[col_idx]:
                record[headers[col_idx]] = str(value).strip() if value is not None else ""
        data.append(record)
    return data


def read_csv(filepath):
    """Read csv file, return list of dict rows."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        data = []
        for row_idx, row in enumerate(reader, start=2):
            record = {"source_row": row_idx}
            record.update({k.strip(): v.strip() if v else "" for k, v in row.items() if k})
            data.append(record)
        return data


def find_column(record, aliases):
    """Find best matching column value from record using aliases."""
    for alias in aliases:
        if alias in record:
            val = record[alias]
            if val:
                return val
    # fuzzy match
    for key in record:
        if any(a.lower() in key.lower() for a in aliases):
            return record[key]
    return ""


def normalize_record(record, batch_index):
    """Convert a raw row dict into a normalized case dict."""
    return {
        "id": str(batch_index).zfill(3),
        "batch_index": batch_index,
        "title": find_column(record, COLUMN_ALIASES["title"]),
        "module": find_column(record, COLUMN_ALIASES["module"]),
        "priority": find_column(record, COLUMN_ALIASES["priority"]),
        "precondition": find_column(record, COLUMN_ALIASES["precondition"]),
        "steps": find_column(record, COLUMN_ALIASES["steps"]),
        "expected": find_column(record, COLUMN_ALIASES["expected"]),
        "case_type": find_column(record, COLUMN_ALIASES["case_type"]),
        "source_row": record.get("source_row", 0),
    }


def classify_skip(case):
    """Classify a case as automatable or non-automatable with skip reason.

    Returns: (is_skipable: bool, skip_reason: str, category: str)
    """
    text = f"{case['title']} {case['steps']} {case['expected']} {case['case_type']} {case['precondition']}"

    # Priority ordered checks (highest priority first)
    checks = [
        (lambda t: "玲珑" in t or "linglong" in t.lower(), "skip-玲珑环境不支持自动化", "LINGLONG"),
        (lambda t: any(k in t for k in ["性能", "压测", "压力测试", "performance", "benchmark", "负载"]),
         "skip-性能压测类不支持自动化", "PERF"),
        (lambda t: any(k in t for k in ["触摸", "touch", "手势", "gesture", "pinch", "swipe",
                                        "多点触控", "手势缩放", "双指缩放", "长按拖动"]),
         "skip-触摸操作无法自动化", "GESTURE"),
        (lambda t: any(k in t for k in ["重启", "reboot", "重启后", "重启系统", "注销"]),
         "skip-重启类场景需要letmego支持", "REBOOT"),
        (lambda t: any(k in t for k in ["需要U盘", "插入USB", "需要打印机", "需要蓝牙设备",
                                        "需要耳机", "需要外接显示器", "需要特定硬件"]),
         "skip-依赖特定硬件环境", "HARDWARE"),
        (lambda t: any(k in t for k in ["调用外部应用", "打开第三方", "外部程序"]),
         "skip-外部应用交互无法验证", "EXTERNAL"),
        (lambda t: any(k in t for k in ["人工确认", "肉眼观察", "主观判断", "听感", "感官", "音质"]),
         "skip-需要人工主观判断", "MANUAL"),
    ]

    for check_fn, reason, category in checks:
        if check_fn(text):
            return True, reason, category

    return False, "", "AUTOMATABLE"


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    batch_size = 10
    autotest_root = None

    for i, arg in enumerate(sys.argv):
        if arg == "--batch-size" and i + 1 < len(sys.argv):
            batch_size = int(sys.argv[i + 1])
        elif arg == "--autotest-root" and i + 1 < len(sys.argv):
            autotest_root = sys.argv[i + 1]

    if not os.path.exists(input_path):
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # Read
    ext = os.path.splitext(input_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        raw_data = read_xlsx(input_path)
    elif ext == ".csv":
        raw_data = read_csv(input_path)
    else:
        print(f"Error: unsupported format: {ext}. Use .xlsx or .csv")
        sys.exit(1)

    if not raw_data:
        print("Error: no data rows found")
        sys.exit(1)

    # Normalize
    cases = [normalize_record(row, idx) for idx, row in enumerate(raw_data)]

    # Classify
    classification = defaultdict(list)
    for case in cases:
        is_skip, reason, cat = classify_skip(case)
        case["_is_skip"] = is_skip
        case["_skip_reason"] = reason
        case["_category"] = cat
        classification[cat].append(case["id"])

    # Separate automatable
    automatable = [c for c in cases if not c["_is_skip"]]
    skipped = [c for c in cases if c["_is_skip"]]

    print(f"Total cases: {len(cases)}")
    print(f"Automatable: {len(automatable)}")
    print(f"Skip: {len(skipped)}")
    for cat, ids in sorted(classification.items()):
        if cat != "AUTOMATABLE":
            print(f"  [{cat}] {len(ids)} cases: {', '.join(ids[:5])}{'...' if len(ids) > 5 else ''}")

    # Batch automatable cases
    batches = [automatable[i:i + batch_size] for i in range(0, len(automatable), batch_size)]

    for batch_idx, batch in enumerate(batches):
        filename = os.path.join(output_dir, f"batch_{batch_idx + 1:03d}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)
        print(f"  Wrote {filename} ({len(batch)} cases)")

    # Write skipped cases
    if skipped:
        filename = os.path.join(output_dir, "batch_skip.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(skipped, f, ensure_ascii=False, indent=2)
        print(f"  Wrote {filename} ({len(skipped)} cases)")

    # Write summary
    summary = {
        "total": len(cases),
        "automatable": len(automatable),
        "skipped": len(skipped),
        "batches": len(batches),
        "batch_size": batch_size,
        "classification": {cat: len(ids) for cat, ids in classification.items()},
        "skipped_ids": [c["id"] for c in skipped],
    }
    filename = os.path.join(output_dir, "batch_summary.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {filename}")

    # Copy to autotest/module_batches/ for permanent reference
    if autotest_root:
        module_batches_dir = os.path.join(autotest_root, "module_batches")
        os.makedirs(module_batches_dir, exist_ok=True)
        for fname in os.listdir(output_dir):
            src = os.path.join(output_dir, fname)
            dst = os.path.join(module_batches_dir, fname)
            shutil.copy2(src, dst)
        print(f"  Copied to {module_batches_dir}/")


if __name__ == "__main__":
    main()
