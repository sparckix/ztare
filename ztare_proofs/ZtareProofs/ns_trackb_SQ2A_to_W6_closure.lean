/-
# NS Track B — SQ2.A → W6 Closure (one-line composition)

**Date**: 2026-05-09 evening session.
**Provenance**: SQ2 dichotomy `SQ2_bohr_diophantine_2026_05_09.md` §2.4
+ §4.2 claim "this composition is one Lean line".

## What this file IS

The **one-line composition** of the SQ2 dichotomy's branch A
(`NearZeroBohrL1 BohrSpec a`) with the already-shipped axiom
`W6_sharp_conditional_lerner2026_bohrAP_port` to conclude
`IdenticallyZeroSpatial u`.

SQ2.A statement (per `SQ2_bohr_diophantine_2026_05_09.md` §2.4):
```
∃ R > 0 s.t. Σ_{ζ ∈ Σ_u, |ζ|<R} |a(ζ)| < ∞
```
which is, by definition, `NearZeroBohrL1 BohrSpec a`.

The W6 sharp conditional axiom takes hypothesis
`W6Plus_NearZeroBohrL1 BohrSpec a := W6_AmplitudeClassL2NotL1 BohrSpec a
∧ NearZeroBohrL1 BohrSpec a`.  Since `IsW6ClassStationary` already
contains `W6_AmplitudeClassL2NotL1` (via `W6_Stratum`'s fourth
conjunct), the SQ2.A → W6 closure is the conjunction-introduction +
axiom-application — a single term.

## What this file is NOT

* **NOT a closure of SQ2.A itself.**  SQ2.A is the open arithmetic
  conjecture `NearZeroBohrL1`.  This file only composes it into the
  W6 closure once SQ2.A is hypothesized.
* **NOT a new axiom.**  The body discharges via the existing
  `W6_sharp_conditional_lerner2026_bohrAP_port` axiom.  No new axioms
  are introduced.

## PATTERN-007 enumeration of upstream constructors

Constructors that could yield `IdenticallyZeroSpatial u` from
`IsW6ClassStationary + NearZeroBohrL1`:

| Candidate | Verdict |
|---|---|
| `W6_sharp_conditional_lerner2026_bohrAP_port` (existing axiom)
  — **load-bearing**: Wiener-algebra ℓ¹ + tail elliptic damping.
| Track B Følner-Birkhoff
  — unrelated hypothesis structure (external `D[u]`).
| Restrict-Σ / Redefine-space
  — structurally distinct hypothesis classes (per §4 of the
  sharp-conditional file).

Only one constructor attaches.  The composition is exactly:

  `axiom (h_class.2.2.2.2.2 : W6_AmplitudeClassL2NotL1) ∧ (h_sq2a : NearZeroBohrL1)`

— i.e., a single anonymous-constructor term followed by axiom
application.  This is a **legitimate** one-line composition, not
vocabulary-laundering: the structural projection
`h_class.2.2.2.2.2` extracts the genuine ℓ²\\ℓ¹ amplitude-class witness
from the W6 stratum bundle and pairs it with the SQ2.A witness.

-/

import Mathlib.Tactic
import ZtareProofs.ns_trackb_W6_conditional_impossibility
import ZtareProofs.ns_trackb_W6_track_b_folner_birkhoff
import ZtareProofs.ns_trackb_W6_sharp_conditional

namespace ZtareProofs.NS

noncomputable section

/-- **SQ2.A → W6 closure (one-line composition)**.

Given the W6 four conditions on `(BohrSpec, a)` (encoded in
`IsW6ClassStationary`) and the SQ2.A witness `NearZeroBohrL1`,
the velocity `u` vanishes identically.

The body is a single term: package the `W6_AmplitudeClassL2NotL1`
projection out of `h_class` together with the SQ2.A witness into a
`W6Plus_NearZeroBohrL1` pair, then apply the existing W6 sharp
conditional axiom. -/
theorem SQ2A_to_W6_closure
    (ν : ℝ) (u : StationaryVelocityField)
    (BohrSpec : Set (Euc ℝ 3))
    (a : Euc ℝ 3 → Euc ℂ 3)
    (h_class : IsW6ClassStationary ν u BohrSpec a)
    (h_sq2a : NearZeroBohrL1 BohrSpec a) :
    IdenticallyZeroSpatial u :=
  W6_sharp_conditional_lerner2026_bohrAP_port ν u BohrSpec a h_class
    ⟨h_class.2.2.2.2.2, h_sq2a⟩

end

end ZtareProofs.NS
