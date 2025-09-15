#!/usr/bin/env python3
"""指标名重命名工具。

将 CSV 或 JSON 文件中的通用键名映射到 Prometheus 规范名称，便于统一上报。
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List

from vllm_cibench.metrics.rename import DEFAULT_MAPPING


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    p = argparse.ArgumentParser(
        description="Rename metric keys to Prometheus-friendly names"
    )
    p.add_argument("--in", dest="in_path", type=Path, required=True)
    p.add_argument("--out", dest="out_path", type=Path, required=True)
    p.add_argument("--fmt", choices=["csv", "json"], required=True)
    return p.parse_args()


def _rename_dict(d: Dict[str, object]) -> Dict[str, object]:
    """按 DEFAULT_MAPPING 重命名字典键。"""

    out: Dict[str, object] = {}
    for k, v in d.items():
        out[DEFAULT_MAPPING.get(k, k)] = v
    return out


def process_csv(in_path: Path, out_path: Path) -> None:
    """重命名 CSV 表头并写出新文件。"""

    rows: List[Dict[str, object]] = []
    with in_path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(_rename_dict(dict(row)))
    if not rows:
        out_path.write_text("", encoding="utf-8")
        return
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def process_json(in_path: Path, out_path: Path) -> None:
    """重命名 JSON（数组或对象）中的键名。"""

    data = json.loads(in_path.read_text(encoding="utf-8") or "{}")
    if isinstance(data, list):
        data = [_rename_dict(x) for x in data]
    elif isinstance(data, dict):
        data = _rename_dict(data)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    ns = parse_args()
    if ns.fmt == "csv":
        process_csv(ns.in_path, ns.out_path)
    else:
        process_json(ns.in_path, ns.out_path)


if __name__ == "__main__":
    main()
