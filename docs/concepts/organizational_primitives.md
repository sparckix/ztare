# Organizational Primitives: The M-Form in Code

**Status:** public companion to `docs/concepts/architecture.md`
**Paper parent:** *The Cognitive Firm* (Paper 4) — M-form governance for recursive AI
**Code parent:** `src/ztare/signals/`, `src/ztare/sessions/`, `src/ztare/validator/mform_alignment_audit.py`, `src/ztare/cli_org.py`
**Philosophical parent:** Chandler (1962), Matzinger (2002), Margulis (1967), Kauffman (1993)

---

## The Relationship to Paper 4

Paper 4 (*The Cognitive Firm*) argues that recursive AI systems require the same structural separation that Chandler documented in human firms: strategic oversight in a general office, operational execution in autonomous divisions, with a deterministic governance layer between them. When the division that generates output also evaluates it, you get specification gaming, metric inflation, and fabricated compliance — regardless of substrate.

This document describes the **code primitives** that make that separation physical. They are to Paper 4 what the [cognitive gym](docs/concepts/architecture.md) is to Paper 5: the operational instantiation of a theoretical claim.

| Paper | Theory | Code instantiation | Doc |
|-------|--------|-------------------|-----|
| Paper 5 (Epistemic Verification) | Ten operations decompose judgment | Cognitive gym: semantic router, topological sieve, deterministic sidecar, contamination gate | `docs/concepts/architecture.md` §L3 |
| Paper 4 (The Cognitive Firm) | M-form separation bounds gaming | **This document**: damage signals, session claims, M-form audit, closure map | You are here |

---

## The Four Primitives

### 1. Damage Signals (Matzinger Danger Model)

**Biological analog:** The immune system does not ask "is this self or non-self?" It asks "is this dangerous?" Matzinger's danger model (2002) separates identity (who are you?) from damage (are you hurting the host?).

**The M-form problem it solves:** Identity-based authorization (`src/ztare/roles/authorization.py`) answers "is this actor allowed here?" It does NOT answer "is this action damaging the host?" An authorized agent can damage the system legally — specification gaming is precisely this failure mode.

**How it works:**
- Any code can `emit()` a damage signal with a kind (e.g., `cost_spike`, `quality_regression`, `handoff_conflict`, `evidence_contradiction`)
- Signals are plain JSON files under `org/signals/damage/`, one per emission
- The supervisor calls `list_recent()` before making a decision
- No enforcement is baked in — the point is to create the write surface so future invariant tripwires have somewhere to land
- Signals are best-effort (never raise on filesystem issues)

**Code:** `src/ztare/signals/damage.py`

**Any-LLM applicability:** Any multi-agent system where authorized actions can still be harmful. The damage channel is a typed "something went wrong" surface that doesn't depend on knowing WHO did it or WHETHER they were authorized — just that something hurts.

---

### 2. Session Claims (Membrane Exclusion)

**Biological analog:** Endosymbiosis (Margulis 1967). When two organisms could both metabolize the same resource, membrane exclusion determines who gets it. The excluded organism defers, not dies.

**The M-form problem it solves:** When two sessions (a Claude conversational session AND a headless cron manager, or two parallel agents) could both act on the same task, uncoordinated writes produce race conditions and corrupt state. Identity doesn't solve this — both sessions may be authorized. The problem is simultaneous access to a shared resource.

**How it works:**
- Claiming a task writes a JSON file under `org/sessions/_claims/<task_id>.json` with owner (session_id), task_id, and expiry
- Any other session that tries to claim the same task while the first claim is live MUST defer
- Deferred sessions SHOULD emit a damage signal of kind `handoff_conflict`
- Claims are gitignored (runtime coordination, not shipped state)

**Code:** `src/ztare/sessions/claims.py`

**Companion:** `src/ztare/sessions/enforce.py` — `ensure_session()` (idempotent session open) and `require_no_conflict()` (raises on multi-session collision)

**Any-LLM applicability:** Any workflow where multiple agents or sessions operate on shared files. GitHub, CI/CD, multi-agent chat — anywhere two writers can collide on the same artifact.

---

### 3. M-Form Alignment Audit (Immune Self/Non-Self)

**Biological analog:** The adaptive immune system audits cells for foreign peptides displayed on MHC molecules. The audit is stochastic (not every cell is checked), cross-reactive (the checker has never seen this specific pathogen before), and lethal (flagged cells are killed, not warned).

