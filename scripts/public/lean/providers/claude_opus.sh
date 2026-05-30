#!/usr/bin/env bash
# Claude Opus 4.7 prover provider (subscription, no API key).
# Router contract: $1=goal_text (or @goal_file), writes proof to stdout.
set -euo pipefail
GOAL_TEXT="${1:?goal_text required}"
claude -p "You are a Lean 4 theorem prover. Produce ONLY the Lean proof term or tactic block that closes this goal (no prose, no markdown fence):

$GOAL_TEXT" --print 2>/dev/null
