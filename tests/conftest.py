"""测试全局配置。

将 `src` 目录加入 `sys.path`，以便在未打包安装时可直接导入包。
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
