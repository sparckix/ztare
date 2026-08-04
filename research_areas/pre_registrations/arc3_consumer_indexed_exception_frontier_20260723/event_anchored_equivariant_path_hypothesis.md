# Event-anchored equivariant path hypothesis

Date: 2026-07-26

Hypothesis ID: `H-ARC3-EVENT-ANCHORED-EQUIVARIANT-PATH-20260726-27`

## Eigenquestion

Does the shared finite-configuration event become a transportable action skill
when the surrounding control path is expressed in canonical coordinates under
translation, rotation, and reflection?

## Hypothesis

The prior completion sections are two coordinate presentations of the same
event-anchored control mechanism. After choosing the first
finite-configuration change as an internal origin, removing displacement
magnitudes, collapsing straight runs, and quotienting one whole path by a
single dihedral symmetry, the epoch-0 path will embed completely and uniquely
in the held-out epoch-1 completion. It will not embed as well in any epoch-1
non-discharge terminal section.

## Governing identity

The tested object is an `event-anchored equivariant path section`: a continuous
observed section, one internal mechanism-event witness, ordered controlled-base
translations before and after it, one global lattice symmetry, and exact
transition lineage.

The equality relation permits:

- arbitrary translation of the coordinate origin;
- one global element of the square-lattice dihedral group;
- division of each nonzero displacement by the gcd of its components;
- collapse of adjacent equal primitive directions.

It does not permit a different rotation per step, path reversal, event
relocation, action-label copying, or rendered-state equality.

## Fixed languages

For each boundary-terminated section, locate the first ordinary transition
whose mechanism changes `finite_configuration`. Sections without that event
have no anchored word.

Construct two fixed words:

1. `anchored_direction_runs`: primitive controlled-translation directions,
   one `ANCHOR` token at the event, and run collapse independently on each
   side; choose the lexicographically least image under the eight global
   dihedral transforms.
2. `anchored_relative_turns`: the anchor plus the ordered invariant between
   successive primitive directions on each side, represented by squared norms,
   dot product, and absolute determinant. This is invariant under the same
   rotations and reflections without choosing an orientation.

Every token retains its source transition as a backward section.

## Discriminating test

Use the epoch-0 completion as the sole template. Hide epoch-1 terminal valence,
score every epoch-1 boundary section by LCS F1 in both fixed languages, then
reveal the labels. Require the held-out completion to contain every template
token and rank uniquely above all terminal failures.

Run three fixed ablations:

- reverse the template order;
- remove the anchor token;
- replace the one global dihedral transform with independently canonicalized
  step directions.

The first two must score strictly below the admitted word. The third is
reported as an over-quotient confuser and cannot certify transport.

## Success criterion

At least one language contains the anchor, at least one motion token on each
side, and at least three motion/turn tokens total; aligns the full template to
the held-out completion with positive unique margin; beats reversal and
anchor-removal; and emits one global symmetry plus exact transition lineage.

## Kill condition

Either completion lacks the anchor; one side is empty; no full embedding
exists; a failure ties or wins; reversal or anchor removal ties; the match
requires independent per-step rotations, literal operation labels, rendered
coordinates, or hidden valence; or lineage is incomplete.

## Claim boundary

A pass certifies a prior-level equivariant path correspondence only. Ranking or
executing a Level 3 intervention requires a separately preregistered consumer.

