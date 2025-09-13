# isort: skip_file
"""一体化编排：按场景执行启动→功能→性能→（可选）指标推送。

最小化实现：不负责实际“启动服务”，而是基于场景进行资源发现与探活，
然后运行基础功能与性能流水线，并在 daily 任务时推送汇总指标到 Pushgateway。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from vllm_cibench.config import Scenario, list_scenarios, load_matrix, resolve_plan
from vllm_cibench.deploy.k8s import hybrid as k8s_hybrid
from vllm_cibench.deploy.k8s import pd as k8s_pd
from vllm_cibench.deploy.local import scenario_base_url, wait_service_ready
from vllm_cibench.metrics.pushgateway import metrics_from_perf_records, push_metrics
from vllm_cibench.metrics.rename import DEFAULT_MAPPING, rename_record_keys
from vllm_cibench.testsuites.functional import run_smoke_suite
from vllm_cibench.testsuites.perf import PerfResult, gen_mock_csv, parse_perf_csv
from vllm_cibench.testsuites.accuracy import run_accuracy


def _load_accuracy_cfg(base: Path, scenario: Scenario) -> Dict[str, Any]:
    """加载 accuracy 配置：优先使用场景内配置，否则读取全局配置文件。

    参数:
        base: 仓库根目录。
        scenario: 场景对象。

    返回值:
        dict: accuracy 配置字典（可能为空）。

    副作用:
        文件读取。
    """

    cfg = scenario.raw.get("accuracy", {}) or {}
    if cfg:
        return dict(cfg)
    path = base / "configs" / "tests" / "accuracy.yaml"
    if path.exists():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                return dict(data)
        except Exception:
            return {}
    return {}


def _find_scenario(root: Path, scenario_id: str) -> Scenario:
    """在场景目录中查找指定 id 的场景对象。

    参数:
        root: 仓库根目录。
        scenario_id: 场景 ID。

    返回值:
        Scenario: 匹配的场景对象。

    副作用:
        读取文件系统。
    """

    scenarios_dir = root / "configs" / "scenarios"
    for s in list_scenarios(scenarios_dir):
        if s.id == scenario_id:
            return s
    raise KeyError(f"scenario not found: {scenario_id}")


def _discover_and_wait(
    root: Path, s: Scenario, timeout_s: Optional[float] = None
) -> str:
    """根据场景模式发现 base_url 并等待就绪，返回 base_url。

    参数:
        root: 仓库根目录（当前未使用，预留）。
        s: 场景对象。
        timeout_s: 探活最大等待时长（秒），缺省读取场景
            `startup_timeout_seconds`，未配置则为 60。

    返回值:
        str: 服务基础 URL。

    副作用:
        调用 K8s API 或本地 HTTP 探活。
    """

    mode = s.mode
    timeout = timeout_s or float(s.raw.get("startup_timeout_seconds", 60))
    if mode == "local":
        base_url = scenario_base_url(s)
        # 注意：当外部传入较小的 timeout（例如 0.5）时，int(0.5) 会变为 0，
        # 若直接传入 0 将被 wait_service_ready 视为未提供并回退到场景配置（例如 1200 秒）。
        # 因此这里对 timeout 做下限保护，至少为 1 秒，避免 smoke 测试卡住。
        safe_timeout = int(timeout) if timeout >= 1 else 1
        wait_service_ready(s, timeout_seconds=safe_timeout)
        return base_url
    if mode == "k8s-hybrid":
        base_url = k8s_hybrid.discover_base_url(s)
        k8s_hybrid.wait_ready(s, timeout_s=timeout)
        return base_url
    if mode == "k8s-pd":
        base_url = k8s_pd.discover_base_url(s)
        k8s_pd.wait_ready(s, timeout_s=timeout)
        return base_url
    raise ValueError(f"unsupported scenario mode: {mode}")


def execute(
    scenario_id: str,
    run_type: str = "pr",
    *,
    root: Optional[str] = None,
    timeout_s: Optional[float] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """执行编排：探活→功能→性能→（daily）指标推送。

    参数:
        scenario_id: 场景 ID。
        run_type: 运行类型，`pr` 或 `daily`。
        root: 仓库根路径（便于测试传入），默认使用 CWD。
        timeout_s: 探活最大等待时长（秒），默认读取场景配置。
        dry_run: 若为 True，即使在 daily 运行也不会推送指标。

    返回值:
        dict: 汇总结果，包括 `base_url`、`functional` 状态、`perf_metrics` 与 `pushed` 标记等。

    副作用:
        读取文件系统、可能进行网络探活（已在测试中通过 monkeypatch 避免）。
    """

    base = Path(root) if root else Path.cwd()
    matrix = load_matrix(base / "configs" / "matrix.yaml")
    scenario = _find_scenario(base, scenario_id)

    plan = resolve_plan(matrix, scenario_id, run_type)
    result: Dict[str, Any] = {
        "scenario": scenario_id,
        "run_type": run_type,
        "functional": "skipped",
        "perf_metrics": {},
        "pushed": False,
    }

    base_url = _discover_and_wait(base, scenario, timeout_s=timeout_s)
    result["base_url"] = base_url

    # Functional
    if plan.get("functional"):
        try:
            resp = run_smoke_suite(base_url=base_url, model=scenario.served_model_name)
            ok = bool(resp.get("choices"))
            result["functional"] = "ok" if ok else "failed"
        except Exception:
            result["functional"] = "failed"

    # Perf (mock-based)
    if plan.get("perf"):
        # 生成少量 mock 数据 -> 解析 -> 重命名 -> 聚合
        csv_text = gen_mock_csv(
            [
                PerfResult(1, 128, 128, 50.0, 10.0),
                PerfResult(2, 128, 128, 60.0, 20.0),
            ]
        )
        parsed = parse_perf_csv(csv_text)
        renamed = [rename_record_keys(r, DEFAULT_MAPPING) for r in parsed]
        agg = metrics_from_perf_records(parsed)
        result["perf_metrics"] = {**agg, "records": renamed}

        # Push (daily only)
        labels = {
            "model": scenario.model,
            "quant": scenario.quant,
            "scenario": scenario.id,
        }
        if not dry_run:
            pushed = push_metrics(
                "vllm_cibench",
                agg,
                labels=labels,
                run_type=run_type,
                dry_run=dry_run,
            )
            result["pushed"] = bool(pushed)

    # Accuracy
    if plan.get("accuracy"):
        acc_cfg = _load_accuracy_cfg(base, scenario)
        try:
            acc = run_accuracy(
                base_url=base_url,
                model=scenario.served_model_name,
                cfg=acc_cfg,
            )
            result["accuracy"] = acc
        except Exception as exc:
            result["accuracy"] = {"error": str(exc)}

    return result
