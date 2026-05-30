#!/usr/bin/env bash
# LeanCopilot prover provider (IDE incumbent).
# Wraps `search_proof` / `suggest_tactics`. Requires LeanCopilot installed in the Lake project.
# Router contract: $1=goal_file (a .lean file with a `by lean_copilot_search_proof` placeholder),
# writes the elaborated proof to stdout via lake build capture.
set -euo pipefail
GOAL_FILE="${1:?goal_file required}"
REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$REPO/ztare_proofs"
# LeanCopilot emits suggestions to stderr during elaboration; capture them.
lake env lean "$GOAL_FILE" 2>&1 | grep -A2 "Try this\|suggest_tactics\|search_proof" || \
  { echo "-- leancopilot: no suggestion"; exit 1; }
