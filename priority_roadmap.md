# ZTARE Priority Roadmap

**Last refreshed:** 2026-05-02
**Planning horizon:** next 2 weeks
**Board owner:** `role.principal` with execution by `role.manager`, `role.research_director`, `role.engineer`, and `role.reviewer`

This is the public product-management surface. It is not the experiment
ledger, not the seam archive, and not a claims registry. It answers one
question:

```text
What should the repo make easy, reliable, and public next?
```

## North Star

Build a falsification-native research company in a box.

The roadmap is organized as four public tracks plus one release gate. This is
not branding cleanup; it is the product architecture implied by the seams,
debates, and experiment ledger:

- The supervisor-loop/A2A/org-runtime seams point to a reusable **organization
  runtime** whose state is files, gates, roles, mandates, and transition logs.
- The kernel debates and substrate postmortems point to a separate **discovery
  kernel** whose job is adversarial validation, not general company operation.
- The current board and live closure discipline show the repo itself acting as
  a **dogfood research company** that instantiates those primitives.
- The gravity/neural/NS/transformer work belongs in **scientific case studies**:
  high-value stress tests with bounded claims, not product infrastructure.
- Public release hygiene is the gate in front of all four; it is not a
  standalone product track.

The four public tracks are related, but they should not be collapsed into one
story:

| Track | Public name | What it is | Success condition |
|---|---|---|---|
| 1 | Agentic Organization Runtime | The reusable org primitives: roles, mandates, tasks, gates, preferences, transition logs, damage signals, and operator surfaces. | A principal can run a role-bound AI organization from a clean checkout without hidden chat state. |
| 2 | ZTARE Kernel | The scientific discovery loop: evidence substrate, mutator, judge, gates, telemetry, closure, and anti-Goodhart hardening. | A domain user can pressure-test a hypothesis and recover why it failed or survived. |
| 3 | ZTARE Research Co | The dogfood instantiation of the org runtime, using ZTARE to run its own research programs. | The repo demonstrates an AI research company operating on its own state, not just docs about agents. |
| 4 | Scientific Case Studies | Gravity, neural scaling, Navier-Stokes, transformer-successor, and other bounded research campaigns. | Each case study has scoped claims, provenance, closure rows, and clear separation between evidence and speculation. |

The hierarchy matters. The org runtime is the general primitive. ZTARE Research
Co is one instantiation of that primitive. The ZTARE Kernel is the discovery
engine the organization uses. Scientific case studies are stress tests and
public demonstrations, not license to overclaim a theory.

## Track Validation

This section exists so future roadmap edits do not re-flatten the repo into a
generic "AI agents + science" story.

| Candidate track | Keep / merge / demote | Rationale |
|---|---|---|
| Agentic Organization Runtime | **Keep as Track 1** | The supervisor-loop debate, A2A channel work, org bootstrap manifest, roles, gates, and transition logs are a reusable product primitive independent of any one research program. |
| ZTARE Kernel | **Keep as Track 2** | The validator, rubrics, fit primitives, gates, substrate contracts, and anti-Goodhart hardening are the scientific discovery engine. They can be used by the org runtime but should not be described as the org runtime. |
| ZTARE Research Co | **Keep as Track 3, but as dogfood instance** | This is not a second organization framework. It is the repo operating its own research company using the org runtime plus ZTARE kernel. |
| Scientific Case Studies | **Keep as Track 4** | The ledger shows gravity, neural scaling, NS, GP116B, and older sandbox tracks have different evidence burdens. Group them as case studies to prevent any single live result from redefining the product. |
| Cognitive gym / recursive primitives | **Merge across Tracks 1 and 2** | These are cross-cutting principles and exercises, not a separate customer-facing layer. They explain how the org runtime and kernel harden themselves. |
| Formal proofs / Lean | **Place under case studies and kernel boundary** | `ztare_proofs/` is public source for proof stubs and formalization experiments. It supports scientific/proof case studies and kernel credibility, but generated `.lake/` state is not source. |
| Papers | **Treat as artifact layer, not a track** | Papers communicate results from all tracks. They should not drive the architecture taxonomy. |

## Current Priorities

