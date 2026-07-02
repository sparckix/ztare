---
description: "What LeanMill is, who it's for, and the receipts behind the claims."
---

# LeanMill: what it is, who it's for, and the receipts

## Table of Contents

- [What it is](#what-it-is)
- [What it adds over a strong model](#what-it-adds-over-a-strong-model)
  - [The faithfulness decision procedure](#the-faithfulness-decision-procedure)
- [Receipts: through the wired kernel and governance](#receipts-through-the-wired-kernel-and-governance)
  - [Soundness: the adversarial red-team (2026-06-16)](#soundness-the-adversarial-red-team-2026-06-16)
  - [Governance under adversarial pressure](#governance-under-adversarial-pressure)
  - [Capability receipts](#capability-receipts)
- [Near-term scope: decidable systems assurance](#near-term-scope-decidable-systems-assurance)
- [Gaps and limitations](#gaps-and-limitations)
- [Why open source](#why-open-source)

## What it is

LeanMill turns an ambiguous specification, a compliance rule, an access policy, or a math claim, into a
kernel-certified guarantee. Three engines compose, each scoped to one job:

- an agent (subscription codex/claude) translates intent into a formal statement;
- an SMT solver (z3 quantifier-elimination / cvc5) searches the boundary: the missing premise, the policy
  combination, the off-by-one that flips a decision;
- the Lean 4 kernel ratifies and emits an auditable certificate (`#print axioms ⊆ {propext,
  Classical.choice, Quot.sound}`, no `sorry`, no smuggled axiom).

The agent is never trusted. Every statement it produces is re-verified by the kernel before the result
counts, so a model that writes plausible code and retries cannot slip a wrong answer past the gate.

## What it adds over a strong model

A frequent objection: a strong model is already accurate, so what does the kernel add? We measured it over 7
compliance domains (14 faithful/laundered cases).

On catch-rate it adds nothing. The steelmanned agent judge tied the kernel (7/7 launderings each) because
these off-by-ones are visible in the formula text and the judge reads them.

The edge is precision and verifiability. The firewall is 14/14 = 100% with zero false-alarms; the judge is
13/14 = 93%, having false-rejected one faithful rule. And every firewall verdict ships as an auditable
certificate. You cannot sue an LLM for a hallucinated compliance opinion; you can stand behind a kernel
proof.

We also built and measured the harder must-search class: boolean precedence flips, divisibility refactors,
linear-combination disguises. The frontier judge caught those too, 3/3, by reasoning through them. So against
a strong judge there is no catch-rate edge, only precision and the certificate. Receipts:
`analytics/public/leanmill/results/nonmath_mustsearch_ab.md`.

### The faithfulness decision procedure

`certify_policy_faithfulness` is a typed 3-verdict artifact (CERTIFIED_EQUIVALENT,
REFUTED-with-a-distinguishing-input, or OUT_OF_FRAGMENT) composing z3 + Gröbner + the Lean kernel (lineage
PCP/IP, Rice, Gröbner/Farkas). On an N=18 policy corpus across 8 compliance domains it decides all 18 and
agrees with the z3 ground truth.

Because the engine is z3, that agreement is a consistency check, not an accuracy claim. Two results do carry.
Every verdict is a checkable artifact; and against the independent judge oracle the outcome is a kept null:
the N=5 witness gap (3/3 vs 2/3) did not replicate, and at N=18 the judge matched 18/18 (9/9).

The guarantee is soundness: a decision-procedure certificate, where the judge gives only an unguaranteed
opinion. That is the claim, ahead of any leaderboard number.

The same trichotomy drives a transport-to-decidability router, with a decidable-fraction lift of +3
(portfolio 5/7 vs single-theory 2/7) on a mixed math+policy seed
(`results/{certify_policy_corpus_run,decidability_router}.md`).

## Receipts: through the wired kernel and governance

### Soundness: the adversarial red-team (2026-06-16)

A verification reviewer's central worry is a false closure, an unsound proof slipping past the gate. So we tried
to smuggle one through (`audit_external`). Every attack was rejected and the clean control proof passed:

| attack | gate verdict |
|---|---|
| `sorry` / `admit` / nested `sorry` | rejected (sorryAx caught) |
| `native_decide` ⇒ `Lean.ofReduceBool` | rejected (axiom outside the {propext, Classical.choice, Quot.sound} allowlist) |
| false custom `axiom` + cite it | rejected (extra axiom caught) |
| clean proof (control) | passes |

→ catch-rate 5/5 = 100%, 0 false-flags. Re-runnable: `PYTHONPATH=src python projects/leanmill_experiments/governance_redteam.py`.

### Governance under adversarial pressure

A stronger model cannot give you this, because the model is the thing being policed:

| the differentiator | result | what it shows |
|---|---|---|
| anti-laundering on an OPEN target | denef_lipshitz: agent produced 3 closes that compiled, no `sorry`, clean axioms; `statement_integrity` rejected all three (`ratified=0`) | a naive "it compiled" verifier accepts all three; the governance catches the faithless close. You cannot get this from a stronger model, because the model is what's being policed. |
| autoformalization firewall | 13/13 domains (compliance, pharma/HIPAA/aviation/export, DeFi incl. nonlinear `k≤x·y`, IAM: terminated-contractor / MFA / SoD / RBAC) | NL rule → Lean predicate; faithful admitted, laundered (∧→∨ / off-by-one / dropped-conjunct / `<` vs `≤`) caught by the kernel |
| firewall vs steelmanned agent judge (7 domains, 14 cases, 2026-06-15) | firewall 14/14 = 100% (0 false-alarms) vs judge 13/14 = 93% (1 false-reject); catch-rate tied 7/7 vs 7/7 | the edge is precision + cert, not catch-rate; receipts `dashboard_data/nonmath_firewall_ab.json` |

### Capability receipts

The environment multiplies the leaf. It is not a capability edge over a shell-agent (see the architecture
doc's SETTLED note):

| capability | result | what it shows |
|---|---|---|
| P1 rungs (construct NEW proofs not in Mathlib) | L0 / RUNG C / RUNG B kernel-closed, axioms ⊆ {propext, Classical.choice, Quot.sound} | the open-problem regime: builds the proof bottom-up, governance keeps it sound |
| witness-transport (SymPy → Lean) | 12/12 vs native Lean tactics (0/12); and only-N factoring 4/4 kernel-verified vs a bare text model (deepseek 1/4, 6-digit control only), +3 | a cheap deterministic lever the leaf prefers over hand-rolling a solver (5 tool-calls, 0 self-coded). The bare-text edge holds (a no-tool model cannot factor a 16+ digit semiprime), but it is not an edge vs a *shell*-agent, which self-codes the same compute. |
| QE-abduction (z3 QE → Lean) | 6/6 advance vs blind conjecture | the most-general missing premise (Dillig "Explain"), kernel-admitted, same reliability lever |

`solve_witness`, `qe_abduct_premise`, `default_instance_battery`, and `solve_adhoc_governed` are the wired
production functions, with no re-implemented per-experiment battery.

## Near-term scope: decidable systems assurance

Use cases rank by decidability.

**Strongest now, Cloud IAM / access-policy verification.** Policies are decidable (linear/boolean), which is
z3 QE's home turf. "Is there any scenario where a terminated contractor can read prod?" is a
quantifier-elimination query: eliminate the role variables, return the witness. This is the mechanism we wired
and measured.

**Strong, algorithmic compliance and regulation.** Threshold logic: Basel CET1, Reg-T margin, tax cliffs.
The 7 validated domains are exactly this shape.

**Demonstrated, DeFi / smart-contract defense.** Now shown for the formalize-and-prove route, no longer just
aspirational. Filed in [`ztare_proofs/leanmill-formalizations/finance/`](../../ztare_proofs/leanmill-formalizations/finance/):
the constant-product AMM temporal and no-arbitrage invariants, and *no round-trip arbitrage at any reachable
pool state* (no flash-loan, sandwich, or cyclic path makes a round-trip profitable).

Both hold over the nonlinear `k = x·y` curve in `NNReal`, kernel-ratified, axioms ⊆ {propext,
Classical.choice, Quot.sound}, the second compounding on the first by citation.

The nonlinear-undecidability caveat holds but is specific to the SMT-QE *search* lever (z3 QE / cvc5 abduction
over nonlinear ℤ); the agent-constructs-proof / kernel-verifies route has no such limit. The boundary is the
lever, not the domain.

## Gaps and limitations

One bottleneck gates production claims: autoformalizer reliability at scale, the complexity of a 1000-page
regulation or a production contract.

The proofs themselves are past toy. The filed finance and strategy theorems are multi-lemma results: the AMM
no-arbitrage chain composes a 5-lemma decomposition atop a banked constant-product theory, and the
corporate-waterfall and Topkis results are similar, all kernel-ratified and axiom-clean.

But each was driven from a hand-written natural-language blueprint. Turning an unstructured thousand-page spec
into faithful Lean statements at that volume is the least-validated of the three engines, and it gates
everything else.

Some SMT/abduction moves are subsumed on easy substrates (reflection by `decide`, degree-2 abduce by
`nlinarith`). The deterministic levers add value only where the native tactic cascade is blind.

## Why open source

Trust is the product, and you cannot sell certainty as a proprietary black box. Open-sourcing the governance
layer (the faithfulness firewall and the anti-laundering kernel) lets anyone audit that the kernel does not
launder, and run it self-hosted or air-gapped with their own model weights. The same discipline applies to
LeanMill's own development: every capability here was measured with a zero-control and a carrier preflight
before it was written down.
