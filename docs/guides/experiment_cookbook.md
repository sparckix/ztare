---
description: "Recipes for running experiments; run make seal before make experiment-loop."
---

# Experiment Cookbook

> **Up:** [Documentation map](../README.md)

**Provenance:** Distilled from the private sealed pre-registration discipline and AGENTS.md sealed-pre-registration rules.
**Canonical for:** pre-run procedure, `make seal` workflow, Division A/B protocol.
**Supersedes:** the older manual pre-run checklist; this cookbook is the entry point.

---

## The one-line rule

> Run `make seal` before `make experiment-loop`. If seal fails, stop. If seal passes, you have a data point. If you skip seal, you have a warm-up.

---

## 0. Which track are you on?

| Track | When | Entry |
|---|---|---|
| **New substrate** | New GT, new domain | Start at Division A/B |
| **Grammar extension or rubric variant on existing substrate** | Same GT, different grammar/rubric | Skip to scaffold Division B |
| **Re-run / replication** | Same GT, same rubric, different model pair | Skip to seal |
| **Qualitative thesis (policy, philosophy, social science)** | Text evidence, no GT | See qualitative projects, then seal |

---

## 0A. Qualitative Projects, `make generate-gp` ([GP-104](../../research_areas/seams/protocol/GP-104_qualitative_rubric_gate_configuration_seam.md))

For qualitative projects (text evidence, no numerical GT), use `generate-gp` instead of the Division A/B substrate pipeline. The generator scaffolds the project with correct gate configuration and an LLM-drafted adversarial rubric.

```bash
make generate-gp \
    PROJECT=<slug> \
    BRIEF="One-paragraph thesis question, be specific about domain and claim direction" \
    JUDGE_MODEL=gpt4.1
```

**What it creates:**

| Artifact | Purpose |
|---|---|
| `projects/<slug>/evidence.txt` | Blank evidence file, edit directly for a curated-evidence project |
| `projects/<slug>/raw/` | Drop source documents here for `make evidence-compile` in a source-ingest project |
| `projects/<slug>/raw/source_type_map.json` | Type map for evidence compiler |
| `projects/<slug>/thesis.md` | Neutral seed thesis template |
| `projects/<slug>/project_charter.md` | Auto-drafted from your brief |
| `projects/<slug>/workspace/` | Runtime outputs directory |
| `rubrics/<slug>.json` | LLM-drafted persona + criteria, all Type B gate opt-outs pre-filled |

**Type B gate opt-outs (pre-filled automatically):**

Qualitative projects require three non-obvious configuration keys that must be present to prevent global gate misfires. `generate-gp` injects them automatically:

```json
{
  "farther_tail_region": null,
  "disable_evidence_fit_gate": true,
  "disable_uniqueness_gap_gate": true
}
```

**Do not omit these.** Their absence causes hard fails that look like scoring failures (score 0 every iteration). Three projects hit this in one session before the generator was built ([GP-104](../../research_areas/seams/protocol/GP-104_qualitative_rubric_gate_configuration_seam.md)).

**Evidence: two paths:**

- **Curated-evidence route** (small projects): edit `evidence.txt` directly, one observation per line.
- **Source-ingest route** (large projects, many source documents): drop PDFs/markdown into `raw/`, optionally type them via `raw/source_type_map.json`, then `make evidence-compile PROJECT=<slug> MODEL=gpt4.1`.

**After generating:**

1. Review and edit `rubrics/<slug>.json`, the LLM draft is a starting point. Verify the persona is genuinely adversarial for your domain.
2. Add evidence using the curated-evidence or source-ingest route above.
3. Proceed to §4 (Seal), no smoke gate needed for qualitative projects (no numerical gate harness).

```bash
make seal PROJECT=<slug> RUBRIC=rubrics/<slug>.json
make loop PROJECT=<slug> RUBRIC=rubrics/<slug>.json ITERS=10 \
    MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gpt4.1
```

---

## 1. Division A, GT selection and sealed artifacts

> Division A knows the GT. Division A must not write files the mutator sees.

**What Division A produces:**

| Artifact | Location | Mutator-visible? |
|---|---|---|
| GT module (`gp0NN_*_gt.py`) | `src/ztare/substrates/` | No |
| `evidence.txt` | `projects/<slug>/` | Yes, no GT names |
| `evidence_holdout.txt` | `projects/<slug>/` | Yes, no GT names |
| `evidence_farther_tail.txt` | `projects/<slug>/` | Yes, no GT names |
| `.denylist` | `projects/<slug>/` | No (read by sentinel only) |
| `sealed_assertions.py` | `projects/<slug>/` | No (black-box import by harness) |
| Pre-registration | private sealed area | No |

**Use the substrate generator, not manual Python:**

```bash
# For integer-sequence substrates
python generate_substrate.py --project <slug> --gt-module <module>

# For science substrates with continuous GT
python -m src.ztare.substrates.render_evidence --project <slug> --gt-class <class>
```

