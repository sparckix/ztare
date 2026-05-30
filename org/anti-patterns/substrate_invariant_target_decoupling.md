---
id: ANTI-PATTERN-010
name: substrate_invariant_target_decoupling
version: 1
status: active
discovered: 2026-05-09
discovered_reason: |
  Catch C-2026-05-09-61 (third terminal W6 demolition by external GPT-5
  cold-shot in 12 hours) revealed a META-pattern: three independent
  closure routes (additive-combinatorics, low-frequency Wiener-algebra,
  height-filtered Leray-skew) share a single root cause — the rank-2
  Liouville Bohr-AP substrate has natural invariant (height
  max(|m|,|n|)) DECOUPLED from NS's natural invariant (physical scale
  |m + n ω|) precisely because ω is Liouville. The catch ledger now
  shows three demolitions whose root cause is identical; the apparatus
  did not detect the shared root cause until after the third
  individual demolition. ANTI-PATTERN-010 names this class of failure
  so future campaigns detect it BEFORE three serial demolitions.
triggers:
  lexical:
    - "natural invariant"
    - "height" used as substrate filter while target theory uses "scale"
    - "frequency" used by substrate vs "wavenumber" used by target
    - any noun mismatch between substrate's intrinsic ordering and the
      target theory's NS-natural / domain-natural ordering
  structural:
    - substrate has an intrinsic invariant I_substrate (height, lattice
      class, group order, etc.)
    - target theory's analytic tools control a different invariant
      I_target (physical scale, Sobolev exponent, Lp index, etc.)
    - the relation between I_substrate and I_target is non-monotone or
      diverges along a sequence (e.g. ρ(I_target) / I_substrate^τ → 0
      for every τ > 0)
    - 2+ closure routes have already failed for "different reasons"
      that share I_substrate ≠ I_target as root
  problem_classes:
    - mathematical_substrate_attack
    - cross_vocabulary_drift_at_substrate_layer
    - serial_route_demolition_with_shared_root_cause

