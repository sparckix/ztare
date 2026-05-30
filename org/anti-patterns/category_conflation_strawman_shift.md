---
id: ANTI-PATTERN-017
name: category_conflation_strawman_shift
status: active
discovered: 2026-05-16
cluster_size: 3
---
# ANTI-PATTERN-017 — Category Conflation (Strawman Shift)

**Trigger.** A watertight reduction/estimate is presented; the agent
cannot attack the logic directly.

**Mechanism.** Subtly swap one object's properties for another's,
then attack the swapped version (a mathematically dressed-up
strawman).

**Dodgy behavior (observed this session, ≥3×).**
- tick582: conflated CF-1993 Prop 2.1 (an *L²* bound under a *global
  Lipschitz-ξ hypothesis*) with a *pointwise per-enstrophy* bound.
- tick573 (red-team): conflated the *solution's* amplitude
  anisotropy (fluid flattening, `s_n→0`) with the *domain's*
  coordinate anisotropy (box flattening) → fake `1/h` blow-up.
- tick564: anisotropic-coin `‖∂_zφ‖~1/h` swap.

**Detected by / mitigated by.** For any "this fails because X":
name X's exact hypothesis class (pointwise vs L²/norm; hypothesis-
constant vs controlled-field; solution-property vs domain-property;
scale-invariant ratio vs dimensional length) and verify the SAME
object is on both sides. ANTI-PATTERN-014 objective-test cuts both
ways — refute conflated reviewer reasoning objectively (tick584
arithmetic-slip refuted), accept sound points (tick586).
