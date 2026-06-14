# GP-230 — cognitive-firm absorption from 2026 governance-kernel wave

> **Seam metadata** · `seam_id:` GP-230 · `track:` mission · `status:` open · `last_updated:` 2026-05-08


**Status:** open
**Created:** 2026-05-07
**Owner:** principal + research_director + self_recursive_orchestrator
**Substrate hook:** ZoZ-style recursive evaluation per candidate (no blind borrowing)

## Eigenquestion

Given that cognitive-firm was extracted as a public sibling repo on 2026-05-07, and given the 2026 governance-kernel literature wave (Sovereignty Kernel, Arbiter-K, Aegis, Microsoft Agent Governance Toolkit), **which specific primitives from that prior art should cognitive-firm absorb, in what form, and which should it reject as not decisive for our threat model?**

The mistake to avoid is borrowing-as-is. Each candidate must be evaluated by the same discipline we apply to substrate proposals: pose the question to the apparatus, produce alternatives, critique each, ship what survives.

## Discipline

For each candidate primitive:
1. State the property the prior art is trying to provide.
2. State whether cognitive-firm's actual threat model and use case (single principal, trusted hardware, git as audit) needs that property.
3. Generate at least three implementations: the prior-art version, a simpler version, and a structurally different version that achieves the same property.
4. Run cross-family critique on each.
5. Ship what survives, or document why none survives.
6. Record the verdict in this seam plus a damage signal if the verdict reverses a previously-shipped choice.

This is the same recursion-discipline finding from §5.7 of paper 4 (self-reference gravity in recursive self-evaluation): when the apparatus is given license to evolve its own architecture, the failure mode is to converge on its own outputs as ground signals. Cross-family judges + principal-final-arbitration are the structural guard.

## Candidate primitives (open — none yet evaluated)

### C1. Tamper-evident audit trail
- **Prior art (Sovereignty Kernel):** RFC 6962 Merkle tree + ed25519-signed root per session.
- **Property under question:** can a third party verify that the action log was not retroactively modified?
- **Threat-model fit:** uncertain. Single principal + signed git commits already provide tamper-evidence at commit granularity. Per-action Merkle is finer but adds key-management surface.
- **Alternatives to evaluate:** RFC 6962 full Merkle / signed checkpoint at session end / git-commit-only (status quo).

### C2. Formal invariant proofs
- **Prior art (Aegis, Sovereignty Kernel):** Lean / Coq proof sketches for decisive safety invariants.
- **Property under question:** does formality buy a bug class that property-based + integration tests don't catch?
- **Threat-model fit:** uncertain. Aegis ships into adversarial deployment; we ship into single-principal-trusted. Different calculus.
- **Candidate invariants to formalize if we proceed:** authorized_paths enforcement; transition-precedes-action; budget caps fail-closed; mandate hash verified each tick; cross-family hygiene.

### C3. EU AI Act compliance mapping
- **Prior art (Aegis):** mapping doc from primitives to AI Act articles.
- **Property under question:** does any current or near-term adopter need this?
- **Threat-model fit:** speculative. Hold until first adoption signal; substrate-evaluate when one arrives.

### C4. Capability-based isolation refinement
- **Prior art (Sovereignty Kernel + capability theory):** fine-grained per-action revocable capabilities.
- **Property under question:** is the bug class "agent wrote outside its lane" actually happening at non-trivial rate?
- **Action:** mine recent transitions over the last N tenant-weeks; if rate is non-trivial, refine; if not, document why coarse model holds.

### C5. Explicit instruction dependency graph
- **Prior art (Arbiter-K):** DAG of instructions with taint propagation.
- **Property under question:** does git-history-as-audit + transitions.jsonl already give us cross-action contamination detection in retrospect, or do we need it pre-dispatch?
- **Action:** wait for a concrete contamination case the existing audit can't diagnose; build only if one arrives.

## Why this seam is private

The competitive comparison and threat-model framing belongs in the apparatus's research seams, not in the public cognitive-firm README. Public framing should describe what cognitive-firm IS, not what it explicitly does or does not borrow from named competitors. Public-vs-private split per the standing visibility rules.

