# Synthetic UX Panels: Productizing LLM-Simulated User Research as a Pre-Ship Design Step

*Draft v0. 2026-05-04. Daniel Alami.*

**Status:** seed draft. Captures the methodology used to build Falsify v0.1 → v0.2 in two compute sessions, plus the path to make the technique a real research contribution.

---

## What this is

A short methodology piece on using LLM-simulated panels of (a) UX expert perspectives and (b) user-test subjects as a pre-ship design step. The technique is not a substitute for real user research. It catches a specific class of issues — empty-state confusion, loading-state abandonment, copy framing, anchoring effects — that are predictable from prior work and can be fixed before any real user encounters them.

---

## Why write this up

Three reasons.

1. The technique is in active use across product teams that ship LLM-tooling, but it is not documented as a methodology. People do it ad hoc, without structure, without measurement, without standards.
2. The literature has discussed LLM-as-user-research-subject (Park et al. 2023, "Generative Agents") as a research probe but not as a routine product step.
3. Falsify v0.1 → v0.2 is a worked example. The simulated panel surfaced eight specific issues, all of which were fixed in the same session that surfaced them. The technique compresses a week of design review into a 30-minute pass.

---

## What is mildly novel about this specific application

The standard literature treatment is one of three:
- LLMs simulating one user at a time (Park et al.)
- LLMs as critique generators (various design-tools work)
- LLMs as A/B test simulators (Google, Meta internal)

Three things in the Falsify application differ:

1. **Multi-perspective expert panel critiquing one artifact.** Five UX experts argue from different schools (editorial designer, operator-tool designer, UX researcher, accessibility, growth/brand). Their disagreements are the deliverable, not their consensus.
2. **User-test panel of seven personas with different drop-off vulnerabilities.** Each persona has a profile, expectation, action, and verdict. The verdicts converge on patterns (empty-state drop-off, loading abandonment, screenshot ugliness) that map to specific changes.
3. **Same-session implementation.** The panels run, produce prioritized changes, and the changes are shipped before the panel's recommendations have a chance to drift. The deliverable is not "a report." It is "a punch list that gets executed."

These are workflow innovations more than research findings. The technique is **mildly novel as a routine product practice**, not as a research contribution.

---

## What would make it truly novel

Three paths, in increasing rigor.

### Path A — Calibrated persona library (light)

Build a library of LLM personas (UX experts, user types) with documented hit rates on specific issue classes. Each persona is validated against a benchmark of products with known UX issues (documented post-launch). For each persona, record:

