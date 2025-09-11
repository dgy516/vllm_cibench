"""vLLM CI Bench / 系统测试套件包。

该包包含启动器、部署运行器（本地 / K8s）、功能/性能/精度测试器，以及指标处理与发布组件。
"""

__all__ = ["__version__", "get_version"]

__version__ = "0.0.1"


def get_version() -> str:
    """返回当前包版本号。

    返回值:
        str: 版本号字符串，例如 "0.0.1"。
    副作用:
        无副作用，仅读取内置常量。
    """

    return __version__
