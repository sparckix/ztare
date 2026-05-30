#!/usr/bin/env bash
# Codex GPT-5 prover provider (subscription).
# Router contract: $1=goal_text, writes proof to stdout.
set -euo pipefail
GOAL_TEXT="${1:?goal_text required}"
ZTARE_CODEX_AGENT_MODEL="${ZTARE_CODEX_AGENT_MODEL:-gpt-5.5}" \
  codex exec "You are a Lean 4 theorem prover. Produce ONLY the Lean proof term or tactic block that closes this goal (no prose, no fence):

$GOAL_TEXT" 2>/dev/null
