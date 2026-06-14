---
description: "For people who want to run ZTARE as an experiment and reproduce a result."
---

# ZTARE For Researchers

> **Up:** [Documentation map](../README.md)

This document is for people who want to **run ZTARE as an experiment**, reproduce a result, design a new discriminating test, or extend the gate battery, rather than pressure-test a thesis on a domain. If you just want to run the engine on a new project, start at `README.md` and `docs/guides/workflow.md`. Come back here once you care whether a run is *scientifically valid* rather than just whether it *finished*.

The housekeeping layout of `research_areas/` is documented in `research_areas/README.md`. This document is about the discipline a run must satisfy to count as evidence.

---

## 1. What makes a run scientifically valid

A ZTARE run produces a score, a champion thesis, and a debate log. None of that is evidence by itself. A run is scientifically valid only when:

1. **There is a pre-registration.** A falsifiable claim, a discriminating test, and a success criterion written *before* the run. No pre-reg means the run is exploration, not an experiment. In-flight pre-regs live in a private sealed area outside public docs and move to `research_areas/seams/` at close time.
2. **The mutator cannot see the target.** No GT form, no GT parameter values, no algebraic derivation of the target representation in any file `autoresearch_loop.py` reads on turn 1 (`project_charter.md`, `thesis.md`, `current_iteration.md`, rubric).
3. **The gates are real gates, not narratives.** A deterministic gate battery (fit-contract, farther-tail residual, fixture regression, etc.), not a persona judging prose.
4. **The outcome maps to the taxonomy.** Every run closes as Outcome A/B/C/D. "Interesting but inconclusive" is not an outcome.

If any of these is missing, the run is not a data point. It is a warm-up.

---

## 2. Charter contamination, the most common way runs die silently

`autoresearch_loop.py:1319` injects `project_charter.md` verbatim into the mutator prompt every turn. Anything you write to motivate, justify, or explain the target in the charter becomes a turn-1 cheat sheet.

**The rule.** The charter may describe *that* a target exists and *how* grading works. It must not contain:

- the target functional form (even as an example, even in LaTeX, even "hypothetically")
- target parameter values
- worked derivations of the target representation (reparameterizations, limits, factorizations)
- prose that names the specific mechanism the mutator is supposed to discover

The target itself lives only in the private sealed pre-reg area, which the loop never reads.

**The proof case.** [GP-023](../../research_areas/seams/substrates/planck/GP-023_ontology_trap_planck_mechanism_seam.md) sandbox_07, 2026-04-14. Two separate mutators transcribed the charter's derivation on iter 1 and "recovered" the GT to six decimal places. Neither run was diagnostic. After scrub, iter 1 returned 0 with the mutator genuinely searching.

**The check.** Before sealing a charter:

1. `sha256sum project_charter.md`, record in the pre-reg.
2. Grep the charter for any substring of the GT form and its parameter names.
3. Ask: if a stranger read only this charter, could they reconstruct the target? If yes, scrub.

**The pre-run discipline.** Before the first `autoresearch_loop.py` invocation a scaffold must pass: the charter contamination scrub and strip test, an identifiability check, a sealed pre-registration, a smoke gate, and a dry-run of the sealed command. A sandbox missing any of these is a warm-up, not a data point.

---

## 3. The gate battery, how to read a score

A ZTARE score is a compression of a gate battery, not a fitness number. When you look at a run, look at which gates passed and which failed, not at the headline.

Standard deterministic gates currently enforced:

- **Fit contract** (`validator/information_yield.py`), the declared `fit_declaration` block must be algebraically consistent with the Python `I_model` body. Catches "fit a different function than you claim to fit" gaming.
- **Farther-tail global residual** (`validator/runner_r4_fixture_regression.py`), out-of-window residual sampled beyond the fit window. Catches finite-window surrogates that terminal-only tests would miss. [GP-046](../../research_areas/seams/protocol/GP-046_asymptotic_regime_claim_discipline_seam.md) is the empirical anchor.
- **Fixture regression**, closed-form fixtures whose expected output is pinned. Any drift flags immediately.
- **Fit-primitive contract ([GP-035](../../research_areas/seams/engine/grammar/GP-035_mutator_missing_fit_primitive_seam.md))**, always injected. Prevents mutators from declaring a fit that cannot run.
- **NaN-stub fail-closed**, any primitive returning NaN/inf fails the turn. No "robust to missing data" dodges.

Honeypot mode (`rubrics/honeypot_minimal.json`) replaces the gate battery with a loose discovery-oriented rubric. Honeypot scores are not comparable to standard-run scores. Use honeypot to *find new gates*, not to claim a result. See §6.

