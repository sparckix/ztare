#!/usr/bin/env bash
# Refresh the local LeanSearch factory dashboard data from the Remote machine.
#
# This is read-only with respect to the experiment: it recomputes rollups from
# existing factory artifacts on the Remote machine, then pulls the JSON snapshots locally.
# It does not run Lean.
set -euo pipefail

VPS="${ZTARE_VPS_SSH:-ztare@49.13.160.58}"
KEY="${ZTARE_VPS_KEY:-$HOME/.ssh/id_ed25519}"
RREPO="${ZTARE_VPS_REPO:-/home/ztare/figs_activist_loop}"
ROOT="${ZTARE_FACTORY_ROOT:-/tmp/rung1/factory_intake_full_drain_vps}"
INTAKE_DB="${ZTARE_FACTORY_INTAKE_DB:-/tmp/rung1/factory_intake_full_vps.sqlite}"
LOCAL_DIR="${ZTARE_FACTORY_DASHBOARD_DATA:-analytics/public/leanmill/dashboard_data}"
WATCH_SECONDS="${1:-}"

bounded_run() {
  local timeout_s="$1"
  shift
  "$@" &
  local pid=$!
  local elapsed=0
  while kill -0 "$pid" >/dev/null 2>&1; do
    if [ "$elapsed" -ge "$timeout_s" ]; then
      kill "$pid" >/dev/null 2>&1 || true
      wait "$pid" >/dev/null 2>&1 || true
      return 124
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  wait "$pid"
}

pull_remote() {
  local src="$1"
  local dst="$2"
  bounded_run 20 scp -i "$KEY" -o ConnectTimeout=8 -o ServerAliveInterval=4 -o ServerAliveCountMax=1 -q "$VPS:$src" "$dst" 2>/tmp/leanmill_dashboard_scp.err && return 0
  sleep 2
  bounded_run 20 scp -i "$KEY" -o ConnectTimeout=8 -o ServerAliveInterval=4 -o ServerAliveCountMax=1 -q "$VPS:$src" "$dst" 2>/tmp/leanmill_dashboard_scp.err && return 0
  printf 'WARN dashboard pull failed: %s -> %s (%s)\n' "$src" "$dst" "$(tail -1 /tmp/leanmill_dashboard_scp.err 2>/dev/null)" >&2
  return 0
}

remote_test() {
  bounded_run 10 ssh -i "$KEY" -o ConnectTimeout=8 -o ServerAliveInterval=4 -o ServerAliveCountMax=1 "$VPS" "test -f $1" >/dev/null 2>&1
}

