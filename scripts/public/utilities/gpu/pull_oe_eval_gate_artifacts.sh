#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  pull_oe_eval_gate_artifacts.sh \
    --host ubuntu@203.0.113.10 \
    --identity ~/.ssh/id_ed25519 \
    --remote-root ~/ztare_gpu_run \
    --output-dir projects/foo/workspace/outputs/official_stage1_step_100000 \
    --local-dir projects/foo/workspace/outputs/official_stage1_step_100000

Copies only the artifacts usually needed by fail-closed oe-eval gates:
metrics-all.jsonl, task-*-metrics.json, task-*-predictions.jsonl, and
.ztare_done.json. This avoids copying request/recorded-input files on every
poll.
USAGE
}

host=""
identity=""
remote_root=""
output_dir=""
local_dir=""
known_hosts="${ZTARE_GPU_KNOWN_HOSTS:-/private/tmp/ztare_gpu_known_hosts}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      host="$2"
      shift 2
      ;;
    --identity)
      identity="$2"
      shift 2
      ;;
    --remote-root)
      remote_root="$2"
      shift 2
      ;;
    --output-dir)
      output_dir="$2"
      shift 2
      ;;
    --local-dir)
      local_dir="$2"
      shift 2
      ;;
    --known-hosts)
      known_hosts="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$host" || -z "$identity" || -z "$remote_root" || -z "$output_dir" || -z "$local_dir" ]]; then
  usage >&2
  exit 2
fi

safe_name="$(basename "$output_dir" | tr -c 'A-Za-z0-9_.-' '_')"
remote_tar="/tmp/ztare_${safe_name}_gate_artifacts.tgz"
local_tar="${TMPDIR:-/tmp}/ztare_${safe_name}_gate_artifacts.tgz"

ssh_opts=(
  -i "$identity"
  -o BatchMode=yes
  -o UserKnownHostsFile="$known_hosts"
  -o StrictHostKeyChecking=accept-new
)

mkdir -p "$local_dir"

ssh "${ssh_opts[@]}" "$host" \
  "cd ${remote_root}/${output_dir} && tar -czf ${remote_tar} metrics-all.jsonl task-*-metrics.json task-*-predictions.jsonl .ztare_done.json"
scp "${ssh_opts[@]}" "${host}:${remote_tar}" "$local_tar"
tar -xzf "$local_tar" -C "$local_dir"

echo "Pulled gate artifacts from ${host}:${remote_root}/${output_dir} to ${local_dir}"
