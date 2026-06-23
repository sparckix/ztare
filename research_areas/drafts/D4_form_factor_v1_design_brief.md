# ZTARE Product Surface — v1 Design Brief

**Status:** v1.2 refresh, derived from `research_areas/private/seams/interfaces/D4_distribution_form_factor_seam.md` (converged 2026-04-11) and updated against the 2026-06 project-intake, source-check, autoresearch-trace, loop-admission, graph/forecast read-model, and review-artifact surfaces. This is a designer-facing input document, not a kernel spec. It is written to be handed to a UI/UX designer for wireframing and design-system work.

**Audience:** UI/UX designer (external or internal). Assumes no ZTARE background but does assume familiarity with product design for technical review tools.

**What this brief is not:** an implementation spec, a code architecture document, or a feature list. It is a frame for design work — what surfaces exist, who uses them, what jobs they do, and what visual/interaction language must hold across them.

---

## 1. The product in one paragraph

ZTARE is a local, file-backed workbench for bounded claims. A user creates or opens a project, states a claim, attaches sources, checks whether the evidence surface is admissible, runs preflight and in-loop validation when the project is ready, and exports an auditable claim record. The core value is that ZTARE separates generation, judgment, provenance, and claim status so a human can see what is proposed, what is being challenged, what evidence is missing, and what can safely be said. The product surface being designed in v1 is the place where a human reviewer directs that loop without losing the file-backed audit trail.

## 1.1 ICP and value proposition

The first customer profile is not "anyone who chats with an LLM." The first
user is a technical founder, researcher, analyst, or serious independent
reviewer who already has local files, a bounded question, and a decision that
would be harmed by a plausible but unsupported answer. They are willing to use
an inspectable local tool if it tells them:

1. what claim is currently allowed;
2. what source or evidence made that claim admissible;
3. what the system challenged or demoted;
4. what exact falsifier or missing source would change the verdict; and
5. which command, file, or receipt proves each visible state.

The v1 customer value proposition is:

> Turn a messy local claim-and-evidence project into an auditable verdict and
> next falsifier, without asking the user to trust a chat transcript.

The surface can be general-purpose across science, operations, strategy,
markets, policy, and proof work because the object model is general:
`project -> bounded claim -> sources/evidence -> readiness -> adversarial
check -> verdict/demotion -> next falsifier -> export`. The interface should
not become general-purpose by becoming an unbounded assistant surface. It should stay
general-purpose by making that object model reusable across domains.

The near-term wedge is the forensic workbench. Didactic judgment coaching is
valuable, but it is not the first adoption bet unless a real teaching channel
is live. Broad agent delegation, background swarms, team task management, and
org governance are separate control-plane problems.

## 2. The surface

**One surface, two modes.** v1 is a single product with a hard mode switch between two user experiences that share the same underlying engine, the same objects (projects, bounded claims, source/evidence state, verdicts), and the same file layer, but foreground different affordances.

- **Forensic mode** (primary design target) — the in-loop claim and evidence workbench. Feels investigative. The user is a reviewer working a bounded project through source checks, intake validation, trace readiness, preflight, in-loop run state, verdict/demotion, and export. The workflow is: create or open project, inspect claim and sources, repair blockers, run preflight, launch the next admissible in-loop action, inspect loop history and verdicts, export a review artifact.
- **Didactic mode** (secondary design target) — the Judgment Coach. Feels teaching-first and fast. The user is a student, instructor, trainer, or diligence reviewer who wants to learn how to interrogate arguments rather than produce them. The workflow is: paste an argument, detect the failure family, surface the killer question, understand why it is the killer question.

Both modes operate on the same underlying objects. The mode switch is not a "product switch" — it is a change in which affordances are surfaced and which are pruned, plus a shift in visual and interaction language.

**Deferred out of v1:** a supervisor / principal cockpit for routing work across multiple concurrent programs, enforcing governance, and auditing approvals. Orbit and cognitive-firm-style control surfaces can own that broader role/mandate/task-management plane. The ZTARE v1 workbench should stay focused on the in-loop project/claim/evidence surface. Reopen cockpit design work only after the workbench v1 proves it can reduce first-use friction without hiding files, commands, receipts, or authority boundaries.

