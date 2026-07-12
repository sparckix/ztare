#!/bin/bash
# Compatibility launcher for the frozen P1 RUNG A campaign. Runtime, budget,
# stopping, target bytes, and execution identity are owned by its frontmatter.
set -euo pipefail
cd "$HOME/figs_activist_loop"
export PATH="$HOME/.elan/bin:$HOME/.local/bin:/usr/local/bin:$PATH"
export PYTHONPATH=src
exec ./venv/bin/python scripts/public/control/leanmill/p1_rung_retry.py
