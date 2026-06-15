---
description: "LeanMill positioning: a receipts-first account of what it is, who it is for, and the kernel-certified guarantee it sells."
---

# LeanMill — positioning (receipts-first)

## What it is, plainly

LeanMill turns an ambiguous specification (a compliance rule, an access policy, a math claim) into a
**kernel-certified** guarantee. Three engines, each doing the one thing it is good at:

- an **agent** (subscription codex/claude) translates intent → a formal statement;
- an **SMT solver** (z3 quantifier-elimination / cvc5) searches the boundary — the missing premise, the
  policy combination, the off-by-one that flips a decision;
- the **Lean 4 kernel** ratifies, emitting an auditable certificate (`#print axioms ⊆ {propext,
  Classical.choice, Quot.sound}`, no `sorry`, no smuggled axiom).

It is not a semantic wrapper that asks a model for code and retries. Every output the agent produces is
**independently re-verified by the kernel**; the agent is never trusted.

## The differentiator, measured (not asserted)

A frequent objection: "a strong model is already accurate — what do you add?" We measured it. On the
numeric compliance class, a steelmanned agent judge matched the kernel's faithfulness verdict exactly
(3/3 laundered caught, 0 false positives). So the differentiator is **not** the verdict — it is the
**auditable certificate**. You cannot sue an LLM for a hallucinated compliance opinion; you can stand
behind a kernel proof. **Verifiability is the product.**

## Receipts (measured 2026-06-09, each through the **real** wired kernel + governance)

THE differentiating receipt — governance under adversarial pressure:

| the differentiator | result | what it shows |
|---|---|---|
| anti-laundering on an OPEN target | denef_lipshitz: agent produced **3 closes that compiled, no `sorry`, clean axioms** — `statement_integrity` rejected ALL three (`ratified=0`) | a naive "it compiled" verifier accepts all three; the governance catches the faithless close. **This is the differentiator** — you cannot get it from a stronger model, because the model is what's being policed. |
| autoformalization firewall | **13/13 domains** (compliance, pharma/HIPAA/aviation/export, DeFi incl. nonlinear `k≤x·y`, IAM: terminated-contractor / MFA / SoD / RBAC) | NL rule → Lean predicate; faithful admitted, laundered (∧→∨ / off-by-one / dropped-conjunct / `<`vs`≤`) caught by the kernel |
| firewall vs steelmanned agent judge | agent = kernel on accuracy | the differentiator is the **cert**, not the verdict |

Capability receipts (the *environment* multiplying the leaf — but NOT a capability edge over a shell-agent; see the architecture doc's SETTLED note):

| capability | result | honest reading |
|---|---|---|
| P1 rungs (construct NEW proofs not in Mathlib) | **L0 / RUNG C / RUNG B** kernel-closed, axioms ⊆ {propext, Classical.choice, Quot.sound} | the open-problem regime: builds the proof bottom-up, governance keeps it sound |
| witness-transport (SymPy → Lean) | 12/12 closure **vs native Lean tactics** (0/12) | a cheap **deterministic** lever the leaf *prefers* over hand-rolling a solver (measured: 5 tool-calls / 0 self-coded). NOT an edge vs a shell-agent, which recalls/self-codes the same compute. |
| QE-abduction (z3 QE → Lean) | 6/6 advance vs blind conjecture | the most-general missing premise (Dillig "Explain"), kernel-admitted — same reliability lever |

`solve_witness` / `qe_abduct_premise` / `default_instance_battery` / `solve_adhoc_governed` are the **real**
wired functions; no re-implemented per-experiment battery.

## The near-term wedge: decidable systems assurance

Order the use cases by what the math actually allows, not by market size:

- **Strongest now — Cloud IAM / access-policy verification.** Policies are decidable (linear/boolean), which
  is exactly z3 QE's domain. "Is there any scenario where a terminated contractor can read prod?" *is* a
  quantifier-elimination query: eliminate the role variables, return the witness. This is the mechanism we
  wired and measured.
- **Strong — algorithmic compliance/regulation.** Threshold logic (Basel CET1, Reg-T margin, tax cliffs) —
  the 7 validated domains are exactly this shape.
- **Aspirational — DeFi / smart-contract defense.** Contract arithmetic is often *nonlinear*, where both z3
  QE and cvc5 abduction break down (undecidable over ℤ — measured). Do not lead with it.

## Honest gaps (kept, not hidden)

- Everything validated is **toy-scale** (5-case batteries, single-threshold predicates). The bottleneck to
  real-world claims is **autoformalizer robustness** at the complexity of a 1000-page regulation or a real
  contract — the least-validated of the three engines.
- Several moves are SUBSUMED on easy substrates (reflection by `decide`, degree-2 abduce by `nlinarith`) —
  lift exists only where the native cascade is genuinely blind.

## Why open source

Trust is the product, and you cannot sell cryptographic certainty as a proprietary black box. Open-sourcing
the governance layer (the faithfulness firewall + the anti-laundering kernel) lets the security community
audit that the kernel does not launder — and lets banks/defense run it air-gapped with their own weights.
That auditability is also what the autoresearch loop provides as living proof: the same discipline is
self-applied to LeanMill's own development (every capability here was measured with a 0-control and a
carrier preflight, not asserted).
