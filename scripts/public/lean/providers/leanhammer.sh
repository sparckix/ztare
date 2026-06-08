#!/usr/bin/env bash
# LeanHammer prover provider (premise-selection hammer for Lean 4).
#
# Upstream: arXiv:2506.07477 "Premise Selection for a Lean Hammer"
#           github.com/hanwenzhu/premise-selection  (the `Hammer` tactic +
#           the `hammer` premise-selection client) and the companion
#           lean-auto / Duper reconstruction backend.
# Reported: ~33% one-shot proof rate on a Mathlib eval set with retrieval.
#
# Router contract (mirrors leancopilot.sh): $1 = goal_file, a .lean file that
# elaborates inside the ztare_proofs Lake project and ends the target theorem
# with `:= by hammer` (the `hammer` tactic runs premise selection then calls the
# reconstruction backend). On success the elaborated proof / "Try this" tactic
# block is written to stdout; on failure exit non-zero.
#
# STATUS: STUB. LeanHammer is NOT installed in ztare_proofs (no `lake require`
# entry, no premise-selection model fetched, reconstruction backend absent).
# Until installed (see leanhammer_feasibility_report.md for exact steps) this
# wrapper emits a typed provider-unavailable line and exits 1 so the router
# records `proof_nonempty=false` rather than silently treating the diagnostic
# as proof text. tested:false in the registry reflects exactly this.
set -euo pipefail
GOAL_FILE="${1:?goal_file required}"
REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
PROOFS="$REPO/ztare_proofs"

# Allow opting in once the dependency is actually present in the Lake project.
# Set ZTARE_LEANHAMMER_INSTALLED=1 to take the live `lake env lean` path.
if [ "${ZTARE_LEANHAMMER_INSTALLED:-0}" != "1" ]; then
  # Diagnostics go to STDERR (not stdout) so invoke() captures them as `error`
  # and leaves proof_text empty -> proof_nonempty:false. This keeps the typed
  # contract honest: a provider_unavailable stub must NOT look like a proof.
  {
    echo "provider_unavailable: LeanHammer (arXiv:2506.07477) is not installed in ztare_proofs."
    echo "needs a 'require Hammer' (lean-auto + Duper + premise-selection client) in lakefile.toml,"
    echo "a fetched premise-selection model, and a rebuilt Lake project. See"
    echo "scripts/public/control/leanmill/leanhammer_feasibility_report.md for install steps."
    echo "re-run with ZTARE_LEANHAMMER_INSTALLED=1 once the dependency is present."
  } >&2
  exit 1
fi

# ── Live path (only reached when the operator has installed LeanHammer) ──────
# The `hammer` tactic prints its discovered proof as a `Try this:` suggestion
# during elaboration (same surface as LeanCopilot / exact?). Capture it.
cd "$PROOFS"
lake env lean "$GOAL_FILE" 2>&1 | grep -A4 "Try this\|hammer\|Duper\|premises" || \
  { echo "-- leanhammer: no proof found by the hammer tactic"; exit 1; }
