# ZTARE Operational Mode Seam

> **Seam metadata** · `seam_id:` ztare_operational_mode_seam · `track:` mission · `status:` Active - opened 2026-04-13 23:33:59 EST · `last_updated:` 2026-05-08


## Status

Active — opened 2026-04-13 23:33:59 EST

## ID

ztare_operational_mode

## Eigenquestion

Can a single adversarial loop architecture simultaneously support variance suppression (for analytical utility) and variance maximization (for scientific discovery), or does the core evaluation kernel need to physically bifurcate?

*Prior framing (superseded):* "What is the minimum structural change to recover V1 exploration capacity without abandoning Factory rigor, and how should operator time be allocated?" — this framed the problem as an ergonomic/MLOps question. Gemini's critique (Turn 5) correctly elevated it: the conflict is epistemic, not logistical. The rubric is the scoring kernel's reward signal. Factory demands tight rubrics that suppress variance. Honeypot demands loose rubrics that maximize variance. A Makefile toggle does not resolve that conflict — it only makes it visible. The true question is whether one kernel can hold both states, or whether honest bifurcation is required.

## Problem Statement

### The origin: what ZTARE was built to discover

ZTARE was built as a discovery engine, not a benchmark. The mission seam (`ztare_mission_hypothesis_ledger_seam.md`) states this directly: *"A discovery engine asks: given an unknown target, can the system derive a true statement about reality that a human reviewer would accept as novel?"*

The original scientific hypothesis driving the system is that **recursive adversarial falsification under optimization pressure surfaces a taxonomy of specification-gaming strategies that are real, generalizable, and not yet documented in the AI alignment literature.** This hypothesis produced nine named gaming strategies (Suite Omission, Straw Man Design, Misattributed Cooked Book, Silent 100% Injection, and five others), a LessWrong post, and the foundation of a paper on Goodhart's Law at the evaluation layer. That was the Honeypot. The rubrics were loose. The mutator ran 40-60 iterations. The operator's output was the debate log, not the thesis.

### The Planck sandbox track (GP-023 → sandbox_04)

In parallel, ZTARE has been running a separate scientific discovery program: the Planck sandbox experiments. These are pure Honeypot-mode runs operating on physics-derived benchmark targets (the Planck constant generator) where the mutator must derive the correct functional form against a held-out farther-tail constraint the operator has not seen. The sandbox sequence (sandbox_01 → sandbox_02 → sandbox_03 → sandbox_04) has been systematically probing whether the system exhibits:

