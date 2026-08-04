# History-state audit result

Date: 2026-07-25

Parent hypothesis: `history_state_hypothesis.md`

## Outcome

The identical-frame counterexample is not time-separated: both sources occur
at transition time `79`.

Across 981 evidence records, including six sealed task-open boundaries, the
frame/action relation contains five ambiguous groups covering 18 rows.

Candidate lifts:

- exact trajectory position and total action counts remove ambiguity by making
  almost every row unique; they discard compression and are rejected;
- distance since boundary separates the named pair and reduces ambiguity to
  two groups / four rows, but retains 978 of 981 groups;
- action counts since boundary reduce ambiguity to one group / two rows, but
  retain 979 groups;
- a recursive action suffix of length 12 separates the named pair and reduces
  ambiguity to one group / three rows while retaining 890 groups.

Evidence:
`history_state_audit_result.json`.

## Verdict

The evidence supports an action-driven latent state. A finite action suffix is
the smallest tested coordinate with both an update mechanism
(`suffix -> shift + operation`) and material compression. Exact counters are
diagnostic only.

## Lineage correction

The length-12 estimate used action histories reconstructed over the flattened
episode bank. That store does not retain trajectory prefixes and therefore
cannot own a history-state claim. Recompilation over the four verified sealed
trajectories (six boundaries) finds that suffix length 1 removes every
boundary-contaminated non-commutation. The sealed result supersedes the
flattened length estimate for live control.
