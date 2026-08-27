# H125 palette-quotiented pose/motion affordance

**Status:** Passed offline on 2026-08-08. The preregistered claim boundary
remains in force.

## Eigenquestion

Did H122 preserve pose as a coordinate while discarding the higher-order
relation needed at H124's failure seam: edge-marker bearing covaries with
motion direction and can transport across palette-renamed oriented tokens?

## Frozen evidence

- H119 report SHA-256:
  `e0482a75e6d657315e43bf5860a3c15ceec51e7fbda272593dd169529e9ed2c3`.
- H122 result SHA-256:
  `60dbf8f66377625a28f08a1252c07f11f99f17673848cd16dab535ae712f0dd7`.
- H124 result SHA-256:
  `86a72142e1e47f4ad521bc283b27ac95d4262b854ace8f3ac84f085522b16457`.
- H124 audit SHA-256:
  `cfde30df1e2241dc46eeefd4f9b4377df0955a9402c843645aea5e1c970841a6`.
- Exact Level-2 grid-carrier SHA-256:
  `dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24`.
- H124 primary result: treatment `0/3`, control `0/3`; treatment chose the
  correct first action `3/3` but never chose the lower flank by action 4.

## Candidate mechanism

The governing identity is a covariant relational schema rather than a colored
component:

```text
dominant body + one minority cardinal-edge marker
    --palette quotient + D4 quotient-->
oriented-token identity + marker bearing
    --source transition support-->
predicted motion bearing
```

The identity is invariant to palette renaming and D4 presentation; bearing is
covariant and remains in state. Source evidence may establish the mapping only
from within-epoch controlled-object transitions. Applying the relation to a
new palette supplies a predicted motion cone, not a task label or contact
outcome.

A relational-affordance frontier then combines that cone with an extracted
finite route graph. For each route it records the first relative exposure to
the oriented object (`head_on`, `rear`, `transverse`, or `none`), exposure
depth, route length, goal reachability, and budget feasibility. With contact
outcome unknown, it prefers a budget-feasible route that avoids closing
head-on exposure and preserves a transverse approach. It must return a
decision-seam direction, never a memorized action word.

## Offline discriminating test

Use only H119 Level-1 transition evidence and H119's settled Level-2 start
observation. Do not load or execute the game implementation and do not call a
controller.

The test must show all of the following:

1. Source transitions support one palette-quotiented oriented-token relation
   whose post-transition marker bearing agrees with displacement direction.
2. The Level-2 start contains exactly one controlled token and at least one
   distinct-palette oriented token admitted by that relational schema.
3. The transported entity bearing is west/left.
4. A topology extractor using learned stride, learned node baseline, and
   observed connector regularity—not frozen coordinates or entity colors—
   exposes both a direct head-on route and a lower transverse route to the
   source-derived goal role.
5. The transverse route is within the 10-action budget, and the compiled
   frontier selects `down` at the state reached by geometric prefix
   `up,right,right`.
6. Rotating/reflection-transforming the entire symbolic scene commutes with
   compilation: route/contact identities remain equal after canonicalization
   and the selected direction transforms covariantly.
7. Palette permutations preserve the receipt; malformed markers, non-cardinal
   markers, missing alternate routes, incompatible stride, goal-role
   mutation, and target-carrier mutation are rejected or change the expected
   identity.

## Prediction and kill conditions

Prediction: all seven checks pass, producing one source-supported
marker-motion relation and one target-local lower-flank decision receipt.

Kill the mechanism if source pose does not predict displacement, the new
entity requires its literal colors or coordinates, direct and flank contacts
collapse into one class, the selected branch is not down, the route exceeds
budget, any D4/palette test fails, or a mutation is silently accepted.

## Prior-art boundary

Affordance competition, successor representations, active-inference value of
information, safe exploration, and relational affordance graphs contain
neighboring ingredients. H125 tests a narrower composition: a
palette-quotiented/D4-covariant pose-motion relation learned from one object,
transported to another object class, joined to a viability frontier, and later
eligible for causal acquisition settlement. No novelty conclusion follows
from the offline test.

## Claim boundary

Success would establish an offline relational abstraction and target-local
decision-seam compiler. It would not establish that the inferred entity moves,
that the selected path succeeds, controller gain, cross-game transfer,
multi-generation compounding, broad capability gain, or literature novelty.

## Outcome

All 24 preregistered checks passed. The source law had support `21/21` and
zero mismatches. The frozen Level-2 carrier yielded four candidate routes;
the compiler selected `down`, a 10-action transverse route. Deleting its
alternate edge changed the decision to `right` and `head_on`. All eight D4
transforms shared canonical frontier SHA-256
`54c6bfeb79bf0e9eccee4650e88b9d55155b8378ef2960d47e1387f60dc9570f`,
and palette renaming preserved the semantic receipt.

Evidence:

- `h125_palette_quotiented_pose_motion_affordance_result.json`
  (`bf2dfe105aa9bad163cacaf47c45ca87310abe65e59ec17d804cb3e77cd077f1`)
- `h125_palette_quotiented_pose_motion_affordance_audit.py`
- `src/ztare/worldmodel/relational_affordance.py`

This establishes the offline relation and decision compiler described above.
The next discriminator is causal acquisition at the exact branch state.