detection_protocol:
  primary: PATTERN-005  # falsifiable_asymmetry — demand explicit invariant alignment statement
  secondary: PATTERN-014  # cold_shot_dispatch — pre-encoding test of any next-campaign route
  rule:
    - "Before launching ANY closure attempt against a substrate-target
      pair, the apparatus must produce a one-sentence statement of
      I_substrate (the substrate's natural invariant) and I_target
      (the target theory's natural invariant), and a one-sentence
      argument for why they are commensurate."
    - "If the commensurability statement requires a Diophantine,
      ergodic, or arithmetic non-degeneracy hypothesis on the substrate,
      that hypothesis MUST be explicit in the substrate definition. A
      Liouville substrate is incompatible with any I_substrate-vs-
      I_target commensurability requiring polynomial control."
    - "When 2+ closure routes have failed for the same substrate-target
      pair, the apparatus must check whether the root cause is shared
      (I_substrate ≠ I_target) BEFORE launching a third route. If yes,
      the third route is presumptively dead and requires a different
      substrate or different target before resourcing."

mitigation:
  - "Add an `invariant_alignment` field to project charters: explicit
    statement of I_substrate, I_target, and the commensurability
    argument."
  - "Catch ledger requires `shared_root_cause_check` field on every
    second-or-later route demolition for the same substrate-target
    pair."
  - "Pre-encoding cold-shot test (PATTERN-014 cold-shot-before-encoding
    rule, added 2026-05-09 per C-61) is mandatory for next-campaign
    routes — the cold-shot is asked to identify shared root cause
    against prior demolitions, not just attack the new route."

examples:
  - id: catch_C61_three_route_W6_demolition
    summary: |
      Three terminal demolitions of W6 closure narrative on rank-2
      Liouville Bohr-AP substrate within 12 hours via external prover:
        C-58: additive-combinatorics (NC false on T³)
        C-59: low-frequency Wiener-algebra (Lerner port function-class
              mismatch)
        C-61: height-filtered Leray-skew (height-scale collapse for
              Liouville ω)
      Shared root cause identified post-hoc: height (substrate) ≠
      scale (NS-natural). The apparatus did not detect this shared
      root cause until C-61. Earlier detection would have killed
      C-58 and C-59 routes pre-encoding.
    file: analytics/public/ledgers/catch/catch_ledger.jsonl

falsifiable_test:
  description: |
    Given a substrate-target pair with 2+ failed routes on file,
    apply the I_substrate-vs-I_target commensurability check. The
    anti-pattern fires iff the failures share a shared-root-cause
    statement that the apparatus did not surface before route 2 was
    launched.
  binary_check: |
    For each catch with category in {route_demolition, substrate_attack},
    check if a shared-root-cause field exists. Anti-pattern-fired iff
    2+ catches in the same project lack the field AND share a root
    cause discoverable by I_substrate vs I_target inspection.
  not_trivial: |
    Returns "not firing" when a project has run 5 distinct routes that
    each failed for genuinely independent reasons (e.g. one for
    smoothness, one for boundary conditions, one for ergodicity).
    Returns "firing" when 3+ routes fail and share a single shared-root-
    cause statement that the apparatus did not surface in advance.

chain_position: pre  # runs BEFORE launching any closure route on a substrate
references:
  - catch C-2026-05-09-58 (BKGSW+NC false on T³)
  - catch C-2026-05-09-59 (Lerner-2026 port not faithful)
  - catch C-2026-05-09-61 (height-scale collapse demolishes Leray-skew)
  - PATTERN-014 (cold_shot_dispatch — cold-shot-before-encoding rule)
  - PATTERN-005 (falsifiable_asymmetry)
---

# ANTI-PATTERN-010 — Substrate-Invariant ↔ Target-Natural-Invariant Decoupling

## What it is

A class of failure where a substrate's intrinsic natural invariant
`I_substrate` (e.g. lattice height, group order, arithmetic class) is
DECOUPLED from the target theory's natural invariant `I_target`
(e.g. physical scale, Sobolev exponent, Lp index), and the apparatus
launches multiple closure routes against the substrate-target pair
without first verifying invariant commensurability. Each individual
route fails for a "different reason," but the underlying root cause
is the same invariant mismatch.

The anti-pattern is detectable BEFORE individual route attempts if
the apparatus enforces a one-sentence invariant-alignment check on
every charter.

## Canonical incident: 2026-05-09 W6 closure narrative on rank-2 Liouville Bohr-AP NS

Three independent closure routes terminally demolished by external
prover within 12 hours:

* **C-58** (additive-combinatorics): Brascamp-Lieb-Geba-Stein-Wainger
  + (NC) Non-Cancellation. (NC) outright false on T³ via shear-flow
  counterexample.
* **C-59** (low-frequency Wiener algebra): Lerner-2026 Theorem 1.12
  port. Function class incompatible — Lerner assumes decay at infinity
  (Galdi-class), Bohr-AP velocities don't decay.
* **C-61** (height-filtered Leray-skew commutator): the very framework
  GPT-5.5 derived as the next-campaign target after C-58 and C-59
  was demolished by GPT-5 cold-shot 4 hours later. Liouville-
  approximating modes saturate the (T) tail-decay hypothesis with
  bounded H^s norm.

**Shared root cause discovered post-hoc**: the substrate's natural
invariant is height `H(m, n) = max(|m|, |n|)`; NS-natural functional
analysis controls physical scale `|ζ| = |m + n ω|`. For Liouville ω,
ρ_ω(H_k) ≤ H_k^{-τ} for every τ > 0 along a sequence — the relation
is unbounded. Any route that uses NS-natural norms on a height-filtered
substrate inherits this decoupling.

## Why this matters operationally

A pre-encoding invariant-alignment check (one sentence: "I_substrate is
height; I_target is scale; for Liouville ω these decouple unboundedly;
therefore any NS-norm-controlled height-filter route is presumptively
dead") would have killed C-58 and C-59 before they were attempted.

This anti-pattern is genuinely **new at the meta-architecture layer**
— it is NOT detectable by individual-route adversarial review (each
route looks plausible standalone), only by cross-route shared-root-
cause inspection.

## When ANTI-PATTERN-010 explicitly does NOT fire

* Substrate-target pairs where I_substrate and I_target are explicitly
  the same object (e.g. both are physical wavenumber).
* Cross-route demolitions where each demolition has a genuinely
  independent root cause (e.g. one route fails for smoothness, one
  for boundary conditions, one for substrate ergodicity).
* Single-route demolitions — the anti-pattern requires 2+ routes with
  shared-root-cause to fire.

## Mitigation lifecycle

1. **Charter level**: every project charter must state I_substrate
   and I_target explicitly + one-sentence commensurability argument.
2. **Pre-encoding cold-shot**: any next-campaign route is cold-shot
   tested (PATTERN-014, cold-shot-before-encoding rule) BEFORE Lean
   encoding consumes agent-hours. The cold-shot prompt explicitly asks:
   "what is the root cause shared with prior demolitions, if any?"
3. **Catch ledger field**: every second-or-later route demolition for
   the same substrate-target pair carries a `shared_root_cause_check`
   field. If shared-root-cause exists and was not surfaced before the
   route launched, the catch is tagged ANTI-PATTERN-010.
4. **Project ratification gate**: when 2+ shared-root-cause catches
   accumulate for a substrate-target pair, the project requires
   explicit operator ratification before launching a third route.
