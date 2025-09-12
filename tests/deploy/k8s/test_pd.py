"""K8s PD 模式适配层测试。"""

from __future__ import annotations

from vllm_cibench.config import Scenario
from vllm_cibench.deploy.k8s import pd


def _make_pd_scenario() -> Scenario:
    raw = {
        "id": "k8s_pd_deepseek-r1_2p1d_reasoning_w8a8",
        "mode": "k8s-pd",
        "model": "DeepSeek-R1",
        "served_model_name": "deepseek-r1",
        "quant": "w8a8",
        "k8s": {
            "namespace": "default",
            "service_name": "infer-vllm-pd",
            "port_name": "http",
        },
        "base_path": "/v1",
        "pd": {
            "scheduler_params": "--max-num-seqs=256 --enable-reasoning --reasoning-parser=deepseek_r1",
            "prefill_params": "--max-num-seqs=24 --tokenizer-pool-size=8 --enforce-eager --enable-prefix-caching",
            "decode_params": "--max-num-seqs=24 --preemption-mode=swap --swap-space=16",
        },
    }
    return Scenario(
        id=str(raw["id"]),
        mode=str(raw["mode"]),
        served_model_name=str(raw["served_model_name"]),
        model=str(raw["model"]),
        quant=str(raw["quant"]),
        raw=raw,
    )


def test_build_pd_args_and_discover(monkeypatch):
    s = _make_pd_scenario()
    args = pd.build_pd_args(s)
    assert "--enable-reasoning" in args["scheduler_params"]
    assert "--tokenizer-pool-size=8" in args["prefill_params"]
    assert "--swap-space=16" in args["decode_params"]

    called = {}

    def fake_discover(**kw):
        called.update(kw)
        return "http://10.0.0.2:30001/v1"

    monkeypatch.setattr(pd, "discover_service_base_url", fake_discover)
    url = pd.discover_base_url(s)
    assert url == "http://10.0.0.2:30001/v1"
    assert called["service_name"] == "infer-vllm-pd"
    assert called.get("node_port") is None


def test_wait_ready_pd(monkeypatch):
    s = _make_pd_scenario()
    called = {}

    def fake_wait(**kw):
        called.update(kw)
        return True

    monkeypatch.setattr(pd, "wait_k8s_service_ready", fake_wait)
    ok = pd.wait_ready(s, timeout_s=10.0, interval_s=0.5)
    assert ok is True
    assert called["namespace"] == "default"
    assert called["service_name"] == "infer-vllm-pd"
    assert called["port_name"] == "http"
    assert called["path_prefix"] == "/v1"
    assert called.get("node_port") is None


def test_node_port_override(monkeypatch):
    s = _make_pd_scenario()
    s.raw["k8s"]["node_port"] = 32001
    called = {}

    def fake_discover(**kw):
        called.update(kw)
        return "http://10.0.0.2:32001/v1"

    monkeypatch.setattr(pd, "discover_service_base_url", fake_discover)
    url = pd.discover_base_url(s)
    assert url.endswith("32001/v1")
    assert called["node_port"] == 32001


def test_wait_ready_node_port_override(monkeypatch):
    s = _make_pd_scenario()
    s.raw["k8s"]["node_port"] = 32001
    called = {}

    def fake_wait(**kw):
        called.update(kw)
        return True

    monkeypatch.setattr(pd, "wait_k8s_service_ready", fake_wait)
    ok = pd.wait_ready(s)
    assert ok is True
    assert called["node_port"] == 32001
