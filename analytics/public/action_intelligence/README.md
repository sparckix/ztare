# action_intelligence/

Read-model surface for GP-243 action-impact diagnostics. Daemon-owned;
operators read, daemon writes.

## Files

- `state/source_health.json` — current source-lane health snapshot.
- `state/action_intelligence.json` — recommended next-operator actions
  + the structural rationale per action.
- `state/shadow_recommendations.json` — proposed actions held back
  for review before promotion to the live recommendation set.

Consumer: `src/ztare/reports/operations_intelligence.py` (the RD-side
intelligence reporter). The CLI surface is `ztare action-intel`.

## Update cadence

Refreshed by the action-intelligence daemon at end of every RD tick.
Files are atomic-write (temp + rename), so readers always see a
consistent snapshot.
