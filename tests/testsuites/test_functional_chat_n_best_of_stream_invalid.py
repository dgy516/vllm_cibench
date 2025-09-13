"""n + best_of + stream 组合的负路径校验。"""

from __future__ import annotations

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
@pytest.mark.validation
def test_chat_n_gt_best_of_with_stream_invalid(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    err = {"error": {"message": "n cannot be greater than best_of when streaming"}}
    requests_mock.post(url, json=err, status_code=400)
    client = OpenAICompatClient(base_url=base)
    with pytest.raises(Exception):
        _ = run_basic_chat(
            client,
            model="dummy",
            messages=[{"role": "user", "content": "hi"}],
            n=2,
            best_of=1,
            stream=True,
        )