## 3. Primary users (per mode)

**Forensic mode:**

- Reviewer / analyst — building and stress-testing a bounded claim for their own work
- Founder — stress-testing a strategic or product claim before committing
- Researcher — running adversarial loops on a hypothesis

Primary user characteristic: comfort with file-based, inspectable systems. Willing to look at artifacts and provenance. Does not want a chatbot.

**Didactic mode:**

- Student — learning to interrogate arguments
- Instructor — teaching judgment through worked examples
- Trainer — running a workshop
- Diligence reviewer — fast-scanning an argument for its failure family before deep work

Primary user characteristic: wants to learn or teach a *method*, not produce output. Will accept more guidance and more visual scaffolding than the forensic user.

## 4. Jobs-to-be-done

### Forensic mode

1. Create or open a project
2. State a bounded claim and the question it is meant to answer
3. Attach raw sources and compile or index the evidence surface
4. See whether the intake is ready, blocked, malformed, stale, or out of scope
5. Inspect the trace/kernel-entry contract and source/evidence blockers
6. Run preflight before spending an in-loop run
7. Launch the next admissible in-loop action when readiness gates pass
8. Inspect loop history, verdicts, demotions, next falsifiers, and evidence links
9. Export a review artifact or claim record that another human can audit
10. Return to the project later and pick up from the latest file-backed state

### Didactic mode

1. Paste or import a target argument
2. See the failure family the argument falls into, explained in plain language
3. See the single "killer question" that collapses the argument if the user cannot answer it
4. See a worked example of the same failure family from a corpus of teaching notes
5. Optionally, take a short interactive drill on that failure family

## 5. Shared design principles (hold across both modes)

These constraints are central. Violating them breaks the product's core claim.

1. **Evidence-first, not chat-first.** The interaction metaphor is not a chatbot. The UI foregrounds provenance, weakest links, and artifacts. Where the system responds to the user, it does so in the form of structured objects the user can inspect, not in the form of a free-text conversation.

2. **Generation and judgment must remain visually distinct.** ZTARE's core claim is that producing an argument and interrogating an argument are different activities. The surface must preserve that distinction. A user should never be confused about whether they are looking at something the engine *produced* or something the engine is *attacking*.

3. **Local-first inspectability.** The system's credibility comes from inspectable files and artifacts the user can read directly, not from invisible cloud state. v1 is designed to run locally. The UI must treat "show me the underlying file" as a first-class affordance, not an advanced/hidden one.

4. **Teaching and operating are related but not identical.** The didactic mode should feel didactic and fast. The forensic mode should feel investigative and careful. Do not try to collapse them into one tone — they are intentionally different experiences on the same engine.

5. **No governance UI in v1.** Do not let the supervisor / principal cockpit leak into either mode. Routing work across programs, approvals, audit trails — all of that is deferred. If a feature is motivated by governance rather than by the in-loop claim/evidence workbench, it is out of scope for this brief.

## 6. What is shared across modes (common surface)

- **Object model.** Both modes operate on the same underlying objects: project, bounded claim, source/evidence state, intake readiness, trace/kernel-entry contract, run/preflight receipt, verdict/demotion, next falsifier, and exportable review artifact. The visual representation of these objects must be recognizable across modes even when the layout differs.
- **File surface.** Both modes use the same local file layer. "Show me the raw file" should look and behave the same in both modes.
- **Typography and color base.** A single design system with shared type, color, spacing, and iconography. Mode differentiation is layered on top, not through a second design system.
- **Mode switch affordance.** The user must always know which mode they are in and must be able to switch cleanly. The switch should feel purposeful, not like tabs.

## 7. What must be visually and behaviorally distinct across modes

