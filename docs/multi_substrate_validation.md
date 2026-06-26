---
description: "Evidence inventory for what ZTARE's claim discipline has and has not shown across several research domains."
---
# Multi-domain evidence inventory

Has ZTARE only worked on one research domain, or has its checking discipline
started to travel?

It has started to travel, but the current v0.4 workbench has not yet been
validated as one repeatable product path across all domains.

Several tempting claims were narrowed after checks forced the repo to name
missing evidence, unstable measurements, old obstructions, or source problems.
No domain was solved.

## Bottom line

This is an evidence memo. It records where the same discipline showed up in
different domains, and where that discipline was not enough to support the
larger claim someone might want to make.

| Domain | What the repo can defend | What it cannot defend | Next check |
|---|---|---|---|
| Modified gravity / AQUAL | Bounded nulls, numerical-method warnings, and an ambiguity audit around 3-D field-slice experiments | A new MOND law, a gravity unification claim, or a physical orientation law | Higher-resolution tensor boundary-condition sweep with matched off-diagonal tidal boundaries |
| Consciousness-ascription governance | A measurement-governance rule for when low-concern verdicts are not admissible | A theory of consciousness or a definition of consciousness | Keep the governance result separate from denotation claims, then test whether the rule ports to another governance domain |
| Neural interpretability and scaling | A measurement-artifact diagnosis, cross-layer orthogonality evidence, and clean negative scaling results | A universal scaling law or a named-constant law | Keep endpoint-free validation and external replication separate |
| Navier-Stokes Track B | Residual localization, formal smoke checks, and a record of demoted closure language | Clay closure or proof of global regularity | Attack the named residuals without renaming old obstructions |

One maintained repo used a consistent checking discipline across several
unrelated campaigns and recorded where claims became smaller.

Do not read this as: solved Millennium problems, consciousness solved, a new
gravity law, a universal neural-scaling law, or proof that the current v0.4
workbench has already generalized across all four domains.

The filename is retained for historical links. The reader-facing claim is
"multi-domain evidence inventory," meaning an inventory, not completed
validation.

## What to inspect first

With ten minutes available, start with the demotions:

| Demotion | Why it matters |
|---|---|
| Gravity scalar-boost story became an instrument audit | A tempting physical story was narrowed when the numerical setup was not stable enough. |
| Consciousness pluralism became a training-corpus warning | A plausible governance thesis was narrowed when the source of the idea looked contaminated. |
| Neural `beta = 1 / phi` was retired | A named-constant story lost to cross-modality testing. |
| Navier-Stokes closure language became named residuals | Proof-search progress was not allowed to become a global-regularity claim. |

Those four cases are the point. The project is worth attention here because it
records where claims got smaller, before any domain was finished.

## Domain notes

### Modified Gravity / AQUAL

**Where to inspect.** Start with the gravity entries in
[the public claim register](public_claim_register.md#modified-gravity--aqual--rar)
and the project directories named there, including the modified-gravity
campaign directories and the
[3-D unified-acceleration field-slice sandbox](../projects/gp163d_unified_accel/).
The
historical run postmortem is the
[unified-acceleration field-slice audit](../research_areas/seams/audits/2026_04_25/GP-163d_unified_accel_run_postmortem.md).

**What mattered.** The repo tested universality versus scale-dependence as a
pre-committed split, checked solar-system constraints only when the rubric
enabled the gravity-specific checks, and treated the 3-D AQUAL-style result as
numerical evidence, not physics law.

**What survived.** The row-wise RAR campaign returned a bounded null: no joint
interpolation form passed the stated cross-class threshold. The 3-D sandbox
showed a diffuse-source susceptibility pattern, but the result is held as an
instrument and numerical-methods finding.

**What blocks promotion.** The field-slice result needs a higher-resolution
tensor boundary-condition sweep before it can be treated as anything stronger
than an instrument audit.

### Consciousness-Ascription Governance

**Where to inspect.** Start with the consciousness entries in
[the public claim register](public_claim_register.md#consciousness-ascription-governance)
and the project directories named there:
[consciousness-ascription audit](../projects/gp169_consciousness_ascription_audit/),
[consciousness-theory workbench](../projects/gp210_consciousness_theory/),
and
[Omega-gaming consciousness audit](../projects/gp212_consciousness_omega_audit/).

**What mattered.** The key result is a governance rule: a low-concern verdict
about a system of unknown consciousness is not admissible unless the
measurement channel can actually identify the target property. This is named
the measurement-channel veto protocol. Historical provenance lives at
[the cold-LLM consciousness seam](../research_areas/seams/engine/discovery/GP-169_cold_llm_synthetic_erdos_seam.md)
and [the Omega-gaming classifier seam](../research_areas/seams/engine/meta/GP-212_meta_solver_kernel_seam.md).

**What survived.** The measurement-governance rule held up better than the
early pluralism thesis. The repo kept the part it could inspect and demoted
the part that looked source-contaminated.

**What blocks promotion.** This is a governance rule, not a theory of
consciousness. It ports to another setting only if measurement access is
actually limited there, without smuggling in the same assumptions.

### Neural interpretability and scaling

**Where to inspect.** Start with the neural entries in
[the public claim register](public_claim_register.md#neural-scaling-and-mechanistic-audits),
`papers/paper6_neural_scaling/draft.md`, the neural-scaling project
directories, and [`projects/neural_hunt/`](../projects/neural_hunt/).

**What mattered.** The checks separated measurement artifacts from model
behavior. In the interpretability work, mean pooling made a bottleneck look
stronger than it was because the BOS token dominated the norm. In the scaling
work, endpoint-free validation blocked a clean promotion of the named-constant
story.

**What survived.** The BOS-contamination diagnosis and cross-layer
orthogonality result are stronger than the original bottleneck story. The
scaling-law work produced useful trajectory morphology and clean negative
results: a toy-transformer optimizer-control law did not transfer, and the
`beta = 1 / phi` anchor was retired.

**What blocks promotion.** External replication is still needed, along with
clean separation between measurement choices, endpoint choices, and claimed
laws.

### Navier-Stokes Track B

**Where to inspect.** Start with
`projects/ns_millennium_hunt/`, the public Navier-Stokes entries in
[the public claim register](public_claim_register.md#navier-stokes-track-b),
and the Lean project under `ztare_proofs/ZtareProofs/`.

**What mattered.** Residual localization is the main value. Specific formal
and mathematical blockers are named, and near-misses are held at that
description. The campaign does not let them become closure language.

**What survived.** Several proof-search paths became sharper residuals:
Wall W6, Atom 8c, PR-A1 transitive obligations, Galerkin-level liminf-equality
hypotheses, and the ten-proposition bucket around Atom 1. That is evidence of
better problem localization, not of a solved problem.

**What blocks promotion.** Global regularity is not proved. Any stronger claim
requires a named blocker, recurrence checks, tool-depth records, formal/source
review records, and external mathematical review.

## Cross-domain lesson

Across the four domains, the recurring behavior is:

```text
make the claim inspectable -> run a check that can fail
-> narrow or block the claim -> record the next check
```

That behavior has appeared in more than one domain. The current release still
owes a fresh non-NS pass through the v0.4 workbench path before it can claim
repeatable cross-domain product validation.

For the claim-by-claim version, read
[the public claim register](public_claim_register.md). For the evidence-level
map, read [the evidence atlas](evidence_atlas/README.md).
