"""能力探测跳过：对未支持能力的用例标记为 skipped。"""

from __future__ import annotations

import pytest

from vllm_cibench.testsuites.functional import ChatCase, run_chat_suite


@pytest.mark.functional
def test_chat_suite_skips_unsupported_capability(monkeypatch):
    # 构造要求 chat.logprobs 能力的用例，但不提供该能力
    case = ChatCase(
        id="need_chat_logprobs",
        messages=[{"role": "user", "content": "hi"}],
        params={"logprobs": True, "top_logprobs": 1},
        required_capabilities=["chat.logprobs"],
        skip_if_unsupported=True,
    )

    # 不应发生任何网络请求，因此无需 requests_mock；直接运行套件
    report = run_chat_suite(
        base_url="http://example.com/v1",
        model="dummy",
        cases=[case],
        capabilities=[],  # 缺少 chat.logprobs
    )
    assert report["summary"]["total"] == 1
    assert report["summary"]["skipped"] == 1
    assert report["summary"]["passed"] == 0
    assert report["summary"]["failed"] == 0
    assert report["results"][0]["skipped"] is True

