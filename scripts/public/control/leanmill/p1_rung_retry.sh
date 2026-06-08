#!/bin/bash
# P1 rung-retry launcher — VPS. Self-contained: sets PATH (elan/lake), strategist-move flags + the
# per-move caps (the unstarving fix so SPECIALIZE/GENERALIZE are REACHABLE), runs the governed run,
# writes a result JSON + a sentinel. Detach with: setsid bash p1_rung_retry.sh >log 2>&1 </dev/null &
set -uo pipefail
cd "$HOME/figs_activist_loop"
export PATH="$HOME/.elan/bin:$HOME/.local/bin:/usr/local/bin:$PATH"
export PYTHONPATH=src
export ZTARE_LEANMILL_SPECIALIZE=1      # generate kernel-verified weaker-case RUNGS (never closes G)
export ZTARE_LEANMILL_GENERALIZE=1      # closure via an internal strengthening
export ZTARE_LEANMILL_PERMOVE_CAPS=1    # the REAL unstarving fix: absolute per-move caps, not wallclock fractions
export ZTARE_CONJECTURE_DECOMPOSE=1     # decomposition active (spawn sub-lemmas)
export ZTARE_DAG_MOVE_BUDGET=32         # don't starve the cost-4 strategist moves
export ZTARE_CALIBRATE_PRIORS=1         # self-tuning priors on
export ZTARE_SOLVER_RUN_TAG=p1_rung_retry
echo "[p1] start $(date -u +%FT%TZ)"
python3 scripts/public/control/leanmill/p1_rung_retry.py
code=$?
echo "P1_RUN_EXIT=${code}"
echo "[p1] done $(date -u +%FT%TZ)"
touch "$HOME/figs_activist_loop/analytics/public/queries/.p1_rung_retry.done"
