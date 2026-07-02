#!/usr/bin/env bash
# GPU env for the void SFT test — run ON the Lambda A10 box. Small: torch + transformers + trl + peft.
set -euo pipefail
run_root="${1:-$HOME/void_sft_run}"
mkdir -p "$run_root"; cd "$run_root"

echo "[void-sft-bootstrap] $(date -u +%Y-%m-%dT%H:%M:%SZ)"
command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

python3 -m venv venv
. venv/bin/activate
python -m pip install -U pip wheel setuptools

# CUDA torch wheels come from the default index on Lambda images; pin the training stack for reproducibility.
python -m pip install \
  "torch" \
  "transformers>=4.45,<5" \
  "trl>=0.12,<0.20" \
  "peft>=0.13" \
  "datasets>=2.20" \
  "accelerate>=0.34" \
  "bitsandbytes>=0.44" \
  "hf_transfer"

python - <<'PY'
import torch, transformers, trl, peft
print("[void-sft-bootstrap] torch", torch.__version__, "cuda", torch.cuda.is_available(),
      torch.cuda.get_device_name(0) if torch.cuda.is_available() else "(no gpu)")
print("[void-sft-bootstrap] transformers", transformers.__version__, "trl", trl.__version__, "peft", peft.__version__)
PY
echo "[void-sft-bootstrap] done"