| Priority | Track | Bet | Status | Owner | Outcome | Proof of done | Next action |
|---|---|---|---|---|---|---|---|
| P0 | Repo release | Public push hygiene | In progress | `role.manager` + `role.engineer` | Repo can be pushed publicly without private/runtime leakage or stale entry docs | README, docs map, roadmap, papers index, release checklist, `.gitignore`, and tracked-file audit agree | Finish staged cleanup, verify no tracked private/generated artifacts, run link/path and whitespace checks |
| P0 | Repo release | Roadmap/board terminology sync | Verify | `role.manager` | Public roadmap and execution board use the same track language | `priority_roadmap.md`, `research_areas/ZTARE_BOARD.md`, `docs/README.md`, and root README agree on the four-track map | Run a final terminology scan and link/path check before staging |
| P0 | Agentic Organization Runtime | Single-principal org bootstrap | Verify | `role.manager` | A clean checkout can explain and boot the org primitives without relying on chat history | `org/README.md`, org quickstart, role preflight, runtime smoke test, task/objective/key-result examples | Run first-run setup and smoke tests after release cleanup |
| P0 | ZTARE Kernel | Contract reliability and cost control | In progress | `role.engineer` | The inner loop stops burning full LLM iterations on deterministic contract errors | R1 repair, rubric validation, contract checks, prompt assembly tests, substrate triumvirate checks | Run targeted kernel tests and document the verified command path |
| P0 | ZTARE Research Co | Dogfood governance loop | In progress | `role.manager` + `role.research_director` | Persistent roles can claim tasks, route gates, close experiments, and update ledgers under mandate | Transition log, executive inbox, role assignments, closure rows, and damage signals are exercised on live work | Keep Mode A collaboration lightweight; mechanize only repeated closure/routing moves |
| P0 | Scientific Case Studies | Gravity gp163d admissibility closure | Active GPU run | `role.research_director` | Gravity is recorded as instrument-grade numerical evidence with scoped claims, not cosmological overreach | GPU artifacts downloaded, parity/admissibility status logged, E-row/F-row/INS-row decision completed | Finish the missing rot90 field-slice run, then stop scale-up unless it changes the claim boundary |
| P0 | Scientific Case Studies | Neural scaling external validation | Active | `role.research_director` | The trajectory-shape law is tested on modern external raw telemetry, not just inherited literature curves | OLMo packet, trajectory-only ablation record, 1B void status, pre-registered validation criterion | Acquire exact OLMo 1B raw or sealed equivalent; run trajectory-only point and integrated-segment audits |
| P1 | ZTARE Kernel | Rubric and substrate authoring guardrails | In progress | `role.engineer` | Research directors cannot accidentally launch malformed rubrics or broken substrate contracts | `validate-rubric`, holdout-file checks, substrate four-artifact audit, submission snapshot review | Make rubric/spec checks a pre-flight habit and document the failure modes |
| P1 | Agentic Organization Runtime | Operator surfaces | Verify | `role.engineer` | Principal can operate through CLI, Orbit, or mobile without state divergence | Operator console, Orbit dashboard, Telegram bot, one executive inbox, one transition log | Run the clean-checkout operator-surface checklist; keep filesystem as source of truth |
| P1 | Agentic Organization Runtime | A2A / persistent role channels | Prototype shipped | `role.engineer` | Role offices communicate through durable typed envelopes instead of transient chat context | Agent cards, inbox files, transition events, work-discovery integration | Add examples and enterprise adapter boundary notes |
| P1 | Scientific Case Studies | GP116B transformer-successor substrate | Active | `role.research_director` | Residual-state / successor-architecture data is acquisition-ready without provenance leakage | Schema, acquisition manifests, sourced rows where available, mechanism/family feature abstraction | Acquire non-transformer and learned-residual rows before another serious law loop |
| P2 | Agentic Organization Runtime | Enterprise control plane | Design | `role.research_director` + `role.engineer` | Clear path from local filesystem runtime to multi-tenant deployment | Auth, leases, RBAC, event outbox, retention, signed audit, and idempotent gates are specified | Keep as design until the single-principal path is boringly reliable |

## Track Roadmaps

### 1. Agentic Organization Runtime

This track is the general product primitive. It should be named and documented
as an organization runtime, not merely as "agent tools." The unit of
accountability is the role office, not the model call.

**Now**

- Make `org/` legible as public source: roles, assignments, task queues,
  objectives, key results, signals, and bootstrap manifest.
- Keep principal-specific preferences, directives, channels, and runtime gates
  out of git.
- Verify first-run setup from a clean checkout.
- Preserve three operating modes: direct collaboration, supervisor hardening,
  and domain validation.

**Next**

- Add small examples that show a role claiming a task, opening a gate, closing
  the task, and writing a transition.
- Document the enterprise boundary: what remains filesystem-first locally and
  what becomes Postgres/API/RBAC/leases in a multi-tenant deployment.
- Make operator surfaces projections over the same state, not independent
  state machines.

### 2. ZTARE Kernel

This track is the discovery and validation engine. It is not the whole company.
It is the kernel used by the organization to run bounded hypothesis pressure
tests.

**Now**

- Reduce wasted LLM calls from contract mistakes: rubric validation,
  substrate contract audit, no module-level `I_model(...)`, and submission
  snapshot checks.
- Keep closure discipline mechanized where it is stable: E-rows, F-row
  decision, INS-row decision, thesis marker, and goal advancement.
- Keep evidence/provenance separation strict. Model-facing features should use
  abstract mechanisms and families, not source names that leak the answer.

**Next**

- Document a single verified `make experiment-loop` path after checking the
  Makefile target and rubric spec.
- Add regression fixtures for failure modes already paid for: R1 compiler
  bounces, malformed rubrics, missing holdout files, and broken substrate
  imports.
