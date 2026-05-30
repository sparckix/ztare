#!/usr/bin/env bash
# vps_pull.sh — REVERSE sync: pull the authoritative research record
# FROM the VPS INTO this local git repo. Counterpart of vps_update.sh
# (which only pushes local→VPS). The membrane lifecycle runs on the
# VPS (local-enforce); the daemon materializes official F-rows and
# ticks append ledgers/manifests THERE, so the real record is on the
# VPS — this brings it home so it is not lost. JUDICIOUS: only the
# curated deploy/vps_pull_files.txt + a read-only snapshot of the
# daemon-owned official store chain (agent-unwritable; the single most
# important artifact). NEVER pulls src/ or the 33GB tree.
#
# Run from this Mac:  deploy/vps_pull.sh [-n]   (-n = rsync dry-run)
# Safety: every local file about to change is backed up to
# .vps_pull_backup/<ts>/ first — no data loss in EITHER direction.
set -euo pipefail

DRY=""; [ "${1:-}" = "-n" ] && DRY="--dry-run"
SSH_TGT="${ZTARE_VPS_SSH:?set ZTARE_VPS_SSH}"
KEY="${ZTARE_VPS_KEY:?set ZTARE_VPS_KEY}"
REMOTE_REPO="${ZTARE_VPS_REPO:-/home/ztare/figs_activist_loop}"
LOCAL_REPO="${ZTARE_LOCAL_REPO:-$(cd "$(dirname "$0")/.." && pwd)}"
SSH="ssh -i ${KEY} -o BatchMode=yes -o ConnectTimeout=20"
FILES="${LOCAL_REPO}/deploy/vps_pull_files.txt"
say(){ printf '\n== %s ==\n' "$*"; }

[ -f "$KEY" ]   || { echo "FAIL: ssh key $KEY not found" >&2; exit 2; }
[ -f "$FILES" ] || { echo "FAIL: $FILES missing" >&2; exit 2; }

say "target  vps=$SSH_TGT  remote=$REMOTE_REPO  ->  local=$LOCAL_REPO"

say "1. timestamped backup of local copies about to change"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
BK="${LOCAL_REPO}/.vps_pull_backup/${TS}"
mkdir -p "$BK"
while read -r p; do
  case "$p" in ''|\#*) continue;; esac
  if [ -e "${LOCAL_REPO}/${p}" ]; then
    mkdir -p "$BK/$(dirname "$p")"
    cp -a "${LOCAL_REPO}/${p}" "$BK/${p}" 2>/dev/null || true
  fi
done < "$FILES"
echo "  backup: $BK"

say "2. rsync VPS → local (curated list${DRY:+ — DRY-RUN})"
rsync -az ${DRY} --files-from="$FILES" -e "$SSH" \
  "$SSH_TGT:$REMOTE_REPO/" "$LOCAL_REPO/" | tail -8

say "3. snapshot the daemon-owned OFFICIAL STORE chain (read-only archival)"
# Agent cannot write the official store; this is the authoritative,
# daemon-signed transition chain + the frozen legacy manifest. Saved
# under a clearly-labelled snapshot dir — NOT the live store, never
# fed back as authority; pure disaster-recovery copy.
SNAP="${LOCAL_REPO}/analytics/public/official_store_snapshot"
mkdir -p "$SNAP"
if [ -z "$DRY" ]; then
  # #61: THIN fetch of the DAEMON-PRODUCED export bundle. The daemon
  # refreshes /srv/ztare_official_store/export/{transitions.stamped.
  # jsonl,F_rows.jsonl,last_close.json} on every stamped tick_close
  # (commit_membrane_daemon #61) — so this is just a copy of what the
  # AUTHORITY already exported, not the agent curating it. Falls back
  # to the live official/ path if the export bundle is not present yet
  # (pre-#61 deploy / no close since deploy).
  _src_dir=/srv/ztare_official_store/export
  $SSH "$SSH_TGT" "sudo -u ztare_verify test -f ${_src_dir}/transitions.stamped.jsonl" 2>/dev/null \
    || _src_dir=/srv/ztare_official_store/official
  $SSH "$SSH_TGT" "sudo -u ztare_verify cat ${_src_dir}/transitions.stamped.jsonl 2>/dev/null" \
    > "${SNAP}/transitions.stamped.jsonl.tmp" \
    && mv "${SNAP}/transitions.stamped.jsonl.tmp" "${SNAP}/transitions.stamped.jsonl" \
    && echo "  official chain (${_src_dir##*/}): $(wc -l < "${SNAP}/transitions.stamped.jsonl" | tr -d ' ') rows"
  $SSH "$SSH_TGT" "sudo -u ztare_verify cat ${_src_dir}/F_rows.jsonl 2>/dev/null" \
    > "${SNAP}/F_rows.jsonl.tmp" 2>/dev/null \
    && mv "${SNAP}/F_rows.jsonl.tmp" "${SNAP}/F_rows.jsonl" \
    && echo "  materialized F-rows: $(wc -l < "${SNAP}/F_rows.jsonl" | tr -d ' ')" || rm -f "${SNAP}/F_rows.jsonl.tmp"
  $SSH "$SSH_TGT" "sudo -u ztare_verify cat ${_src_dir}/last_close.json 2>/dev/null" \
    > "${SNAP}/last_close.json.tmp" 2>/dev/null \
    && mv "${SNAP}/last_close.json.tmp" "${SNAP}/last_close.json" || rm -f "${SNAP}/last_close.json.tmp"
  $SSH "$SSH_TGT" 'sudo -u ztare_verify cat /srv/ztare_official_store/legacy/gp241_legacy_manifest.txt 2>/dev/null' \
    > "${SNAP}/gp241_legacy_manifest.txt.tmp" \
    && mv "${SNAP}/gp241_legacy_manifest.txt.tmp" "${SNAP}/gp241_legacy_manifest.txt" \
    && echo "  legacy manifest: $(wc -l < "${SNAP}/gp241_legacy_manifest.txt" | tr -d ' ') ids"
  printf '%s\n' "Snapshot of the daemon-owned /srv/ztare_official_store taken ${TS} by deploy/vps_pull.sh." \
    "READ-ONLY disaster-recovery copy. NOT the live store; never fed back as authority." \
    > "${SNAP}/README.txt"
else
  echo "  (dry-run: official-store snapshot skipped)"
fi

say "DONE — authoritative VPS research record pulled into the local git repo"
echo "Review with: git status --porcelain | grep -E 'EXPERIMENT_TRACK|ns_residual_manifest|forecast_pool|catch_ledger|official_store_snapshot'"
echo "Backups (if you need to undo a pull): $BK"
