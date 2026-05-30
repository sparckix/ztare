#!/usr/bin/env bash
# Stable approval-friendly entrypoint for bounded VPS actions.
# Implementation lives in deploy/vps_run.py; do not add action logic here.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

# Remote noninteractive SSH must not depend on login-shell PATH setup.
# Keep this as a literal remote expression; vps_run.py expands $REMOTE_REPO
# locally and leaves $HOME for the remote shell.
export ZTARE_VPS_REMOTE_PATH_PREFIXES="${ZTARE_VPS_REMOTE_PATH_PREFIXES:-\$REMOTE_REPO/venv/bin:\$HOME/.elan/bin:\$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin}"

exec "$PYTHON" "$SCRIPT_DIR/vps_run.py" "$@"