- Issue classes the persona reliably surfaces
- Issue classes the persona misses
- False-positive rate (issues persona claims that real users don't experience)

Open-source the library + the benchmark. Other teams can run the panels with confidence about which personas catch which issue classes.

This converts the technique from "plausible" to "calibrated." No new mathematical insight, just rigor.

### Path B — Empirical validation (medium)

For a specific product, run the synthetic panel before launch. Ship. Observe real-user behavior at scale. Post-mortem where the panel was right, where it was wrong. Build a hit-rate analysis. Repeat across multiple products.

Output: a paper titled *Synthetic UX Panels Validated Against Real Users: A Hit-Rate Analysis*. Real research contribution, but expensive — requires real products and real user data.

### Path C — Multi-model consistency + closed-loop synthesis (heavy)

Run the same panel through multiple LLMs (Claude, GPT, Gemini). Convergence indicates real signal; divergence is itself interesting (which model "thinks" like which expert school). Then close the loop: panel surfaces issues → system implements changes → panel re-tests → measures whether the change addresses the issue (within the simulation). Compare to ground-truth real-user behavior.

This combines empirical validation with a self-improving simulation framework. The closest analog is reinforcement-learning evaluation suites, applied to UX research.

Output: a top-tier HCI paper. Multi-month research project.

### What I would actually do

**Path A.** It is feasible solo, produces a reusable artifact, and bridges to Path B if traction develops. The persona library + benchmark can be built in 2–4 weeks of focused work and released as an open-source toolkit.

---

## The Falsify worked example

### The panel structure used

**Panel A — five UX expert perspectives:**
- Editorial designer (Are.na / Read.cv school)
- Operator-tool designer (Linear / Vercel DNA)
- UX researcher / behavioral (NN/g + IDEO)
- Accessibility / inclusion (WCAG / GOV.UK)
- Growth / brand (Vercel marketing / Linear design)

**Panel B — seven user-test personas:**
- MBA student under deadline, light AI user, skeptical
- Junior consultant, deadline-driven, jaded heavy AI user
- Founder pre-Series A, technical, high skepticism
- Senior PE partner, low patience, low AI usage
- Policy researcher, domain outside corpus
- AI researcher, will adversarially test the tool
- Random visitor from a tweet, no context

### Issues surfaced (eight, all shipped)

| Persona | Issue | Change shipped |
|---|---|---|
| Tom (random visitor) | Empty state had no example → no paste → no value | Empty-state exemplar with three-example cycler |
| Priya (MBA, deadline) | 5-second wait, no progress indicator → almost reloaded | Loading skeleton with caption |
| Marcus (junior consultant) | Wanted to share, screenshot was ugly | Copy-as-markdown export button |
| Greg / Aisha (domain mismatch) | Irrelevant exhibit case_id broke trust | Threshold-gated, then stripped exhibit entirely (also addresses corpus moat) |
| Sara (UX researcher) | Verdict-on-user copy created ego load | Reframed copy to attribute-of-argument; added "did this match your read?" affordance |
| Yuki (AI researcher) | Wanted similarity score visibility | Noted; partial — the strip-exhibit decision overrode it |
| Elena (founder) | Wanted save / export for later review | Copy-as-markdown for v0; save deferred |
| (Panel C synthesis) | Paste-mode is verdict, not teaching | v0.2 conversational interrogation mode (architectural) |

### What this does and does not validate

The panel produced a punch list that got shipped. It does not validate that the changes shipped will produce better real-user outcomes. That validation requires real users.

The panel is **predictive of plausible issues**, not **predictive of actual user behavior**. The distinction matters for the methodology claim.

---

## Skeleton of the publishable piece

Tentative structure for a Substack / arXiv preprint:

1. **The standard practice** (one paragraph). Most teams ship LLM tools without structured pre-ship UX review. Real user research is gated on real users. The gap is "predictable issues you could catch before launch but don't."

2. **The technique** (one section). Two panels, structured personas, prioritized changes, same-session implementation.

3. **Worked example: Falsify v0.1 → v0.2.** Eight issues surfaced, all shipped. Time-to-implementation: same session.

4. **What it catches and what it misses.** Predictable issues: caught. Surprising issues: not caught (definition: surprising ⇒ not predictable from prior work ⇒ panel cannot derive from training).

5. **The novelty caveat.** Multi-perspective expert panels are workflow innovation, not research. Calibrated persona library would be a real research artifact (Path A above).

6. **Open-source intent.** Persona library + benchmark, if built, would be released.

7. **Limits.** Not a substitute for real-user research. Does not produce statistically valid claims about real user behavior. Should be paired with, not replace, post-launch user research.

---

## Where this should live

| Repo | Fit | Notes |
|---|---|---|
| **ZTARE** (figs_activist_loop) | Strong — sits with paper 5 (Principles of Epistemic Verification) and paper 4 (Cognitive Firm); the technique is in the same family as ZTARE's adversarial verification methodology | Currently here as `research_areas/private/drafts/synthetic_ux_panels_methodology.md` |
| **Falsify** | Weak — Falsify is the product, not the research; methodology piece does not belong in product repo | — |
| **Substack** | Strong as publication channel | Distribution + indexability |
| **arXiv preprint** | Medium — only worth the investment if Path A or B is done | Citable, but premature for a methodology-only piece |
| **Paper appendix** (companion to paper 5) | Medium — could be a chapter in a future revision | Defer until paper 5 is published |

**Recommendation:**
- Draft and refine here (`research_areas/private/drafts/`)
- Publish as a Substack post for distribution
- If Path A is built, write up as a short arXiv preprint
- If publishing in paper 5's next revision, add as an appendix or chapter

---

## TODO

- [ ] Decide whether to invest in Path A (calibrated persona library + benchmark)
- [ ] Substack post v1: tighten this draft to 1500 words
- [ ] Reference list: Park et al. 2023; relevant HCI papers on simulated user research; design-crit traditions (Cooper, NN/g)
- [ ] Self-criticism section: where the technique fails, what it would not catch
- [ ] Sample panel transcript (publicly shareable redacted version) as appendix
