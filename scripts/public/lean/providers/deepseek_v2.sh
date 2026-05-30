#!/usr/bin/env bash
# DeepSeek-Prover-V2 prover provider (open weights).
# Default path: local Ollama. Override with ZTARE_DEEPSEEK_ENDPOINT for an HF/vLLM server.
# Router contract: $1=goal_text, writes proof to stdout.
set -euo pipefail
GOAL_TEXT="${1:?goal_text required}"
PROMPT="Complete the following Lean 4 theorem. Output ONLY the proof (no prose):

$GOAL_TEXT"
if [ -n "${ZTARE_DEEPSEEK_ENDPOINT:-}" ]; then
  curl -s "$ZTARE_DEEPSEEK_ENDPOINT/v1/completions" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c 'import json,sys; print(json.dumps({"model":"deepseek-prover-v2","prompt":sys.argv[1],"max_tokens":2048,"temperature":0.0}))' "$PROMPT")" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["choices"][0]["text"])'
else
  ollama run deepseek-prover-v2 "$PROMPT" 2>/dev/null
fi
