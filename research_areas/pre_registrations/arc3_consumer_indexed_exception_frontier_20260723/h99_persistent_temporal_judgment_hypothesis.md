# H99 persistent temporal judgment

Date: 2026-08-05

Hypothesis:
`H-GPSA-PERSISTENT-TEMPORAL-JUDGMENT-20260805-99`

Status: pre-registered; controller-neutral and offline

## Eigenquestion

Can matched distal task credit survive a continual-memory round trip and enter
the existing protocol-selection door under exact authority, while legacy
immediate open/open evidence remains uncredited and protocol costs remain
unchanged?

## Hypothesis

Continual memory can retain finite decision-eligibility chains as episodic
evidence, deterministically reconstruct their predicted-versus-observed yield
calibrations, and compile matched terminal contrasts into option preferences
at query time. The planner may combine those preferences with its existing
immediate-choice judgments only when task, decision namespace, source context,
continuation controller, and complete option set all match.

Legacy immediate-choice experiences are a different evidence category. An
open/open immediate pair must remain uncredited after memory migration and
must not acquire distal credit unless an explicit eligibility chain and
terminal external adjudication are recorded.

## Discriminating test

1. Start from a legacy `ztare-continual-skill-memory-v1` payload containing an
   immediate open/open decision pair.
2. Migrate it through the public loader and verify that its immediate task
   preferences remain zero.
3. Record two anonymous matched temporal pairs whose first decisions are open,
   whose continuation policies and primitive costs match, and whose terminal
   outcomes contrast attained/open.
4. Save and reload the memory. Recompile distal judgments and yield
   calibrations only from the restored chains.
5. Feed the exact-authority distal preferences through the existing
   acquisition-protocol calibration resolver and selector.
6. Repeat the query with a changed controller context and changed complete
   option set.

## Success criterion

1. The legacy v1 payload migrates to the new memory identity without
   manufacturing task credit from its open/open experiences.
2. All temporal chains and their hashes survive save/load exactly.
3. Restored yield calibrations equal the pre-save calibrations and explicitly
   carry no task-credit authority.
4. Two matched terminal contrasts reconstruct `+1` for the enabling option and
   `-1` for the hazardous option.
5. The exact-authority planner selection flips to the enabling protocol.
6. Controller or option-set mismatch exposes no distal task values and leaves
   the baseline selection unchanged.
7. Primitive and control costs are byte-identical before and after reranking.
8. Conflicting immediate and distal nonzero judgments fail closed to neutral
   rather than allowing one evidence category to silently override the other.

## Kill conditions

- persistence stores a derived preference without the eligibility chains that
  authorize it;
- load accepts drift between materialized yield calibration and its chain
  evidence;
- a legacy open/open experience gains task value;
- distal credit crosses any authority component;
- planner integration changes protocol cost;
- a nonzero immediate/distal conflict is resolved by precedence; or
- save/load changes the selected exact-scope value.

## Claim boundary

Passing establishes persistent, controller-neutral distal judgment and its
entry into the existing synthetic protocol selector. It does not establish
ARC improvement, automatic chain collection from the play loop, H97 support,
cross-task value transport, or live score gain.
