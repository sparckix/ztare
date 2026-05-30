#!/usr/bin/env bash
# Snapshot an in-progress MCB corpus expansion and run a small source-to-mill
# microbatch. This reduces time-to-first-qualified-row without changing the
# scientific gates: source qualification, target-context filtering, Path-A
# execution, and Path-B governance remain the same.
set -euo pipefail

SOURCE_ROOT="${SOURCE_ROOT:-/tmp/rung1/mcb_refill_after_remaining}"
ROOT="${ROOT:-/tmp/rung1/mcb_microbatch_$(date +%Y%m%d_%H%M%S)}"
EXCLUDE="${EXCLUDE:-/tmp/rung1/mcb_expand100/mcb_corpus_expand100.json}"
MIN_KEPT="${MIN_KEPT:-8}"
MIN_NEW_ROWS="${MIN_NEW_ROWS:-8}"
MAX_ROWS="${MAX_ROWS:-12}"
LEANSEARCH_LIMIT="${LEANSEARCH_LIMIT:-6}"
MAX_CANDIDATES_PER_ROW="${MAX_CANDIDATES_PER_ROW:-4}"
RUN_MILL="${RUN_MILL:-1}"
WORKERS="${WORKERS:-1}"
INTAKE_LIMIT_PER_WORKER="${INTAKE_LIMIT_PER_WORKER:-8}"
A_TIMEOUT="${A_TIMEOUT:-120}"
B_TIMEOUT="${B_TIMEOUT:-180}"
DRY_RUN="${DRY_RUN:-0}"
WAIT_SECONDS="${WAIT_SECONDS:-0}"
SLEEP_SECONDS="${SLEEP_SECONDS:-30}"
SOURCE_ALREADY_DEDUPED="${SOURCE_ALREADY_DEDUPED:-0}"
INCLUDE_UNCLASSIFIED="${INCLUDE_UNCLASSIFIED:-0}"

log() {
  printf '[leanmill-microbatch] %s\n' "$*" >&2
}

json_field() {
  python3 - "$1" "$2" <<'PY'
import json, sys
path, key = sys.argv[1], sys.argv[2]
try:
    obj = json.load(open(path))
except FileNotFoundError:
    print("")
    raise SystemExit(0)
print(obj.get(key, ""))
PY
}

PROGRESS="$SOURCE_ROOT/mcb_progress.json"
PARTIAL="$SOURCE_ROOT/mcb_corpus.partial.json"
EXCLUDED_ROWS="$(python3 - "$EXCLUDE" <<'PY'
import json, sys
try:
    obj = json.load(open(sys.argv[1]))
except FileNotFoundError:
    print(0)
    raise SystemExit(0)
rows = obj if isinstance(obj, list) else (obj.get("rows") or obj.get("corpus") or obj.get("targets") or [])
print(len(rows))
PY
)"
if [[ "$SOURCE_ALREADY_DEDUPED" == "1" ]]; then
  EXCLUDED_ROWS=0
fi
WAIT_START="$(date +%s)"
while true; do
  KEPT="$(json_field "$PROGRESS" kept)"
  KEPT="${KEPT:-0}"
  NEW_ROWS=$(( KEPT - EXCLUDED_ROWS ))
  if (( KEPT >= MIN_KEPT && NEW_ROWS >= MIN_NEW_ROWS )); then
    break
  fi
  if (( WAIT_SECONDS <= 0 )); then
    if (( KEPT < MIN_KEPT )); then
      log "not enough kept rows yet: kept=$KEPT min=$MIN_KEPT"
    else
      log "not enough new rows after exclusion: kept=$KEPT excluded=$EXCLUDED_ROWS new=$NEW_ROWS min_new=$MIN_NEW_ROWS"
    fi
    exit 0
  fi
  NOW="$(date +%s)"
  if (( NOW - WAIT_START >= WAIT_SECONDS )); then
    log "wait expired before enough new rows: kept=$KEPT excluded=$EXCLUDED_ROWS new=$NEW_ROWS min_new=$MIN_NEW_ROWS"
    exit 0
  fi
  log "waiting for new rows: kept=$KEPT excluded=$EXCLUDED_ROWS new=$NEW_ROWS min_new=$MIN_NEW_ROWS"
  sleep "$SLEEP_SECONDS"