- **Information density.** Forensic mode is dense. It shows verdicts, iteration history, the current weakest link, the attack surface, the evidence compiler state. Didactic mode is sparse. It shows one argument, one failure family, one killer question, one worked example.
- **Tone of copy.** Forensic mode speaks in the language of investigation ("weakest link," "attack surface," "iteration 7 result"). Didactic mode speaks in the language of teaching ("this argument is vulnerable to X," "the question that collapses it is Y," "here is how a strong version would answer that question").
- **Pacing.** Forensic mode is user-driven — the reviewer drives the loop and inspects at their own pace. Didactic mode is more structured — the user is walked through a short sequence, not dropped into a workbench.
- **Affordance count.** Forensic mode exposes many affordances (inspect, re-run, compare, export, step back). Didactic mode exposes few (understand, next example, drill).
- **Visual register.** Forensic mode reads as a review tool: dense enough for evidence work, close to the file surface, and quiet enough for repeated use. Didactic mode reads as an educational surface: more whitespace, more guidance, less instrument density. Think "editor vs. textbook" rather than "dark mode vs. light mode."

## 8. Information architecture (high level)

v1 needs to represent at least these object types in the UI, shared across modes:

- **Project** — a named container for a bounded claim, sources, evidence, run history, and exports
- **Bounded claim** — the claim being generated, stress-tested, demoted, or exported
- **Source / evidence state** — raw inputs, source-index receipts, evidence freshness, gaps, and blockers
- **Intake readiness** — whether the project can enter the in-loop kernel, and why not if blocked
- **Trace / kernel-entry contract** — the read-only route from project state to admissible in-loop action
- **Preflight / loop-admission receipt** — the command output that proves a run can safely start or must stop
- **Run history** — preflight and in-loop run attempts, their state, verdict, and artifact links
- **Verdict / demotion** — the current claim status, weakest blocker, and allowed bounded wording
- **Next falsifier** — the concrete check or evidence item that would change the claim state
- **Review artifact** — a claim record, report, memo, or evidence-atlas dossier another human can inspect
- **Failure family** — a named category the argument's weakness falls into
- **Killer question** — the single question that, if unanswered, collapses the argument
- **Worked example** — a teaching-note-shaped artifact showing how a failure family has played out in a real case

Forensic mode primarily surfaces: project, bounded claim, source/evidence state, intake readiness, trace/preflight state, run history, verdict/demotion, next falsifier, and export.

Didactic mode primarily surfaces: bounded claim or argument, failure family, killer question, worked example.

The same Project and Bounded Claim objects can be opened in either mode. Opening an existing workbench project in didactic mode shows a teaching-framed view of its current verdict. Opening a didactic session in forensic mode shows the underlying project, evidence, trace, and run state.

## 9. First controller / screen contract

This is the first narrow controller contract for v1. It is not a mandate to
build UI now. It says which current repo surfaces the first interface must read
or launch, and what every screen must prove before it can show a ready state.

### 9.1 Project browser

Purpose: let a user choose an existing project or start the smallest admissible
new one.

Reads:

- `projects/<project>/`
- `rubrics/<rubric>.json`
- `examples/project_packets/*.json` for demo/fixture projects
- project prep-ledger rows when intake is blocked on source or artifact work

Primary actions:

- open project
- create or open intake
- open raw/source and workspace folders
- start the guided fresh-project flow

Every row must show one of: intake file, rubric file, project folder, prep
ledger row, or an explicit missing-surface warning.

### 9.2 Claim and intake inspector

Purpose: make the bounded claim, non-claims, evidence refs, expected command,
and missing-reference falsifier visible before any run can start.

Reads / launches:

- `ztare project intake validate --path <intake.json>`
- `ztare project intake falsify --path <intake.json> --remove-ref ...`

Primary states:

- `ready`
- `malformed`
- `missing_source`
- `missing_evidence`
- `out_of_scope`
- `stale`

The launch button is disabled unless the intake state is ready and the
underlying receipt is visible.

### 9.3 Source and evidence state

Purpose: show whether raw sources, source typing, evidence compilation, and
artifact binding are present enough for the kernel-entry check.

Reads / launches:

- `ztare project source-check --project <project> --json`
- `ztare project source-index --help` as the command family for source-index receipts
- `ztare project evidence-bind --help` as the command family for output/evidence binding
- source freshness, evidence-gap, and output-binding receipts when present

The screen should distinguish "source exists", "source is typed", "evidence is
compiled", and "evidence is bound to the claim." A source-ready project is not
automatically loop-ready.

### 9.4 Trace and kernel-entry console

Purpose: show the read-only handoff from project state to admissible in-loop
action.

