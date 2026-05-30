#!/usr/bin/env bash
# Build the next leak-tight MCB corpus slice, qualify it, and optionally launch
# a bounded REPL-step LeanMill drain.
#
# This is factory plumbing, not proof credit. It keeps the line fed while
# preserving the same source qualification and governance boundaries.
set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
RUN_MILL="${RUN_MILL:-1}"
WORKERS="${WORKERS:-2}"
WAIT_PATTERN="${WAIT_PATTERN:-}"
ROOT="${ROOT:-/tmp/rung1/mcb_refill_$(date +%Y%m%d_%H%M%S)}"
SANDBOX="${SANDBOX:-analytics/public/leanmill/external_benchmarks/sandboxes/v28A_carleson_baseline/carleson}"
PAIRS="${PAIRS:-analytics/public/leanmill/gnn_ranker/mathlib_pairs.jsonl}"
EXCLUDE="${EXCLUDE:-/tmp/rung1/mcb_expand100/mcb_corpus_expand100.json}"
TARGET_N="${TARGET_N:-140}"
SCAN_CAP="${SCAN_CAP:-700}"
MAX_ROWS="${MAX_ROWS:-80}"
LEANSEARCH_LIMIT="${LEANSEARCH_LIMIT:-8}"
MAX_CANDIDATES_PER_ROW="${MAX_CANDIDATES_PER_ROW:-6}"
INCLUDE_UNCLASSIFIED="${INCLUDE_UNCLASSIFIED:-0}"
INTAKE_LIMIT_PER_WORKER="${INTAKE_LIMIT_PER_WORKER:-16}"
A_TIMEOUT="${A_TIMEOUT:-120}"
B_TIMEOUT="${B_TIMEOUT:-180}"

mkdir -p "$ROOT"

log() {
  printf '[leanmill-refill] %s\n' "$*" >&2
}

run_or_echo() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRY_RUN'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

if [[ -n "$WAIT_PATTERN" ]]; then
  log "waiting for active pattern to clear: $WAIT_PATTERN"
  while tmux ls 2>/dev/null | grep -E "$WAIT_PATTERN" >/dev/null; do
    sleep 20
  done
fi

CORPUS="$ROOT/mcb_corpus.json"
FILES_DIR="$ROOT/mcb_files"
INTAKE_DB="$ROOT/intake.sqlite"
PIPE_ROOT="$ROOT/source_pipeline"
MILL_ROOT="$ROOT/mill"

log "building corpus target_n=$TARGET_N scan_cap=$SCAN_CAP root=$ROOT"
if [[ "$DRY_RUN" != "1" ]]; then
  python3 - "$ROOT" <<'PY'
import json, pathlib, sys, time
root = sys.argv[1]
p = pathlib.Path("/tmp/rung1/current_leanmill_run.json")
p.parent.mkdir(parents=True, exist_ok=True)
json.dump({
    "name": "MCB refill source expansion",
    "machine": "Remote",
    "state": "running",
    "phase": "source_expansion",
    "progress": "building leak-tight rows before source qualification",
    "next_handoff": "source qualification conveyor",
    "root": root,
    "started_epoch": time.time(),
}, open(p, "w"), indent=2, sort_keys=True)
PY
fi
run_or_echo python3 scripts/public/control/build_module_context_benchmark.py \
  --sandbox "$SANDBOX" \
  --pairs "$PAIRS" \
  --out "$CORPUS" \
  --files-dir "$FILES_DIR" \
  --target-n "$TARGET_N" \
  --scan-cap "$SCAN_CAP" \
  --exclude-corpus "$EXCLUDE" \
  --checkpoint-jsonl "$ROOT/mcb_checkpoint.jsonl" \
  --partial-out "$ROOT/mcb_corpus.partial.json" \
  --progress-json "$ROOT/mcb_progress.json"

log "qualifying sources into intake"
if [[ "$DRY_RUN" != "1" ]]; then
  python3 - "$ROOT" <<'PY'
import json, pathlib, sys, time
root = sys.argv[1]
p = pathlib.Path("/tmp/rung1/current_leanmill_run.json")
json.dump({
    "name": "MCB refill source qualification",
    "machine": "Remote",
    "state": "running",
    "phase": "source_qualification",
    "progress": "qualifying sources into canary intake",
    "next_handoff": "bounded REPL-step mill if ready rows exist",
    "root": root,
    "started_epoch": time.time(),
}, open(p, "w"), indent=2, sort_keys=True)
PY
fi
run_or_echo python3 scripts/public/control/leanmill/search/mcb_source_pipeline.py \
  --corpus "$CORPUS" \
  --exclude "$EXCLUDE" \
  --root "$PIPE_ROOT" \
  --intake-db "$INTAKE_DB" \
  --max-rows "$MAX_ROWS" \
  --leansearch-limit "$LEANSEARCH_LIMIT" \
  --max-candidates-per-row "$MAX_CANDIDATES_PER_ROW" \
  $(if [[ "$INCLUDE_UNCLASSIFIED" == "1" ]]; then printf '%s' '--include-unclassified'; fi) \
  --summary "$PIPE_ROOT/summary.json"

if [[ "$RUN_MILL" != "1" ]]; then
  log "RUN_MILL=0; stopping after intake"
  exit 0
fi

if [[ "$DRY_RUN" == "1" ]]; then
  log "DRY_RUN=1; stopping before ready-count query and worker launch"
  exit 0
fi

READY="$(python3 - "$INTAKE_DB" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
print(con.execute("select count(*) from intake_queue where status='ready'").fetchone()[0])
PY
)"
if [[ "$READY" == "0" ]]; then
  log "no ready intake rows; not launching mill"
  exit 0
fi

mkdir -p "$MILL_ROOT"
python3 - "$ROOT" "$MILL_ROOT" "$READY" <<'PY'
import json, pathlib, sys, time
root, mill_root, ready = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path("/tmp/rung1/current_leanmill_run.json")
p.parent.mkdir(parents=True, exist_ok=True)
json.dump({
    "name": "MCB refill qualified drain",
    "machine": "Remote",
    "state": "running",
    "phase": "proof_execution_repl_step_parallel",
    "progress": f"{ready} ready rows from refill buffer",
    "next_handoff": "governance gate or residual compiler",
    "root": mill_root,
    "source_root": root,
    "started_epoch": time.time(),
}, open(p, "w"), indent=2, sort_keys=True)
PY

log "launching $WORKERS bounded REPL-step workers on $READY ready rows"
for w in $(seq 1 "$WORKERS"); do
  tmux new-session -d -s "gp225_mcb_refill_w${w}" \
    "cd $(pwd) && python3 scripts/public/control/leanmill/search/factory_mill.py \
      --from-intake \
      --intake-db '$INTAKE_DB' \
      --intake-limit '$INTAKE_LIMIT_PER_WORKER' \
      --worker-id 'mcb_refill_w${w}' \
      --root '$MILL_ROOT' \
      --summary '$MILL_ROOT/summary_w${w}.json' \
      --corpus '$CORPUS' \
      --static-filter '$PIPE_ROOT/row_context_filter.json' \
      --backend repl_step \
      --b-workers 1 \
      --a-timeout '$A_TIMEOUT' \
      --b-timeout '$B_TIMEOUT' \
      --max-candidates 4 \
      --max-actions 3 \
      --candidate-mode first_then_all \
      --limit-per-worker 999"
done

log "launched; root=$ROOT"
