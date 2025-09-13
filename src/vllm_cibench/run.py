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

from .config import ScenarioRegistry, load_matrix, resolve_plan
from .orchestrators import run_matrix as run_matrix_mod
from .orchestrators import run_pipeline

app = typer.Typer(help="vLLM CI Bench / 计划与编排 CLI")


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    scenario: Optional[str] = typer.Option(
        None, "--scenario", help="场景 ID（默认执行 plan）"
    ),
    run_type: str = typer.Option("pr", "--run-type", help="运行类型: pr/daily"),
    root: Optional[str] = typer.Option(
        None, "--root", help="项目根目录（默认当前工作目录）"
    ),
) -> None:
    """根命令：若未指定子命令，则回退为 `plan`。"""

    if ctx.invoked_subcommand is None:
        if scenario is None:
            raise typer.BadParameter("未提供 --scenario，或明确使用子命令 plan/run")
        plan(scenario=scenario, run_type=run_type, root=root)


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
    registry = ScenarioRegistry.from_dir(scenarios_dir)
    try:
        registry.get(scenario)
    except KeyError:
        raise typer.BadParameter(
            f"未知场景: {scenario}. 可选: {sorted(registry.mapping.keys())}"
        )

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


@app.command()
def run(
    scenario: str = typer.Option(..., "--scenario", help="场景 ID"),
    run_type: str = typer.Option("pr", "--run-type", help="运行类型: pr/daily"),
    root: Optional[str] = typer.Option(
        None, "--root", help="项目根目录（默认当前工作目录）"
    ),
    timeout: float = typer.Option(60.0, "--timeout", help="探活最大等待时长（秒）"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅运行不推送指标"),
) -> None:
    """执行集成编排：探活→功能→性能→（daily）指标推送。

    参数:
        scenario: 场景 id。
        run_type: 运行类型（pr/daily）。
        root: 项目根目录，便于在测试中传入固定路径；缺省为 CWD。
        timeout: 探活最大等待时长（秒）。
        dry_run: 若为 True，即使 daily 也不会推送指标。

    返回值:
        无返回；以 JSON 打印编排结果到标准输出。

    副作用:
        读取配置与进行网络探活（在 CI 中可通过 monkeypatch 避免）。
    """

    res = run_pipeline.execute(
        scenario_id=scenario,
        run_type=run_type,
        root=root,
        timeout_s=timeout,
        dry_run=dry_run,
    )
    typer.echo(json.dumps(res, ensure_ascii=False))


@app.command("run-matrix")
def run_matrix(
    run_type: str = typer.Option("pr", "--run-type", help="运行类型: pr/daily"),
    root: Optional[str] = typer.Option(
        None, "--root", help="项目根目录（默认当前工作目录）"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅运行不推送指标"),
    timeout: float = typer.Option(60.0, "--timeout", help="探活最大等待时长（秒）"),
) -> None:
    """批量执行 matrix.yaml 中的所有场景。

    参数:
        run_type: 运行类型（pr/daily）。
        root: 仓库根目录，缺省为 CWD。
        dry_run: 若为 True，则跳过指标推送。

    返回值:
        无；结果以 JSON 打印到标准输出。

    副作用:
        读取配置并调用 `run_pipeline.execute`，可能触发网络探活。
    """

    res = run_matrix_mod.execute_matrix(
        run_type=run_type, root=root, dry_run=dry_run, timeout_s=timeout
    )
    typer.echo(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
