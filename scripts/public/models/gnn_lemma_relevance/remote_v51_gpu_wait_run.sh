#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/gnn_v51_run/figs_activist_loop}"
PY="${PY:-$HOME/gnn_v51_venv/bin/python}"
FREE_MB_REQUIRED="${FREE_MB_REQUIRED:-12000}"
SLEEP_SECONDS="${SLEEP_SECONDS:-300}"
MAX_WAITS="${MAX_WAITS:-96}"

cd "$ROOT"
mkdir -p analytics/public/leanmill/_legacy_lemma_relevance/logs

wait_for_gpu() {
  local waits=0
  while true; do
    local free_mb
    free_mb="$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -n 1 | tr -d ' ')"
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) gpu_free_mb=${free_mb} required=${FREE_MB_REQUIRED}"
    if [ "${free_mb}" -ge "${FREE_MB_REQUIRED}" ]; then
      return 0
    fi
    waits=$((waits + 1))
    if [ "${waits}" -ge "${MAX_WAITS}" ]; then
      echo "Timed out waiting for GPU memory." >&2
      return 2
    fi
    sleep "${SLEEP_SECONDS}"
  done
}

export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

wait_for_gpu

"${PY}" scripts/public/models/gnn_lemma_relevance/v51_train_hetero_gnn.py \
  --device cuda \
  --max-targets 500 \
  --max-files 60 \
  --include-file-regex 'ns_|Navier|CKN|L3A' \
  --include-ztare-trusted \
  --epochs 600 \
  --v41-epochs 400 \
  --hidden 64 \
  --out analytics/public/leanmill/results/v51_hetero_gnn_train_gpu_ns_report.json \
  2>&1 | tee analytics/public/leanmill/_legacy_lemma_relevance/logs/v51_gpu_ns.log

wait_for_gpu

"${PY}" scripts/public/models/gnn_lemma_relevance/v51_train_hetero_gnn.py \
  --device cuda \
  --max-targets 300 \
  --max-files 140 \
  --exclude-file-regex '^ns_' \
  --include-ztare-trusted \
  --epochs 600 \
  --v41-epochs 400 \
  --hidden 64 \
  --out analytics/public/leanmill/results/v51_hetero_gnn_train_gpu_non_ns_report.json \
  2>&1 | tee analytics/public/leanmill/_legacy_lemma_relevance/logs/v51_gpu_non_ns.log
