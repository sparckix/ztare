# Project Workbench — PRD (design thesis, information architecture & build spec)

This is the north star for the workbench UI. It exists because section-by-section redesign
without a shared thesis produces locally-pretty, globally-incoherent screens and unanswerable
questions like "does the constraint ledger go on the claim page or its own screen?" That
question is an **IA** question; this doc answers it with a rule, not a vibe.

Read order: **Thesis → JTBD → Data inventory → IA (the rule + screen map) → Layout system →
Per-screen specs → Anti-patterns.** Visual system (tokens, primitives, per-section references) lives
in the companion **`workbench_design_brief.md`** — read it before touching any screen's look.

---

## 1. Thesis — what this product is

**The workbench is where you run a research program to find out whether a claim holds up under
adversarial scrutiny — and to defend it when someone pushes back.**

The operator is *anyone who must defend a thesis under scrutiny and wants a research environment to
stress-test it*: a **PE / diligence analyst** building an IC memo, a **strategy consultant**
pressure-testing a recommendation before it ships to a client, or a **researcher / scientist**
testing a hypothesis. Same job, different domain — the tool is general-purpose but earns its keep
where a thesis carries real consequence and someone *will* push back. These are the same job:

| Research-program concept | What it is in the tool |
|---|---|
| Central position / hypothesis | the **thesis** (sharpened to a **bounded claim**) |
| Sub-claims / threads of the argument | the **research map** |
| Falsification conditions | **what would change my mind** (falsifiers) |
| Rejected alternatives | **ruled out** (non-claims) |
| Established lab facts | **derived constraints** (provisional → confirmed ledger) |
| Evidence base | **sources** (typed / raw) + **gaps** |
| Adversarial review | the **run** loop (mutator → committee judge → inverter), anti-Goodhart |
| Is it publishable / defensible | the **verdict** + the deliverable (report / claim card) |
| The program itself | the **research map** (sub-questions, threads) + **open points** |

Design consequence: the UI is not a settings panel with data tables. It is a **reasoning
surface**. Every screen answers a question the operator is actually asking, in their words, and
shows the *one artifact that screen owns* in full — flanked by summaries of what it depends on.

### 1.1 Core principles

1. **The Thesis is king.** The core object is the *thesis* — the program's central position, which
   is broader than any single claim. A thesis sharpens into a **bounded claim** (the sharp, testable
   statement) and can decompose into sub-claims / threads (the research map). Every screen revolves
   around hardening, grounding, testing, or judging **one thesis**. (Today: one thesis, sharpened to
   one bounded claim, per project — so the project *is* the thesis. Multi-thesis is a future
   extension; design thesis-centric so it extends, but build no list we have no data for.)
2. **Evidence is first-class.** Sources, what's thin, and what would weaken the claim are surfaced,
   not buried in attachments or comments.
3. **Governance is visible, not heavy.** Show backing strength, the assumptions the claim rests on,
   and what would change your mind — as calm signal, never a wall of kernel metrics.
4. **Human steering is fast.** Adding evidence, hardening the claim, and recording a decision are
   one click from the claim, always.
5. **Local and inspectable.** Everything is local with clear provenance (every value traces to a
   file); the operator can always open the raw artifact behind a summary.

Voice: plain, conversational, zero kernel jargon. Never surface raw status strings
(`ready_for_bounded_run`, `attention`). The reader is smart but not in our codebase.

### 1.2 The jobs the operator will not ask for, but will feel immediately

The visible jobs in §2 are necessary but incomplete. A strong first-pass chat answer is often faster at
explaining a problem. The Workbench earns the extra surface only when it creates consequences that prose
cannot preserve. These are product requirements, not a rationale for adding screens:

1. **Return without reconstruction.** After an hour, a day, or a long run, the operator needs the current
   standing, what changed, what is still running, and the one move most likely to change the decision. This is
   a compact *return-to-work* state, not another dashboard or a feed of every metric.
2. **Explore without laundering.** A hypothetical, a rough memo, or a model suggestion must remain visibly
   separate from the checked decision until it is admitted. Counterfactuals are read-only; drafting is allowed,
   but promotion crosses a deliberate evidence/re-ingest boundary.
3. **See the consequence of a write.** Adding evidence, recording a test result, or changing a charter must end
   in a decision delta: what standing, hinge, next test, and document freshness changed. A toast saying “saved”
   is not enough.
4. **Write without losing the chain.** People will compose in ordinary prose. The Workbench should make this
   pleasant while refusing to turn prose into evidence by assertion. A readable checked draft, annotation, and
   re-ingest/promotion loop are one product path, not an export graveyard.
5. **Wait without doubt.** Long autoresearch, proof, and fetch work need one durable status/receipt grammar:
   queued, running, last trustworthy receipt, finished, interrupted, and where to resume. Do not make users
   infer liveness from a spinner or terminal-shaped details.
6. **Trust the right thing.** A model forecast is useful diagnostic context; the checked standing, source tier,
   and falsifier remain the decision posture. Never let a percentage, a score, or a decorative bar masquerade
   as the reason a conclusion is safe.
7. **Hand off to a real person.** The final artifact must be audience-readable *and* bound to the decision that
   produced it. Its current/stale state is product data, not a footnote.

**Product test:** an artifact earns a visible surface only if the operator can inspect it, change it, simulate
it, or rely on it differently. Explanations of kernel internals belong in a receipt or tooltip, not as a
primary workflow.

---

## 2. JTBD spine — the operator's jobs, in order

- **J1 · Frame** — "State what I'm claiming and what would change my mind." → **Claim**
- **J2 · Ground** — "Bring in what backs it; show me what's thin; fill the gap." → **Evidence**
- **J3 · Constrain** — "What is my program committed to? What rules has it learned?" → **Assumptions**
- **J4 · Pressure-test** — "Attack my claim, then tell me how it held up." → **Run**
- **J5 · Judge** — "Can I rely on this, where is it weak, give me the deliverable." → **Verdict**
- **J6 · Steer** — "Where's the program, what's open, let me pick up where I left off." → **Overview / Map / Open points / History**

A formal-proof lane (**LeanMill**) sits beside this spine for claims that admit formal targets.

The operating loop is: **activate a body of work → see its topography → find the dependency that most changes
the decision → run or collect that test → recompile → ship only what the new state supports.** This is the
Workbench's product unit. Screens own artifacts, but they must make that transition legible rather than behaving
like independent dashboards.

---

## 3. Data inventory — grounded in the kernel primitives

