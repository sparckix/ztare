---
description: "Paste-ready prompts for using Codex, Claude, or another coding agent with ZTARE."
---

# Agent Prompts

> **Up:** [Documentation map](../README.md)

A short, opinionated set of prompts for a person using their own Codex,
Claude, or other coding agent on ZTARE. Each prompt covers a real
use case for a *new arrival* — understanding what's here, deciding what
to look at, inspecting a claim, having a claim adversarially reviewed,
or running the engine on their own substrate. Paste one prompt at a time
and replace bracketed text.

Ground rules for every prompt:

- Treat the live filesystem as the source of truth.
- Read before editing.
- Do not commit or push unless explicitly asked.
- Do not treat chat as the system of record.
- Do not depend on private or ignored paths for public documentation.
- Preserve existing user changes.

## 1. Repo map — what is this and what does it have

```text
You are helping me understand the ZTARE repository. Read README.md, docs/README.md, docs/evidence_atlas/README.md, docs/evidence_atlas/primitive_evidence_matrix.md, docs/concepts/capabilities.md, docs/concepts/architecture.md, docs/concepts/glossary.md, docs/public_claim_register.md, and docs/guides/cli.md. Then give me a concise map of:

1. ZTARE's scope boundary: the adversarial-reasoning kernel here versus the reusable governance kernel in cognitive-firm;
2. the three architectural layers (in-loop validator, operating discipline, named primitives) and one concrete capability inside each;
3. where the conservative public claims live, which evidence level each currently reaches, and what non-claims or caveats attach to them;
4. the single CLI entry point (`ztare`) and the subcommands worth knowing;
5. what I should read next given [my interest or task].

Do not summarize every file. Explain the repo as an operating system for adversarial scientific reasoning.
```

## 2. Pick what to look at — your first session

```text
I have about an hour with the ZTARE repo and I want to spend it well on [my goal — e.g. evaluate a specific claim, understand the apparatus, decide whether to use the engine on my own data, look at the LeanMill / forecast-pool / a specific gate]. Read README.md, docs/evidence_atlas/README.md, docs/evidence_atlas/claim_cards.md, docs/concepts/capabilities.md, docs/public_claim_register.md, and the per-substrate `public/CLAIM_SUMMARY.md` files that match my interest. Then:

1. point me at the 3–5 files that are highest-yield for my stated goal;
2. name which sealed claims (in the public claim register) are most relevant, and which "held privately" items I would otherwise be tempted to chase;
3. flag any place where my goal is actually outside ZTARE's scope (e.g. it belongs to cognitive-firm) and route me accordingly;
4. give me one concrete first action I can take on my own machine.

Do not propose anything that requires private artifacts I cannot reach.
```

## 3. Inspect a specific claim or project

```text
Inspect projects/[project_slug]/public/CLAIM_SUMMARY.md plus its entry in docs/public_claim_register.md, any relevant card in docs/evidence_atlas/claim_cards.md, and any relevant rows in research_areas/EXPERIMENT_TRACK_RECORD.md. Summarize:

1. what the project actually claims, in one sentence;
2. the gate verdicts and the retest tag — what was sealed, what is partial, what is a documented null or demotion;
3. the honest non-claims attached to it;
4. the next falsifier or source-design step;
5. whether the claim would survive cross-family or external review, and which adjacent claims in the register would be affected if it didn't.

Do not invent results that are not in the public summary. If something is held privately, say so and stop — do not infer.
```

## 4. Adversarial review of a claim

```text
Review [project, claim, or sealed sandbox] adversarially. Read its public/CLAIM_SUMMARY.md, its entry in docs/public_claim_register.md, the relevant gate library (src/ztare/gates/) entries, and docs/concepts/anti_pattern_catalog.md + docs/concepts/goodhart_at_every_layer.md. Assume the claim overclaims; find the hole. Answer:

1. What can this substrate actually answer at the stated gate thresholds, and what would it take to discriminate the claim from its nearest structural rival?
2. Is the binding constraint data coverage, gate looseness, grammar ceiling (the form is unreachable), space ceiling (the mutator did not enter the right category), contamination, or operator anchor?
3. Which specification-gaming strategy from the catalogue would best produce this claim *if* it were laundered? Test the claim against that strategy.
4. What would falsify the current interpretation? Name the cheapest concrete falsifier.

Keep the output calibrated. A high apparatus-internal score is not a discovery unless the artifacts and retest tags license that reading.
```

## 5. Operate the engine on your substrate

```text
You are helping me use ZTARE on my own substrate for [my task]. Read docs/guides/cli.md, docs/concepts/capabilities.md, src/ztare/cli.py, and the relevant control scripts under scripts/public/control/ for the `ztare` subcommand I would use (e.g. forecast / leanmill / bundle / charter / routine-review / action-intel). Then:

1. confirm which subcommand is the right entry for my task, and which step of the apparatus loop it covers;
2. show the exact invocation with the operator flags I need, including how to pass `--help` through to see the underlying script's full surface;
3. explain what the run reads (charter, rubric, evidence files) and what it writes (ledger row, bundle verdict, action-intel delta);
4. name the side effects I should check after the run;
5. if my task requires governance-side primitives (roles, mandates, role daemons, OKR closure), route me to cognitive-firm — they deliberately do not live in `ztare`.

Do not invent subcommands. If the right capability is not in the current CLI, name the underlying script in scripts/public/control/ to run directly and say why it has not been promoted yet.
```
