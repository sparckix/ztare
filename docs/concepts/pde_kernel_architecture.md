---
description: "PDE kernel architecture: reusable estimate/currency/gate/work-order substrate, LeanMill service boundary, and project app boundary."
---

# PDE Kernel Architecture

> Up: [Documentation map](../README.md) · Related: [`leanmill_architecture.md`](./leanmill_architecture.md), [`structural_language_catalog.md`](./structural_language_catalog.md).

## 1. Purpose

The PDE kernel is the reusable substrate for PDE work across projects. It is not a Navier-Stokes app and it is not a second LeanMill. It owns PDE estimate structure: operation vocabulary, proof currencies, estimate skeletons, gate metadata, receipt schemas, leaf work orders, gate execution envelopes, and formal-surface inventory.

LeanMill remains the formal theorem service. It owns citable premise retrieval, proof cache, no-good memory, compiler feedback, typed exits, and proof governance. PDE code consumes those services through narrow adapters.

Project apps own substrate data: theorem profiles, hostile packets, receipts, PDE-language instantiations, and formal-surface rows. For example, NS/TICK theorem profiles live in project/workspace or app data, not in the PDE kernel.

## 2. Why This Boundary

The gp55.5 feedback identified the right failure mode: the older workbench was a serious receipt OS but too monolithic to be a reusable leaf-agent platform. The kernel now separates durable PDE services from the RD workbench caller.

Recent public systems point in the same direction:

- Matlas emphasizes large-scale mathematical statement retrieval with dependency unfolding. PDE should use theorem-profile and formal-premise retrieval as a service, not as hardcoded project constants. Source: `https://arxiv.org/abs/2604.17484`.
- Rethlas/Archon puts theorem retrieval and LeanSearch-style formalization in the reasoning loop. PDE should feed LeanMill formal context and consume typed exits instead of duplicating formal theorem stores. Source: `https://arxiv.org/abs/2604.03789`.
- LEAP and OProver emphasize decomposition, compiler feedback, failed-attempt repair, and indexed trajectories. PDE leaves therefore need atomic work orders and LeanMill no-good/proof-cache adapters. Sources: `https://arxiv.org/abs/2606.03303`, `https://arxiv.org/abs/2605.17283`.
- APRIL shows compiler diagnostics are useful training and repair data. PDE should preserve compiler feedback as context rather than burying it in one-off transcripts. Source: `https://arxiv.org/abs/2602.02990`.
- The De Giorgi-Nash-Moser Lean formalization shows modern PDE formalization needs an explicit surface map: weak solutions, Sobolev infrastructure, and quantitative estimates have different formalization states. Source: `https://arxiv.org/abs/2604.05984`.
- Dimensional analysis and physics-constrained PDE learning point to the same guardrail: physical constraints must be forced as typed obligations, not accepted as soft labels. The PDE kernel therefore includes a physical-accounting gate for dimensions, balance laws, flux/boundary terms, localization carriers, sign/positivity, and operator/cutoff losses before an estimate route can receive credit. Background: Buckingham-Pi/dimensional homogeneity and recent hard-constraint physics-informed PDE work such as `https://arxiv.org/abs/2402.07251`.

## 3. Module Map

Kernel package: `src/ztare/pde/`.

| Module | Owns |
|---|---|
| `registry.py` | Declarative gate registry with stable gate ids, workbench flags, runners, tags, and GP-219 op affinities. |
| `gate_runner.py` | Uniform gate execution envelopes and next-required-work-unit generation. |
| `work_order.py` | Atomic leaf-agent work orders from a target, GP-219 op id, and registry-backed gates. |
| `ops.py` | Kernel facade over GP-219 PDE operation cards and execution templates. |
| `currency.py` | Kernel facade over proof-currency exchange obligations. |
| `estimates.py` | Kernel facade over estimate skeleton generation. |
| `receipts.py` | Work-unit and gate-payload receipt registry. |
| `applicability_cards.py` | Deterministic field-level theorem-profile retrieval and applicability cards. |
| `formal_feedback.py` | Read-only LeanMill formal premise and compiler-feedback adapter. |
| `knowledge_service.py` | PDE theorem-profile context plus LeanMill proof-cache/no-good summary. |
| `formal_surface_status.py` | Formal-surface inventory rows and required-primitive gap reports. |
| `canary.py` | Canary re-ingestion: gate bundle to next leaves, project-local PDE failure memory, and formal-surface map updates. |
| `engine.py` | Composable context builder for workbench packs and leaf dispatch. |
| `subkernel.py` | Readiness, service-boundary, and architecture-requirement status. |
| `architecture_requirements.py` | Machine-readable gp55.5 feedback coverage matrix. |
| `cli.py` | Public `ztare pde ...` user surface. |

## 4. Service Boundaries

