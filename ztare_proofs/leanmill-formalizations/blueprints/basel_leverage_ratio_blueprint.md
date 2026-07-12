# Basel III Leverage Ratio — a non-risk-based capital backstop

Opens a new domain for the library: **prudential banking regulation (Basel III)**. The leverage ratio is Basel
III's deliberately crude companion to the risk-weighted capital ratios: Tier-1 capital divided by a **total
exposure measure** must not fall below a flat **3%** floor, with *no risk weighting at all*. Its whole reason for
existing is contested institutional intent, not mathematics — after 2008 the Committee added it precisely because
risk weights are model-dependent and gameable, so a bank could show a comfortable risk-weighted ratio while being
catastrophically levered on assets its own models rated near-zero-risk. The leverage ratio is the **backstop that
binds when the risk weights are gamed**. That intent — "a floor that holds regardless of how the assets are
weighted" — is exactly the kind of non-mathematical, numeric-boundary rule this library exists to formalize
faithfully and certify, and no filed result yet exercises the numeric-boundary firewall.

Assumption-accounting note: the results depend on (1) **nonnegativity** — Tier-1 capital and every exposure
component are nonnegative monetary quantities; (2) the **total exposure measure** being the genuine on-balance-
sheet *plus* off-balance-sheet-via-credit-conversion measure (a measure at least as large as on-balance assets
alone — the conservatism is the point, so it must not be modelled as on-balance-only); (3) the **3% floor** and
the **8% risk-weighted capital minimum** as the actual Basel Pillar-1 constants, not free parameters. Surface where
each is used. Keep the model over an ordered field of real-valued quantities; do **not** collapse it to a fixed
decidable integer instance (that would trivialize the boundary the firewall is meant to police). A non-closure is
an honest gap, never a fake closure.

## Domain
formalization-nonmath

## Theory file
basel_leverage_theory.lean

## Vocabulary (build these as definitions — do not prove them)
- **Total exposure measure**: an institution's total exposure is its on-balance-sheet assets plus its
  off-balance-sheet notional scaled by a credit-conversion factor in `[0,1]`; hence total exposure is nonnegative
  and at least as large as on-balance-sheet assets alone.
- **Leverage-compliant**: an institution is leverage-compliant when its Tier-1 capital is at least 3% of its total
  exposure measure — i.e. `100 · tier1 ≥ 3 · exposure` (the ratio `tier1 / exposure ≥ 3/100`, cross-multiplied to
  avoid division and keep the boundary exact).
- **Risk-weighted capital floor**: with an effective average risk weight `w ∈ [0,1]` applied to exposure, the
  risk-weighted capital requirement is 8% of risk-weighted assets — i.e. Tier-1 capital at least `(8/100) · (w ·
  exposure)`.

## Target
Consider an institution described by a nonnegative Tier-1 capital level and a nonnegative total exposure measure
(on-balance-sheet assets plus credit-converted off-balance-sheet exposure), together with an effective average
risk weight `w` between 0 and 1 that its risk-weighted capital requirement is computed against. The Basel leverage
ratio requirement is that Tier-1 capital be at least 3% of total exposure; the risk-weighted capital requirement
is that Tier-1 capital be at least 8% of risk-weighted assets (`w · exposure`). The claim is that the leverage
ratio is a genuine **non-risk-based backstop**: whenever the risk weight is low enough that the risk-weighted floor
does not already dominate — precisely when `8 · w ≤ 3`, i.e. the effective risk weight is at or below 37.5% —
every leverage-compliant institution automatically satisfies its risk-weighted capital requirement as well. In
that regime the flat leverage floor subsumes the risk-weighted one, so a bank that games its risk weights toward
zero cannot use a thin risk-weighted ratio to escape the capital the leverage floor independently demands. Surface
that the conclusion uses nonnegativity of exposure, the range of `w`, and the crossover boundary `8 · w ≤ 3`.

## Lemmas
- The leverage requirement caps total exposure at `100/3` (≈ 33.3) times Tier-1 capital: every leverage-compliant
  institution has total exposure at most `(100/3) · tier1`.
- Consolidating two leverage-compliant books yields a leverage-compliant book: if two institutions are each
  leverage-compliant, the merged institution — Tier-1 capital added and total exposure added — is leverage-compliant.
- Raising capital preserves compliance: a leverage-compliant institution that increases its Tier-1 capital while
  holding total exposure fixed remains leverage-compliant.
- Deleveraging preserves compliance: a leverage-compliant institution that reduces its total exposure while
  holding Tier-1 capital fixed remains leverage-compliant.
- The 3% floor is sharp: an institution whose Tier-1 capital is exactly 3% of total exposure (`100 · tier1 = 3 ·
  exposure`) is leverage-compliant, while any institution strictly below the floor (`100 · tier1 < 3 · exposure`)
  is not.

## Idea
Everything is linear arithmetic over an ordered field of nonnegative real-valued quantities; the value is the
faithful non-mathematical model and the certified numeric boundary, not proof depth. Keep the ratios cross-
multiplied (`100 · tier1 ≥ 3 · exposure`, `100 · tier1 ≥ 8 · w · exposure`) so no division or positivity-of-
denominator side-condition is needed and the 3% / 8% boundaries stay exact. For the backstop target: from
leverage-compliance, `100 · tier1 ≥ 3 · exposure`; when `8 · w ≤ 3` and `exposure ≥ 0`, multiply to get `3 ·
exposure ≥ 8 · w · exposure`, so `100 · tier1 ≥ 8 · w · exposure`, which is exactly the risk-weighted requirement —
one `nlinarith`/`linarith` step once the `8·w ≤ 3` boundary and `exposure ≥ 0` are in hand. The exposure cap is
dividing the compliance inequality by 3. Consolidation and the two monotonicity lemmas are adding or weakening the
compliance inequality (`linarith`). Sharpness is the boundary being inclusive (`≥`) on one side and its strict
negation on the other. The `8·w ≤ 3` crossover and the 3% / 8% floors are the genuine regulatory content — state
and use them as the actual Basel constants; do not generalize them into free parameters and do not fix the field
to a decidable integer toy.
