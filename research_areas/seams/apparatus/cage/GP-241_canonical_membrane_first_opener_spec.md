# GP-241 — Canonical Membrane-First Opener (precommitted spec)

> **Seam metadata** · `seam_id:` GP-241 · `track:` apparatus/cage · `status:` active - 2026-05-18 · `last_updated:` 2026-05-20

Status: SPEC-v1 FLAWED (Codex CLI subscription review 2026-05-18, all
5 items FAIL, code-cited — accepted, not relitigated). SPEC-v2 below
is the corrected, minimal, anti-ladder design. Discipline: spec →
independent adversary review → implement → regression + not-the-
builder + dogfood → trust. NOT a mid-session hack.

**UNFOLDED per review (folding was unsound):** #49 (sys.path) is a
small INDEPENDENT fix; #50 (PATTERN-011) belongs in the typed
pretick/menu path NOT a shell counter (and its premise — a tracked
parseable `ns_residual_manifest.md` — does not hold; it is
workspace-only); #51 is ONLY the documented correct sequence + an
optional thin fail-loud wrapper over EXISTING tools.

## SPEC-v2 — corrected lifecycle (code-cited by the review)

The freeze trigger is **`start_tick` itself** (daemon hashes the
contract file — commit_membrane_daemon.py:822/840/862). `codex.json`
gates **resolve**, not the start-freeze (forecast_pool.py:861).
SPEC-v1's "add-forecast/codex-warm freezes" was a misread (the source
of this session's gate-grind). Canonical membrane-FIRST sequence:

```
0. ZTARE_OFFICIAL_STORE=/srv/ztare_official_store  (NOTE: read-side
   ignores env unless ZTARE_MEMBRANE_OBSERVE handling is correct —
   stamped_state.py:27; propose.py:45/64 local-inbox vs VPS-pinned —
   the wrapper MUST assert enforce-mode, not assume the env suffices)
1. forecast_pool init-contract … --consumes-surfaced … --emit-warm-wake --warm-forecasters codex:codex
2. (optional) forecast_pool add-forecast --agent-id <owner> --read-only-attestation …   RD prior, pre-work
3. start_tick --tick-id <F> --goal <g> --forecast-contract-id <c> --substrate <s> --residual-target <r> --tick-class <k> --transition-type tick_open
       ⇒ daemon HASHES + FREEZES the contract, stamps the signed start row
4. pretick_runner.py …  ⇒ pretick manifest + daemon manifest_receipt   (close HARD-requires this — daemon:1330/1397)
5. — research work (RD depth-n + swarm, aggregated) —
6. codex live forecast produced  (resolve HARD-requires codex.json — forecast_pool.py:861)
7. forecast_pool resolve --contract-id <c> …   (+ catch-ledger entry if success=FALSE — H6)
8. posttick_runner.py … ⇒ posttick manifest + daemon manifest_receipt  (close HARD-requires — daemon:1420/1464)
9. tick_close --tick-row <F> --contract-id <c> …  ⇒ daemon-signed official E/F close
```

The wrapper (if built) is a THIN fail-loud chainer of these EXISTING
tools in this order; it builds NO new orchestration. The leanest
acceptable outcome is documentation-only: "always run this sequence,
membrane-FIRST" + the C4 bypass-debt fallback for any inverted tick.

OPEN for SPEC-v2 review: remote-enforce vs observe assertion
(stamped_state.py:27 / propose.py:45,64); non-atomic contract-create
race (forecast_pool.py:541,618); the codex *live* forecast at step 6
must be the mandated Codex CLI subscription, self-serve, honest.

## SPEC-v2.1 — derived read-only state oracle (gated stays gated; aware = advisory nudge)

Design question (operator): should the mutator be AWARE of the
lifecycle state machine, or only GATED by it? Answer, from the
secure-systems + agent-FSM literature:

- **Security = GATED, unchanged.** Reference-monitor principle
  (Saltzer & Schroeder 1975: complete mediation, fail-safe defaults,
  enforcement independent of the subject): the membrane stays the
  sole non-bypassable authority; the mutator stays untrusted. The
  soundness property MUST NOT depend on the agent reading anything.