PDE kernel:

- GP-219 operation cards and execution templates.
- Proof-currency ledgers and exchange-rate obligations.
- Estimate skeleton generation.
- Registry-backed gates and gate runners.
- Atomic leaf work orders.
- Receipt registry.
- PDE theorem-profile applicability cards.
- Formal-surface inventory.
- Operator-admissibility and rigorous-numerics certificate gate surfaces.
- Physical-accounting gate surface for dimensions, balance laws, flux/boundary/source invoices, localization carrier identity, sign/positivity, projection/cutoff/tail losses, and hostile physical packets.

LeanMill service:

- Semantic premise shelf and LeanSearch-style premise recall.
- Verified proof cache.
- No-good/failure memory.
- Compiler feedback and typed exits.
- Proof governance and anti-laundering.

Project app:

- Substrate theorem profiles.
- Hostile packets and counterpackets.
- PDE-language instantiations.
- Source-specific receipts and workbench packs.
- Formal-surface rows for project primitives.

RD workbench:

- Pack assembly.
- Markdown rendering.
- Legacy flag compatibility.
- Project run orchestration.

## 5. Leaf-Agent Contract

A PDE leaf gets one atomic work order:

```json
{
  "target": "annular_bandlimited_riesz_l1_psd_trace_payment",
  "op_id": "pec_l",
  "goal": "audit projection/cancellation currency",
  "given": {
    "carrier": "same annular C7 stream",
    "known_confusers": ["raw_cz", "signed_moment"]
  },
  "gate_requirements": [
    {"gate_id": "G-PDE-ANALYTIC-SUBSTANCE"},
    {"gate_id": "G-PDE-PHYSICAL-ACCOUNTING"},
    {"gate_id": "G-PDE-OPERATOR-ADMISSIBILITY"},
    {"gate_id": "G-PDE-THEOREM-APPLICABILITY"}
  ],
  "must_return": {
    "target_inequality_or_statement": "required",
    "proof_steps": "required list",
    "first_failed_line_or_success": "required",
    "hostile_packet_tested": "required unless leaf is purely formal",
    "currency_exchange_used": "required when target currency changes",
    "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM | NEED_FORMALIZATION"
  }
}
```

The gate runner then normalizes each gate result into:

- `passed`
- `complete`
- `missing_fields`
- `rejected_substitutes`
- `provenance`
- `next_required_work_unit`

This is the executable replacement for a leaf claiming that it "did PDE work" without inspectable estimate or hostile-packet structure.

## 5.1 Physical Forcing Layer

`G-PDE-PHYSICAL-ACCOUNTING` is the gate that prevents a workbench pack from treating a plausible analytic inequality as a PDE payment before the physical invoices are exposed. It requires:

- the physical system and governing balance law;
- conserved or dissipated quantity, quantity dimensions, target dimensions, and scale normalization;
- flux, boundary, source, and sink terms;
- localization region and carrier/control-volume identity;
- sign or positivity structure;
- operator/projection losses and cutoff/commutator/tail terms;
- initial/boundary data and a hostile physical packet.

It also runs three deterministic audits when the route is evaluated:

- the candidate inequality is sent through `G-PDE-INEQ-DIM` with declared dimensions and endpoint bindings;
- the physical balance must be decomposed into term rows with roles, dimensions, and payment status, so a named balance law is not enough;
- optional Pi-group contracts are checked with `G-PI-GROUP-FORCING`, so scaling claims such as heat-length forcing are executable constraints.

It rejects label-only conservation, discarded boundary terms, ignored projection/operator losses, signed cancellation spent as positive payment, proxy carriers, post-selected physical regions, unit-inhomogeneous inequalities, and soft physics-loss-only evidence.

When it fails, it emits four physical leaves: dimensional homogeneity, balance/flux/boundary invoice, localization/carrier identity, and sign/operator/tail invoice. This is a routing gate, not estimate credit: the emitted leaves still need PDE derivations, theorem applicability, hostile-packet survival, and formal/compiler evidence where claimed.

## 5.2 Equality Provenance Layer

`G-PDE-EQUALITY-PROVENANCE` blocks a common PDE proof failure: treating an equality stored in an assumed record as if the equality had been constructed.

The gate requires the equality target, left/right streams, provenance kind, constructor or theorem, generated fields, source binding, anti-proxy fields, hostile packet, and proof boundary. Constructor-provenance claims must also expose body assignments showing how both sides are generated. It accepts constructor-defined equality, source-binding isomorphism, direct same-stream proof, or a theorem proving equality from source data. It rejects assumed record fields, field projection only, label matches, proxy streams, posthoc selection, same-type-as-same-source substitutions, and `rfl` without a constructor body.

