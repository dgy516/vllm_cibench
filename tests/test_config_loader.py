from pathlib import Path
import tempfile
import textwrap

import pytest

from vllm_cibench.config import (
    load_providers,
    load_scenario,
    load_perf_profile,
    load_accuracy_profile,
    load_matrix,
    select_for_run,
    discover_scenarios,
)


def test_load_providers_from_repo_samples():
    providers = load_providers(Path("configs/providers.yaml"))
    assert providers, "providers should not be empty"
    p = providers[0]
    assert p.base_url.endswith("/v1")
    assert p.model_name


def test_load_scenario_and_validate_quant_ok():
    # pick one sample scenario file
    scenarios = list(Path("configs/scenarios").glob("*.yaml"))
    assert scenarios, "expect sample scenarios in repo"
    sc = load_scenario(scenarios[0])
    assert sc.quant in {"w8a8", "w4a8", "none"}


def test_load_scenario_invalid_quant_raises():
    content = textwrap.dedent(
        """
        id: sc-invalid
        mode: local
        model: Q
        served_model_name: q
        quant: w3a8
        base_url: http://127.0.0.1:9000/v1
        """
    ).strip()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "invalid.yaml"
        p.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError):
            load_scenario(p)


def test_perf_accuracy_profiles():
    pr_profile = load_perf_profile(Path("configs/tests/perf/profiles/pr.yaml"))
    daily_profile = load_perf_profile(Path("configs/tests/perf/profiles/daily.yaml"))
    assert pr_profile.profile == "pr"
    assert daily_profile.profile == "daily"
    a_pr = load_accuracy_profile(Path("configs/tests/accuracy/pr.yaml"))
    a_daily = load_accuracy_profile(Path("configs/tests/accuracy/daily.yaml"))
    assert a_pr.run_type == "pr" and a_pr.debug is True
    assert a_daily.run_type == "daily" and a_daily.debug is False


def test_matrix_selection_defaults_and_defined():
    matrix = load_matrix(Path("configs/matrix.yaml"))
    # existing scenario id
    some_id = next(iter(matrix.keys()))
    sel = select_for_run(matrix, some_id, "pr")
    assert sel["perf"] and sel["accuracy"]
    # unknown scenario should fallback to defaults
    sel2 = select_for_run(matrix, "unknown_scn", "daily")
    assert sel2 == {"functional": "all", "perf": True, "accuracy": True}


def test_discover_scenarios_sorting():
    paths = discover_scenarios(Path("configs/scenarios"))
    assert paths == sorted(paths)