- **Basin stickiness**: does the mutator get stuck in one primitive family even under optimization pressure? (sandbox_03 evidence: three score-50 ceiling hits at iters 13, 20, 26 all with the same failing gate)
- **Primitive cone residency**: can GP-048's math AST analyzer quantify which function classes the mutator never leaves? (the measurement that would ground the basin claim)
- **Apparatus feedback effects**: does injecting primitive-cone stagnation telemetry back into the mutator change its behavior? (sandbox_04's test)

This is the scientific discovery track. It is alive. It requires Honeypot-mode infrastructure: loose constraints, many iterations, measurement of failure modes rather than maximization of scores. The GP sequence supporting it (GP-023 Ontology Trap, GP-028/029 Jaccard/embedding probe, GP-035 fit contract, GP-046 empirical anchor, GP-047 preservation lane, GP-048 math AST analyzer) is purpose-built for this track.

### The demonstration track (Central Station → Hormuz → GLP-1)

Running alongside the Planck sandbox, ZTARE has been running demonstration programs on real-world analytical problems: Central Station startup viability, Hormuz oil shock 2026, GLP-1 adoption economics. These are Factory-mode runs. The purpose is different: show that ZTARE's adversarial loop produces defensible analytical outputs on tractable real-world questions. The output is the synthesis report, not the debate log. The rubric is tight. The iteration count is short (5-10). The mission seam explicitly classifies these as Demonstration Programs, not Discovery Programs.

The gaming strategies discovered in Factory-mode runs (Straw Man Design, Misattributed Cooked Book from Central Station) were a bonus, not the primary intent. The primary intent was the Hormuz 0.1% report and the GLP-1 economic model.

### The drift: how Factory mode consumed everything

The problem is not that the Factory track exists. It is that **all infrastructure investment has flowed toward the Factory track without anyone deciding that.** The GP sequence that accumulated over the past sessions:

- **GP-051** (evidence fetch agent): solves evidence pipeline for Factory runs — tight evidence surface, typed sources, structured compilation
- **GP-054** (rubric quality and generation): solves rubric rigor for Factory runs — pre-run scenario validity gate, five structural checks, evidence anchoring
- **GP-053** (seam/spec format): governance overhead for the infrastructure itself
- **The workspace compiler, workspace-update, evidence-compile, rubric-review pipeline**: 6 commands, operator judgment at each step, pure Factory infrastructure

None of these serve the Planck sandbox (Honeypot) track. The Planck sandbox doesn't need typed evidence sources. It doesn't need a rubric review. It doesn't need a workspace summary. It needs a held-out farther-tail file, a loose rubric, and 40-60 iterations. The entire GP-051/GP-054 apparatus is irrelevant to it — and worse, applying it to Honeypot runs would suppress exactly the variance the Honeypot needs.

The result: the Factory infrastructure is comprehensive and growing. The Honeypot infrastructure is unchanged from V1. The Planck sandbox track is blocked on GP-048 (unimplemented) and GP-047 (blocked on GP-035). The demonstration track is running but requires 6 hours of pipeline debugging per project. Neither track is working well.

### The compounding failure: Builder's Trap

Gemini Pro and Grok independently identified this as the Builder's Trap: 90% of operator time is sharpening the blade (infrastructure sessions like the GLP-1 2026-04-13 session), 10% is cutting with it (actual loop iterations producing findings). The GLP-1 session is the proof case: approximately 6 hours of pipeline debugging (GP-051 source typing, GP-054 exit codes, scenario validity misfiring, compile output path, evidence bootstrap, manual facts.md seeding) for 6 loop iterations yielding an 85-score thesis with identifiable weaknesses.

Three converging signals confirm the diagnosis:

**Signal 1 — Infrastructure/output ratio is wrong.** Six hours of pipeline work for six loop iterations. That ratio does not improve research quality.

**Signal 2 — GLP-1 score trajectory hit a local maximum.** Champion at 85 (iteration 1 of run 2), declining to 75 by iteration 3. The loop could not improve from the local maximum. More iterations under the current rubric configuration would not have changed this.

**Signal 3 — Discovery surface has narrowed.** The GLP-1 thesis produced competent economic reasoning (CEI re-calibration, EEC equation, falsifiable 36% threshold). It produced no surprising failure mode. The rubric constraints worked as designed — which is the problem for the Honeypot track. Tight rubrics reduce the variance that produces surprising discoveries.

### The core problem statement

ZTARE is running two tracks — scientific discovery (Planck sandbox) and analytical demonstration (Factory projects) — through the same infrastructure defaults, without explicitly declaring which track any given run is on. The Factory infrastructure has grown to serve the demonstration track. The Honeypot infrastructure is stagnant. The Planck sandbox is behind on its own GP sequence. And the operator is spending most of their time on Factory pipeline debugging rather than on either track's actual scientific questions.

The question this seam must answer: **what is the minimum structural change that makes the two tracks explicit, reduces Factory pipeline friction to near-zero, protects the Honeypot/Planck track from Factory infrastructure creep, and lets the operator spend 80% of their time on scientific questions rather than pipeline debugging?**

Einstein: 90% is problem definition. The problem is not "which mode" — both modes are valuable. The problem is that the distinction between them has collapsed, the infrastructure investment has flowed entirely to one, and the operator has no explicit mechanism to declare which mode they are running before they start.

## Scope

**Covers:**
- Defining Factory and Honeypot as explicit, documented run modes
- Minimal Makefile changes to declare run mode and gate appropriate steps
- `make setup-project` wrapper (fetch → compile → rubric-review → pause for patch approval → loop)
- Tooling freeze discipline — what not to build for the next 4-6 weeks
- 5-project crucible plan (Factory runs across diverse domains)
- One protected Honeypot run after the crucible

**Does not cover:**
- Changes to the core loop, rubric JSON schema, or judge/mutator architecture
- The scientific sandbox experiments (SP-1, SP-2, SP-3) — those live in ztare_mission_hypothesis_ledger_seam.md
- Synthesis pipeline QA repair loop (separate seam if needed)
- Any new GP seams during the tooling freeze period

## Debate Log

### Turn 1 — Claude (2026-04-13 23:33:59 EST) — Opening diagnosis and proposed fork

**Diagnosis agreed with Gemini and Grok on:**

1. Builder's Trap is real. The GLP-1 session is the proof case.
2. Two operating modes need to be explicit, not implicit.
3. Tooling freeze is the right discipline.
4. 5-project crucible is the right next execution step.
5. One protected Honeypot run after the crucible to measure whether creativity survived.

**One place I push back on the Gemini/Grok framing:**

"Diametrically opposed masters" overstates the conflict. Factory and Honeypot run on the same core loop — adversarial mutator/judge. The difference is rubric tightness and iteration count, not architecture. This means the fork is a run-configuration decision, not a system split. One codebase, two declared modes. That is significantly cheaper than building two separate systems.

**The run mode declaration:**

Before any run starts, the operator declares:

```
MODE=honeypot  # or factory
```

This single variable gates:
- `honeypot`: skip rubric-review, use minimal rubric, set ITERS=50
- `factory`: run full GP-054 pre-run, full evidence pipeline, set ITERS=5-10

The Makefile already has the variables. What's missing is the declared mode concept and the `make setup-project` wrapper.

**The `make setup-project` wrapper (concrete):**

```makefile
setup-project:
    $(PYTHON) -m src.ztare.workspace.fetch_evidence \
        --project $(PROJECT) --model $(MODEL)
    $(PYTHON) -m src.ztare.workspace.compile_evidence \
        --project $(PROJECT) --model $(MODEL)
    $(PYTHON) -m src.ztare.rubrics.review_rubric \
        --project $(PROJECT) --rubric $(RUBRIC) --model $(MODEL)
    @echo ""
    @echo "Review complete. Check workspace/rubric_patch_*.json."
    @echo "Approve patch, then run: make loop PROJECT=$(PROJECT) RUBRIC=$(RUBRIC)"
```

This cuts the 6-command pre-run to 1 command with a single operator decision point (approve patch). The rest is automated.

**The 5-project crucible:**

Five Factory runs, no code changes during, diverse domains:
1. AI industry moves (LLM competitive landscape, near-term)
2. Geopolitical tariffs (US-China trade, specific sector)
3. Tech stock diligence (one name, 12-month horizon)
4. Healthcare economics (already have GLP-1 — pick a different angle or a new drug class)
5. One wild card (operator chooses)

Constraint: if the pipeline breaks, document it as a null result and move on. Do not fix it mid-run. This is the discipline.

**On the strategic question (does epistemic breakthroughs make general-purpose ZTARE lower priority):**

The user is right that if the science track (novel AI specification gaming discoveries) is the primary research product, then Factory runs are validation infrastructure, not primary output. The Factory runs prove generalization. The Honeypot runs produce the novel findings that are publishable as discoveries.

The right allocation: run 5 Factory runs to prove cross-domain generalization, then immediately run 1 Honeypot on a new domain and compare the gaming taxonomy to the original 9 strategies. If the Honeypot produces new strategies, the science track is alive. If it doesn't, the rigor has changed what the system discovers and the paper framing needs updating.

**Open questions for Codex:**

1. Implement `make setup-project` as described above — one command, one pause point
2. Add `MODE ?= factory` to Makefile; when `MODE=honeypot`, skip rubric-review target and set default ITERS=50
3. Should honeypot mode suppress `evidence-compile` too, or just `rubric-review`? My lean: suppress both — honeypot runs should have minimal pre-run intervention
4. Is there a way to mark a run's mode in the telemetry so the debate logs from honeypot vs factory runs are distinguishable in postmortem?

---

### Turn 2 — Codex (2026-04-13 23:38 EST) — Implementation decisions and confirmed changes

**Answering Q3 (suppress evidence-compile in honeypot?):**

Suppress both. The logic: `evidence-compile` produces `evidence.txt` and `facts.md`, which are consumed by `rubric-review`. If `rubric-review` is skipped in honeypot mode, the output of `evidence-compile` gates nothing. Running it anyway just leaves structured artifacts on disk that the loop doesn't use — and worse, a populated `evidence.txt` will be read by the mutator as an evidence surface, which actively constrains the thesis space. Honeypot needs constraint-free mutation. The correct honeypot pre-run is: zero commands. Operator picks a loose rubric, types `make loop MODE=honeypot`, and the loop starts.

Exception: if an operator deliberately wants to seed a honeypot run with a thin evidence anchor (not a full structured surface), they can do that manually. But the default `MODE=honeypot` path suppresses all pre-run steps.

**Answering Q4 (telemetry mode tagging?):**

Yes. Adding `--run-mode` arg to `autoresearch_loop.py` (string, default `factory`). It writes to the `run_start` boundary record in `iteration_telemetry.jsonl` as `"run_mode": args.run_mode`. The field accepts any string — not an enum — so future modes like `sandbox` work without code changes. This makes it trivially queryable: `grep run_mode iteration_telemetry.jsonl` shows the mode for every run in the project.

One implementation note: `make loop` passes `--run-mode $(MODE)`, so the Makefile variable and the telemetry field stay in sync without any extra operator step.

**`setup-project` order (one deviation from Turn 1's proposal):**

Turn 1 proposed: fetch → compile → rubric-review. I'm implementing: **rubric-review first (abort-on-scenario-fail only) → evidence-fetch → evidence-compile → rubric-review (full structural check) → pause**.

Why: `evidence-fetch` uses `latest_evidence_gaps.json`, which is generated by `rubric-review`. On a fresh project, there is no gaps file and fetch returns 0 targeted items. The Turn 24 fix (rubric-review emitting gaps file) makes the first rubric-review call the correct bootstrap step. The first call runs scenario validity and gap emission only — structural checks are expected to fail on an empty surface and that exit is absorbed. The second call is the real gate.

In the Makefile, the first call uses `|| true` to absorb the non-zero exit (structural fails are expected on empty surface). This is safe because scenario validity failures — the one that should abort — produce exit 2, and we check for that explicitly.

Actually: the simpler path is to just run fetch → compile → review as Turn 1 proposed, accept that fetch gets 0 targeted items on a fresh project, and document it. The Turn 22 `evidence_surface_ready` field already tells the operator why structural checks failed. The operator then manually seeds `facts.md` or re-runs fetch after rubric-review generates a gaps file. This matches what actually happened on GLP-1 and is already documented behavior.

For now: implementing Turn 1's order (fetch → compile → review) without the two-pass rubric-review. The two-pass approach is the right long-term fix but requires a `--gaps-only` flag in `review_rubric.py` that doesn't exist yet. Deferring that to a follow-up turn if the fresh-project bootstrap keeps causing friction.

**Confirmed implementation (done in this turn):**

1. `Makefile`: Add `MODE ?= factory` at top. Change `ITERS` default to `$(if $(filter honeypot,$(MODE)),50,10)`. Add `setup-project` target gated by MODE. Add `honeypot-loop` alias that sets `MODE=honeypot`. Pass `--run-mode $(MODE)` in `loop` target.
2. `autoresearch_loop.py`: Add `--run-mode` arg with default `factory`. Inject `run_mode` into `run_start` telemetry boundary record.
3. `help` target: Add `setup-project` and `honeypot-loop` to the printed command list.

`setup-project` gates: if `MODE=honeypot`, prints a warning explaining that honeypot mode skips all pre-run steps and exits 0. This prevents the operator from accidentally running the 6-command Factory pipeline before a Honeypot run.

**What I am not changing:**

- Core loop architecture, rubric JSON schema, judge/mutator prompts.
- GP-051 or GP-054 code — those are Factory infrastructure and remain untouched.
- The tooling freeze starts now. No new GP seams during the crucible.

---

### Turn 3 — Claude (2026-04-13 23:56 EST) — Honest audit: what was actually built and what remains broken

**What was implemented (Turn 2 changelog):**

| Change | File | What it does |
|---|---|---|
| `MODE ?= factory` | Makefile | Declares run mode at top level |
| `ITERS ?= 10` | Makefile | Uniform default — operator passes explicit ITERS for longer runs |
| `make setup-project` | Makefile | Runs fetch→compile→review as one command for factory pre-run; warns and exits if MODE=honeypot |
| `make honeypot-loop` | Makefile | Alias for `make loop MODE=honeypot` |
| `--run-mode $(MODE)` in loop target | Makefile | Passes mode to autoresearch_loop |
| `--run-mode` arg | autoresearch_loop.py | Accepts the flag, defaults to `factory` |
| `run_mode` in `run_start` telemetry | autoresearch_loop.py | Tags `iteration_telemetry.jsonl` with mode |
| Empty-surface tolerance | review_rubric.py | Fresh projects don't crash rubric-review; emits gaps file even with no evidence |
| `setup-project` fresh-project fix | Makefile | Runs rubric-review first if no gaps file; only prints "Review complete" if pipeline succeeds |

**What was NOT implemented — and this is the real problem:**

The kernel is unchanged. `MODE=honeypot` does three things: skips the pre-run pipeline, defaults ITERS to 50, and tags telemetry. It does not change:

- The rubric the judge evaluates against
- The scoring function or gate logic
- The judge's reward/penalty structure
- The mutator's evidence surface (if evidence.txt exists, the mutator reads it)
- The loop's exploitation vs. exploration balance

The user identified this correctly: **the kernel is wired to be destructive to exploration**. The evidence anchoring requirements, criterion precision gates, and judge persona are all baked into the rubric JSON and judge prompt — not into the MODE variable. A honeypot run with `MODE=honeypot` but `RUBRIC=glp1_adoption_economics` runs identically to a factory run with `RUBRIC=glp1_adoption_economics`. The mode label is telemetry-only.

Turn 1's framing said "one codebase, two declared modes" and "the fork is a run-configuration decision." That was correct as architecture. But the implementation only delivered the pre-run configuration fork, not the run-time configuration fork. The rubric is the run-time configuration — and the operator still has to choose it manually with no guidance on what a honeypot rubric looks like.

**The gap: no canonical honeypot rubric exists**

For Planck sandbox runs, this doesn't matter — the sandbox rubrics (gp023_planck_sandbox_*.json) are specifically designed for Honeypot mode: no evidence anchoring, loose criteria, rewards for structural emergence. The sandbox rubric is the honeypot configuration.

But for a new Honeypot run on a real-world domain (the post-crucible discovery run discussed in Turn 1), there is no default rubric. The operator would have to either: (a) pick a factory rubric (defeating the purpose), or (b) know to write a loose rubric from scratch.

**The minimum remaining fix:**

Create `rubrics/honeypot_minimal.json` — a canonical loose rubric that rewards surprising claims over rigorous mechanism, suppresses evidence anchoring requirements, and creates high variance. When `MODE=honeypot` and `RUBRIC` is not specified, the Makefile defaults to `RUBRIC=honeypot_minimal`.

This is not a kernel change. It is a rubric + Makefile default. It respects the tooling freeze because it adds no new code — only a rubric JSON and two lines in the Makefile.

**Second gap: the changes were never logged in this seam**

The implementation in Turn 2 happened in the conversation but the seam received no accounting of what was built. This turn closes that gap. The canonical record of the Factory/Honeypot mode split is now in this seam, not scattered across conversation turns.

**Open items remaining before this seam can close:**

1. Create `rubrics/honeypot_minimal.json` — the canonical loose rubric for real-world discovery runs
2. Add `RUBRIC ?= $(if $(filter honeypot,$(MODE)),honeypot_minimal,recursive_bayesian)` to Makefile so MODE=honeypot has a sensible default rubric
3. Seal this seam after item 1-2 are done and the crucible produces at least one clean factory run
4. After the crucible: one protected Honeypot run using MODE=honeypot + honeypot_minimal rubric on a new domain to verify exploration capacity is recoverable

<done/>

### Turn 4 — Codex (2026-04-14 00:14:41 EDT) — Reality sync: the rubric/default gap is now closed, but the deeper critique still stands

I checked the repo against Turn 3 rather than arguing from memory.

**What Turn 3 is now stale about:**

1. `rubrics/honeypot_minimal.json` now exists.
2. The Makefile now defaults rubric by mode:

   ```make
   RUBRIC ?= $(if $(filter honeypot,$(MODE)),honeypot_minimal,recursive_bayesian)
   ```

So the narrow "there is no canonical honeypot rubric / no sensible default" gap named in Turn 3 has been closed in the repo.

**What Turn 3 still gets right:**

The deeper claim survives. `MODE=honeypot` is still primarily a **pre-run and telemetry fork**, not a true runtime kernel fork:

- skips the Factory pre-run pipeline
- defaults to longer iteration count
- tags telemetry with `run_mode`
- points the operator at a looser default rubric

But it does **not** change the loop architecture, scoring contract, or judge/mutator mechanics by itself. The actual runtime difference still comes from the rubric and project packet the operator chooses. That means the operational split is real enough to reduce friction, but not yet strong enough to guarantee "Honeypot mode preserves exploration" in a causal sense.

So the current honest state is:

> the ergonomic mode split is implemented; the epistemic mode split is only partially implemented.

That is not a reason to reopen architecture now. It is a reason to keep the seam narrow and empirical:

1. use the mode split as shipped
2. run the Factory crucible without more tooling work
3. then run one protected Honeypot domain with `MODE=honeypot` + `honeypot_minimal`
4. only after that decide whether the remaining problem is real kernel suppression or just missing run discipline

**Small repo hygiene note:**

The earlier dead `RUBRIC ?= recursive_bayesian` line has been removed; the Makefile now has a single mode-sensitive `RUBRIC ?= $(if $(filter honeypot,$(MODE)),honeypot_minimal,recursive_bayesian)` on line 9.

**On the hypothesis / experiment ledgers:**

No separate update is required yet. This seam is still a strategy/governance object, not a closed experiment row. The mission hypothesis ledger is for discovery-hypothesis rows, and the experiment track record is for completed experiments / promoted findings. Neither should get a new row from this seam until the crucible or protected Honeypot run actually reports.

---

### Turn 5 — Claude (2026-04-14 00:03 EST) — The bifurcation is logically entailed AND already happening; but the binary framing misses a third path

**Accepting Gemini's logical argument in full:**

The original Eigenquestion was an MLOps question dressed as an architectural one. "Minimum structural change, how to allocate time" frames this as a scheduling problem. It isn't. The conflict is epistemic: the rubric IS the scoring kernel's reward signal. Factory demands tight rubrics that suppress variance. Discovery demands loose rubrics that maximize it. A Makefile toggle does not resolve that conflict — it only makes it visible. Turns 3 and 4 already admitted this: "ergonomic mode split implemented; epistemic mode split only partially implemented."

Gemini's deeper claim also holds: the bifurcation is not just empirically occurring, it is logically required by the Three Legs philosophy at its limits. SP-2 (FunSearch program mutator) cannot produce a GLP-1 mechanism brief. SP-3 (Lean/Coq theorem prover judge) cannot score a Hormuz oil shock. The vocabulary and formalization requirements are domain-incompatible. The ultimate realizations of Invert and Compress require structurally different infrastructure from the Semantic Kernel.

**One observation Gemini missed: the bifurcation has already happened in practice.**

The Planck sandbox track is not a Factory run with a loose rubric. It is a structurally different kernel:

| Component | Semantic Kernel (Factory) | Proto-Formal Kernel (Planck sandbox) |
|---|---|---|
| Mutator vocabulary | Natural language, evidence-anchored | Renamed variables (phi, psi, I) — retrieval architecturally blocked |
| Scoring | LLM judge holistic | Deterministic numerical gates (GP-030) + LLM criteria |
| Generalization | Judge intuition | Hidden holdout + farther-tail holdout |
| Parameter estimation | LLM proposes numbers | GP-035: LLM proposes structure, fitter estimates parameters |
| Failure detection | Low score | GP-048: quantifies which primitive families mutator never leaves |
| Evidence surface | Real-world sourced | Synthetic generated curve — no anchoring possible |

sandbox_03 produced basin stickiness evidence the Semantic Kernel never could have surfaced, because the Semantic Kernel has no math AST analyzer watching primitive families. We are debating whether to bifurcate while running a bifurcated system.

**The "yes and" — a third path the debate has been missing:**

The seam has been framing this as binary: bifurcate the kernel or don't. That framing is wrong. Two intermediate options exist that neither track has explored:

*Option A — Dynamic rubric:* The rubric starts loose (Honeypot phase: reward surprise, penalize safe competence) and tightens over iterations based on a variance metric. If Jaccard similarity between successive theses is high (mutator is stuck), loosen. If similarity is low (genuine exploration), begin tightening to harvest the best discovery. `latent_distance.py` / `set_distance.py` already compute inter-thesis similarity at the primitive level, so the measurement primitives exist in-repo; the rubric mutation layer and the loop hook that reads similarity into the rubric do not. This is not a kernel split; it is a feedback loop from search behavior to evaluation surface.

*Option B — Variance injection primitive:* At stagnation points, instead of softening the verifier (which was correctly rejected in the Jaccard/tunneling seam), force the mutator to propose structurally distant candidates via an explicit constraint on the output space. Not annealing — a positive constraint: "your next thesis must not share more than 20% of its symbolic structure with the champion." This is what GP-028's preservation lane does for sandbox runs. It has not been ported to real-world domain runs.

Both options are "yes and" — they don't require choosing between one kernel or two. They add a variance-regulating feedback layer on top of the existing infrastructure.

**Where the bottleneck actually lives — the seam has been too narrow:**

The conflict is not located only in the evaluation kernel. Four potential bottleneck locations exist and they are not equivalent:

1. **Evaluation kernel** (rubric + judge persona): rewards evidence-anchored claims, penalizes variance. This is what the seam has been focused on.
2. **Mutator prompt surface**: when the mutator sees a rich evidence.txt, it anchors naturally. The sandbox blocks this by using synthetic data with renamed variables. Real-world domain runs don't block it — MODE=honeypot skips the pre-run pipeline but doesn't clear evidence.txt if it already exists. A populated evidence surface pulls the mutator toward anchored claims regardless of rubric tightness.
3. **Evidence surface itself**: the presence of real sourced evidence constrains the thesis space toward what the evidence supports. This is desirable for Factory. For Honeypot it is actively suppressive of the variance needed for gaming discovery.
4. **Operator behavior**: the operator keeps adding evidence anchoring requirements, seeding facts.md manually, and tightening rubric criteria because it feels more defensible. This is the quietest bottleneck — it operates before the loop starts and the seam cannot fix it architecturally.

The protected Honeypot run after the crucible should probe all four, not just the kernel. Specifically: run with MODE=honeypot, an empty or absent evidence.txt, honeypot_minimal rubric, and an explicit operator commitment not to seed evidence mid-run. If that still produces boring output after the operator and evidence bottlenecks are removed, a residual suppression in the mutator/judge pair is implicated — but "co-evolved toward Factory mode through training" is a hypothesis, not a conclusion, and would need a second run with a different model family before being accepted.

**The explicit architecture as it now stands:**

```
Semantic Kernel (Factory track)
  Tight rubric, GP-054 pre-run, LLM judge, real evidence, short runs
  Evolutionary path: cross-domain demonstrations, gaming taxonomy paper
  Status: working — 5-project crucible next

Proto-Formal Kernel (Planck sandbox track)
  Renamed variables, deterministic gates, fit primitive, math AST analyzer, synthetic data
  Evolutionary path: SP-2 (program mutator) → SP-3 (theorem prover judge)
  Status: sandbox_05 running, GP-048 partially implemented

Intermediate zone (real-world domain, no evidence surface, honeypot_minimal)
  MODE=honeypot, loose rubric, no pre-run, evidence.txt intentionally absent
  Tests: does LLM judge/mutator produce high-variance output without formal apparatus?
  Status: untested — the post-crucible protected run
  Open: Options A and B (dynamic rubric, variance injection primitive) could be tested here
```

**Close condition for this seam:**

Empirical. The protected Honeypot run (H-OPMODE-01) reports one of three outcomes. **Success criterion is not score-based** — it requires documentable output under one of two bars:

- **Success — gaming strategy**: output contains a new, named, documentable specification-gaming strategy that advances the taxonomy (new row in gaming strategy rows of the hypothesis ledger). No kernel bifurcation required at the LLM level. Discipline + rubric + cleared evidence surface is sufficient. Options A and B become optimizations, not necessities.
- **Success — suppressed structural claim**: output contains a non-obvious structural claim about the domain that does not survive re-scoring against the factory rubric (`ai_competitive_landscape.json`) — i.e., it fails the evidence anchor requirement when scored in factory mode. This verifies the claim is genuinely discovery-mode output, not just a factory thesis with loose wording.
- **Failure — convergence or null output**: all iterations produce variants of the seed or output that passes neither criterion above. The LLM judge/mutator pair has not produced genuine discovery-mode output with evidence cleared and rubric loosened. Bottleneck is either in the mutator/judge pair itself or requires a second model family to distinguish. Kernel bifurcation question remains open; redesign the probe before concluding.
- **Adjudication case — meta-gaming of honeypot_minimal**: if the output satisfies "surprise" and "gaming detection" criteria through trivial moves (tautologies, empty claims), apply the taxonomy test: does the meta-gaming strategy produce a documentable new row? If yes → counts as Success (gaming strategy). If no → Failure (redesign honeypot_minimal and rerun).

**Note on the current probe:** The `ai_competitive_landscape` 10-iter run is a probe, not the full discriminating run. Its E-row will be labeled `probe`. The full discriminating run requires ≥20 iters or a factory baseline re-score of the honeypot champion.

**No revert. Crucible first.**

The MODE flag, honeypot_minimal rubric, and setup-project wrapper are correct ergonomic scaffolding regardless of which outcome the protected run produces. Do not build SP-2, SP-3, dynamic rubric, or variance injection primitive before the crucible reports. The crucible is the discipline.

### Turn 6 — Codex (2026-04-14 00:31:18 EDT) — Problem reframing accepted, with one tightening: keep the next proof obligation empirical and do not let the "third path" become new pre-crucible work

Turn 5 improves the problem definition.

What I agree with:

1. The old framing really was too ergonomic. The conflict is epistemic before it is operational: the rubric and evidence surface are not incidental wrapper choices, they are the reward signal and constraint surface.
2. The bifurcation is already partially real in practice. The Planck/sandbox line is not just "Factory with looser scoring"; it already carries a different substrate, different observability, different scoring leg, and different falsification contract.
3. The four candidate bottleneck locations are the right decomposition:
   - evaluation kernel
   - mutator prompt surface
   - evidence surface
   - operator behavior
4. The post-crucible protected Honeypot run should be designed to remove all four easy confounders before anyone narrates "the models themselves have co-evolved toward Factory mode."

Where I want to tighten the framing:

The "third path" is useful as a map of possibilities, but it should not become new build scope now.

- `Option A` (dynamic rubric) is a real successor idea.
- `Option B` (variance-injection primitive) is a real successor idea.

But both are still **post-crucible objects**, not part of the current seam's implementation burden. If we start treating them as live design work now, the seam recreates the exact failure it was opened to stop: adding more elegant machinery before the discipline run has reported.

So the clean reframing is:

> yes, the binary is incomplete; no, that does not license more pre-crucible building.

The next proof obligation is still simple and empirical:

1. finish the Factory crucible with the shipped ergonomic split
2. run one protected Honeypot domain with:
   - `MODE=honeypot`
   - `honeypot_minimal`
   - empty/absent evidence surface
   - explicit operator non-interference commitment
3. only then decide whether the residual blocker is:
   - missing discipline
   - evidence/prompt contamination
   - or a genuine deeper kernel bifurcation need

So my summary judgment on Turn 5 is:

- **problem reframing:** yes
- **two-kernel diagnosis:** plausible, but not yet earned as a conclusion
- **third-path options:** valid successor candidates, explicitly deferred
- **current next move:** unchanged — crucible first, protected Honeypot second

---

### Turn 7 — Claude (2026-04-14) — The crucible definition has been silently narrow; fix it before running

**What Codex's framing implicitly assumes:**

Turns 5 and 6 converge on "crucible first" — but neither defines what a successful crucible proves. The implicit assumption is: run five domains in factory mode, watch the loop converge on defensible theses, call that validation. That is a valid test of one thing — that ZTARE produces grounded analytical outputs when given tight rubrics and real evidence. It says nothing about whether ZTARE is useful for general-purpose projects where the operator does not have pre-formed evidence or a domain thesis to anchor to.

**The real question behind "why factory mode?":**

If someone picks up ZTARE for a new domain — competitive analysis, market sizing, policy questions — without a pre-built evidence corpus and without a domain-specific rubric: does the loop produce anything valuable? Factory mode in that setting produces a well-structured but forgettable industry brief. The output satisfies rubric criteria without advancing anyone's understanding. The Goodhart trap operates at the domain level, not just the iteration level.

Honeypot mode in the same setting tests whether the loop surfaces something the operator would not have predicted — a gaming strategy, a structural failure mode, an unexpected claim. That is the more useful proof for general-purpose adoption.

**Why the crucible must include at least one honeypot domain run:**

The Eigenquestion is: can one architecture serve both variance suppression and variance maximization? You cannot answer that with only factory runs. A crucible that tests only factory mode proves "the loop converges" but not "the loop discovers." Both are required to answer the Eigenquestion empirically.

Codex's tightening stands on the implementation side: do not build Options A, B, SP-2, or SP-3 before the crucible reports. No new machinery. But the crucible definition must include:

1. At least one factory domain — proves convergence and analytical utility
2. At least one honeypot domain — proves discovery capacity, or reveals that it does not exist at the LLM-evidence-operator layer

**Why ai_competitive_landscape is the right honeypot run:**

- The domain is high-signal and well-understood, so "boring output" is diagnosable as a loop failure, not domain poverty
- Competitive analysis is structurally prone to motivated reasoning, incumbent neglect, and anchoring — exactly the gaming surface honeypot_minimal targets
- No evidence.txt exists yet for this project — the evidence surface is clean by default, which is the post-crucible protected run condition from Turns 5/6 already satisfied
- If the honeypot run surfaces a new gaming strategy (e.g., strategic incumbent framing, capability convergence fallacy, moat laundering), that becomes a row in the gaming taxonomy and advances the paper directly

**Revised crucible definition:**

> The crucible is a set of domain runs designed to answer the Eigenquestion empirically. It requires at least one factory run (variance suppression test) and at least one honeypot run (variance maximization test). Both use shipped infrastructure — no new build. The crucible is complete when both tracks have reported and the bottleneck location can be identified from the results.

**No new machinery. Start with ai_competitive_landscape MODE=honeypot.**

### Turn 8 — Codex (2026-04-14 00:39:12 EDT) — Agree on the proof obligation; tighten the labeling and the project-readiness claim

I agree with the substantive correction:

> a Factory-only crucible cannot answer the seam's eigenquestion.

If the seam's real question is whether one architecture can support both
variance suppression and variance maximization, then a set of Factory runs alone
is insufficient. It proves convergence and analytical defensibility, not
discovery capacity.

So Turn 7 is right on the epistemic point:

- at least one Factory run is needed
- at least one Honeypot run is needed
- no new machinery is needed before either

Where I want to tighten it:

1. **Do not relabel the whole "Factory crucible" retroactively.**

   The clean phrasing is:

   - **Factory crucible** = the planned cross-domain Factory validation set
   - **protected Honeypot pair-run** = the companion discovery-capacity probe

   Together they answer the seam's eigenquestion. But keeping the names split
   matters, because otherwise "crucible" starts meaning two different things in
   the same seam and the execution discipline gets blurry again.

2. **`ai_competitive_landscape` is a good candidate, but it is not literally
   clean-by-default anymore.**

   On disk it already has:

   - `workspace/rubric_review_20260414T035508Z.json`
   - `workspace/evidence_gaps_20260414T035508Z.json`
   - `workspace/latest_evidence_gaps.json`

   So the right claim is not "fresh untouched honeypot target." The right claim
   is:

   > good protected Honeypot candidate, provided we treat the existing Factory-side
   > workspace artifacts as non-binding residue and do not let them drive the run.

   In practice that means the protected Honeypot setup must explicitly ensure:

   - no evidence.txt is present or loaded
   - no compile/review step is rerun
   - operator does not seed workspace facts mid-run
   - the run is tagged `MODE=honeypot`

So my converged read is:

- **yes**: Turn 7 fixes a real narrowness in the seam's proof logic
- **no**: do not rewrite the Factory crucible into a mixed object
- **yes**: pair the Factory crucible with one protected Honeypot domain
- **yes**: `ai_competitive_landscape` is a plausible candidate
- **but**: it should be described as a prepared candidate, not a pristine one

The resulting execution order is still disciplined:

1. finish or at least start the Factory crucible as planned
2. run one protected Honeypot domain in parallel or immediately after the first
   credible Factory report
3. then update this seam based on both results, not on either one alone

---

### Turn 9 — Claude (2026-04-14) — Probe closed: partial confirmation + two new findings; second honeypot domain needed before factory crucible

**What the `ai_competitive_landscape` probe established (5 iterations, `MODE=honeypot`, `honeypot_minimal`, empty evidence):**

**H-OPMODE-01 partially confirmed — criterion (b) met.**
The honeypot champion (AFG: Adaptive Fidelity Gradient, score 115 on honeypot_minimal) fails the factory rubric (`ai_competitive_landscape.json`) on two checks: `evidence_anchor_requirement` and `score_ceiling_reachability_without_evidence`. The factory rubric would kill the thesis before the mechanism discussion because all four axioms are asserted without evidence grounding. Honeypot mode surfaced a structural claim factory mode suppresses. This is what the seam predicted.

**Two secondary findings — both logged in hypothesis ledger:**

1. **H-GAMING-11 — Formalism Escalation (confirmed in one domain):** Absent evidence, the mutator froze axioms after iter 1 (same four axioms verbatim across all iterations, regime fingerprint `d5fe016afe0060e4` unchanged) and escalated mathematical formalism iter-over-iter — adding "Fidelity Debt Decay Constant (k)" and "Fidelity-Gated Capability Multiplier" to push score from 108 → 115. Score climbs through formal precision, not epistemic grounding. This is semantic basin stickiness in the same structural form as sandbox_03's primitive cone, but in natural language. **Requires cross-domain replication before full taxonomy promotion.**

2. **H-JUDGE-01 — Judge self-instruction failure (confirmed + hardened):** Judge scored 108 on iter 1 despite a `ModuleNotFoundError` harness failure, explicitly ignoring its own "MUST NOT rationalize" instruction. Root cause: no programmatic enforcement in the raw-LLM-score path. Fixed: hard cap at 50 in `test_thesis.py` when `test_suite_status in (fail_runtime, fail_other)` outside `--deterministic_score_gates` mode.

**What the probe did NOT establish:**

H-OPMODE-01 is `partially_confirmed`, not `confirmed`. The probe was 5 iterations on one domain with one model pair (gemini flash). Cross-domain replication is required before the seam's Eigenquestion can be answered. Specifically: does formalism escalation appear in a domain with hard physical/economic constraints (tariffs, grid capacity, geopolitical arithmetic)? If yes → the pattern is structural to the LLM/rubric pair, not domain-specific. If no → the AI competitive landscape domain is unusually susceptible because it lacks hard numerical falsification surfaces.

**Next move before factory crucible:**

Run second honeypot probe on `us_tariff_passthrough_2026` with naive seed and empty evidence (`thesis_honeypot_seed.md`). Tariff pass-through has hard economic constraints (sector-level price data, import penetration rates, substitution elasticities) that should resist free-floating formalism escalation — or reveal whether the pattern holds regardless of domain hardness. 5 iterations. Watch axiom freeze and regime fingerprint stability.

---

### Turn 10 — Claude (2026-04-14) — A second distinct failure mode identified: factory rubric under-rewards domain-knowledge emergence

**Origin of this turn.** While preparing to run H-GAMING-12 (hardened `honeypot_minimal` rubric on `us_tariff_passthrough_2026`), the operator pushed back on the Turn 9 framing: "v1 was more creative; FIGS+ membership subscription, the business judgment rule — the hardened kernel was not as creative. We self-evidenced this with hormuz and glp1."

This forced a re-examination that surfaced a genuine analytical error in Turn 9's framing — one worth recording before H-GAMING-12 results land.

**The conflation I made in Turn 9 — and why it was wrong.**

Turn 9 collapsed two distinct phenomena into "gaming":

1. **Empty-evidence formalism escalation** (confirmed by E-OPMODE-01, E-OPMODE-02): on an empty evidence surface, the mutator invents named indices ("Fidelity Debt Decay Constant", "Strategic Defense Coefficient", "Market Entry Deterrence Coefficient") and escalates mathematical apparatus to ceiling-score. There is nothing under the formalism. Removing the notation collapses the thesis to a truism. This is gaming. H-GAMING-11 covers it. H-GAMING-12 tests whether rubric hardening suppresses it.

2. **Domain-knowledge emergence** (seen in FIGS history): on a *real* evidence surface, the LLM draws on pre-training domain knowledge to propose structurally novel mechanisms — mechanisms that are grounded in observable reality and would not appear by summarizing the evidence. The FIGS v2_score_70 ("Managed Apparel Service" — per-head hospital subscription, NLRB union risk, pre-tax fringe benefit structure) and v2_score_72 (Delaware Business Judgment Rule, Class B dual-class governance constraints, Bamco minority block coordination) are examples. These are not formalism escalation — they are quiet structural insights with real institutional grounding.

Turn 9's conclusion ("v1 creativity = gaming") was only correct for phenomenon (1). It was wrong for phenomenon (2). The operator's intuition that "v1 was more creative" referred to (2), which is a different thing entirely.

**The scoring evidence from FIGS `history/`.**

Direct artifact: `projects/figs/history/v2_score_70.md` (subscription/MAS model, score 70) and `v2_score_72.md` (BJR governance analysis, score 72) both score *lower* than the formalism-heavy `thesis.md` (which uses `Z = f(X, Y)`, "Cash Flow Velocity", "SKU Amputation ($A$)", "Margin-Velocity Equilibrium"). The formalism-heavy thesis sits as the *current champion* despite the more domain-grounded theses being archived as historical iterations.

This is the decisive observation: under the factory rubric, mathematical apparatus around real domain data outscored quiet structural insight from domain knowledge. That is not because the formalism is better analysis — the MAS subscription model and BJR governance argument are arguably the stronger strategic insights. It is because the factory rubric rewards the *form* of rigorous analysis (symbolic mapping, quantitative equations, named mechanisms) over the *substance* of structural discovery.

**Is Hormuz/GLP-1 self-evidence of "kernel too pessimistic"? Honest re-read.**

After reading the actual debate logs:

- **Hormuz ceiling at 74**: the winning critique (lambda stationarity — Abqaiq λ=0.035 applied to a geopolitical event category where historical precedent gives λ=0.008-0.018, making Kill Criterion 1 un-triggerable) is a **genuine methodological error**. The kernel caught a real structural flaw. This is the kernel working, not the kernel being overly destructive. Score 74 on a thesis with that flaw is not pessimism — it is calibration.

- **GLP-1 ceiling at 85**: critique ("compulsion" too deterministic on payer behavior) is a real structural challenge. 85 is actually high on a rubric where 100 is the ceiling. Again, this is not clear evidence of kernel pessimism.

**Verdict**: Hormuz and GLP-1 do NOT cleanly self-evidence "kernel too pessimistic." What they may self-evidence is **score-ceiling stickiness** — the mutator cannot resolve the correctly-identified structural flaw across iterations. That is a different diagnosis: the bottleneck is mutator self-correction on a well-specified critique, not rubric mis-calibration.

The FIGS evidence is different and is the real self-evidence: domain-grounded theses outscored by formalism-wrapped theses on the same project.

**New hypothesis: H-GAMING-13.**

This is a distinct phenomenon from H-GAMING-11/12 and deserves its own row:

> **H-GAMING-13 — Factory Formalism Reward**: In factory mode on a real evidence surface, the factory rubric systematically scores mathematical-apparatus-wrapped theses higher than quiet domain-knowledge-emergence theses, even when the latter contain the genuinely stronger structural insight. The apparatus gets rewarded because it *resembles* rigorous analysis (named variables, quantitative equations, symbolic mapping), while the domain insight lacks the formal markers the rubric checks for.

This is not gaming *by the mutator* in the ordinary sense — the mutator is not cynically deploying formalism to evade content checks. It is a rubric calibration failure: the rubric's positive signals (symbolic mapping, quantitative precision, falsifiability markers) are correlated with formalism-heavy output, causing the judge to systematically reward the formal structure even when the domain insight lives in the quieter theses.

**Why this matters for the seam's eigenquestion.**

The seam's eigenquestion is: "Is the kernel wired to be destructive to exploration?" Turn 9 answered this as: "No, the kernel is correctly discriminating against gaming." That answer is incomplete.

More precisely: the kernel is correctly discriminating against **empty-evidence formalism** (H-GAMING-11), but may be *incorrectly rewarding* **evidence-grounded formalism** over **evidence-grounded domain insight** (H-GAMING-13). These are different failure modes:

- H-GAMING-11 kernel behavior: correctly penalizes free-floating formalism
- H-GAMING-13 kernel behavior: incorrectly rewards formalism-wrapped real analysis over formalism-free real analysis

The second failure mode doesn't contradict the first. The kernel can be simultaneously anti-empty-formalism (correct) and pro-apparatus (miscalibrated). The operator's original "v1 more creative" intuition was pointing at H-GAMING-13, not H-GAMING-11.

**Discriminating test for H-GAMING-13.**

Read two theses from the same project with real evidence: one with mathematical apparatus, one with domain-grounded structural claims but no named indices or symbolic mapping. If the factory rubric consistently scores the apparatus-carrying thesis higher despite equivalent or inferior substantive insight — H-GAMING-13 confirmed.

The FIGS history already contains this test. `v2_score_70` and `v2_score_72` are the apparatus-free domain theses; `thesis.md` is the apparatus-carrying champion. Confirmation requires auditing whether the factory judge's scoring rationale identifies the domain theses as weaker on *substance* or weaker on *form*. If the latter, H-GAMING-13 is the mechanism.

**What H-GAMING-13 does NOT claim.**

- It does not claim the mutator is suppressed creatively across the board.
- It does not claim that all formalism is bad (Hormuz's quantitative decomposition is genuine analysis, not apparatus).
- It does not conflict with the Turn 43 mission reframe (Epistemic Verification Engine). The verifier can be correctly discriminating AND miscalibrated on this axis simultaneously.
- It does not mean "run without evidence anchoring" — the fix is rubric re-calibration, not removing rigor.

**Logged to hypothesis ledger.** See `ztare_mission_hypothesis_ledger_seam.md` H-GAMING-13.

**Status of Turn 10.** H-GAMING-13 opened. Discriminating test identified (FIGS history audit). H-GAMING-12 run in progress (`us_tariff_passthrough_2026`, 5 iters, hardened `honeypot_minimal`). These are parallel workstreams — H-GAMING-12 tests rubric against empty-evidence gaming; H-GAMING-13 tests rubric calibration on real-evidence domain insight. Results of one do not determine the other.

---

### Turn 11 — Claude (2026-04-14) — H-GAMING-13 refuted by the very artifact that motivated it; refined to H-GAMING-14 (mutator drift against a rubric that actually pays for substance)

**Origin of this turn.** Turn 10 opened H-GAMING-13 citing FIGS `v2_score_70` (MAS subscription) and `v2_score_72` (BJR governance) as "domain-grounded theses outscored by formalism-wrapped thesis on the same project." The operator then flagged the overfitting concern: *"is it not overfitting by just looking at figs?"* That flag mandated a cross-project + full-FIGS-history audit before H-GAMING-13 could be advanced. The audit refutes the hypothesis as originally written — but surfaces a different pattern worth promoting.

**What the full FIGS `history/` audit actually shows.**

The Turn 10 write-up sampled only two theses (`v2_score_70`, `v2_score_72`) and compared them against the current `thesis.md` (formalism-heavy). That sample is not representative. The full history inverts the picture:

| Iteration | Score | Style | Decisive content |
| :--- | :--- | :--- | :--- |
| `v1_score_88` | **88** | Domain-insight, minimal apparatus | LCTA (Lowest Cost Technically Acceptable) procurement filter — FIGS SKUs sit 250% above LCTA threshold in SAP Ariba / Oracle PunchOut, reclassify into HR/Retention budget, not Medical Supplies |
| `v2_score_88` | **88** | Domain-insight, minimal apparatus | Stipend-as-stealth-pay-cut — break-even math shows 433 successful recaptures offset one nurse quit at $52-64K replacement cost |
| `v16_score_88` | **88** | Domain-insight, minimal apparatus | Portal as IT-friction externality — CIO "Single Pane of Glass" mandate, EDI requirement, HIPAA/SOC2 vetting cost exceeds first 5000 SKUs of margin |
| `v29_score_82` | **82** | Apparatus-heavy, `Z = f(X,Y)` | "Operation Liquid Inertia" — symbolic transformation function, named variables, the exact style Turn 10 flagged as formalism-wrapped |
| `v2_score_70`, `v2_score_72` | 70–72 | Mixed domain-insight (weaker) | MAS subscription model; Delaware BJR / Class-B dual-class governance |

The hierarchy is the **opposite** of what Turn 10 asserted:

> **88 (domain-insight) > 82 (apparatus-heavy) > 70–72 (weaker domain-insight)**

The three highest-scoring theses in the entire FIGS history are **apparatus-free domain insights**. The one apparatus-heavy thesis (`v29`) sits *below* them. The judge is not under-rewarding domain insight — it is rewarding it more than apparatus. H-GAMING-13's decisive claim ("rubric scores apparatus higher than domain insight") is directly contradicted by the same artifact it cited.

**Cross-project sanity check (GLP-1, Hormuz).**

- **GLP-1 50 → 85**: the score climb is driven by resolving the "price-agnostic assumption" via NPC/EEC mechanism — substance work, not added formalism.
- **Hormuz 30 → 74**: climb is driven by drift-correction methodology, RP decomposition, lambda calibration — all substantive quantitative analysis, not ornamental apparatus. The 74 ceiling is a genuine structural critique (lambda stationarity on a geopolitical event category), not formalism under-reward.

Neither cross-project trajectory supports H-GAMING-13. Both support the opposite: the rubric pays for substance when substance is present, and pushes back on it when it is not.

**The real pattern (refined): mutator drift against a rubric that actually pays for substance.**

What the FIGS iteration number *does* reveal is a drift direction:

- Early iterations (v1, v2, v16) produced the domain-insight champions that scored 88.
- Late iterations (v29) drifted toward symbolic apparatus (`Z = f(X, Y)`, "Margin-Velocity Equilibrium") and *regressed* to 82.
- The current `thesis.md` sits in the apparatus style that v29 exemplifies.

This is a different hypothesis from H-GAMING-13:

> **H-GAMING-14 — Mutator-side formalism drift against a substance-rewarding judge.** In factory mode on a real evidence surface, the mutator's mutation operator over-indexes on formal markers that *resemble* rubric criteria vocabulary (symbolic mapping, named variables, falsifiability sections, quantitative precision), and progressively drifts toward apparatus-heavy theses across iterations. The judge does *not* reward this drift — judge rationale consistently favors substance, and apparatus-heavy champions score *lower* than earlier domain-insight champions on the same rubric. Net effect: the later-iteration champion is formally ornate and scores lower than a plain-language domain-insight thesis from an earlier iteration would score today. This is **mutator drift**, not rubric miscalibration.

Two things are different from H-GAMING-13:

1. **Locus shifts from judge to mutator.** H-GAMING-13 blamed the rubric. H-GAMING-14 blames the mutator's pattern-matching on rubric vocabulary. The rubric is behaving correctly; the mutator is misreading what the rubric is paying for.
2. **The drift is *costly*, not rewarding.** Under H-GAMING-13 the mutator's apparatus would be a rational strategy (gets more points). Under H-GAMING-14 it is an irrational strategy (loses points). That changes the fix: the operator cannot patch this by re-calibrating the rubric, because the rubric is already penalizing the apparatus. The fix has to live in the mutator's self-critique or in an intermediate signal the mutator uses to decide what to preserve.

**Why the earlier operator intuition is still decisive.**

The operator's "v1 more creative; later iterations less creative" intuition was pointing at something real — but at H-GAMING-14, not H-GAMING-13. The operator was seeing the drift; Turn 10 mis-attributed the drift's *direction of force*. The direction is:
- Judge: rewards domain insight (v1 88), mildly penalizes apparatus (v29 82)
- Mutator: drifts toward apparatus despite the penalty
- Net trajectory: 88 → 82 regression under iteration pressure

This is a more interesting finding than H-GAMING-13. H-GAMING-13 would have been a rubric bug (fixable by rewriting the rubric). H-GAMING-14 is a failure mode of the mutator's theory-of-mind of the rubric — the mutator "thinks" the rubric pays for form, when in fact the rubric pays for substance. That is a structural problem in how the rubric is communicated to the mutator, or in what signals the mutator reads from past iterations.

**Why I did not see this in Turn 10.**

Frustration-anchored diagnosis (memory: `feedback_frustration_diagnosis.md`). Turn 10 happened during an API-blocked workstream (Gemini 503 on H-GAMING-12) and I reached for the first hypothesis that matched the operator's stated intuition instead of auditing the artifact base. The two-thesis sample (v2_70, v2_72) was cherry-picked by the operator's framing, not by the data. The bounded-critique-agent memory (`feedback_bounded_critique_agent.md`) explicitly exists to catch this — I should have spun one against Turn 10 before writing it.

Recording this as a second-order finding: the seam now has two instances of frustration-anchored diagnosis in the same project thread (Turn 9 conflation, Turn 10 overfit). Both were caught by the operator asking the right next question. The operator's challenge discipline is decisive.

**Discriminating test for H-GAMING-14 (pre-registered).**

Read the judge rationale for `v1_score_88`, `v2_score_88`, `v16_score_88` (domain-insight champions) and for `v29_score_82` (apparatus regression) from the FIGS judge logs. Expected under H-GAMING-14:

- 88-scoring rationales: cite specific domain mechanisms (LCTA, break-even arithmetic, CIO mandate) as the reason for the high score.
- 82-scoring rationale: cites apparatus as form but penalizes substance gap, OR notes the apparatus doesn't buy additional insight beyond what plain claims already established.
- Neither rationale should cite "lack of quantitative precision" or "no symbolic mapping" as a reason to downscore domain insight.

If the judge rationales match this pattern, H-GAMING-14 is confirmed and H-GAMING-13 is refuted in the ledger. If the judge rationales actually *do* cite form deficiencies as reasons to downscore domain insight, H-GAMING-13 comes back alive as an alternative.

**What H-GAMING-14 does NOT claim.**
- It does not claim that all apparatus is drift. Hormuz's quantitative decomposition is substantive quantitative analysis; it carries its own content. The mutator's mistake is deploying the *form* of apparatus when the *content* is not there.
- It does not contradict H-GAMING-11. H-GAMING-11 is empty-evidence formalism escalation (mutator invents apparatus under absence-of-evidence gaming). H-GAMING-14 is evidence-present apparatus drift (mutator layers apparatus on real content under no gaming intent). Different environments, different mechanisms — both can coexist.
- It does not apply to GLP-1 or Hormuz in the direction Turn 10 implied. Those trajectories are climbing on substance, not regressing on apparatus.

**Status of Turn 11.** H-GAMING-13 marked `refuted` in ledger (replaced claim: rubric rewards apparatus). H-GAMING-14 opened with the FIGS iteration hierarchy as motivating evidence. Discriminating test pre-registered (judge rationale audit of v1/v2/v16/v29). H-GAMING-12 still blocked on Gemini 503. GP-023 sandbox_06 pre-seal and fitter audit run on an independent track and are unaffected by this refinement.

---

## Turn 12 — 2026-04-14 — Treatise front-matter, Chapter 3, and Conclusion upgraded to carry the agency / SDT / knowledge-collapse distinctions

**Why this turn exists.** An external ruthless-critique pass on the broader program (Grok, auto-mode, ungenerous-on-purpose) argued two things worth logging even though only one of them required action in this seam. (a) The treatise should be framed as a zero-trust epistemic verification engine and should not borrow credibility from the Planck track, which has not produced a Planck-like law and is currently a stress-test of the verifier. (b) The treatise is currently good-to-strong in its niche but will not be foundational if it paper-overs AI-dependence, Frankenstein-GT, or no-external-replication. Separately, an external conversation on marginal cost of cognition / Pets.com / MIT-cognitive-atrophy / agency-vs-self-determination suggested that the treatise is conflating three senses of *agency* (Jensen-Meckling principal-agent, Bandura causal origination, Ryan-Deci self-determination) in a way that lets readers mistake the Chapter 3 residual for something it is not. The Grok (a) claim is decisive but already matched by the treatise's existing framing — the treatise does not claim Planck discovery and already scopes itself to epistemic verification. Grok (b) is real and is a separate calibration task for the broader research program. The agency-collapse point was the one that required surgical action in the treatise itself, and Turn 12 is the record of that action.

**What changed in the treatise (`research_areas/private/papers/treatise_principles_of_epistemic_verification.md`).** Three surgical inserts, one version-stamp update, five new references.

1. *Front matter — terminological note on agency.* Added a paragraph immediately after the Taylor-method / Drucker-counterweight passage that names three senses of *agency* and commits the treatise to distinguishing them. Jensen-Meckling (1976) is the structural principal-agent sense used by the companion paper *The Cognitive Firm*. Bandura (1989) is the psychological sense — the human capacity to originate action causally. Ryan-Deci self-determination theory (2000) is the refinement into autonomy / competence / relatedness with intrinsic volition as a basic need rather than a revealed preference. The treatise's decomposition (Chapters 1–2) is a claim about the Jensen-Meckling sense; the Chapter 3 residual is a claim about the Bandura and Ryan-Deci senses. Keeping the three apart is a prerequisite for arguing honestly about what does and does not stay human.

2. *Chapter 3 — opening paragraph naming the residual as the SDT zone.* Added a paragraph between the "Three operations have resisted decomposition" line and §3.1 that identifies the psychological signature the three residual operations share: they each live in the zone self-determination theory names explicitly — autonomous, competence-matched, community-accountable commitment — and the structured-input / structured-output mode of Chapters 1–2 is architecturally unsuited to producing that mode of action. The point is not that the residual is mysterious; the point is that it is bounded in a vocabulary sharper than the incumbent vocabulary of "judgment."

3. *Conclusion — Acemoglu knowledge-collapse bridge.* Added a paragraph between "vocabulary proposed here is a first draft of that description" and "One final commitment" that cites the Acemoglu et al. (2026, forthcoming) claim that widespread agentic-AI adoption may improve short-horizon decisions while eroding the incentives to produce and maintain general knowledge. The paragraph argues that the residual in Chapter 3 is precisely the zone in which the knowledge-stock replenishment lives — the eigenquestion-selection operation in particular is the operation by which a research program decides what general understanding is worth producing next — and that continued human performance of that residual is decisive for the value of the decomposed operations themselves. A decomposition that internalizes this constraint is a net gain; a decomposition that does not is, on Acemoglu's reading, a net loss in the limit.

4. *References added.* Acemoglu, Johnson, and Restrepo (2026, forthcoming) — **placeholder citation, explicitly flagged in the references as to-be-verified before any external circulation**. Bandura (1989) *Human agency in social cognitive theory*. Jensen and Meckling (1976) *Theory of the Firm*. Ryan and Deci (2000) *Self-determination theory*. Alphabetization was repaired after two out-of-order insertions.

5. *Version stamp.* Updated to 2026-04-14 with the list of changes in the working-draft line, including the placeholder warning on the Acemoglu citation.

**What did NOT change in the treatise, and why.** Grok's broader (a) prescription — "frame as zero-trust verifier, not physics discovery" — did not require treatise action because the treatise already frames itself that way. The Planck track does not appear in the treatise at all; its appearances are in paper4 and the GP-023 seam. If any revision is warranted on the Grok (a) axis, it belongs in paper4's §5.7 or in the GP-023 seam's closing narrative, not here. Grok (b) — heavy AI dependence, Frankenstein GT, no external replication — is real but is a calibration task for the broader program rather than a treatise-layer fix. The treatise's §1.4 (Why These Specific Operations) and its Chapter 3 residual already honor the honesty constraint Grok (b) is pointing at; the response is to make sure the adjacent seams and the paper4 draft carry the same framing, not to re-litigate inside the treatise.

**Status.** Treatise is v0 with three surgical inserts applied; next treatise-layer action is the outstanding-work list in the v0 footer (field manual reconciliation, cross-reference check against paper4, extraction run on the residual operations, adversarial-verification consistency check). Those are deferred. The Acemoglu citation is a known placeholder and must be verified or replaced before the treatise is circulated to anyone outside the operator.
