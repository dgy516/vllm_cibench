"""
CLI 占位：打印计划（不执行启动与测试）。
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from .config import (
    load_providers,
    load_matrix,
    select_for_run,
    discover_scenarios,
    load_scenario,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="vLLM CI Bench - Plan Printer")
    parser.add_argument("--run-type", choices=["pr", "daily"], required=True, help="运行类型")
    parser.add_argument("--scenarios-dir", default="configs/scenarios", help="场景目录")
    parser.add_argument("--matrix", default="configs/matrix.yaml", help="矩阵配置文件")
    parser.add_argument(
        "--providers", default="configs/providers.yaml", help="providers.yaml 路径"
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    scenarios_dir = Path(args.scenarios_dir)
    matrix = load_matrix(Path(args.matrix))
    providers = load_providers(Path(args.providers))
    print(f"Loaded providers: {[p.base_url for p in providers]}")

    files: List[Path] = discover_scenarios(scenarios_dir)
    if not files:
        print("No scenarios found.")
        return

    print(f"Run type: {args.run_type}")
    for f in files:
        sc = load_scenario(f)
        sel = select_for_run(matrix, sc.id, args.run_type)
        print(
            f"- Scenario {sc.id} [{sc.mode}/{sc.quant}] -> functional={sel['functional']} perf={sel['perf']} accuracy={sel['accuracy']}"
        )


if __name__ == "__main__":
    main()

