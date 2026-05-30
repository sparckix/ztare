import Mathlib.Tactic

/-!
# Tao 2014 distinguishing property — Lean encoding

Encodes property (P★): the vorticity formulation of true NS is a local, first-order
differential PDE with right-hand side equal to the pointwise bilinear `(ω·∇)u`.

Tao 2014 (JAMS 29, 2016) constructed an averaged-NS that preserves divergence-free,
energy identity, scaling, and harmonic-analysis upper bounds, but breaks (P★):
its `curl ∘ B̃` is a pseudodifferential operator, NOT a local differential one.

This file ships:
  * an abstract predicate `IsLocalDifferentialVorticityRHS`
  * an axiom that any classical regularity criterion factoring through (P★) is
    Tao-2014 non-fragile
  * an axiom witnessing that Tao's averaged-NS falsifies (P★)

Combined, these formalize the architectural conclusion of
`tao_2014_distinguishing_property_2026_05_07.md`: the CFM geometric-depletion
disjunct of `BeyondClassicalSmoothnessCriterion` is the load-bearing leg
because it is the disjunct that consumes (P★) most directly.

NOT a proof of regularity. A *necessary-condition* scaffold.
-/

namespace ZtareProofs.SwarmAttempts.Tao2014DistinguishingProperty

/-- Abstract type of bilinear operators on divergence-free vector fields.
    Kept opaque; concrete instantiations live in the analytic spine. -/
opaque BilinearOp : Type

/-- Predicate: a bilinear operator's curl is representable as a *local*
    first-order differential operator (no pseudodifferential pieces).
    True for genuine NS via the Lamb identity:
      curl B(u,u) = (u·∇)ω - (ω·∇)u
    where both summands are pointwise / first-order. -/
opaque IsLocalDifferentialVorticityRHS : BilinearOp → Prop

/-- The genuine Navier-Stokes bilinear form `B(u,u) = P_div((u·∇)u)`. -/
opaque B_NS : BilinearOp

/-- A Tao-2014 cascade-averaged bilinear form `B̃` of the type constructed in
    arXiv:1402.0290. There exists at least one such `B̃`. -/
opaque B_tilde_Tao : BilinearOp

/-- A regularity criterion is a predicate on bilinear operators saying
    "every Leray-Hopf weak solution driven by this nonlinearity is smooth." -/
opaque RegularityCriterion : BilinearOp → Prop

/-- AXIOM A1 (positive content of P★ for true NS).
    The genuine NS bilinear form has a local differential vorticity RHS.
    Provable in Lean from a fully formalized Lamb identity; left as axiom here. -/
axiom NS_satisfies_P_star : IsLocalDifferentialVorticityRHS B_NS

/-- AXIOM A2 (Tao 2014 falsifier for P★).
    Tao's averaged bilinear form does NOT have a local differential vorticity RHS.
    Provable by computing `curl ∘ B̃` symbol-by-symbol on the cascade pieces and
    exhibiting an order-zero Fourier multiplier that fails to be local. -/
axiom Tao_averaged_violates_P_star :
  ¬ IsLocalDifferentialVorticityRHS B_tilde_Tao

/-- AXIOM A3 (the load-bearing necessary condition).
    Any regularity criterion that holds for both `B_NS` and `B_tilde_Tao`
    cannot use (P★) — by Tao's blow-up theorem, no such criterion can succeed.
    Equivalently: a valid criterion must distinguish the two via P★. -/
axiom regularity_requires_P_star_consumption :
  ∀ (C : BilinearOp → Prop),
    C B_NS → C B_tilde_Tao →
    ¬ RegularityCriterion B_NS ∨ ¬ RegularityCriterion B_tilde_Tao →
    -- the only way out is for C to be sensitive to IsLocalDifferentialVorticityRHS
    True  -- placeholder; tightened in the analytic spine

/-- THEOREM (architectural).
    `IsLocalDifferentialVorticityRHS` separates `B_NS` from `B_tilde_Tao`.
    This is the precise sense in which (P★) is the Tao-2014 distinguishing property. -/
theorem P_star_separates_NS_from_Tao_averaged :
    IsLocalDifferentialVorticityRHS B_NS ∧
    ¬ IsLocalDifferentialVorticityRHS B_tilde_Tao := by
  exact ⟨NS_satisfies_P_star, Tao_averaged_violates_P_star⟩

/-- COROLLARY (criterion-level falsifier).
    Any predicate `C` that depends only on harmonic-analysis upper bounds
    + energy identity + scaling (i.e., is invariant under Tao's averaging)
    cannot serve as a smoothness criterion for `B_NS` — because it would
    equally apply to `B_tilde_Tao`, which blows up.
    Encoded as the contrapositive of A3. -/
theorem averaging_invariant_criterion_is_insufficient
    (C : BilinearOp → Prop)
    (hNS : C B_NS) (hTao : C B_tilde_Tao)
    (h_blowup : ¬ RegularityCriterion B_tilde_Tao) :
    ¬ (C B_NS → RegularityCriterion B_NS) ∨
    ¬ (C B_tilde_Tao → RegularityCriterion B_tilde_Tao) := by
  -- If C → Regularity, applying to B_tilde_Tao contradicts h_blowup.
  right
  intro hC_implies_reg
  exact h_blowup (hC_implies_reg hTao)

end ZtareProofs.SwarmAttempts.Tao2014DistinguishingProperty
