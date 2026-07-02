# Restricted-payments covenant: faithful permission logic + two safety invariants

## Domain
formalization-compliance

## Source (verbatim, a real public covenant)

Section 4.07 (RESTRICTED PAYMENTS) of a high-yield note indenture (Chattem, Inc., SEC EDGAR
`a2039699zex-4_2.txt`). The operative test: the Company shall not make a Restricted Payment (dividends /
equity repurchases / junior-debt prepayments / Restricted Investments — clauses (i)–(iv)) **unless, at the
time of and after giving effect to such Restricted Payment**, ALL THREE conditions hold:

- **(a)** no Default or Event of Default has occurred and is continuing, or would occur as a consequence;
- **(b)** the Company could, on a pro forma basis, incur at least $1.00 of additional Indebtedness under the
  Fixed Charge Coverage Ratio test of Section 4.09;
- **(c)** the Restricted Payment, **together with the aggregate of all other Restricted Payments** made since
  the Indenture date (**excluding** those permitted by clauses (ii), (iii), (iv) of the succeeding paragraph),
  is **less than** the builder basket (50% of cumulative Consolidated Net Income since the Indenture, plus
  further add-ins).

## Abstraction directive (the engine performs this from NL — do NOT pre-solve it)

Do not model the accounting internals. Treat the following as OPAQUE given predicates/quantities over an
abstract financial `State` and a Restricted Payment `rp` with a real `amount`:

- `NoDefault : State → Prop`      — condition (a) holds at the state (no Default continuing / arising);
- `FCCRTestPasses : State → Prop`  — condition (b): the pro-forma Fixed Charge Coverage Ratio test admits ≥ $1.00 of additional debt;
- `builderBasket : State → ℝ`      — the clause-(c) cap (50% cumulative Consolidated Net Income + add-ins);
- `cumulativeRP  : State → ℝ`      — aggregate of all prior Restricted Payments counted against the basket (already net of the (ii)(iii)(iv) carve-outs);
- `amount : RP → ℝ`.

Formalize the PERMISSION LOGIC faithfully — the part the covenant actually turns on and where a mis-reading
changes which payments are allowed. This is the contested structure; keep it exact.

## Target

Faithful covenant predicate:

`Permitted (s : State) (rp : RP) : Prop := NoDefault s ∧ FCCRTestPasses s ∧ (cumulativeRP s + amount rp < builderBasket s)`

Prove BOTH safety invariants (each holds only if the logic above is faithful):

1. **Default block.** A continuing Default forbids every Restricted Payment, whatever the coverage or basket
   headroom: `∀ s rp, ¬ NoDefault s → ¬ Permitted s rp`.
2. **Basket exhaustion.** Once prior Restricted Payments reach the builder basket, no further positive
   Restricted Payment is permitted until the basket grows:
   `∀ s rp, builderBasket s ≤ cumulativeRP s → 0 < amount rp → ¬ Permitted s rp`.

## Faithfulness guards (anti-weakening — the closure must honor these, never a silent retreat)

- Condition is a THREE-way conjunction (`∧`), never a disjunction — a payment needs (a) AND (b) AND (c), not
  any one of them. A `∨` reading is a laundering and must not close.
- Clause (c) is a STRICT inequality (`<`), not `≤` — a payment landing exactly at the basket is NOT permitted.
- No dropped conjunct: dropping (a), (b), or (c) changes which payments pass and must not close.
- The basket in (c) is net of the (ii)(iii)(iv) carve-outs (captured in `cumulativeRP`); do not fold the
  carved-out payments back in.
- Invariant 2 needs `0 < amount rp` — do not weaken to `≤` or drop it (a zero-amount payment at an exhausted
  basket is a boundary case, not a breach).

## Matched negative controls (for the faithfulness-certification pass — NOT to be filed as closures)

Each laundered predicate should FAIL the firewall and make one invariant kernel-false with a distinguishing
`State`:

- `Permitted_drop_c := NoDefault s ∧ FCCRTestPasses s`  — drops (c); breaks Basket exhaustion (witness: an
  exhausted-basket state that this reading still permits).
- `Permitted_or := NoDefault s ∨ FCCRTestPasses s ∨ (cumulativeRP s + amount rp < builderBasket s)` — `∧→∨`;
  breaks Default block (witness: a defaulted state with basket headroom).
- `Permitted_le := NoDefault s ∧ FCCRTestPasses s ∧ (cumulativeRP s + amount rp ≤ builderBasket s)` — `<→≤`;
  breaks Basket exhaustion at the boundary (witness: `cumulativeRP s = builderBasket s`, `amount rp = 0`… use
  the exact-boundary payment the strict reading forbids).
