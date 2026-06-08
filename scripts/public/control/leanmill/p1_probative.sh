#!/bin/bash
# P1 PROBATIVE run — VPS. Fixes the two foot-guns the prior run exposed: (1) the warm agent ate 535s of
# 900s (budget starvation of the tail) → per-move caps + a bigger total wallclock; (2) 4 strategist moves
# were dormant → enable ALL of them, so the full move space is exercised and MEASURED (run_tag slices it).
set -uo pipefail
cd "$HOME/figs_activist_loop"
export PATH="$HOME/.elan/bin:$HOME/.local/bin:/usr/local/bin:$PATH"
export PYTHONPATH=src
# ALL strategist moves on (prior run left generalize/falsify/tactic_step dormant)
export ZTARE_LEANMILL_SPECIALIZE=1
export ZTARE_LEANMILL_GENERALIZE=1
export ZTARE_LEANMILL_FALSIFY=1
export ZTARE_LEANMILL_TACTIC_STEP=1
export ZTARE_CONJECTURE_DECOMPOSE=1          # decomposition-first: spawn + attack sub-lemmas (the rung path)
# per-move wallclock caps ON + cap warm/cold so one move can't dominate (warm ate 535s last run)
export ZTARE_LEANMILL_PERMOVE_CAPS=1
export ZTARE_LEANMILL_CAP_CLAUDE_WARM=120
export ZTARE_LEANMILL_CAP_COLD_SHOT=120
export ZTARE_DAG_MOVE_BUDGET=48              # more move-budget units so the tail gets turns
export ZTARE_P1_TIMEOUT=1200                 # bigger total wallclock (665s+ free for the tail even if warm caps high)
export ZTARE_CALIBRATE_PRIORS=1
export ZTARE_SOLVER_RUN_TAG=p1_probative
echo "[p1-probative] start $(date -u +%FT%TZ)"
python3 scripts/public/control/leanmill/p1_rung_retry.py
echo "P1_RUN_EXIT=$?"
echo "[p1-probative] done $(date -u +%FT%TZ)"
touch "$HOME/figs_activist_loop/analytics/public/queries/.p1_probative.done"
