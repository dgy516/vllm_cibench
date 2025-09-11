"""命令行入口（规划/Plan）。

提供最小的 `plan` 子命令：
- 加载 `configs/matrix.yaml` 与 `configs/scenarios/`，
- 校验场景是否存在，
- 输出该场景在 `pr/daily` 下的测试计划。

示例:
    python -m vllm_cibench.run plan --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from .config import list_scenarios, load_matrix, resolve_plan

app = typer.Typer(help="vLLM CI Bench / 计划与编排 CLI")


@app.command()
def plan(
    scenario: str = typer.Option(..., "--scenario", help="场景 ID"),
    run_type: str = typer.Option("pr", "--run-type", help="运行类型: pr/daily"),
    root: Optional[str] = typer.Option(
        None, "--root", help="项目根目录（默认当前工作目录）"
    ),
) -> None:
    """解析并打印某场景在指定运行类型下的测试计划。

    参数:
        scenario: 场景 id。
        run_type: 运行类型（pr/daily）。
        root: 项目根目录，便于在测试中传入固定路径；缺省为 CWD。

    返回值:
        无返回；以 JSON 打印计划到标准输出。

    副作用:
        读取文件系统中的配置文件。
    """

    base = Path(root) if root else Path.cwd()
    matrix_path = base / "configs" / "matrix.yaml"
    scenarios_dir = base / "configs" / "scenarios"

    matrix = load_matrix(matrix_path)
    scenarios = list_scenarios(scenarios_dir)

    known_ids = {s.id for s in scenarios}
    if scenario not in known_ids:
        raise typer.BadParameter(f"未知场景: {scenario}. 可选: {sorted(known_ids)}")

    plan_obj = resolve_plan(matrix, scenario, run_type)
    typer.echo(
        json.dumps(
            {"scenario": scenario, "run_type": run_type, "plan": plan_obj},
            ensure_ascii=False,
        )
    )


def main() -> None:
    """CLI 入口包装。

    参数:
        无。

    返回值:
        无。

    副作用:
        调用 Typer 应用进行命令行解析与执行。
    """

    app()


if __name__ == "__main__":
    main()
