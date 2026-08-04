# Operation-effect predictive-state result

Date: 2026-07-25

Parent hypothesis: `operation_effect_history_hypothesis.md`

## Outcome

The comparison exposed a section-identity defect before it required the
larger state:

- frame-only state retains one boundary-contaminated non-commuting relation;
- action suffix length one reduces that count to zero;
- operation-effect suffix length one also reduces it to zero;
- action history is the smaller quotient on this evidence (79 fibers versus
  81 for operation-effect history at length one).

The operation-effect mechanism passes the transport test, but the evidence
does not justify selecting it over action history.

## Cause of the prior residual

Each sealed boundary had entered the relation through two paths:

1. its ordered trajectory, carrying the pre-boundary history;
2. an explicit boundary edge carrying an incomplete history section.

Both paths referenced the same evidence row. Treating them as independent
observations manufactured a conflict that survived every suffix length.
The compiler now deduplicates those presentations by evidence reference and
retains the ordered trajectory as authority.

The verified level seed also ends at a lifecycle boundary. Its preceding
actions therefore do not belong to the target level's within-epoch history;
the replay trace now resets both predictive histories at that boundary.

## Updated frontier

After admitting the latest law-only `[0, 1]` slice, the observed frontier
moves to `[0, 2]` rather than repeating the prior route:

- zero ambiguous traversal edges;
- 34 reachable witnessed nodes;
- 97 open source/operation pairs;
- one remaining non-boundary non-commuting relation, not used by the route.

Evidence:
`operation_effect_history_active_audit_result.json`.
