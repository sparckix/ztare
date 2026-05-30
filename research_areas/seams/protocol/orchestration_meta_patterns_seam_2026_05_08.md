# Orchestration Meta-Patterns Seam — 2026-05-08

> **Seam metadata** · `seam_id:` orchestration_meta_patterns_seam_2026_05_08 · `track:` protocol · `status:` active · `last_updated:` 2026-05-09


**Status:** active *(inferred 2026-05-08 — needs operator review)*

**Status**: in-progress (decisions made, implementation phase next)
**Cabinet**: protocol (workflow rules)
**Owner**: Research Director (this session)
**Linked**: GP-188 RD-primitive-compilation-boundary, GP-172 RD-mform-role,
           GP-226 charter-critic-role

## What this seam captures

A 2026-05-08 working session producing reusable orchestration patterns
(Pattern 1 friction debate, DARWIN-IDEA-KILLER, Reducer, Vocabulary
Quarantine, Falsifiable Asymmetry, Tautology Trap, Smuggling Audit, 3-leg
verification) and the architectural decisions for how to operationalize them.

Tonight's iteration produced the patterns AS-USED but not as first-class
ZTARE primitives. This seam records the architectural debate (5 friction
debates + 2 literature/practitioner scans) and locks the implementation plan.

## The 5 friction debates

### Debate A — Canonical pattern format

**Question**: Markdown vs YAML vs Hybrid for LLM-read pattern catalog?

**Verdict**: **Markdown file with YAML frontmatter, one file per pattern**,
mirrored by generated `org/runtime/pattern_catalog.yaml` index.

**Split**:
- Frontmatter (YAML): id, version, triggers (lexical + structural), spawn
  spec, output schema, fallback, preconditions
- Body (Markdown prose): Problem / Pattern / Why-it-works / When-to-deploy
  / Anti-pattern / Concrete-example

**Falsifiable asymmetry**: with markdown-only catalog, ≥1 incident where
Director invents tool list per spawn (no schema). With YAML-only catalog,
≥1 incident where Director refuses to deploy on OOD situation (no prose
rationale to extrapolate from).

**Critical alignment with practitioner survey (post-debate)**: this format
EXACTLY matches Anthropic Skills `SKILL.md` (YAML frontmatter + markdown
body + bundled assets). Adopted by OpenAI Codex CLI / Cursor / Gemini CLI
as open standard (Dec 2025). **Decision is non-novel; it's extending an
established cross-tool standard from "capability skills" to "orchestration
patterns".**

### Debate B — `org/` separate repo vs subdirectory

**Question**: Should `org/` (governance + agentic patterns) split from
ZTARE monorepo to its own github?

**Verdict**: **Subdirectory now, engineered to be split-ready.** Falsifiable
trigger for split: when ≥2 non-ZTARE substrates need org-runtime standalone
(today N=1).

**Split-ready engineering**:
- `org/INTERFACE.md` — what ZTARE consumes
- CI check: `grep -r "from src.ztare\|import ztare" org/` must return empty
- `org/VERSION` semver bumped on contract changes

**Migration path** (when triggered): `git subtree split --prefix=org/ -b
org-runtime-extract`, push to standalone, ZTARE consumes via
`pip install org-runtime` (NOT submodule — UX cost real).

**Cheaper-operation asymmetries**:
- Cheaper in subdir: atomic cross-cutting (role + validator) PR — happens weekly
- Cheaper in polyrepo: standing up new substrate that uses org-runtime — happens 0 times to date

**Verdict follows the count**.

### Debate C — Menu granularity

**Question**: 5 broad classes vs 15 narrower vs role-based for problem-class
→ pattern-chain menu?

**Verdict**: **Hierarchical — 5 broad → drill to ~15 sub-classes, with
cross-cutting pattern library indexed separately.**