Do not generate evidence by writing inline Python in a chat session. The generator scripts enforce the [GP-072](../../research_areas/seams/protocol/GP-072_role_separation_sandbox_construction_seam.md) Division A boundary and are the auditable path. If no generator script exists for your substrate type, create one under `src/ztare/substrates/` before generating evidence, do not bypass with one-off scripts.

**Custom substrate three-file alignment (gp159/160/161 lessons, 2026-04-25):**

When building a custom substrate (not using `generate_substrate.py`), evidence.txt, test_model.py, and gate_harness.py must agree on the I_model contract:

1. **gate_harness.py** is the authority, contains GT, holdout splits, gate logic. It dynamically imports test_model.py and calls `I_model(d)`.
2. **test_model.py** is the mutator's submission, starts as a NaN-returning stub. The mutator overwrites it. **Must NOT be a copy of gate_harness.py** (causes infinite import recursion).
3. **evidence.txt** must have data inline (not "run this command"), a Python code template with a WRONG example form (not GT-leaking), and the same `I_model` signature as gate_harness expects.
4. **cage_meta.class** in rubric must match the actual substrate type (`1d` for scalar substrates, `nd_features` for feature-dict substrates). Mismatch injects the wrong prompt contract.
5. Run `python scripts/validate_evidence.py <slug>` to check evidence quality before sealing.
6. Global gates (`farther_tail_region`, `disable_evidence_fit_gate`, `disable_uniqueness_gap_gate`) must be explicitly opted out for custom substrates with their own gate harness.

**Identifiability protocol (required before sealing):**

1. Multi-start fit, ≥20 random seeds in the plausible parameter box. All convergence paths must recover GT to pre-reg tolerance.
2. Pairwise bowl check, fix each pair at GT, sweep the third. Loss must be convex-down with a unique minimum.
3. Jacobian column-rank, equals parameter count at GT. Catches α/β collapse (sandbox_06 incident).
4. Bootstrap, ≥200 resamples; 95% CIs for each parameter must not overlap a neighbor's GT value.

Paste results into the pre-registration before sealing it. A pre-reg without identifiability results is not sealed.

---

## 2. Division B, charter, rubric, seed model

> Division B is GT-blind. Division B produces everything the mutator reads.

**What Division B produces:**

| Artifact | Location |
|---|---|
| `project_charter.md` | `projects/<slug>/` |
| `rubrics/<slug>_01.json` | `rubrics/` |
| `test_model.py` (seed) | `projects/<slug>/` |
| `thesis.md` (seed) | `projects/<slug>/` |
| `gate_harness.py` | `projects/<slug>/` |

**Charter rules:**

- Describes *that* the target exists and *how* grading works. Never *what* the target is.
- No GT functional form, no parameter names, no domain nouns that name the law class.
- Grammar extensions (e.g. `UNIVERSAL_DENOMINATOR`) must be named in the charter as structural options, not as hints that the answer belongs to that class.
- Strip test (Mungerian inversion): remove proper nouns and concrete mechanisms from every sentence. If the sentence collapses to "the answer has property X," it was a leak.

**Rubric rules:**

- Persona must not mention ZTARE architecture internals (structural extractors, seam IDs, negative_space_extractor).
- No cross-project comparisons in rubric text (sandbox_07, Planck family, etc.).
- `"grammar_extension"` field must match the charter's grammar extension list exactly.
- Domain-expert review (Phase 5 of [GP-072](../../research_areas/seams/protocol/GP-072_role_separation_sandbox_construction_seam.md)) requires GT knowledge: verify the rubric is well-posed for the actual answer class before sealing.

---

## 3. Smoke gate

```bash
python projects/<slug>/gate_harness.py --run-smoke-test
```

Must exit 0 and report:
- `harness_ok: true`
- `rmse` is a finite float (not null/NaN/inf)
- `n_points` matches evidence.txt row count

If smoke gate fails, fix the harness. Do not proceed to seal.

---

## 4. Seal (`make seal`)

```bash
make seal PROJECT=<slug> RUBRIC=rubrics/<slug>_01.json
```

`make seal` runs in sequence:

1. **Sentinel**, scans all mutator-visible files (`project_charter.md`, `thesis.md`, `test_model.py`, `evidence.txt`, `evidence_holdout.txt`, `evidence_farther_tail.txt`, rubric) against `.denylist`. Exit 1 = contamination. Fix the file with the match, then re-run seal.
2. **Integration test**, runs `gate_harness.py --run-smoke-test` and verifies RMSE is finite, harness_ok=true.
3. **Writes `sandbox_seal.json`**, records sentinel result + smoke test result. This file is the proof of seal. Do not proceed to `make experiment-loop` without it.

