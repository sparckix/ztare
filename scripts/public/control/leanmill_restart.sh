#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${LEANMILL_PYTHON:-./venv/bin/python}"
SHUTDOWN_SCRIPT="${LEANMILL_SHUTDOWN_SCRIPT:-${SCRIPT_DIR}/leanmill_shutdown.py}"
WATCHDOG_SCRIPT="${LEANMILL_WATCHDOG_SCRIPT:-${SCRIPT_DIR}/leanmill_watchdog.py}"
RESTART_GATE_SCRIPT="${LEANMILL_RESTART_GATE_SCRIPT:-${SCRIPT_DIR}/leanmill_restart_gate.py}"
WATCHDOG_SESSION="${LEANMILL_WATCHDOG_SESSION:-leanmill_watchdog}"

POLICY_PROFILE="${LEANMILL_POLICY_PROFILE:-}"
WORKER_HEARTBEAT_STALE_S="${LEANMILL_WORKER_HEARTBEAT_STALE_S:-}"
REASON="${LEANMILL_RESTART_REASON:-reload latest LeanMill control code}"
FORCE_CLEAR_SHUTDOWN_MARKER="${LEANMILL_FORCE_CLEAR_SHUTDOWN_MARKER:-0}"

PATH_DEFAULTS="$(${PYTHON_BIN} - "${SCRIPT_DIR}" <<'PY'
import sys
from pathlib import Path
script_dir = Path(sys.argv[1])
sys.path.insert(0, str(script_dir))
from leanmill_paths import DATA_DIR
print(str(Path(DATA_DIR) / "leanmill_shutdown_requested.json"))
PY
)"
SHUTDOWN_MARKER="${LEANMILL_SHUTDOWN_MARKER:-$(printf '%s\n' "${PATH_DEFAULTS}" | sed -n '1p')}"

if [[ -z "${POLICY_PROFILE}" || -z "${WORKER_HEARTBEAT_STALE_S}" ]]; then
  POLICY_DEFAULTS="$(${PYTHON_BIN} - "${SCRIPT_DIR}" <<'PY'
import json
import sys
from pathlib import Path
script_dir = Path(sys.argv[1])
sys.path.insert(0, str(script_dir))
try:
    from leanmill_paths import FACTORY_POLICY
    policy = json.loads(Path(FACTORY_POLICY).read_text(errors="ignore"))
except Exception:
    policy = {}
ops = policy.get("operations") if isinstance(policy, dict) else {}
if not isinstance(ops, dict):
    ops = {}
print(str(ops.get("restart_policy_profile") or "supervised_24x7"))
print(str(ops.get("restart_worker_heartbeat_stale_s") or 900))
PY
)"
  if [[ -z "${POLICY_PROFILE}" ]]; then
    POLICY_PROFILE="$(printf '%s\n' "${POLICY_DEFAULTS}" | sed -n '1p')"
  fi
  if [[ -z "${WORKER_HEARTBEAT_STALE_S}" ]]; then
    WORKER_HEARTBEAT_STALE_S="$(printf '%s\n' "${POLICY_DEFAULTS}" | sed -n '2p')"
  fi
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --policy-profile)
      POLICY_PROFILE="$2"
      shift 2
      ;;
    --reason)
      REASON="$2"
      shift 2
      ;;
    --worker-heartbeat-stale-s)
      WORKER_HEARTBEAT_STALE_S="$2"
      shift 2
      ;;
    --force-clear-shutdown-marker)
      FORCE_CLEAR_SHUTDOWN_MARKER=1
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "${FORCE_CLEAR_SHUTDOWN_MARKER}" != "1" ]]; then
  echo "refusing restart without --force-clear-shutdown-marker; use leanmill_shutdown.py for stop-only drains" >&2
  exit 2
fi

GATE_ARGS=(
  "--policy-profile" "${POLICY_PROFILE}"
  "--shutdown-marker" "${SHUTDOWN_MARKER}"
)
if [[ "${FORCE_CLEAR_SHUTDOWN_MARKER}" == "1" ]]; then
  GATE_ARGS+=("--force-clear-shutdown-marker")
fi
"${PYTHON_BIN}" "${RESTART_GATE_SCRIPT}" "${GATE_ARGS[@]}"

"${PYTHON_BIN}" "${SHUTDOWN_SCRIPT}" --reason "${REASON}" --operator restart_wrapper

WATCHDOG_ARGS="--daemon --policy-profile ${POLICY_PROFILE} --worker-heartbeat-stale-s ${WORKER_HEARTBEAT_STALE_S}"
if [[ "${FORCE_CLEAR_SHUTDOWN_MARKER}" == "1" ]]; then
  WATCHDOG_ARGS="${WATCHDOG_ARGS} --clear-shutdown-marker --force-clear-shutdown-marker"
fi

tmux new-session -d -s "${WATCHDOG_SESSION}" \
  "${PYTHON_BIN} ${WATCHDOG_SCRIPT} ${WATCHDOG_ARGS}"

echo "LeanMill restart requested: policy_profile=${POLICY_PROFILE} watchdog_session=${WATCHDOG_SESSION} force_clear_shutdown_marker=${FORCE_CLEAR_SHUTDOWN_MARKER}"
