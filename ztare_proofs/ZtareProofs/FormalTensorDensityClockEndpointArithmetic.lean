import Mathlib.Tactic

/-!
# Endpoint arithmetic for the weight-3/2 density clock

The selected density-clock continuation has first fractional exponent `5/2`.
At a simple nonzero root of the polynomial residual, cubic clock inversion
would force a polynomial-generator root multiplicity `3/2`.  At infinity,
leading balance gives `2 * e = 3 * d + 2`; hence `d` is even and the
fractional increment `3/2` is outside the `1 / (d - 1)` exponent lattice.

This file owns those characteristic-zero arithmetic contradictions.  It does
not construct the selected analytic continuation or prove the local clock
expansions that instantiate them.
-/

namespace FormalTensorDensityClockEndpointArithmetic

/-- A finite nonzero zero of multiplicity `r` has clock exponent
`1 - 2*r/3`.  Matching a nonzero linear source clock with positive endpoint
ramification forces a simple zero and cubic leading displacement. -/
theorem finite_zero_balance_forces_simple_cubic
    (r : ℕ) (ramification : ℚ)
    (hr : 1 ≤ r) (hramification : 0 < ramification)
    (hbalance : ramification * (3 - 2 * (r : ℚ)) = 3) :
    r = 1 ∧ ramification = 3 := by
  have hrational : (1 : ℚ) ≤ (r : ℚ) := by
    exact_mod_cast hr
  have hdenominator : 0 < 3 - 2 * (r : ℚ) := by
    nlinarith
  have hrUpper : (r : ℚ) < 2 := by
    linarith
  have hrNatUpper : r < 2 := by
    exact_mod_cast hrUpper
  have hrequal : r = 1 := by omega
  subst r
  constructor
  · rfl
  · norm_num at hbalance
    exact hbalance

/-- Cubic inversion of a `5/2` germ would demand the nonintegral
multiplicity `1 + ((5/2)-1)/3 = 3/2`. -/
theorem simple_root_forced_multiplicity_impossible
    (multiplicity : ℕ)
    (hforced :
      (multiplicity : ℚ) =
        1 + (((5 : ℚ) / 2) - 1) / 3) :
    False := by
  have htwice : (2 * multiplicity : ℚ) = 3 := by
    norm_num at hforced ⊢
    linarith
  have htwiceNat : 2 * multiplicity = 3 := by
    exact_mod_cast htwice
  omega

/-- The infinity degree balance forces the polynomial generator degree to be
even. -/
theorem generator_degree_even_of_infinity_balance
    (generatorDegree residualDegree : ℕ)
    (hbalance : 2 * residualDegree = 3 * generatorDegree + 2) :
    Even generatorDegree := by
  have hresidual : 1 ≤ residualDegree := by omega
  have htwoThree : 2 ∣ 3 * generatorDegree := by
    refine ⟨residualDegree - 1, ?_⟩
    omega
  have hcoprime : Nat.Coprime 2 3 := by decide
  obtain ⟨half, hhalf⟩ := hcoprime.dvd_of_dvd_mul_left htwoThree
  exact ⟨half, by omega⟩

/-- Under the infinity balance, `3/2` is not in the Puiseux lattice generated
by `1/(d-1)`. -/
theorem three_halves_outside_infinity_lattice
    (generatorDegree residualDegree latticeIndex : ℕ)
    (hdegree : 2 ≤ generatorDegree)
    (hbalance : 2 * residualDegree = 3 * generatorDegree + 2) :
    (latticeIndex : ℚ) / ((generatorDegree - 1 : ℕ) : ℚ) ≠
      (3 : ℚ) / 2 := by
  intro hlattice
  have hdenNat : 0 < generatorDegree - 1 := by omega
  have hden : ((generatorDegree - 1 : ℕ) : ℚ) ≠ 0 := by
    exact_mod_cast (Nat.ne_of_gt hdenNat)
  have hcross :
      (2 * latticeIndex : ℚ) =
        3 * ((generatorDegree - 1 : ℕ) : ℚ) := by
    rw [div_eq_iff hden] at hlattice
    linarith
  have hcrossNat :
      2 * latticeIndex = 3 * (generatorDegree - 1) := by
    exact_mod_cast hcross
  obtain ⟨half, hhalf⟩ :=
    generator_degree_even_of_infinity_balance
      generatorDegree residualDegree hbalance
  omega

/-- The coefficient equation in the new infinity coset is itself
incompatible with a polynomial degree at least two. -/
theorem infinity_fractional_coefficient_impossible
    (generatorDegree : ℕ)
    (hdegree : 2 ≤ generatorDegree)
    (hcoefficient :
      (generatorDegree : ℚ) =
        1 - ((3 : ℚ) / 2) *
          ((generatorDegree - 1 : ℕ) : ℚ)) :
    False := by
  have hdegreeQ : (2 : ℚ) ≤ generatorDegree := by
    exact_mod_cast hdegree
  have hsubNonnegative : (0 : ℚ) ≤ generatorDegree - 1 := by
    have : (1 : ℚ) ≤ generatorDegree := by linarith
    linarith
  linarith