## Verdicts (open)

- C1: open — schedule substrate run.
- C2: open — schedule substrate run on the invariant set.
- C3: hold pending adoption signal.
- C4: open — schedule mining-only diagnostic first.
- C5: hold pending concrete case.

## Closure criteria

This seam closes when each candidate has either:
1. Shipped to cognitive-firm with a recorded verdict + design doc, or
2. Been recorded as rejected with a why-not.

## OS-Path: Adoption And Distribution (new strategic axis, opened 2026-05-22)

Distinct from C1-C5 (which ask which competitor PRIMITIVES to absorb). This
axis asks how cognitive-firm becomes ADOPTABLE. It is a candidate for promotion
to its own seam (GP-NNN) if it grows past a few entries; recorded here for now
per the operator's "add to the existing cognitive-firm seam" instruction.

Eigenquestion: cognitive-firm is a kernel - what is its Ubuntu, and what does
it ship on? Full framing in the research-assistant synthesis
`research-assistant/wiki/syntheses/2026-05-22-cognitive-firm-os-analogy-and-10x-eigenproblem.md`.

Design spec (private, under adversarial review):
`research_areas/specs/private/GP-230_os_path_distribution_userland_spec.md`.

Diagnosis (OS analogy held seriously): the kernel/architecture is sound; the
gap is the missing distribution layer. A bare Linux kernel is ~3% of the
"Linux" experience. cognitive-firm today is the kernel with no distro,
installer, userland, package ecosystem, or carrier.

Direction (private strategy; public-appropriate parts go to the cognitive-firm
ROADMAP, not here):
- O1 userland - a layer a non-technical operator lives in; kernel hidden.
- O2 distro + installer - a day-one runnable "starter firm", one action.
- O3 package / overlay ecosystem - tenant overlays as installable packages.
- O4 distribution model - open-core kernel + managed hosted (GitHub/Vercel
  shape); a naive pure-SaaS breaks the inspect/fork/replay invariant.
- O5 beachhead vertical - not "all orgs"; pick the vertical where governed
  human+agent roles are most acute (Linux won servers, then Android).

Sequencing rule (decisive): distribution before validation 10xes risk, not
value. The kernel's central claim - governed learning improves a measured
outcome - is still untested with zero external adopters. Gate O1-O5 on one
real validated field pilot.

Verdict: open. O1-O3 are being pulled forward now at operator request; O4-O5
are strategy decisions held pending the validating pilot.

## 2026-06-09 competitive-landscape reconciliation

Status update: the public cognitive-firm repo now has a canonical positioning
page at `docs/system-positioning.md`. That page should own public framing
against LangGraph, CrewAI, AutoGen, Letta, Google ADK, Microsoft Agent
Framework, SaaS automation, and observability tools.

Boundary decision:
- Public docs may compare by category and capability boundary.
- This seam continues to own named prior-art absorption decisions and
  threat-model verdicts.
- Do not duplicate a second public landscape table inside ZTARE. Link to the
  cognitive-firm page when public positioning is needed.

Current competitive thesis:
- cognitive-firm should not compete on graph execution, model inference,
  prompt orchestration, runtime memory, tracing dashboards, connector catalogs,
  or enterprise IAM administration.
- Its edge is typed organizational authority, human work as state, obligation
  lifecycle, machine provenance, accountable closure, and durable learning.
- The implementation roadmap is adapter-first: LangGraph interrupt-to-A2H,
  then thin lifecycle projections for CrewAI, AutoGen / Microsoft Agent
  Framework, Letta, and Google ADK.

Open cleanup:
- The rubric still references C1-C6 while this seam enumerates C1-C5 plus the
  OS-path axis. Either add an explicit C6 or revise the rubric anchors before
  re-running the GP-230 substrate.
- Reconcile shipped cognitive-firm features against C1-C5 so this seam records
  which prior-art properties were absorbed, rejected, or deferred.
