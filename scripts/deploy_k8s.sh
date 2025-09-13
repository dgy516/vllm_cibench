#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") -f <k8s_yaml> [-n]

Options:
  -f, --file   Path to Kubernetes manifest YAML.
  -n, --dry-run  Print actions without executing kubectl apply.
  -h, --help   Show this help.

Environment:
  DRY_RUN=1     Same as --dry-run.

Example:
  $(basename "$0") -f configs/deploy/infer_vllm_kubeinfer.yaml
USAGE
}

FILE=""
DRY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--file)
      FILE="$2"; shift 2 ;;
    -n|--dry-run)
      DRY=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  DRY=1
fi

if [[ -z "$FILE" ]]; then
  echo "Error: -f/--file is required" >&2
  usage; exit 2
fi

if [[ $DRY -eq 1 ]]; then
  echo "[DRY-RUN] kubectl apply -f $FILE"
  exit 0
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "Error: kubectl not found in PATH" >&2
  exit 2
fi

echo "> Applying $FILE"
kubectl apply -f "$FILE"

echo "> Done. If using NodePort, discover via:\n  kubectl get svc -n default infer-vllm -o wide\n  # Then curl http://<node_ip>:<node_port>/v1/chat/completions"