- Treat weakest-point feedback as work orders: rival tests, residual audits,
  extrapolation stress, and PSLQ/closed-form probes when appropriate.

### 3. ZTARE Research Co

This is the dogfood instantiation: the repo operating as a small research
company that uses the org runtime and ZTARE kernel on itself.

**Now**

- Keep the public entry path clear: `README.md` -> `docs/README.md` ->
  roadmap -> workflow/architecture -> org runtime.
- Make the live board and experiment ledger the source of truth for what is
  active, closed, blocked, or safe to claim.
- Separate executive/product state from scientific evidence. A paper claim is
  not promoted because the org is excited; it is promoted because evidence and
  closure rows license it.

**Next**

- Use Research Director taste ranking to pick experiments by information yield
  and claim value, not by score-chasing.
- Mechanize repeated collaboration lessons only after they generalize.
- Keep active seams private unless they are closed or have a sanitized public
  derivative.

### 4. Scientific Case Studies

These are demonstrations and research campaigns. They matter because they
stress the kernel on hard domains, but each claim must stay bounded by its
instrument and evidence.

**Gravity / GP163D**

- Public frame: numerical-discovery case study and theoretical falsifier
  candidate.
- Current burden: finish missing orientation/admissibility slice, download
  artifacts, close the run, and state whether the signal survives instrument
  checks.
- Non-goal: do not claim dark-matter resolution or cosmological proof from a
  sandbox simulation.

**Neural Scaling / GP154**

- Public frame: externally validated trajectory-shape candidate, not an
  a-priori theorem yet.
- Current burden: acquire exact modern raw telemetry, especially the OLMo 1B
  void, and run pre-registered trajectory-only validation.
- Non-goal: do not rescue optimizer-control laws that anti-transfer to
  production data.

**Navier-Stokes / NS**

- Public frame: formalization and discriminator track for recurrence,
  admissibility, and proof-spine candidates.
- Current burden: keep Lean proof sources public while marking conjectural
  boundaries explicitly.
- Non-goal: do not conflate empirical/proof-stub checks with discharged
  mathematical proof.

**Transformer-Successor / GP116B**

- Public frame: architecture-search substrate for residual-state and
  successor mechanisms.
- Current burden: build acquisition-ready rows and schemas across learned
  residual, SSM, matrix residual, RWKV/KV-direct, and transformer variants.
- Non-goal: do not let model names become features; use audited provenance
  pointers separately from abstract mechanism features.

## Public Push Checklist

Before pushing publicly:

1. **Tracked artifact audit:** no tracked `node_modules`, `.lake`, `.DS_Store`,
   root runtime logs, private preferences, private directives, runtime gates,
   secrets, checkpoints, or one-off GPU artifacts.
2. **Entry-point audit:** root README, `docs/README.md`, roadmap, papers index,
   and release checklist agree on the four tracks and current status.
3. **Private/public audit:** active strategy seams remain private; closed safe
   seams are promoted or represented by sanitized public derivatives.
4. **Science-claim audit:** every case-study claim has an evidence pointer,
   scope limit, and next falsifier.
5. **Lean/proofs audit:** `ztare_proofs/` source is public; generated `.lake/`
   build state is ignored.

## Explicit Non-Goals For This Sprint

- Do not dump every private seam into public.
- Do not make the roadmap a second experiment ledger.
- Do not route live Mode-A collaboration through supervisor ceremony.
- Do not treat Docker success as enterprise readiness.
- Do not overclaim science results because the simulation was expensive.
- Do not rename tracked directories casually; public labels can be cleaned up
  before filesystem moves are justified.

## Decision Rules

- **Promote public:** closed/converged/falsified/confirmed/withdrawn and no
  active GT, exploit, sealed pre-registration, personal, or first-mover-sensitive
  content.
- **Keep private:** open/testing/active/note/verify seams, sealed
  pre-registrations, private principal context, product-sensitive strategy, and
  in-flight discovery tactics.
- **Create public derivative:** when the private source contains active
  strategy but the stable principle is useful to users.
- **Archive:** when a program is closed and artifacts remain in active folders;
  use `git mv` when tracked.

## Current Open Questions

| Question | Why it matters | Default until resolved |
|---|---|---|
| Is "Agentic Organization Runtime" the right public name? | It should feel larger than agent tooling but less grandiose than a firm theory. | Use this name publicly for now; keep "ZTARE Research Co" for the dogfood instantiation. |
| What is the minimum enterprise-ready backend? | Avoid overbuilding before the single-principal loop is solid. | Filesystem-first single-principal runtime first; Postgres/API only after schema stability. |
| Which scientific claims are public-ready? | Case studies can demonstrate capability without overstating discoveries. | Claim methodology and bounded findings only where the ledger supports them. |
| How much Lean should ship now? | Public proof sources are valuable, but `.lake` and generated state should not ship. | Ship source under `ztare_proofs/`; ignore build artifacts. |