---

## 4. Pre-registration format

A pre-reg is a single markdown file in the operator's private sealed area. Minimum structure:

```markdown
# GP-0NN <name> pre-registration
Status: sealed | in-flight | closed
Sealed: YYYY-MM-DD HH:MM:SS
Charter fingerprint: sha256:<hash of project_charter.md at seal time>

## Eigenquestion
One sentence. The smallest decisive question whose answer changes what to build next.

## Falsifiable claim
One sentence. Must be falsifiable by the discriminating test below, not by general skepticism.

## Discriminating test
What command will run. What rubric. Which gates. Expected pass/fail pattern under each rival hypothesis.

## Success criterion
Binary. "Champion score ≥ X on gate Y", not "seems to work better."

## What would make this uninterpretable
Contamination paths, known escape hatches, operator-patch temptations. Written *before* the run so a later "success" can be audited against them (Mungerian inversion, AGENTS.md §6c).
```

The pre-reg is sealed by dry-running the exact sealed command string and pinning all implicit defaults (model family, rubric path resolution). A pre-reg that has never been dry-run is not sealed. See AGENTS.md §7 rule on sealed pre-registrations.

---

## 5. Outcome taxonomy

Every experiment closes as one of four outcomes. Write the closing status on the pre-reg, then move it to `research_areas/seams/`.

- **A, Confirmed.** Discriminating test passed the pre-registered success criterion. The falsifiable claim survives.
- **B, Falsified.** Discriminating test ran cleanly and returned the negative. The claim is dead. This is a successful experiment.
- **C, Inconclusive (apparatus).** The run revealed a problem with the apparatus (gate bug, contamination, operator-patch drift). The claim is neither confirmed nor falsified. The apparatus gets a new seam; the original claim goes back to open.
- **D, Withdrawn.** The claim stopped being decisive before the test ran (the question changed, the blocker shipped, the direction was abandoned). Close without a result.

If you cannot pick one of these, the experiment is not closable. Keep it open or rewrite the pre-reg.

---

## 6. Honeypot mode, bug-bounty, not discovery-proof

Honeypot mode (`rubrics/honeypot_minimal.json`) uses a loose rubric that rewards surprise (40), failure-mode revelation (35), falsifiability (25), and a gaming-detection bonus (+15). Max score 115.

**What honeypot is good at.** Finding gates the standard suite is missing. A champion that scores high in honeypot by exposing a structural bug in a prior model is a bug report: it names something the normal run would have missed. Those bugs become candidates for new deterministic gates in kernel hardening.

**What honeypot is not.** It is not a discovery proof. A 115/115 honeypot run does not mean the engine discovered the law; it means the rubric could not disqualify the champion. Read the judge's "weakest point" and treat it as the handle to grab next.

**Integration pattern (bug-bounty loop).** A standard run produces a champion → honeypot red-teams it → if honeypot breaks it, either the standard run has a gap or the champion has a weakness the gate suite did not catch. Either way, the next action is a new gate, not a result claim.

---

## 7. Replication procedure

To reproduce a closed experiment from this repo:

1. Find the closed seam in `research_areas/seams/` and the sealed pre-reg alongside it. The charter fingerprint in the pre-reg is the canonical charter state for that run.
2. Check the current `project_charter.md` hash against the pre-reg fingerprint. If they differ, the charter has drifted, replication must use the pinned version from git at the pre-reg seal time, not `HEAD`.
3. Run the exact sealed command string from the pre-reg. Do not substitute a "same thing" alternative, pinned defaults matter.
4. Compare the closing outcome (A/B/C/D) to the seam's recorded outcome. A divergence is a finding; file it as a new experiment, not as a correction to the old one.

Sealed artifacts (pre-regs after seal, scoring sheets) are never edited in place. Corrections go in post-mortems. Do not invent addenda or supplements, use the correction vocabulary the project already has (AGENTS.md §7).

---

## 8. Where to look

- `AGENTS.md`, standing rules, visibility rules, and hard rules. This is the short file both Claude Code and Codex load at session start.
- `docs/guides/workflow.md`, operator-facing workflow reference.
- `docs/concepts/architecture.md`, kernel internals, primitives, validator surface.
- `research_areas/seams/`, closed seams (public). Start here if you want to see what the engine has actually proven.
- private sealed area, open seams and in-flight pre-regs (gitignored, not in the public mirror).
- private notes area, principal-facing notes. Gitignored.

If this document and AGENTS.md disagree, AGENTS.md wins and this document is stale, flag it.
