#!/usr/bin/env bash
# Orchestrate the void SFT test on a Lambda A10 from the laptop: ship scripts + corpus, bootstrap, train, eval,
# pull the result. The corpus (sft_train.jsonl / sft_eval.jsonl) is produced by format_corpus.py; default /tmp/void_sft.
#   bash remote_run.sh <lambda-ip> [model] [data-dir]
set -euo pipefail
IP="${1:?usage: remote_run.sh <lambda-ip> [model] [data-dir]}"
MODEL="${2:-deepseek-ai/DeepSeek-Prover-V1.5-Base}"
DATA="${3:-/tmp/void_sft}"
KEY="${KEY:-$HOME/.ssh/id_ed25519}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
O="-i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ServerAliveInterval=30 -o ServerAliveCountMax=120"
SSH="ssh $O ubuntu@$IP"
SCP="scp $O"

echo "[remote_run] target ubuntu@$IP  model=$MODEL"
$SSH 'mkdir -p ~/void_sft_run/scripts ~/void_sft_run/data'
$SCP "$here"/format_corpus.py "$here"/train_lora.py "$here"/eval_completion.py "$here"/bootstrap.sh ubuntu@"$IP":~/void_sft_run/scripts/
$SCP "$DATA"/sft_train.jsonl "$DATA"/sft_eval.jsonl ubuntu@"$IP":~/void_sft_run/data/

$SSH 'bash ~/void_sft_run/scripts/bootstrap.sh ~/void_sft_run'
$SSH "cd ~/void_sft_run && . venv/bin/activate && HF_HUB_ENABLE_HF_TRANSFER=1 python scripts/train_lora.py --train data/sft_train.jsonl --model '$MODEL' --out ./void_adapter --epochs 3"
$SSH "cd ~/void_sft_run && . venv/bin/activate && python scripts/eval_completion.py --eval data/sft_eval.jsonl --model '$MODEL' --adapter ./void_adapter --out ./void_eval_result.json"

$SCP ubuntu@"$IP":~/void_sft_run/void_eval_result.json "$here"/void_eval_result.json
$SCP ubuntu@"$IP":~/void_sft_run/void_generations.json "$here"/void_generations.json
echo "=== VOID SFT RESULT (nll_delta_lower_is_better; negative on prove/formalize = the corpus lifted the model) ==="
cat "$here"/void_eval_result.json
echo
echo "[remote_run] pulled held-out generations -> $here/void_generations.json"
echo "[remote_run] NEXT (real pass@k, on the Lean VPS): scp void_generations.json hetzner-ztare:/tmp/ &&"
echo "             ssh hetzner-ztare 'cd ~/figs_activist_loop && PYTHONPATH=src venv/bin/python \\"
echo "               scripts/public/models/void_sft/kernel_check.py --gens /tmp/void_generations.json'"
