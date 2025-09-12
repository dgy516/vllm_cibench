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
    monkeypatch.setenv("GITHUB_REPOSITORY", "dgy516/vllm_cibench")
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


def test_dry_run_skips_push(monkeypatch: pytest.MonkeyPatch):
    called = {}

    def fake_push(*a, **kw):
        called["flag"] = True

    monkeypatch.setattr(pg, "push_to_gateway", fake_push)
    monkeypatch.setenv("GITHUB_REPOSITORY", "dgy516/vllm_cibench")
    ok = pg.push_metrics(
        job="ci",
        metrics={"ci_perf_throughput_rps_avg": 1.0},
        labels={},
        run_type="daily",
        gateway_url="http://pushgw:9091",
        dry_run=True,
    )
    assert ok is False
    assert "flag" not in called


def test_skip_on_fork(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "someone/fork")
    ok = pg.push_metrics(
        job="ci",
        metrics={"ci_perf_throughput_rps_avg": 1.0},
        labels={"model": "dummy"},
        run_type="daily",
        gateway_url="http://pushgw:9091",
    )
    assert ok is False


def test_metrics_from_perf_records():
    out = pg.metrics_from_perf_records(
        [
            {"throughput_rps": 10, "latency_p50_ms": 40},
            {"throughput_rps": 20, "latency_p50_ms": 60},
        ]
    )
    assert out["ci_perf_throughput_rps_avg"] == 15
    assert out["ci_perf_latency_p50_ms_avg"] == 50