/-- Aggregated arithmetic surface for the root and infinity branches. -/
theorem tensor_density_clock_endpoint_arithmetic_terminal_certificate :
    (∀ (r : ℕ) (ramification : ℚ),
      1 ≤ r → 0 < ramification →
      ramification * (3 - 2 * (r : ℚ)) = 3 →
      r = 1 ∧ ramification = 3) ∧
    (∀ multiplicity : ℕ,
      (multiplicity : ℚ) =
          1 + (((5 : ℚ) / 2) - 1) / 3 →
        False) ∧
    (∀ generatorDegree residualDegree : ℕ,
      2 * residualDegree = 3 * generatorDegree + 2 →
        Even generatorDegree) ∧
    (∀ generatorDegree residualDegree latticeIndex : ℕ,
      2 ≤ generatorDegree →
      2 * residualDegree = 3 * generatorDegree + 2 →
      (latticeIndex : ℚ) / ((generatorDegree - 1 : ℕ) : ℚ) ≠
        (3 : ℚ) / 2) ∧
    (∀ generatorDegree : ℕ,
      2 ≤ generatorDegree →
      (generatorDegree : ℚ) =
          1 - ((3 : ℚ) / 2) *
            ((generatorDegree - 1 : ℕ) : ℚ) →
        False) := by
  exact ⟨finite_zero_balance_forces_simple_cubic,
    simple_root_forced_multiplicity_impossible,
    generator_degree_even_of_infinity_balance,
    three_halves_outside_infinity_lattice,
    infinity_fractional_coefficient_impossible⟩

/-! ## Inhomogeneous Duhamel-coordinate arithmetic -/

/-- On a through-infinity sheet for an actor of degree `d`, a module
monomial of degree `e` has Duhamel exponent
`(5*d+5-2*e)/(2*d)`.  It cannot equal `3/2`: clearing denominators would
equate an even integer with `2*d+5`.  The statement applies to every integer
monomial degree, not only the leading one. -/
theorem duhamel_three_halves_not_from_infinity
    (actorDegree moduleDegree : ℤ) :
    5 * actorDegree + 5 - 2 * moduleDegree ≠ 3 * actorDegree := by
  omega

/-- If the start and terminal equilibria have multiplicities `m,n ≥ 2`,
the cleared `3/2` Duhamel exponent equation reduces to
`(m-1)*(2*q-2*n-1)=0`.  Both factors are nonzero: the first by multiplicity,
the second by parity. -/
theorem duhamel_three_halves_not_from_multiple_equilibria
    (startMultiplicity terminalMultiplicity moduleVanishingOrder : ℤ)
    (hstart : 2 ≤ startMultiplicity)
    (hterminal : 2 ≤ terminalMultiplicity) :
    3 * startMultiplicity * (terminalMultiplicity - 1) +
          (startMultiplicity - 1) *
            (2 * moduleVanishingOrder + 2 - 5 * terminalMultiplicity) ≠
        3 * (terminalMultiplicity - 1) := by
  intro hbalance
  have _hterminalDenominator : terminalMultiplicity - 1 ≠ 0 := by
    omega
  have hfactor :
      (startMultiplicity - 1) *
          (2 * moduleVanishingOrder - 2 * terminalMultiplicity - 1) = 0 := by
    calc
      (startMultiplicity - 1) *
          (2 * moduleVanishingOrder - 2 * terminalMultiplicity - 1) =
          (3 * startMultiplicity * (terminalMultiplicity - 1) +
              (startMultiplicity - 1) *
                (2 * moduleVanishingOrder + 2 -
                  5 * terminalMultiplicity)) -
            3 * (terminalMultiplicity - 1) := by ring
      _ = 0 := sub_eq_zero.mpr hbalance
  rcases mul_eq_zero.mp hfactor with hstartZero | hparity
  · omega
  · omega

/-- Negative control: the preceding parity argument deliberately says
nothing at a simple starting equilibrium.  Its multiplicity factor vanishes
identically, leaving room for a finite integration constant times
`u^(3/2)`. -/
theorem simple_equilibrium_not_excluded_by_multiple_parity
    (terminalMultiplicity moduleVanishingOrder : ℤ) :
    ((1 : ℤ) - 1) *
        (2 * moduleVanishingOrder - 2 * terminalMultiplicity - 1) = 0 := by
  ring

/-- Aggregated arithmetic boundary for a Duhamel residual whose first
fractional exponent is `3/2`.  Analytic construction of the characteristic
formula and continuation routing are intentionally outside this terminal. -/
theorem tensor_density_duhamel_ramification_arithmetic_terminal_certificate :
    (∀ actorDegree moduleDegree : ℤ,
      5 * actorDegree + 5 - 2 * moduleDegree ≠ 3 * actorDegree) ∧
    (∀ startMultiplicity terminalMultiplicity moduleVanishingOrder : ℤ,
      2 ≤ startMultiplicity →
      2 ≤ terminalMultiplicity →
      3 * startMultiplicity * (terminalMultiplicity - 1) +
            (startMultiplicity - 1) *
              (2 * moduleVanishingOrder + 2 - 5 * terminalMultiplicity) ≠
          3 * (terminalMultiplicity - 1)) ∧
    (∀ terminalMultiplicity moduleVanishingOrder : ℤ,
      ((1 : ℤ) - 1) *
          (2 * moduleVanishingOrder - 2 * terminalMultiplicity - 1) = 0) := by
  exact ⟨duhamel_three_halves_not_from_infinity,
    duhamel_three_halves_not_from_multiple_equilibria,
    simple_equilibrium_not_excluded_by_multiple_parity⟩

end FormalTensorDensityClockEndpointArithmetic