**Top level (5 classes from tonight's iteration)**:
1. `hard_mathematical_residual` — conjectural class is opaque
2. `pre_category_emergence` — N traditions converging on same wall
3. `apparatus_self_audit` — catch rate climbing, build green but suspect
4. `pure_analysis_drift` — N consecutive iterations no concrete numerics
5. `too_complex_direct_attack` — question feels too big

**Drill (2-4 sub-classes per top, ~12-18 leaves)**:
- e.g., `apparatus_self_audit` → `mungerian_fallback_failure`,
  `post_rabbit_hole_audit`, `tautology_trap_detection`,
  `closure_impossibility`

**Cross-cutting library**: P11 Vocabulary Quarantine, P12 Falsifiable
Asymmetry, etc. tagged with `applies_to: [class_ids]`.

**Promotion rule** (mirrors substrate taxonomy §4): sub-classes promote
from candidate → leaf at N≥3 distinct projects. Below threshold, Director
sees `confidence: low` and falls back to parent default chain.

**Role overlay deferred**: until ≥3 cases of role-vs-class divergence under
same failure mode, single-role (Director) menu sufficient.

### Literature scan (D)

WebSearch verdict (May 2026 arxiv + practitioner sources):

**Multi-agent debate**: well-established but mostly PARALLEL
(Du et al. 2305.14325, Liang et al. 2305.19118). FRICTION-MODE
(alternating rebuttal) closest is Khan et al. 2402.06782 Anthropic/Oxford
2024 "Debating with More Persuasive LLMs". Recent 2026 frameworks: DOVA
(2603.13327), DebateCV (2603.28488), Heterogeneous Debate Engine
(2603.27404). Friction-mode is on frontier but not formalized as
orchestration primitive in any framework.

**Reducer / Vocabulary Quarantine / Falsifiable Asymmetry**: appear ABOVE
the published frontier. Closest analog is sycophancy detection (Sharma et
al. 2310.13548); generator-critic loops with "Necessary Friction"
instructions referenced in 2604.00478 "Silicon Mirror" but not formalized.

**Director picks from menu**: Magentic-One (arxiv 2411.04468 Nov 2024
Microsoft) Task Ledger + Progress Ledger + Lead-Orchestrator pattern is
THE industry precedent. Implemented in Microsoft Agent Framework as
canonical workflow.

### Practitioner survey (E)

**Frameworks survey**:
- DSPy 2.x/3.x: Python signatures + module composition. NO markdown DSL.
- LangGraph: Python StateGraph + Postgres/SQLite checkpointers. Production
  pushes DB, not files.
- AutoGen / MS Agent Framework (MAF): Python pattern catalog (GroupChat,
  SelectorGroupChat, Magentic). MAF released late 2025 unifying AutoGen +
  Semantic Kernel.
- CrewAI: YAML for agents+tasks, Python for crew. Only YAML-first
  framework; NO markdown.
- **Anthropic Skills (SKILL.md)**: YAML frontmatter + markdown body +
  bundled scripts. Open-sourced; cross-tool adopted (Codex CLI, Cursor,
  Gemini CLI) Dec 2025. **THIS IS THE PRECEDENT for our format.**

**Net architecture verdict**:
- Markdown for orchestration patterns: NOVEL scope-wise (Skills do
  capabilities, not multi-agent patterns) but format is established
- Thin Python state: AGAINST production wind (LangGraph DB), OK for
  research-loop scale; plan for migration path
- Director runtime picks pattern from menu: PARTIALLY ESTABLISHED
  (Magentic Orchestrator) — borrow that frame

## Implementation plan (locked after debates)

### Files to create / modify

**New (`org/`)**:
1. `org/patterns/` — directory with one `.md` file per pattern (SKILL.md format)
   - `org/patterns/pattern_1_friction_debate.md`
   - `org/patterns/darwin_idea_killer.md`
   - `org/patterns/reducer.md`
   - `org/patterns/vocabulary_quarantine.md`
   - `org/patterns/falsifiable_asymmetry.md`
   - `org/patterns/tautology_trap.md`
   - `org/patterns/smuggling_audit.md`
   - `org/patterns/three_leg_verification.md`
   - `org/patterns/independent_cas_verification.md`
   - `org/patterns/business_framing.md`
2. `org/menu/orchestration_menu.yaml` — hierarchical 5-broad → 15 leaves
3. `org/INTERFACE.md` — what ZTARE consumes from org/
4. `org/VERSION` — `0.1.0` initial
5. `org/runtime/pattern_catalog.yaml` — generated index (script populated)

**New (`src/ztare/orchestration/`)**:
6. `src/ztare/orchestration/pattern_catalog_indexer.py` — scans
   `org/patterns/*.md`, extracts YAML frontmatter, generates
   `org/runtime/pattern_catalog.yaml`
7. `src/ztare/orchestration/friction_debate.py` — extends
   `debate_orchestrator.py` with friction mode (alternating rebuttal)

**New (`scripts/public/`)**:
8. `scripts/public/control/check_org_independence.py` — CI lint:
   `org/` doesn't import ZTARE-specific modules

**Modified**:
9. `org/mandates/research_director_mandate.md` — add §X chain-protocol
   section pointing at `org/patterns/` + `org/menu/`
10. `AGENTS.md` — one-line reference to `org/menu/orchestration_menu.yaml`
11. `org/runtime/process_catalog_seed.yaml` — register pattern-catalog as
    process

### Implementation order (sequenced)

1. Create directory structure (`org/patterns/`, `org/menu/`)
2. Author 10 pattern files (SKILL.md format) — biggest chunk
3. Author `org/INTERFACE.md` + `org/VERSION`
4. Author `org/menu/orchestration_menu.yaml` (hierarchical)
5. Implement `pattern_catalog_indexer.py` + run it (regenerate
   `org/runtime/pattern_catalog.yaml`)
6. Extend `debate_orchestrator.py` with friction mode
7. Author `scripts/public/control/check_org_independence.py`
8. Update mandate + AGENTS.md
9. Build green check + CI sweep
10. Public/private mirror sweep per AGENTS.md §4b

### Effort estimate

10 pattern files × ~80-120L each + 5 infrastructure files + governance
updates. Realistic 4-8 hours focused work for first cut, 1-2 days for
hardening.

## Why this beats Gemini Pro's "build a Stateful Workflow Engine" proposal

Gemini Pro proposed: build separate DAG executor above autoresearch_loop
with stateless LLM Compute Nodes. After scouring the codebase:

- DAG executor: `orchestration/{debate_orchestrator,arbiter,work_discovery,
  execution_routing}.py` ALREADY EXISTS
- LLM compute nodes: `orchestration/agent_channels.py` (287L) +
  `orchestrator/parallel_mutator.py` ALREADY EXISTS
- Anti-laundering: `orchestrator/charter_critic.py` (2852L, regex
  `\btautolog(y|ical)\b`) + `post_run_meta_audit.py` (533L, cross-family
  meta-audit) ALREADY EXISTS
- Org/runtime: full M-form already in place

Gemini Pro proposal would have me re-build what exists. Honest verdict:
EXTEND existing primitives.

## Anti-laundering self-audit

Per Reducer (P13) discipline: stripped of "DAG executor", "Compute Nodes",
"AgentInvoker" elite-noun framing, my proposal reduces to: "10 markdown
files in `org/patterns/`, 1 YAML menu, 1 indexer script, 1 friction-mode
extension to existing debate_orchestrator, 1 CI lint, governance pointer
updates." That's the operator-level truth. **Not laundered.**

## Cross-references

- `agentic_engineering_patterns.md` (322L) — existing pattern catalogue
  template (will be extended)
- `agent_agnostic_recursive_gain.md` (123L) — relevant background
- `anti_pattern_catalog.md` (440L) — existing anti-pattern catalogue
- `problem_class_taxonomy.md` (234L) — existing 6-substrate-class taxonomy
  (orthogonal axis to our 5 failure-mode classes)
- `closed_loop_theorem_writer_workflow.md` (163L) — closed-loop precedent
- `ns_trackb_10x_swarm_promotion_criteria.md` — 10x criteria for promotion

## Closure criterion

Seam closes when:
1. All 10 pattern files shipped + indexed
2. Menu YAML shipped + validated
3. Friction-mode extension shipped + tested
4. CI lint green
5. Build green at architecture level
6. Public/private mirror sweep done per AGENTS.md §4b

Once closed, this seam promotes from `private/` to `public/seams/protocol/`
per AGENTS.md visibility rule (3-test: shipped + no exploit + no first-mover IP).

## Sources for literature/practitioner inputs

- Magentic-One: https://arxiv.org/abs/2411.04468
- Anthropic Skills: https://github.com/anthropics/skills
- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- DOVA deliberation-first: https://arxiv.org/html/2603.13327
- DebateCV courtroom-style: https://arxiv.org/html/2603.28488v1
- Khan et al. friction debate: https://arxiv.org/abs/2402.06782
- AutoGen Selector GroupChat: https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/selector-group-chat.html
