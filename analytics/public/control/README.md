# analytics/public/control/

Control-plane state for the tick lifecycle: the close-out history and
current state the post-tick gate and RD loop read/write.

- `tick_close_history.jsonl` - append-only record of tick closures.
- `tick_close_state.json` - current tick close-out state.

Written by `scripts/public/control/` (the post-tick check and agent
loop). Append-only; do not reformat.
