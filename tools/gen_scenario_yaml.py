#!/usr/bin/env python3
"""生成场景 YAML 示例。

根据命令行参数生成最小可用的 `configs/scenarios/*.yaml` 内容。
"""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate scenario YAML skeleton")
    p.add_argument("--id", required=True)
    p.add_argument("--mode", choices=["local", "k8s-hybrid", "k8s-pd"], required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--served-model-name", required=True)
    p.add_argument("--quant", default="w8a8")
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args()


def main() -> None:
    ns = parse_args()
    content = f"""id: {ns.id}
mode: {ns.mode}
model: {ns.model}
served_model_name: {ns.__dict__['served_model_name']}
quant: {ns.quant}
features:
  guided_decoding: false
  function_call: false
  reasoning: false
base_url: http://127.0.0.1:9000/v1
startup_timeout_seconds: 1200
env: {{}}
args: {{}}
"""
    ns.out.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()

