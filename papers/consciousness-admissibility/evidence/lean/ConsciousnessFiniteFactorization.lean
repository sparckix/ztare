/-
  Consciousness paper (v2) — FINITE descent-factorization reduction, machine-verified.

  WHAT THIS PROVES (the finite case of the paper's descent-factorization obligation, in BOTH regimes):
  An identification procedure restricted to the observation record recovers the target property IFF the
  target is constant on the fibres of the observation map — equivalently, the target factors through the
  observation map on its REALIZED IMAGE (`Set.range`). The realized-image restriction (`Set.rangeFactorization`)
  is what makes the iff hold unconditionally (an unrestricted "factors through the codomain" iff is FALSE when
  the image is a proper subset — empty-domain / unrealized-value degeneracy). Established for:
    • `deterministic_factorization_through_range_iff_constant_on_fibers` — deterministic observation maps `E : H → R`
    • `exact_stochastic_factorization_through_range_iff_constant_on_fibers` — exact stochastic (Markov / `PMF`)
      kernels `K : H → PMF R`
  Together these discharge the FINITE descent-factorization reduction the paper currently argues informally.
  (The deterministic ↔ stochastic statements are isomorphic up to the codomain type; both are proved here so
  each regime stands on its own kernel-checked certificate.)

  VERIFICATION STATUS (kernel-checked, not LLM-asserted):
    • Compiles clean against Mathlib, SORRY-FREE (no `sorry`/`admit`, no added axioms).
    • `#print axioms` ⊆ {propext, Classical.choice, Quot.sound} (Mathlib's standard classical base):
        deterministic → {Classical.choice};  stochastic → {Classical.choice, Quot.sound, propext}.
    • Toolchain: Lean 4 `leanprover/lean4:v4.30.0-rc2` + Mathlib (the `ztare_proofs` lake project).
    • Statement-faithfulness was kernel-checked (the agent's `∀`-fronted phrasing is the SAME Prop as the posed
      binders-before-colon statement, by `@orig = @agent := rfl` type-equality — not a text match).

  PROVENANCE: autoformalized + proved by the LeanMill governed solver (codex/kimi leaves), then ratified by the
  anti-laundering kernel (axiom allowlist + statement-integrity + vacuity/conclusion-discrimination). 2026-06-21.
-/
import Mathlib

set_option maxHeartbeats 1000000

theorem deterministic_factorization_through_range_iff_constant_on_fibers :
    ∀ {H R T : Type*} (E : H → R) (theta : H → T),
    (∃ thetaHat : Set.range E → T,
        ∀ h : H, theta h = thetaHat (Set.rangeFactorization E h)) ↔
      (∀ h1 h2 : H, E h1 = E h2 → theta h1 = theta h2) := by
  intro H R T E theta
  constructor
  · rintro ⟨thetaHat, hthetaHat⟩ h1 h2 hE
    calc
      theta h1 = thetaHat (Set.rangeFactorization E h1) := hthetaHat h1
      _ = thetaHat (Set.rangeFactorization E h2) := by
        congr 1
        ext
        simpa [Set.rangeFactorization] using hE
      _ = theta h2 := (hthetaHat h2).symm
  · intro hfiber
    refine ⟨fun x => theta (Classical.choose x.property), ?_⟩
    intro h
    exact hfiber h (Classical.choose (Set.rangeFactorization E h).property)
      (by
        simpa [Set.rangeFactorization] using
          (Classical.choose_spec (Set.rangeFactorization E h).property).symm)

theorem exact_stochastic_factorization_through_range_iff_constant_on_fibers :
    ∀ {H R T : Type*} (K : H → PMF R) (theta : H → T),
    (∃ thetaHat : Set.range K → T,
        ∀ h : H, theta h = thetaHat (Set.rangeFactorization K h)) ↔
      (∀ h1 h2 : H, K h1 = K h2 → theta h1 = theta h2) := by
  intro H R T K theta
  constructor
  · rintro ⟨thetaHat, hthetaHat⟩ h1 h2 hK
    calc
      theta h1 = thetaHat (Set.rangeFactorization K h1) := hthetaHat h1
      _ = thetaHat (Set.rangeFactorization K h2) := by
        congr 1
        exact Subtype.ext hK
      _ = theta h2 := (hthetaHat h2).symm
  · intro hfiber
    refine ⟨fun k => theta (Classical.choose k.property), ?_⟩
    intro h
    exact hfiber h (Classical.choose (Set.rangeFactorization K h).property)
      (by
        simpa [Set.rangeFactorization] using
          (Classical.choose_spec (Set.rangeFactorization K h).property).symm)

/-
  R1 — Reflexive non-identification (a COROLLARY, not a new theorem). A system with global state space `H`,
  internal self-report map `ρ : H → S` (a monitor valued in an internal report space `S`), and target property
  `Θ : H → T` can CERTIFY `Θ` from its own report iff `Θ` is constant on the fibres of `ρ` — equivalently,
  self-certification FAILS iff `ρ` has a kernel pair on `Θ` (∃ h₁ h₂, ρ h₁ = ρ h₂ ∧ Θ h₁ ≠ Θ h₂). This is the
  deterministic factorization lemma above with `E := ρ`; it is provided as an explicit instantiation so the
  paper's reflexive-certification conditional carries its own kernel-checked certificate. The substance (the
  diagonal NECESSITY of a kernel pair under proper-part self-report) is R2 — NOT a corollary; see the paper.
-/
theorem reflexive_self_certification_iff_constant_on_report_fibers
    {H S T : Type*} (rho : H → S) (Theta : H → T) :
    (∃ certify : Set.range rho → T,
        ∀ h : H, Theta h = certify (Set.rangeFactorization rho h)) ↔
      (∀ h1 h2 : H, rho h1 = rho h2 → Theta h1 = Theta h2) :=
  deterministic_factorization_through_range_iff_constant_on_fibers rho Theta