**The M-form problem it solves:** The mutator optimizes the rubric's scoring surface. If the rubric is a narrow proxy of the charter's intent, the mutator will satisfy the rubric while violating the charter — the fractal Goodhart pattern documented in Paper 4 §5.4. The rubric is the evaluator; the charter is the intent. The gap between them is where gaming lives.

**How it works:**
- Fires stochastically when a qualitative run scores high: `p = 0.15 + 0.65 * sigmoid(score - 85)`
- A "General Office" LLM call audits the champion thesis against the charter while BLINDED to the rubric
- Cross-family model separation: general_office_model ≠ judge_model ≠ mutator_model
- If the General Office finds charter-spirit misalignment, it appends a new rubric dimension at 15% weight
- Max 2 audits per run; late-run high scores (iter > 10) are skipped

**Code:** `src/ztare/validator/mform_alignment_audit.py`

**Integration:** Before main loop: `_mform_audits_this_run = 0`. Start of each iter: `apply_mform_pending()`. After scoring: `maybe_fire_mform_audit()`.

**Any-LLM applicability:** Any LLM evaluation pipeline where the scoring rubric could diverge from the actual intent. The pattern: randomly audit high-scoring outputs against the original specification using a model that has never seen the scoring rubric. If the audit finds misalignment, tighten the rubric. This is the LLM equivalent of internal audit.

---

### 4. Closure Map (Kauffman Autocatalytic Sets)

**Biological analog:** Kauffman's (1993) autocatalytic sets: a collection of molecules is "closed" if every molecule needed for the set's reproduction is produced by some member of the set. An organism that needs vitamin C but cannot synthesize it is not closed on that axis — it depends on external supply.

**The M-form problem it solves:** A research cycle (evidence → hypothesis → experiment → finding → paper) has steps. If only one agent can perform a step, that step is a single point of failure. If NO agent can perform a step, the cycle is broken. The closure map identifies these gaps.

**How it works:**
- Enumerates the research cycle steps
- For each step, lists which agents/roles are qualified
- Flags steps with only one qualified agent (fragile) or zero (broken)
- Reports as a CLI output for operator inspection

**Code:** `python -m src.ztare.cli_org closure-map`

**Any-LLM applicability:** Any multi-agent workflow with a defined process. Map the process steps, list who can do each, flag the bottlenecks. This is organizational design 101 applied to agent workflows.

---

## The Relationship Between the Two Instantiation Docs

```
Paper 5 (Epistemic Verification)     Paper 4 (The Cognitive Firm)
         │                                     │
         ▼                                     ▼
Cognitive Gym                        Organizational Primitives
(how the engine enforces epistemic discipline on the LLM)       (how the firm governs the agents)
         │                                     │
    ┌────┴────┐                         ┌──────┴──────┐
    │         │                         │             │
Semantic   Determin-                Damage        Session
 Router    istic                   Signals        Claims
           Sidecar                     │             │
    │         │                    M-Form         Closure
Topolog-   Contam-                Alignment         Map
ical       ination                 Audit
Sieve      Gate
```

The cognitive gym answers: **how does a single LLM operate within the verification pipeline?** (Caged, with typed inputs and deterministic checks.)

The organizational primitives answer: **how do multiple agents coordinate without dissolving the governance layer?** (Through damage signals, membrane exclusion, stochastic audits, and closure analysis.)

Both are operational instantiations of theoretical claims. Both are domain-general. Both ship as runnable code in this repo.

---

## Where This Does NOT Belong

- **Not Paper 4 itself.** Paper 4 is the theory; this doc is the implementation. A sentence here should not be cited as "Paper 4 says X" — it should be cited as "the implementation of Paper 4's M-form in this repo does X."
- **Not the reflexive engineering doc.** The reflexive primitives (`docs/concepts/reflexive_engineering.md`) are about the engine improving its OWN infrastructure. The organizational primitives are about agents coordinating with EACH OTHER. Different problem, different solution, same philosophical roots.
- **Not AGENTS.md.** AGENTS.md is the standing rules; this doc explains WHY those rules exist and WHAT code enforces them.

---

*Created: 2026-04-26. Update whenever a new organizational primitive ships or Paper 4 adds a theoretical claim that needs an implementation companion.*
