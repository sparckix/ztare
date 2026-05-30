#!/usr/bin/env bash
# C4 operator-signed tick retire — one-shot, VPS-only.
#
# Does NOT bypass the boundary: STEP 2 is `sudo -u ztare_operator
# operator_sign.py`, which only succeeds for the operator identity
# (the agent cannot read the operator key; sudo will deny it). The
# script just removes the STORE footgun + copy-paste toil.
#
# It forces ZTARE_OFFICIAL_STORE=/srv/ztare_official_store so propose
# resolves to LOCAL-ENFORCE (authoritative), and HARD-REFUSES if the
# submission would be observe/dry-run (no more silent dry-runs).
#
# Usage (on the VPS, as the operator user with sudo→ztare_operator):
#   bash deploy/operator_retire.sh <OWNER> <TICK_ROW> <REASON>
# All three are REQUIRED — no hardcoded target (a default would
# silently retire the wrong tick on a later bare run). REASON must be
# one of the admin_retire enum.
set -euo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"

if [ $# -lt 3 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
  cat >&2 <<'USAGE'
usage: bash deploy/operator_retire.sh <OWNER> <TICK_ROW> <REASON>
  OWNER     e.g. codex:RD or agent:RD
  TICK_ROW  the EXACT full F-row id to retire (no substring)
  REASON    one of: legacy_raw_propose_no_forecast_contract
                     legacy_audit_finding_no_forecast_contract
                     pre_lifecycle_bypass_debt
REFUSED: all three args are required — no default target (a hardcoded
default would silently retire the wrong tick on a later bare run).
USAGE
  exit 2
fi
OWNER="$1"
TROW="$2"
REASON="$3"

export ZTARE_OFFICIAL_STORE=/srv/ztare_official_store
unset ZTARE_MEMBRANE_OBSERVE 2>/dev/null || true

if [ ! -d "$ZTARE_OFFICIAL_STORE" ]; then
  echo "ABORT: $ZTARE_OFFICIAL_STORE not present — not the VPS authority host." >&2
  exit 2
fi
if python3 -c 'import os,sys; sys.exit(0 if not os.access("/srv/ztare_official_store", os.W_OK) else 1)'; then
  : # good: this user CANNOT write the store ⇒ propose → local-enforce
else
  echo "ABORT: this user CAN write $ZTARE_OFFICIAL_STORE — propose would NOT be authoritative (the daemon must be the sole writer). Run as the unprivileged agent identity, not root." >&2
  exit 2
fi

AR=scripts/public/control/admin_retire_uncloseable_tick.py

echo "== STEP 1: derive canonical payload (nothing submitted) =="
STEP1="$(python3 "$AR" --owner "$OWNER" --tick-row "$TROW" --reason "$REASON" 2>&1 || true)"
PAYLOAD="$(printf '%s\n' "$STEP1" | sed -n 's/^  payload: //p' | head -1)"
if [ -z "$PAYLOAD" ]; then
  echo "ABORT: could not parse payload from STEP 1 output:" >&2
  printf '%s\n' "$STEP1" >&2
  exit 2
fi
TS="${PAYLOAD##*|}"
echo "payload : $PAYLOAD"
echo "ts      : $TS"

echo "== STEP 2: operator signs (sudo→ztare_operator; key agent-unreadable) =="
SIGOUT="$(sudo -u ztare_operator python3 deploy/operator_sign.py "$PAYLOAD" 2>&1 || true)"
SIG="$(printf '%s\n' "$SIGOUT" | sed -n 's/^SIG_HEX=//p' | head -1)"
if [ -z "$SIG" ]; then
  echo "ABORT: operator_sign produced no SIG_HEX (are you the operator with sudo→ztare_operator? the agent CANNOT be — that is the boundary):" >&2
  printf '%s\n' "$SIGOUT" >&2
  exit 2
fi
echo "sig     : ${SIG:0:24}... (len ${#SIG})"

echo "== STEP 3: submit signed tick_retire (authoritative) =="
OUT="$(python3 "$AR" --owner "$OWNER" --tick-row "$TROW" --reason "$REASON" --ts "$TS" --operator-sig "$SIG" 2>&1 || true)"
printf '%s\n' "$OUT"
if printf '%s\n' "$OUT" | grep -q '"OBSERVE_ONLY"\|"mode": "observe"\|DRY-RUN'; then
  echo "" >&2
  echo "🛑 ABORT: submission ran in OBSERVE/dry-run — NOT official. The STORE/enforce path is still wrong; do not treat this as done." >&2
  exit 3
fi
if printf '%s\n' "$OUT" | grep -q 'RETIRE NOT STAMPED\|quarantine'; then
  echo "" >&2
  echo "🛑 daemon REFUSED the retire (see failed[] above). NOT stamped." >&2
  exit 1
fi
echo ""
echo "✅ operator-signed tick_retire submitted on the AUTHORITATIVE path."
echo "   Verify NS unblocks:  RD_OWNER=$OWNER python3 scripts/public/control/rd_tick_brief.py | head -3"
