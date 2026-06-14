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

say "5b. REPL SETUP + toolchain PARITY — the vendored repl (vendor/lean_repl) is gitignored and NOT in the rsync"
say "    allowlist, so a fresh box / the VPS has NO repl source. This step FETCHES it (clones the pinned upstream"
say "    commit when absent) and builds it to the ACTIVE substrate's toolchain BEFORE the preflight asserts it."
say "    MECHANIZES the dead-instrument RCA: a substrate that moved forward (v4.29 → v4.30) leaves a stale repl"
say "    ABI-dead over it, so the warm-REPL compile path silently falls back to a cold 'lake env lean' reload per"
say "    probe and every hand-guessed timeout false-fails. The repl has no deps ⇒ fast 'lake build' (no Mathlib"
say "    recompile), idempotent (no-op when matched), and ends with a live PersistentLean calibration. Substrate"
say "    = ZTARE_PREFLIGHT_REQUIRE (comma-sep) if set, else ztare_proofs when present; skipped only if neither."
_rp_subs="${ZTARE_PREFLIGHT_REQUIRE:-}"
if [ -z "$_rp_subs" ] && [ -f "$REPO/ztare_proofs/lean-toolchain" ]; then _rp_subs="ztare_proofs"; fi
if [ -n "$_rp_subs" ]; then
  _rp_args=""
  for _s in ${_rp_subs//,/ }; do _rp_args="$_rp_args --substrate $_s"; done
  PYTHONPATH="$REPO:$REPO/src" "$PY" scripts/public/control/leanmill/repl_parity.py $_rp_args
else
  echo "WARN: no Lean substrate (ZTARE_PREFLIGHT_REQUIRE unset and ztare_proofs/ absent) — skipping repl setup."
fi

say "6. Node preflight — INSTRUMENT calibration (the dead-REPL RCA guard). Asserts the"
say "   vendored repl binary's toolchain MATCHES a Mathlib-built project AND PersistentLean"
say "   actually loads Mathlib. Step 5's lake-env-lean uses the project toolchain and would"
say "   NOT catch a vendored-repl/oleans mismatch — the silent empty-env that voided runs."
say "   HARD-fails (abort) if no live REPL pair; warns on a dead embedder / missing providers."
say "   Set ZTARE_PREFLIGHT_REQUIRE=ztare_proofs (comma-sep for >1) to assert the repl is live over the"
say "   ACTIVE substrate(s) the node solves over — closes the 'any project matches' toolchain-drift slip"
say "   (do this once the node's repl is rebuilt at the substrate's toolchain, e.g. v4.30 for ztare_proofs)."
_pf_req=""
if [ -n "${ZTARE_PREFLIGHT_REQUIRE:-}" ]; then
  for _s in ${ZTARE_PREFLIGHT_REQUIRE//,/ }; do _pf_req="$_pf_req --require $_s"; done
fi
PYTHONPATH="$REPO:$REPO/src" "$PY" scripts/public/control/leanmill/node_preflight.py --soft-ok $_pf_req

say "6b. Python CARRIER deps — INSTALL (mechanized node PARITY, not just verify). The SMT/spectral carriers"
say "    (z3-solver, cvc5, sympy, numpy) MUST be in THIS venv or every exogenous move + the carrier preflight"
say "    (preflight_carriers.assert_carriers_live) fabricates a fail-closed null. The deploy previously only"
say "    VERIFIED these — a rebuilt venv missing z3/cvc5 passed silently until a run hit it (2026-06-10). Install"
say "    requirements.txt into the venv idempotently so a freshly-spun node has parity. SKIP_PY_DEPS=1 to skip."
if [ "${SKIP_PY_DEPS:-0}" != "1" ]; then
  if [ -f "$REPO/requirements.txt" ]; then
    "$PY" -m pip install -q -r "$REPO/requirements.txt" \
      || { echo "ERROR: 'pip install -r requirements.txt' FAILED — exogenous carriers would be DEAD"; exit 1; }
  else
    "$PY" -m pip install -q "sympy>=1.14" "z3-solver>=4.12" "cvc5>=1.2" "numpy>=2.0" \
      || { echo "ERROR: carrier-dep pip install FAILED — exogenous carriers would be DEAD"; exit 1; }
  fi
  echo "OK: carrier deps present in $PY"
else
  echo "SKIP_PY_DEPS=1 — skipping carrier pip install (venv assumed pre-provisioned)"
fi

say "7. Solver-backend POSITIVE CONTROLS — assert the SMT/spectral deps actually COMPUTE (not just"
say "   import), so a mis-provisioned box fails LOUD instead of turning a move into a silent inert"
say "   stub. numpy (functor_lift) + z3 (cross-vote/nlsat) + cvc5 (abduce, in requirements.txt) REQUIRED;"
say "   sdp/cvxpy (multivariate SOS, edge #2 — auto-installed via requirements.txt above) + Isabelle"
say "   (sledgehammer) are ADVISORY (their moves fail-close to None), reported but non-fatal. FUTURE NODES:"
say "   a new transport carrier = (dep in requirements.txt → installed by step 6b) + (a check_* in"
say "   verify_solver_backends.py + a _check_* in preflight_carriers.py) — that is the whole mechanization."
PYTHONPATH="$REPO:$REPO/src" "$PY" scripts/public/control/verify_solver_backends.py --require cvc5

say "8. Isabelle/HOL (MOVE_SLEDGEHAMMER) — GATED provisioning for node parity. Heavyweight (~1.5GB download +"
say "   HOL heap build) and the move is default-OFF + fail-closed, so it is OPT-IN: set PROVISION_ISABELLE=1 to"
say "   provision it the SAME mechanized way on every node (stage the tarball via ISABELLE_TARBALL to skip the"
say "   download). Default: skipped (sledgehammer stays a silent no-op — never a false closure)."
if [ "${PROVISION_ISABELLE:-0}" = "1" ]; then
  bash "$REPO/deploy/prepare_isabelle_server.sh" \
    || { echo "ERROR: Isabelle provisioning FAILED (PROVISION_ISABELLE=1)"; exit 1; }
  echo "OK: Isabelle provisioned — export ZTARE_ISABELLE_SERVER=http://127.0.0.1:8080 to enable sledgehammer"
else
  echo "PROVISION_ISABELLE unset — Isabelle/sledgehammer NOT provisioned (default; set =1 on a node that needs it)"
fi

say "Lean backend preparation complete"
