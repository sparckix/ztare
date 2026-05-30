#!/usr/bin/env bash
# Native-tactic provider for the LeanMill prover router.
# Wraps lean_tactic_hammer.py — runs exact?/aesop/polyrith/linarith/omega/
# decide/simp_all/norm_num/ring/rfl on a fully-formed Lean statement BEFORE
# any neural prover. Static-first baseline; the field's leaders skip publishing this.
#
# Router contract (goal_file path): the goal_file must contain a COMPLETE Lean
# theorem header ending in ':= by' (the hammer needs the statement, not a bare goal;
# see lean_tactic_hammer.py docstring "Honest scope" — statement synthesis from a
# bare goal needs field-type elaboration we don't have, so the router passes the
# statement directly). Writes the closing tactic/proof to $PROOF_FILE on success.
#
# Usage: native_hammer.sh <goal_file_with_statement> <proof_file> [target] [field]
set -euo pipefail
GOAL_FILE="${1:?goal_file (containing a Lean statement ending in := by) required}"
PROOF_FILE="${2:?proof_file required}"
TARGET="${3:-router_goal}"
FIELD="${4:-continuation}"
REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
STATEMENT="$(cat "$GOAL_FILE")"
python3 "$REPO/scripts/public/lean/lean_tactic_hammer.py" \
  --target "$TARGET" --field "$FIELD" --statement "$STATEMENT" --out "$PROOF_FILE" 2>/dev/null \
  && [ -s "$PROOF_FILE" ] \
  || { echo "-- native_hammer: no tactic in {exact?,aesop,polyrith,linarith,omega,decide,simp_all,norm_num,ring,rfl} closed the goal" > "$PROOF_FILE"; exit 1; }
