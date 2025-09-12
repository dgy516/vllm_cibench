"""Pushgateway 指标发布测试（mock）。"""

from __future__ import annotations

import pytest

import vllm_cibench.metrics.pushgateway as pg


def test_skip_on_pr_run_type(monkeypatch: pytest.MonkeyPatch):
    ok = pg.push_metrics(
        job="ci",
        metrics={"ci_perf_throughput_rps_avg": 1.0},
        labels={"model": "dummy"},
        run_type="pr",
        gateway_url="http://localhost:9091",
    )
    assert ok is False


def test_skip_when_no_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PROM_PUSHGATEWAY_URL", raising=False)
    ok = pg.push_metrics(
        job="ci",
        metrics={"ci_perf_throughput_rps_avg": 1.0},
        labels={"model": "dummy"},
        run_type="daily",
    )
    assert ok is False


def test_push_success(monkeypatch: pytest.MonkeyPatch):
    called = {}

    def fake_push(url: str, job: str, registry, grouping_key):
        called["url"] = url
        called["job"] = job
        called["grouping_key"] = grouping_key

    monkeypatch.setattr(pg, "push_to_gateway", fake_push)
    ok = pg.push_metrics(
        job="ci",
        metrics={
            "ci_perf_throughput_rps_avg": 12.3,
            "ci_perf_latency_p50_ms_avg": 50.5,
        },
        labels={"model": "m", "quant": "w8a8", "scenario": "s"},
        run_type="daily",
        gateway_url="http://pushgw:9091",
    )
    assert ok is True
    assert called["url"].startswith("http://pushgw")
    assert called["job"] == "ci"
    assert called["grouping_key"]["model"] == "m"


def test_push_metrics_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """dry_run=True 时应跳过 push_to_gateway。"""

    called = {"flag": False}

    def fake_push(url: str, job: str, registry, grouping_key):  # pragma: no cover
        called["flag"] = True

    monkeypatch.setattr(pg, "push_to_gateway", fake_push)
    ok = pg.push_metrics(
        job="ci",
        metrics={"ci_perf_throughput_rps_avg": 1.0},
        labels={"model": "m"},
        run_type="daily",
        gateway_url="http://pushgw:9091",
        dry_run=True,
    )
    assert ok is False and called["flag"] is False


def test_metrics_from_perf_records():
    out = pg.metrics_from_perf_records(
        [
            {"throughput_rps": 10, "latency_p50_ms": 40},
            {"throughput_rps": 20, "latency_p50_ms": 60},
        ]
    )
    assert out["ci_perf_throughput_rps_avg"] == 15
    assert out["ci_perf_latency_p50_ms_avg"] == 50
