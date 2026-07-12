#!/bin/bash
# Compatibility launcher; the P1 campaign frontmatter owns its policy.
set -euo pipefail
cd "$HOME/figs_activist_loop"
export PATH="$HOME/.elan/bin:$HOME/.local/bin:/usr/local/bin:$PATH"
export PYTHONPATH=src
exec ./venv/bin/python scripts/public/control/leanmill/p1_rung_retry.py
