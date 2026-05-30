#!/usr/bin/env bash
set -euo pipefail

run_root="${1:-$HOME/ztare_neural_gpu_run}"
python_bin="${PYTHON_BIN:-python3}"

mkdir -p "$run_root"
cd "$run_root"

echo "[ztare-transformer-probe-bootstrap] start $(date -u +%Y-%m-%dT%H:%M:%SZ)"

arch="$(uname -m)"
if [ "$arch" != "x86_64" ]; then
  echo "[ztare-transformer-probe-bootstrap] unsupported arch: $arch; use x86_64 for CUDA wheels" >&2
  exit 2
fi

command -v nvidia-smi >/dev/null
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

"$python_bin" -m venv venv
. venv/bin/activate

python -m pip install -U pip wheel setuptools
python -m pip install -U torch transformers accelerate numpy pandas safetensors sentencepiece protobuf hf_transfer

cat > ACTIVATE_ZTARE_TRANSFORMER_PROBE_ENV.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
. venv/bin/activate
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"
EOF
chmod +x ACTIVATE_ZTARE_TRANSFORMER_PROBE_ENV.sh

python - <<'PY'
import torch
import transformers

print("torch", torch.__version__, torch.version.cuda, torch.cuda.is_available())
print("transformers", transformers.__version__)
assert torch.cuda.is_available()
PY

echo "[ztare-transformer-probe-bootstrap] done $(date -u +%Y-%m-%dT%H:%M:%SZ)"
