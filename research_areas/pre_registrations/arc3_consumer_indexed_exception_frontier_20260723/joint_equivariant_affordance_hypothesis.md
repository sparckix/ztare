# Joint-equivariant terminal affordance

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-JOINT-EQUIVARIANT-AFFORDANCE-20260726-30`  
Status: preregistered

## Eigenquestion

Is task discharge native to the relative orientation between the attempted
destination footprint and the finite-configuration display, rather than to
either object in an independently chosen coordinate frame?

## Hypothesis

Apply one shared element of the eight-element dihedral group to the raw
attempted-destination footprint and the square finite-configuration matrix,
palette-normalize both transformed matrices, and choose the lexicographically
least joint image. The epoch-0 completion joint code will:

1. exactly match the held-out epoch-1 completion;
2. match none of the five epoch-1 `GAME_OVER` edges;
3. outperform footprint-only, configuration-only, and independently
   canonicalized-product ablations; and
4. have at least one configuration preimage in the active epoch-2 evidence
   distinct from the observed non-discharging configuration `293fb91a…` when
   paired with the frozen H28 target footprint.

## Fixed lowering

- infer each operation displacement from the uniquely supported modal
  controlled-object translation, as in H28/H29;
- require exactly one controlled-object origin;
- extract the raw 5-by-5 footprint at the attempted destination;
- reshape the finite-configuration factor as a square matrix, rejecting
  nonsquare configurations;
- for each named D4 transform, apply that same transform to both matrices;
- normalize palette/equality classes only after the shared transform;
- hash the lexicographically least pair
  `("joint_affordance", footprint_partition, configuration_partition)`;
- hide epoch-1 boundary valence until all codes are frozen;
- reconstruct the active raw target footprint from the H29 representative and
  enumerate distinct active epoch-2 finite configurations from admitted
  evidence.

No literal action identity, absolute coordinate, palette value, route length,
success label, per-object transform, or game-specific rule enters the code.

## Discriminating test

Use the single epoch-0 completion as the template. Score every epoch-1 terminal
edge by exact joint-code equality before exposing boundary valence. Compare
against the three fixed ablations. Then hold the active H29 target footprint
fixed and compute the joint code for every distinct active configuration,
retaining evidence lineage for each matching preimage.

## Success criterion

- all terminal and active inputs are admissible;
- held-out completion match count is exactly one;
- epoch-1 failure match count is zero;
- the independent-product ablation fails or is strictly less selective;
- at least one active matching configuration has a digest different from
  `293fb91ad721cdd6f9126d2d6e9e0750b257c86ae5f3802e1ce11c814ab8f94b`;
- all matches carry observation references.

## Kill conditions

Reject the hypothesis on any ambiguous displacement/origin, nonsquare
configuration, missing positive match, failure collision, no active
configuration preimage, only the already observed non-discharging
configuration, independent canonicalization sufficiency, transform mismatch,
hidden-label use, or missing lineage.

## Claim boundary

A pass certifies a cross-epoch joint affordance code and an active
configuration preimage. Route reachability, edge productivity, live execution,
and external completion remain separate tests.
