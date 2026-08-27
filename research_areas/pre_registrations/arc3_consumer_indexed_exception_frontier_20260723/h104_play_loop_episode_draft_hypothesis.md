# H104 play-loop episode draft

Date: 2026-08-07

Hypothesis:
`H-GPSA-PLAY-LOOP-EPISODE-DRAFT-20260807-104`

Status: pre-registered; offline play-loop fixtures

## Eigenquestion

Can the ARC play loop assemble and persist an H100 episode draft from its
chronological protocol-decision windows only when H101/H103 produced complete
yield evidence, without creating a temporal chain or task preference?

## Hypothesis

At run close, chronological decision windows can be lowered into one H100
episode draft when every window contains:

- exact task/decision/source/controller/choice-set authority;
- selected option family and variant;
- a frozen H101 forecast;
- a successful H101 observation bound to that forecast;
- primitive cost and one invariant measure identity; and
- immediate external task adjudication.

Each window's successor decision state is the next window's exact source
context; the final successor is a content-addressed terminal adjudication
state. Environment source and initial replay prefix remain caller-owned exact
identities. The episode ledger is separate from continual temporal chains and
is idempotent by episode hash.

## Discriminating test

1. Assemble a two-window attained episode and a one-window open episode from
   complete anonymous H101 receipts.
2. Save and reload both drafts from the episode ledger.
3. Run the ARC multilife wrapper with a fake selected-protocol receipt and
   verify automatic persistence under a supplied exact environment source.
4. Repeat the same episode and verify idempotence.
5. Remove or alter forecast hash, observation status, yield measure, evidence
   reference, environment source, or replay prefix.
6. Inspect continual memory after draft persistence.

## Success criterion

1. Complete chronological windows produce H100 drafts with correct adjacency
   and terminal status.
2. Draft hashes survive save/load.
3. The play-loop fixture writes one episode draft automatically.
4. Repeating an identical episode does not duplicate it.
5. Missing, unavailable, or cross-forecast yield evidence refuses assembly.
6. Measure mismatch refuses assembly.
7. Environment source and replay prefix are required.
8. Draft persistence adds no temporal decision chain, matched pair, or task
   preference.
9. Draft receipts deny task-credit authority.
10. Existing immediate-choice recording remains unchanged.

## Kill conditions

- an unavailable yield observation is replaced with a guessed value;
- a window crosses forecast, measure, or evidence identity;
- chronological adjacency is not preserved;
- drafts enter temporal credit before a sealed replay contract;
- repeated collection duplicates an episode; or
- persistence manufactures task preference.

## Claim boundary

Passing establishes automatic offline play-loop episode-draft collection. It
does not establish live replay-contract creation, counterfactual arm execution,
H97 support, or ARC score gain.
