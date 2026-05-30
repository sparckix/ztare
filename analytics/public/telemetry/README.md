# analytics/public/telemetry/

Run telemetry (agent activity, insight yield, sorry counts). Append /
snapshot outputs the audits and P0 page sample.

- `agent_telemetry.jsonl` - per-action agent telemetry stream.
- `insight_yield_summary.json` - rolled-up insight-yield snapshot.
- `sorry_count_*.json` - dated Lean `sorry` counts (proof-debt
  tracking).

Regenerable from runs; dated snapshots accumulate by design.