refresh_once() {
  mkdir -p "$LOCAL_DIR"
  bounded_run 60 ssh -i "$KEY" -o ConnectTimeout=8 -o ServerAliveInterval=4 -o ServerAliveCountMax=1 "$VPS" "cd $RREPO && \
    ./venv/bin/python scripts/public/control/leanmill/search/factory_p0_rollup.py --root $ROOT --out $ROOT/p0_rollup_final.json >/dev/null && \
    ./venv/bin/python scripts/public/control/leanmill/search/factory_ops_timeseries.py --root $ROOT --intake-db $INTAKE_DB --bucket-seconds 120 --include-now --out $ROOT/ops_timeseries.json >/dev/null && \
    ./venv/bin/python scripts/public/control/leanmill/search/factory_status.py --root $ROOT --intake-db $INTAKE_DB --top-packets 4 --out $ROOT/status_final.json >/dev/null && \
    ./venv/bin/python scripts/public/control/leanmill/search/factory_scoreboard.py --root $ROOT --out $ROOT/scoreboard_final.json >/dev/null && \
    ./venv/bin/python scripts/public/control/leanmill/search/factory_residual_plan.py --root $ROOT --out $ROOT/residual_plan_final.json >/dev/null && \
    if [ -f /tmp/rung1/factory_source_all40/source_packet.json ]; then \
      ./venv/bin/python scripts/public/control/leanmill/search/source_quality_dashboard.py \
        --label all40_failed \
        --source-packet /tmp/rung1/factory_source_all40/source_packet.json \
        --static-filter /tmp/rung1/factory_source_all40/static_filter.json \
        --row-context-filter /tmp/rung1/factory_source_all40/row_context_filter.json \
        --out /tmp/rung1/factory_source_all40/source_quality.json >/dev/null; \
    fi" || printf 'WARN remote completed-run rollup refresh timed out or failed; using last pulled files\n' >&2
  pull_remote "$ROOT/p0_rollup_final.json" "$LOCAL_DIR/p0_rollup_final.json"
  pull_remote "$ROOT/ops_timeseries.json" "$LOCAL_DIR/ops_timeseries.json"
  pull_remote "$ROOT/status_final.json" "$LOCAL_DIR/status_final.json"
  pull_remote "$ROOT/scoreboard_final.json" "$LOCAL_DIR/scoreboard_final.json"
  pull_remote "$ROOT/residual_plan_final.json" "$LOCAL_DIR/residual_plan_final.json"
  if remote_test /tmp/rung1/factory_source_all40/source_quality.json; then
    pull_remote "/tmp/rung1/factory_source_all40/source_quality.json" "$LOCAL_DIR/source_quality_all40_failed.json"
  fi
  if ! bounded_run 25 ssh -i "$KEY" -o ConnectTimeout=8 -o ServerAliveInterval=4 -o ServerAliveCountMax=1 "$VPS" "python3 - <<'PY' > /tmp/rung1/leanmill_mcb_expansion_status.json
import json, pathlib, subprocess, time
roots = [
    pathlib.Path('/tmp/rung1/mcb_refill_dedup_after_expand100'),
    pathlib.Path('/tmp/rung1/mcb_refill_after_remaining'),
    pathlib.Path('/tmp/rung1/mcb_expand100'),
]
builders = subprocess.run(\"ps -Ao pid,ppid,stat,etime,command | grep build_module_context_benchmark.py | grep -v grep || true\", shell=True, text=True, capture_output=True).stdout.strip().splitlines()
payload = {'state': 'finished_or_idle', 'target_n': None, 'updated_epoch': time.time()}
for root in roots:
    progress = root / 'mcb_progress.json'
    corpus = root / 'mcb_corpus.json'
    if not progress.exists() and not corpus.exists():
        continue
    row = ''
    for candidate in builders:
        if str(root) in candidate:
            row = candidate
            break
    payload = {'state': 'running' if row else 'finished_or_idle', 'root': str(root), 'updated_epoch': time.time()}
    if row:
        parts = row.split(None, 4)
        payload.update({'pid': parts[0], 'elapsed': parts[3] if len(parts) > 3 else '', 'command': parts[4] if len(parts) > 4 else ''})
    if progress.exists():
        try:
            obj = json.load(open(progress))
            payload.update({
                'n': obj.get('kept'),
                'kept': obj.get('kept'),
                'scanned': obj.get('scanned'),
                'target_n': obj.get('target_n'),
                'scan_cap': obj.get('scan_cap'),
                'progress_state': obj.get('state'),
            })
        except Exception as e:
            payload['progress_error'] = repr(e)
    if corpus.exists() and payload.get('n') is None:
        try:
            obj = json.load(open(corpus))
            payload.update({'n': obj.get('n'), 'selection': obj.get('selection')})
        except Exception as e:
            payload.update({'corpus_error': repr(e)})
    break
print(json.dumps(payload, sort_keys=True))
PY"
  then
    printf 'WARN remote MCB expansion status refresh timed out or failed; using last pulled file\n' >&2
  fi
  if remote_test /tmp/rung1/leanmill_mcb_expansion_status.json; then
    pull_remote "/tmp/rung1/leanmill_mcb_expansion_status.json" "$LOCAL_DIR/mcb_expansion_status.json"
  fi
  if ! bounded_run 25 ssh -i "$KEY" -o ConnectTimeout=8 -o ServerAliveInterval=4 -o ServerAliveCountMax=1 "$VPS" "python3 - <<'PY' > /tmp/rung1/leanmill_source_conveyor_status.json
import json, pathlib, subprocess, time
pipe_candidates = [
    pathlib.Path('/tmp/rung1/mcb_refill_dedup_after_expand100/source_pipeline_220'),
    pathlib.Path('/tmp/rung1/mcb_refill_dedup_after_expand100/factory_watchdog/source_pipeline'),
    pathlib.Path('/tmp/rung1/mcb_expand100/factory_watchdog/source_pipeline'),
]
pipe_candidates = [p for p in pipe_candidates if p.exists()]
pipe_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
pipe = pipe_candidates[0] if pipe_candidates else pathlib.Path('/tmp/rung1/mcb_expand100/factory_watchdog/source_pipeline')
tmux = subprocess.run(\"tmux ls 2>/dev/null | grep -E 'gp225_mcb_refill220_source_pipeline|gp225_mcb_source_resume|gp225_mcb_factory_watchdog|gp225_mcb_static_fallback|gp225_mcb_row_context_fallback' || true\", shell=True, text=True, capture_output=True).stdout.strip().splitlines()
lean = subprocess.run(\"pgrep -af 'leansearch_candidate_static_filter|leansearch_static_filter_probe_|leansearch_row_context_filter|leansearch_row_context_' || true\", shell=True, text=True, capture_output=True).stdout.strip().splitlines()
fallback_probe = ''
static_filter = ''
context_probe = ''
for line in lean:
    if 'leansearch_candidate_static_filter.py' in line and 'pgrep' not in line:
        static_filter = line
    if 'leansearch_static_filter_probe_' in line and '/tmp/leansearch_static_filter_' in line and 'pgrep' not in line:
        fallback_probe = line
    if '/tmp/leansearch_row_context_' in line and 'pgrep' not in line:
        context_probe = line
phase = 'source_qualification'
if any('gp225_mcb_row_context_fallback' in s for s in tmux):
    phase = 'row_context_filter'
elif any('gp225_mcb_static_fallback' in s for s in tmux):
    phase = 'static_filter_fallback'
payload = {
  'state': 'running' if tmux else 'idle_or_finished',
  'root': str(pipe),
  'sessions': tmux,
  'lean_processes': lean,
  'updated_epoch': time.time(),
  'phase': phase,
  'next_handoff': 'intake_buffer_then_bounded_mill_if_ready_rows_exist',
}
sp = pipe / 'source_packet.json'
if sp.exists():
    try:
        obj = json.load(open(sp))
        payload['source_packet'] = {
          'row_count': obj.get('row_count'),
          'usable_candidate_total': obj.get('usable_candidate_total'),
          'status': obj.get('status'),
        }
    except Exception as e:
        payload['source_packet_error'] = repr(e)
summary = pipe / 'summary_resume.json'
if not summary.exists():
    summary = pipe / 'summary.json'
if summary.exists():
    try:
        obj = json.load(open(summary))
        payload['pipeline_summary'] = obj.get('summary') or {}
        if not any('gp225_mcb_static_fallback' in s or 'gp225_mcb_row_context_fallback' in s for s in tmux):
            payload['state'] = 'complete'
    except Exception as e:
        payload['pipeline_summary_error'] = repr(e)
fallback = pipe / 'static_filter_fallback.json'
if fallback.exists():
    try:
        obj = json.load(open(fallback))
        payload['static_filter_fallback'] = {
          'row_count': obj.get('row_count'),
          'resolved_total': obj.get('resolved_total'),
          'canary_ready_total': obj.get('canary_ready_total'),
          'fallback_per_row_used': obj.get('fallback_per_row_used'),
          'attempts': len(obj.get('fallback_per_row_attempts') or []),
        }
    except Exception as e:
        payload['static_filter_fallback_error'] = repr(e)
elif fallback_probe:
    import re
    m = re.search(r'probe_(\d+)\.lean', fallback_probe)
    payload['static_filter_fallback'] = {
      'state': 'running',
      'current_probe_index': int(m.group(1)) if m else None,
      'fallback_per_row_used': True,
    }
elif static_filter:
    payload['static_filter_fallback'] = {
      'state': 'running',
      'mode': 'static_filter',
      'current_probe_index': None,
      'fallback_per_row_used': False,
    }
context = pipe / 'row_context_filter_fallback.json'
if not context.exists():
    context = pipe / 'row_context_filter_fallback.partial.json'
if context.exists():
    try:
        obj = json.load(open(context))
        payload['row_context_fallback'] = {
          'row_count': obj.get('row_count'),
          'candidate_count': obj.get('candidate_count'),
          'row_context_ready_total': obj.get('row_context_ready_total'),
        }
    except Exception as e:
        payload['row_context_fallback_error'] = repr(e)
elif context_probe:
    payload['row_context_fallback'] = {
      'state': 'running',
      'current_file': pathlib.Path(context_probe.split()[-1]).name if context_probe.split() else '',
    }
print(json.dumps(payload, sort_keys=True))
PY"
  then
    printf 'WARN remote source conveyor status refresh timed out or failed; using last pulled file\n' >&2
  fi
  if remote_test /tmp/rung1/leanmill_source_conveyor_status.json; then
    pull_remote "/tmp/rung1/leanmill_source_conveyor_status.json" "$LOCAL_DIR/source_conveyor_status.json"
  fi
  if remote_test /tmp/rung1/current_leanmill_run.json; then
    pull_remote "/tmp/rung1/current_leanmill_run.json" "$LOCAL_DIR/current_leanmill_run.json"
  else
    rm -f "$LOCAL_DIR/current_leanmill_run.json"
  fi
  if ! bounded_run 25 ssh -i "$KEY" -o ConnectTimeout=8 -o ServerAliveInterval=4 -o ServerAliveCountMax=1 "$VPS" "python3 - <<'PY' > /tmp/rung1/leanmill_latest_source_buffer.json
import glob, json, pathlib, time
roots = []
for pat in [
    '/tmp/rung1/mcb_partial40_source_only_*',
    '/tmp/rung1/mcb_refill_dedup_after_expand100/source_pipeline_220',
    '/tmp/rung1/mcb_refill_dedup_after_expand100/factory_watchdog/source_pipeline',
    '/tmp/rung1/mcb_expand100/factory_watchdog/source_pipeline',
]:
    roots.extend(pathlib.Path(p) for p in glob.glob(pat))
roots = [p for p in roots if p.exists()]
def freshness(root):
    files = [
        root / 'row_context_filter.json',
        root / 'row_context_filter.partial.json',
        root / 'static_filter.json',
        root / 'source_packet.json',
        root / 'queue.json',
    ]
    mtimes = [p.stat().st_mtime for p in files if p.exists()]
    # Prefer fuller modern source buffers over older partial smoke buffers when
    # both are present; freshness breaks ties.
    richness = 0
    sp = root / 'source_packet.json'
    if sp.exists():
        try:
            obj = json.load(open(sp))
            richness = int(obj.get('row_count') or 0) * 1000000 + int(obj.get('usable_candidate_total') or 0)
        except Exception:
            richness = 0
    return (richness, max(mtimes) if mtimes else root.stat().st_mtime)
roots.sort(key=freshness, reverse=True)
payload = {'state': 'missing', 'updated_epoch': time.time()}
for root in roots:
    sp = root / 'source_packet.json'
    q = root / 'queue.json'
    sf = root / 'static_filter.json'
    rc = root / 'row_context_filter.json'
    partial = root / 'row_context_filter.partial.json'
    if not any(p.exists() for p in [sp, q, sf, rc, partial]):
        continue
    payload = {'state': 'present', 'root': str(root), 'updated_epoch': time.time()}
    if q.exists():
        try:
            obj = json.load(open(q))
            payload['queue_count'] = obj.get('source_discovery_queue_count')
        except Exception as e:
            payload['queue_error'] = repr(e)
    if sp.exists():
        try:
            obj = json.load(open(sp))
            payload['source_packet'] = {
                'row_count': obj.get('row_count'),
                'usable_candidate_total': obj.get('usable_candidate_total'),
                'exact_target_excluded_total': obj.get('exact_target_excluded_total'),
                'post_target_forbidden_total': obj.get('post_target_forbidden_total'),
                'status': obj.get('status'),
            }
        except Exception as e:
            payload['source_packet_error'] = repr(e)
    for label, path in [('static_filter', sf), ('row_context_filter', rc), ('row_context_partial', partial)]:
        if path.exists():
            try:
                obj = json.load(open(path))
                payload[label] = {
                    'row_count': obj.get('row_count'),
                    'canary_ready_total': obj.get('canary_ready_total'),
                    'row_context_ready_total': obj.get('row_context_ready_total'),
                    'candidate_count': obj.get('candidate_count'),
                }
            except Exception as e:
                payload[label + '_error'] = repr(e)
    break
print(json.dumps(payload, sort_keys=True))
PY"
  then
    printf 'WARN remote latest source buffer refresh timed out or failed; using last pulled file\n' >&2
  fi
  if remote_test /tmp/rung1/leanmill_latest_source_buffer.json; then
    pull_remote "/tmp/rung1/leanmill_latest_source_buffer.json" "$LOCAL_DIR/latest_source_buffer.json"
  fi
  ./venv/bin/python scripts/public/control/leanmill/search/source_quality_dashboard.py \
    --label mcb_remaining \
    --source-packet analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_SOURCE_PACKET.json \
    --static-filter analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_STATIC_FILTER.json \
    --row-context-filter analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json \
    --out "$LOCAL_DIR/source_quality_mcb_remaining.json" >/dev/null
  ./venv/bin/python scripts/public/control/leanmill/search/residual_family_source_planner.py \
    --source-packet analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_SOURCE_PACKET.json \
    --row-context-filter analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json \
    --residual-plan "$LOCAL_DIR/residual_plan_final.json" \
    --out "$LOCAL_DIR/residual_family_source_plan.json" >/dev/null
  ./venv/bin/python scripts/public/control/leanmill/search/factory_live_state.py \
    --data-dir "$LOCAL_DIR" \
    --out "$LOCAL_DIR/factory_live_state.json" >/dev/null
  ./venv/bin/python scripts/public/control/leanmill/search/factory_ops_insights.py \
    --data-dir "$LOCAL_DIR" \
    --out "$LOCAL_DIR/ops_insights.json" >/dev/null
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$LOCAL_DIR/last_refreshed_utc.txt"
  ./venv/bin/python - "$LOCAL_DIR" <<'PY'
import json, sys, time
from pathlib import Path

data = Path(sys.argv[1])

def read(name):
    p = data / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(errors="ignore"))
    except Exception:
        return {}

p0 = read("p0_rollup_final.json")
live = read("factory_live_state.json")
insights = read("ops_insights.json")
source = (
    read("source_quality_mcb_expand100_final_context.json")
    or read("source_quality_mcb_expand100_partial_context.json")
    or read("source_quality_mcb_expand100_static_fallback.json")
    or read("source_quality_mcb_remaining.json")
)
ops = read("ops_timeseries.json")

h = p0.get("headline") or {}
st = source.get("totals") or {}
sr = source.get("rates") or {}
summary = ops.get("summary") or {}
row = {
    "ts_epoch": int(time.time()),
    "verified_rows": int(h.get("verified_value_rows") or 0),
    "residual_rows": int(h.get("path_c_learning_rows") or 0),
    "pending_governance": int(h.get("pending_governance") or 0),
    "source_canary_ready_rows": int(st.get("canary_ready_rows") or 0),
    "source_target_ready_candidates": int(st.get("target_compatible_sources") or 0),
    "source_canary_ready_per_100_raw": sr.get("canary_ready_rows_per_100_raw_sources"),
    "mean_proof_cycle_s": ((summary.get("path_a_cycle_s") or {}).get("mean")),
    "seconds_per_factory_event": summary.get("seconds_per_factory_event"),
    "live_station": insights.get("current_live_station"),
    "completed_batch_bottleneck": insights.get("completed_batch_bottleneck"),
}
hist_path = data / "ops_history.json"
if hist_path.exists():
    try:
        hist = json.loads(hist_path.read_text(errors="ignore")).get("points") or []
    except Exception:
        hist = []
else:
    hist = []
if not hist or any(hist[-1].get(k) != row.get(k) for k in row if k != "ts_epoch"):
    hist.append(row)
hist = hist[-240:]
hist_path.write_text(json.dumps({
    "schema": "leanmill-ops-history-v1",
    "generated_at_epoch": int(time.time()),
    "points": hist,
}, indent=2, sort_keys=True) + "\n")
PY
  ./venv/bin/python - "$LOCAL_DIR" <<'PY'
import json, sys, time
from pathlib import Path

data = Path(sys.argv[1])
names = [
    "p0_rollup_final.json",
    "ops_timeseries.json",
    "residual_plan_final.json",
    "source_quality_mcb_expand100_final_context.json",
    "source_quality_mcb_expand100_partial_context.json",
    "source_quality_mcb_expand100_static_fallback.json",
    "source_quality_mcb_remaining.json",
    "source_quality_all40_failed.json",
    "residual_family_source_plan.json",
    "factory_live_state.json",
    "ops_insights.json",
    "ops_history.json",
]
payload = {}
for name in names:
    path = data / name
    if not path.exists():
        continue
    try:
        obj = json.loads(path.read_text(errors="ignore"))
    except Exception:
        continue
    payload[name] = obj
    payload[f"factory_dashboard_data/{name}"] = obj
payload["embedded_generated_at_epoch"] = int(time.time())
last_refreshed = data / "last_refreshed_utc.txt"
if last_refreshed.exists():
    payload["last_refreshed_utc"] = last_refreshed.read_text(errors="ignore").strip()
(data / "embedded_live_state.js").write_text(
    "window.LEANMILL_EMBEDDED_DATA = "
    + json.dumps(payload, sort_keys=True)
    + ";\n",
    encoding="utf-8",
)
PY
  echo "factory dashboard data refreshed: $(cat "$LOCAL_DIR/last_refreshed_utc.txt")"
}

if [ -n "$WATCH_SECONDS" ] && [ "$WATCH_SECONDS" != "0" ]; then
  while true; do
    refresh_once || exit 1
    sleep "$WATCH_SECONDS"
  done
else
  refresh_once
fi
