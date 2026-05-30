# GP-079 Persona Library Unification

> **Seam metadata** · `seam_id:` GP-079 · `track:` protocol · `status:` Open · `last_updated:` 2026-05-08


**Status:** Open
**Date:** 2026-04-17
**Origin:** GP-078 rubric domain-expert review — ad-hoc persona spin revealed 4+ independent persona stores with no shared registry
**Parent:** GP-072 Phase 5 (domain-expert review step)

## Problem

Persona definitions are scattered across four independent stores, each with its own format, loading path, and consumer. When a new review context arises (e.g., GP-078 domain-expert rubric audit), the operator spins an ad-hoc agent prompt because there is no discoverable registry of available personas and no shared loading mechanism.

### Current Stores

| Store | Format | Loaded By | Consumer | File(s) |
|---|---|---|---|---|
| **Domain lenses** | Markdown files `reviewer_domain_*.md` | `load_reviewer_domains()` in `supervisor_findings_runner.py:223` | Skeptic prompt in findings runner (injected into `reviewer_domains_text`) | `config/prompts/reviewer_domain_{munger,philosophy_of_science,symbolic_regression,systems_ml}.md` |
| **Shadow board roles** | Python dict `{role, persona, focus_area}` in `ROLE_DEFINITIONS` | `instantiate_fixed_committee()` in `committee_instantiation.py` | `shadow_board.py` → `assign_shadow_board()` | `src/ztare/validator/shadow_board.py:35-83` |
| **Review rubric persona check** | Hardcoded string in check #5 (`persona_blind_spot_coverage`) | Inline in `review_rubric.py` | GP-054 pre-run rubric review | `src/ztare/rubrics/review_rubric.py:171-173` |
| **Ad-hoc agent prompts** | One-off prompt strings passed to agent spins | Manual (operator or Claude Code) | Contamination audits, wiring verification, domain-expert rubric review, peer review critique | Not persisted |

### Why This Matters

1. **Ad-hoc personas can't be tested or versioned** — the GP-078 domain-expert reviewer was a one-shot prompt; if we need the same lens again, it's reconstructed from scratch
2. **Shadow board roles and domain lenses serve the same function** (focus an LLM on a specific review angle) but use incompatible formats
3. **review_rubric.py has no persona system at all** — check #5 describes what a resistant persona should do but doesn't load one
4. **GP-072 Phase 5 (domain-expert review)** needs a GT-aware persona from the registry, but the registry doesn't exist

## Constraint: Do NOT Conflate with Dynamic Committee Generation

`generate_committee.py` dynamically composes committees for debate. That mechanism is separate. The persona library is a **registry of named, versioned persona definitions** that any consumer can load. The committee generator is one consumer. The findings runner is another. The rubric reviewer is a third. They each compose differently.

## Proposed Architecture

### Single Registry Format

```python
# config/personas/<category>/<name>.yaml  (or .md with frontmatter)
---
name: symbolic_regression_expert
category: domain        # domain | audit | methodology
role: Domain Expert — Symbolic Regression
persona: |
  You are an expert in symbolic regression...
focus_area: |
  Evaluate whether proposed expressions...
tags: [sr, math, eureqa, pysr]
---
```

### Unified Loader

```python
# src/ztare/personas/registry.py
def load_persona(name: str) -> PersonaDefinition: ...
def list_personas(category: str | None = None) -> list[str]: ...
def load_personas(names: list[str]) -> list[PersonaDefinition]: ...
```

### Dataclass

Reuse and extend `CommitteeBriefBinding`:
```python
@dataclass(frozen=True)
class PersonaDefinition:
    name: str
    category: str          # domain | audit | methodology
    role: str
    persona: str
    focus_area: str
    tags: tuple[str, ...]
    profile_key: str       # filesystem-derived key for traceability
```

## Dependencies (What Needs to Change)