Reads / launches:

- `ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --json`

Visible fields:

- readiness status
- `kernel_entry.can_enter`
- source/evidence blockers
- graph and forecast read-model summaries when present
- loop-admission receipt status
- exact next command

The console must not synthesize a ready state from prose. It renders the trace
payload and links to the command that produced it.

### 9.5 Preflight and bounded-run launch

Purpose: let the user run the cheapest admissibility check first, then launch
only when the trace allows it.

Reads / launches:

- `ztare autoresearch run --project <project> --rubric <rubric> --intake <intake.json> --preflight-only`
- `ztare autoresearch run --project <project> --rubric <rubric> --intake <intake.json> ...`

Rules:

- preflight is available when intake validation passes and source/evidence
  prerequisites are inspectable;
- full run is disabled unless the latest trace says the project can enter the
  kernel, or the user explicitly accepts a visible blocked-run state;
- model/provider selection is an expert disclosure, not the first screen;
- launch output must write or link a receipt before the UI changes state.

### 9.6 Run history and verdict view

Purpose: make loop history, generated candidates, gate failures, demotions,
next falsifiers, graph focus, and forecast/prediction read-model rows visible
without requiring terminal archaeology.

Reads:

- autoresearch trace and projection outputs
- workspace run artifacts
- loop-admission receipts
- review artifacts or claim-register rows when exported
- graph carrier and prediction-contract read models when present

The verdict view must keep generated material and judgment material visually
separate. A demotion is a first-class result, not an error state.

### 9.7 Export

Purpose: produce an auditable claim record another human can inspect.

Minimum export contents:

- bounded claim
- non-claims
- evidence refs
- source/evidence state
- latest trace status
- verdict or demotion
- next falsifier
- file/command/receipt links for every visible assertion

The first export can be a local review artifact. It does not need accounts,
sharing, hosting, or a dashboard backend.

### 9.8 Acceptance tests for any prototype

A prototype is not useful unless it passes all of these:

1. A new user can open `demo_claims`, see a missing-evidence blocker, run
   preflight, and find the exact file or receipt behind every visible row.
2. A fresh project can be created without entering the loop prematurely.
3. A blocked intake disables launch and names the missing surface in user-facing
   language.
4. A ready intake can run preflight and produce a visible loop-admission
   receipt.
5. Generated claims, judge/gate verdicts, demotions, and exports are visually
   distinct.
6. The UI does not hide the filesystem: every row has a file path, command,
   receipt, review-artifact link, or explicit no-receipt warning.
7. Supervisor, principal, and background-agent controls are absent from v1.

### 9.9 First prototype slice

The first prototype should be a falsifiable UX bet, not a general GUI. Its
question is:

> Can a local workbench make the current kernel easier to adopt than the CLI
> path alone while preserving file-backed provenance?

Use one of two fixtures:

- `demo_claims` for the smallest public on-ramp: ready intake, missing-ref
  falsifier, preflight, and demotion/export inspection.
- `ops_root_cause_diagnosis_demo` for the first customer-shaped path: typed
  organization sources, source/evidence readiness, trace status, preflight
  launch, provider/runtime risk, and blocked report support.

The prototype should implement only this flow:

```text
open project -> inspect bounded claim -> inspect source/evidence state
-> read trace/kernel-entry status -> run preflight
-> inspect loop-admission receipt -> inspect verdict/demotion/export state
```

Required controller calls:

- list/open project and rubric paths;
- validate and falsify the intake file;
- run source-check and show source-index/evidence-binding receipts when present;
- run autoresearch trace in JSON mode;
- run preflight-only launch;
- show run history, verdict/demotion state, report-support status, and export
  artifact links when present.

Every visible row must carry one of:

- file path;
- command;
- receipt hash or status;
- review artifact link;
- explicit no-receipt warning.

The first prototype must not include accounts, sharing, hosted storage,
background swarms, supervisor/principal routing, billing, chat history, or
generic task management. Text entry is allowed only for bounded object edits:
claim text, source note, evidence gap note, refinement proposal, or export
note.

Measure the slice by workflow, not visual polish:

