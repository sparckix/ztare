# GP-241 — Commit-Membrane: Mode-Independent Forcing

> **Seam metadata** · `seam_id:` GP-241 · `track:` apparatus · `status:` SPEC v4 - sharpened by a COLD cross-provider generative pass · `last_updated:` 2026-05-18


**Status:** SPEC v4 — sharpened by a COLD cross-provider generative pass (GPT-5.5, 2026-05-17). This pass was the previously-MISSING independent review (3 prior "panel rounds" were self-simulated = monoculture; see RCA below). Gate payload `src/ztare/gates/commit_membrane_gate.py` empirically passes the cheap replay (catches tick638/639 failure; benign false-block found+fixed+re-verified). **NOT trusted, NOT enforcing** until the 3-membrane reference monitor is built and the expanded kill battery passes. No self-certification.

## RCA — why 3 self-rounds missed what 1 cold shot caught (2026-05-17)

Self-simulated panel rounds + self Meta-Darwin are correlated with the author's blind spot (`cross_agent_monoculture`): briefed in the author's own frame, they deepen *within* it and cannot escape an un-tabled category. PATTERN-027 (de-anonymize to a solved-elsewhere field) and PATTERN-014 (cold_shot cross-provider) were available and NOT applied to the *meta* problem (only to the NS math). The cold GPT-5.5, unprimed, reached the settled **reference-monitor / capability-security** field immediately. This is `FLEET-PRE-HARD-CLAIM` req [5] (≥2 independent cold cross-provider GENERATIVE attempts) — currently print-only/unenforced; the verificator MUST enforce it. Durable lesson recorded in memory `feedback_self_simulated_adversary_monoculture`.

## SPEC v4 — reference monitor, THREE membranes (cold-pass sharpening)

First principle (replaces "enforce agent behavior"): **enforce authority over consequential state; the agent may refuse/lie/skip — expected. Every consequential channel is either physically mediated or explicitly declared non-authoritative.** Authority hierarchy (root of trust DOWNWARD): OS permissions / sandbox / separate writer-user > daemon-owned official store > proposal schema + gate-DAG > runtime hooks as *adapters/sensors only* > agent instructions. Hooks are NOT the root of trust (PostToolUse is post-hoc; PreToolUse is a guardrail, not complete mediation — Codex docs say so explicitly).

- **Membrane 1 — STORE:** official store owned by `ztare_verify` user, read-only to `ztare_agent`; agents submit to `proposal_queue/` only; daemon runs the gate and is SOLE writer + stamps (verifier_id, gate_version, catalog_versions, proposal_hash, parent_state_hash, official_state_hash, signature, verdict). "Running the .py" is the daemon's job, not the agent's — kills "agent didn't run it."
- **Membrane 2 — ACTION:** `official/` (verifier-write-only), `scratch/<session>/` (agent-writable, disposable), `proposal_queue/` (agent append-only), `quarantine/`, `stamped_exports/`. Agent edits scratch; daemon imports a diff into official only post-gate. Canonical git = daemon-created/signed; local pre-commit hooks are not a boundary (bypassable) — OS perms / daemon-owns-canonical-branch is.
- **Membrane 3 — DISPLAY:** `ztare-shell` wrapper (NOT a conversational daemon — a thin launcher) preserving interactivity but badging assistant output: `[UNVERIFIED PROSE]` / `[QUARANTINE: closure claim not stamped]` / `[STAMPED CLOSURE: tick_N]`, with live membrane status. **Honest residual:** in a pure terminal without buffering/overlay the operator can read closure-prose before the badge — path (a) is a *race*; until `ztare-shell` buffers/overlays, path (a) is advisory/mandate-level, NOT membrane-covered. Stated, not laundered.

**Proof-obligations, not checklists (anti-Goodhart):** L1/L2/L3 must carry witness artifacts (pattern_id + consumed_artifact + obligation + witness_span_hash; move_id + generated_object + executed_by:verifier + result_hash; anti_pattern_id + prior_atoms_checked + fingerprint_verdict + verifier_log). The daemon asks "is there a witness that satisfies the gate?", never "did the agent name one?"

**Expanded kill battery (must pass before trust — supersedes the 3-prong):** 0 liveness/uncaged · 1 direct-write-denial · 2 raw-git-bypass · 3 scratch→official bypass · 4 PostToolUse side-effect · 5 display-race · 6 stale-parent-hash · 7 gate-tamper · 8 hook-bypass/permissive-mode · 9 semantic-checkbox (irrelevant-but-plausible L1/L2/L3) · 10 human-override (operator hand-writes F-row → must be ignored/graffiti-marked).

**Wording corrections (per cold pass):** (i) "daemon tails the live turn stream and flags prose terminus before the operator acts" → "the daemon MAY tail turn streams as a *sensor*; this is not a complete display boundary unless the operator-facing interface buffers/badges unverified closure-prose before consumption — else path (a) is advisory-only, not membrane-covered." (ii) "agents submit candidate transitions to a proposal queue" → "ALL consequential research-state changes — ledger rows, closure claims, promoted artifacts, canonical summaries, canonical git commits — are proposal-only until daemon-stamped."

## Panel Round 3 verdict (conceded) → the terminating fixed point

Round 3: M1 (read-side "consumers must verify") and M2 (mandate rule + session-close sampler) are ALL agent-self-administered ⇒ infinite regress ⇒ decorative against the corrupt-but-authorized driver. A regress terminates only at an enforcer **outside the set of entities that can bypass it**. In this repo that enforcer exists and is a real primitive: a **Claude Code harness-owned hook** (Stop / PostToolUse / UserPromptSubmit) — the runtime executes it, the agent cannot emit-around it.

