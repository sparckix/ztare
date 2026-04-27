#!/usr/bin/env bash
# GP-135 MLH Family Program — end-to-end runbook.
#
# Phases (can be called individually or end-to-end):
#   scaffold  — build 6 substrates + seal F6 (only needed once; skip if already done)
#   runs      — run F1..F5 via `make discover`
#   packet    — export a sanitized prediction packet for the cold-agent step
#   seal      — seal a prediction JSON the operator has authored
#   unlock    — unlock F6 evidence (one-way, requires sealed prediction)
#   score     — score the sealed prediction against F6 ground truth
#   reset     — invalidate and rewind a contaminated round
#   all       — runs + packet + pause for prediction + seal + unlock + score
#
# Typical usage (single call):
#   bash scripts/run_mlh_family.sh all
#
# Other usage:
#   bash scripts/run_mlh_family.sh scaffold
#   bash scripts/run_mlh_family.sh runs
#   bash scripts/run_mlh_family.sh packet
#   bash scripts/run_mlh_family.sh seal --prediction path/to/pred.json
#   bash scripts/run_mlh_family.sh unlock
#   bash scripts/run_mlh_family.sh score --prediction path/to/sealed.json
#   bash scripts/run_mlh_family.sh reset
#
# Environment variables:
#   ITERS          — iterations per substrate (default 10)
#   MUTATOR_MODEL  — mutator model alias (default: o3)
#   JUDGE_MODEL    — judge model alias (default: claude)
#   DYNAMIC        — 0 or 1 (default 1; enables DAG steering + committee)
#   PREDICTION_JSON — path to pre-authored prediction JSON for unattended `all`
#                     mode. If unset, `all` will pause for interactive entry.
#
# Output: human-readable verdict + scorecard JSON at
#   research_areas/private/mlh_predictions/<tag>_sealed_scorecard.json

set -euo pipefail

# Force live output: Python unbuffered, UTF-8, no stdout/stderr buffering.
# Propagates to subprocesses (make, python -m ..., nested calls) via export.
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

PHASE="${1:-all}"
shift || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PY_BIN="${PY:-$REPO/venv/bin/python}"
if [ ! -x "$PY_BIN" ]; then
    PY_BIN="python3"
fi
# Use an array so -u is a separate word at invocation time. A plain
# string with " -u" appended would be parsed as a single path by bash
# and fail ("No such file or directory").
PY=("$PY_BIN" "-u")

ITERS="${ITERS:-5}"
MUTATOR_MODEL="${MUTATOR_MODEL:-o3}"
JUDGE_MODEL="${JUDGE_MODEL:-claude}"
DYNAMIC="${DYNAMIC:-1}"
OPEN_SLUGS=(mlh_f1 mlh_f2 mlh_f3 mlh_f4 mlh_f5)

banner() {
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  GP-135 MLH family — phase: $1"
    echo "════════════════════════════════════════════════════════════"
    echo ""
}

phase_scaffold() {
    banner "SCAFFOLD"
    if [ -d "$REPO/projects/mlh_f6" ] && [ -f "$REPO/projects/mlh_f6/sealed_holdout.json" ]; then
        echo "⏭  family already scaffolded; skipping. Remove projects/mlh_f*/ to rebuild."
        return 0
    fi
    "${PY[@]}" scripts/build_mlh_family.py
    "${PY[@]}" scripts/upgrade_mlh_rubrics.py
    echo "✅ scaffold complete."
}

phase_runs() {
    banner "RUNS — F1..F5 under discover"
    for slug in "${OPEN_SLUGS[@]}"; do
        echo ""
        echo "▶ $slug"
        make discover \
            PROJECT="$slug" \
            RUBRIC="$slug" \
            ITERS="$ITERS" \
            MUTATOR_MODEL="$MUTATOR_MODEL" \
            JUDGE_MODEL="$JUDGE_MODEL" \
            DYNAMIC="$DYNAMIC" \
            || echo "⚠ $slug exited non-zero; continuing (informative null is a valid outcome)"
    done
    echo ""
    echo "✅ F1..F5 runs complete. Summary of champion scores:"
    for slug in "${OPEN_SLUGS[@]}"; do
        if [ -f "$REPO/projects/$slug/champion_eval_results.json" ]; then
            score=$("${PY[@]}" -c "import json; print(json.load(open('$REPO/projects/$slug/champion_eval_results.json')).get('score','?'))" 2>/dev/null || echo "?")
            echo "  $slug: score=$score"
        else
            echo "  $slug: no champion_eval_results.json"
        fi
    done
}