- time to first bounded project;
- time to first blocker;
- time to preflight;
- time to export or blocked-export explanation;
- percentage of visible rows with inspectable provenance;
- whether generated material and judgment/demotion material are visually
  distinct.

Current implementation baseline:

- `forensic-workbench/` is a React/Vite local web app, not a static mockup.
- Static mode reads `forensic-workbench/public/workbench_snapshot.json`.
- Live mode uses `scripts/public/control/forensic_workbench_server.py` as a
  thin local API for `/api/projects`, `/api/snapshot`, and `/api/review`.
- The local API reads project-local intakes and public example intakes, builds
  fresh snapshots from the same CLI/read-model surfaces as static mode, and
  writes the same review receipt shape as
  `ztare forensic-workbench apply-review`.
- Startup may fall back to the static snapshot when the API is absent. Once the
  API is present, project-specific refresh failures must stay visible instead
  of silently swapping in stale static data.

## 10. Trust posture

The product is local-first. The user's trust in the product comes from:

- Being able to read the files the engine is operating on
- Being able to see what the engine just did (iteration history, provenance)
- Being able to inspect why a verdict is what it is (weakest link, failing criterion, evidence cited)
- Being able to open the command, receipt, hash/status, or review artifact behind every visible row
- Not being asked to trust invisible cloud state

The design must reflect this. Hiding state behind chat or behind opaque "done" affordances will break the trust posture.

## 11. Questions for the designer

Questions a designer is expected to answer during design work, not before:

1. What does the mode switch look like, physically? A literal toggle? A different entry point? A different top-bar surface? The decision is not architectural — it is a design judgment about how prominent the mode change should be.
2. How should the shared object model be visually unified across modes? The same bounded claim must be recognizable in both modes without looking identical.
3. In forensic mode, what is the single most important object on screen at any given moment — the current verdict? the weakest link? the iteration history? — and how does that change as the user moves through a run?
4. In didactic mode, what is the right pacing for the "one argument → one failure family → one killer question" flow? Is it a single screen or a short wizard?
5. What is the minimum shared design system that lets the modes feel related without collapsing into sameness?
6. What affordances belong in the default surface and what belongs behind "expert" disclosure? The rule of thumb is: if it is about *the method working correctly*, it belongs default. If it is about *optimizing or tuning the method*, it belongs expert.

## 12. Out of scope for v1

- Supervisor / principal cockpit (deferred, see §2)
- Orbit replacement or broader agent/task-management UI
- Multi-user collaboration
- Cloud-hosted version
- Billing, accounts, team management
- Any feature motivated by governance rather than by the in-loop claim/evidence workbench
- Mobile / tablet surfaces
- A marketing site

## 13. Explicit assumption the maintainer can override

This brief assumes the case-method teaching-judgment distribution channel is **notional** — there is interest in using ZTARE's didactic mode in a case-method teaching context, but there is no committed teaching slot this semester or next. Under that assumption, forensic mode is the primary design target and didactic mode is secondary within the same surface.

If the maintainer has evidence that the channel is **live** — a real teaching slot with a real student population using didactic-mode output this semester or next — the ordering flips: didactic mode becomes the primary design target and forensic mode becomes the secondary mode within the same surface. Everything else in this brief is stable under the flip: the modes-of-one-surface decision holds, the shared design principles hold, the object model holds, the deferred supervisor cockpit holds. Only §2, §3, §4, and the visual-register guidance in §7 need to be reversed on which mode is "primary."

The maintainer should confirm this assumption before the designer begins wireframing.

## 14. Reference files

Background the designer may want to read:

- `research_areas/private/seams/interfaces/D4_distribution_form_factor_seam.md` — the debate that produced this brief
- `research_areas/private/seams/interfaces/D3_layer3_surfacing_seam.md` — the earlier seam for the didactic / teaching surface
- `research_areas/private/product-strategy/local_workbench_productization.md` — the earlier workbench productization note (gitignored; maintainer can share directly)
- `config/renderers/field_manual.md` and `config/renderers/teaching_note.md` — existing renderer conventions for the teaching surface

These are background, not requirements. The brief itself is the canonical input to design work.

![alt text](Gemini_Generated_Image_l7vi1jl7vi1jl7vi.png)
