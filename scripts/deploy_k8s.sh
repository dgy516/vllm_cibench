#!/usr/bin/env bash
# 轻量级 K8s 部署脚本
#
# 用途：对给定的 K8s YAML 执行 kubectl apply，并给出简单的探活提示。
#
# 使用示例：
#   scripts/deploy_k8s.sh -f configs/deploy/infer_vllm_kubeinfer.yaml
#   scripts/deploy_k8s.sh --file ./my_deploy.yaml --namespace infer --wait 60
#
# 退出码：
#   0 = 成功提交给 K8s；非 0 = 发生错误（例如缺少 kubectl/YAML 不存在）。

set -euo pipefail

usage() {
  cat <<'USAGE'
用法：deploy_k8s.sh [选项]

选项：
  -f, --file PATH          部署的 YAML 文件（默认：configs/deploy/infer_vllm_kubeinfer.yaml）
  -n, --namespace NS       目标命名空间（可选）
  -w, --wait SECONDS       部署后等待的秒数，仅做提示性等待（默认 0）
  -h, --help               显示本帮助

说明：
  本脚本仅封装最小化的 kubectl apply 操作，并不会做复杂的就绪性判断。
  若需探活或更精细的等待逻辑，请结合项目的编排 CLI（run/run-matrix）或在 CI 中使用 wait 步骤。
USAGE
}

YAML_PATH="configs/deploy/infer_vllm_kubeinfer.yaml"
NAMESPACE=""
WAIT_SECONDS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--file)
      YAML_PATH="$2"; shift 2 ;;
    -n|--namespace)
      NAMESPACE="$2"; shift 2 ;;
    -w|--wait)
      WAIT_SECONDS="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "未知参数：$1" >&2
      usage; exit 2 ;;
  esac
done

# 校验 kubectl
if ! command -v kubectl >/dev/null 2>&1; then
  echo "错误：未找到 kubectl，请先安装并配置 KUBECONFIG。" >&2
  exit 1
fi

# 校验文件
if [[ ! -f "$YAML_PATH" ]]; then
  echo "错误：找不到 YAML 文件：$YAML_PATH" >&2
  exit 1
fi

set -x
if [[ -n "$NAMESPACE" ]]; then
  kubectl apply -n "$NAMESPACE" -f "$YAML_PATH"
else
  kubectl apply -f "$YAML_PATH"
fi
set +x

if [[ "$WAIT_SECONDS" -gt 0 ]]; then
  echo "已提交资源至集群，等待 ${WAIT_SECONDS}s 以便资源创建……"
  sleep "$WAIT_SECONDS"
fi

cat <<EOF
已执行 kubectl apply：$YAML_PATH
下一步建议：
- 使用 'kubectl get pods -A | grep -i vllm' 查看 Pod 状态
- 暴露端口/查看 Service：'kubectl get svc -A | grep -i vllm'
- 如需手动探活，可端口转发后访问：curl http://127.0.0.1:9000/v1/models
EOF

exit 0

