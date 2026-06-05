#!/usr/bin/env bash
# Prepare the Lean backend stack used by the governed proof-search
# harness on a fresh server.
#
# This is the deploy-level entrypoint. It installs/checks the small OS
# prerequisites (`unzip` and `ripgrep` when apt/sudo are available), builds the pinned
# Lean sandbox backend artifacts, ensures Zipperposition is present,
# and then runs the parity probe with backend readiness required.
#
# Usage:
#   bash deploy/prepare_lean_backends.sh
#   TIMEOUT=1800 SKIP_OS_DEPS=1 bash deploy/prepare_lean_backends.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TIMEOUT="${TIMEOUT:-1800}"
SKIP_OS_DEPS="${SKIP_OS_DEPS:-0}"

say() { echo "== $* =="; }

cd "$REPO"

if [ -x "$REPO/venv/bin/python" ]; then
  PY="$REPO/venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi

say "1. OS prerequisite check"
missing_os_deps=()
if command -v unzip >/dev/null 2>&1; then
  echo "OK: unzip present ($(command -v unzip))"
else
  missing_os_deps+=(unzip)
fi
if command -v rg >/dev/null 2>&1; then
  echo "OK: ripgrep present ($(command -v rg))"
else
  missing_os_deps+=(ripgrep)
fi

if [ "${#missing_os_deps[@]}" -gt 0 ] && [ "$SKIP_OS_DEPS" = "1" ]; then
  echo "WARN: missing OS deps: ${missing_os_deps[*]}; continuing because SKIP_OS_DEPS=1"
elif [ "${#missing_os_deps[@]}" -gt 0 ] && command -v apt-get >/dev/null 2>&1 && command -v sudo >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${missing_os_deps[@]}"
  echo "OK: installed OS deps: ${missing_os_deps[*]}"
elif [ "${#missing_os_deps[@]}" -gt 0 ] && command -v apt-get >/dev/null 2>&1 && [ "$(id -u)" = "0" ]; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${missing_os_deps[@]}"
  echo "OK: installed OS deps: ${missing_os_deps[*]}"
elif [ "${#missing_os_deps[@]}" -gt 0 ]; then
  echo "WARN: missing OS deps and no apt/sudo path: ${missing_os_deps[*]}"
fi

say "2. Python helper self-test"
"$PY" scripts/public/control/prepare_lean_backends.py --self-test
"$PY" scripts/public/control/lean_env_parity.py --self-test

say "3. Build Lean backend artifacts"
"$PY" scripts/public/control/prepare_lean_backends.py --timeout "$TIMEOUT"

say "4. Verify Lean backend readiness"
"$PY" scripts/public/control/lean_env_parity.py --timeout 120 --require-backends

say "5. Solver-lane self-check (elan resolves, solver modules import, trivial proof"
say "   compiles, sorry proof is rejected) — fail-loud before any node solves"
PYTHONPATH="$REPO:$REPO/src" "$PY" scripts/public/control/leanmill/solver_lane_worker.py selfcheck

say "6. Node preflight — INSTRUMENT calibration (the dead-REPL RCA guard). Asserts the"
say "   vendored repl binary's toolchain MATCHES a Mathlib-built project AND PersistentLean"
say "   actually loads Mathlib. Step 5's lake-env-lean uses the project toolchain and would"
say "   NOT catch a vendored-repl/oleans mismatch — the silent empty-env that voided runs."
say "   HARD-fails (abort) if no live REPL pair; warns on a dead embedder / missing providers."
PYTHONPATH="$REPO:$REPO/src" "$PY" scripts/public/control/leanmill/node_preflight.py --soft-ok

say "Lean backend preparation complete"
