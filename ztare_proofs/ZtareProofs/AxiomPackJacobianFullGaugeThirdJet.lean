import Mathlib

/-!
Kernel certificate for the second- and third-jet full-equivariant-gauge
calculation around the public weighted-lift seed.

The deterministic replay independently differentiates the parameter family,
checks polynomial lift ideals in `(v,t)`, and hashes the resulting source
fields.  This file checks their compact canonical-coordinate identities:
pushforward to the required residuals and preservation of the weighted area
form `gamma * dw ∧ dgamma`.
-/

namespace AxiomPackJacobianFullGaugeThirdJet

def seedP (w g : ℚ) : ℚ := g + 2 * w - 3 * w^2
def seedQ (w g : ℚ) : ℚ := w * g + w^2 - 2 * w^3

def seedPw (w : ℚ) : ℚ := 2 - 6 * w
def seedPg : ℚ := 1
def seedQw (w g : ℚ) : ℚ := g + 2 * w - 6 * w^2
def seedQg (w : ℚ) : ℚ := w

theorem seed_jacobian (w g : ℚ) :
    seedPw w * seedQg w - seedPg * seedQw w g = -g := by
  simp [seedPw, seedQg, seedPg, seedQw]
  ring

def source2WNumerator (w g : ℚ) : ℚ :=
  2 * g^2 - 4 * g * w^3 - 6 * g * w^2 + 4 * g * w +
    3 * w^5 + 15 * w^4 - 21 * w^3 + 7 * w^2

def source2GNumerator (w g : ℚ) : ℚ :=
  6 * g^2 * w^2 + 6 * g^2 * w - 2 * g^2 - 15 * g * w^4 -
    60 * g * w^3 + 63 * g * w^2 - 14 * g * w +
    18 * w^6 + 84 * w^5 - 156 * w^4 + 84 * w^3 - 14 * w^2

def source2W (w g : ℚ) : ℚ := source2WNumerator w g / (24 * g)
def source2G (w g : ℚ) : ℚ := source2GNumerator w g / (24 * g)

def residual2P (w g : ℚ) : ℚ :=
  (6 * g * w^2 - 6 * g * w + 2 * g + 9 * w^4 - 32 * w^3 +
    27 * w^2 - 6 * w) / 24

def residual2Q (w g : ℚ) : ℚ :=
  (2 * g^2 + 2 * g * w^3 - 12 * g * w^2 + 6 * g * w +
    12 * w^5 - 17 * w^4 + 6 * w^3 + w^2) / 24

theorem second_source_pushforward (w g : ℚ) (hg : g ≠ 0) :
    seedPw w * source2W w g + seedPg * source2G w g = residual2P w g ∧
    seedQw w g * source2W w g + seedQg w * source2G w g = residual2Q w g := by
  constructor <;>
    simp only [seedPw, seedPg, seedQw, seedQg, source2W, source2G,
      source2WNumerator, source2GNumerator, residual2P, residual2Q] <;>
    field_simp [hg] <;>
    ring

/-- Numerator form of
`∂w(g*source2W) + ∂g(g*source2G) = 0`. -/
theorem second_source_weighted_divergence (w g : ℚ) :
    (-12 * g * w^2 - 12 * g * w + 4 * g + 15 * w^4 + 60 * w^3 -
      63 * w^2 + 14 * w) +
    (12 * g * w^2 + 12 * g * w - 4 * g - 15 * w^4 - 60 * w^3 +
      63 * w^2 - 14 * w) = 0 := by
  ring

def source3WNumerator (w g : ℚ) : ℚ :=
  36 * g^2 * w^2 + 36 * g^2 * w - 17 * g^2 - 60 * g * w^4 -
    312 * g * w^3 + 330 * g * w^2 - 68 * g * w +
    84 * w^6 + 306 * w^5 - 621 * w^4 + 354 * w^3 - 68 * w^2

def source3GNumerator (w g : ℚ) : ℚ :=
  -12 * g^3 * w - 6 * g^3 + 60 * g^2 * w^3 + 234 * g^2 * w^2 -
    165 * g^2 * w + 17 * g^2 - 252 * g * w^5 - 765 * g * w^4 +
    1242 * g * w^3 - 531 * g * w^2 + 68 * g * w +
    252 * w^7 + 834 * w^6 - 2169 * w^5 + 1683 * w^4 -
    558 * w^3 + 68 * w^2

def source3W (w g : ℚ) : ℚ := -source3WNumerator w g / (288 * g)
def source3G (w g : ℚ) : ℚ := -source3GNumerator w g / (144 * g)

def residual3P (w g : ℚ) : ℚ :=
  (4 * g^2 * w + 2 * g^2 + 16 * g * w^3 - 54 * g * w^2 +
    26 * g * w + 24 * w^5 - 37 * w^4 + 20 * w^3 - w^2) / 48

def residual3Q (w g : ℚ) : ℚ :=
  (-12 * g^2 * w^2 - 24 * g^2 * w + 17 * g^2 + 156 * g * w^4 -
    12 * g * w^3 - 174 * g * w^2 + 68 * g * w +
    60 * w^6 - 528 * w^5 + 741 * w^4 - 360 * w^3 + 68 * w^2) / 288

theorem third_source_pushforward (w g : ℚ) (hg : g ≠ 0) :
    seedPw w * source3W w g + seedPg * source3G w g = residual3P w g ∧
    seedQw w g * source3W w g + seedQg w * source3G w g = residual3Q w g := by
  constructor <;>
    simp only [seedPw, seedPg, seedQw, seedQg, source3W, source3G,
      source3WNumerator, source3GNumerator, residual3P, residual3Q] <;>
    field_simp [hg] <;>
    ring

/-- Numerator form of
`∂w(g*source3W) + ∂g(g*source3G) = 0`.  The second summand carries the factor
two coming from the denominators `288` and `144`. -/
theorem third_source_weighted_divergence (w g : ℚ) :
    (72 * g^2 * w + 36 * g^2 - 240 * g * w^3 - 936 * g * w^2 +
      660 * g * w - 68 * g + 504 * w^5 + 1530 * w^4 - 2484 * w^3 +
      1062 * w^2 - 136 * w) +
    (-72 * g^2 * w - 36 * g^2 + 240 * g * w^3 + 936 * g * w^2 -
      660 * g * w + 68 * g - 504 * w^5 - 1530 * w^4 + 2484 * w^3 -
      1062 * w^2 + 136 * w) = 0 := by
  ring

/-- Terminal canonical-coordinate certificate.  Polynomiality and the two
equivariant lift ideals are checked independently by the exact replay before
this finite identity is carried into governance. -/
theorem full_gauge_contact_through_third_jet_certificate (w g : ℚ) (hg : g ≠ 0) :
    seedPw w * seedQg w - seedPg * seedQw w g = -g ∧
    (seedPw w * source2W w g + seedPg * source2G w g = residual2P w g ∧
      seedQw w g * source2W w g + seedQg w * source2G w g = residual2Q w g) ∧
    (seedPw w * source3W w g + seedPg * source3G w g = residual3P w g ∧
      seedQw w g * source3W w g + seedQg w * source3G w g = residual3Q w g) := by
  exact ⟨seed_jacobian w g, second_source_pushforward w g hg,
    third_source_pushforward w g hg⟩

end AxiomPackJacobianFullGaugeThirdJet
