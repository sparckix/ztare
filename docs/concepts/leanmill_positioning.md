---
description: "What LeanMill is, who it's for, and the receipts behind the claims."
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

## What it actually adds

A frequent objection: "a strong model is already accurate — what do you add?" We measured it, over 7
compliance domains (14 faithful/laundered cases). On **catch-rate** the steelmanned agent judge tied the
kernel (both caught 7/7 launderings — these off-by-ones are visible in the formula text, so the judge
reads them). The kernel's measured edge is **precision + verifiability**: firewall **14/14 = 100%** (0
false-alarms) vs. judge **13/14 = 93%** (it false-rejected one *faithful* rule), and every firewall verdict
is an **auditable certificate** rather than an opinion. You cannot sue an LLM for a hallucinated compliance
opinion; you can stand behind a kernel proof. **Verifiability is the product** — and a verifier that never
false-rejects a compliant rule. (We also **built and measured** the harder *must-search* class — boolean
precedence flips, divisibility refactors, linear-combination disguises — and the frontier judge caught those
too, 3/3: it *reasons* through them. So we claim **no catch-rate edge** against a strong judge; the edge is
precision + the certificate. Receipts: `analytics/public/leanmill/results/nonmath_mustsearch_ab.md`.)

The certificate point made concrete (`certify_policy_faithfulness`, a typed 3-verdict artifact — CERTIFIED_EQUIVALENT / REFUTED-with-a-distinguishing-input / OUT_OF_FRAGMENT, composing z3 + Gröbner + the Lean kernel; lineage PCP/IP, Rice, Gröbner/Farkas): on an **N=18** policy corpus across 8 compliance domains the engine *decides* all 18 and agrees with the z3 ground truth — but the engine **is** z3, so that's a **consistency check, not an accuracy claim**. The real signals: every verdict is a checkable artifact, and vs the **independent** judge oracle the result is a **kept null** (the N=5 witness gap 3/3-vs-2/3 did not replicate; at N=18 the judge matched it 18/18, 9/9). The edge is the **soundness guarantee** (a decision-procedure certificate vs an unguaranteed opinion), not a number. The same trichotomy drives a **transport-to-decidability router** whose *decidable-fraction lift* is **+3 (portfolio 5/7 vs single-theory 2/7)** on a mixed math+policy seed (`results/{certify_policy_corpus_run,decidability_router}.md`).

## Receipts (each through the **real** wired kernel + governance)

**Soundness — adversarial red-team (2026-06-16).** The one claim a verification reviewer should stress: *no
false closures*. We tried to smuggle an unsound "closure" past the production gate (`audit_external`) — and
every attack was rejected, the genuine proof passed:

| attack | gate verdict |
|---|---|
| `sorry` / `admit` / nested `sorry` | **rejected** (sorryAx caught) |
| `native_decide` ⇒ `Lean.ofReduceBool` | **rejected** (axiom outside the {propext, Classical.choice, Quot.sound} allowlist) |
| false custom `axiom` + cite it | **rejected** (extra axiom caught) |
| genuine clean proof (control) | **passes** |

→ **catch-rate 5/5 = 100%, 0 false-flags.** Re-runnable: `PYTHONPATH=src python projects/leanmill_experiments/governance_redteam.py`.

THE differentiating receipt — governance under adversarial pressure:

| the differentiator | result | what it shows |
|---|---|---|
| anti-laundering on an OPEN target | denef_lipshitz: agent produced **3 closes that compiled, no `sorry`, clean axioms** — `statement_integrity` rejected ALL three (`ratified=0`) | a naive "it compiled" verifier accepts all three; the governance catches the faithless close. **This is the differentiator** — you cannot get it from a stronger model, because the model is what's being policed. |
| autoformalization firewall | **13/13 domains** (compliance, pharma/HIPAA/aviation/export, DeFi incl. nonlinear `k≤x·y`, IAM: terminated-contractor / MFA / SoD / RBAC) | NL rule → Lean predicate; faithful admitted, laundered (∧→∨ / off-by-one / dropped-conjunct / `<`vs`≤`) caught by the kernel |
| firewall vs steelmanned agent judge (7 domains, 14 cases, 2026-06-15) | firewall **14/14=100%** (0 false-alarms) vs judge **13/14=93%** (1 false-reject); catch-rate tied **7/7 vs 7/7** | the differentiator is **precision + cert**, not catch-rate — receipts `dashboard_data/nonmath_firewall_ab.json` |

Capability receipts (the *environment* multiplying the leaf — but NOT a capability edge over a shell-agent; see the architecture doc's SETTLED note):

| capability | result | honest reading |
|---|---|---|
| P1 rungs (construct NEW proofs not in Mathlib) | **L0 / RUNG C / RUNG B** kernel-closed, axioms ⊆ {propext, Classical.choice, Quot.sound} | the open-problem regime: builds the proof bottom-up, governance keeps it sound |
| witness-transport (SymPy → Lean) | 12/12 **vs native Lean tactics** (0/12); and only-N factoring **4/4 kernel-verified vs a bare text model** (deepseek 1/4, 6-digit control only) — +3 | a cheap **deterministic** lever the leaf *prefers* over hand-rolling a solver (5 tool-calls / 0 self-coded). The bare-text edge is real (a no-tool model can't factor a 16+ digit semiprime); NOT an edge vs a *shell*-agent, which self-codes the same compute. |
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

## Honest gaps

- Everything validated is **toy-scale** (5-case batteries, single-threshold predicates). The bottleneck to
  real-world claims is **autoformalizer robustness** at the complexity of a 1000-page regulation or a real
  contract — the least-validated of the three engines.
- Several moves are SUBSUMED on easy substrates (reflection by `decide`, degree-2 abduce by `nlinarith`) —
  lift exists only where the native cascade is genuinely blind.

## Why open source

Trust is the product, and you cannot sell certainty as a proprietary black box. Open-sourcing the governance
layer (the faithfulness firewall and the anti-laundering kernel) lets the security community audit that the
kernel does not launder, and lets banks and defense run it air-gapped with their own weights. The same
discipline is applied to LeanMill's own development: every capability here was measured with a zero-control
and a carrier preflight before it was written down.
