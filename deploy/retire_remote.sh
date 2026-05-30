#!/usr/bin/env bash
# ONE command from your laptop: ssh → cd → operator_retire → verify.
# You never type ssh/cd/payload/sig. Args required (no hardcoded
# target — a default would silently retire the wrong tick later).
#
# Usage (from the laptop):
#   bash deploy/retire_remote.sh <OWNER> <TICK_ROW> <REASON>
#
# Boundary unchanged: the actual sign still happens on the VPS via
# sudo→ztare_operator inside operator_retire.sh; this only removes the
# ssh/cd toil. Fail-loud: aborts on any dry-run/refusal upstream.
set -euo pipefail

VPS="${ZTARE_VPS_SSH:?set ZTARE_VPS_SSH}"
KEY="${ZTARE_VPS_KEY:?set ZTARE_VPS_KEY}"
REPO="${ZTARE_VPS_REPO:-figs_activist_loop}"

if [ $# -lt 3 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
  cat >&2 <<'USAGE'
usage: bash deploy/retire_remote.sh <OWNER> <TICK_ROW> <REASON>
  OWNER     e.g. codex:RD or agent:RD
  TICK_ROW  EXACT full F-row id (no substring)
  REASON    legacy_raw_propose_no_forecast_contract |
            legacy_audit_finding_no_forecast_contract |
            pre_lifecycle_bypass_debt
REFUSED: all three required — no default target.
USAGE
  exit 2
fi

# shellcheck disable=SC2029  (we WANT the args expanded locally)
ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=20 "$VPS" \
  "cd ~/$REPO && ZTARE_OFFICIAL_STORE=/srv/ztare_official_store bash deploy/operator_retire.sh $(printf '%q ' "$1" "$2" "$3")"
rc=$?
if [ $rc -ne 0 ]; then
  echo "" >&2
  echo "🛑 remote retire FAILED (rc=$rc) — see the VPS output above. NOT stamped." >&2
  exit $rc
fi
echo ""
echo "✅ remote retire chain completed. Verify NS on the VPS:"
echo "   ssh -i $KEY $VPS 'cd ~/$REPO && ZTARE_OFFICIAL_STORE=/srv/ztare_official_store RD_OWNER=$1 python3 scripts/public/control/rd_tick_brief.py | head -3'"