| Consumer | Current State | Required Change | Blocked By |
|---|---|---|---|
| `supervisor_findings_runner.py` | `load_reviewer_domains()` reads `config/prompts/reviewer_domain_*.md` → raw text injection into skeptic prompt | Replace with `load_personas()` call; format output the same way (backward-compatible text block) | Registry loader |
| `shadow_board.py` | `ROLE_DEFINITIONS` dict with 4 inline roles | Migrate roles to registry files; `ROLE_DEFINITIONS` becomes a thin adapter calling `load_persona()` | Registry loader |
| `committee_instantiation.py` | `CommitteeBriefBinding` dataclass + `instantiate_fixed_committee()` | Extend to accept `PersonaDefinition`; keep `CommitteeBriefBinding` as output format for committee consumers | Registry loader |
| `review_rubric.py` | No persona system; check #5 is a hardcoded description | Add optional `--persona` flag to inject a loaded persona into the LLM review prompt | Registry loader |
| GP-072 Phase 5 | Not implemented | `review_rubric.py --gt-script ... --persona domain:mathematics` loads a GT-aware domain persona for answer-class compatibility check | Registry loader + review_rubric persona support |
| GP-070 review phases | Shadow board assignment only | Could select from registry by tags matching the project domain | Registry loader |
| Ad-hoc agent spins | One-off prompts | Operator can `load_persona("mathematics")` instead of writing from scratch; still allows ad-hoc overrides | Registry loader |

## Migration Path

1. **Create `src/ztare/personas/registry.py`** with `PersonaDefinition` dataclass and `load_persona()` / `list_personas()`
2. **Move `config/prompts/reviewer_domain_*.md`** → `config/personas/domain/` (or keep in place and have registry index them)
3. **Extract shadow board roles** to `config/personas/audit/` files
4. **Adapt `load_reviewer_domains()`** to call registry internally (keep function signature for backward compat)
5. **Adapt `instantiate_fixed_committee()`** to accept `PersonaDefinition` alongside raw dicts
6. **Add `--persona` flag to `review_rubric.py`** for GP-072 Phase 5

## What This Does NOT Cover

- Dynamic committee composition logic (stays in `generate_committee.py`)
- Persona generation / LLM-authored personas — this is a static, versioned registry
- Prompt template engine — personas are injected as text blocks, not template-rendered

## Dynamic Selection — Implementation Target

### Option 1 (shipped): Rubric declares `reviewer_domains`

`experiment-loop` introspects `reviewer_domains` from the rubric JSON and
appends `--reviewer-domains` automatically. Zero new logic beyond the existing
`holdout_hard_gate` introspection pattern.

### Option 3 (target): Failure-family routing

**Principle**: persona selection is zero-oracle — driven entirely by what the
run is failing at, not by the operator or rubric author knowing the GT.

**Mechanism**:

After each iteration, `latent_distance.jsonl` records `failure_families` (e.g.
`inductive_epistemology`, `model_class_constraint`, `lookup_table_epicycle_overfit`).
A routing table maps each family to the persona(s) best positioned to attack it:

| Failure family | Persona(s) |
|---|---|
| `inductive_epistemology` | `philosophy_of_science` |
| `lookup_table_epicycle_overfit` | `symbolic_regression` |
| `model_class_constraint` | `systems_ml` |
| `overfitting_non_uniqueness` | `philosophy_of_science`, `symbolic_regression` |
| `post_hoc_exceptions_ad_hoc_fitting` | `munger_multidisciplinary` |
| `underdetermination` | `philosophy_of_science`, `systems_ml` |
| `pattern_induction_algorithmic_parsimony` | `symbolic_regression`, `philosophy_of_science` |

**Where it lives**: `src/ztare/personas/routing.py` — a pure function
`select_personas_for_iteration(failure_families: list[str]) -> list[str]`
that returns persona names from the registry. No LLM call, no GT access.

**Integration point**: `supervisor_findings_runner.py` or `autoresearch_loop.py`
calls `select_personas_for_iteration()` after each iteration's
`latent_distance` record is written, before the next skeptic prompt is
assembled. Replaces static `reviewer_domains_text` with dynamically selected
lenses that track the current failure surface.

**Why option 2 was rejected**: LLM-driven selection requires the rubric author
(who knows the GT) to pick the expert. That's oracle-lite — the selection
itself leaks GT knowledge. Option 3 is driven by the observed failure signal,
which is GT-blind.

**Open question**: routing table is currently hand-authored. Eventually the
table itself could be learned from the labeled debate log dataset (per
`project_debate_log_as_dataset.md` memory) — but that is a future slice, not
a blocker.

## Implemented Architecture (2026-04-19)

### Option 4 (shipped): LLM Router + Dynamic Fallback + Promotion Loop

