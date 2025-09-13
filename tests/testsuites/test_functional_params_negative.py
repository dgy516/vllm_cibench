"""参数合法性（负路径）测试。"""

# isort: skip_file

from __future__ import annotations

import pytest
import requests

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat, run_basic_completion


@pytest.mark.functional
@pytest.mark.validation
def test_chat_invalid_top_p_raises_http_error(requests_mock):
    """非法 top_p 应返回 4xx 并触发 HTTPError。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    err = {"error": {"message": "invalid top_p"}}
    requests_mock.post(url, json=err, status_code=400)

    client = OpenAICompatClient(base_url=base)
    with pytest.raises(requests.HTTPError):
        _ = run_basic_chat(
            client,
            model="dummy",
            messages=[{"role": "user", "content": "hi"}],
            top_p=1.5,
        )


@pytest.mark.functional
@pytest.mark.validation
def test_completions_negative_max_tokens(requests_mock):
    """负数 max_tokens 应返回 4xx 并触发 HTTPError。"""

    base = "http://example.com/v1"
    url = base + "/completions"
    err = {"error": {"message": "max_tokens must be >= 0"}}
    requests_mock.post(url, json=err, status_code=422)

    with pytest.raises(requests.HTTPError):
        _ = run_basic_completion(
            base_url=base,
            model="dummy",
            prompt="Hello",
            max_tokens=-1,
        )
