# H127 autonomous relational-affordance recall compiler

**Status:** Passed offline on 2026-08-08. The preregistered claim boundary
remains in force.

## Eigenquestion

Can the H125/H126 mechanism be invoked from raw source transitions plus one
current observation, with no supplied target palette, coordinates, route,
prefix, entity bearing, branch action, or puzzle-specific label?

## Frozen evidence

- H119 report SHA-256:
  `e0482a75e6d657315e43bf5860a3c15ceec51e7fbda272593dd169529e9ed2c3`.
- H126 result SHA-256:
  `96791887bcd7b16abb89b24eec8085d08c6aca77ebc064bece10da7105257eea`.
- H126 audit SHA-256:
  `13abfad64202814da4729797acdde765437560c03f7c95d296127135e72bfd34`.
- Source rows: H119 turns 0--21, with observation 21 as the terminal
  predecessor and boundary action 1.
- Target: H119 observation 22; observation SHA-256
  `c654ced9fcd15bcc9937e6748e64c4d55b5fe15b21547acbb982068947f7eae4`;
  grid-carrier SHA-256
  `dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24`.
- Budget: 10 primitive actions.

The exact consumption scope is frozen as task
`6bdf4d...b279c`, controller `b2b2e9...a89fb`, context
`c654ce...eae4`, choice set `93526d...981c`, and action vocabulary
`b06730...2770`.

## Candidate mechanism

Add an ARC/worldmodel recall compiler with four owned objects:

1. a source memory revision containing the palette/D4-quotiented pose-motion
   relation and source-derived goal-role identity;
2. a target-local decision seam discovered as the longest shared prefix of
   competing budget-feasible goal routes;
3. a context-bound recall proposal containing only invariant/covariant
   semantics, branch-relative contact classes, costs, uncertainty, and typed
   refusal;
4. an ordinary `MemoryCandidate` routed through the existing sparse wake-sleep
   selector under the exact five-axis `MemoryScope`.

The compiler must derive every target fact from inputs. Its module may contain
no game id, H125/H126 hash, target color, target coordinate, route literal, or
action sequence. Current-scene planning may expose the automatically derived
common approach and branch direction; source memory identity may not absorb
that target presentation.

## Discriminating test

From the frozen inputs alone, require:

1. one source relation with support 21 and zero mismatches;
2. one target decision seam whose common approach is
   `up,right,right`, whose competing first branches include `right` and
   `down`, and whose selected branch is `down`/action 1;
3. a source memory revision unchanged under target palette renaming and all
   eight D4 presentations;
4. a target proposal identity that changes when its observation, graph,
   decision seam, budget, or scope changes;
5. sparse selection of exactly this candidate under the exact scope and zero
   selection after independently mutating each scope axis;
6. typed refusal for no competing route, no supported source relation,
   malformed entity pose, over-budget safe route, or ambiguous goal;
7. compact digest reconstruction from the compiler receipt with no hand-coded
   target semantic fields in the audit.

## Prediction and kill conditions

Prediction: all seven groups pass and the emitted recall digest reconstructs
H125's decision seam from raw evidence.

Kill the mechanism if the audit supplies any derived prefix/bearing/action,
the source memory revision changes under target presentation, scope drift
selects the candidate, the proposed action differs from H125, a mutation is
silently accepted, or the digest requires a target literal embedded in the
compiler module.

## Claim boundary

Success establishes autonomous proposal and sparse selection offline. It does
not establish controller consumption from the Level-2 start, online target
settlement, cross-game transfer, a later acquisition derivative, broad
capability gain, or literature novelty.

## Outcome

All 21 fixed checks passed. Raw H119 inputs produced memory revision
`858791e0752c25121f1f04c0c702346b91bd104a93a6e140ad2784243f0dc935`
and target proposal
`a606753f1fa48bd9c583d89e13b3f567633df34876695cb04fce30d97de28ced`.
The compiler recovered the `up,right,right` common approach and selected
`down`/action 1. Sparse recall selected once under the exact scope and zero
times under each independent scope mutation.

Implementation exposed and repaired a hidden goal-color dependency. Goal
identity is now the unique nonstructural uniform lattice region attached to
the learned route graph through the learned connector; literal color remains
source evidence only. Entity/goal palette changes and all eight D4 target
presentations preserve the source memory and frontier identities.

Evidence:

- `h127_autonomous_relational_affordance_recall_result.json`
  (`9a61127622e25ad4f16fb16edffa2ccf6f8ea2f2e835dda89281d1c52422df4b`)
- `h127_autonomous_relational_affordance_recall_audit.py`
- `src/ztare/worldmodel/relational_affordance_recall.py`
