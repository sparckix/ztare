#!/usr/bin/env bash
# retire_uncloseable_tick.sh — one-shot operator-signed C4 tick_retire.
#
# WHY THIS EXISTS: a tick whose frozen forecast contract was lost
# (e.g. the untracked analytics/public/forecast_pool/contracts/<id>.json
# wiped by a git clean/reset before close — see task #54) can NEVER be
# cleanly closed. The membrane-sanctioned terminal is a chain-valid,
# OPERATOR-signed tick_retire. The operator key is OS-fenced to the
# `ztare_operator` user ON THE VPS (mode 0400) — that separation IS the
# gate; this script does not weaken it, it only removes the multi-step
# copy-paste toil (fresh-TS / sign-as-ztare_operator / submit-as-ztare).
#
# RUN FROM: your Mac (it SSHes to the VPS and does the rest there).
#
# Usage:
#   deploy/retire_uncloseable_tick.sh [-t TICK_ROW] [-r REASON] [-o OWNER]
#                                     [-H user@host] [-k ssh_key] [-R vps_repo]
# Every flag also has an env fallback (TICK_ROW / REASON / OWNER /
# ZTARE_VPS_SSH / ZTARE_VPS_KEY / ZTARE_VPS_REPO) and a sane default.
# Fail-loud, never silent. Ends with the chain verification.
set -euo pipefail

TICK_ROW="${TICK_ROW:-F-NS-BKM-FAITHFUL-ENCODING-JUDGE-VALIDATE-20260518}"
REASON="${REASON:-legacy_raw_propose_no_forecast_contract}"
OWNER="${OWNER:-${RD_OWNER:-agent:RD}}"
SSH_TGT="${ZTARE_VPS_SSH:?set ZTARE_VPS_SSH}"
KEY="${ZTARE_VPS_KEY:?set ZTARE_VPS_KEY}"
REMOTE_REPO="${ZTARE_VPS_REPO:-/home/ztare/figs_activist_loop}"
# propose.py picks local-enforce ONLY when ZTARE_OFFICIAL_STORE points
# at the real daemon-owned store (else STORE defaults to ~/ztare_
# official_store ⇒ a sandbox ⇒ observe/DRY-RUN that never counts).
OFFICIAL_STORE="${ZTARE_OFFICIAL_STORE:-/srv/ztare_official_store}"

usage(){ sed -n '13,21p' "$0"; exit "${1:-0}"; }
while getopts ":t:r:o:H:k:R:h" opt; do
  case "$opt" in
    t) TICK_ROW="$OPTARG" ;;
    r) REASON="$OPTARG" ;;
    o) OWNER="$OPTARG" ;;
    H) SSH_TGT="$OPTARG" ;;
    k) KEY="$OPTARG" ;;
    R) REMOTE_REPO="$OPTARG" ;;
    h) usage 0 ;;
    \?) echo "FAIL: unknown flag -$OPTARG" >&2; usage 2 ;;
    :) echo "FAIL: -$OPTARG needs an argument" >&2; usage 2 ;;
  esac
done

SSH="ssh -i ${KEY} -o BatchMode=yes -o ConnectTimeout=20"
say(){ printf '\n== %s ==\n' "$*"; }

[ -f "$KEY" ] || { echo "FAIL: ssh key not found: $KEY" >&2; exit 2; }
[ -n "$TICK_ROW" ] && [ -n "$REASON" ] && [ -n "$OWNER" ] \
  || { echo "FAIL: TICK_ROW/REASON/OWNER must all be non-empty" >&2; exit 2; }

say "target"
echo "  vps        : $SSH_TGT"
echo "  repo (vps) : $REMOTE_REPO"
echo "  tick_row   : $TICK_ROW"
echo "  reason     : $REASON"
echo "  owner      : $OWNER"

say "sign (as ztare_operator) + submit (as ztare) + verify — all on the VPS"
# Non-secret params are substituted locally; TS/PAYLOAD/SIG are computed
# REMOTELY (signing must happen where the OS-fenced key lives). Remote-only
# shell vars are \$-escaped so they evaluate on the VPS, not here.
$SSH "$SSH_TGT" bash -s <<EOF
set -euo pipefail
cd "$REMOTE_REPO"

# Force propose.py into local-enforce against the REAL daemon store
# (not the ~/ztare_official_store sandbox that yields observe/DRY-RUN).
export ZTARE_OFFICIAL_STORE="$OFFICIAL_STORE"
unset ZTARE_MEMBRANE_OBSERVE ZTARE_VERIFICATOR_SSH 2>/dev/null || true
[ -d "\$ZTARE_OFFICIAL_STORE" ] || { echo "FAIL: official store \$ZTARE_OFFICIAL_STORE not found on VPS" >&2; exit 3; }

TS="\$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
PAYLOAD="${OWNER}|${TICK_ROW}|${REASON}|\${TS}"
echo "payload: \${PAYLOAD}"

SIGN_PY="$REMOTE_REPO/deploy/operator_sign.py"
[ -f "\$SIGN_PY" ] || { echo "FAIL: \$SIGN_PY not found on VPS (sync the repo)" >&2; exit 3; }

# Step 1 — operator signature. sudo -u ztare_operator is the ONLY identity
# that can read /srv/ztare_operator_keys/operator_ed25519.key (ztare has
# NOPASSWD sudo). Invoke via python3 + ABSOLUTE path: sudo resolves a bare
# command through secure_path (not cwd), so a relative path => "command
# not found". Running as any other user => permission denied = the C4 gate.
SIGLINE="\$(sudo -u ztare_operator python3 "\$SIGN_PY" "\${PAYLOAD}")"
echo "\${SIGLINE}"
SIG="\$(printf '%s\n' "\${SIGLINE}" | sed -n 's/^SIG_HEX=//p')"
if [ -z "\${SIG}" ]; then
  echo "FAIL: operator_sign produced no SIG_HEX (key unreadable / wrong user / refused)" >&2
  exit 3
fi

# Step 2 — submit the retire as the plain agent identity (ztare is ACL'd to
# write the daemon inbox; the daemon gates + stamps it if chain-valid).
python3 scripts/public/control/admin_retire_uncloseable_tick.py \
  --owner "${OWNER}" --tick-row "${TICK_ROW}" --reason "${REASON}" \
  --ts "\${TS}" --operator-sig "\${SIG}"

# Step 3 — verification: the daemon only appends to the stamped ledger when
# a transition is chain-valid + verdict=pass. Prove the tick_retire landed.
echo
echo "== VERIFY (chain-valid stamped tick_retire) =="
sudo -u ztare_verify grep -h "${TICK_ROW}" \
  /srv/ztare_official_store/official/transitions.stamped.jsonl 2>/dev/null \
  | python3 -c "
import sys, json
rows=[json.loads(l) for l in sys.stdin if l.strip()]
ret=[r for r in rows if r.get('transition_type')=='tick_retire']
if ret:
    r=ret[-1]
    print('PASS: chain-valid tick_retire stamped for ${TICK_ROW}')
    print('  ts        =', r.get('ts'))
    print('  reason    =', r.get('reason'))
    print('  state_hash=', r.get('official_state_hash'))
    sys.exit(0)
print('FAIL: NO tick_retire row in the stamped ledger for ${TICK_ROW}', file=sys.stderr)
print('      (rows seen: %s)' % sorted({x.get(\"transition_type\") for x in rows}), file=sys.stderr)
sys.exit(4)
"
EOF

say "DONE — tick retired and chain-verified"
echo "Tell the active RD agent; it will open a fresh membrane-FIRST NS tick"
echo "(its contract is now durably chain-bound by the #54 daemon fix)."
