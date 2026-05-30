# External-prover dispatch epd-e6e55c39ab05

**Model**: gpt-5-2025-08-07
**Substrate**: gp225_rung3_t2p93_compose
**Dispatched**: 2026-05-17T21:44:51.258087+00:00
**Cost**: $0.1338
**Tokens**: 975 in / 4135 out

## Question

# Rung-3 proof-composition task (you are the independent composer; your output will be governed, not self-certified)

Produce ONE Lean 4 theorem that compiles VERBATIM in **Mathlib v4.29.0** (pinned; rev 8a178386ff). Output only the Lean code block, nothing else.

## Goal (prove exactly this; keep the name `T2P_93`)
```
theorem T2P_93 {E : Type*} [NormedAddCommGroup E] [CompleteSpace E]
    {x : α → E} (hx : Memℓp x 1) : Summable x
```

## Hard constraints (your proof will be kernel-governed; violations are auto-rejected)
- Pinned v4.29.0 ONLY. A convenient post-v4.29 one-shot closer for this exact statement is **ABSENT by construction** — do not rely on a single high-level lemma named like `summable_of_one`/`Memℓp.summable_one`; prove from pinned primitives.
- NO `sorry`, `admit`, `stop`, `native_decide`, declared `axiom`, `@[implemented_by]`. Governance runs `#print axioms` — only `propext`/`Classical.choice`/`Quot.sound` are allowed; anything else = rejected.
- Must NOT be closeable by a single bare-goal `exact?` (single-lemma laundering is rejected). A genuine multi-step proof is expected.
- Do not invent Mathlib names. Use real pinned lemmas.

## Pinned candidate primitives confirmed resolvable at v4.29.0 (use as relevant; not exhaustive)
`Memℓp.summable` (note: in v4.29 `Memℓp.summable` requires `0 < p.toReal`; for `p = 1`, `(1 : ℝ≥0∞).toReal = 1 > 0`, and it yields `Summable (fun i => ‖x i‖ ^ (1:ℝ).toReal-ish)` — reconcile the exponent), `ENNReal.toReal_one` (NOT `ENNReal.one_toReal`), `Real.rpow_one`, `Summable.of_norm` (`(Summable fun a => ‖f a‖) → Summable f`, needs `CompleteSpace`), plus the row's retrieval pool: `Asymptotics.IsBigO.comp_summable`, `Asymptotics.IsTheta.summable_iff`, `NormedAddCommGroup.summable_imp_tendsto_of_complete`, `summable_of_isBigO'`.

## Math sketch (you must verify/repair against the real Lean kernel; names/exponents may differ at the pin)
`Memℓp x 1` ⇒ `Summable (fun i => ‖x i‖ ^ (1:ℝ))` via `Memℓp.summable` with `0 < (1:ℝ≥0∞).toReal`; simplify `^ 1` (`Real.rpow_one`/`ENNReal.toReal_one`); then `Summable.of_norm` (needs `[CompleteSpace E]`, which is given) to get `Summable x`.

Return exactly one fenced ```lean block with the full `theorem T2P_93 … := by …`.


## Response

```lean
theorem T2P_93 {E : Type*} [NormedAddCommGroup E] [CompleteSpace E]
    {x : α → E} (hx : Memℓp x 1) : Summable x := by
  have hp : 0 < (1 : ℝ≥0∞).toReal := by
    simp [ENNReal.toReal_one]
  have hsum_rpow :
      Summable (fun i => ‖x i‖ ^ ((1 : ℝ≥0∞).toReal)) := by
    simpa using hx.summable hp
  have hsum1 : Summable (fun i => ‖x i‖ ^ (1 : ℝ)) := by
    simpa [ENNReal.toReal_one] using hsum_rpow
  have hsum_norm : Summable (fun i => ‖x i‖) := by
    simpa [Real.rpow_one] using hsum1
  exact Summable.of_norm hsum_norm
```