**Seal is not manual.** Do not run the sentinel and smoke gate separately and declare the sandbox sealed. `make seal` is the canonical gate; `sandbox_seal.json` is the evidence. A sandbox without `sandbox_seal.json` is not sealed.

---

## 5. Pre-reg and dry run

Before the first `make experiment-loop`:

1. **Write the pre-registration** in the private sealed area:
   - `Leak Audit`, paste sentinel output from `sandbox_seal.json`
   - `Identifiability`, paste multi-start fit results
   - `Smoke Gate`, paste harness smoke gate output
   - `Charter Fingerprint`, `sha256sum projects/<slug>/project_charter.md`
   - `Sealed Expected Slots`, GT form, expected champion form, discriminator thresholds (private, never in charter)

2. **Dry-run the sealed command:**
   ```bash
   make experiment-loop PROJECT=<slug> RUBRIC=rubrics/<slug>_01.json ITERS=0
   ```
   This pins all implicit defaults. A pre-reg whose sealed command has never been dry-run is not sealed.

---

## 6. Launch

```bash
make experiment-loop \
  PROJECT=<slug> \
  RUBRIC=rubrics/<slug>_01.json \
  ITERS=<n> \
  MUTATOR_MODEL=<label> \
  JUDGE_MODEL=<label>
```

**Always use `make experiment-loop`, not `make loop`, for pre-registered experiments.** `make experiment-loop`:
- Reads `holdout_hard_gate` from the rubric and sets `--underidentified_after` to the iteration budget automatically.
- Always sets `--disable_attacker_tools`.
- Pre-flight verifies `gate_harness.py` produces valid JSON.

Model labels (not raw API IDs): `gemini`, `gemini-lite`, `gemini-pro`, `claude`, `claude-opus`, `gpt4o`, `gpt4.1`, `gpt4.1-mini`.

**Branch audit before every launch:**

For every rubric flag that switches a code path (`fit_score_mode`, `run-mode`, grammar variant, `enable_*`), verify that prompt contracts, gate harnesses, and deterministic checks cover the flag's **actual value** in this rubric, not the default. The [GP-080](../../research_areas/seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md) incident burned three iterations because `def f()` contract existed for `discrete_exact` but not for `continuous_rmse`.

---

## 7. Closure (after run ends)

Mandatory in the same session:

1. **Freeze workspace.** Confirm all per-iteration artifacts are written. No post-hoc edits.
2. **Write E-row** in `research_areas/EXPERIMENT_TRACK_RECORD.md`.
3. **Evaluate for F-row and INS-row.** F-row if the result changes what to believe or build next. INS-row if paper-grade.
4. **Run telemetry reporter:**
   ```bash
   python -m src.ztare.validator.telemetry_reporter --write-cost-summary --update-run-summary
   ```
5. **Update thesis.md** with best-iteration marker (or null result note).
6. **Advance goal state** if tracked by [GP-070](../../research_areas/seams/apparatus/supervisor/GP-070_meta_supervisor_goal_orchestrator_seam.md): `python -m src.ztare.orchestration.cli advance <slug>`.

---

## Quick reference

```
# Full happy path for a new science sandbox

# Division A (GT-aware):
python -m src.ztare.substrates.render_evidence --project gp0NN_<name> --gt-class <class>
# (generates evidence.txt, holdout, farther_tail, .denylist, sealed_assertions.py)

# Division B (GT-blind):
# Write project_charter.md, rubrics/gp0NN_<name>_01.json, test_model.py, thesis.md, gate_harness.py

# Smoke gate:
python projects/gp0NN_<name>/gate_harness.py --run-smoke-test

# Seal:
make seal PROJECT=gp0NN_<name> RUBRIC=rubrics/gp0NN_<name>_01.json

# Pre-reg (manual write), then dry-run:
make experiment-loop PROJECT=gp0NN_<name> RUBRIC=rubrics/gp0NN_<name>_01.json ITERS=0

# Launch:
make experiment-loop PROJECT=gp0NN_<name> RUBRIC=rubrics/gp0NN_<name>_01.json ITERS=15 \
  MUTATOR_MODEL=gemini-2.5-flash JUDGE_MODEL=gpt4.1
```

---

## Cross-references

- Full leak taxonomy + denylist construction: `docs/guides/for_researchers.md` §2 (charter contamination) and AGENTS.md §7
- Strip test procedure: `docs/guides/for_researchers.md` §2
- Identifiability + pre-registration protocol: `docs/guides/for_researchers.md` §4 and AGENTS.md §7
- [GP-072](../../research_areas/seams/protocol/GP-072_role_separation_sandbox_construction_seam.md) full 7-phase spec: `GP-072 (internal seam)`
- Operational philosophy: `docs/concepts/epistemic_principles.md`
- Three-leg/reflexive framing: `docs/concepts/reflexive_engineering.md`
- Enforcement principles (P13, P14): `docs/concepts/epistemic_principles.md`