Supersedes the hand-authored routing table (Option 3 v1) while preserving it
as fallback. Three-tier resolution:

1. **LLM router** (`gemini-2.5-flash`, ~30s, ~$0.001/call) sees the full static
   persona catalog + observed failure families. Selects 1-3 best matches.
2. **Dynamic fallback**: If the LLM determines no static persona covers a
   failure family, it generates a dynamic persona inline (role + persona +
   focus_area). Always supplements, never replaces, static selections.
3. **Promotion loop**: On debate convergence, dynamic personas that contributed
   to a successful outcome are promoted to `config/prompts/reviewer_domain_*.md`
   — becoming static, cached, and discoverable for future runs.

**Static fallback**: If the LLM is unavailable (no API key, transient failure,
or `ZTARE_DISABLE_LLM_ROUTER=1`), the hand-authored `_STATIC_ROUTING_TABLE`
activates. This is the original Option 3 table, preserved as a reliability floor.

**Why this is zero-oracle**: The LLM router sees only (a) persona catalog
descriptions and (b) `failure_families` from `latent_distance.jsonl`. Neither
source contains GT knowledge. The router's LLM call has no access to the rubric,
evidence, or thesis — it sees only the failure signal and the catalog.

**generate_committee.py is NOT touched**: The kernel committee pipeline
(shadow board + dynamic attackers for Gemini-judged runs) is a separate
consumer. The registry provides personas; the committee generator consumes
them independently. These are different pipeline stages.

### Static Persona Catalog (9 domain personas as of 2026-04-19)

| Name | Lens | Origin |
|------|------|--------|
| `philosophy_of_science` | Popper, Lakatos, falsifiability | v1 (2026-04-16) |
| `symbolic_regression` | PySR, genetic programming, Pareto | v1 |
| `systems_ml` | Information theory, BIC/AIC, oracle contamination | v1 |
| `munger_multidisciplinary` | Inversion, mental models, incentives | v1 |
| `validator_hardening` | Gate design, Goodhart's Law | v1 |
| `formal_methods` | Dijkstra — contracts, invariants, constructive proof | v2 (2026-04-19) |
| `empirical_ai` | Norvig — ablation, Pareto, sequential testing | v2 |
| `literate_programming` | Knuth — pedagogical chains, maintenance cost | v2 |
| `neural_net_practitioner` | Karpathy — loss landscape, gradient signal, inductive bias | v2 |

### Files Modified

- `src/ztare/personas/routing.py` — rewritten: LLM router + `RouteResult` + `DynamicPersona` + `promote_dynamic_persona()`
- `src/ztare/validator/supervisor_findings_runner.py` — auto-route path uses `RouteResult.format_for_injection()` + promotion on convergence
- `config/prompts/reviewer_domain_{formal_methods,empirical_ai,literate_programming,neural_net_practitioner}.md` — new static personas

## Debate Log

### Turn 1 — Operator (2026-04-17)
Four independent persona stores with incompatible formats discovered during GP-078 rubric domain-expert review. User directive: "we have config/prompts as persona library... also the generate committee is dynamic, we should not conflate, but i agree we should do a common library." Opened seam to map dependencies before implementation.

### Turn 2 — Operator + Claude (2026-04-19)
Operator observed that dynamic debate agents (Dijkstra/Knuth/Norvig panel in GP-101 seam) outperformed static personas in findings_runner. Directive: "create dynamic personas (Dijkstra) that keep coming up as a baseline to avoid regeneration + a router (LLM) that fetches potential personas dynamically and if it doesn't find one of the proposed candidates generate dynamically and if good promote to static persona in config/." Implemented Option 4 (LLM router + dynamic fallback + promotion). Added 4 new static personas (formal_methods, empirical_ai, literate_programming, neural_net_practitioner). generate_committee.py explicitly not touched — separate pipeline stage.

<!-- FINDINGS_DEBATE: Persona library consumers identified: findings_runner, shadow_board, committee_instantiation, review_rubric, GP-072 Phase 5, GP-070 review, ad-hoc agent spins. Key constraint: registry is static/versioned, committee composition is dynamic — do not merge. Option 4 shipped: LLM router + dynamic fallback + promotion. 9 static domain personas. generate_committee NOT modified. -->