done
if [[ ! -s "$PARTIAL" ]]; then
  log "partial corpus missing or empty: $PARTIAL"
  exit 1
fi

mkdir -p "$ROOT"
CORPUS="$ROOT/mcb_corpus.snapshot.json"
PIPE_ROOT="$ROOT/source_pipeline"
INTAKE_DB="$ROOT/intake.sqlite"
MILL_ROOT="$ROOT/mill"

log "snapshotting kept=$KEPT excluded=$EXCLUDED_ROWS new=$NEW_ROWS from $PARTIAL into $CORPUS"
if [[ "$DRY_RUN" == "1" ]]; then
  printf 'DRY_RUN cp %q %q\n' "$PARTIAL" "$CORPUS"
else
  cp "$PARTIAL" "$CORPUS"
  python3 - "$ROOT" "$SOURCE_ROOT" "$KEPT" <<'PY'
import json, pathlib, sys, time
root, source_root, kept = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path("/tmp/rung1/current_leanmill_run.json")
p.parent.mkdir(parents=True, exist_ok=True)
json.dump({
    "name": "MCB partial microbatch",
    "machine": "Remote",
    "state": "running",
    "phase": "source_qualification_microbatch",
    "progress": f"qualifying a partial corpus snapshot with {kept} kept rows",
    "next_handoff": "bounded REPL-step mill if ready rows exist",
    "root": root,
    "source_root": source_root,
    "started_epoch": time.time(),
}, open(p, "w"), indent=2, sort_keys=True)
PY
fi

log "qualifying microbatch sources"
if [[ "$DRY_RUN" == "1" ]]; then
  printf 'DRY_RUN python3 scripts/public/control/leanmill/search/mcb_source_pipeline.py ...\n'
else
  python3 scripts/public/control/leanmill/search/mcb_source_pipeline.py \
    --corpus "$CORPUS" \
    --exclude "$EXCLUDE" \
    --root "$PIPE_ROOT" \
    --intake-db "$INTAKE_DB" \
    --max-rows "$MAX_ROWS" \
    --leansearch-limit "$LEANSEARCH_LIMIT" \
    --max-candidates-per-row "$MAX_CANDIDATES_PER_ROW" \
    $(if [[ "$INCLUDE_UNCLASSIFIED" == "1" ]]; then printf '%s' '--include-unclassified'; fi) \
    --summary "$PIPE_ROOT/summary.json"
fi

if [[ "$RUN_MILL" != "1" ]]; then
  log "RUN_MILL=0; stopping after source qualification"
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
json.dump({
    "name": "MCB partial microbatch drain",
    "machine": "Remote",
    "state": "running",
    "phase": "proof_execution_repl_step_parallel",
    "progress": f"{ready} ready rows from partial microbatch",
    "next_handoff": "governance gate or residual compiler",
    "root": mill_root,
    "source_root": root,
    "started_epoch": time.time(),
}, open(p, "w"), indent=2, sort_keys=True)
PY

log "launching $WORKERS bounded REPL-step worker(s) on $READY ready rows"
for w in $(seq 1 "$WORKERS"); do
  tmux new-session -d -s "gp225_mcb_microbatch_w${w}" \
    "cd $(pwd) && python3 scripts/public/control/leanmill/search/factory_mill.py \
      --from-intake \
      --intake-db '$INTAKE_DB' \
      --intake-limit '$INTAKE_LIMIT_PER_WORKER' \
      --worker-id 'mcb_microbatch_w${w}' \
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
