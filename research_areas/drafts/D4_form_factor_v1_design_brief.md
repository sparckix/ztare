# ZTARE Product Surface — v1 Design Brief

**Status:** v1 brief, derived from `research_areas/seams/D4_distribution_form_factor_seam.md` (converged 2026-04-11). This is a designer-facing input document, not a kernel spec. It is written to be handed to a UI/UX designer for wireframing and design-system work.

**Audience:** UI/UX designer (external or internal). Assumes no ZTARE background but does assume familiarity with product design for technical/operator tools.

**What this brief is not:** an implementation spec, a code architecture document, or a feature list. It is a frame for design work — what surfaces exist, who uses them, what jobs they do, and what visual/interaction language must hold across them.

---

## 1. The product in one paragraph

ZTARE is an adversarial hardening engine for arguments. You give it a thesis — a claim about a company, a policy, a scientific model, a business — and it runs a structured attack loop that surfaces the weakest points, generates falsifications, and produces a legible verdict you can defend in writing. The core value is that ZTARE separates *producing* an argument from *interrogating* it, and makes the interrogation cheap enough to do systematically. The product surface being designed in v1 is the place where a human operator sits in front of this engine and directs its attention.

## 2. The surface

**One surface, two modes.** v1 is a single product with a hard mode switch between two user experiences that share the same underlying engine, the same objects (theses, evidence, verdicts), and the same file layer, but foreground different affordances.

- **Forensic mode** (primary design target) — the thesis-hardening workbench. Feels investigative. The user is an operator working a real argument through a real adversarial loop. The workflow is: create project, compile evidence, run hardening loops, inspect verdicts and weakest links, export a memo or report.
- **Didactic mode** (secondary design target) — the Judgment Coach. Feels teaching-first and fast. The user is a student, instructor, trainer, or diligence reviewer who wants to learn how to interrogate arguments rather than produce them. The workflow is: paste an argument, detect the failure family, surface the killer question, understand why it is the killer question.

Both modes operate on the same underlying objects. The mode switch is not a "product switch" — it is a change in which affordances are surfaced and which are pruned, plus a shift in visual and interaction language.

**Deferred out of v1:** a supervisor / principal cockpit for routing work across multiple concurrent programs, enforcing governance, and auditing approvals. This surface is real and will be needed eventually. It is not part of the v1 design. Reopen design work on this when (a) the workbench v1 ships and (b) more than one concurrent program is being run through the supervisor.

## 3. Primary users (per mode)

**Forensic mode:**

- Operator / analyst — building and hardening a thesis for their own work
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
2. Upload raw evidence and compile it into structured form
3. State a thesis
4. Run a hardening loop against the thesis
5. Inspect the current verdict, the weakest link, and the attack surface
6. Step through iterations of the loop and see how the thesis is being pressured
7. Export a memo, report, or artifact that another human can review
8. Return to the project later and pick up where it was left

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

5. **No governance UI in v1.** Do not let the supervisor / principal cockpit leak into either mode. Routing work across programs, approvals, audit trails — all of that is deferred. If a feature is motivated by governance rather than by the core hardening loop, it is out of scope for this brief.

## 6. What is shared across modes (common surface)

- **Object model.** Both modes operate on the same underlying objects: thesis, evidence, falsification suite, verdict, weakest link. The visual representation of these objects must be recognizable across modes even when the layout differs.
- **File surface.** Both modes use the same local file layer. "Show me the raw file" should look and behave the same in both modes.
- **Typography and color base.** A single design system with shared type, color, spacing, and iconography. Mode differentiation is layered on top, not through a second design system.
- **Mode switch affordance.** The user must always know which mode they are in and must be able to switch cleanly. The switch should feel purposeful, not like tabs.

## 7. What must be visually and behaviorally distinct across modes

- **Information density.** Forensic mode is dense. It shows verdicts, iteration history, the current weakest link, the attack surface, the evidence compiler state. Didactic mode is sparse. It shows one argument, one failure family, one killer question, one worked example.
- **Tone of copy.** Forensic mode speaks in the language of investigation ("weakest link," "attack surface," "iteration 7 result"). Didactic mode speaks in the language of teaching ("this argument is vulnerable to X," "the question that collapses it is Y," "here is how a strong version would answer that question").
- **Pacing.** Forensic mode is user-driven — the operator drives the loop and inspects at their own pace. Didactic mode is more structured — the user is walked through a short sequence, not dropped into a workbench.
- **Affordance count.** Forensic mode exposes many affordances (inspect, re-run, compare, export, step back). Didactic mode exposes few (understand, next example, drill).
- **Visual register.** Forensic mode reads as an operator tool: monospace-adjacent, instrument-panel-like, close to the file surface. Didactic mode reads as an educational surface: more whitespace, more guidance, less instrument density. Think "editor vs. textbook" rather than "dark mode vs. light mode."

