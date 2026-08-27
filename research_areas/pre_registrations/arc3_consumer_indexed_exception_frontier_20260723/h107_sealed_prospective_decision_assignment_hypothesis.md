# H107 sealed prospective decision assignment

Date: 2026-08-07

Hypothesis:
`H-GPSA-SEALED-PROSPECTIVE-DECISION-ASSIGNMENT-20260807-107`

Status: pre-registered; exact-source offline mechanism audit

## Eigenquestion

Can the controller prospectively execute both arms of an exact current planner
choice, then bind the resulting H104 episodes to H105 graded external utility,
without representing randomized assignment as learned task value?

## Hypothesis

A sealed replay contract plus a separately witnessed arm assignment can select
one canonical guarded protocol through an assignment authority that is
disjoint from task credit, utility, contrast priority, and information yield.
The assignment is admissible only when the planner's task, choice context,
continuation controller, complete canonical option set, environment source,
replay prefix, and information-yield measure equal the frozen contract.

After execution, a draft-bound external adjudication may materialize one H105
utility arm only by first passing the existing H100 episode binder. The frozen
utility measure evaluates externally supplied components; neither the planner
nor the assignment may author those values. Primitive action cost is copied
from the collected episode and remains unchanged.

## Discriminating test

1. Construct two guarded protocols where the higher-yield baseline differs
   from the arm selected by a sealed assignment.
2. Select each arm under the same canonical protocol set and verify the
   assignment overrides baseline and learned-value ordering without entering
   either value map.
3. Change the task, choice context, continuation controller, complete option
   set, assigned option, or assignment contract hash and attempt selection.
4. Assemble one H104-complete draft per assigned arm from the same frozen
   environment source and replay prefix.
5. Bind externally adjudicated component values to each draft through one
   utility measure and settle the resulting H105 pair.
6. Change the episode arm, environment source, replay prefix, continuation
   policy, yield measure, utility measure, adjudication draft hash, evidence
   identity, or primitive cost and attempt materialization or settlement.
7. Feed two settled prospective pairs into continual memory and query the
   exact current option families.

## Success criterion

1. The assigned arm is selected even when its base yield and learned-value
   rank are lower, while all protocol cost receipts remain byte-identical.
2. Selection receipts name assignment authority and explicitly deny task,
   utility, and information-yield credit.
3. Every authority or source mismatch refuses selection before execution.
4. Each utility arm is derived from an H100-bound episode; its chosen family,
   variant, continuation, terminal status, and primitive cost equal the draft.
5. External values equal the frozen measure applied to the adjudicated
   components and the exact-source pair settles at support one.
6. Two prospective pair repetitions yield support-two persistent preference
   for the better option under the exact current planner authority and measure.
7. The same evidence is invisible under any changed task, context,
   controller, choice set, or measure.

## Kill conditions

- assignment is encoded as task value, utility, contrast priority, or a yield
  bonus;
- the assigned option is absent, deduplicated, unpriced, or unaffordable but a
  fallback protocol executes;
- a partial choice set is accepted;
- external components are authored by the planner or inferred from yield;
- utility materialization bypasses H100 exact-source binding;
- collected primitive cost is replaced by compiled-token or budget cost;
- an edited episode or adjudication receipt retains the same authority; or
- synthetic settlement is reported as an ARC environment result.

## Claim boundary

Passing establishes a prospective exact-source evidence path and offline
planner-to-memory circuit. It does not establish ARC task improvement, H97 API
support, cross-context transport, or a benchmark result.