The UI presents the kernel's actual output, not a toy subset. Principle: **the workbench reads
everything through the CLI.** A primitive the workbench shows but the CLI doesn't expose is a
**CLI gap** we fill *first* (§3.1) — never a direct file-read in the workbench server (that's the
frankenstein we're removing). **The whole stack is fair game**: if serving the JTBD needs the
**autoresearch kernel** (the engine behind the CLI) or anything in `src/` improved — not just the
CLI or workbench — improve it (e.g. compute a real trust/gaming signal rather than surface the
judge's narrative). Start small; change the kernel only when the JTBD genuinely needs it. Columns: source file · **CLI** (verb that exposes it, or GAP) ·
**Pri** (P0 build-now / P1 next / P2 later) · screen.

### Frame (the thesis itself)
| Primitive | Source | CLI | Pri | Screen |
|---|---|---|---|---|
| Bounded claim, warning | snapshot `Bounded claim`; intake/packet | `project intake`/`packet`; snapshot | P0 | Thesis |
| Falsifiers ("what would change my mind") | snapshot `Next falsifier` | snapshot/`trace` | P0 | Thesis |
| Ruled-out (non-claims) | snapshot `Non-claims` | snapshot | P0 | Thesis |
| Candidate claims (alternatives considered) | `workspace/candidate_claims.md` | **GAP** | P2 | Thesis (detail) |

### Ground (evidence)
| Primitive | Source | CLI | Pri | Screen |
|---|---|---|---|---|
| Source files (typed/raw), readiness | source index; `evidence.txt`/`compiled_evidence_*` | `project source-check`/`source-index`/`evidence-replay` | P0 | Evidence |
| Backing (claim support: count, weak/unsourced, rows) | claimSupport | `project claim-support` | P0 | Thesis · Evidence |
| Evidence gaps (target, severity, fetch_query, can_public_fetch) | `latest_evidence_gaps.json` | `project evidence-gap` / `evidence-fetch` | P0 | Evidence · Pressure-test |
| Evidence boundary ceiling (can't be sourced publicly) | eval `score_contract.evidence_boundary_*` | **via eval-results GAP** | P1 | Evidence |
| Compiled evidence packet + provenance + replay | `compiled_evidence_*.json` | `project evidence-replay` | P1 | Evidence |

### Constrain (what the program is committed to)
| Primitive | Source | CLI | Pri | Screen |
|---|---|---|---|---|
| Derived constraints (confirmed/provisional ledger, threshold) | `workspace/derived_constraints.json` | **GAP** (workbench reads file) | P0 | Assumptions |
| Constraint proposals (new, pending confirmation) | `latest_constraint_proposals.json` | **GAP** | P1 | Assumptions |
| Verified axioms / retired axioms | `verified_axioms.json`; eval `verified_axioms` | **via eval-results GAP** | P1 | Assumptions |
| Obligation contract (what the thesis must satisfy) | `workspace/obligation_contract_*.json` | **GAP** | P2 | Assumptions |

### Test (the run + how it held up) — **the agreed P0 eval payload**
| Primitive | Source | CLI | Pri | Screen |
|---|---|---|---|---|
| Score | eval `score` | `autoresearch trace` / `score-trajectory` | P0 | Pressure-test |
| **Weakest point** (most fragile part, explained) | eval `weakest_point` | `trace` (`latest_weakest_point`) — confirm full text | P0 | Pressure-test · Thesis |
| Logic gaps | eval `logic_gaps` | **GAP** | P0 | Pressure-test |
| Friction points (evaluator vs thesis) | eval `friction_points` | **GAP** | P0 | Pressure-test |
| Debate summary (what the committee argued) | eval `debate_summary` | **GAP** | P0 | Pressure-test |
| **Adversarial alignment** (is the score real or gamed) | eval `adversarial_alignment` | **GAP** | P0 | Pressure-test (trust banner) |
| Probability DAG (reasoning as nodes+edges) | `latest_probability_dag.json`; eval `probability_dag` | `trace` (carrier summary) | P1 | Pressure-test |
| Score contract / regime (gap counts by severity, mode, fingerprint) | eval `score_contract` | `score-trajectory` (fingerprint) | P1 | Pressure-test |
| Score trajectory (per-iter + across-run, rubric-change aware) | `iteration_telemetry.jsonl` | `autoresearch score-trajectory` | P0 | Pressure-test |
| Information yield (how much each iter learned) | `latest_information_yield.json` | `trace` (`information_yield_*`) | P1 | Pressure-test |
| Epistemic coherence (coherence over time) | `epistemic_coherence_*.json` | **GAP** | P2 | Pressure-test |
| Latent distance (semantic movement — gaming detector) | `latent_distance.jsonl` | **GAP** | P2 | Pressure-test (trust) |
| Structural anti-pattern (gaming tells) | `structural_anti_pattern_*.json` | **GAP** | P2 | Pressure-test (trust) |
| Inverter review (the adversary's structured objections) | `inverter_review.json` | **GAP** | P1 | Pressure-test |
| Contradictions detected | `workspace/contradictions.md` | **GAP** | P2 | Pressure-test |
| Next-discriminator queue (questions that separate rivals) | `next_discriminator_queue.jsonl` | **GAP** | P1 | Pressure-test · Open points |
| Cold-shot / OOD stress runs | `cold_shot_*` | **GAP** | P2 | Pressure-test |
| Contract violations | `contract_violations.jsonl` | **GAP** | P2 | Pressure-test (trust) |
| Run config (models, iters, judging, rubric-mode, cross-family, transport) | per-project file | `/api/run-config` (web-persisted, by design) | P0 | Pressure-test |
| Run status (live in-progress) | `ps` scan | `/api/run-status` (live-process, web) | P1 | Pressure-test |
| Scoring guide / rubric spec (Newton/Kepler/gate flags) | `rubrics/` | workbench scoring-guide; `make validate-rubric` | P1 | Pressure-test (settings) |

### Judge (verdict + deliverable)
| Primitive | Source | CLI | Pri | Screen |
|---|---|---|---|---|
| Verdict (report_support_contract: status, weak spots, reasons) | report support check | `project claim-support` / report-action | P0 | Verdict · Thesis (badge) |
| Report doc | report synthesis | workbench report-synthesis — confirm CLI | P1 | Verdict |
| Claim card (the shareable deliverable) | claim card | `ztare card build --format all --record` | P1 | Verdict |

### Steer (program navigation)
| Primitive | Source | CLI | Pri | Screen |
|---|---|---|---|---|
| Research map (sub-questions, threads, files) | `research_map.json/md` | **GAP** (workbench reads file) | P1 | Map |
| Open points / next steps | snapshot rows + receipts | snapshot | P0 | Open points |
| Open questions, facts, ranges (program notes) | `open_questions.md`, `facts.md`, `ranges.md` | **GAP** | P2 | Map/Open points |
| History / receipts (saved work timeline) | receipts jsonl | workbench (web writes) | P1 | History |
| LeanMill (targets, proof files, status) | leanmill dirs | `leanmill` CLI verbs | P1 | LeanMill |
| Settings (global model/provider access) | `.env` | `/api/settings`; settings CLI | P1 | Settings |

### 3.1 CLI gaps — fill CLI-first, but NO CLI sprawl

The CLI is itself a user surface; do not proliferate one verb per primitive. `latest_eval_results.json`
**already aggregates** `score, weakest_point, logic_gaps, friction_points, debate_summary,
adversarial_alignment, probability_dag, verified_axioms, derived_constraints, evidence_gaps,
score_contract` — so the gap is **one** read verb that surfaces that object, not six. The workbench
must not read these off disk; it shells out (pattern: `score_trajectory.py` → `autoresearch
score-trajectory`).

**One new verb covers the P0/P1 gaps:**

- **P0 · `autoresearch eval-results --project <p> [--champion] [--facet <name>] --json`** — returns
  the run's epistemic payload from `latest_eval_results.json` (or champion), reshaped/cleaned for
  presentation: `score, weakest_point, logic_gaps, friction_points, debate_summary,
  adversarial_alignment, probability_dag (summary), verified_axioms, derived_constraints (the ledger,
  confirmed/provisional + threshold — merged with `derived_constraints.json`), score_contract`.
  `--facet` returns one sub-object (e.g. `--facet constraints`, `--facet trust`) so screens fetch
  only what they render without N verbs. This single command powers **Pressure-test**, the **Thesis**
  weakest-point, and **Assumptions**. Replaces every direct `latest_eval_results.json` /
  `derived_constraints.json` read in the workbench server.

**Reuse, don't add:** `autoresearch trace` (information_yield, probability_dag carrier, dispatch),
`autoresearch score-trajectory` (score series + fingerprint), `project evidence-gap` /
`project evidence-fetch` (gaps), `project claim-support` (backing + report support).

**Transport-local does not mean writer-local:** live run status may remain an HTTP projection of process/job
state, but persisted project or Workbench state still needs one CLI-owned write contract. The browser calls
HTTP; HTTP stages request content and calls `cli.py`; the command validates and writes. Do not maintain a second
HTTP-only writer for run config, research maps, or saved history.

**P2, only if a screen needs them — add as `--facet`s of `eval-results`, never new verbs:**
`information_yield, epistemic_coherence, latent_distance, structural_anti_pattern, inverter_review,
next_discriminator_queue, contradictions, cold_shot, contract_violations`.

Each gap: add/extend the module under `src/ztare/reports/`, wire **one** verb in `cli.py` +
`_AUTORESEARCH_VERBS`, then the workbench `snapshot.run([... cli ...])` shells out. Verify with
`make public-adversarial-smoke` (failed_count: 0).

> **Verification gate (trust signal) — RESOLVED 2026-06-29:** `adversarial_alignment` is **NOT a
> computed gaming metric** — it's the judge's free-text self-assessment (a STRING the evaluator model
> fills: "high - thesis and evaluator aligned on scope/evidence/falsifiers…"; emitted in
> `validator/test_thesis.py` meta-judge schema). Do **not** present it as a hard "real / gamed"
> verdict — that overclaims. Instead:
> - **The trust banner is built from real anti-Goodhart MECHANISMS that ran**, not prose: did the
>   rubric rotate (`--auto-evolve`, score survived a tougher rubric)? committee (`--dynamic`)?
>   cross-family? were caps applied (`rubric_score_caps`)? anti-pattern tells (`structural_anti_pattern`)?
>   latent-distance flat/declining (`latent_distance` — gaming tell)? These are checkable facts.
> - **`adversarial_alignment` is shown as qualitative context** ("Evaluator's read on alignment:
>   high — …"), clearly the judge's opinion, not a metric.
> A "Trust" panel is honest only when it says *which* hardening actually ran and what the mechanical
> signals show — surface the mechanisms, label the narrative as narrative.

### 3.2 Reasoning IR contract — provenance is not support

The research map, decision state, deliverables, and stale-decision recompile consume one typed graph. Its
relations answer distinct questions and must not collapse:

- **Node provenance:** `sourced` means an indexed file or hash-bound excerpt; `llm` means the proposition or
  wording was extracted/drafted by a model. Naming a source ID does not change an extracted proposition to
  `sourced`.
- **`REPORTS`:** source → proposition provenance. It says “this source reports this,” not “this supports the
  thesis.” It is visually neutral and excluded from support reachability, dominators, strength, and corroboration.
- **`SUPPORTS` / `DERIVES`:** the only positive inferential edges. `TESTS` identifies an experiment;
  `CONSTRAINS` limits a claim; neither counts as support.
- **Warrant and admission:** every edge has an explicit W0–W3 warrant and begins W3 unless a deterministic
  admission earns more. An unmatched fact remains unattached; there is no fact→thesis fallback.
- **Citation binding:** the operator selects an indexed `source_evidence` file. The server reads and hashes that
  file and verifies the excerpt against stored bytes. Exact claim text may earn W2; a merely relevant quote keeps
  the source at W2 and the inference at W3. A changed/missing source demotes the edge to W3 on the next compile.
- **Independent sources:** byte-identical sources share a content key and count once for strength and Shapley.
  Paths and filenames do not create corroboration.
- **Stable identity:** projected node IDs are content-addressed, so a saved target survives separate CLI runs.

Complexity contract: graph assembly is `O(V + E + B)` where `B` is the bytes of distinct admitted source files;
node and edge insertion are amortized `O(1)`. Source-lineage collapse is union-find
`O((V + E) α(V))`. Exact Shapley runs over independent source groups up to the declared cap; above it the seeded
Monte Carlo path is bounded to roughly 6,000 QEM solves. The four-tier QEM profile is
`O(4 · I · (V + E))`, with convergence surfaced rather than hidden when the iteration cap is reached.

### 3.2a Compiled decision state

The domain-neutral `ztare-decision-state-v1` is the single authoritative read projected by Thesis, Pressure-test,
Open points, Map, and Verdict. It contains the crisp status (`SUPPORTED`, `BLOCKED`, `REFUTED`), operator posture,
reason, trust floor/warrant ceiling, minimal cores, hinge, next test, and a subordinate graded strength profile.
Model score/probability is run telemetry, not a field in this state. The compiler performs grounded acceptance,
minimal-core enumeration, agenda ranking, and strength propagation once per compile and reuses those results;
consumers must not recompute parallel verdicts.

### 3.3 Document activation contract

The first useful action may start with an artifact rather than a blank form. Create Project accepts Markdown,
text, CSV/TSV, JSON/log, PDF, DOCX, PPTX, and XLSX up to 8 MB. Extraction is deterministic: structured Office
formats are read from bounded ZIP/XML entries, PDF uses the local text extractor and fails closed when that
capability is absent, and text formats decode directly. Extraction is bounded to 5,000 ZIP members, 64 MB of
uncompressed ZIP content, and 400,000 returned characters.

The browser preview is not an admission boundary. Project creation submits the original bytes and the server
extracts them again. The original is preserved under `projects/<project>/attachments/`; the loop consumes a
Markdown projection under `projects/<project>/raw/` whose frontmatter records the original path, SHA-256,
extraction method, and truncation state. The same extracted text can seed one model call that drafts the pivotal
question, falsifiable thesis, falsifier, and scope guards; all drafted fields remain editable before creation.
Extraction is `O(B + X)`, where `B` is submitted bytes and `X` is bounded decompressed content.

---

## 4. Information architecture — the rule, then the map

### 4.1 The IA decision rule (memorize this)

> **Every artifact has exactly ONE home screen, where the full thing lives and is edited.
> Everywhere else it appears, it appears as a SUMMARY CARD: a headline (number or one phrase),
> ≤3 supporting facts, and a link to its home. A screen shows its own artifact in full, plus
> summary cards for what it depends on or produces. Never render a full secondary artifact inline.
> Never show a bare count with no path to the full thing.**

**Corollary: a diagnostic is not an editor.** A screen may identify the missing condition for a decision,
but it navigates to the owning surface to change that condition. Verdict judges; Evidence admits source
passages; Open points plans and records tests; Plugins define reusable document shapes; Handoff composes
the shapes that are currently safe to create. Do not turn a useful summary into a second, partial workflow.

This single rule answers every "here vs another screen?":
- The **11 derived constraints** → *home* is the **Assumptions** screen (full ledger). On **Claim**
  and **Overview** they are a summary card: "0 confirmed · 11 provisional — top: '…' — View ledger →".
- **Score trajectory** → *home* is **Pressure-test / Ready to run**. On **Overview** it's a card: latest score +
  sparkline + "See the run →".
- **Evidence gaps** → *home* is **Evidence** (and summarized post-run on **Pressure-test**). On
  **Claim** backing they're "2 points thin → Fix in Evidence".

A bare count ("11 provisional constraints") with nowhere to go is the #1 violation and is banned.

### 4.2 Screen map

Left nav, in JTBD order. Each screen is the **home** of one artifact (bold) and hosts summary
cards of related artifacts. **Overview is the returning-user landing**: a compact read model of the current
decision, next decisive test, and canonical paths into the project. It owns no second copy of an artifact;
the Thesis remains the home of the thesis, Verdict the home of reliance, and Open points the home of tests.

**Flat sidebar — the DEFINITIVE list (don't add items ad-hoc; this is the JTBD spine).** Only the
spine + first-class program views are top-level. Everything else is a sub-tab, a modal, or a prep
affordance — surfaced *in context*, never as its own menu item:

| Sidebar item | → | Contains / note |
|---|---|---|
| **Overview** *(landing)* | projects/Current project | current decision + next decisive test + shortest paths to the owning screens; no duplicate editor or project inventory |
| **Charter** *(mandate, top)* | overview/Charter | the human mandate the whole project serves — question · working thesis · scope limits · what would change it · run contract; **+ charter-drift findings** from runs (does the evolving thesis still serve the charter?) |
| **Thesis** | overview/Thesis | the current best answer **tackling the charter**; verdict badge + rail |
| **Assumptions** | overview/Assumptions | the full constraint/axiom ledger; Thesis shows a summary card linking here |
| **Evidence** | sources/Prepare files | files · compile pipeline · gaps |
| **Pressure-test** | run/Ready to run | **Run settings + Scoring guide are PREP here** (links on the landing + run sub-tabs), NOT top-level items; findings lead when a run exists; **+ inverter review + charter-drift** in the run payload |
| **Map** | overview/Research map | the program graph — promoted (this is what makes it more than one claim) |
| **Open points** | review/Things to review | kernel open-questions + discriminators |
| **Verdict** | save/Report readiness | trust judgment + deliverable |
| **History** | review/Saved history | timeline of saved work |

**Product configuration is adjacent to, not inside, the project spine.** The static product navigation exposes
**Plugins** immediately above **Settings**. Plugins is the durable home for defining domain context, scoring guides,
capabilities, and reusable document shapes; it is not a hidden sub-tab or a document-production action. A plugin
may not add, reorder, or relabel global navigation.

**Navigation ownership:** **ZTARE Projects** owns inventory, recovery, and project creation. It is active only on
those surfaces. A loaded project's **Overview** lives under **Selected project** and is the only active item on the
landing. Overview links perform ordinary navigation to the canonical section; they do not also open that section
in a modal. Modals are reserved for bounded edits, previews, confirmations, and other tasks that must return to the
same page.

**Charter is top-level (2026-06-29).** The charter (`projects/<p>/project_charter.md`) is the mandate
the kernel treats as MANDATORY CONTEXT for every mutation (`autoresearch_loop.py:2368` injects it
verbatim; it hard-caps candidates on anchor-proxy coverage). The **thesis tackles the charter** — so
the charter sits ABOVE the thesis in the IA, not buried in setup. Its home screen also surfaces
**charter drift** (below). JTBD justification for promoting it: all four personas pre-register a mandate
(deal scope / engagement brief / research question) and need to see whether the answer is still
serving it — that's a distinct object from the answer itself.

NOT top-level (deliberately): Run settings (Pressure-test prep), Scoring guide (Pressure-test prep), Report inputs
(Verdict detail). **Assumptions is top-level** because its ledger is a first-class program artifact; Thesis
shows a summary card and links to its home. **Help removed** (2026-06-29) — each screen
carries its own plain-language context, so a separate Help page was redundant. Settings (global) sits
in the app-level nav, not the project sidebar. **Adding a new sidebar item requires a PRD edit + a
JTBD justification — improvising menu items is drift.**

### 4.2a Governed-decision surfaces (the scenario / QBAF kernel) — 2026-07-10

The scenario kernel (`/api/scenario-*`: strength, wager, rice, deliverables, agenda) adds four decision
surfaces. Per the ONE-home rule they are **NOT new sidebar items** — the 2026-07-09 session that bolted
`Decision · Bets · Prioritize · Deliverables` under the Thesis subnav (10 items, no icons, off-token) was
drift and is reverted. Each surface lands as an in-context BLOCK in an existing spine home:

- **Decision** (graded strength profile + "what it rests on"/Shapley + crux) → the **Verdict** screen,
  as the *"how firmly"* block beneath the crisp reliability verdict. It exists because the crisp verdict
  is inert (every live governed map reads BLOCKED); the graded profile is the gradation.
  **Two-lane caveat (load-bearing):** the spine's `claim_support.reliability_verdict` and the scenario
  `strength.status` are DIFFERENT engines until the loop consumes the governed seams — so the strength
  block is **lane-labelled** ("From the governed map:") and never overrides the crisp verdict on the page.
- **Decision tests** (internal model: wagers) + the challenge/discriminator queue → the **Open points** screen,
  merged into ONE ranked *"what would settle it"* agenda (`unified_agenda`: implicit + declared + loop-proposed,
  one admission gate, Pareto frontier). A decision test is a discriminator with a lifecycle — a second worklist
  is the redundancy §4.2 forbids. The user-facing language is **decision test**, not gambling language; the kernel
  and CLI may retain `wager` as the stable type/verb. Defining a test is a MODAL, not an inline form or a menu
  item.
- **Deliverables** (compose-vs-loop gap) → the **Verdict** screen's existing **Handoff** block (decision
  report · claim card · checked drafts). It creates current document instances; document shapes are
  defined in Plugins. Deliverable-as-governed-view generalises to every persona, so it is spine, not
  scenario-only.
- **Prioritize (Governed RICE)** → NOT spine and NOT gated by a hard-coded PM noun. A PLUGIN-CONTRIBUTED
  panel: the product-manager scenario declares it and the workbench renders it in the scenario context
  only when that scenario is active. The panel is auto-discovered from `src/scenario-panels/`, mounted in
  the `results` host slot, and selected by `workbench_panels: [results:governed-rice]`. PM is the example;
  kernel + chrome carry no PM nouns.

#### Plugin contribution contract

- Global navigation is owned by this PRD. A plugin cannot add or reorder sidebar items.
- Scenarios compose declarative kernel capabilities and may select contextual panel refs.
- A frontend panel is code owned by its plugin author. The maintainer supplies host props and shared UI
  primitives but does not maintain a generic renderer for every domain.
- Panel modules export `scenarioPanel {id, host, label, description}` plus a default React component. Vite
  discovers modules at build time; Python capability reload does not rebuild frontend code.
- Plugin dialogs portal to `document.body` through `ModalPortal` and use `useModalBehavior`; host overflow or
  route animation must never clip a dialog. Escape closes only the top dialog, focus stays contained, and the
  trigger regains focus on close.
- Scenario selection is route state (`?scenario=<name>`). Refresh and Back/Forward must preserve the selected
  panel without making the scenario a new navigation level.

#### 4.2a.1 Scenario contributions and one-shot documents — 2026-07-11

The plugin surface has two distinct jobs. Keep them separate so extensibility does not become another
settings maze:

| Operator job | Core owns | Scenario/plugin owns |
|---|---|---|
| **See the current standing** | `decision_state`, agenda, map, evidence, fingerprint | contextual labels and a domain reading of those carriers |
| **Choose the next move** | one agenda and one admission path | optional domain panel that pre-fills the same core action |
| **Hand the decision to someone else** | governed slots, relations, stale binding, re-ingest gate | audience, section order, terminology, and renderer/presentation |
| **Make a new handoff once** | safe composition + provenance firewall | a YAML recipe or a richer code template, never a second source of truth |

The plugin authoring JTBD is therefore: **“Define the context I need without learning the Workbench’s CSS or
forking its navigation, then edit that context safely when the workflow changes.”** A plugin author should be
able to select a host, use the shared scenario-panel primitives/tokens, and declare a deliverable shape. They do
not add a sidebar item, a core carrier, a PM noun to the kernel, or a global stylesheet.

##### Declarative deliverable contract

The simplest useful one-shot document is declared in scenario YAML under `deliverable_specs`:

- `name`, `label`, `audience`, and `description` are presentation metadata.
- `sections` are labelled selections of governed node kinds (`thesis`, `claim`, `evidence`, `tension`, `gap`,
  `constraint`, `falsifier`, or `rejected`). A section includes all matching governed elements by default; a
  positive `limit` is an explicit presentation cap, not a hidden evidence filter, and should be rare.
- `presentation_brief` is renderer guidance about emphasis and reading order. It is **not** evidence, a prompt
  that can mint facts, or permission to paraphrase a governed slot.

The engine composes the recipe into the existing `Deliverable` type, includes only relations already present in
the governed graph, and runs the same set-completeness and provenance firewall as code-owned templates. **An
editable declarative design wins over a same-named code template.** Otherwise the Workbench would offer section
controls whose edits did not affect the generated document. Code-owned composition remains available for a
deliberately distinct document name with no declarative design. A customer can create a new one-shot document
from the plugin editor without writing CSS or Python.

Readable prose is a renderer responsibility, not a license to invent. The current baseline renderer emits a
clean, sectioned **checked draft** from exact graph text; it is deliberately not marketed as an audience-
ready memo. Handoff can open that draft directly in Annotate, where a writer can revise and trace it against the
current project record. The next renderer may use `presentation_brief` to produce editorial copy, but it must return through
`reingest_gate` against the exact decision fingerprint before it can be treated as a deliverable. If the pass
drops a claim, changes a relation, or adds an unsupported sentence, the result remains a draft and is not allowed
to ship. The Workbench should show this distinction plainly: **Checked draft**, **Current**, **Stale**, or
**Blocked by backing**.

##### Decision-test / wager contract

The JTBD is: **“When the decision is blocked, help me choose one uncertainty worth resolving, state what I
could actually observe, and know in advance how each result would change the standing.”** This is a planning and
learning affordance, not a confidence score or a fourth verdict.

- **One home:** Open points owns the unified *What would settle it* agenda. It contains implicit untested
  assumptions, declared user tests, and loop-suggested tests; they pass through the same kernel admission and
  Pareto lenses. No bets-only list, second ranker, or PM-specific copy is allowed.
- **Typed test:** a test names one blocked claim, an observable procedure, declared effort/cost and optional
  target date, and at least two uniquely named plausible outcomes. The author attests that the outcome set is
  exhaustive; an inconclusive branch is explicit whenever the observation may fail to resolve the question.
- **Kernel admission:** each outcome is compiled as typed evidence/edge edits and simulated against the frozen
  graph. A test is persisted only when every edit is valid and at least one declared outcome changes the compiled
  standing. Bits, severity, status changes, and tradeoff rank are computed; cost, deadline, and stakes are
  declarations, never hidden priors or confidence.
- **Lifecycle:** `open → preview → executed` (or `expired` / `invalidated`). The preview is a counterfactual:
  it applies the selected observed outcome to a copy of the current decision, writes nothing, and shows the
  before/after standing, hinge/next-test movement, and governed writes. Apply is a separate explicit action and
  writes exactly once; the resulting decision delta and fingerprint refresh the map, agenda, and deliverables.
  Expiry returns the unresolved claim to ordinary Open points; extension requires a fresh feasibility/evidence
  receipt.
- **Surface rule:** rows lead with the test and the decision under test, list human outcome labels with
  “strengthen / weaken / leave open” consequences, expose the ranked tradeoff in a tooltip, and offer only the
  next valid action: **Define this test**, **Record outcome**, or **Preview effect**. Stable IDs and kernel nouns
  remain in receipts/tooltips, not as the primary label.

##### Upcoming feature JTBDs (the acceptance bar)

These are the next lovable moves, ordered by consequence rather than novelty:

1. **Return to the work:** “What is the standing, what changed since I left, and what is the one move that can
   change it?” The project home leads with the compiled decision standing and its highest-leverage unresolved
   test, then quietly shows live work and the latest saved move. Generic readiness may fill gaps before a
   decision exists, but must never outrank a compiled next test. This must be answerable without opening six
   panels. **Standing, live work, the exact define/record action, and a project-keyed prior/current fingerprint
   comparison across browser visits are live.** The visit comparison reports only observed standing, next-test,
   or supporting-structure movement; the governed current state and Map-time typed graph diff remain authoritative.
2. **See the terrain:** “Where is the argument strong, contested, or unsupported, and which test is worth doing
   next?” Map is a presentation over the existing graph and decision state, not a new carrier.
   A saved reference may be compared with the current map as a bounded argument diff: standing, flipped claims,
   next test, and added/removed/reworded nodes or typed links. This is a projection over two governed states,
   not a replay engine or second history ledger. **The comparison now preserves both sides of reworded claims
   and renders added/removed typed links with their warrant instead of flattening the graph into prose.**
3. **Admit and learn:** “If I add this evidence or execute this decision-test outcome, what changed in the
   decision?” Every write ends in a typed delta and a new fingerprint, not a success toast. The Open-points
   agenda must make the test’s target, plausible outcomes, and computed consequence visible before the write.
4. **Wait without doubt:** “Is my run/proof/fetch still alive, and where do I pick up when it finishes?” All
   long operations use the same durable job, heartbeat, budget, and receipt affordance.
5. **Hand off once:** “Can I make the audience-facing memo now, and can I trust that it is still current?”
   Compose from governed state, label presentation guidance separately, and invalidate on decision change.
6. **Extend without drift:** “Can I add my domain’s view without becoming a Workbench maintainer?” Use shared
   panel primitives and the plugin editor; no custom global CSS, new nav, or duplicate ranker.
7. **Close the document loop:** “Can I edit or polish the copy without laundering new claims?” Annotate,
   re-ingest, and promote only through the same provenance gate.
8. **Formalize when it pays:** “Can I take the exact open obligation into LeanMill and return with an independent
   receipt?” LeanMill remains a neighbouring lane with its own job state, not a second research map.

### 4.2b UIUX laws for the governed surfaces (Fable UIUX+JTBD review, 2026-07-10)

- **Evidence admission has one owner.** **Evidence** → **Verify claim support** is the admission door:
  select an indexed source, highlight its exact passage in an inline reader, and choose the claim it bears on.
  Manual paste is an accessibility fallback, not the primary workflow. The UI
  distinguishes “source verified” from “inference checked”; it never asks the user to paste both source and
  quote into the same trust transaction. **Verdict only diagnoses the gap and links to Evidence; it never
  opens a binding modal or mutates evidence.** A project with no admitted backing shows one calm line on Verdict
  and hides zero-filled blocks. Never show a wall of `0.00` tiers, per-source `+0.00` rows, or a dead rerun action.
  Evidence shows **Source coverage** and **Decision support** as separate properties: a claim may reference a
  traceable file without its inference being admitted. Neither label may use “backed” as shorthand for both.
- **Document production has one owner.** **Handoff** creates a checked draft from an existing document design;
  **Plugins** define reusable document designs. Never expose a bare `document name` field or implementation
  action on Verdict. The operator sees a named document, why it can or cannot assemble, and the one next action.
  **Draft assembly is not decision readiness:** a checked draft may faithfully record a blocked decision and its open
  work. PM and other domain panels must show the draft's freshness separately from whether the decision is
  ready to rely on or share.
- **Run quality and reliance readiness are orthogonal.** A judge score evaluates the latest thesis against its
  scoring guide. Reliance readiness requires admitted claim-to-source inference paths and resolution of material
  open challenges. A high score may therefore coexist with a blocked decision, but the UI must state why at the
  point where both signals appear. `BLOCKED` is an amber verification state; red is reserved for `REFUTED`,
  rejected, invalid, or failed states. The reason must lead with the binding failure (for example, zero admitted
  claim-support paths) before secondary open-gap counts.

### 4.2c Surface review gate — required before a feature is called done

For every core surface, evaluate the operator's likely mental model, not just whether the component renders:

1. **Category and ownership:** Is this a read, a mutation, a planner, a document definition, or a handoff?
   It must live with that owner and link to another owner rather than partially recreating its workflow.
2. **Semantic visualisation:** Does the visual form imply a relationship the data does not support? A bar,
   percentage, colour, or position must make its unit and relation explicit. Never sort away a graph's edges or
   make per-claim probabilities look additive.
3. **Primary question:** Can an operator state what this page answers and identify one valid next action in one
   scan? Supporting detail belongs in its owning screen, a disclosure, or the file reader.
4. **State transitions:** Loading, empty, stale, blocked, running, and changed-after-write states all explain
   what is true and what happens next. A successful mutation ends with a consequential delta or receipt, not a
   generic toast.
5. **Navigation and scale:** Every persistent configuration surface is reachable from navigation; selected
   project/context is visually first; long source documents show a bounded reading excerpt and open the existing
   full-reader modal. No active context is left to ordinary alphabetical sorting. Every screen has one active
   navigation owner and every action has one transition: navigate to an owner or open a bounded task, never both.
6. **Reference-quality check:** Compare density, hierarchy, controls, and modal anatomy against the curated
   Linear/Notion/Origin/Mercury references for that surface. Borrow interaction discipline, never a second visual
   language. Any mismatch is an implementation issue, not polish deferred to a later feature pass.
- **One trust stack per screen (J5).** The crisp verdict, the graded strength, and the forecast probability are
  THREE lanes of ONE question — show one as the headline (verdict word → ONE number with a provenance caption →
  its drivers), the others subordinate and lane-labelled. Never six competing readouts. "Fresh forecast" has ONE
  home (Open points' "Ask the loop"), not a duplicate on Verdict.
- **One "Run again"** — Pressure-test owns it; every other surface links there.
- **EmptyState** = one calm LEFT-aligned line + at most one primary chip. No centered 260px void, no box (the
  three legacy `.empty-state` CSS rules are the source of the centered/left alignment inconsistency).
- **The graph fills the canvas** (`clamp(480px, calc(100vh - 320px), 820px)`) and RE-FITS on facet-change +
  resize + node-select pan — `fitView` once-at-init is not enough.
- **Confidence (the probability DAG):** the aggregate % is a JUDGMENT over the claims, not an arithmetic sum —
  caption it so, and render the claims INDENTED BY THE DAG EDGES (already shipped in the eval payload), never a
  flat %-list sorted by probability.
- **No kernel nouns on screen** (§1.1): "governed map", "bits", "Shapley share", W3/W2/W1, "DF-QuAD",
  "dominator" become plain words; method names live in `title` tooltips only.
- **Calibration (reliability prior, J5):** the Verdict shows an empirical HOLD-RATE per backing tier read from the
  recheck receipts (real re-executions: held/earned vs demoted/failed), NEVER a fabricated confidence %. Below N
  re-checks it reads "not enough to calibrate yet (N=…)"; silent with none. It accrues via the MAINTAIN/recheck
  loop and is NEVER sited at recompile (which recomputes hypothetical states — logging those would fabricate
  outcomes). Source: `warrant_recheck.tier_hold_rates` over the canonical `recheck_receipts.jsonl` — no new ledger.

| Screen | Home of | Job | Summary cards / rail it shows |
|---|---|---|---|
| **Claim** *(landing)* | the **claim, falsifiers, ruled-out** + **verdict badge** | J1 | Backing · Assumptions · Open points · Recent activity (rail) |
| **Evidence** | the **evidence base + gaps** | J2 | Backing · (gap → fetch) |
| **Assumptions** | the **constraint ledger** | J3 | (which run derived each) |
| **Pressure-test** *(Run)* | **config → readiness → run → findings + score trajectory** | J4 | Evidence gaps (post-run) · Constraints learned · Verdict |
| **Verdict** | the **trust verdict + deliverable** (report / claim card) | J5 | Backing · Open points |
| **Map** | the **research-program structure** | J6 | — |
| **Open points** | the **worklist + notes** | J6 | — |
| **History** | the **timeline / provenance** | J6 | — |
| **LeanMill** | **formal proof lane** | — | (own sub-IA) |
| **Plugins** | **domain configuration** | — | Scenarios · scoring guides · document designs; runtime integrations stay in a collapsed diagnostic disclosure |
| **Settings** | **global access** | — | — |

Notes:
- **There is no separate "Overview" screen.** Overview and Claim were showing the same information
  — the redundancy the operator called out. In a single-claim project, the program's standing
  *is* the claim's standing, so the **Claim screen carries the at-a-glance status** (verdict badge +
  quick stats in its rail) and there is nothing left for an Overview to add. When multi-claim lands,
  Overview returns as the **claims list** (health per claim) — a genuinely different object.
- **Assumptions is a top-level screen.** First-class program knowledge (a lab notebook's established
  facts), not a footnote. Concrete fix to the "11 constraints buried in a disclosure" failure.
- **Pressure-test collapses the old 3 kernel subtabs** (preflight → bounded run → findings) into one flow,
  score trajectory as the payoff.
- **Verdict badge lives on the Claim** (the IA rule: verdict's *home* is the Verdict screen; the
  Claim shows the badge + links there).

---

## 5. Layout system — two canonical layouts, one grid

Content max-width **1080px**, centered, with **32px** outer padding. Never let a reading column
strand a wide empty half — that was the My-claim v1 failure.

**L1 · Document + rail** (Linear issue detail). For a single focused artifact: Claim, Verdict,
a Run, a single constraint.
- Main column **~62%** (min 0): the artifact as a reading document — hero first, then sections.
- Rail **~34%**, sticky, `gap:16px`: summary cards (§6) of related artifacts + properties.
- Collapses to one column under ~860px.

**L2 · Summary-card grid** (Mercury home). For a home-of-many surface: Overview.
- Responsive grid, `minmax(300px, 1fr)`, `gap:20px`. Each cell is a summary card (§6).
- One **lead** card may span 2 cols and carry the headline number large (e.g. latest score).

**L3 · List** (Linear list, Mercury transactions). For Evidence, Assumptions ledger, Open points,
History. Main column is a list of label→value rows (§6 row), not a bordered table. Row click →
detail (modal or rail).

---

## 6. Design system → see the Design Brief

Tokens, the type/space scale, the primitive vocabulary (Eyebrow · Prose · SummaryCard · FactRow ·
Chip · Switch · StatusLine · Meter · the two layouts), the per-section reference map, and the visual
laws (no card-soup, status-as-words, one accent, whitespace over borders) all live in
**`workbench_design_brief.md`**. This PRD owns *what a screen does and which kernel data it shows*;
the brief owns *how it looks*. Build screens from the brief's primitives — never invent a per-screen look.

---

## 7. Per-screen PRDs (build targets)

Each screen is a `sections/<name>.jsx` **pure-view** module; `main.js` computes a view-model from
**CLI output** and passes props (pattern: `sections/thesis.jsx`). Per screen: JTBD · layout · CLI
source · main blocks (data · component · empty state) · rail · actions/links · done-when.
Build order is **PRD → CLI → screen → screenshot-judge → delete dead code**, one section at a time.

### 7.0 Definition of Done — the verification gate (run EVERY item; a green build is NOT done)

This gate exists because the recurring failure is claiming "done" on a build that has dead links,
bare counts, or mislabeled data. Before saying a screen is done, verify and **state which items you
checked** — not "looks good":

1. **Every interactive element reaches a REAL, built destination.** Drive the screenshot harness:
   click every link/button. A link whose destination screen isn't built yet **self-links** via the
   subnav fallback (`subnav[0]`) — that is a BUG, not done. List each link → its verified destination.
2. **No bare count.** Every number has a path to the underlying items (listed inline, or a working
   link to its home). "11 provisional" / "4 alternatives" with nowhere to go = NOT done (anti-pattern #2).
3. **Labels match the data.** Inspect what each field ACTUALLY contains before labeling it — e.g. intake
   `non_claims` are *scope disclaimers*, NOT ruled-out rivals. Mislabeling = NOT done.
4. **Screenshot-judged against the Mobbin reference.** Put the shot next to Linear/Mercury and name
   what's worse. Dead space / narrow-column-in-a-void = NOT done.
5. **Data is real and via the CLI** (no direct file-reads in the workbench server). Empty / never-run
   states render sensibly.
6. **Dead code deleted; `npm run build` green; `make public-adversarial-smoke` failed_count: 0.**
7. **Runtime payloads reach the exact object.** Route tests and endpoint tests are insufficient on their own.
   Exercise each rendered action with the path, ID, anchor, or artifact returned by the live CLI. A file action
   must open readable content; a navigation action must land on the named object; a refused action must explain
   why. Artifact eligibility comes from the authoritative project-file inventory; an expected filename is not
   evidence that a file exists. Invalid-path modals, guessed-file actions, containing-page landings, and silent
   no-ops are failures.
8. **Every semantic field contains instance-level information.** A field named “what would change your mind”
   must name an observable project-specific condition, not generic advice to revisit the claim when it is wrong.
   If the real value is absent, show the absence and the action that creates it; never satisfy a schema with
   boilerplate. This is the content analogue of exact deep-linking: preserve the specificity promised by the UI.

Document-review corollary: a matched passage must lead with the actual project claim it matched. Stable graph
IDs may remain as quiet audit metadata; an internal ID is not a humane answer to “what does this rest on?”

Only after ALL eight pass, say done — and report the checklist, e.g. "links: 4/4 reach built screens;
counts: constraints + ruled-out both checkable; labels verified against packet". If any item fails,
it is in-progress, not done.

### 7.0c The eigenquestion test — what every section must answer (apply BEFORE building each one)

Each section exists to answer **one question a researcher / PE diligence analyst / strategy consultant
actually has** while stress-testing a thesis. Name that question first; then surface only the kernel/CLI data
that answers it. Four rules, learned the hard way:

1. **State the eigenquestion, then source backward from it.** Don't render "whatever the prior code wired up"
   or the nearest field. History's is "did my thesis's *credibility* evolve, can I trust where it landed" — not
   "what files did I save." Thesis's is "is my claim sharp and falsifiable." Verdict's is "can I rely on this,
   and where exactly is it thin." If you can't name the right kernel artifact for the question, you haven't
   earned the right to style the screen.
2. **The score is a partial, rubric-relative signal — never the headline.** Under autoevolve / cross-run rubric
   change the bar moves, so a raw number isn't a verdict. Lead with the rubric-independent substance (what got
   stronger, what weakness surfaced, what was ruled out, what's unsupported); show the score as a *caveated*
   secondary, flagged when the rubric moved.
3. **Don't repeat what another section owns.** Pressure-test owns the deep score trajectory; Verdict owns the support
   breakdown; Map owns the topology; History owns the narrative. A figure shown in its home section is context
   elsewhere at most, never a second full rendering.
4. **If the kernel/CLI lacks the data the question needs, extend the CLI (and kernel) — don't fake it.** Log the
   gap in the section's PRD entry with the exact producer to touch (e.g. per-run `rubric_fingerprint` in
   `score_trajectory.py`). A fabricated/placeholder signal (the old `compile.fresh` lie) is worse than absence.

Negative-space sweep — **DONE 2026-06-30**: the cause was each section capping itself at 700–860px and sitting
**left-pinned** in a ~1156px area, so the right ~400px read as an empty second column. Fix: `.workspace-view`
is now ONE centered column (`max-width:960px; margin-inline:auto`) — header + sections share width and
alignment; the per-section left-pinned `max-width` caps were removed so they fill it (inner prose keeps its own
reading width). Map's graph canvas grew 760×440 → 960×540. Symmetric margins, no dead gutter.

Built this pass (2026-06-30, eigenquestion lens, all screenshot-verified): **History · Thesis · Verdict ·
Evidence · Open points · Assumptions · Map · Pressure-test** (per-section detail in each §7.x and in the project memory
`workbench-redesign-prd`). The reliability verdict moved into the CLI (`claim_support.py:reliability_verdict`).

### 7.0b Charter *(mandate, top-level)* — L1 doc+rail — **kernel-grounded, build with Thesis**
JTBD: *"State the mandate this whole project serves — and tell me if my thesis has drifted off it."*
Why top-level: the charter (`projects/<p>/project_charter.md`) is the kernel's MANDATORY CONTEXT —
injected verbatim into every mutation prompt (`autoresearch_loop.py:2368`), and it enforces real
constraints (forecast-type grammar guard `:2374`; **anchor-proxy coverage hard-caps a candidate at 50**
`:2391`). The **thesis tackles the charter**; the charter is the thing it must keep serving.
CLI / data:
- charter text + validation: `/api/charter` (`charter_payload_for_project`) — sections (with aliases):
  Project Question · Working Thesis · What Would Change It · Scope Limits · Run Contract; typed
  contracts the kernel parses (`charter_parsing.py`): **Anchor Proxies**, **Forecast Type**,
  **Asymptotic Claim Contract**. Editable via `ztare forensic-workbench save-charter`.
- **charter drift** (the "is my thesis still serving the charter?" signal): the General Office /
  M-Form audit (`mform_alignment_audit.py`) fires mid-run as score rises and writes
  `workspace/mform_pending.json` `{gap_detected, gap_description, adversarial_criterion, criterion_name}`
  + cross-run `rubrics/goodhart_log.jsonl`. When a drift gap is found it injects a 15%-weight
  "M-Form Charter Alignment" rubric dimension. **CLI GAP** → add an `eval-results --facet charter-drift`.
- **charter-critic patches** (post-run charter tuning, `charter_critic.py`): advisory patches to
  evidence/charter/rubric in `workspace/charter_patch_candidate_<run>.md` + `workspace/charter_patches.jsonl`;
  committed via the existing `ztare charter` verb. Surface as review items (later; commit stays CLI).
Main column: the five mandate sections rendered as a calm document (the CharterEditor, de-boxed),
each section editable in place. Drift, when present, leads with a labelled callout: "A run found your
thesis drifting from the charter: <gap_description>" + the adversarial criterion it added.
Rail: validation (sections present?) · forecast-type / anchor-proxy contracts (what the kernel will
enforce) · "last drift check: clean / N gaps".
Done-when (DoD §7.0): charter is in the flat sidebar (top); the five sections edit in place and save
via the storage provider; drift findings surface when a run produced them; data via CLI/`/api/charter`.

### 7.1 Thesis *(landing)* — L1 doc+rail — **BUILT (verdict-led header)**
JTBD: *"What am I arguing, what would change my mind, where is it weakest, and can I rely on it?"*
CLI: snapshot (claim/falsifiers/non-claims) · `claim-support` (backing + **`reliability`** verdict) ·
**`eval-results`** (weakest_point, score_contract ceiling, constraints.proposed_this_run).
Header — the **VERDICT leads, not the score** (score is rubric-relative/partial, §7.0c): the headline
is the CLI's reliability verdict ("Usable — verify the inferences" / "Holds up — every claim directly
sourced" / "Don't rely on it yet") with a tone dot; the **score is a caveated chip** ("scored 86") in the
substatus, followed by the WHY — the real per-claim backing mix ("21 directly sourced · 14 synthesized
across sources · none unsupported of 35"). This replaced the coarse `report_status`→"Almost there" map,
which gave no affordance. Quick actions (chips): **Pressure-test**, **Add evidence**, **Check a draft**.
**Check a draft** opens a focused modal over Thesis; it is compiler I/O, not a navigation destination.
Project-check reviews open contextually from the named check in Open points. They record a check disposition
(`reviewed` / `deferred` / `blocked`) and must never be labelled as a thesis-level decision.
Rail: **Backing** — when `score_contract.evidence_boundary_ceiling_detected`, says "score capped by
missing evidence — add sources, the claim isn't the problem". **Assumptions** — "+N learned this run"
from `constraints.proposed_this_run`. The redundant Verdict rail card (now in the header) and the dead
hardcoded `recent: []` card were removed.
Main column (~62%):
- **Hero claim** — the bounded claim, 29px. The canvas shows at most the first 900 characters; a longer
  `thesis.md` shows one calm “Open full thesis” action in the existing Markdown file-reader modal, with its
  table of contents and reading typography. Empty: "State what you're arguing in your brief →".
- **What would change my mind** — falsifiers parsed to bullets (lead + conditions). Empty: CTA.
- **Where it's weakest** — `eval-results.weakest_point` as a short honest paragraph (this is the
  P0 upgrade; replaces generic backing copy). Empty (no run yet): "Pressure-test the thesis to find its
  weakest point →".
- **Ruled out** — the non-claims, as a short list (not a bare "4").
Rail (~34%, sticky, SummaryCards):
- **Backing** — N/M strong + Meter + "k thin → Evidence".
- **Assumptions** — "0 confirmed · 11 provisional" + the single pivotal one + "View ledger →"
  (Assumptions screen). **This is the fix for the buried-count bug.**
- **Verdict** — status phrase + weak-spot count + "Open verdict →".
- **Recent activity** — last 2–3 receipts + "History →".
Done-when: no dead right-half; constraints reachable in one click; weakest_point shown; screenshot
sits beside Linear issue-detail without embarrassment.

### 7.2 Pressure-test *(Run)* — L1 staged — **BUILT** (one Ready-to-run home + RunFindings; "Harden" retired app-wide)
JTBD: *"Attack my thesis, then tell me how it held up — and whether the score is real."*
CLI: `/api/run-config` (settings) · readiness (snapshot) · `/api/run-status` (live) ·
`score-trajectory` · **`eval-results`** · `evidence-gap`.
One flow, staged (not 3 subtabs): **Settings → Ready? → Run (live) → findings in the same home.**
The post-run payoff:
- **Navigation rail** — when a run has findings, the single Pressure-test home gains a sticky **On this page**
  rail for the console, current standing, weakest point, run observation, argument path, reasoning gaps, and
  falsification work. It is a reading aid, never a second route or a duplicate summary.
- **Score trajectory** — sparkline within/across runs, rubric-change marked (built; land here).
- **Trust banner** *(if verified)* — `adversarial_alignment`: "Score is real — evaluator & thesis
  aligned on scope/evidence/falsifiers" vs "Possible gaming — …". The differentiator, up top.
- **Weakest point** · **Logic gaps** · **Friction points** · **Debate summary** — the eval payload,
  each a labelled block, plain language.
- **Model forecast / argument path** — one component, not two copies of the same DAG: a clear conclusion with
  its uncalibrated estimate, followed by the actual premise tree. Each premise percentage means confidence in
  that statement, not a contribution that adds into the conclusion; direct premises are grouped once rather
  than a ranked list that loses graph structure.
- **"How would this be proven wrong?"** — the **inverter review** (`workspace/inverter_review.json`,
  written post-champion when score ≥ 50). Plain framing, NOT "inverter": a short list of concrete
  tests that would falsify the thesis — each with what you'd measure, what counts as pass, what counts
  as fail — plus "the adversary's confidence it survives: N%". This is the strongest "what would change
  my mind" the kernel produces; surface it as that. CLI GAP → `eval-results --facet inverter`.
- **"Did the answer drift from the mandate?"** — **charter drift** (`workspace/mform_pending.json`):
  when a run found the thesis optimizing a narrow proxy instead of the charter's real intent, say so
  in one honest line + link to Charter. CLI GAP → `eval-results --facet charter-drift`.
- **Evidence gaps** — surfaced with one-click **Fetch this gap** (built).
- **Constraints learned this run** → Assumptions.
Done-when: one human flow; the eval payload is legible; trust banner only if the signal is verified;
inverter tests read as "what would change my mind", not kernel jargon; drift links to Charter.

### 7.3 Evidence — L1 main + rail — **BUILT** (compiled-evidence + "Your files" + Add-file/Edit-file modals; old `SourceEvidencePanel` replaced)
JTBD: *"What backs my thesis, where is it thin, and let me add more."*
CLI / data (grounded in `/api/sources`, `/api/evidence-fetch`, `claim-support`):
- per file: `path` (→ name), `source_type` (the typed kind, e.g. log/ticket/config), `source_type_source`
  (how it was typed), `chars` (size), `sha256` (provenance), `invalid_source_type_declaration` (flag);
  plus `source_count`, `untyped_source_count`, `source_type_counts`, `raw_dir`, compiled packet/
  provenance/replay (`compiled_evidence_*`).
- gaps: `evidence_fetch.active_gaps` (target · severity · fetch_query · can_public_fetch) + one-click
  **Fetch this gap** (already wired).
- backing: `claim-support` (claim_count, weak_or_unsourced).
- evidence-boundary ceiling: `eval-results.score_contract.evidence_boundary_ceiling_detected`.

Main column (top→bottom):
1. **Backing line** — "N of M thesis points have a source · K thin" (the "where is it thin" answer).
2. **Evidence gaps** — first-class, each: what's missing · severity · **Fetch this gap** (public) or
   "add a file / justify" (not publicly fetchable). The boundary-ceiling note when a gap can't be sourced.
3. **Your files** — the source list grouped by `source_type` (logs, tickets, configs…), each row:
   name · typed-kind · size · a provenance dot (sha256) · ⚠ if `invalid_source_type_declaration`.
   Untyped files called out. Row click → file preview.
4. **Add + compile (a PIPELINE, not two equal paths — grounded in the kernel).** The loop reads
   `evidence.txt` = the **compiled** output (`test_thesis.py EVIDENCE_PATH`); raw files in `raw/` are
   the *input*. So: **(a) Add a file** → deposits to `raw/` (optionally typed via `source_type`
   frontmatter: `source_evidence / seed_hypothesis / research_question / collection_todo`); **(b)
   Compile** → turns raw into the typed, provenance-tracked, **replayable** evidence the loop reads
   (`compiled_evidence_packet.json` + provenance + replay manifest, `evidence.txt`). Surface compile
   freshness (raw changed since last compile = stale → "Compile" CTA). **(c) Inspect compiled evidence**
   → opens `compiled_evidence_packet.json` in the **general-purpose JSON modal** (must render any JSON
   to good taste — reuse the file viewer's JSON tree). Explain the pipeline in plain words; don't
   pretend raw-only is equivalent (the loop won't see uncompiled changes).
5. **Add cited source** — choose an already indexed source file, paste an exact passage from it, and target one
   thesis/subclaim. The server verifies against stored bytes and returns source-vs-inference admission separately.
   No arbitrary citation label, no self-supplied “full source” textbox, no silent semantic promotion.
Rail: Backing card; compile-state card; counts.
Done-when (verified 2026-06-30): the raw→compile→typed pipeline is explained; compile + inspect first-class;
every file checkable. **Source soundness added** — `claim_support.source_context` (kernel content-hash) drives
"N files changed since you last compiled — the loop is scoring the old version" + a per-file "changed since
compiled" mark; gap line is severity-aware (degrading/blocking from `score_contract`) and honest when the gap
is a boundary (`evidence_boundary_ceiling_detected` → "more evidence won't lift it"). Claim breakdown left to
Verdict (dedup). Plain language, no `hash_matches_index` jargon. Loading is a distinct state: the file list must
never report zero files before `/api/sources` resolves. A stale replay manifest is explained separately from
source-file health so "all files match" and "compile required" cannot read as a contradiction. Add-file fields
collapse to one column before their minimum widths can overflow the modal.

### 7.4 Assumptions — L3 ledger — **new top-level screen — BUILT** (`sections/assumptions.jsx`)
JTBD: *"What is my program committed to, and how solid is each commitment?"*
CLI: **`eval-results`** — `verified_axioms` (top-level) + `constraints` (the ledger: confirmed/
provisional + threshold + `proposed_this_run`).
Main, strongest→weakest (these are powerful run-generated outputs — surface them, don't bury):
- **Verified axioms** — the foundation the loop treats as established (e.g. "Synthetic dates are
  internal scenario coordinates, not real-world claims"). First-class, not a footnote.
- **Provisional constraints** — rules the loop learned, not yet confirmed; full text per row +
  "confirmed after surviving N runs".
- **Confirmed constraints** — held across runs.
- **Retired** *(BUILT 2026-06-30)* — `retired_axioms`: assumptions the loop GAVE UP. A ledger that only grows
  is dishonest; show what it retracted. (Dedup: `weakest_point` stays on Thesis, not repeated here.)
- **Proposed in the latest run** — disclosure, now **deduped** against provisional (the CLI returns a newly-
  proposed constraint in both lists; the view filtered the overlap so the analyst doesn't see it twice).
**Access = a real top-level ledger with contextual summaries** (clarified 2026-07-11): Assumptions is in the
`overview` subnav because the ledger is a first-class program artifact, not a setup disclosure. Thesis and
Overview may show a short summary card, but the full list lives here; links open this built screen rather than a
second modal copy. A reusable detail modal remains appropriate for a single selected constraint. Done-when:
"View the ledger" reaches the Assumptions home showing axioms + constraints in full; no bare count; data via the
CLI.

### 7.5 Verdict — L1 doc+rail — **BUILT (CLI reliability verdict + per-claim list)**
JTBD: *"Can I rely on this, exactly where is it thin, give me the deliverable."*
Kernel read: `claim_support.py` assigns each report claim a **support status** (`direct_source_support` /
`synthesized_across_sources` / `mixed_source_support` / `local_or_seed_support` / `unsupported_no_sources`
/ `unsupported_missing_sources`) AND now a derived **`reliability`** verdict (tier + headline + summary +
breakdown) — the CLI is the master (the workbench only renders it; **the verdict logic lives in
`claim_support.py:reliability_verdict`, not the server/frontend**, per the user's CLI-first rule). This
replaced the coarse `report_status`→"Almost there" map (#51 / "almost there is bullshit").
Main:
- **Hero verdict** — the CLI reliability headline ("Usable — verify the inferences") + the WHY
  (`reliability.summary`: "21 directly sourced · 14 synthesized across sources · none unsupported of 35").
  Shared with the Thesis header (one source of verdict truth). + evidence-ceiling caveat when capped.
- **Where to verify** — every claim that ISN'T directly sourced, from `claim_support.rows`, each with its
  plain status chip + clickable source files. Sorted unsupported→inference. (Server row cap raised 12→80
  so all attention claims surface, not a sample.) Replaced the old prose `support_issues` list that showed
  "Nothing flagged" while hiding 14 inference claims.
- **The deliverable** — **View full report** / **Open claim card** (rendered docs in the file viewer).
Dedup: the score trajectory stays on Pressure-test; History owns the run narrative — Verdict repeats neither.
Done-when (verified 2026-06-29): hero states the real reliability verdict + breakdown (not freshness);
every non-direct claim listed with sources + clickable; verdict computed by the CLI; build + react-contract
smoke green.

### 7.6 Map — the problem's topography — **BUILT (typed graph + deterministic natural-language query)**
JTBD (esp. research/science ICP): *"Show me the **terrain of the problem** — what's cheap/established,
what's open, what's conceptual vs computational vs genuinely hard, the open tensions, the branches left
to test, and which sub-goals are most feasible — so I can SEE the problem and steer."* This is the
researcher's "high-resolution panorama / topographical map" (see [[product-north-star-research-scaffold]]),
the most-valued artifact for the science ICP — NOT the kernel's generic process scaffold
(Orientation/Project work/Synthesis/Handoffs, identical per project = noise; drop or tuck it).
CLI: `research-map` / `/api/research-map` (nodes · edges+relations · sections+details) · discriminators
(branches to test) · tensions · supported points. Map onto these real affordances — don't invent.
Two complementary views:
- **Textual map (built):** the live structure as plain lists — **Open tensions** · **Left to test** ·
  **What holds it up** — with the generic scaffold tucked behind "full run breakdown". (`sections/researchmap.jsx`.)
- **Queryable graph (built):** an interactive, traversable React Flow graph. Click a node for its typed
  relations and provenance; use one graph-native query bar for deterministic natural-language structural reads;
  filter by predicate or lens; move the waterline to inspect which nodes and warrant-bearing edges survive a
  stricter trust floor. Query results focus the relevant subgraph rather than producing a detached answer list.
Done-when (verified 2026-06-30): the graph leads and **reads as reasoning, not a grey hairball** — the 45
typed edges are **coloured by relation** (supports/derives green · tests blue · constrains purple · challenges
orange · could-falsify red) with arrowheads + a legend; clicking a node lists its **typed relations** in plain
verbs; `truncated` is surfaced ("+N nodes not shown"); the graph fills the centered column (960×540).
Dedup: cut the duplicate text lists — only **Open tensions** stays in text (Left-to-test → Open points,
support → Verdict, generic scaffold dropped). Grounded in `research-graph`. The NL-query layer remains future
(§55/§56). CLI gap logged: non-claim nodes carry no `weight`, so radial sizing only works for claims —
`research_graph.py` would pass a severity through to rank "hottest front".

### 7.7 Open points — L3 — **BUILT** (`sections/openpoints.jsx`: red-team + logic gaps, selected-point content, "Add evidence" → modal)
JTBD: *"What's still unresolved, why it matters, what would resolve it — and my notes."*
Kernel read (the REAL open points, not the snapshot row-table):
- **`open_questions.md`** — substantive unresolved questions, each parsed into: **the question** + **why
  it matters** + **what's blocking it** (e.g. "Whether cache miss can exceed 0.10 during healthy
  exports → determines independent-cause vs symptom; blocked: only synthetic evidence").
- **`next_discriminator_queue.jsonl`** — the **cheapest experiment to separate the rival hypotheses**
  (`cheapest_discriminator`, `auto_testable`, `can_support_promotion`).
- the user's saved reviews / next-steps (receipts).
CLI: these are workspace files → **CLI gap**: expose via `autoresearch eval-results --facet
open-questions` (questions) + `--facet discriminators` (queue) — no new verbs, just facets. Workbench
shells out (no direct file read).
Main:
- **Open questions** — each a block: question (prominent) · why it matters · what's blocking it. The
  substance, not a row label.
- **What would settle it** — the discriminators: the cheapest test per open rival, with auto-testable /
  supports-promotion flags.
- **Your notes** — saved reviews + record-next-step (existing flow).
Done-when (verified 2026-06-30): **leads with the run's own red-team** — `inverter.tests` ("Ways it could be
wrong": the adversary's doubt + a collapsible "how to check it"), then open questions (why + blocker), then
**`logic_gaps`** ("Gaps in the reasoning" — holes vs missing data), then the discriminators. No generic rows;
data via CLI facets. Dedup: discriminators live here, so Map dropped its "Left to test" list.

### 7.8 History — the investigation's research log — **BUILT (run-narrative-led)**
Eigenquestion (§7.0c): *"How did my thesis's **credibility** evolve over this investigation, and can I trust
where it landed?"* — NOT "what files did I save." The audit trail is pivotal for PE/consulting/research
defensibility, but the trail that matters is the **runs** (the reasoning), not the workbench's internal save log.

**Data — joined from two kernel sources by `run_id`:**
- `score-trajectory.runs[]` — `first/best/final_score`, `iteration_count`, `exit_reason`, `judge_model`,
  `mutator_model`, `rubric`, `iterations[]` (`estimated_cost_usd`, `champion_promoted`, `score_cap_reason`),
  plus top-level `rubric_changed_vs_champion` + champion/latest fingerprints.
- `run-history.recent_runs[]` — per-run `weakest_point` (the analyst-grade observation of what the run exposed),
  `gate_failure_count`, `timestamp`.
- `receiptHistory.receipts` — manual saves (decisions / evidence / charter). **Demoted**, see below.

**The score is partial and rubric-relative.** Under autoevolve (or any cross-run rubric change) the bar moves,
so a raw score is NOT a verdict — it never leads. What's real and rubric-independent: **did the kernel find a
STRONGER version** (`champion_promoted`) vs only re-test and hold; **what weakness the run exposed**
(`weakest_point`); **was it independently cross-checked** (judge≠mutator) or self-judged; **cost**; **gates**.

**Pattern — a research log on a day-grouped spine (Linear/GitHub feed), run events lead:**
- **Run node headline = the qualitative outcome**, not the number: "Produced a stronger version of the claim"
  (promoted, accent dot) / "Re-tested — held, no stronger version found" (scored but no new champion, ok dot).
- **The weak spot it exposed** — `weakest_point` verbatim, the substance of the log ("Weak spot it exposed: …").
- **Signal chips** (muted, deduped against Pressure-test which owns the deep trajectory): `scored N` — and when the
  rubric moved, `scored N (revised rubric — not comparable to earlier runs)`; `Cross-checked by a different
  model` / `Self-judged (same model drafted and scored)`; cost; `all gates clear` / `N gates failed`.
- **Runs NEVER collapse** — each is a distinct milestone. Only truly-identical manual saves collapse (expandable).
- **Manual saves** (decisions/evidence/charter) appear as their own dots; **process saves** (readiness refreshes,
  file writes) + **exploratory runs that changed nothing** are demoted to **quiet footnotes** ("+ N routine saves").
- No "N saved changes" count header (count-and-link smell). The timeline is the summary.

**Anti-duplication:** History is the *narrative*; the **dense sparkline + per-iteration trajectory lives on Pressure-test
(§7.2)** — History does not repeat it. The verdict's support breakdown lives on Verdict — History does not repeat it.

**CLI/kernel gap (logged):** the trajectory exposes only `rubric_changed_vs_champion` (latest-vs-champion boolean)
+ a per-run `rubric` *name*, not a per-run rubric **fingerprint** — so we can flag the newest run as "revised
rubric" but cannot mark the EXACT run where the rubric drifted. To draw a true "rubric changed here" divider in a
multi-run history, add a per-run `rubric_fingerprint` to `score_trajectory.py`/`run-history`. Deferred.
Done-when (DoD §7.0): leads with the run research-log (outcome + weak-spot + trust/cost chips), score never the
headline + rubric-relativity stated; runs don't collapse; process noise footnoted; own component
(`sections/history.jsx`); no raw paths/kernel statuses; nothing duplicated from Pressure-test/Verdict.

### 7.9 LeanMill — own lane, same design system — **job-led Workbench DONE 2026-07-10**
Formal targets / proof files / proof status. Out of the thesis spine; consistent visual language.
Was the last lane still on **Mantine** (visually foreign). Fix: `forensic-workbench/src/workspaces/leanmill-ui.jsx`
implements the subset of the Mantine API used by LeanMill and project creation (Button/TextInput/Textarea/
NativeSelect/Card/Paper/Group/Stack/SimpleGrid/Text/Title/Badge/Code/Divider/Anchor/Alert/Accordion) as
**native + design-system** shims — `.chip` buttons, `.lm-input` fields, hairline `.lm-paper`, tone `.lm-badge`
pills, and native `<details>` accordion. The Mantine runtime and styles are no longer bundled. Start is a compact
proof-state console followed by the three operator jobs: Formalize & solve, Fix a failing proof, and Ratify a
finished proof. Routes adapt to the files already indexed. Ratification is wired through
`POST /api/leanmill/ratify` to the background `proof_audit` action, with compilation, axiom allowlist, and
closure controls shown as distinct stages.

### 7.10 Settings — global only
Model/provider access (global). Per-project run config lives on **Pressure-test**, not here.

### 7.11 Capabilities to surface — DON'T FORGET (with taste)

These are powerful kernel capabilities the UI must surface; logged here so they aren't lost.

**(a) Per-project Run config — must be EXHAUSTIVE** (Pressure-test → Run settings; web-persisted overrides on
global). Surface every knob the kernel/CLI actually exposes — verify against `make experiment-loop` /
`autoresearch run` flags, don't hardcode a subset. At minimum:
- **Models per role**: mutator model · judge model · inverter model · committee model.
- **Panel / anti-Goodhart**: generate-committee (`--dynamic`) · rotating rubric / **auto-evolve**
  (`--auto-evolve`) · **cross-family** committee (`--cross-family`).
- **Run shape**: iterations · transport (api vs subscription CLI) · per-call timeout · retries ·
  model-fallback on/off.
Each with a plain-language one-liner of what it does. Audit the kernel for any flag we're missing
(e.g. honeypot, committee size, cold-shot/OOD) and add it. CLI-first: these flow through the run command.

**(b) Probability DAG** (Pressure-test findings + a peek modal). Today we show only the outcome + node/edge
count. Explain what it IS — the evaluator's probabilistic reasoning graph: nodes = claims/sub-conclusions
with probabilities, edges = inferential support. Render a real **graph visualization** (nodes + edges,
node size/color by probability) from `latest_probability_dag.json`, opened in a modal. CLI: add
`eval-results --facet dag` returning full nodes+edges (today it's summarized — extend it).

**(c) Research map — with a graph visualization** (Map screen, §7.6). The map is kernel-generated
program structure (sub-questions / threads / how they connect). Beyond the file list, render the map as
a **graph/tree viz** (threads → sub-questions → evidence). CLI gap: `project research-map --json` (read).

**(d) Rubric / Scoring guide — overhaul** (still a Codex-era panel). JTBD: *"how is my thesis scored,
and tune it."* Ground in the rubric spec (`specs/` — Newton/Kepler/gate flags, weights). Humane editor:
the real spec flags grouped (scoring dims + weights / gate toggles / run-discipline), self-explanatory,
validates (weights = 100, disable⇒reason) like `make validate-rubric`. Not raw JSON.
  - **DELIGHTFUL: "Propose a rubric from my thesis."** The kernel can generate a thesis-tailored rubric
    (`orchestrator/dynamic_rubric.py` — the engine behind auto-evolve that synthesizes rubric
    dimensions). Surface a one-click "Propose a scoring guide for this thesis" that drafts a tailored
    rubric the user then edits — instead of starting from a blank/default. **CLI gap**: today only
    `make validate-rubric` exists; add a read/generate verb (e.g. `autoresearch propose-rubric
    --project --json` wrapping `dynamic_rubric`) so the workbench consumes it CLI-first. (Confirm the
    exact entrypoint in `dynamic_rubric.py` at build time.) Not building now — logged so we don't forget.

**(e) General-purpose JSON modal** — the file viewer must render ANY JSON tastefully (already reused for
"inspect compiled evidence"); use it for DAG raw, eval-results raw, any artifact peek.

**(f) The lovable research-scaffold trio — critical integration design (2026-06-30):**

Three kernel capabilities map to the three questions a researcher asks. The design discipline is **one
home each + they COMPOSE through forecast** (the common currency = a probability). All three are
**advisory** in the kernel, so the UI frames them as *"ask the loop,"* never as truth — that honesty is
the taste, and the restraint against gimmickry.

| Capability | The question it answers | CLI | Home (one, not scattered) |
|---|---|---|---|
| **Eigenquestion** (`research_director/eigenquestion_generator.py`, `generate_eigenquestion`) | "What should I even be asking?" — the most pivotal framing question; advisory `proposed_eigenquestion_<ts>.md` | `ztare forecast`-style verb (NEW) | **Thesis / landing** — "Sharpen the question" |
| **Isomorphism** (`research_director/research_isomorphism.py`, `surface_for_research_ceiling` → `ResearchPrescription{source_theorem, transported_structure, predict_then_falsify}`) | "What is this structurally LIKE, and what does that predict?" | verb (NEW) | **Research Map** — "What is this like?" (the problem's terrain ← a known terrain) |
| **Forecast** (`forecast scratch-elicit`, DONE) | "How likely is ANY question?" — calibrated p + tail-risk | DONE | cross-cutting **"Ask anything"** + the thesis forecast (Verdict) |

**Composition (the WOW, without overdoing it):** the eigenquestion *is a question* → forecast it. The
isomorphism's `predict_then_falsify` *is a prediction* → forecast it. The user's own ad-hoc questions →
forecast them (the "random questions" delight — a lightweight Ask box where questions naturally live:
Open points). So forecast is the verb the other two feed into; we do NOT bolt a forecast button onto
every surface — just the Ask box + the thesis, and the two generators offer "forecast this" inline.

Mobbin refs (`internal/screens/curated/`): forecast → `confidence/origin-home-bignumber-forecast-button.webp`,
`confidence/origin-forecast-matrix-trend-arrows.webp` (forecast-over-horizon, a later enhancement).

Status (2026-06-30) — **all three wired end-to-end (CLI → server → one home each), advisory framing:**
- **Forecast** — CLI (`forecast scratch-elicit`) + UI DONE: Confidence block (Results) + chip (Verdict) +
  Verdict "Fresh forecast" + **"Ask the loop"** box in Open points (type ANY project question → priced p +
  tail-risk; the WOW ad-hoc embed). Reuses `/api/forecast-scratch`.
- **Eigenquestion** — DONE. CLI `ztare research eigenquestion --project <slug>` → server
  `eigenquestion_payload` → `/api/eigenquestion` → Thesis **"Sharpen the question →"** (`thesis.jsx`,
  `runEigenquestionLive`). Shows the proposed eigenquestion, advisory, "Propose another →".
- **Isomorphism** — DONE. CLI **`ztare research isomorphism --seam "<claim>" [--abstract <weakest>] --json`**
  (NEW `prescribe_for_seam()` — a thin wrapper over the existing `surface_for_research_ceiling` +
  `compile_to_test`; **no new kernel logic**, just a JSON-shaped CLI contract — this is the "improve the
  CLI first so the workbench consumes it" discipline) → server `isomorphism_payload` (builds the seam from
  the project's claim + weakest link) → `/api/isomorphism` → Map **"What is this like?"** (`researchmap.jsx`
  `WhatIsThisLike`, `runIsomorphismLive`). Renders *it's-like [theorem] in [field]* + *how it maps to your
  problem* + an actionable **"your move — predict, then falsify"** that composes into the Ask box, +
  alternatives. Verified live (Gershgorin Circle Theorem surfaced for `ai_capex`).
- **Presentation bar (2026-06-30):** every lovable feature is *delightfully presented + afforded +
  explained* — a plain-language title (the question it answers), a lead that explains it AND says advisory,
  a button that names what will happen, a running state that sets expectations, and a scannable result. The
  forecast Ask box set the bar; eigenquestion + isomorphism match it.
- **Model — no surprises (2026-06-30):** all three run on ONE model — the user's **Report model** (global
  settings; falls back to Evidence model, then gemini), via a single server helper `advisory_model(project)`.
  Each CLI takes a `--model <family>` flag fed from it. **Both API and subscription are supported**, routed by
  repo policy in `research_isomorphism._provider_and_model` / the dispatch door: **Claude → subscription CLI;
  GPT/o-series → subscription CLI** (never a metered OpenAI/Anthropic call); **gemini / deepseek / kimi / grok
  → API with the EXACT resolved model id** (the old isomorphism path silently fell back to gemini for any
  non-{gemini,deepseek,claude,codex} pick — fixed). Eigenquestion previously passed NO model (ran on the
  script default `kimi-k2.6`) — now honors the pick (`resolve_model_id`, guarded so already-resolved full ids
  pass through untouched → existing callers unaffected; 122 tests green). The Report-model setting's help text
  states this so the user sees it at the point of choice.

---

## 8. Anti-patterns — what we are killing (these are bugs)

1. **Narrow document in a wide void** — a reading column with a dead empty half. Use L1 (rail) or
   L2 (grid). (My-claim v1.)
2. **A bare count with nowhere to go** — "11 provisional constraints" and no link/list. Every count
   is a SummaryCard linking to its home.
3. **Fact-grids / fake tables** (`gap:1px` cells) — replace with FactRows.
4. **Raw kernel strings** as status — map to dot + plain word.
5. **Full secondary artifact inline** — don't render the whole evidence table on the claim page; show
   a Backing card linking to Evidence.
6. **Disclosure used to hide what the operator asked for** — disclosures are for genuinely secondary
   reference only.
7. **Mixed accents** — one indigo accent; semantic colors only on status.
8. **Overclaiming "done"** — a screen is done only after it's screenshotted and judged against the
   Mobbin references, not after it builds.


---

## §8 Build additions (2026-06-30) — keep this current

**Terminology (whole-app):** the loop verb is **"Pressure-test"**, never "Harden" (slop). The overall
argument is the **"thesis"**, never "claim" — "claim" is reserved for Verdict's *individual report
claims*. (sed pass across main.js + sections; build green.)

**Demo projects:** 6 un-ignored for ICP variety (`.gitignore` per-project allowlist, ~996K): `oeis_a001156`
(math/Lean), `glp1_adoption_economics` (healthcare), `eu_union_failure_probability_2035` (geopolitics),
`fermi_paradox_discriminator` (science), `figs_hbs_turnaround_2026` (PE/consulting), `ai_capex` (AI/finance,
**has 4 web-fetchable gaps** — demo the fetch here; `ops` has 0 so its Missing-evidence block correctly hides).

**Evidence — Add-file is a MODAL** (`openModal("sources","Add file")`, also from Open points), redesigned:
real file drop-zone (old Upload btn was dead), centered 620px form, provenance tucked, write-boundary boxes
cut. **Online evidence-gap FETCH** surfaced as "Missing evidence" — each gap shows severity + what's missing
+ one-click **"Fetch online →"** (public gaps) wired to `requestEvidenceFetchLive(target)` → the kernel's
GP-051 web-search agent (`ztare project evidence-fetch --target … --search-backend openai|anthropic
--auto-compile`). Local-only gaps say "needs a local check".

**Map — research-backed query (§7.6):** the graph is a triple store (node —predicate→ node). Added a **no-LLM
faceted query** (the established RDF approach — faceted search = a SPARQL fragment, no NL→LLM): keyword search
+ predicate-facet chips + a **"Read as statements"** triples readout (subject—predicate→object). Composes with
the type lenses. Edges already colour-coded by predicate + legend + per-node relations on click + truncation note.

**Report generation — user direction (CLI + kernel + UI) — DONE:** `synth --instructions "<NL direction>"` (or
`ZTARE_REPORT_INSTRUCTIONS` env, or `make synth INSTRUCTIONS=…`) injects a high-priority STYLE/EMPHASIS/
STRUCTURE directive into the render **and** refine prompts, for templated + dynamic renderers — bounded by the
support contract (never invents facts). The "Rewrite the report" confirm dialog now carries an optional
**"Direction for this report"** free-text field (`allowInstructions` on the prompt); it posts `instructions`
to `/api/report-synthesis`, which threads it through `run_report_action(instructions=…)` → `ZTARE_REPORT_INSTRUCTIONS`
on the synth subprocess.

**LLM transport — the ONE door (documented in `docs/concepts/architecture.md`) — DONE:** every model call (kernel,
autoresearch, **synth**, evidence-fetch) chooses API vs subscription-CLI through `dispatch_call_text(call_site,…)`
/ `ZTARE_AGENT_DISPATCH[_<SITE>]`. synth's `LLMClient.call` routes through it (call-site `"synthesis"`) — no
bespoke flag. Report model is the `report_model` workbench setting (not hardcoded). The workbench transport setting
now mirrors onto synth: `load_workbench_env` translates `ZTARE_WORKBENCH_RUN_TRANSPORT=subscription` →
`ZTARE_AGENT_DISPATCH_SYNTHESIS=agent` for every synth subprocess (explicit env still wins).

**Edit-file is a MODAL too (§7.3) — routing fix + redesign:** off-subnav modal sections (Add file, Edit file) were
silently folded to `subnav[0]` by `normalizeWorkspaceTarget` — `openModal` + `detailCopy` now resolve the raw
off-subnav key so both modals open the right panel with the right copy. The editor was redesigned to **lead with
the file being edited** ("Editing <file>"); the 12-file picker is demoted to a collapsed "Switch to another file"
disclosure (open only when no file is loaded).

**De-jargon (project-connect affordances, #70):** inventory project-details now read plain — "Brief ready to edit /
Brief is read-only / No project brief yet", "Pressure-tested · verdict ready / Not pressure-tested yet", and the
file buttons "View a source file / View a working file" (was "editable brief", "report readiness missing",
"Preview source/workspace").

**Route consolidation (2026-07-11):** `run:Results` duplicated the outcome flow and is no longer a screen. Its
findings live directly under `run:Ready to run`; `Results` remains a legacy alias only, so old links resolve to the
single Pressure-test home. The dead `run:Help` affordance remains removed, and `run:"Start run"` is an explicit
alias to `"Ready to run"`.

**Iconography (#75):** lucide icons across the sidebar nav/subnav, Day0 onboarding (JTBD journey), and the landing
`home-links` (icons mirror the sidebar). KaTeX/markdown render in modals.

**Layout (whole-app):** content is ONE centered column (`.workbench` max-width 1240, margin auto) — symmetric
small margins, header+sections aligned. (Not left-anchored — that floated off-balance.)

**Design-system component kit (the anti-wall-of-text layer):** `:root` type-scale + rhythm tokens
(`--fs-title/subhead/lead/body/meta/label`, `--lh-body`, `--gap-*`) replace the 26-font-size sprawl;
`design-system.js` exports `Block` (titled, hairline-separated subsection), `Card`, `Tag`, `MetaRow`, `Lead`.
EVERY section composes from these — migrated: Thesis, Open points, Verdict, Evidence, Assumptions, Scoring guide,
Results red-team (Lead cards, R# badges). History (timeline) + Charter (Notion doc) were already world-class.
0 console errors whole-app. Verdict-tone bug fixed (verify_inference → amber, not red — use CLI tone, not `warn`).

**Confidence (forecast — #78, part 1 DONE):** the kernel's `probability_dag` (autoresearch eval — the thesis
decomposed into sub-claims, each with a probability + watch_signal) was computed but never shown. Now a
Results "How confident is the loop?" block: a big-number outcome % (honest tones — green ≥85, amber ≥60),
each sub-claim as a probability bar, the lowest flagged **weakest link**, each with its watch signal. Compact
`78% likely to hold` chip at the Verdict hero (`v.confidence`). CLI-master (all from `/api/eval-results`).
**On-demand forecast (#78 part 2 — CLI DONE):** the **forecast pool** is separate — standalone, on-demand,
ANY domain. The sealed `forecast pool scratch-forecast` PRICES a supplied `--p-success` (tail-risk +
calibration) but doesn't invent it. NEW CLI verb `ztare forecast scratch-elicit --question … [--domain …]
[--stub-p]` (`forecast/scratch_elicit.py`) closes the gap: it ELICITS `p_success` (+ tail terms + rationale +
failure modes) via `dispatch_call_text("forecast_elicit", …)` (API/subscription — the one door), then shells
out to the sealed pool to price it → a contract `{p_success, tail_*, rationale, certified}`. Pool stays
isolated (subprocess); only elicitation is agentic. `--stub-p` = deterministic model-free path (tested,
self-check passes). REMAINING (thin): server `/api/forecast-scratch` + a workbench "Forecast this" action
(question → run the verb → render the contract; confirm/loading like the synth flow).

REMAINING: forecast-pool on-demand scratch-contract (#78 pt2, CLI-first); research-map kernel graph algorithms
(#84 — PageRank/backbone/shortest-path/cycle already in kernel, apply to claim/evidence/tension graph);
kernel-surface map for more lovable adds (#80 — DONE, see §9); non_claims kernel (#52);
main.js refactor (#40). (Pre-existing: ops-demo `synthesis_input_binding_digest_mismatch` keeps one smoke red.)

**#79 dead-code sweep (2026-06-30):** SERVER done — 9 confirmed-unused functions removed (~95 lines); the
server is genuinely load-bearing (~300 single-call payload builders), NOT the bloat it looked like. Two
audit-subagent ERRORS caught by verification before deletion: (1) it flagged `case_file_stem` as dead but a
test calls it via the dynamically-loaded server module — KEPT; (2) its CSS dead-list flags `.lm-*`/`.start-*`
/`.write-*`/`.command-*`/`.receipt-*` as safe-contiguous-deletes, but all have live JS refs (`.lm-*` has 27,
via `workspaces/leanmill-ui.jsx` which the audit didn't scan). LESSON: a dead-code subagent that greps only
`main.js`+`sections/` misses `workspaces/` and cross-file test calls — NEVER bulk-delete on its say-so;
re-verify every token against ALL frontend files + tests. CSS sweep deferred (high white-page risk, low
value). Also pre-existing: 5 run-config `effective_settings` tests are stale (expect fewer keys than the
current cross-family/committee settings emit) — fails on HEAD too, not a regression; trivial test-data fix.

---

## §9 Deferred for future versions — autoresearch capabilities the workbench does NOT surface (2026-06-30)

A read-only three-layer sweep (kernel `src/ztare/…` → CLI `cli.py` → workbench server+UI) mapped what the
engine can do vs. what the workbench exposes. **The dominant structural finding:** ~80 kernel rubric flags
are reachable ONLY by editing rubric YAML — neither `ztare autoresearch run` nor the workbench expose them
as toggles. The workbench's run-steering surface is *deliberately* the ~11 `PROJECT_RUN_CONFIG_KEYS`
(`workspace/workbench_settings.py`). Most "kernel-only" rows below are instances of that one decision — and
keeping the run surface small is correct (a UI toggle on a stagnation-triggered, N×-cost forcing function
invites expensive misuse). We surface the *advisory* research tools (the trio + inverter + committee +
rotating rubric); we defer the *run-internal forcing functions* and *fleet/portfolio ops*.

**Already wired (no action):** isomorphism, scratch forecast, adversarial inverter (`--inverter`),
dynamic/cross-family committee judging, auto-evolve/rotating rubric, one-shot eigenquestion propose.

**Cheap pull-forwards (candidate "wire now" — small, advisory, reuse an existing pattern):**
- **Charter-critic button** — kernel `orchestrator/charter_critic.py` (rubric `enable_charter_critic`). The
  workbench already owns charter editing (`/api/charter`, `charter.jsx`); a "review my charter" advisory
  call mirrors the eigenquestion-propose pattern. *Needs a CLI verb first* (no standalone verb today).
- **Eigenquestion-rotation badge** — `reports/operations_intelligence.py:summarize_eigenquestion_rotation`
  already emits `pending_projects`; a read-only "this project is due for a fresh eigenquestion" badge beside
  the existing Thesis propose button. *Rotation queue not yet a standalone CLI verb (lives inside
  `operations-intelligence`).*
- **Calibration/Elo card** — read-only panel backed by `ztare forecast brier-elo` / `calibration-stats`
  JSON, complementing the scratch-forecast Ask box. CLI exists; just a workbench consumer.

**Deferred (future versions — by design not now):**
- **Run-internal diversity/forcing functions (kernel-only, rubric-YAML, stagnation-triggered):** parallel
  mutators (`orchestrator/parallel_mutator.py`, `parallel_mutator_k`), recombination
  (`orchestrator/recombination.py`, panel-review-pending upstream), forced REFRAME
  (`orchestrator/forced_reframe.py`), cold-shot seeding family (`cold_shot_seed.py`,
  `cold_llm_erdos_seed.py`, `qualitative_evidence_cold_shot.py` + Erdős requery), divergence sweep
  (`divergence_sweep_context.py`), cross-substrate exclusion / scientific-amnesia
  (`research_director/scientific_amnesia.py`), primitive-class-rotation ledger. *Firing these by hand
  undercuts their trigger semantics; many interacting knobs. A single future "diversify seeds" preset could
  expose the seeding family at the right altitude — not per-knob toggles.*
- **Fleet/RD-ops altitude (CLI exists, wrong scope for a single-project workbench):** operations-intelligence
  report, substrate/workbench recommender (`substrate_recommender.py`), substrate portfolio sweep
  (`substrate_portfolio.py`). *Revisit if/when the workbench grows a portfolio home screen.*
- **Analysis instruments (not run-steering):** two-cultures classifier (`two_cultures.py`), research-taste
  attention router (`orchestrator/research_taste.py`).

**One-line rule for the future:** surface *advisory* tools a researcher steers by; defer *run-internal*
forcing functions (they self-trigger) and *fleet ops* (wrong altitude). Source: capability-gap sweep
2026-06-30 (#80).

### 9.1 Decision portfolios (bounded roadmap, not a dashboard)

The missing portfolio object is a **program of related governed decisions**, not the existing substrate-ops
portfolio and not merely portfolio RICE. Each member remains its own project, eigenproblem, change test, and
run history. A future explicit registry may add typed cross-project relations such as `SUPPLIES`, `BLOCKS`,
`DUPLICATES`, and `CAN_SHIP_WITHOUT`, plus shared outcomes, sequencing, and portfolio-level stop conditions.
Never infer membership by scanning `projects/`; never average project scores into a portfolio verdict; never let
progress on one project mask failure of another. Until a real repeated JTBD justifies a portfolio view, record
cross-project dependencies bidirectionally in the member charters and keep Projects centered on one decision.

---

## §10 LeanMill data audit (#91, 2026-06-30) — data is real but the pipeline is not CLI-master

Triggered by the user seeing Proof-status show **"PROOF ATTEMPTS 1"** + a raw `adhoc::cost_eq_statePriceWeighted_payoff`.

**Findings:**
- **The data is REAL.** `ztare leanmill ui-state` reports 8 Lane-B targets, 6 audit-clean, **3,151 solver
  attempts, 486 closures**, 2 corpus mandates. `analytics/public/queries/adhoc_closure_certificates.jsonl`
  is a real ledger. Not stale/placeholder.
- **CLI-master violation.** The workbench panel state comes from `server_payloads/leanmill.py:state_payload`,
  which **globs `*.lean` / `blueprints/*.md` and reads jsonl ledgers DIRECTLY** (in-process kernel-file
  reads), not by shelling a CLI. The canonical, comprehensive `ztare leanmill ui-state --json` exists
  (`leanmill/ui_state_dump.py` → `leanmill_ui_state.json`, schema `leanmill-ui-state-v1`) but is NOT consumed.
- **Scope ambiguity (the "1 vs 3151").** `state_payload`'s "Proof attempts" = `solver_lane.result_count`
  (workbench-LOCAL scope: attempts launched from the workbench = 1). `ui-state`'s 3,151 is the GLOBAL
  operation. Both "correct" for their scope, but the panel never says which — so the number reads as wrong.
- **Raw identifiers.** `adhoc::<lean_decl>` shown verbatim. Fixed in UI: `humanizeTarget()` splits the
  `adhoc::` prefix into a "ad hoc" kind tag + the Lean declaration name in code font (snake_case kept — it
  IS the theorem id, not prose).

**Remediation — DONE (CLI-master, 2026-06-30):** rather than re-map the panel to the `ui-state` schema (which
is a different, ops-level view), a thin CLI door `ztare leanmill workbench-state --json`
(`leanmill/workbench_state_dump.py`) now wraps the SAME kernel `state_payload`, and the server `/api/leanmill`
shells out to it (`leanmill_state_via_cli`, in-process fallback so the panel never blanks). Verified
byte-identical. So the state read is now CLI-master like `autoresearch research-graph`. STILL a product
decision (minor): the panel's counts are workbench-LOCAL scope ("launched here"); if the global operation view
(3,151 attempts) is wanted, add a scope label or a toggle. The write-action endpoints already surface their
`ztare leanmill …` CLI command; routing their execution through the CLI is a small follow-up.

---

## §11 "A run is happening" — telemetry-based, for BOTH lanes (#94, 2026-06-30)

**Principle:** run-in-progress feedback is derived from TELEMETRY FILES the run itself writes, NEVER from
process-grepping the OS (pgrep/psutil). Telemetry survives across machines, is CLI-readable, and doesn't
assume the run and the workbench share a host.

- **Autoresearch — already correct.** `run_status_payload` shells `ztare autoresearch run-progress
  --project <slug> --json`, which reads `iteration_telemetry.jsonl` (the per-iteration telemetry the loop
  writes). Wired: `/api/run-status` → polled every few seconds in `main.js` → global `run-progress-banner`
  (pulsing dot) when `runStatus.active`.
- **LeanMill — NEW (this session).** A worker heartbeat proves only that a worker is connected. The
  `ztare leanmill workbench-state` CLI calls proof work active only when a process-valid heartbeat owns a
  non-empty `claimed_work_id` whose work-queue row is still `claimed`. Connected idle capacity is reported
  separately and never produces a "LeanMill is running" banner; no pid/pgrep state is used as job truth.
  Missing DB → no run (never raises). The AxiomPack campaign panel also polls its existing attempt
  lease/budget read model, so a long campaign is visible before and after its attempt folder is created.

**Rule:** any future "is X running" signal reads X's telemetry/heartbeat file via a CLI, and the workbench
relays it. Never `pgrep`.

---

## §12 Research Map — what it is

The Map is the argument's topography. Nodes are typed (thesis/claim/candidate/evidence/gap/tension/
constraint/falsifier); edges are typed by what they do (`REPORTS`, `SUPPORTS`, `DERIVES`, `TESTS`,
`CHALLENGES`, `CONSTRAINS`, `FALSIFIES`). `REPORTS` is a quiet provenance edge; support edges alone determine
support paths. A strongly-connected-component condensation handles cyclic arguments first; topological
longest-path layering then puts evidence and reported propositions upstream, subclaims in the middle, and the
thesis at the decision edge. Cycles share one elevation instead of producing unstable coordinates. Layout is
`O(V + E)` plus `O(V log V)` for stable within-layer ordering and is memoized by the visible typed subgraph.
Falsifiers remain visually distinct.

Elevation is the four-tier warrant profile from the QEM kernel: proven / reproducible / cited / unchecked. The
waterline is a trust projection over that profile, never a second score; it attenuates both nodes and
warrant-bearing edges below the selected floor. Structural reads use only the typed
topology: peaks = linchpin/essential, ridge = k-core `skeleton`, passes = `critical_link`, fronts/valleys =
`fronts`, lowland = weakest-link/unsupported/defeated. The zero-dependency graph suite
(`graph_algorithms.py`, `--selfcheck`ed) computes these reads. The renderer remains React Flow; revisit only when
measured graph size or interaction latency justifies a different engine.

## §13 Interestingness — the taste rule

Compression progress, information yield, and MDL measure a PROCESS question ("is the search still
productive"), not the TRUST question the workbench exists for. So they do **not** go on the Map (that's the
argument's topography). The one read the ICP faces — **"Worth another pass?"** — lives in History as a single
band-coloured verdict, from a two-part MDL of the champion DAG (computed live or ex-post from
`history/*_dag.json`; CLI-master via `ztare autoresearch compression-progress`). **Never surface the judge
score as interestingness** — it's the gameable signal this project exists to expose; the proxy must be a hard
complexity measure.

## §14 LeanMill — its own lane, ICP, and jobs

LeanMill is the FORMAL-VERIFICATION lane. ZTARE Projects asks "is this argument trustworthy?" (soft, judged);
LeanMill asks "is this proof VALID?" (hard, kernel-checked). Same spine — anti-gaming rigor — different users
and jobs, so it is a distinct lane, not a ZTARE sub-view.

**ICP** — overlaps ZTARE's rigor-seekers but more specialized: users who want kernel-grade certainty and a Lean
target. Spans BOTH substrates:
- **Math** — competition/research math, Mathlib-adjacent lemmas (the NS / Erdős / OEIS lanes).
- **Non-math** — any claim reducible to a checkable Lean target (a spec, an invariant, a decision rule).

**JTBD — the three the lane must serve directly:**
1. **Autoformalize + solve** — "I have a statement; turn it into a Lean target and prove it." (`solver` lane)
2. **Fix a failing proof** — "I have a `.lean` that won't compile or has `sorry`s; close it." (solver on a file)
3. **Kernel-ratify a proof** — "I have a (possibly AI-generated) proof; verify it's REAL."
   `proof-audit --target <file>`: L1 compile + L2 axiom-allowlist + L3 anti-pattern / anti-laundering gates.
   This is the formal analog of ZTARE's claim-verification and the most on-brand — it catches laundered/fake
   proofs, exactly the gaming ZTARE exists to expose.

**UI implication — shipped.** The stable sub-IA remains Start / Draft target / Run a proof / Proof files / Proof
status, while Start leads with the three JTBD and live proof-state counts. Formalize routes to Draft target when
none exists and Run a proof otherwise; Fix routes to indexed Lean declarations; Ratify invokes `proof-audit`
through the background-job API. The active ZTARE project is the default save/run scope for both target and action
drafts; an explicitly entered cross-project scope is not overwritten. Axiom discovery remains a separate job and
uses the same portal, scroll lock, focus trap, Escape, and focus-restoration contract as every other Workbench
dialog. The UI does not promise drag/drop when only indexed repo files are supported.

**Decoupling the Lean toolchain (LeanMill is a distributed system).** Three concerns are already separated —
the workbench must NOT assume Lean runs on its own box:
- **Transport (decoupled):** LeanMill is a `formal-verification-provider/v1` — it emits a SIGNED, provider-neutral
  payload (`formal_verification_provider.py`); a consumer VERIFIES the signature and needs no toolchain. A
  workbench without Lean can still display and TRUST a ratify verdict. The verdict travels as a signed artifact,
  not a live compile.
- **Compute (where Lean runs):** `lake env lean` inside a `lean_root` (the lake/Mathlib project). Now
  env-overridable via `LEANMILL_LEAN_ROOT` (was hard-coded `ztare_proofs`) so a worker/box points at its own
  toolchain with no code change; the warm-REPL path (`ztare.formal.repl_compile`, `ZTARE_LEANMILL_REPL_COMPILE=1`)
  is the seam for a persistent/remote compile service.
- **Degradation (on-brand):** no toolchain ⇒ fail-CLOSED (the audit says "can't verify here," never a silent
  pass). Nodes are already addressed (`LEANMILL_NODE_ID`, station scheduler, 24×7 runner).
- **Owed:** the ratify backend should detect a local toolchain (`shutil.which lake` + lean_root exists) → run
  `proof-audit`; else dispatch to a worker / accept + verify a signed payload. Proofs are slow → run it as a
  background job with status telemetry, not a blocking call.

## §15 Shipped this cycle (2026-06-30)

Topographic Map (layout + structural reads + click-to-focus + hover); "Worth another pass?" compression verdict
in History (CLI-master, ex-post-capable); Obsidian export as a Verdict "deliverable" capstone (the verified
graph as a linked vault to write from — ZTARE is the post-thesis rigor layer, NOT a source-discovery tool);
project-list standing chips (champion confidence tier, not the judge score); type-scale + breathing pass
(`--fs-label` 11.5→12.5, denser pages given rhythm, Results metric strip → click-to-scroll); one-command
fresh-clone launch (`make forensic-workbench-live` auto-installs web deps).

**2026-07-10:** document → drafted-project activation with original-file preservation and extraction receipts;
the governed reasoning IR contract in §3.2; indexed-source citation admission; and deterministic natural-language
query over the Map's typed triples; SCC-safe topographic layout and edge-aware waterline; phase-one compiled
decision state across the core judgment surfaces; LeanMill proof-state console and first-class kernel
ratification; project-keyed invalidation so prior-project decisions and findings cannot bleed across a switch;
shared control/radius/spacing/focus tokens across active Workbench surfaces.

**2026-07-10 (decision + plugin pass):** typed compiled-decision deltas on evidence admission; scenario/rubric
authoring and capability diagnostics in Plugins; auto-discovered `results` panel contributions; governed RICE
with evidence-derived confidence and bounded estimate sensitivity; route-persisted scenario selection; and
shared modal focus, layering, and reduced-motion behavior. Follow-through tightened live deep-link hydration,
loading/error states, active-project LeanMill defaults, evidence-chain explanations, and narrow-screen modal
layouts without changing the stable project IA.

**2026-07-11 (consequence + execution pass):** outcome execution now shares one kernel service across CLI/API;
generated deliverables carry the compiled decision fingerprint and surface as stale after a decision change; the
Map defaults to cited support with Cited/Skeptic/Reproducible/Proven-only projections; and confirmed long runs
can execute through a persisted provider-neutral job receipt with stdout/stderr tails, cancellation, and
interruption detection. The browser polls the receipt and refreshes the governed snapshot after completion.

**2026-07-11 (long-run affordance pass):** autoresearch liveness now combines durable Workbench job state with
iteration telemetry, distinguishing queued, active, and stale-heartbeat model calls without declaring a live job
dead. The run console and global banner expose iteration/budget progress, last receipt age, and leave-page-safe
history. AxiomPack campaigns expose their existing phase, lease heartbeat, provider-call count, and budget ledger;
the campaign list/detail refreshes automatically and keeps the attempt-folder handoff visible.

**2026-07-12 (return + boundary pass):** Activity now projects autoresearch, LeanMill, and AxiomPack ledgers with
terminal campaign state overriding stale leases, browser-local “finished while away” state, and one owning-lane
resume action. Shared `SectionHeader`, action-button, icon-button, and segmented-control primitives establish one
34px control baseline across Activity, Plugins, and modal work; domain panels compose these rather than adding
global domain CSS. The compiled strength ledger now snapshots the decision fingerprint, posture, hinge, and next
test when the fingerprint moves, and History exposes the latest prior/current decision change. Governed brief and
decision-test list/register/preview/execute/expire plus evidence recheck now cross the HTTP boundary through
`ztare scenario ... --json`; the server transports the CLI contract. The project picker moved from duplicated full
folder records to relevant compact rows plus on-demand recovery detail, reducing its measured response from
5.55 MB to 0.29 MB while retaining the current-project-first sort.

Project brief, charter, raw-source add/edit, scoring-guide, saved research-map, project-file, global-settings, and
per-project run-settings mutations now
follow the same rule: HTTP stages the request, invokes the matching `ztare forensic-workbench ... --json` or
`ztare project source-file ... --json` command, and refreshes the view from its receipt. CLI rejection becomes
an HTTP refusal; a no-op can never look like a successful save. Settings values are staged in a private temporary
JSON file rather than placed in command arguments, so provider credentials do not appear in process listings.
Portable claim-card generation now follows it too: `ztare card build --format all --record` owns rendering,
evidence-hash verification, and the receipt used by Verdict.

Project creation no longer has a hidden HTTP-only source writer. Uploaded text, extracted documents and their
original attachments, and recovered in-project files all pass through `ztare project source-file add`; review
and next-step inputs pass through `ztare forensic-workbench apply-review` / `save-next-step`; and the wrapper
receipt for a confirmed evidence fetch passes through `record-evidence-fetch`. The server's only direct durable
write is the provider-neutral job ledger, which is transport state rather than project reasoning state. After a
source add/edit, the UI states the exact consequence: **saved, not yet used in the checked decision**. It routes
the operator to map the file in the project brief and compile evidence, and never equates a valid file with an
admitted claim-to-source inference.

**2026-07-12 (portable consequence pass):** Open Points and Map now consume one CLI-owned agenda contract;
Map-time snapshot, status, and typed recompile delta are CLI-owned as well. The graph diff pairs direct identity
first and normalized semantic identity second in `O(V + E)`, preventing an ID-format migration from appearing as
research movement. Scenario effect preview, full-set document production, and audience shaping now execute
through CLI JSON contracts. Verdict document commands use the shared action-button contract; icon-only busy
controls use a distinct busy state so Activity renders one spinner, not two.

The same pass made the plugin beachhead honest: governed RICE single-project reads, portfolio reads, and bounded
factor updates now execute through the CLI, including the advertised scalar-factor shorthand. Run attribution,
document declaration history, deterministic Map query, and the Map's argument overlay are CLI-owned carriers as
well. Deduplicated decision snapshots now record a canonical research-map hash and node/edge counts; History can
say when the map changed even if the decision posture held, without adding a second score or persistent warning
surface.

“Check a draft” and “Promote copy” now share the fingerprinted `scenario reingest --json` contract; the server
only stages request text for the CLI and a changed base refuses promotion before any write. The Plugins scenario
catalog likewise comes from `scenario list --json`, so invalid manifests, document designs, and contextual-view
declarations have one interpretation across CLI and Workbench.

Evidence admission now has the same boundary: `scenario bind` independently resolves a file beneath the project
raw directory, verifies its `source_evidence` classification, hashes its bytes, checks the selected passage
verbatim, and names the target claim before appending a proposed support edge. A verified source passage earns
source authenticity; its inference remains unchecked unless the passage contains the target claim itself. This
keeps source identity and inferential support as separate properties in both kernel and UI.

Compiled-evidence assumption surfacing and sentence-level draft annotation now execute through `scenario
surface/annotate --json`; pasted text is staged by transport and never becomes project state. Document actions
preserve intent without changing the background route: “Revise and trace” opens the shared draft-check modal
directly on Edited-copy trace, loads the selected artifact before enabling review, and returns to Verdict on
close. Loading content must never render as an empty file.

Plugin catalog, detail, create/edit, and discovery reload now share the CLI's plugin-management service. The
Workbench no longer keeps a second scenario/rubric validator in its HTTP process; a manifest that opens in the
editor is the same manifest the CLI validates and the runtime resolves.

Confirmed evidence recovery now uses the same durable job contract as long research and proof work. Preview is
read-only and names the exact command and possible file boundary; confirmation launches one provider-neutral
`evidence_fetch` job, returns immediately, and projects that job into Activity with a return route to Evidence.
The Evidence surface follows the job to a terminal receipt and refreshes sources and open gaps only then. The
refresh control has one loading owner: its existing icon rotates while busy, rather than rendering a second
pseudo-spinner.

Returning-user routing now treats the bare Workbench URL as project home, restores the last successfully loaded
project, and reflects that project in the URL. Day 0 is reserved for an explicit start route or a genuinely empty
live project index. Project home is owned by **Selected project / Overview**; **ZTARE Projects** owns inventory and
setup only. The legacy hybrid detail transition was removed: section actions navigate, bounded tasks open modals,
and modal history never changes the background route.

The Projects inventory now separates three jobs instead of flattening them into one technical list: resume the
current project, switch to another connected project, or connect a folder that contains useful work but lacks a
project brief. The current project is a distinct first band; other projects are compact rows; folder recovery is a
separate segmented mode. Model-forecast percentages, filesystem paths, receipt counts, and inline write-boundary
details do not belong in this chooser. Selecting a project lands on its Overview with one navigation transition.

Navigation also preserves object-level intent. A link that names a subsection (for example **Open decision
tests**) carries a stable target anchor to the canonical owner, waits for asynchronous rendering, focuses and
briefly emphasizes the target, and never opens a second modal. Decision tests lead Open points because choosing
what to resolve is that page's primary job; its “On this page” order matches the content order. Suggested tests
lead with the decision under test, rank, and next action; their repetitive hypothetical outcomes are collapsed
behind an inspectable disclosure so the default view remains scannable.

## §16 Roadmap — highest-yield next

Kernel/CLI work is fair game. Ordered by leverage on the jobs, not by ease. Compose the existing
`research-graph`, `decision_state`, and `eval-results` carriers; do not add a parallel terrain schema:
1. **Close the decision loop.** ~~Prefill a wager from `decision_state.next_test` or an admitted agenda row;
   make outcome execution a first-class action; refresh graph + strength; and lead with the typed decision delta
   (standing, hinge, core, next test, fingerprint) instead of a toast. Add a read-only counterfactual over the
   same simulation path before any optional commit.~~ The shared record-outcome modal requires the operator to
   choose an observed result, previews its kernel-computed decision delta without writing, and only then enables
   the explicit record action; Map and Open points open that same owner surface.
2. **Decision-linked deliverable invalidation.** ~~Decision deltas now persist the prior fingerprint and show
   status, hinge, core, trust-floor, and next-test changes. Next, mark governed deliverables stale until they are
   regenerated from the new decision fingerprint.~~ Keep the binding manifest compatible with remote workers and
   expose a one-click regeneration/review receipt for stale artifacts.
3. **One trust stack.** Reuse one standing → provenance → drivers hierarchy on Thesis, Verdict, and Map. ~~Default
   the Map waterline to cited support and offer skeptic / recompute / kernel-only presets.~~ Forecasts remain in
   Open points; free-text alignment prose never becomes a hard metric.
4. **Map time.** ~~Snapshot the governed carrier on admitted changes; compare two states and explain which typed
   edges changed.~~ The Research map now exposes the existing baseline/recompile carrier as a compact Map time
   control. The strength ledger now preserves fingerprinted decision snapshots and History shows the latest
   posture/hinge/next-test change. Extend this to graph-hash snapshots at every admitted write and a side-by-side
   typed-edge detail. Counterfactual inspection belongs to item 1's read-only overlay, not a second decision carrier.
5. **Provider-neutral background jobs.** ~~Long research and proof actions need one job/receipt/telemetry contract
   so local, remote, and signed-provider execution have the same Workbench affordances.~~ The local contract is
   shipped for bounded runs; extend it to LeanMill proof-audit dispatch, remote signed receipts, and a compact
   job-history affordance without making provider names part of the core UI.
6. ~~**LeanMill ratification receipts.** Join completed proof-audit jobs to signed audit receipts in Proof status,
   show the three stage outcomes independently, and distinguish audited from governance-approved proof credit.~~
7. **PM plugin depth and the generic contribution contract.** ~~Compose fingerprint-bound leadership briefs,
   backed roadmaps, and decision-test registers from core claim cards and graph carriers.~~ The PM panel now consumes the
   core standing/agenda and the plugin editor exposes scenario deliverable designs. Its PM handoff list is resolved
   from those YAML designs and uses the same core actions as Verdict: create a missing checked draft, refresh a stale
   one, or open a current one in the shared file viewer. Finish dogfooding the same contract on Bluejay. PM nouns and
   overlays remain plugin-owned; plugins do not
   add sidebar items, core node types, or global CSS. The adapter may add AWS-specific templates and mappings only
   inside the Bluejay project; the kernel stays domain neutral.
8. **One-shot deliverable composition and editorial handoff.** ~~Let a scenario YAML declare a safe section
   recipe for a new handoff (for example a trade-off register) and compose it through the existing firewall.~~
   The safe YAML recipe, CLI/API resolution, scenario-aware Verdict home, and checked draft are live.
   Build the audience renderer next: use `presentation_brief` for emphasis and voice, keep exact graph citations
   attached to every factual sentence, and route the result through `reingest_gate` before promotion. Keep the
   visible state honest: Checked draft → audience draft → Current, or Stale/Blocked. Measure the path on decision
   quality, time-to-handoff, unsupported claims, revision after new evidence, and reproducibility against a
   plain-chat baseline; do not call it “10x” until the repeated cycle wins.

### 16.1 Sol/Grok reconciliation — the next lovable queue

The independent review agrees with Grok on the boundary and disagrees only with treating the PM lane as a late
phase. Dogfood PM now, but keep the consequence paths honest. The following are the next product bets, each tied
to a JTBD and a measurable acceptance bar:

| JTBD | Move | Owner | Acceptance bar |
|---|---|---|---|
| “I return after a change and know what moved.” | Standing + prior/current typed delta + hinge + next test in one home banner; read-only counterfactual before commit. | Core | Every admission/outcome yields a delta and new fingerprint; counterfactual never writes. |
| “Keep the fast path fast, but interrupt me when trust actually changes.” | **Event-gated verification:** evidence mutation, collaboration handoff, stale document use, and declared reliance are the triggers for a compact changed-dependencies checkpoint. Reuse the existing fingerprint delta, lineage, and stale carriers; do not add a generic debt score or permanent dashboard. | Core | Against periodic prompts at equal verification budget, reduce impact-weighted stale reliance without adding prompts to unchanged work. Kill the move if the event trigger misses affected descendants or adds material quiet-path latency. |
| “When several things are stale, check the one with the largest consequence first.” | Add downstream reuse and decision-impact signals to recheck ordering as an explicit, inspectable rank component; confidence remains one input, not the allocation rule. | Core agenda | At equal check budget, consequence-weighted ordering catches more impact-weighted stale dependencies than confidence-only and recency-only baselines; raw catch count is reported separately. |
| “I know which uncertainty is worth resolving next.” | Treat wagers as user-facing decision tests: one target, observable outcome set, explicit inconclusive branch when needed, declared effort/deadline, deterministic preview, and one explicit apply action. | Core agenda | One unified admission gate rejects one-sided/duplicate/malformed tests; rows show target, human consequences, rank/cost, and the next valid action. |
| “I can hand this to a real audience in good prose.” | **Shape for audience** lets the configured report model propose headings, grouping, and reading order over a checked draft. The deterministic renderer requires every governed slot exactly once and inserts its exact wording; Draft → Current only after fingerprint-bound trace and promotion. | Core + plugin renderer | Unsupported-claim rate remains zero by construction; measure whether ordering/headings improve readability and time-to-handoff against the checked draft and plain-chat baselines. |
| “I can define a handoff without CSS or Python.” | Use a dedicated document-design editor with governed-kind chips, reading-order controls, a structural reading-shape preview, and auto-declaration. | Core editor | YAML/UI/CLI round-trip is lossless; an editable design always owns its same-named output; unknown kinds fail before write; caps are explicit. |
| “I can add a domain lens without maintaining chrome.” | `plugin_contribution_contract_v1` is enforced during panel discovery: host, governed carriers, and typed read/write/navigate actions are required; violations appear in existing Plugins health. Shared primitives remain the visual contract. | Core contract + plugin | An invalid panel cannot load; a valid panel declares its host/carriers/actions and passes keyboard/loading/error/route checks without global CSS. |
| “I can leave long work running and resume later.” | **BUILT for autoresearch, LeanMill, AxiomPack, and evidence fetch.** Activity projects their existing durable ledgers into one shelf; each row returns to its owning lane for recovery. On a later visit, completed ledger entries newer than the prior visit are distinguished as “finished while away”; first visit does not label the backlog as new. | Core jobs | Reload and route changes preserve queued/running/stale/completed/interrupted state and a resume/recover path without inventing a second job authority; idle worker heartbeats never appear as active work. |
| “I can turn a draft into governed work.” | Edited-copy trace opens a base-fingerprint re-ingest session, shows traced, omitted, and ungoverned claims, then offers one explicit Promote action. Promotion writes a current rendering and sibling audit receipt; it never mutates the graph. | Core round-trip | Promotion refuses changed base or ungoverned sentences; the UI distinguishes omitted governed claims from inserted ungoverned prose; no pasted prose mutates the graph. |
| “I can see why this node is a ridge or valley.” | Structural reads focus the corresponding node; the node drawer explains provenance, trust tier, minimal cores, and the cheapest matching test, then routes to the owning decision-test, evidence, or verdict workflow. Counterfactual preview appears only when that node has a real registered wager. | Core map | Every label and action traces to existing research-graph/decision-state fields; no terrain carrier, second ranker, or fake simulation affordance. |
| “I know whether this is better than ChatGPT.” | Bluejay and non-PM fixtures run as the same-task baseline lane. | Evaluation | Measure time-to-sound-decision, unsupported claims, revision after new evidence, reproducibility, and spend. |
| “I want the best available model to help without rebuilding or laundering context.” | **Brief another model — BUILT.** Compile the existing governed decision brief into a read-only, fingerprinted context for blind-spot finding, thesis strengthening, next-test planning, or audience handoff. Treat project text as data, separate admitted facts from proposals, and route the response back through Check a draft. | Core interoperability | Copied context names the current fingerprint and preserves the governed brief verbatim; no external response mutates the graph; a changed fingerprint is visible before reuse; compare setup time and unsupported-claim rate with an ordinary pasted chat prompt. |

Do not ship a scalar “confidence” headline, a second agenda/ranker, a `project_terrain_v1` carrier, or reflexive
ZTARE meta in project maps. Those are explicitly rejected by the Grok review and by the IA/eigenquestion rules.

Contextual panels must invoke the same typed core action as its owning surface. The PM decision kit therefore
opens the selected agenda row's shared define/record modal; it may not replace that action with generic
navigation or a PM-specific test editor.

The Plugins page owns an on-demand extension guide rather than permanent instructional copy. It distinguishes
live data authoring (scenario, rubric, document design), reloadable Python capabilities, and build-time
contextual views, and names the actual install paths. Frontend discovery/contract validation lives in the
domain-neutral scenario-panel registry, not the application shell. Domain algorithms may be specific, but
their panels and dialogs must use reusable scenario/design-system patterns rather than domain-named global CSS.

**2026-07-12 (exact-object pass):** bare-root routing restores the last active project; Overview owns the
selected-project landing; section actions use one navigation transition and can carry an exact in-page anchor;
the project inventory leads with the current project and separates ready work from folders needing setup.
Generated-document paths are repository-relative across CLI, API, viewer, and revise/trace flows. Folder
recovery no longer invents a generic change test: missing project-specific falsifiers remain visibly missing.
The interaction smoke opens every generated document path against the real shared viewer contract. Thesis,
Evidence, History, project-map, and Handoff file actions now require the authoritative project-file inventory;
expected filenames never earn an Open action. Document provenance has a distinct `not-yet-pinned` state before
the first pressure-test, because without a baseline “added later” is not a meaningful property.

**2026-07-12 (release boundary):** the production Workbench has one release smoke for the actual adopter
surface. It builds and serves the frontend from the API origin, starts a public-scope server on an isolated
loopback port, proves that the tracked manifest is the entire visible inventory, and refuses an unlisted project
read, file preview, and write before dispatch. Remote use remains a trusted-local-user deployment over an SSH
tunnel; project scopes and CORS prevent accidental disclosure but are not authentication.

Already live, not roadmap: evidence gap → one-click **fetch**, targeted single-claim falsification, document
activation, deterministic Map query, and portable governed context for external reasoning clients.

Discipline: harden the create→run→verdict spine and freeze before piling more; the above are post-freeze.

### 16.2 Execution sequence — make the compiler feel inevitable

The queue is deliberately ordered by the product unit, not by how visually impressive a screen might be.
Every item must pass the surface-review gate (§4.2c) before the next begins.

1. **Surface correctness and semantic cleanup.** One owner per artifact; remove duplicated/legacy Results
   views; use *Pressure-test* and *decision test* in operator copy; remove implementation nouns from screens;
   keep model forecasts as one conclusion plus a non-additive premise tree. This is in progress.
2. **Close the move → consequence loop.** **BUILT for decision tests.** Map and Open points preserve the exact
   uncertainty when they open the shared define/record modal; the modal previews the kernel-computed outcome
   delta before one explicit apply; confirmation recompiles the decision; and an open Verdict rechecks handoff
   freshness from the new decision fingerprint. Existing agenda, simulation, recompile, and fingerprint carriers
   remain the source of truth. Extend this same consequence contract to other admitted writes rather than adding
   parallel flows.
3. **Return-to-work and durable jobs.** **BUILT for autoresearch, LeanMill, AxiomPack, and evidence fetch.** The
   compact shelf and project return state show standing, changed since last visit, active work, and the next
   decisive move. Confirmed evidence fetch returns immediately as a provider-neutral job, Activity owns its
   durable progress and receipt, and Evidence refreshes sources and gaps when the job reaches a terminal state.
4. **Time travel and safe authorship.** **Fingerprint decision history and full before/after typed-edge detail
   are live.** Evidence admission, recorded decision-test outcomes, warrant rechecks, and source add/edit now
   checkpoint through the CLI at their write boundaries; each checkpoint carries the governed graph hash and
   decision fingerprint. Source edits do not pretend to change the compiled decision before recompile. Audit the
   remaining admitted-write commands against the same invariant. Make annotate → re-ingest → promote the way an
   edited draft becomes trustworthy, with a clear draft/current/stale distinction.
5. **Plugin depth after the core loop holds.** Let domain lenses compose existing carriers and document shapes
   through shared primitives. PM depth should dogfood the contract, not create a parallel PM workbench.