## 8. Information architecture (high level)

v1 needs to represent at least these object types in the UI, shared across modes:

- **Project** — a named container for a thesis and its evidence
- **Thesis** — the claim being hardened
- **Evidence set** — the raw inputs and the compiled structured form
- **Hardening run** — an instance of the adversarial loop against a thesis
- **Iteration** — a single step of a hardening run, with its candidate, verdict, and score
- **Verdict** — the current state of the hardening (including the weakest link)
- **Failure family** — a named category the argument's weakness falls into
- **Killer question** — the single question that, if unanswered, collapses the argument
- **Worked example** — a teaching-note-shaped artifact showing how a failure family has played out in a real case

Forensic mode primarily surfaces: project, thesis, evidence set, hardening run, iteration, verdict.

Didactic mode primarily surfaces: thesis (as "the argument"), failure family, killer question, worked example.

The same Project and Thesis objects can be opened in either mode. Opening an existing workbench project in didactic mode shows a teaching-framed view of its current verdict. Opening a didactic session in forensic mode shows the underlying hardening run.

## 9. Trust posture

The product is local-first. The user's trust in the product comes from:

- Being able to read the files the engine is operating on
- Being able to see what the engine just did (iteration history, provenance)
- Being able to inspect why a verdict is what it is (weakest link, failing criterion, evidence cited)
- Not being asked to trust invisible cloud state

The design must reflect this. Hiding state behind chat or behind opaque "done" affordances will break the trust posture.

## 10. Questions for the designer

Questions a designer is expected to answer during design work, not before:

1. What does the mode switch look like, physically? A literal toggle? A different entry point? A different top-bar surface? The decision is not architectural — it is a design judgment about how prominent the mode change should be.
2. How should the shared object model be visually unified across modes? The same thesis must be recognizable in both modes without looking identical.
3. In forensic mode, what is the single most important object on screen at any given moment — the current verdict? the weakest link? the iteration history? — and how does that change as the user moves through a run?
4. In didactic mode, what is the right pacing for the "one argument → one failure family → one killer question" flow? Is it a single screen or a short wizard?
5. What is the minimum shared design system that lets the modes feel related without collapsing into sameness?
6. What affordances belong in the default surface and what belongs behind "expert" disclosure? The rule of thumb is: if it is about *the method working correctly*, it belongs default. If it is about *optimizing or tuning the method*, it belongs expert.

## 11. Out of scope for v1

- Supervisor / principal cockpit (deferred, see §2)
- Multi-user collaboration
- Cloud-hosted version
- Billing, accounts, team management
- Any feature motivated by governance rather than by the core hardening loop
- Mobile / tablet surfaces
- A marketing site

## 12. Explicit assumption the operator can override

This brief assumes the case-method teaching-judgment distribution channel is **notional** — there is interest in using ZTARE's didactic mode in a case-method teaching context, but there is no committed teaching slot this semester or next. Under that assumption, forensic mode is the primary design target and didactic mode is secondary within the same surface.

If the operator has evidence that the channel is **live** — a real teaching slot with a real student population using didactic-mode output this semester or next — the ordering flips: didactic mode becomes the primary design target and forensic mode becomes the secondary mode within the same surface. Everything else in this brief is stable under the flip: the modes-of-one-surface decision holds, the shared design principles hold, the object model holds, the deferred supervisor cockpit holds. Only §2, §3, §4, and the visual-register guidance in §7 need to be reversed on which mode is "primary."

The operator should confirm this assumption before the designer begins wireframing.

## 13. Reference files

Background the designer may want to read:

- `research_areas/seams/D4_distribution_form_factor_seam.md` — the debate that produced this brief
- `research_areas/seams/D3_layer3_surfacing_seam.md` — the earlier seam for the didactic / teaching surface
- `research_areas/private/product-strategy/local_workbench_productization.md` — the earlier workbench productization note (gitignored; operator can share directly)
- `config/renderers/field_manual.md` and `config/renderers/teaching_note.md` — existing renderer conventions for the teaching surface

These are background, not requirements. The brief itself is the canonical input to design work.

![alt text](Gemini_Generated_Image_l7vi1jl7vi1jl7vi.png)