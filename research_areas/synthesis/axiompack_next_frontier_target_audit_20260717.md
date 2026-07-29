---
description: "Current-source and apparatus-fit audit for the next broader AxiomPack mathematics campaign."
---

# Next AxiomPack Frontier Target Audit

Date: 2026-07-17

## Decision state

`campaign_live / deterministic_controls_passed / construction_lifecycle_first_fired`

The leading next campaign is a binary linear-code construction target:

\[
\text{construct a binary linear }[50,20,14]\text{ code}.
\]

The current best-known table entry for \([50,20]\) has lower bound \(13\)
and upper bound \(14\). A witness of minimum distance at least \(14\) would
therefore improve the construction bound and settle that parameter at the
upper bound. The table's current \([50,20,13]\) construction is quasicyclic
of degree five and was last modified on 2025-05-14.

This is a selected target, not a priority claim. The source snapshot,
fresh bounded source replay, and deterministic controls are complete. The
live attempt has now passed:

1. residual-directed blueprint compilation and executable preflight;
2. independent semantic review with the deterministic preflight joined;
3. registered witness-construction authorship and exact artifact checking;
4. provider-free construction-artifact ratification on a matched small control;
5. a fresh replay of the frozen Grassl target page.

Attempt `attempt-65f7e0c52d1b499fa583847f63daad07` is active. A transport
schema defect forced evidence-context hypothesis IDs into a formal-context ID
shape during its first navigator pass. The durable trace was preserved, the
schema was generalized to adapter-owned hypothesis identities, and the same
attempt resumed. No target witness or mathematical disposition exists yet.

## Why this target fits

The target has an executable success predicate. For a proposed generator
matrix \(G\), the host can check:

\[
\operatorname{rank}_{\mathbf F_2}(G)=20,
\qquad
\min_{0\ne u\in\mathbf F_2^{20}}\operatorname{wt}(uG)\ge 14.
\]

One finite witness is consequential; bounded failure is only a search result.
This cleanly separates the construction campaign from a universal theorem
campaign. It also supports the complete AxiomPack loop:

\[
\begin{aligned}
&\text{known generator matrices and construction traces}\\
&\to \text{candidate structural packs}\\
&\to \text{low-weight-codeword attack}\\
&\to \text{pack revision or representation change}\\
&\to \text{exact distance certificate}\\
&\to \text{LeanMill ratification}\\
&\to \text{fresh table and literature replay}.
\end{aligned}
\]

The formal substrate is finite, but the certificate route must remain
kernel-pure. Mathlib supplies finite-field linear algebra and
`InformationTheory.Hamming`. The deterministic boundary can enumerate the
\(2^{20}-1\) nonzero messages and expose a conventional generator matrix for
independent verification. LeanMill cannot credit a bare `native_decide`
enumeration because its generated axiom is outside the closure allowlist. A
terminal Lean certificate therefore needs either a compact construction chain
with proved rank/distance preservation, a replayable branch-and-bound or weight
enumerator certificate checked by ordinary reduction, or another kernel-pure
certificate whose cold compile fits the campaign budget.

## Required campaign language

The campaign must author the mathematical representation. The host may offer
reviewed capabilities for:

- binary matrices and row-space rank;
- Hamming weight and exact minimum-distance checking;
- cyclic and quasicyclic block constructors;
- puncture, shorten, extend, direct sum, Construction X, and Construction XX;
- low-weight counterexample extraction;
- equivalence normalization under row operations and coordinate permutation;
- external-bound target predicates.

The host must not choose the generator polynomials, construction composition,
or invariant to optimize. Those are campaign decisions. A missing constructor
is a typed language-expansion input; it does not license a one-off search
script that bypasses the campaign state machine.

## Controls and stop rules

Matched positive controls:

- reconstruct and certify the published \([50,20,13]\) quasicyclic code;
- reconstruct its published extended \([51,20,14]\) code;
- deliberately perturb a generator to recover a low-weight counterexample.

All three controls now replay through the typed binary-code adapter. The
published quasicyclic generator has exact rank 20 and distance 13 after all
\(2^{20}-1\) nonzero messages are checked; its parity extension has exact
distance 14; toggling coordinate zero in generator row zero produces a
rank-20 distance-12 counterexample. The content-bound matrices, witnesses,
and receipts are in
[`binary_code_control_replay.json`](../pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/binary_code_control_replay.json).

Discriminating target:

- a rank-20 length-50 generator with no nonzero codeword below weight 14.

Stop rules:

- success requires the explicit matrix, exact rank and distance receipts,
  a kernel-pure LeanMill certificate, and a fresh external-target replay;
- search exhaustion within any chosen constructor family does not imply
  nonexistence;
- recurrence with a known construction is retained as calibration and earns
  no priority credit;
- representational stagnation returns a typed language request to the campaign
  successor route.

## Broader alternatives compared

| Target class | Current residual | Executable frontier | Formal surface | Main risk | Rank |
|---|---|---:|---:|---|---:|
| Binary linear codes | close the \([50,20]\) distance gap \(13\le d\le14\) | exact witness | bounded and direct | heuristic search may stall | 1 |
| Cycle double cover | every bridgeless graph has a cycle double cover | only after choosing a restricted structural lemma | strong graph substrate | finite examples do not discriminate the universal claim | 2 |
| Union-closed sets | Frankl abundance conjecture and minimal-counterexample structure | finite families plus candidate inequalities | moderate build | crowded source surface and many invalid proof claims | 3 |
| GF(5) matroids | excluded-minor structure beyond ten elements | exact representability/minor checks | strong Mathlib matroid base | requires partial-field and catalogue infrastructure first | 4 |

The cycle-double-cover conjecture remains a strong theorem-lane candidate, but
the current-source audit has not yet isolated a narrow residual whose finite
counterexamples can revise a proof mechanism. The coding target already has a
one-bit external gap and a decisive witness predicate.

## Current-source anchors

- Grassl code table, \([50,20]\):
  <https://codetables.de/BKLC/BKLC.php?k=20&n=50&q=2>
- Grassl code table, derived \([51,20,14]\) control:
  <https://codetables.de/BKLC/BKLC.php?k=20&n=51&q=2>
- Chubenko--Kurz, source of the current quasicyclic construction family:
  <https://arxiv.org/abs/2312.00885>
- Current Magma best-known-linear-code interface:
  <https://magma.maths.usyd.edu.au/magma/handbook/text/1980>
- Ghanbari--Šámal, current CDC formulation and approximation lane:
  <https://arxiv.org/abs/2511.07285>
- Bouchard, current minimal-counterexample conditions for union-closed sets:
  <https://arxiv.org/abs/2503.00277>
- Brettell, excluded minors for GF(5)-representability through ten elements:
  <https://arxiv.org/abs/2307.14614>