- **Usability = AWARE, but only as a DERIVED read-only nudge.** The
  agent-FSM literature (StateFlow, Formal-LLM) shows an explicit
  followed state machine sharply cuts lifecycle errors — but there
  the FSM *is* the controller. We already have a controller (the
  membrane). A second, hand-authored FSM is a NEW rung AND a drift
  surface (a parallel model that disagrees with the real gates is
  exactly how this session failed). FORBIDDEN.
- **Therefore:** add `membrane_state.py` — a read-only oracle that
  computes the current lifecycle state SOLELY by calling the
  membrane's OWN existing predicates (`stamped_state.official_
  transitions/chain_valid/tick_closed/is_official` + contract /
  codex.json / pretick·posttick manifest-receipt presence). It emits
  `{current_state, next_legal_transition, exact_next_command,
  last_refusal_reason}`. It introduces NO state not already implied
  by a gate predicate; it cannot weaken the gate (derived from it);
  it cannot drift (single source of truth = the gate code). It turns
  opaque `frozen=False` refusals into stateful next-step guidance —
  pure observability, not a mechanism. The spec FORBIDS any
  hand-maintained parallel FSM; if the derivation ever needs a fact
  no predicate exposes, the fix is to expose it from the predicate,
  not to mirror it.

States (each ≡ an existing predicate, not invented): `NO_CONTRACT →
CONTRACT_UNFROZEN → STARTED(frozen) → PRETICK_RECEIPTED → IN_WORK →
RESOLVED → (CATCH_OWED if FALSE) → POSTTICK_RECEIPTED → CLOSED`.

References (seam literature):
- Saltzer & Schroeder, *The Protection of Information in Computer
  Systems* (1975) — complete mediation / fail-safe defaults /
  enforcement independent of the subject.
- Wu et al., *StateFlow: Enhancing LLM Task-Solving through
  State-Driven Workflows* (arXiv:2403.11322).
- *Formal-LLM: Integrating Formal Language and Natural Language for
  Controllable LLM-based Agents* (arXiv:2402.00798).
- *MetaAgent: Multi-Agent Systems Based on Finite State Machines*
  (arXiv:2507.22606).

## SPEC-v1 5-FAIL remediation (documented + fixed, per operator)

| # | SPEC-v1 FAIL (review brh46p3ew) | Fix in SPEC-v2 / code |
|---|---|---|
| 1 | "codex.json freezes contract" — WRONG; start_tick freezes (daemon hashes contract, daemon:822/840/862) | SPEC-v2 lifecycle corrected; `membrane_state.py` uses `stamped_state.tick_started` (the real freeze predicate); codex.json correctly placed as a *resolve* precondition only |
| 2 | Lifecycle missing pretick/posttick + manifest_receipt; start_tick args underspecified | SPEC-v2 sequence now includes pretick_runner/posttick_runner + receipts; `open_tick.sh` passes all required start_tick args (`--substrate --residual-target --tick-class --transition-type`) |
| 3 | Fleet footguns: store env vs enforce-mode, non-atomic contract-create race, gameable PATTERN-011 counter (no tracked manifest) | `open_tick.sh` asserts store dir + fail-loud on observe/local-enforce; PATTERN-011 fold REMOVED (#50 re-scoped: needs a typed live-program registry first); contract-create race flagged OPEN for v2 review (not papered over) |
| 4 | Acceptance = happy-path theatre | Acceptance expanded (negative cases) + the no-parallel-FSM invariant is now itself dogfooded by MD cycle 1 below |
| 5 | Folding #49/#50/#51 unsound | UNFOLDED: #49 independent small fix; #50 re-scoped + parked; #51 = documented sequence + thin wrapper only |

## Self-Meta-Darwin (2 real cycles, BEFORE cold dispatch, per operator)

**Cycle 1 — oracle derivation soundness.** Found: the first
`membrane_state.py` (a) consumed `official_transitions()` rows
WITHOUT confirming chain-validity (could report STARTED off a
forged/invalid row), and (b) `_has_manifest_receipt` used a
`json.dumps` substring heuristic — a hand re-derivation of a daemon
check = the parallel-FSM the spec FORBIDS; I had overclaimed "purely
derived" (recurrence of the documented builder-optimism overclaim
bias). FIX: deleted both heuristics; the oracle now calls ONLY
`stamped_state.tick_started/tick_closed` (which chain_valid
internally) and HONESTLY surfaces the manifest-receipt sub-state as
"daemon-verified at close; not re-derived here (no clean predicate —
surface-not-mirror)". The invariant is now true, not asserted.

**Cycle 2 — wrapper + framing.** Found: `open_tick.sh` used
`cmd | _assert_stamped`; a function in a pipeline runs in a SUBSHELL
so its `exit 5` did NOT abort the script — the fail-loud guard was
not fail-loud (decisive bug). Also the membrane-first grep guard
checks only one file (best-effort, was implied as a guarantee). FIX:
capture to a var in the main shell then assert (real abort); added
`local-enforce` to the refusal pattern; documented the grep guard as
a best-effort tripwire, not an interlock; the real guarantee remains
the daemon gates + C4.

**Cycle 3 — invariant CONSISTENCY.** Cycle 1 fixed the receipt
heuristic but `_catch_refs` was the SAME parallel-FSM violation
(substring re-derivation of the daemon H6 catch-attest) AND
permission-blind (unreadable 0600 ledger → silent False → false
CATCH_OWED). FIX: catch status downgraded to a clearly-labelled
NON-authoritative hint that distinguishes absent / present /
unreadable; H6 remains the sole authority.

**Cycle 4 — forgeable-artifact derivation.** "RESOLVED" /
"RESOLVED_NO_POSTTICK" were derived from `outcomes/<cid>.json`, an
AGENT-WRITABLE file (grep confirmed: NO chain-valid resolve
predicate exists). The oracle was leaning on a forgeable artifact for
a near-close state — the exact bug class the membrane exists to stop,
reappearing in the oracle. FIX (also a SIMPLIFICATION, anti-ladder):
the oracle now asserts ONLY the three states backed by real
chain-valid predicates — `CONTRACT_UNFROZEN | IN_LIFECYCLE | CLOSED`
— and for IN_LIFECYCLE emits the ordered remaining sequence + labelled
non-authoritative hints; it no longer claims resolved/catch/receipt
sub-states.

**Cycle 5 — wrapper laundering + fragility.** `open_tick.sh`
hardcoded a free-text `--objective-resolver` (violates the H5b /
task-#27 artifact-bound discipline), and trusted only the refusal
grep while discarding `start_tick`'s exit code. FIX: OBJ_RESOLVER is
now a REQUIRED arg, asserted to reference the F-row/contract; the
start_tick exit code aborts independently of the grep
(defence-in-depth).

**Cycle 6 — honest value proposition (anti-overclaim).** `open_tick.sh`
cannot FORCE membrane-first — an agent can still skip it and do work
first; the only real prevention remains the daemon's fail-closed
gates + C4 bypass-debt. The packet's honest value is **legibility +
correct-sequence convenience + the read-only nudge**, NOT new
enforcement. The spec/wrapper must not imply it "fixes" the
inversion. OPEN QUESTION for cold review (do not self-decide):
**OVER-BUILT?** — should `open_tick.sh` be deleted entirely, keeping
only (a) the documented sequence and (b) the read-only oracle? That
is the maximal anti-ladder position; the reviewer should rule on it.

MD cycles 1–6 each found DECISIVE defects and drove the design
SIMPLER + more honest (fewer asserted states, fewer heuristics) — the
opposite of a ladder. Self-MD is assessed as APPROACHING EXHAUSTION:
remaining candidates are cosmetic. Treadmill guard: no further
self-kill/redispatch loops — the packet now goes to TWO independent
reviewers in parallel (cold Codex CLI subscription + a bounded-info
subagent) and their verdicts are acted on ONCE.

## Review reconciliation (single pass — act ONCE on the union)

Bounded-info subagent (a2545938…): **FLAWED + OVER-BUILT**.
- DECISIVE (accepted): `stamped_state.chain_valid` imports
  `from src.ztare.gates._daemon_sig` (the C5/#49 dual-module bug
  itself); `membrane_state.py` puts only `REPO/src` on `sys.path`
  ⇒ `ModuleNotFoundError: 'src'` ⇒ oracle fail-safes to UNEVALUABLE
  for EVERY real started/closed tick. Security intact (no forged
  state) but the feature is INERT exactly when needed ⇒ #49 is now
  on the critical path; fix must MATCH how the working daemon
  imports (it tolerates `src.`), not fight it.
- OVER-BUILT delete-list (accepted): `ZTARE_OFFICIAL_STORE` env
  passthrough validates a path enforce-mode does not read (hardcoded
  `/srv/...`) — drop it / assert the enforce path instead.
- OVER-BUILT delete-list (**REJECTED — principal override**):
  the subagent recommended deleting the optional RD-forecast arm.
  Operator ruling: **RD-forecast is good discipline — it forces
  skin in the game** (pre-registered `p_success` is the
  accountability/calibration signal; it is exactly what surfaced the
  tick641 mis-calibration). Reconciliation: do NOT delete; instead
  STRENGTHEN — make the RD-forecast step REQUIRED, not optional, in
  `open_tick.sh` (a tick opens with a pre-registered prior or it
  does not open). See [[feedback_rd_forecast_skin_in_the_game]].
- KEEP the opener (subagent + principal agree): it encodes the
  ordering + non-laundering stamp assertion the manual sequence
  cannot self-enforce; the MD-cycle-2 fail-loud fix is verified.
Pending: cold Codex review (b11rcv46f). The single reconciled fix
pass runs only AFTER both verdicts are in (act-once discipline).

## FINAL RECONCILED OUTCOME (both reviewers in; act-once pass done)

- Cold Codex (b11rcv46f): PACKET-FLAWED p=0.82, "delete open_tick.sh".
  Bounded subagent (a2545938…): FLAWED+OVER-BUILT, "keep trimmed".
- **DECISION: `open_tick.sh` DELETED.** It was the recurring-defect
  surface (every review round found new bugs: subshell-exit,
  `local-enforce` *false-refusal of a valid official mode*,
  OBJ_RESOLVER weak substring-lint, `ZTARE_OFFICIAL_STORE` validating
  a path enforce-mode ignores, brittle mode parsing) and the spec
  itself concedes it cannot force membrane-first ⇒ no real forcing,
  only pseudo-policy. Deleting the surface > patching it a 4th time
  (treadmill). If ever rebuilt: a TESTED Python client that verifies
  the exact stamped `tick_started` predicate from the same endpoint
  it submitted to — NOT a shell wrapper. (New task if pursued.)
- **`membrane_state.py` KEPT + FIXED** (the one durably-valuable
  artifact). Two decisive fixes, both verified: (A) sys.path now
  also includes repo root so `stamped_state`'s own `src.*` import
  resolves — oracle is FUNCTIONAL on the VPS (was a security-safe
  dead-letter); (B) empty/absent authoritative ledger ⇒ `UNEVALUABLE`,
  never a false `CONTRACT_UNFROZEN` (verified: local→UNEVALUABLE,
  VPS→real state). #49 (C5) is the canonical import fix and is on the
  oracle's critical path.
- **RD-forecast: principal override UPHELD over BOTH reviewers.** It
  is skin-in-the-game discipline (it produced the tick641 calibration
  signal). Preserved as a REQUIRED step in the documented sequence
  (below), not a deleted shell arm. See
  [[feedback_rd_forecast_skin_in_the_game]].
- **Honest retraction:** "self-MD approaching exhaustion" was an
  OVERCLAIM — cold review then found deploy blockers (store
  false-negative, local-enforce). This is the documented
  builder-optimism overclaim bias recurring AGAIN; named, not
  smoothed. MD is necessary-not-sufficient; the cold pass earned its
  keep.

### THE deliverable (documented sequence — there is no wrapper)

Run, membrane-FIRST, BEFORE any research work, with
`ZTARE_OFFICIAL_STORE=/srv/ztare_official_store`:
1. `forecast_pool.py init-contract … --consumes-surfaced … --emit-warm-wake --warm-forecasters codex:codex`
2. **`forecast_pool.py add-forecast --agent-id <owner> --read-only-attestation --p-success <p> …` — REQUIRED (skin in the game), not optional**
3. `start_tick.py …` ⇒ daemon hashes+FREEZES the contract, signs the start row (verify it stamped, not observe/local-DRYRUN)
4. `pretick_runner.py …` ⇒ daemon manifest_receipt
5. research work (RD depth-n + swarm, aggregated)
6. produce `codex.json` via Codex CLI ChatGPT-subscription (resolve HARD-requires it). VPS: Codex CLI is already installed + ChatGPT-logged-in; VPS-side `codex exec` MUST pass `--skip-git-repo-check` (the repo dir is not in codex's trusted list — a flag, NOT an auth/deploy/operator-boundary issue). Warm-consumer codex wiring already exists (`forecast_pool.py:2059`); invoke with `runtime=codex`. The deprecated `dispatch_external_prover.py`/API path is NOT used.
7. `forecast_pool.py resolve …` (+ independent catch-ledger entry if success=FALSE — H6)
8. `posttick_runner.py …` ⇒ daemon manifest_receipt
9. `tick_close.py …` ⇒ daemon-signed official E/F close

`membrane_state.py --tick-id … --contract-id …` at any point is the
read-only nudge: it tells you the chain-valid state (UNFROZEN /
IN_LIFECYCLE / CLOSED / UNEVALUABLE) and the next step — advisory
only; the daemon remains the sole authority.

> SUPERSEDED PRE-v2 PROSE BELOW. The text in "SPEC-v1" that calls
> `codex.json` the freeze trigger / "authoritative" is WRONG and
> retained ONLY for the audit trail — `start_tick` is the freeze
> trigger (daemon hashes the contract); `codex.json` gates *resolve*.
> Do not read SPEC-v1 as guidance.

## SPEC-v1 (FLAWED — retained for the audit trail; see SUPERSEDED banner above)

Tasks folded: #51 (canonical opener), #50 (PATTERN-011 forcing),
#49 (C5 rd_tick_brief dual-module sys.path).

## Problem (empirically mapped this session, 2026-05-18)

Doing math-first then hand-sequencing the membrane post-hoc hit FIVE
sequential fail-closed gates: (1) `ZTARE_OFFICIAL_STORE` unset ⇒
observe-only; (2) `frozen=False` ⇒ `start_tick` SM2-refused; (3)
`add-forecast` (RD only) does NOT freeze; (4) `tick_close` F1 (no
signed start) / H6 (catch-attest) ; (5) `warm-consumer-once` only
*previews* the codex prompt (`runtime:null`) — no `codex.json`, so
the contract never freezes. The membrane is correctly fail-closed at
every step; the defect is the **operating process**: there is no
single canonical "open a tick the right way BEFORE work" entrypoint,
so the lifecycle gets inverted and the science can only be recorded
as C4 bypass-debt instead of a clean daemon close.

## The canonical lifecycle (authoritative, from this session's mapping)

```
1. ZTARE_OFFICIAL_STORE=/srv/ztare_official_store           (else observe-only)
2. forecast_pool init-contract … --emit-warm-wake --warm-forecasters codex:codex
3. forecast_pool add-forecast --agent-id <owner> --read-only-attestation …   (RD prior, pre-work, honest)
4. PRODUCE codex.json  ⟵ THE FREEZE TRIGGER (see Open Question)
5. (contract now forecast_identity_frozen=True)
6. start_tick --tick-id <F-id> --goal <g> --forecast-contract-id <c> …  ⇒ daemon-signed frozen start row
7. — research work (RD depth-n + swarm, aggregated) —
8. forecast_pool resolve --contract-id <c> …            (codex.json must exist; H6 catch if FALSE)
9. tick_close --tick-row <F-id> --contract-id <c> …     ⇒ daemon-signed official E/F close
```

## Deliverable: one self-contained command

`open_tick.sh <OWNER> <F-ROW-ID> <CONTRACT-ID> <GOAL> <CONSUMES-SURFACED> <RD-P> <RD-RATIONALE-FILE>`

- Self-contained (parses its own intermediates, sensible defaults,
  fail-LOUD-never-silent, ends by printing the verified `start_tick`
  daemon-stamp + the exact next commands). Per
  [[feedback_self_contained_one_command_scripts]].
- Exports the official store; HARD-aborts on any observe/dry-run.
- Runs steps 2–6; refuses to return success unless the daemon
  actually stamped the frozen `start_tick` row (chain-valid).
- Emits the post-work close command (`resolve` → `tick_close`) so the
  agent cannot skip the hard record.
- BLOCKS if called after research artifacts for `<F-ROW-ID>` already
  exist (enforces membrane-FIRST: refuses the inverted order that
  caused this session's debt) — the dogfood positive.

## #50 fold — PATTERN-011 forcing precondition

`open_tick.sh` (and the pretick path) computes the count of
independent LIVE programs/doors in `ns_residual_manifest.md`. If ≥2
AND problem_class=hard_mathematical_residual, it HARD-requires either
`--swarm-dispatched <agentIds>` or `--serial-justification <text>`
(owner-attested) before stamping start. Registered in BOTH the
orchestration menu and the pretick channel (two-channel rule).

## #49 fold — C5 dual-module

`open_tick.sh` and `ns_brief.sh` must invoke with the single
canonical `sys.path` (repo/src first; `ztare.*` only), never the
`src.ztare.*` spelling. Guard already exists
(`tests/gates/test_no_src_prefixed_imports.py`); the opener must run
under it.

## OPEN QUESTION (the one thing the adversary must pressure-test)

Step 4 — what actually produces `codex.json` and freezes the
contract? Observed: `warm-consumer-once` returns `runtime:null`,
status `previewed` (writes a prompt to
`org/channels/forecasting_agent/responses/…`, no forecast). Prior
ticks' `codex.json` have `runtime:None, source:None` — produced by
*some* path. Candidates: (a) `warm-consumer-once` invoked WITH an
explicit codex runtime (`forecast_pool.py:2059 if runtime=="codex"`);
(b) the agent-daemon's own warm loop answers it; (c) a Codex CLI
ChatGPT-subscription responder answers the previewed prompt file
(mandated channel) and the consumer ingests it. The spec REQUIRES
the chosen mechanism be (i) self-serve from a session, (ii) the
mandated Codex CLI subscription (NOT the OpenAI API — operator
2026-05-18), (iii) honest (codex forecasts the question read-only,
does not see the outcome). Implementation MUST resolve this against
the working code before coding step 4; if (b) only, the spec's
verdict is "manual sessions RECORD-only; officialization is the
daemon's job" and `open_tick.sh` instead emits the daemon-handoff +
the C4 bypass-debt fallback.

## Acceptance (not-the-builder + dogfood)

1. Independent adversary (Codex CLI subscription) reviews THIS spec —
   design AND fleet-global race/footgun bugs (esp. the store env,
   the freeze trigger, concurrent ticks) — BEFORE implementation.
2. After implement: regression (existing clean ticks still open),
   plus DOGFOOD CLAUSE — it provably (a) FIRES the membrane-first
   block on this session's exact inverted order, and (b) does NOT
   fire on a genuine clean pre-work open, and (c) the codex-freeze
   step actually freezes a fresh test contract end-to-end.
3. Fail ⇒ revert + keep spec as task; do NOT reimplement mid-session.
