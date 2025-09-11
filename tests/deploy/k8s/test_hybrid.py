"""K8s Hybrid 适配层测试。"""

from __future__ import annotations

from vllm_cibench.config import Scenario
from vllm_cibench.deploy.k8s import hybrid


def _make_scenario() -> Scenario:
    raw = {
        "id": "k8s_hybrid_qwen3-32b_tp2_w4a8",
        "mode": "k8s-hybrid",
        "model": "Qwen3-32B",
        "served_model_name": "qwen3-32b",
        "quant": "w4a8",
        "k8s": {
            "namespace": "default",
            "service_name": "infer-vllm",
            "port_name": "http",
        },
        "base_path": "/v1",
    }
    return Scenario(
        id=raw["id"],
        mode=raw["mode"],
        served_model_name=raw["served_model_name"],
        model=raw["model"],
        quant=raw["quant"],
        raw=raw,
    )


def test_discover_base_url_monkeypatch(monkeypatch):
    s = _make_scenario()
    called = {}

    def fake_discover(**kw):
        called.update(kw)
        return "http://10.0.0.1:30000/v1"

    monkeypatch.setattr(hybrid, "discover_service_base_url", fake_discover)
    url = hybrid.discover_base_url(s)
    assert url.endswith("/v1") and url.startswith("http://")
    assert called["namespace"] == "default"
    assert called["service_name"] == "infer-vllm"
    assert called["port_name"] == "http"


def test_wait_ready_monkeypatch(monkeypatch):
    s = _make_scenario()
    called = {}

    def fake_wait(**kw):
        called.update(kw)
        return True

    monkeypatch.setattr(hybrid, "wait_k8s_service_ready", fake_wait)
    ok = hybrid.wait_ready(s, timeout_s=9.0, interval_s=0.5)
    assert ok is True
    assert called["namespace"] == "default"
    assert called["service_name"] == "infer-vllm"
    assert called["port_name"] == "http"
    assert called["path_prefix"] == "/v1"
