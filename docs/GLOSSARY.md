# ZTARE Glossary

Plain-English definitions for every term that matters. If a term isn't here, it's either standard (Google it) or jargon inflation that should be removed.

---

## Core Concepts

**ZTARE (Zero-Trust Adversarial Reasoning Engine)**
A system that stress-tests claims by having one AI propose an answer and another AI attack it, with hard numeric checks that neither can override. Think of it as an independent audit for any claim — the same idea as hiring an auditor who doesn't work for the company being audited.

**Mutator**
The AI that proposes answers. It writes a thesis (the argument) and a test suite (code that checks the argument against data). Named "mutator" because each iteration mutates/improves the previous answer.

**Firing Squad**
Three adversarial AI agents that attack the mutator's answer. They look for the weakest assumption and write counter-tests. Named for the obvious reason — they're trying to kill the thesis.

**Meta-Judge**
The AI that scores the result. It only looks at what the code produced when it ran — never the prose. This prevents the mutator from writing a convincing essay that hides a wrong answer.

**Champion**
The current best answer. When a new iteration scores higher than the champion, it gets promoted. Think of it as "the leading candidate."

**Iteration**
One cycle of: mutator proposes → firing squad attacks → judge scores → best answer kept. A typical run does 10-100 iterations.

---

## Evidence & Data

**Evidence (evidence.txt)**
The data the AI is allowed to see. This is the bounded input — everything the mutator and judge work from. It's a snapshot, not a live feed.

**Hidden Holdout**
Data points the mutator never sees. Used to check if the answer actually generalizes vs. just memorizing the visible data. Standard machine learning practice — like a teacher keeping some exam questions secret.

**Visible Slice / Hidden Slice**
The split between data the mutator can see (visible, typically 75%) and data reserved for checking (hidden, typically 25%).

**Workspace**
The persistent memory layer where source material accumulates over time. Think of it as a research folder that grows as you add documents. The validator never trusts it directly — it only sees the bounded evidence snapshot extracted from it.

---

## Scoring & Gates

**Hard Gates (formally: Deterministic Charter Gates, GP-030)**
Numeric pass/fail tests that no AI judge can override. Example: "the model's prediction must be within 5% of the actual data on the hidden points." If a hard gate fails, the score is capped at 50 regardless of how good the prose looks. This prevents the judge from rationalizing a wrong answer into a high score.

**Rubric**
A JSON file that defines what "good" looks like for a specific project. Contains scoring criteria, the AI persona, and feature flags. Think of it as the grading rubric for an exam.

**Score Regime**
The scoring context — which evidence, rubric, and model combination produced a score. When the evidence changes, old scores become incomparable (like changing the exam and comparing grades). The system detects this automatically.

**Stagnation**
When the score stops improving across iterations. After 3 stagnant iterations, the system changes strategy (rotates the attack angle). After sustained stagnation, it may reset the approach entirely.

---

## Research Process

**Seam**
An open investigation or problem being tracked. Contains the problem description, debate turns between Claude and Codex, and status. Think of it as an issue tracker entry with a built-in debate log.

**Bounded Discriminator (formally: Bounded-Discriminator Mode)**
A "show your work" mode where the AI must: (1) break the problem into distinct regimes, (2) name a specific rival explanation, (3) point to a numeric feature in the data that distinguishes its answer from the rival, and (4) cite actual numbers from the evidence. Prevents hand-wavy arguments that sound good but aren't testable.

**Ontology Trap**
When the AI recognizes what the data is (e.g., "this looks like Planck radiation") and imports the known formula instead of deriving it from the data. Named "trap" because it looks like success — the formula fits perfectly — but the AI cheated by recognizing the pattern rather than discovering it. This is a specific form of data contamination.

**Fit Primitive (GP-035)**
A tool that lets the AI propose the shape of an equation, then uses a numerical optimizer (scipy) to find the best parameters. Without this, the AI has to guess the numbers, which it's bad at. With this, the AI proposes structure and the computer finds the numbers. Like giving a student a calculator after they set up the equation.

**Findings Track**
A ledger of patterns discovered during actual runs (not planned in advance). Each finding needs to be observed at least twice (the "two-strike rule") before it's promoted to active status. This prevents over-reacting to one-off flukes.

**Two-Strike Rule (formally: Findings-Track Invariant)**
A pattern must be observed in at least two independent contexts before the project acts on it. Exception: a controlled experiment designed to produce the second observation counts.

---

## Loop Control

**Pivot / Strategy Rotation (formally: Topological Pivot)**
When the AI is stuck, the system changes the attack angle. Different project types get different rotation strategies. The goal is to avoid grinding the same failed approach.

**Underidentified**
When the loop runs out of iterations without finding a satisfactory answer. The system stops and says "I couldn't solve this with the current evidence and approach" rather than pretending to have an answer.

**Early Stop**
Stopping the loop before the full iteration budget if the answer is already good enough (all gates pass, score is high, minimum iterations completed).

---

## Architecture

**Validator**
The adversarial engine itself — the mutator/firing-squad/judge loop. Stateless: every run starts fresh from the evidence snapshot.

**Supervisor**
The work-management layer for improvement programs. Routes tasks, tracks progress, enforces budgets. Does NOT decide truth — that's the validator's job.

**Kernel**
The core evaluator code being improved. When we say "kernel hardening," we mean making the scoring and evaluation more robust against gaming.

---

## Project Types

**Sandbox**
A controlled test environment with synthetic (fake) data. Used to test whether a tool works before using it on real problems. The data is generated from a known formula, so we can check if the AI discovers the right answer.

**Substrate Swap**
Testing a tool on a completely different type of problem to separate "the tool works" from "we got lucky on this specific problem."

**Pre-Registration**
A document written BEFORE running an experiment that specifies: what we'll test, how we'll run it, what counts as success/failure, and the exact commands. Prevents moving the goalposts after seeing the results. Borrowed from scientific practice.

---

## Artifacts

**Thesis (thesis.md)**
The current best argument/answer for a project. Written by the mutator, attacked by the firing squad, scored by the judge.

**Test Model (test_model.py)**
Code that implements the thesis's claims in a testable way. For curve-fitting projects: a Python function that takes inputs and returns predictions. The gates evaluate this against hidden data.

**Post-Mortem**
A correction document created when something goes wrong. Sealed artifacts (scoring sheets, pre-registrations) are never edited — corrections go in post-mortems instead.

**Scoring Sheet**
A sealed record of what was believed at the end of a run. Immutable — never edited after the run. If the conclusions change, the correction goes in a post-mortem.
