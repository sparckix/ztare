#!/usr/bin/env bash
set -euo pipefail

run_root="${1:-$HOME/ztare_gpu_run}"
python_bin="${PYTHON_BIN:-python3}"
olmes_repo="${OLMES_REPO:-https://github.com/allenai/olmes.git}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$run_root"
cd "$run_root"

echo "[ztare-gpu-bootstrap] start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
arch="$(uname -m)"
if [ "$arch" != "x86_64" ]; then
  echo "[ztare-gpu-bootstrap] unsupported arch: $arch; use x86_64 for OLMES/vLLM wheels" >&2
  exit 2
fi

command -v nvidia-smi >/dev/null
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

"$python_bin" -m venv venv
. venv/bin/activate

python -m pip install -U pip wheel setuptools uv hf_transfer

if [ ! -d olmes/.git ]; then
  git clone "$olmes_repo" olmes
fi

cd olmes
git pull --ff-only || true
uv pip install --python ../venv/bin/python -e ".[gpu]" --torch-backend=auto
cd ..

if [ -f "$script_dir/patch_lm_eval_vllm_prompt_tokens.py" ]; then
  python "$script_dir/patch_lm_eval_vllm_prompt_tokens.py"
fi

if ! command -v oe-eval >/dev/null 2>&1 && command -v olmes >/dev/null 2>&1; then
  ln -sf "$(command -v olmes)" venv/bin/oe-eval
fi

oe-eval --help >/tmp/ztare_oe_eval_help.txt
python - <<'PY'
import torch
import vllm
print("torch", torch.__version__, torch.version.cuda, torch.cuda.is_available())
print("vllm", vllm.__version__)
assert torch.cuda.is_available()
PY

cat > ACTIVATE_ZTARE_GPU_ENV.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
. venv/bin/activate
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"
EOF
chmod +x ACTIVATE_ZTARE_GPU_ENV.sh

echo "[ztare-gpu-bootstrap] done $(date -u +%Y-%m-%dT%H:%M:%SZ)"
