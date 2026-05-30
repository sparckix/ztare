#!/usr/bin/env bash
# Pull bulky LeanMill generated artifacts from the VPS into this local repo.
# This is separate from deploy/vps_pull.sh because queued_learning_work can be
# hundreds of MB and should not ride every routine membrane record pull.
set -euo pipefail
DRY=""; [ "${1:-}" = "-n" ] && DRY="--dry-run"
SSH_TGT="${ZTARE_VPS_SSH:?set ZTARE_VPS_SSH}"
KEY="${ZTARE_VPS_KEY:?set ZTARE_VPS_KEY}"
REMOTE_REPO="${ZTARE_VPS_REPO:-/home/ztare/figs_activist_loop}"
LOCAL_REPO="${ZTARE_LOCAL_REPO:-$(cd "$(dirname "$0")/.." && pwd)}"
SSH="ssh -i ${KEY} -o BatchMode=yes -o ConnectTimeout=20"
ROOT="analytics/public/leanmill/dashboard_data"
FAMILY_ROOT="analytics/public/leanmill/repair_families"
say(){ printf '\n== %s ==\n' "$*"; }
[ -f "$KEY" ] || { echo "FAIL: ssh key $KEY not found" >&2; exit 2; }
TS="$(date -u +%Y%m%dT%H%M%SZ)"
BK="${LOCAL_REPO}/.vps_pull_backup/${TS}_leanmill_artifacts"
mkdir -p "$BK/${ROOT}" "$BK/${FAMILY_ROOT}"
say "target vps=$SSH_TGT remote=$REMOTE_REPO -> local=$LOCAL_REPO"
say "remote LeanMill artifact sizes"
$SSH "$SSH_TGT" "cd '$REMOTE_REPO' && du -sh '$ROOT/queued_learning_work' '$ROOT/c_supply_batch_reports' 2>/dev/null || true"
say "backup local LeanMill artifact dirs"
for p in "$ROOT/queued_learning_work" "$ROOT/c_supply_batch_reports" "$FAMILY_ROOT"; do
  if [ -e "$LOCAL_REPO/$p" ]; then
    mkdir -p "$BK/$(dirname "$p")"
    cp -a "$LOCAL_REPO/$p" "$BK/$p" 2>/dev/null || true
  fi
done
echo "  backup: $BK"
say "rsync bulky family corpora, C-supply reports, and generated repair-family specs${DRY:+ — DRY-RUN}"
mkdir -p "$LOCAL_REPO/$ROOT" "$LOCAL_REPO/$FAMILY_ROOT"
rsync -az --partial --timeout=120 --contimeout=20 ${DRY} -e "$SSH" "$SSH_TGT:$REMOTE_REPO/$ROOT/queued_learning_work/" "$LOCAL_REPO/$ROOT/queued_learning_work/"
rsync -az --partial --timeout=120 --contimeout=20 ${DRY} -e "$SSH" "$SSH_TGT:$REMOTE_REPO/$ROOT/c_supply_batch_reports/" "$LOCAL_REPO/$ROOT/c_supply_batch_reports/"
rsync -az --partial --timeout=120 --contimeout=20 ${DRY} -e "$SSH" "$SSH_TGT:$REMOTE_REPO/$FAMILY_ROOT/" "$LOCAL_REPO/$FAMILY_ROOT/"
say "pull compact C-supply status/freeze artifacts${DRY:+ — DRY-RUN}"
rsync -az --partial --timeout=120 --contimeout=20 ${DRY} -e "$SSH" \
  --include='c_supply_batch*' \
  --include='leanmill_population_elo.*' \
  --include='leanmill_governance_sentinel_suite_latest.json' \
  --exclude='*' \
  "$SSH_TGT:$REMOTE_REPO/$ROOT/" "$LOCAL_REPO/$ROOT/"
say "DONE — LeanMill generated artifacts mirrored locally"
echo "Review with: git status --porcelain $ROOT | head -80"
echo "Backup: $BK"
