"""基础版本测试。

确保包结构与最小功能可用，避免 CI 在无测试时失败。
"""

from vllm_cibench import get_version


def test_get_version_non_empty():
    """校验 `get_version` 返回非空字符串。"""

    v = get_version()
    assert isinstance(v, str) and len(v) > 0