phase_packet() {
    banner "PACKET — sanitized prediction packet"
    "$PY" scripts/export_mlh_prediction_packet.py
}

phase_seal() {
    banner "SEAL — prediction JSON"
    local pred_path="${PREDICTION_JSON:-}"
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --prediction) pred_path="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    if [ -z "$pred_path" ]; then
        echo "❌ --prediction <path> or PREDICTION_JSON env var required for seal phase" >&2
        exit 2
    fi
    "${PY[@]}" scripts/seal_mlh_prediction.py --prediction "$pred_path"
}

phase_reset() {
    banner "RESET — invalidate contaminated round"
    "$PY" scripts/reset_mlh_family_round.py --confirm
}

phase_unlock() {
    banner "UNLOCK — F6 evidence (one-way)"
    "${PY[@]}" scripts/unlock_mlh_holdout.py --confirm
}

phase_score() {
    banner "SCORE — prediction vs F6 GT"
    local pred_path=""
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --prediction) pred_path="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    if [ -z "$pred_path" ]; then
        # Use most recent sealed prediction
        pred_path=$(ls -t "$REPO/research_areas/private/mlh_predictions/"*_sealed.json 2>/dev/null | head -1 || true)
        if [ -z "$pred_path" ]; then
            echo "❌ no sealed prediction found; --prediction <path> required" >&2
            exit 2
        fi
        echo "(auto-selected most recent sealed: $(basename "$pred_path"))"
    fi
    "${PY[@]}" scripts/score_mlh_prediction.py --prediction "$pred_path"
}

phase_all() {
    banner "ALL — scaffold → runs → packet → prediction → seal → unlock → score"
    phase_scaffold
    phase_runs
    phase_packet

    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  OPERATOR INPUT REQUIRED"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "F1..F5 have run. Exported packet above. Author the prediction JSON from"
    echo "the SANITIZED PACKET ONLY, not from the full repo. Required fields:"
    echo ""
    echo "  training_substrates           (list of slugs)"
    echo "  holdout_substrate             ('mlh_f6')"
    echo "  invariant_statement           (plain language)"
    echo "  composition_class_prediction  ('additive' | 'multiplicative' | 'neither')"
    echo "  composition_rule              (closed-form f(a*b) for coprime a, b)"
    echo "  prime_power_rule              (closed-form f(p^k))"
    echo "  predicted_holdout_values      (dict[int, int], >=20 entries from n=81..120)"
    echo "  predicted_at_n1               (int)"
    echo "  confidence                    (float in [0, 1])"
    echo "  derivation_source             ('engine' | 'operator' | 'joint')"
    echo "  source_packet_hash            (from packet README / packet_manifest.json)"
    echo ""

    local pred_path="${PREDICTION_JSON:-}"
    if [ -z "$pred_path" ]; then
        echo "Enter path to prediction JSON (or set PREDICTION_JSON env var next time):"
        read -r pred_path
    fi
    if [ ! -f "$pred_path" ]; then
        echo "❌ prediction JSON not found: $pred_path" >&2
        exit 2
    fi

    phase_seal --prediction "$pred_path"
    phase_unlock
    phase_score
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  GP-135 end-to-end complete. Scorecard above."
    echo "════════════════════════════════════════════════════════════"
}

case "$PHASE" in
    scaffold)      phase_scaffold ;;
    runs)          phase_runs ;;
    packet)        phase_packet ;;
    seal)          phase_seal "$@" ;;
    unlock)        phase_unlock ;;
    score)         phase_score "$@" ;;
    reset)         phase_reset ;;
    all)           phase_all ;;
    -h|--help|help)
        sed -n '2,32p' "$0"
        ;;
    *)
        echo "Unknown phase: $PHASE" >&2
        echo "Valid phases: scaffold, runs, packet, seal, unlock, score, reset, all" >&2
        exit 2
        ;;
esac