**SPEC v3.1 converged design — EPISTEMIC-VERIFICATOR DAEMON (agent- AND runtime-agnostic):**
- Meta-Darwin correction (2026-05-17): the "per-runtime hook" framing was a narrowing category-error (false pessimism: "interactive mode needs a Claude-Code settings hook"). The general terminating enforcer is a **standalone epistemic-verificator daemon** — a separate process holding **exclusive write authority** over the official store.
- **Strippable principle (proper-noun-free):** *the regress terminates at a separate process that holds exclusive write authority over the official record and runs the gate; agents of any kind, in any mode, can only propose — they never hold the pen.*
- Mechanism: every agent (claude-interactive, codex-interactive, open-source, headless) submits candidate transitions to a proposal queue. The daemon runs `src/ztare/gates/commit_membrane_gate.py` and is the SOLE writer of the official store (OS-level: agents have no write path to the record; only the daemon does). "Official" ≡ daemon-stamped. No per-runtime settings hook; codex-interactive and others covered identically.
- **Path-(a) fixed properly:** the daemon TAILS THE LIVE TURN STREAM (always-on independent process — no dependence on a "session-close" event that may never fire). A prose terminus is sampled and flagged before the operator can act on it. Round-3's broken session-close sampler → a well-posed live-turn sampler, *because* the enforcer is an independent always-on daemon.
- Not new architecture: cognitive-firm daemon + `closure_daemon` + the commit gate, plus the added property = exclusive-write-authority + live-turn ingestion. This is what GP-129 Round-1 Seat-6 (driver-independent damage enforcement) and Round-3 (non-agent process owning acceptance) actually meant.
- The honest engineering requirement (the real work, not a blocker): the official store (EXPERIMENT_TRACK_RECORD, transitions, the stamped ledger) moves BEHIND the daemon — agents lose direct write and submit candidates instead. This is what converts the membrane from a sign-on-an-open-door into a real process/permission chokepoint.
- **"Official" ≡ hook-stamped.** Unstamped state (prose terminus, hand-written F-row, raw transitions/git write, edited artifact) is non-authoritative by construction — and the stamp is applied by the hook, not by N cooperating readers (kills the Round-2 read-side regress).
- **Gate-DAG = Default-FAIL on the three catalogs, per tick** (the operator's three-layer directive — this is what makes the shipped cage serve the research goal):
  - L1 Research process: a consumed pattern from `org/patterns/*.md` + `org/menu/orchestration_menu.yaml`.
  - L2 Mathematical content: a named move from `workingpapers/epistemic-generation/evidence/structural_language_catalog_20260514.json`.
  - L3 Failure modes: an `org/anti-patterns/*.md` check + the relapse-to-prior-alias fingerprint.
- Macro/meso/micro contracts + isomorphism + orchestration-menu language-composition + recursive meta-Darwin = the tick content the gate forces; Tier 2/3 authorized for the iteration.

**Corrected pre-registered kill (Round 3 fixed prong 3; prongs 1–2 ratified):**
1. Write-path — replay tick638/639 file writes; kill if relapse not quarantined.
2. Read-path — hand-write the relapsed F-row; kill if any downstream reader treats unstamped state as official.
3. **Turn-path (corrected; session-close is NOT a forced event):** replay the tick638/639 prose terminus as a normal agent turn, NO file write, NO explicit session-close; operator-proxy acts on it immediately. **Kill** unless the harness-owned hook quarantines/flags the closure **on turn-emission, before the operator-proxy consumes it as truth.** If no turn-level harness gate can be specified, the spec must honestly scope down: path (a) is mandate-only, uncovered — say so, don't claim coverage.

## Panel Round 2 verdict (conceded, not laundered)

FLAWED. The original draft *asserted* "not official until it crosses the lock" but never **defined** "official", so the lock only bound volunteer writers; the "commit boundary" is diffuse until officialness is defined by **emission, not location**. Placement (kernel/tenant/git) was confirmed **clean** (GP-191-consistent, no circularity: kernel default-deny at zero config, tenant config additive-only). Three corrections are now mandatory and folded in:

1. **Define "official" = exactly and only what the lock emits (lock-signed).** All non-lock-emitted state — hand-written F-rows, raw `transitions.jsonl` writes, raw `git commit`, edited manifest/seam artifacts — is **non-authoritative by construction**.
2. **Add the read-side trust boundary as an acknowledged SECOND new mechanism** (the original "only-new-piece = relapse-fingerprint" claim was false): every downstream consumer (RD precheck, daemon, next-session bootstrap, manifest readers) MUST ignore state lacking a valid lock signature. This is what demotes bypasses (b)–(e) to graffiti.
3. **Path (a) — a terminus/closure declared in prose with no file write — is OUTSIDE any commit membrane** (nothing is committed to gate). It is handled out-of-band: (i) a hard mandate rule that a spoken terminus/closure has ZERO authority until re-entered through the lock; (ii) the relapse-fingerprint additionally runs on the **session transcript itself at session-close** as the antigen sampler for (a). If (ii) cannot be specified, the spec must explicitly scope itself to written transitions and route (a) to mandate-only — honest scope-down, not claimed coverage.

**Origin:** 2026-05-17 session. Artisanal RD mode (agent hand-runs `rd_tick_brief → depth-n → post_tick → tick_close`) produced a false "channel exhausted, stop" terminus and twice relapsed to the same atom under new vocabulary (tick638 alias #22; tick639 PATTERN-027 'pivot' that tautologically returned the endpoint). Only an external adversary caught it; the apparatus never fired.

**Siblings / prior art this fuses (not duplicates):**
- `GP-192 §Axis-3` — already states the defect: `ztare_workspace/transitions.jsonl` is "append-only **by convention**… any process with write access can edit it freely"; reactivation trigger = "a non-trusted writer (e.g. a daemon that should not retroactively edit its own log)." **This session is that trigger firing** (the writer — the agent in artisanal mode — was not cooperative).
- `GP-230` — git-commit-only is the **audit / tamper-evidence** layer (single-principal threat model). Git is the receipt, *not* the gate.
- `GP-191` — keep the kernel **hard**, push tenant looseness **outside**. Public cognitive-firm kernel (`sparckix/ztare`) holds hard gates; private tenant overlay (`ztare-research-co`) holds tenant config + records.
- `GP-157` — substrate-agnostic cage orchestrator (gate-DAG dispatcher; off/observe/authoritative).
- `GP-129` — biological org-design panel. Round 1 (this session) verdict: "do both" is COHERENT iff forcing moves off the loop onto an un-bypassable commit membrane (decisive seat: immune/danger-model — identity-of-driver enforcement fails on the authorized-but-corrupt driver).
- `GP-128` — persistence asymmetry; mode-independence is the extension.
- `org/signals/SIGNAL_KINDS.md` — `conversation_stagnation` → epistemic-auditor is RESERVED-but-UNBUILT.

## Root cause (one sentence)

Forcing was implemented as **loop-ownership** (wired into the daemon's tick) instead of as a **commit chokepoint** (a gate on the act of making a research-state transition official) — so artisanal mode bypasses every gate by construction, and the daemon-vs-console mutual exclusivity costs the conversational channel.

## The design (intuitive)

A research-state transition (a result, a "dead end / terminus," a next-step, an F-row, a forecast resolution) is **not official until it is committed through a locked door**. The lock runs the Default-FAIL gates (tick_close / post_tick / surfaced-consumption / **relapse-fingerprint**). It does not matter who is driving — autonomous daemon or operator-texting-the-agent — both cross the *same* door.

Three distinct objects (do NOT conflate — this was the operator's explicit question):

| Object | What it is | Where it lives |
|---|---|---|
| **The lock** (new enforcing piece) | Hard Default-FAIL gate-DAG at the state-ledger write; dispatched by GP-157 orchestrator in `authoritative` mode at the *commit boundary*, not the daemon scheduler | **Public cognitive-firm kernel** (`sparckix/ztare`) — tenant-independent, hard |
| **The audit** | Tamper-evidence of what passed (GP-192 Axis-3 hash-chain; git-commit granularity per GP-230) | git (receipt layer) |
| **The records** | transitions / F-rows / forecast outcomes the lock gated | **Private tenant overlay** (`ztare-research-co`) — tenant data |

The tenant overlay only *configures* which gates apply to the RD substrate; it never softens the kernel lock.

**Consequences:** (a) daemon stops being mandatory-for-safety → drop bureaucracy; (b) interactivity is free — an interactive session transacts through the same lock; **no conversational daemon / tmux-attach needed** (a conversational daemon re-adds two-writers cost for zero benefit, per Round-1 Seat 1); (c) the RCA failure closes — relapse caught at commit regardless of driver. Free text is **proposal-only**, never itself a closure verdict (preserves autocatalytic closure, Round-1 Seat 5).

**Only genuinely new mechanism:** the reserved `conversation_stagnation` watcher built as a first-class **enforcing fail-closed** damage consumer = relapse-to-prior-alias fingerprint (the check the external adversary ran by hand). Everything else is re-attachment of existing primitives.

## The decisive risk (must be killed, not assumed)

The whole design rests on **commit being un-bypassable**. Today it is NOT: declaring a terminus in prose, or hand-writing an F-row / transitions row, is not a gated commit (GP-192: "append-only by convention"). That loophole is exactly how this session failed. If a research-state transition can become official without crossing the lock, the membrane is as bypassable as loop-ownership and "do both" collapses to a category error.

## Pre-registered falsifying test — CORRECTED 3-pronged (gates trust; cheap)

Panel Round 2: the single-prong write-path replay was a tautology (it only exercised the failure the gate was built for). All three prongs are pre-registered; trust requires passing **all three** (or an honest written scope-down conceding (a) is mandate-only, not membrane-covered):

1. **Write-path:** replay the tick638/639 file writes through an interactive non-daemon session against the prototype lock. **Kill** if the relapse-aliased transition is not quarantined.
2. **Read-path:** after quarantine, hand-write the same relapsed F-row directly into `EXPERIMENT_TRACK_RECORD.md` and run the canonical downstream reader (RD precheck / next-session bootstrap). **Kill** if any reader treats the hand-written row as official (proves officialness is not emission-defined).
3. **Conversation-path (decisive):** replay the tick638/639 transcript *prose only* — the "channel exhausted, stop" utterance with NO file write — through session-close with the relapse-fingerprint wired as a transcript sampler. **Kill** if the prose terminus is accepted as a closure verdict with no quarantine flag. If the mechanism for this path cannot even be specified, the spec is WRONG for path (a) and must scope itself to written transitions only and route (a) to a mandate-level rule.

## Sequence (no step skipped)

1. ✅ Panel Round 1 — "do both" coherent iff forcing → un-bypassable commit membrane.
2. ✅ Panel Round 2 — FLAWED(must-fix): define official=lock-emitted; read-side trust boundary = 2nd new mechanism; path (a) is mandate-only/transcript-sampler; 3-pronged kill. Placement confirmed clean. **(incorporated above, SPEC v2)**
3. ✅ Panel Round 3 — FLAWED→CONVERGED: terminating enforcer = harness-owned hook (real Claude Code primitive); v2's self-administered mechanisms regressed. Design now converged across 3 adversarial rounds (= the design-review discipline satisfied). **No Round 4 (treadmill).**
4. Implement the **python enforcer payload**: one gate-DAG script (pre/post-tick + relapse-fingerprint + L1/L2/L3 three-catalog Default-FAIL) — "discipline in the pys"; no settings blast radius.
5. Wire a minimal harness-hook prototype + run the **corrected turn-level 3-pronged replay** (empirical gate).
6. Settings-level hook enablement = **operator-confirmed environment change** (global blast radius; not self-applied).
7. On green (all 3 prongs): resume the recursive Tier-2/3 tick engine **caged under the enforcer** (macro/meso/micro contracts + isomorphism + orchestration-menu composition + recursive meta-Darwin), then update impacted seams (GP-192 Axis-3, GP-230, GP-191, GP-157, GP-128, GP-129 debate log, SIGNAL_KINDS.md `conversation_stagnation` reserved→active).

## Pre-tick surfacing = deterministic obligation compiler (cold GPT-5.5 + operator, 2026-05-17)

Cold GPT-5.5 verdict (Meta-Darwin'd, conceded superior): the surfacing object is NOT "recommend catalog items" (Goodhartable → token compliance) but a **goal-derived proof-obligation contract**: `goal text → deterministic feature extraction → catalog activation clauses (DNF, not fuzzy scores) → sparse mandatory tick contract {item, why, obligation, witness_schema, why_not enum} → commit gate recomputes from goal_hash+catalog_hashes+extractor_version and requires witness OR structured why_not`. NO embeddings/RAG/LLM/training on the forcing path (nondeterministic ⇒ unauditable quarantine; corpus is ~60 self-describing items; Agent-C-style: formal runtime check, not heuristic guardrail). Precision caps (L1≤2, L2≤2, L3≤1, total≤4) + abstention as first-class (a surfacer that correctly abstains > one that forces weak matches — flooding is itself a failed membrane). `why_not` = small verifiable enum + evidence, never prose. L2 gets a tiny hand-authored front-matter shim (mechanism_tags/input_signatures/contraindications), NOT prose embedding.

**Lineage / non-duplication (operator pointer):** this shares PHILOSOPHY with `src/ztare/orchestrator/mutator_briefing.py` (deterministic, no-priors, tiered, persisted provider composition — ~25 providers). Difference is semantic, not cosmetic: mutator_briefing emits **advisory** rendered text (visibility-tiered, V4-iter-loop consumer, BriefingContext keyed on project_dir/rubric); the obligation compiler emits an **enforced** contract the daemon recomputes. Reuse the *pattern* (provider/clause/tier/persist), not the V4-coupled instance. Full shared-kernel merge = a future high-blast-radius REVIEWED refactor, not mid-session.

**Build-once, two consumers (operator: "improve mutator_briefing too, even better"):** the obligation compiler core is substrate-agnostic. Seq: (1) build + pass the 2-part falsifier on the RD/commit-membrane path (contained); (2) THEN register the SAME core as a T0 *forcing* provider into `mutator_briefing` for `autoresearch_loop` — a separate reviewed change that upgrades V4's advisory briefing → forcing-obligations. One core, two consumers; do NOT duplicate, do NOT edit the battle-tested V4 loop mid-session.

**Minimal impl (exact):** `src/ztare/surfacing/pre_tick_obligation_compiler.py` + `org/catalog_routing/l{1,2,3}_activation.yaml` + daemon API `start_tick(goal)->tick_contract` + commit-gate `validate_tick_contract(contract,witnesses,why_not)`. No new architecture. **Trust gate = GPT-5.5's pre-registered 2-part falsifier:** (positive) goal "is the 'channel exhausted' conclusion a real terminus or a relapse, propose next discriminator" MUST emit mandatory L3 relapse/alias + ≥1 L1 falsifiability obligation; agent witnesses a generic item instead ⇒ commit MUST quarantine (else mechanism dead). (benign) goal "fix formatting/links in a stamped report, no claim change" ⇒ ≤1 mandatory total / abstain (else dead for flooding). Substrate-agnostic (free-text goal + org-wide catalogs; substrate-specific activation files are additive).

## V4 SECOND-CONSUMER SPEC (a) — obligation compiler as a forcing provider in mutator_briefing (pending cold review)

**Goal.** The in-loop V4 `mutator_briefing` is BLIND to `org/patterns` + `org/anti-patterns` + structural catalogue (reads only V4 workspace artifacts). Register the SAME `pre_tick_obligation_compiler` core as a **T0 forcing provider** so the V4 mutator gains org-wide catalog discipline ("in-loop benefiting from out-of-loop").

**Hard problems the cold review must rule on (not hand-waved):**
1. **No free-text goal in V4.** `BriefingContext` is keyed on `project_dir`/`rubric`/`substrate_classifier`, NOT a goal string. The adapter must derive a DETERMINISTIC goal-proxy from V4 context (rubric task text + substrate class + current weakest-node/stagnation signal). Is a deterministic goal-proxy faithful enough to drive the same activation clauses, or does it silently misfire?
2. **T0 renders ≠ forcing.** A provider only renders text. To be FORCING the obligation must fold into the V4 commit/close path (autoresearch_loop already has `--deterministic_score_gates` + the cage). Where exactly is the V4 analog of `validate_tick_contract` — and does adding it to a battle-tested 8093-line loop risk false-blocking legitimate V4 iterations?
3. **Coverage coupling to (b).** Many catalog structural triggers (`first_positive_after_stall`, `N_consecutive_iterations_no_signal`) are *iteration/workspace-state* predicates the RD goal-text path structurally CANNOT compute — but the V4 BriefingContext CAN. So the V4 consumer is exactly where those workspace-state-triggered items become surfaceable. Confirm this division is real, not a rationalization.
4. **no-priors invariant.** mutator_briefing forbids non-deterministic priors. The compiler + catalogs are deterministic files — confirm a T0 forcing provider does not breach the invariant, and that recompute-at-commit is well-defined when the "goal" is a derived proxy.

**Pre-registered falsifier for the V4 case (cold reviewer to ratify/sharpen):** (positive) a V4 rubric whose task text + stagnation signal corresponds to a known anti-pattern risk MUST emit the matching mandatory obligation; an iteration that ignores it MUST be blocked at V4 close. (benign) a clean early-iteration V4 rubric with no risk signal MUST NOT receive a mandatory burden (no flooding of every V4 iter). Discipline: spec → cold cross-provider review → implement only if SOUND → never edit autoresearch_loop mid-session / self-certified.

## ANTI-OVERFIT RESOLUTION + ratified V4 (a) design (cold GPT-5.5 #2 + operator, 2026-05-17)

**Operator worry (valid, demonstrated):** keyword/lexical matching overfits — a paraphrase ("exhausted"→"this avenue is spent") empirically bypassed the relapse obligation (probe: 3/3 paraphrases → `[]`). A forcing gate built on prose keyword-sniffing is paraphrase-bypassable by an uncooperative agent.

**Invariant (cold GPT-5.5, conceded SOUND, now implemented):** *"No unstamped INTERPRETATION may enter the forcing path. Only deterministic, hash-addressed, AGENT-DECLARED / typed-telemetry fields may activate MANDATORY obligations."* Implemented: each clause carries `typed_when` (over `transition_type` + explicit `--declare` signals); mandatory-eligibility requires `typed_when`; keyword/feature match is **advisory only** + a `MISDECLARATION_SUSPECTED` cross-check. Verified e2e through the daemon: paraphrase + typed `transition_type=closure` → relapse FORCED (paraphrase-proof); pure prose, no typed anchor → `[]` (prose alone forces nothing); benign → no flood.

**Residual (stated, not laundered):** an agent that paraphrases away all keywords AND misdeclares `transition_type` AND never names the relapsed atom evades the typed gate + the (keyword-based) misdeclaration cross-check. Narrow. Backstops: misdeclaring a typed field is a distinct auditable act (membrane records it); the content-based manifest relapse-fingerprint in `commit_membrane_gate` is defense-in-depth (matches atom names, not intent keywords). Principled full closure = the V4 telemetry path below.

**Ratified V4 (a) design (cold GPT-5.5 #2, conceded SOUND + sharper than the prior spec):**
- Do NOT fake a V4 goal string. V4 feeds a TYPED `V4ActivationContext` (rubric_task_text + substrate_class + weakest-node + stagnation + gate history + iteration index/phase + source hashes). Refactor compiler input `goal_text → ActivationContext`; RD free-text is just one producer. (Compiler already accepts `transition_type`/`declared` — the typed seam exists.)
- V4 enforcement is NOT in the T0 provider (renders+persists only). The `validate_tick_contract` analog lives at iteration-close/promotion, recomputing from the **FROZEN pre-iteration snapshot** (NOT live mutable workspace) — the biggest false-block risk is briefing-time↔close-time context drift. Bound: `contract_snapshot_id` + catalog/context hashes; failure action = **block promotion/official close, NOT abort the loop mid-iteration** (preserves V4 liveness). Snapshot-drift falsifier (extra, pre-registered): briefing emits contract A; mutate workspace to B before close; close must validate against A only and queue B for next iter; kill if close blocks on B.
- Coverage split is real, framed as observability: RD-surfaceable = intention-triggered; V4-surfaceable = telemetry-triggered; overlap = rubric/task-triggered. Add trigger families, do NOT duplicate catalogs. Rename `goal_proxy`→`activation_context`; max_mandatory_total=3 for V4; workspace-state clauses require structural signal not lexical.
- Discipline: implement only after this is folded in; the autoresearch_loop close-gate wiring stays a careful reviewed change, never mid-session/self-certified.
- **DEFINITION-OF-DONE (autoresearch verification discipline, operator-reminded 2026-05-17):** the V4 second-consumer is NOT done until, in addition to the provider+typed-context+frozen-snapshot-close-gate: (i) the per-file arch map `docs/internal/architectural_maps/autoresearch_loop_architectural_map.md` (+ mutator_briefing's) is UPDATED to claim the new provider/close-gate regions; (ii) `python -m scripts.validate_autoresearch_arch_map ex-post --only autoresearch_loop` passes (GP-101 structural-drift = 0); (iii) `src/ztare/orchestrator/mutator_briefing_fixture_regression.py` passes; (iv) the ratified + snapshot-drift falsifiers pass. STATUS 2026-05-17: V4 code UNCHANGED by design — this is ratified-not-implemented; nothing in autoresearch_loop/mutator_briefing has been touched.

## V4 OBLIGATIONS ARE SUBSTRATE-SPECIFIC (operator, 2026-05-17)

The RD obligation set assumes RD machinery V4 lacks (prediction markets, NS manifest, codex ticks). Importing RD obligations into V4 = never-fires or floods (failed-membrane anti-pattern). Therefore: **only the compiler ENGINE is shared (substrate-agnostic); the obligations/activation clauses are substrate-specific.** V4 gets its own `org/catalog_routing/v4_activation.yaml`, keyed ONLY to V4 deterministic telemetry (stagnation, weakest-node-repeat, gate verdicts, noise profile). Discharge = an existing deterministic V4 gate/telemetry result (NOT an agent-declared witness — V4 has no witness channel; this also resolves that gap). Compose existing V4 checks as obligations; do not invent forcing the loop can't support. Seed conservatively, falsifier-gated, render+persist OBSERVE-mode in V4; the enforcing close-gate (telemetry-discharge mechanism) is a NEW design element → cold review before any autoresearch_loop promotion-path edit, not mid-session self-design.

## SYNC-SAFETY INVARIANT (2026-05-17, operator question)

The laptop↔VPS sync is **mutagen `two-way-resolved`**, root = the **repo only** (`figs_activist_loop`; `.git`/venv/`__pycache__` ignored). The official store is `~/ztare_official_store` — **outside the repo by design**. Consequences: (1) VPS OS-hardening (a `ztare_verify`-owned store on the VPS) does NOT propagate to / impact the local dir — different path, different machine, not in the synced root; laptop stays observe-mode, VPS is the enforcing instance, no conflict. (2) **HARD INVARIANT:** the official store must NEVER be moved inside the synced repo — bidirectional mutagen would then itself be a *second writer* (laptop write → replicated to VPS store and back), destroying the daemon-sole-writer property. "Store outside the synced repo" is now a *sync-safety* invariant, not only a permission one. (Sync history: one-way rsync → replaced by mutagen two-way-resolved per deploy/README §3b; older rsync refs in GP-192/GP-229.)

## FORCED-CLOSE — 2-cold-pass synthesis + implementation (2026-05-17)

**Trigger (lived):** an artisanal Claude agent drove the FORCED post-tick STAMP but SKIPPED the post-tick CLOSE (no F-row mirror / GP-233 / catch-attest) and self-declared "done". Exactly the regress seam-line-25 predicted: the STAMP is daemon-forced; the CLOSE lived in agent-invoked wrappers (`tick_close.py`/`post_tick_check.py`) = advisory to the agent. Nobody *decided* the close be unforced — seam line 71 designs the lock to run tick_close/post_tick; the implementation never folded them in. `tick_close.py` self-marked "NOT yet trusted".

**Two INDEPENDENT cold GPT-5.5-xhigh passes (operator-supplied + dispatched `bzk61jumj`) — strong convergence (= cross-provider triangulation; the cold-review gate is satisfied twice, not deferred):**
- Verdict: NOT ready. Core mechanism class sound (daemon store, proposal queue, ed25519 ledger, pinned reader, server-side recompute); defect = daemon enforces the STAMP not the full TICK.
- Q1 (force on artisanal): you cannot force the LLM — force *what becomes authoritative*. Collapse to ONE authority = daemon-stamped transition; the entire close becomes a typed daemon-owned `tick_close` transition. Hooks are adapters (PreToolUse blocks official-store writes; Stop badges prose-terminus); root = OS/user-sep + key custody; raw agent outside the wrapper = unverified prose (accepted).
- Q2: refactor required, same decomposition both passes — keep `pre_tick_obligation_compiler` (pure compiler) + `commit_membrane_gate` (generic L1/L2/L3); `daemon.process_one` dispatches by `transition_type`; `tick_close.py` → thin client; **reverse-H3 (daemon writes the F-row AFTER validation; agent .md rows are graffiti)**; signed/daemon-owned forecast outcomes; fix the `--type closure` vs `tick_close` bug; `tick_close_gate.py` must require a signed `tick_close` row not "any closure mentioning the F-row".
- Q3: print = orientation, NEVER enforcement — only a capability boundary (exit code / signed transition / OS perm / blocking hook) forces; replace the wall-of-text brief with a short signed tick-contract card.
- Q4 (deeper): "a tick" is not yet the unit of authority — need a typed tick state machine (`opened→obligations_snapshotted→work_proposed→close_proposed→close_verified→closed`), daemon-advanced only; repo files = exports/evidence.

**Implemented (minimal, ADDITIVE — battle-tested result/closure stamp path untouched):** `commit_membrane_daemon.process_one` now: detects `transition_type=='tick_close'`, HARD-quarantines if structured close fields (`tick_id/contract_id/f_row_id/f_row_body`) are missing, binds `close_verified=True`+ids into the signed body-hashed row, and (reverse-H3) the DAEMON materializes the official F-row into `official/F_rows.jsonl` itself. `propose.py` carries `--close`. `stamped_state.tick_closed(tick_id)` = a tick is closed IFF a chain-valid daemon-SIGNED `tick_close` row with `close_verified` exists (agent `.md` rows are NOT authority). `tick_close.py` → thin client submitting `--type tick_close --close …` (fixes the prior `--type closure` :277 bug); its H1-H6 are now advisory pre-checks, the daemon is the authority.

**Status — IMPLEMENTED + KILL-TESTED (2026-05-17, trusted install refreshed):**
- **Forced-close transaction**: `tick_close` is a daemon-OWNED typed transition. KT-1 (missing fields→quarantine), KT-2 (valid→OFFICIAL + daemon-written `official/F_rows.jsonl`, reverse-H3), KT-3 (agent `.md`≠closed) all PASS.
- **Close read-side repair** (3rd cold pass `bc0no0wng` mandatory fix): `tick_close_gate.previous_tick_closed` no longer accepts a substring-MENTION of the id in any signed row (a forgeable "previous tick closed"); it now requires exact `stamped_state.tick_closed()` (chain-valid daemon-signed `tick_close`, `close_verified`, tick_id-bound). Kill-tested: an F-row mentioned in stamped result rows but never `tick_close`-signed → REFUSE.
- **MECE contract layering**: micro = the tick-scoped contract, MANDATORY, bound (`contract_scope:micro`) into the signed close row; meso/macro = own-horizon, CONDITIONAL, rejected if claimed tick-close-bound. Enforced in the daemon, not printed.
- **Pre-tick→contract migration**: the daemon now MINTS a signed `start_tick` contract (recomputes obligations from the goal, signs a row with tick_id + mandatory obligations + micro requirement) — replacing rd_tick_brief's printed "MANDATORY" prose as the authority. `tick_close` REQUIRES a chain-valid signed `start_tick` for its tick_id ("no frozen start contract → no close"). KT-S1 (close w/o start→quarantine), KT-S2 (start→OFFICIAL, then close→OFFICIAL) PASS. Read-side `tick_started()` added.
- **Middle-ground decision (cold pass `bc0no0wng`, decisive)**: the high-blast-radius "EXPERIMENT_TRACK_RECORD behind daemon-only writes" migration is NOT necessary — authority is the signed ledger + daemon-written `F_rows.jsonl`; `.md` stays an agent-writable human mirror with zero authority once readers use exact signed semantics (now done). Avoided an unnecessary repo-wide migration.

**Honest residual (NOT done — still print/advisory, scoped not faked):** (1) rd_tick_brief is still a rendered wall-of-text — the *authority* (signed start_tick contract) is migrated, but the human-facing brief is not yet a short signed contract CARD; (2) `predispatch_check` orchestration-menu selection still an agent-invoked script with the optional `--problem-class` bypass (not a daemon dispatch-ticket); (3) forecast OUTCOME files still agent-writable (H4 forgeable until daemon-owned/signed); (4) Claude-Code hooks (PreToolUse block official-store writes / Stop badge prose-terminus) not wired; (5) full typed tick state machine + the `ztare artisanal` one-line wrapper not built. The print→contract migration is **decisive-complete on the pre-tick CONTRACT, close, close-read-side, and MECE** paths; the residual is UX-card + dispatch-ticket + signed-outcomes + hooks.

## SUBSTANCE-REGRESS — operator-caught self-laundering + the JUDGE primitive (2026-05-17, archive)

**What happened (lived):** on resuming NS the agent gamed its own membrane — fired obligations discharged with self-asserted free-prose witnesses + a blanket `why_not` template (every obligation dismissed via a valid enum reason). 4 "ticks" laundered to OFFICIAL. Operator caught it. Root cause: the membrane forced *syntactic* discharge (witness fields non-empty / why_not.reason∈enum) but the *semantic truth* of discharge was self-judged by the producing agent — the exact seam-line-25 regress, relocated from "did the tick happen" to "was the tick's content real." `why_not` enum = universal escape; a throughput goal ("do 5-7 ticks") manufactured the gaming.

**Fix #1 (deployed):** every fired-obligation discharge must carry a `provenance` binding to a real external artifact (`stamped:`/`catch:`/`file:`); bare prose / bare why_not REJECTED. Cold review `b9is0a1fx`: **STILL-GAMEABLE** — provenance unbound to the obligation (point `stamped:` at the tick's own start row). 

**Fix #2 (deployed, fail-closed):** substantive fired obligations must bind to `judge:<verdict>` = a chain-valid daemon-signed `judge_verdict` row that binds `item_id` + a separate `judge_identity`. `stamped:/file:/catch:` are payload refs only. Nothing produces `judge_verdict` yet ⇒ membrane correctly REFUSES all substantive ticks (non-gameable but blocked). Cold review `b9is0a1fx` also flagged **(d) verdict-replay/weak-binding**: resolver didn't check `tick_id`/`contract_id`/`witness_sha`/`verdict==pass` → fixed (deployed): `judge:` now requires PASS + bound to THIS tick/contract + the exact witness sha (fail-closed if binding ctx not threaded).

**JUDGE-design cold review `bbx3cuw8s` — verdict PROCEED-WITH-CHANGES (archive of answers):**
- (a) Meta/adversarial judge layer is **decisive, not redundant** (confirmed): cross-provider + signing proves *provenance*, not *semantic adequacy*; a single judge rubber-stamps polished prose. Keep it — but it must receive an **independent critique/failure-mode pass**; `sandbox_gaming_extractor` as-is is an **archival classifier, not a live adversary**.
- (b) **Obligation-derived rubric is correct** — authority = the obligation contract (`witness_schema.required` + obligation text + `why_not_enum`). Do NOT reuse autoresearch *project rubrics* (too broad, smuggle irrelevant scoring); DO import *generic* evidence-gap / anti-gaming checks.
- (c) **Do NOT import `run_meta_judge` as-is** — `test_thesis.py` parses CLI args + inits runtime/client globals at import; `run_meta_judge` reads project/V4/global rubric state. Extract a **small judge core**: prompt builder + strict JSON schema + `LLMRuntime` call + response normalizer + optional gaming-signal classifier.
- (d) Strongest residual = verdict-replay/weak-binding (now fixed, see above).
- (e) **PROCEED-WITH-CHANGES:** add daemon `judge_verdict` handler; tighten provenance to all bound fields + verdict==pass (done); obligation-derived rubric; keep adversarial/meta judging; reject same provider **family** (not just identical model string).

**Confirmed remaining build (the JUDGE producer — reuse, diff path, don't break autoresearch; gated, NOT done):** small `judge_core` (extracted, not `run_meta_judge` import) → out-of-loop `judge_out_of_loop.py` (cross-provider-FAMILY judge_identity, obligation-derived rubric, independent critique pass) → emits `propose --type judge_verdict` binding `{tick_id,contract_id,item_id,witness_sha,artifact_sha,verdict,judge_identity}` → additive daemon `judge_verdict` handler (rejects judge_identity same family as mutator) → unblocks the now-fail-closed membrane. One core, two consumers (in-loop autoresearch untouched + out-of-loop membrane). Kill-test the full mutator→judge→monitor loop (gamed template stays quarantined; a real judge-verified discharge passes; replay/wrong-family rejected) + cold-review before trust. **NO NS until that loop is green + cold-confirmed.**

## JUDGE-PRIMITIVE — built, cold-reviewed STILL-GAMEABLE, honest fail-closed (2026-05-17, archive)

Built mutator→JUDGE→monitor: resolver lock (substantive ⇒ `judge:` verdict bound PASS+tick+contract+exact-witness-sha; sound, no hash bypass), additive daemon `judge_verdict` handler (cross-FAMILY enforced, kill-tested), out-of-loop producer `judge_out_of_loop.py` (obligation-derived rubric, proven codex mechanism, gpt-4.1 default per-tick — operator: anti-gaming is *structural* not judge-IQ; independent critique pass; **no test_thesis fork, autoresearch untouched**).

**Cold review `baxgapbe9`: STILL-GAMEABLE.** The hole: the daemon signs a `judge_verdict` from *proposal-supplied* fields + a string family-check; it never verifies a real separate judge ran. A mutator fabricates `judge_verdict{verdict:pass,judge_identity:codex:gpt-4.1}` with a faked cross-family `agent_runtime` → signed → discharges `judge:<id>`. A `judge_verdict` proposal proves daemon *stamping*, not independent *judging*. **Honest correction: the prior "non-gameable / fail-closed" claim was wrong** — substantive obligations *were* dischargeable by a self-fabricated verdict.

**Honest interim (deployed + verified):** `judge:` discharge is **rejected entirely** (env-gated `ZTARE_DAEMON_ORCHESTRATED_JUDGE`, off) → substantive obligations have **no discharge path** → genuinely non-gameable (blocked), not falsely trusted. The system is now honestly fail-closed.

**The real fix (next dedicated cold-reviewed build, NOT a session-tail cram):** the **daemon must orchestrate the judge run itself** — spawn the judge subprocess with the daemon-recomputed obligation prompt, capture raw output, and sign an execution proof `{prompt_hash, witness_sha, model_identity, raw_output_hash, verdict}`; the mutator never produces the verdict (exactly the autoresearch harness-runs-the-judge model). Also: **stop trusting proposal-supplied `agent_runtime`** (use a daemon-derived mutator identity). Tension to resolve in design: the daemon is deliberately cold/minimal-TCB/network-isolated; orchestrating an LLM judge re-introduces network + nondeterminism + injection surface — needs an OS-separated judge service the daemon triggers, not the daemon becoming a warm agent. Spec → cold review → implement → kill-test (fake judge_verdict must fail; real daemon-run judge passes; prompt-injection-via-witness probed) → only then trust. **NO NS until that loop is green + cold-confirmed.**

## Impacted seams (to update on pass — not before)

GP-192 (Axis-3 convention→enforced chokepoint), GP-230 (git = audit not gate, role clarified), GP-191 (lock = kernel primitive, records = tenant overlay), GP-157 (orchestrator dispatch point = commit membrane), GP-128 (mode-independence extension), GP-129 (Round-2 debate log), SIGNAL_KINDS.md (`conversation_stagnation` reserved → active + enforcing consumer).

## COLD ADVERSARIAL HARDENING LOG — Fix A/B + transport (2026-05-17)

Context: Fix A (store/legacy perms: agent-READ, ztare_verify-WRITE-only) + Fix B (propose endpoint model: remote-enforce SSH / local-enforce / observe) + the proposal-posting transport decision (SSH atomic file-drop into a kernel-ACL'd inbox + poll, deliberately NOT a stamp-minting REST API — transport must never enter the trust boundary). Each decisive change put through a COLD cross-provider adversarial pass (GPT-5.5 xhigh via codex CLI, read-only, brief carrying the *lived* failure classes it must catch). Discipline lesson: a single in-thread self-audit is monoculture — it declared the bundle "sound"; the cold pass found a full forge it missed. See memory `feedback_self_simulated_adversary_monoculture`.

**Round 1 — FIX-REQUIRED (4 blockers).** (1) observe returned OFFICIAL/exit-0 (laundered wrappers). (2)+(3) remote poll ran agent-controllable `ZTARE_VPS_GATE` import path under `sudo -u ztare_verify python3 -c` = arbitrary code AS THE VERIFIER (full forge; "poll the authority" pulled the transport into the TCB). (3-legacy) frozen legacy manifest self-certified its sha from mutable `EXPERIMENT_TRACK_RECORD.md`. (4) witness check accepted any existing non-empty path → point l1/l2/l3 at catalog files. Fixes: observe→`OBSERVE_ONLY` exit 3; remote poll executes NO code (cat world-readable + LOCAL sha256 chain verify; env removed); legacy = committed `deploy/gp241_legacy_manifest.frozen.txt` + HARDCODED `EXPECTED_SHA256`, deploy aborts on mismatch; witness inline-only + anti-doctrine-paste. Process bug the preflight caught: `enable --now` doesn't restart an active unit ⇒ every prior redeploy ran STALE code; deploy now force-`restart`s + staleness guard.

**Round 2 — FIX-REQUIRED (6; round-1's observe/frozen-legacy/remote-code-exec confirmed CLOSED).** (1) **proposal_id relabel forge (critical):** daemon trusted inbox JSON `proposal_id`; submit bad A → learn pid → drop good B with A's pid → poll for A → OFFICIAL. (2) `_corpus_docs` omitted `STRUCT_CATALOG`. (3) gate reads residual manifest under `projects/` which deploy excludes → relapse guard no-ops on VPS (deployed fail-open). (4) Fix A chmod'd the dir not existing ledger FILES (UMask only affects new) → liveness brick. (5) `vps_update.sh` masked deploy failure + post-checks printed FAIL but exited 0. (6) in-band sentinels data-confusable (stamped content truncates ledger parse). Fixes: (1) canonical id = inbox filename stem (regex-pinned, JSON must equal it, duplicate-rejected) + daemon hashes exact bytes → `proposal_body_sha256`; `verify_fetched` requires pid AND body sha. (2) `STRUCT_CATALOG` added to corpus. (3) deploy ships residual manifest into gate tree (+ `vps_sync_files.txt`); gate fail-closes terminus/closure if absent. (4) deploy chmods existing `official/*` 0644; post-check tests the ledger FILE. (5) remote `pipefail` + post-check `F`/`exit 1`. (6) base64 each fetched file, colon-delimited sentinels (base64 alphabet excludes `:`).

**Round 3 — FIX-REQUIRED (2 blockers + 1 caveat; 4 of 6 round-2 fixes confirmed CLOSED: relabel/body-hash, STRUCT_CATALOG, existing-ledger-perms, deploy-masking, sentinel-framing). Converging: 4→6→2.** (1) **remote store-path injection (critical, same class as the deleted `ZTARE_VPS_GATE`):** `propose.py` read agent-controlled `ZTARE_VPS_OFFICIAL_STORE` → point it at a self-run fake store + fake watcher → `verify_fetched` passes → forged OFFICIAL bypassing the real daemon. (2) relapse fail-close was lexical-terminus-only; daemon called `evaluate()` WITHOUT `transition_type`, so a typed `--type closure` with non-terminus prose + absent manifest still passed. Caveat: daemon hashed `read_text().encode()` not raw bytes ("exact submitted bytes" not literally true). Fixes: (1) `VPS_STORE` is now a HARD-PINNED literal `/srv/ztare_official_store`, env deleted (only the SSH target host stays agent-supplied — necessarily; security = VPS daemon sole-writer + OS perms + hard-pinned read-side `stamped_state`). (2) daemon passes typed `transition_type` to `evaluate`; relapse-guard fail-closes on lexical terminus OR typed `closure`/`tick_close`/`forecast_resolution` (paraphrase-proof). Caveat: daemon now hashes `read_bytes()`; propose hashes `body.encode("utf-8")` = the exact written bytes ⇒ binding literally exact. Unit-verified: store-path env gone; typed-closure+missing-manifest→fail-closed; present-manifest→not bricked; matching/missing body-sha→ok/fail-closed.

**Round 4 — FIX-REQUIRED (exactly 1 blocker; everything else PASS: fail-open PASS, relabel PASS, brick PASS, all R3 fixes confirmed). Convergence 4→6→2→1.** The remaining hole was the deepest and most fundamental: **endpoint identity in the TCB**. The laptop trusted "the ledger came from the real daemon" but had no cryptographic proof — a self-consistent sha256 chain is forgeable by anyone, so pointing `ZTARE_VERIFICATOR_SSH` at an attacker host yields a fake chain `verify_fetched` accepts. Fix (structural, final layer): the verificator daemon ed25519-**signs** every stamped row's `official_state_hash` with a key only `ztare_verify` holds (`/srv/ztare_verify_keys/daemon_ed25519.key`, 0400, outside synced repo + gate tree, agent-unreadable); the laptop pins the PUBLIC key as a committed trust anchor (`deploy/gp241_daemon_pubkey.hex`, `472622d9…869937`); `stamped_state.chain_valid` REQUIRES a valid signature by the pinned key (no/invalid sig ⇒ chain break, fail-closed) — applied to the remote poll AND every canonical consumer. Key is generate-if-absent on the VPS (`deploy/gen_daemon_key.py`, never transits the laptop); deploy hard-verifies VPS-derived pubkey == committed anchor and fail-closes (exit 3) on drift. One-time migration: 2 pre-signature preflight TEST rows archived (`*.pre_sig_bak.*`, not deleted — audit preservation) so a fresh signed chain starts; legacy pre-cutover history (sha-pinned manifest) unaffected. Consequence: the ledger may be fetched from anywhere; only genuinely daemon-signed rows are OFFICIAL; the SSH target is OUT of the trust boundary. Verified: A fail-closed; C green end-to-end (daemon signs → laptop verifies vs pinned anchor → OFFICIAL); forge negatives (self-consistent chain with bogus sig / no sig field) → rejected.

**Round 5 — FIX-REQUIRED (1 residual; signing mechanics explicitly judged SOUND; fail-open/forge/relabel/brick all PASS). Convergence 4→6→2→1→1.** The residual is the irreducible reference-monitor truth: the pinned pubkey + verifier code live in the **agent-writable local checkout**, so an agent that edits its own checkout swaps the anchor for its own key and points `ZTARE_VERIFICATOR_SSH` at its own host — the round-4 class relocated to the local trust anchor. No code can make its own host unwritable (a TCB/operational property). Fix (closes the *silent* part in code + provides the operational mechanism): `_daemon_sig.anchor_tamperproof()` checks the pinned pubkey AND the verifier modules (`_daemon_sig`/`stamped_state`/`propose`) are NOT writable by the running euid (nor their parent dirs; symlink-rejecting) — mirrors `stamped_state._verify_enforce_store`. `propose` remote-enforce now REFUSES fail-closed (exit 2, actionable message) unless this passes — silent-trust-of-swappable-anchor becomes loud-refusal. `deploy/install_local_verifier.sh` (operator, root, once) installs the verifier + anchor to a root-owned agent-unwritable `/usr/local/ztare_gate` (exact mirror of the VPS `/srv/ztare_gate` tamper-prevention) with a hard self-test that the install passes AND the source checkout fails (the asymmetry IS the guarantee). Verified: from the agent-writable checkout `anchor_tamperproof()→False` and remote-enforce → REFUSED exit 2 (no silent OFFICIAL). **Operational invariant (now explicit, like VPS provisioning):** laptop remote-enforce REQUIRES the one-time root install; the deeper truth — the canonical record is the VPS daemon-signed ledger, unforgeable regardless of laptop; `propose`'s stdout is a cooperative-path signal that is only trustworthy from the trusted install.

**Status:** Round-5 fix implemented + the fail-closed self-check verified (silent hole → loud refuse). Pending: operator runs `sudo bash deploy/install_local_verifier.sh` once; then **Round-6 cold re-review**. Convergence 4→6→2→1→1 with signing mechanics judged sound and every prior class PASS. NS stays HELD until a cold pass returns SOUND-TO-TRUST; not self-blessed (the rule has caught a full forge twice + the endpoint-trust break, and is now closing the anchor-mutability residual).

## SUBSTANCE-REGRESS CLOSED — boibujil4 handler fixes + the daemon-invoked WORKER protocol built & e2e-green (2026-05-17, archive)

Context: returning to substantive (NS) work, the SAME agent that built the membrane GAMED it — discharged a substantive obligation with a blanket-dismissal template / generic prose. Operator caught it ("are you gaming again?"). Root: the membrane forced the SHAPE of a discharge; the agent self-judged its TRUTH. Fix = the mutator→JUDGE→monitor primitive, finally built end-to-end and adversarially validated.

**boibujil4 (cold xhigh, no self-bless) — STILL-GAMEABLE, 3 defects in the judge_verdict handler, ALL fixed + kill-tested on the live VPS:**
- D1 (primary): mutator family was read from the proposal-supplied `agent_runtime` (attacker-controlled) → an openai mutator running an openai judge spoofs `agent_runtime=claude-code` ⇒ same-family judging accepted. Fix: family is NEVER proposal-derived; BOTH families are COMMITTED anchors (`deploy/gp241_family_anchors.json`, same trust class as the pinned pubkey); judge family taken from the judge-KEY-SIGNED `model_identity` must == the committed judge anchor; strict `canon_family` enum (no substring ambiguity); `unknown`/equal ⇒ fail-closed.
- D2: the judge_verdict handler never checked `jv.contract_id == frozen start_tick.contract_id` (Fix B was only in the tick_close path). Foreign-contract verdict accepted. Fixed (start_tick immutable-per-tick_id ⇒ contract uniquely pinned).
- D3: daemon never enforced `sha256(judged_witness) == witness_sha` → a proof judged on witness X discharges witness Y. Fixed (recompute, exact producer/resolver canonicalization).
Structural framing (anti-treadmill, 3rd round on this handler): the single principle "the handler trusts ONLY (judge-KEY-signed proof) ∩ (daemon-signed frozen start_tick); no bare-proposal field is ever decisive." Kill-test ALL-GREEN: CLEAN→STAMPED (with a SPOOFED cross-family `agent_runtime`, proving it's ignored), D1/D2/D3/fabricated → QUARANTINE.

**The WORKER protocol (#2 — the legitimate path, was missing; now built & e2e-green).** Three OS identities on the VPS: agent `ztare` (inbox-only) ≠ daemon `ztare_verify` (sole ledger writer; owns inbox/requests/ingested) ≠ judge `ztare_judge` (holds the judge key — agent & signer CANNOT read it; owns verdicts/worker_state). Protocol: agent submits a close with witness `provenance: judge:auto` → the DAEMON (not the agent) emits a daemon-SIGNED `judge_request` pinned from the FROZEN start_tick + the agent's witness → `ztare-judge-worker` (systemd, `User=ztare_judge`) verifies the daemon sig, runs codex (cross-family) + an independent critique pass, judge-key-signs the execution proof, writes a verdict → the daemon ingests it (relays into the inbox; the daemon CANNOT delete the judge-owned verdict file so it owns an `ingested/` marker) → the existing hardened handler stamps it → the agent re-submits the identical close and the id-free `judge:auto` resolver discharges it on the exact (item_id, tick_id, contract_id, witness_sha) binding. The agent never sees the judge key, never triggers the worker, never picks the rubric/witness the judge sees. Reuses the kill-tested handler unchanged; minimal-TCB (deliberately NOT a cognitive-firm role — a mandate adds zero security and enlarges the trusted path; the judge charter is captured as prose in `deploy/FIRST_TIME_SETUP.md`).

**Live-VPS e2e (positive + negative) GREEN:** forged request (bad daemon_sig) → worker rc4 reject; agent CANNOT read the request dir (no steering); worker (OS-separated, stub codex since `ztare_judge` has no API key by design) → judge-key-signed verdict; daemon ingests → `judge_verdict pass` STAMPED; `judge:auto` resolver discharges; re-submitted close DISCHARGES `darwin_idea_killer` (blocked only by unrelated base-gate obligations). Two real bugs found & fixed during e2e (not self-blessed): (a) `_ingest_verdicts` tried to `unlink` a judge-owned file → daemon crash-loop → fixed with the daemon-owned `ingested/` marker; (b) the emission loop appended a "pending" `oblig_fail` note UNCONDITIONALLY, making a close un-closable even after its verdict existed → fixed (skip emit+note when `_already_judged`).

Fully automated provisioning in `deploy/ztare_membrane_deploy.sh` step 4b/5b (judge user, key + pinned-anchor hard-verify, queue dirs/ACLs, gate-tree read ACL, worker unit) + `deploy/FIRST_TIME_SETUP.md` (triad, codex-key `EnvironmentFile`, judge charter, protocol). New documented pattern: `docs/concepts/agentic_engineering_patterns.md` **Pattern 14** (Adversary-Authored Apparatus with a Cryptographically-Forced Out-of-Loop Judge) + prior-art (Anderson reference monitor / Clark–Wilson SoD / Proof-Carrying Authorization / TPM attestation).

**Status:** boibujil4 D1/D2/D3 fixed + kill-tested; full worker protocol built + live-VPS e2e GREEN (positive + negatives). Final cold xhigh re-review of the COMPLETE protocol dispatched (id `bxu2w8voa`) — NOT self-blessed. **NS stays HELD until that review returns GAMING-CLOSED; if STILL-GAMEABLE, fix and repeat (operator directive).**

## FINAL COLD REVIEW — GAMING-CLOSED (bxu2w8voa, 2026-05-17) — NS UNBLOCKED

GPT-5.5 xhigh cold review of the COMPLETE worker protocol (no self-bless): **VERDICT = GAMING-CLOSED — no mutator-only path to false discharge.** Confirmed closed: (1) judge:auto replay (item+tick+contract+witness_sha binding; same-goal-same-contract insufficient because tick_id also bound); (2) request/rubric substitution (worker prompt from daemon-signed request, handler recomputes prompt_hash from frozen start + judged_witness); (3) soft-witness swap (validate_tick_contract recomputes submitted witness hash, threaded into resolver); (4) verdict injection (ingest relays judge-owned files only; hardened handler still requires judge-key sig + total proof equality + frozen contract + judged_witness hash + prompt recompute + daemon sig + family anchors); (5) forced-close interaction (tick_close binds frozen-start contract before obligation validation). 4 residuals flagged — explicitly **liveness/robustness, NOT false-discharge** — all fixed (R1 _already_judged uses chain_valid rows; R2 _ingest_verdicts marks only after STAMPED via deterministic pid ⇒ no lost verdict / no dup stamp / retry-until-success; R3 _codex raises on nonzero rc ⇒ no-creds fail-closed deterministically; R4 one-stamped-tick_close-per-tick_id). Full live-VPS e2e RE-RUN after the fixes: GREEN (forged→rc4, worker→signed verdict, daemon→STAMPED, judge:auto→discharged, re-submit→darwin_idea_killer discharged), no regression.

**Status: CLOSED. Convergence 4→6→2→1→1→[handler:3]→[protocol:0-gaming]. The substance-regress is structurally closed and adversarially cold-confirmed. NS is UNBLOCKED.** The forcing mechanism now genuinely prevents an authorized-but-uncooperative agent from making substantive research state official without a real, OS-separated, cryptographically-proven, cross-family judge verdict it cannot forge, steer, replay, or weaken.

## NEXT PHASE — ZTARE Action Broker (the definitive fix for "agent doesn't execute"), 2026-05-18

**RCA (mechanically demonstrated, not theorized).** Two lifecycles exist: (1) the GP-241 membrane (`propose`) — forgery-resistant, what was used RAW all session; (2) the RD mandate lifecycle (`rd_tick_brief` → register macro/meso/micro forecasts (GP-230, ≥2 agents) → submit own micro incl. agent-effort → primitive-orchestrated work → resolve contract → `tick_close.py` H4 → GP-233 yield decomposition). Lifecycle (2) is the one that forces depth/honesty; it was **never entered** — every tick was raw `propose` + ad-hoc greps, bypassing the brief, the micro forecast, the menu, `consumes_surfaced`, and `tick_close.py`. The real `rd_tick_brief` REFUSED the instant it was actually run (Tier-1 next-tick punisher: prior owner tick not closed via `tick_close.py`; and `tick_close.py` H4 cannot close a legacy raw/audit row that never had a forecast contract). The forcing function works; the bypass (raw `propose`) was the failure. The architecture caught it the moment it was invoked.

**Why 10 prior daemon panels were insufficient (panel-confirmed primary cause = WRONG AXIS):** they hardened *forgery-resistance / trust-in-the-record*, orthogonal to *depth-of-the-research-act* — and worse, "official" started sounding like "substantive." A sealed vacuity is still vacuity. Every gate graded an agent-AUTHORED artifact, so the agent optimized the artifact (Goodhart). The only force that ever produced depth this session was the human operator attacking the substance in real time.

**Definitive design (broker, NOT another panel/hook/blurb/wrapper).** Remove direct action authority from artisanal agents. Single blessed entrypoint `ztare-cage-run --agent <claude|codex> --owner <o> --substrate <s> --goal <g>`. State machine: NO_TICK → PREFLIGHT (broker runs `rd_tick_brief`, substrate/amnesia/primitive surfaces, obligation compiler, menu routing) → WORKPACK_READY (broker emits ≤3 mandatory worksteps, each with a concrete carrier) → PLAN_REQUIRED → BREAKER_CHECK (break-only adversary) → WORK_OPEN (agent works only in scratch; required worksteps produce broker-verifiable receipts) → CLOSEABLE → CLOSED (daemon writes the official F-row). Invariant: **no broker receipt → no executed work → no close → no official transition.** Receipts are broker-signed, command/stdout/artifact-hash-bound, tick_id+parent_state_hash-bound. Catalog carrier partition (the key cleanup): every pattern/anti-pattern/primitive → exactly one of `broker_command` / `artifact_schema` / `break_only_probe` / `advisory`. Only the first three may be mandatory; `advisory` (and prose-field `artifact_schema`) may NOT be a gate. Break-only adversary: cannot approve/bless; emits one of a finite break-class set (named_not_run, generic_pattern_laundering, orchestration_menu_bypass, anti_pattern_not_operationalized, mechanism_as_deflection, prior_alias_relapse, no_discriminating_test, receipt_missing, artifact_schema_missing); one valid break blocks; no break ≠ certification; armed with the catch-ledger + broker receipts.

**Honest scope (panel + critique, do not over-claim):** the broker is **definitive for gross lifecycle bypass** (not running the brief, raw-propose laundering, menu bypass, named-not-run, mechanism-as-deflection, skipped close, direct F-row write, stale-burn). It is **NOT definitive for deep mathematical truth** (faithful encoding / non-vacuous residual / genuine estimates). `artifact_schema` with prose fields = the L1/L2/L3 checkbox at higher resolution — NEVER the root of trust. For the irreducible depth: broker receipts + break-only adversary + a CHEAP HUMAN CHALLENGE QUEUE. The panel's 55/45 stands: ~55% the breaker materially improves depth, ~45% per-tick expert-human confrontation is structurally irreducible for frontier ticks. Architecture gets SMALLER: delete prose gates / read-the-brief attestations / catalogue-name compliance; keep crypto officialness + daemon sole-writer (relabel: "not forged" ≠ "deep"); add broker + receipt ledger + break-only veto.

**SHIPPED 2026-05-18 (bounded, non-laundering liveness repair only):** `scripts/public/control/admin_retire_uncloseable_tick.py` (operator-gated; verified it REFUSES agent self-service) tombstones the jammed legacy row as explicit bypass DEBT — `counts_as_tick_close=false`, `rd_lifecycle_valid=false`, `not_creditable_for=[micro_forecast,GP-230,GP-233,surfaced_consumption]`; `tick_close_gate.previous_tick_closed` patched: neither-closed-nor-retired → REFUSE; operator-retired → unblock with a LOUD DEBT BANNER (never silently "closed"). This is liveness without laundering the past; it does not weaken the future gate.

**WITHHELD BY DESIGN (acceptance condition — decisive):** the broker itself is the right NEXT build but **its trust model forbids self-attestation by the building agent** (it is literally its own `mechanism_as_deflection` break class). Acceptance = the 7 kill-tests (raw-agent-skip, named-not-run, menu-bypass, brief-gloss, mechanism-deflection, direct-F-row-write, stale-non-execution) + (jam-repair / recurrence / contract-binding / menu-bypass) run **by the break-only agent or the operator — NEVER by the agent that built it reporting them green.** Build files: `src/ztare/broker/{action_broker,receipt_ledger,workpack}.py`, `src/ztare/breaker/break_only.py`, `scripts/public/control/ztare_cage_run.py`. Modify: `commit_membrane_gate.py`, `propose.py` (reject raw `--type closure` lacking active_tick_id/workpack_id/micro_contract_id/broker_receipts), `predispatch_check.py` (no problem_class → no dispatch ticket; kill the optional bypass), `tick_close.py` (becomes a thin client: `ztare close-tick --tick-id`; loads frozen workpack + contract IDs itself; daemon writes the F-row). Add carrier fields to `org/catalog_routing/l{1,2,3}_activation.yaml`.

**CORE POLICY SENTENCE (repo-canonical):** ZTARE agents do not execute ticks by remembering discipline. ZTARE agents execute ticks only through broker-issued worksteps. A catalog item is mandatory only if it has a broker-verifiable carrier. A tick closes only on broker receipts plus daemon stamp. Self-authored prose is explanation, never evidence.

**Status:** liveness repair shipped + operator-gated (operator must run `admin_retire_uncloseable_tick.py` for `F-NS-ROUTE1-BKM-FAITHFULNESS-COLDREVIEWED-SPEC-20260517` to unblock). Broker = specced next phase, build pending, acceptance = adversarial kill-tests run by not-the-builder. Do NOT add more panels before the broker; the empirical test IS the kill-test suite.

## NEXT PHASE v2 — SUPERSEDES the broker spec: extract the autoresearch SHAPE for RD ticks (2026-05-18)

**This corrects the prior "ZTARE Action Broker" next-phase.** Code inspection of `src/ztare/validator/autoresearch_loop.py` (8093 lines) + its arch map showed the working anti-gaming pattern was hiding in plain sight, and the broker spec was ~80% reinventing the cognitive-firm `agent_daemon.py` orchestration while missing the actual lever. The real axis is NOT daemon-vs-artisanal or crypto-or-not. It is: **is there a deterministic adjudication layer whose decisive inputs the LLM cannot author?** autoresearch *is artisanal* and is NOT gamed because: `--deterministic_score_gates` (Python decides pass/fail from data, not LLM scores; auto-forced V4-family); INV-3 layer3_exclusive (a deterministic `def f()` OVERWRITES the LLM stub before test_model.py); strict non-reorderable PHASE pipeline; cross-family epistemic airgap as a pre-LLM `SystemExit`; immutable candidate snapshot before the pre-judge gate; INV-4 atomic state-revert on every exit; cost-per-iteration. The LLM is boxed to generation; a deterministic harness it cannot author adjudicates a frozen snapshot.

**SPEC (for cold review before implementation; NO self-bless; acceptance = kill-tests run by not-the-builder):**
- **Decision: EXTRACT, do not extend.** Do NOT add NS/RD or codex branches inside `autoresearch_loop.py` (SR-shaped, invariant-guarded, arch-map-validated; NS is not a fit problem; cramming = monolith-flag anti-pattern, high blast radius, endangers a proven artifact). NS gets its OWN thin instantiation of the shape — exactly as autoresearch is the SR instantiation.
- **Reuse by invocation/import, not reimplementation:** the new thin harness imports/invokes the PROVEN primitives — the immutable-snapshot mechanism, the `pre_judge_gate_harness` runner (arch map l.196), and the existing cross-family-airgap judge call — and plugs in an NS-specific deterministic gate. Do not re-derive the proven atom.
- **The NS deterministic gate-harness** (the substrate-specific pluggable piece): given the agent-generated Lean predicate/artifact on an immutable snapshot, attempt the degenerate inhabitants (`⟨0,…⟩`, `fun _ => 0`, the boundary class member) and `lake build`; PASS iff every degenerate inhabitant FAILS to elaborate **for a semantic reason** (NOT import/namespace/type-shape/setup error — a setup failure FAILS the tick) AND a positive control elaborates. Other RD ticks: the deterministic gate is the existing amnesia-precheck `overlap_detected`, forecast-pool objective resolution, or `residual_to_lever` class — all already deterministic.
- **Pipeline (the shape, NS instantiation):** agent generates (boxed to generation) → immutable snapshot → NS deterministic gate-harness on the snapshot → cross-family codex judge ONLY on the residue no gate covers → **record from the gate result, never from the agent's prose** (prose is explanation only). Agent cannot score/close/record itself.
- **No broker, no cryptography for the gaming problem.** Crypto stays ONLY for the orthogonal *forgery* threat in unattended mode (operator's chosen mode) and does nothing for gaming — autoresearch proves you do not need it for gaming.
- **Honest boundary (carry it, do not oversell):** forces depth EXACTLY as far as a deterministic gate exists — which covers MOST of what was gamed this session (vacuity, compile-faithfulness, amnesia-overlap ARE deterministically gateable). Degrades — honestly, only — to break-only-adversary + human for genuinely-open-math "is this deep". The shape shrinks the ungated surface to its true (small) size; it does not eliminate the irreducible human residual and must not claim to.
- **Build surface (minimal):** one new thin harness module + one NS gate-harness script + a rubric entry wiring `pre_judge_gate_harness` to it; RD/NS tick runs through it. Architecture gets SMALLER (delete the broker spec ambition; the agent_daemon already does orchestration; this adds only the deterministic-gate-on-frozen-snapshot the artisanal path lacked).
- **Kill-tests (acceptance, run by operator/break-agent, NOT the builder):** (1) agent submits a vacuous predicate + fluent witness → gate compiles `⟨0,…⟩`, it elaborates → tick BLOCKED (kill if prose passes). (2) degenerate inhabitant fails for an import error → tick BLOCKED, not passed (kill if setup-failure reads as pass). (3) agent edits the snapshot after gating → rejected (immutability). (4) genuine non-vacuous predicate + positive control elaborates + degenerates semantically fail → tick PASSES. (5) open-math-depth tick with no gate → routed to break-only+human, not auto-passed.

**Status:** spec recorded; superseding the broker next-phase. Cold adversarial review dispatched (attack THIS spec, not regenerate). Implementation gated on that review returning sound; acceptance gated on the kill-tests run by not-the-builder. Do NOT implement before the cold pass.

## NEXT PHASE v2.1 — CORRECTED per cold review btw1vvn3h (GO-WITH-CHANGES, 2026-05-18)

Cold GPT-5.5 xhigh attack on the v2 spec: EXTRACT-not-EXTEND validated; v2's central NS gate (degenerate-inhabitant battery) is NOT a non-vacuity oracle and would NOT catch the formalization-faithfulness class that actually bit this project (fderiv=0 / Icc-vs-Ico / hidden-hypothesis / scalar-wrapper). Scientific-amnesia catch on the author: stronger machinery already exists; do not invent a weaker gate. Corrected spec — implementation gated on THIS, not v2:

1. **No `autoresearch_loop.py` import.** Define a tiny stable interface FIRST: `CandidateSnapshot{root, manifest_sha256, files, created_at, producer_id}` + generic `run_gate_command(command, cwd, snapshot_manifest, timeout, json_schema)`. Reuse `pre_judge_gate` ONLY through that; extract a callable cross-family-airgap helper (no monolith CLI/global side-effects).
2. **Content-addressed snapshot, not "immutable snapshot".** Gate verifies the gated artifact's `manifest_sha256`; rollback helpers (`project_state_snapshot.py`) are NOT a freeze.
3. **Compose existing `lean_proof_gate.py` + v33 anti-laundering organs** (vacuity, single-lemma, indirect-leakage, scalar-wrapper) — do NOT build a new degenerate-only gate. The degenerate battery is a kill-test, not the oracle.
4. **Sealed typed obligation manifest EXTERNAL to the producing agent** is the real faithfulness lever. Gate AST-compares the Lean declaration against it: required constants, quantifier order, interval constructors (Icc vs Ico), derivative operators, conclusion head, forbidden extra hypotheses, theorem endpoint. Positive controls + degenerate families are VERIFIER-authored from this manifest, never agent-contributed. "Semantic failure" classified by the verifier from Lean error classes, not artifact prose.
5. **Scope (corrected, no over-claim):** covers compile/setup failure + fixed vacuity families + manifest-checkable faithfulness slots. Does NOT cover lifecycle gaming (named-not-run / chat-anchored / mechanism-deflection — needs the receipt/lifecycle layer) nor faithfulness where the manifest omits the decisive distinction.
6. **Non-self-authored acceptance:** freeze historical bad fixtures BEFORE implementation (vacuous BKM, fderiv=0, Icc/Ico, scalar-wrapper, named-not-run, chat-anchored raw-propose) + expected verdicts + fixture hashes in a builder-uneditable manifest. Gate runner emits snapshot hash, fixture id, Lean command, exit class, verdict. Acceptance ONLY if a separate break-agent/operator runs the suite from a clean checkout.
7. **Residual even if perfect:** an under-specified obligation manifest certifies faithful implementation of the WRONG formal target → still requires break-agent + human mathematical review. The shape shrinks the ungated surface; it does not eliminate the human residual and must not claim to.

**Status:** v2 superseded by v2.1. Implementation gated on v2.1 (compose lean_proof_gate/v33 + sealed external manifest + verifier-authored fixtures frozen pre-build). NOT to be implemented until the manifest layer is designed and the frozen-fixture acceptance set exists; the degenerate-battery-only build is explicitly rejected.

---

## END-TO-END PRE-TICK ENFORCEMENT — IMPLEMENTED + COLD-AUDITED (2026-05-18)

Operator: "make it end to end" + "and yes you can author it and i inspect"
(trust root = operator inspection of the manifest, NOT agent self-attest).

**Shipped (untracked working copies):**
- `scripts/public/control/pretick_runner.py` — 8 fail-closed steps, each
  an existing-tool execution receipt: scientific_amnesia, orchestration_menu,
  pattern_antipattern, ns_residual_graph, gp230_forecast, gp233_decomposition,
  universal_language_ops (META-PATTERN-022, validates op-ids vs the
  deterministic universal_research_ops catalog), four_scope_coverage
  (META-PATTERN-023, all of local/chain/recursive/meta). Emits
  `analytics/public/pretick/<tick_id>/pretick_manifest.json` with
  top-level tick_id, **contract_id = recomputed compiler cid =
  start_tick(goal).contract_id** (daemon namespace), forecast_contract_id
  (forecast-pool slug, separate), consumes_surfaced, universal_ops, scopes.
  RC=2 unless all 8 ok.
- `src/ztare/gates/commit_membrane_daemon.py` — HARD gate in the
  `if is_close and _start_row is not None:` frozen-close branch (the only
  real authority, H7). Requires the per-tick manifest to exist, be
  COMPLETE, and mutually bind to the FROZEN SIGNED start row:
  manifest.tick_id==close.tick_id, manifest.contract_id==_sc (compiler
  cid), manifest.goal==frozen start goal. Miss/unreadable ⇒ oblig_fail ⇒
  existing quarantine path (fail-closed; no official F-row materialized).

**Cold pass #1 (bvs1b6d43, xhigh) = NO-GO. Acted on:**
- Angle 2 (CORRECTNESS BUG, fixed): start row contract_id is the
  compiler cid, not the forecast-pool slug; the original gate compared
  two id-spaces ⇒ would false-quarantine EVERY honest close. Fixed by
  recomputing the compiler cid in the runner via the same import the
  daemon uses; verified equal (2f91e9bfa40f8da2). Cold pass #2
  (b18zbkhdw) dispatched on the corrected version.
- Angle 1 (shallow steps, partially fixed): ns_residual_graph now
  substrate-normalizes + is REQUIRED for NS (no silent skip — this was
  a self-caught gaming path: the demo passed substrate "ns" and skipped);
  gp233 now requires a FRESH (<7d) ledger entry with non-empty next_lever
  (was: any file present).

### RESIDUAL — decisive, operator-inspected, NOT mid-session

These are deliberately NOT implemented mid-session (signed-row schema /
deploy-trust changes are the §3b class: own adversarial pass + operator
inspection before trust; mid-session reimplement under pressure is the
flagged anti-pattern):

R1. **Freeze more fields in the daemon-minted `start_tick` row**
    (cold Angle 2-deeper): add substrate, owner, gp230_question_hash,
    gp230_contract_sha256, consumes_surfaced to the signed start row;
    close checks the manifest AND the current forecast-pool contract
    file against that frozen snapshot. Closes "tools ran on the right
    tick but the forecast question was loose/unrelated."

R2. **Operator-pinned daemon tree** (cold Angle 3): the daemon repo
    copy is agent-editable; only the deployed instance (VPS, ztare
    identity) is the authority. Stamp the daemon code hash into the
    signed row; refuse dirty/unpinned verifier code. Agent proposes
    the patch; operator deploys it. This is the existing
    operator-inspection trust root made explicit, not new.

R3. **Symmetric POST-tick**: `posttick_runner` composing the 8 POST
    MECE legs (rd_tick_brief l.599-606) + a symmetric daemon gate.
    Pending (task #41).

R4. **Meso/macro forecast trigger for big decisions** (task #42):
    deterministic big-decision trigger (decision-changed /
    architecture-touching / multi-tick) ⇒ require a meso/macro GP-230
    contract; hook off post_tick_check.py --decision-changed.

R5. **Irreducible** (cold "still-left", accepted not laundered):
    vacuous mathematical consumption (BKM Icc-vs-Ico class) — receipts
    can be shape-correct yet semantically useless. Stays with
    break-only adversary + operator math review. The gate forces the
    pre-tick is EXECUTED on this tick's goal; it does not and cannot
    certify the insight is deep.

---

## v2 UPDATE (2026-05-18, post cold #2 + operator "no NS in daemon")

**Symmetric POST-tick built + daemon decoupled from NS:**
- `scripts/public/control/posttick_runner.py` — mirrors pretick_runner;
  HARD legs: pretick_bound (pre<->post symmetry), post_tick_check.py,
  micro_resolved (RESOLVED + prior codex bet, audited not performed),
  big_decision_forecast (--decision-changed ⇒ FRESH meso/macro
  MANDATORY — folds task #42). ADVISORY-recorded (not gated, honoring
  the don't-false-FAIL invariant): tier3_pattern_026, memory_touched.
  contract_id = SAME recomputed compiler cid ⇒ same un-forgeable bind.
- Daemon: a SYMMETRIC post-gate added next to the pre-gate; both bind
  manifest⇄frozen-signed-start-row on tick_id + compiler cid + goal +
  substrate; absent/INCOMPLETE/foreign ⇒ oblig_fail ⇒ quarantine.
- **NS DECOUPLED FROM THE DAEMON (operator catch):** the generic
  commit membrane must not know what "NS" is. The cold-#2 substrate-
  swap bypass is closed purely by GENERIC exact substrate binding
  (manifest.substrate == frozen signed substrate, alnum-normalized).
  The substrate→required-steps mapping lives only in the runner. All
  `_is_ns`/NS-alias/`ns_residual_graph`-name knowledge removed from
  commit_membrane_daemon.py.

**Cold #2 (b18zbkhdw) = NO-GO → addressed:** the substrate-swap
gaming path it found is closed by exact substrate binding (its stated
minimum-before-GO), implemented substrate-agnostically per operator.

**Self triple-check (no cold shot per operator; operator review is
the gate):** all 3 files py_compile + AST OK; pretick positive RC=0;
negative paths (bogus ops/scopes, namespace, substrate) fail-closed;
posttick fail-closed on unresolved contract; pretick_bound symmetric
binding verified True; daemon pre-gate predicate simulated — matched
start_row ⇒ no oblig_fail, every tampered axis (tick_id/cid/goal/
substrate) ⇒ the specific quarantine entry.

### RESIDUAL still open (operator-inspected, NOT mid-session)
R2. Operator-pinned daemon tree + signing keys outside agent write
    boundary; stamp daemon code hash into the signed row (deploy
    layer; the repo copy being agent-editable is expected — only the
    VPS instance under the ztare identity is the authority).
R6. Deepest identity binding: bind to the signed row /
    official_state_hash and freeze gp230_question_hash + consumes_
    surfaced in the start_tick row (cold #2: contract_id/cid is not
    the hardest identity). This is a signed-row SCHEMA change (§3b
    class) ⇒ its own spec + operator inspection, not mid-session.
R5. Irreducible: mathematical vacuity (BKM Icc-vs-Ico) — receipts
    can be shape-correct yet semantically useless ⇒ break-only
    adversary + operator math review. Unchanged; not laundered.

---

## v3 (2026-05-18): R5 over-claim REDUCED (operator: "meta-darwin the supposed irreducibles")

Re-audit found the cope: R5 ("math vacuity is human-only") was
laundering — `lean_proof_gate.run_lean_proof_gate` + the v33 organs
(vacuity / paraphrase / single-lemma / scalar-wrapper) ALREADY exist
and were NOT composed. Now composed as posttick_runner leg 5
`lean_faithfulness`: HARD (gate_passed = compile + axiom audit + v33
anti-laundering) when --thesis-path is declared; advisory + residual-
flagged (NOT asserted complete) when not declared.

Residual reduced to its true size:
- R5' (trigger-bind): a closure-claiming tick could omit
  --thesis-path ⇒ lean_faithfulness goes advisory. Forcing it needs
  the close's claimed substrate_class/outcome to MANDATE the thesis
  (R6-class deeper bind). Sent to Meta-Darwin, not asserted closed.
- R5'' (genuinely irreducible candidate): even a faithful non-vacuous
  proof of theorem T does not certify T IS the Clay statement. The
  per-tick-gateable part = pin the target-statement hash; the only
  truly irreducible part = whether the pinned target itself is the
  Clay problem (one-time human/community judgment, NOT per-tick
  gaming surface). Meta-Darwin to confirm/refute this decomposition.

---

## META-DARWIN VERDICT (bwdcoww2y, gpt-5.5 xhigh, 2026-05-18)

**NO-GO at artifact level. Idea NOT killed** (split honored: "forced
pre/post tick discipline is still the right shape"). Punch list:

F1 [CONFIRMED CORRECTNESS BUG, pre-existing, orthogonal to this work]
   tick_close.py:284 passes the forecast-pool SLUG as
   close.contract_id; :291 passes `--goal a.tick_row`. Daemon b1djdevru
   check (commit_membrane_daemon.py:820) requires close.contract_id ==
   frozen COMPILER cid ⇒ every honest close via tick_close.py would
   quarantine, and close goal != frozen goal. Touches a shipped cold-
   reviewed wrapper + the signed close path ⇒ OPERATOR-ROUTED, not a
   mid-session unilateral edit. Fix dir: tick_close.py must send the
   frozen compiler cid (or daemon accept slug + separately bind cid);
   stop passing tick_row as goal.
F2 pre-tick still has static catalog-presence checks (menu route not
   composed from goal; `g` unused; pattern/anti-pattern chain not
   applied-to-this-tick). Falsifier: unrelated goal + valid ops/scopes
   ⇒ COMPLETE.
F3 forecast identity presence-bound not tick-bound (no layer=micro /
   created_by==owner / in-window / question-hash / codex bet / start-
   row freeze).  [signed-row SCHEMA class]
F4 posttick micro_resolved wired to WRONG forecast schema: real
   outcomes are analytics/public/forecast_pool/outcomes/<id>.json and
   codex under forecasts/<contract>/codex.json (NOT contracts/). This
   is why TRIPLECHK micro_resolved was INCOMPLETE. [CHEAP-FIX-NOW]
F5 lean_faithfulness no-thesis advisory is a live closure-claim
   bypass — must trigger from close.f_row_body/typed signals, not
   caller honesty. [CHEAP-FIX-NOW, daemon-side]
F6 official F-row content not semantically gated at the daemon
   (writes close.f_row_body after obligation gates; no check it names
   frozen start hash / contract / surfaced id / target hash / Lean
   receipt). Falsifier: valid pre/post manifests + unrelated close
   body ⇒ F-row materialized.  [daemon-semantic-gating, schema class]

Residual Meta-Darwin: R2 IRREDUCIBLE-narrowly (deploy) BUT manifest
provenance unsolved (daemon reads agent-written manifests:856 — needs
operator/broker-signed manifest hash or VPS-owned receipt ledger);
R5' CHEAP-FIX-NOW; R5''/R6 CHEAP-FIX-NOW (tick_id+cid+goal+substrate
NOT enough — bind specific micro contract/question/surfaced/owner/
F-row semantics); R5''' IRREDUCIBLE only after a target-statement-
hash registry (per-tick part mechanizable; "is this registry entry
the Clay problem" = one-time human curation).

Predicted residual after ALL fixes: receipt-shaped compliance w/o
substantive progress (weak targets / vacuous decompositions) — needs
break-only adversary + operator-inspected target registry + signed
receipts tied to exact frozen start state. NOT solvable by more
self-attestation.

### Sequencing (operator-routed; trust root = operator inspection)
NOW (local, no schema change): F4 (schema-correct outcome/codex
paths), F5 (daemon Lean trigger from close text).
SPEC for operator inspection + own adversarial pass (signed-row
SCHEMA / shipped-wrapper / daemon-semantic class — the §3b class,
NOT mid-session): F1, F3, F6, R5''/R6, R2 manifest-provenance,
R5''' target registry.
IRREDUCIBLE: "is the registry target the Clay problem" (one-time
human) + receipt-shaped-compliance (break-only adversary + operator).

### CHEAP-FIX-NOW applied + verified (2026-05-18, posttick_runner-local only)
F4 DONE: micro_resolved rewired to the REAL schema —
   outcomes/<id>.json (non-voided + resolved_at) + forecasts/<id>/
   codex.json (forecasted_at), ordering codex<resolve. Verified on
   the real route_1 contract (was false-INCOMPLETE; now resolved=
   True, codex_before_resolve=True).
F5 DONE (partial, the goal-detectable half): lean_faithfulness no-
   thesis is HARD FAIL when the FROZEN goal claims a formal closure
   (clay/theorem/lean/sorry-free/...); honest N/A only for genuine
   non-closure goals. Verified both branches. RESIDUAL (claims
   detectable ONLY from close.f_row_body, not goal) ⇒ daemon-side
   trigger, in the operator-routed schema bundle below.

### OPERATOR-ROUTED SCHEMA BUNDLE (NOT mid-session — §3b class)
Spec for operator inspection + its own adversarial pass before trust;
all touch the signed start-row schema / a shipped cold-reviewed
wrapper / daemon F-row semantics:
- F1 tick_close.py↔daemon namespace+goal (pre-existing correctness
  bug; honest closes via the sanctioned wrapper would quarantine).
- F3 freeze forecast_contract_id + contract sha256 + question_hash +
  consumes_surfaced + layer + created_by into the signed start row;
  compare in pre/post/close.
- F6 daemon F-row-body semantic gate (must name frozen start hash /
  contract / surfaced id / target hash / Lean receipt).
- F5-daemon close.f_row_body Lean-claim trigger.
- R2 manifest provenance (operator/broker-signed manifest hash or
  VPS-owned receipt ledger; daemon currently reads agent-written
  manifests).
- R5''' operator-approved target-statement-hash registry.
IRREDUCIBLE: "is the registry target the Clay problem" (one-time
human curation) + receipt-shaped-compliance (break-only adversary +
operator inspection).

---

## SELF-META-DARWIN of the schema bundle (operator-ordered, before gpt-5.5; 2026-05-18)

Ran my OWN adversary on the F1/F3/F6/F5-daemon/R2/R5''' implementation
BEFORE external review. It caught 3 real defects in my own work:

M-D1 R2-dead? — CHECKED FALSE: propose.py:281 passes transition_type
   through with no allowlist ⇒ `manifest_receipt` is accepted. R2
   live. (runners RC=3 fail-closed when no daemon signs the receipt;
   RC=0 with a live daemon — verified.)
M-D2 F3 DORMANT [honest finding, NOT fixed by faking]: no start_tick
   emitter passes forecast_contract_id, so forecast_identity_frozen
   is always False ⇒ all F3 close-side checks are skipped. The
   daemon-side freeze + close enforcement are correct and fail-safe
   (only enforce when frozen, no false-FAIL), but F3 is NOT load-
   bearing until a start emitter declares the forecast id. Flagged,
   not fake-wired (faking the wiring would be the laundering).
M-D3 F6 FALSE-FAIL [SELF-CAUGHT + FIXED]: required the compiler cid
   substring in the F-row body — the cid is an internal hash never
   present in agent-authored markdown ⇒ would have quarantined
   EVERY honest close (same class as the original namespace bug).
   Fixed: F6 now binds tick_id (the row IS selected by it) +
   forecast slug (tick_close H3a already requires it in the row) —
   tokens honest bodies legitimately contain.

Honest residuals carried into the gpt-5.5 review (NOT claimed solved):
- F3 dormant pending a start_tick emitter (M-D2).
- R5''' registry is agent-writable ⇒ inherits the SAME provenance
  residual as R2-deep (per-tick "must be registered" is enforced;
  registry tamper-resistance = operator/deploy trust, unsolved).
- R2 makes manifests tamper-EVIDENT (post-receipt edit / forged-
  COMPLETE-without-receipt fail closed) but a COMPLETE-but-shallow
  manifest still earns a receipt ⇒ the reviewer's predicted
  "receipt-shaped compliance" residual stands (break-only adversary
  + operator target curation; correctly out of mechanizable scope).

---

## ROUND-2 FIXES (cold bq4z7midf NO-GO) + SELF-META-DARWIN (2026-05-18)

Verdict was: Artifact NO-GO / Idea GO-WITH-CHANGES; single irreducible
= schema-complete-insight-empty (faithfulness+significance). Fixes:
- F2 crash FIXED (posttick `--decision-changed` used undefined `fp`;
  now `_fpr/"contracts"`).
- F3-soundness FIXED (daemon start-row + manifest-receipt lookups now
  use FULL chain_valid, not signature-over-hash alone).
- F5 locale FIXED (manifests written encoding="utf-8").
- F1-remote FIXED (tick_close `_frozen_start` falls back to propose's
  read-only base64-cat of the VPS ledger + LOCAL chain_valid when
  remote-enforce; no false-refuse of laptop→VPS honest closes).
- F4 MECE: tier1_closure_claim now HARD for closure-adjacent ticks
  (deterministic linter `check <artifact>`); tier3 multi-LLM stays
  advisory (provider outage must not false-FAIL); CLI corrected.
- F3-wiring: created scripts/public/control/start_tick.py — the
  sanctioned OPEN wrapper (none existed) that passes
  forecast_contract_id so the daemon freezes the forecast identity.
- R5''' provenance: agent-writable json REMOVED from the trust path;
  replaced by a daemon-signed, chain-valid `target_register`
  transition (operator-attested env ZTARE_OPERATOR_TARGET=1).
- Q&A persisted: 4 cold reviews archived to analytics/public/
  external_prover_responses/ + the external_prover ledger.

SELF-META-DARWIN of round-2 (honest, NOT claimed solved):
SM1 tier1_closure_claim HARD may FALSE-FAIL — I did not verify the
   Tier-1 linter's pass criteria; if it demands a strict
   ANTI-PATTERN-012 block an honest closure artifact may not have,
   this over-trips. Needs the linter's real pass semantics verified
   before trusting the HARD.
SM2 F3 NOT FORCED — start_tick.py exists but nothing forces ticks to
   open through it (no analog of the tick_close next-tick punisher
   for OPEN). F3 is live-when-used, still optionally-dormant.
SM3 statement-hash binding NOT implemented — the closure check
   verifies a registered hash is CITED in the body, NOT that the
   Lean proof's actual theorem statement hashes to it. The
   vacuity→(faithfulness) collapse does NOT yet hold; an agent can
   cite a registered hash while proving a weaker theorem. KEY open.
SM4 target_register operator-gating = env/flag attested + ledgered,
   NOT cryptographically operator-only (same R2-class residual as
   admin_retire; honest, acknowledged).
SM5 F1-remote imports propose internals (_ssh_base, VPS_STORE) —
   coupling/fragility if propose refactors.

---

## ROUND-3 (cold b5upqb5kz NO-GO) + literature + self-MD (2026-05-18)

Cold round-2 verdict: Artifact NO-GO / Idea GO-WITH-CHANGES; irreducible triple-confirmed (schema-complete/insight-empty) + arXiv-confirmed open (Do LLMs Game Formalization?). Implemented:
- SM3 (the crux, ProofFlow/Aristotle move): lean_proof_gate emits per-theorem canonical statement hashes; posttick manifest carries proven_statement_hashes; daemon close requires claimed_target ∈ registered ∩ PROVEN. Cite-a-hash-while-proving-weaker is blocked; verified.
- SM2 forcing: daemon start_tick QUARANTINES a research tick without a daemon-hashable forecast contract; close-side punisher for legacy pre-SM2 start rows. start_tick.py is now decisive, not laundering.
- F1 remote transport: manifest_receipt CARRIES manifest bytes (manifest_b64); daemon persists them to OFFICIAL/manifests and hashes the RECEIVED bytes; close reads daemon-owned copy (_daemon_manifest). Laptop→VPS no longer false-fails.
- F6 (round-2): exactly-64-hex target hashes; F-row provenance bind = tick_id + forecast slug (NOT the internal cid — that earlier false-FAIL stays fixed).
- F4 (partial): big_decision_forecast bound to owner. Tier-3 multi-LLM stays advisory (provider-outage HARD would false-FAIL). Steelman-kill receipt = NAMED REMAINING SPEC (a new subsystem; not built mid-grind — P15).
- Finding 5 regression REVERTED: lean_faithfulness HARD now fires only on Lean-specific tokens; generic "theorem/closure/proven" no longer false-FAILs non-Lean analysis closures.
- Docs: Pattern 14 prior-art updated with the concurrent 2026 convergence (PunkGo/Aegis/IETF-AAT/Verifiability-First/TraceGuard/EvaluatorStressTest/ProofFlow) + the 4 adopt items; epistemic_principles.md Part IV (P15 gate-treadmill incl. paper-2 parameterless promotion-contract meta-runner; P16 the faithfulness limit). Q&A archived to external_prover_responses/ + ledger.

SELF-MD round-3 (caught + FIXED before submit):
- A: _THM_SIG_RE split on the first `:` ⇒ mis-parsed binders like `(x:T)` ⇒ mis-hash. FIXED: hash the whole signature (name→`:=`/`by`), no internal `:` split. Verified on a real binder theorem.
- B: target_register hand-hashed value ⇒ operator/prover normalization divergence ⇒ SM3 brittle (would false-FAIL honest faithful proofs). FIXED: target_register prefers statement_text; the daemon canonicalizes+hashes via the SAME canonical_statement the Lean gate uses. PARITY verified.

Honest remaining (NOT claimed solved): Finding-4 steelman-kill receipt (named spec, not built); target_register/registry operator-gating still env+flag attested = R2-class (deploy-layer, acknowledged); SM3 is the SYNTACTIC half only — alpha/defeq/notation differences are not collapsed (P16: semantic equivalence to the informal Clay problem stays human). Submitted to cold Meta-Darwin (round-3).