This gate does not prove the constructor exists. It decides whether a leaf may count an equality as paid after a constructor/provenance path is supplied, and emits a source-equality work order when the route is laundering an equality through an assumed carrier.

## 6. LeanMill Reuse Without Merging

Do not merge PDE into LeanMill for now.

Reason: LeanMill is the formal theorem and governance service. PDE is a domain-work kernel for estimates, currencies, operators, hostile packets, formal-surface inventory, and project work orders. Their overlap is a service interface:

- PDE calls LeanMill through `formal_feedback.py` and `knowledge_service.py`.
- PDE reads LeanMill proof-cache and no-good memory summaries.
- PDE may request premise shelf context with top-k controls. Defaults avoid embedding calls.
- LeanMill does not need PDE theorem profiles in its theorem library.
- PDE theorem-profile cards are profile/applicability objects, not citable Lean lemmas.

This keeps LeanMill's theorem bank and retrieval cache from duplicating PDE theorem profiles while still letting PDE leaves benefit from LeanMill's banked lemmas, no-good memory, and compiler-feedback loop.

## 7. Current Requirement Matrix

The executable status lives in:

```bash
ztare pde status --json
ztare pde completion-audit --repo-root . --json
ztare pde requirements --json
```

The JSON includes:

- `architecture_requirements`
- `architecture_requirement_status_counts`
- `service_boundaries`
- `runner_checks`

`completion-audit` is the completion gate for the PDE subkernel itself. It
cross-checks runner importability, implemented requirement rows, receipt
coverage for every registered gate, the `pec_l` core PDE gates, readiness
canary gate requirements, gate-bundle summaries, and optional source-boundary
checks when a repo root is supplied.

Leaf gate bundles from `ztare pde run-work-order` also carry a compact
`summary` object. It records process-contract status, missing process artifact
refs, gate count, passed/failed/incomplete gate ids, missing field names,
rejected substitutes, and next required work-unit count. This is the primary
handoff field for leaf agents: full nested gate results remain available, but
the summary is the fast path for deciding the next PDE work item.

For hard PDE leaves, the intended caller flow is:

```bash
python scripts/public/control/rd_tick_brief.py --short --workbench-task "<task>"
ztare pde work-order \
  --target "<target>" \
  --op pec_l \
  --require-process-contract \
  --pattern-action-contract-ref <pattern_action_contract.json> \
  --orchestration-contract-ref <orchestration_contract.json> \
  --pencil-artifact-ref <pencil.md> \
  --json
```

Direct calls to `pattern_action_contract.py` and
`orchestration_contract_gate` remain repair/debug surfaces. The normal
orchestration entrypoint is the RD brief, and the PDE work order treats its
compiled artifacts as required process carriers.
- `canonical_modules`

The same matrix is authored in `ztare.pde.architecture_requirements`.

Current implemented requirement ids:

- `pde.registry.gates`
- `pde.leaf.work_order`
- `pde.ops.currency.estimates`
- `pde.receipts`
- `pde.operator.numerics.plugins`
- `pde.physics.equality.plugins`
- `pde.theorem.profile.cards`
- `leanmill.formal.feedback.adapter`
- `leanmill.failure.memory.adapter`
- `pde.formal.surface.map`
- `pde.engine.context`
- `rd.workbench.consumer`
- `project.app.boundary`

## 8. Completion Standard

The PDE kernel subgoal is complete only when all of the following are true in the current worktree:

1. `ztare pde status --json` reports `ready: true` with no runner import errors.
2. The architecture requirement matrix is present and all gp55.5 feedback requirements have a concrete module/CLI evidence row.
3. The root `ztare pde` command exposes status, completion-audit, requirements, readiness, ops, currency, estimates, receipts, gates, run-gate, work-order, run-work-order, context, knowledge, formal-surface, and canary-report.
4. The RD workbench pack includes PDE kernel surfaces: op registry, currency ledger, receipt registry, gate registry, estimate skeletons, and optional knowledge/formal-surface context.
5. LeanMill integration is read-only through adapters: premise shelf, proof cache, no-good memory, compiler feedback, and typed exits.
6. Project-specific theorem profiles and receipts remain outside `src/ztare/pde`.
7. Focused tests pass without embedding calls.

## 9. Operating Notes

- Default knowledge top-k values for LeanMill semantic premise calls should be zero unless the caller explicitly wants embedding spend.
- A workbench pack is evidence of routing and receipt assembly; it is not estimate proof credit by itself.
- A theorem-profile applicability `MATCH` is still a field-level applicability result, not a proof.
- A formal-surface row with `lean_proof_complete` needs compile/proof evidence. Rows with `informal_only` or `external_citation` should not be consumed as Lean proof.
- Rigorous numerics are a plugin lane. Certificates must pass the numerics gate and name theorem linkage before they can support a PDE claim.
