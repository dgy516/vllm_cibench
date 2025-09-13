#!/usr/bin/env python3
"""生成性能 CSV（mock）。

基于 `src/vllm_cibench/testsuites/perf.py` 的 `PerfResult` 与 `gen_mock_csv`，
从命令行参数构造若干行并输出为 CSV 文件，便于离线调试与 CI 演示。
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from vllm_cibench.testsuites.perf import PerfResult, gen_mock_csv


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    返回值:
        argparse.Namespace: 包含并发/输入/输出长度与输出路径。
    副作用:
        读取命令行。
    """

    p = argparse.ArgumentParser(description="Generate mock ACS perf CSV")
    p.add_argument("--concurrency", required=True, help="e.g. 1,2,4")
    p.add_argument("--input-len", type=int, required=True)
    p.add_argument("--output-len", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args()


def main() -> None:
    """入口：写出 CSV 文件。

    副作用:
        写入文件系统。
    """

    ns = parse_args()
    conc = [int(x) for x in str(ns.concurrency).split(",") if x.strip()]
    rows: List[PerfResult] = []
    for c in conc:
        # 构造一些伪数据：随着并发增加，吞吐上升、p50 略上升
        rows.append(
            PerfResult(
                concurrency=c,
                input_len=ns.input_len,
                output_len=ns.output_len,
                latency_p50_ms=max(1.0, 20.0 + 2.0 * (c - 1)),
                throughput_rps=max(0.1, 10.0 * c),
            )
        )
    csv_text = gen_mock_csv(rows)
    ns.out.write_text(csv_text, encoding="utf-8")


if __name__ == "__main__":
    main()

