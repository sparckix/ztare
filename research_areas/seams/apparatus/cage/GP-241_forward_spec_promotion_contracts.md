# GP-241 Forward Spec — Promotion Contracts for the Commit-Membrane Residual

> **Seam metadata** · `seam_id:` GP-241 · `track:` apparatus · `status:` precommitted spec (authored 2026-05-18, · `last_updated:` 2026-05-18


**Status:** precommitted spec (authored 2026-05-18, *before* implementation).
**Parent:** `GP-241_commit_membrane_mode_independent_forcing_seam.md`.
**Governing principle:** `docs/concepts/epistemic_principles.md` P15/P16.
**Method:** paper 2 (*Contract-Governed Adversarial Evaluator Hardening*) —
each item below is admitted to the membrane only by a deterministic,
replayable **PASS / FAIL / BLOCKED** contract authored here, before any
code, and each contract additionally states **what the stage may not
claim**. Acceptance is the contract verdict plus one independent
kill-test run by not-the-builder. Builder self-attestation is
explicitly insufficient and does not count as acceptance.

## Why this document exists

Six cold cross-provider passes over the commit-membrane each returned
artifact-NO-GO. The findings were real and severe but, by pass six,
had collapsed to **two mechanizable structural root causes plus one
irreducible residual**. P15 says the correct response to that pattern
is not patch N+1 but a precommitted spec. This is that spec. It does
not re-litigate the per-finding history (it is in the parent seam);
it states the contracts that close the two root causes and fences the
irreducible one so no contract can be read as closing it.

## Scope

**In scope (mechanizable — these get contracts):**

- **RC1 — no independent recomputation boundary.** The daemon trusts
  an agent-supplied `COMPLETE` manifest / bytes; it neither re-runs
  the deterministic steps nor requires per-step independently-signed
  evidence, and it allows receipt churn (a later receipt silently
  overwriting the daemon-owned copy).
- **RC2 — no real operator-identity boundary.** `target_register`,
  R2 manifest provenance, and admin-retire are "operator-attested"
  only by an env flag the agent's own runtime could carry. There is
  no signature by a key outside the agent's write boundary.
- **RC3 — formal-statement identity is a regex parse.** SM3's
  cite-vs-prove binding is a text parser of a formal language; cold
  findings 4/5 prove it has a next adversarial input by construction
  (it is correctly an advisory tripwire now, not a HARD gate).

**Out of scope (irreducible — P16, fenced, no contract):** whether a
registered Lean target *faithfully formalizes the informal problem*.
No contract in this document closes this; any implementation claiming
to is rejected at review as a P12/P16 laundering. The contracts below
shrink the ungated surface to exactly this residual and no further.

---

## Contract C1 — Independent recomputation / per-step signed sub-receipts

**Intent.** A manifest is trusted only if the daemon can independently
re-derive its decisive verdicts, or each hard step carries evidence
the daemon itself signed; and a tick's manifest is immutable once
first received.

**PASS iff** all of:
1. Each hard step in the manifest carries a `step_receipt` whose
   payload hash is recorded in a chain-valid daemon-signed ledger row
   (`step_receipt` transition), OR the daemon re-executes that step's
   deterministic checker and reproduces its ok/!ok verdict.
2. The manifest is content-addressed: the first chain-valid
   `manifest_receipt` for `(tick_id, kind)` pins a `manifest_sha256`;
   any later receipt for the same `(tick_id, kind)` with a different
   hash is **rejected**, not overwritten (first-receipt-wins).
3. Close reads only the daemon-owned, first-pinned bytes.

**FAIL** if any hard step has neither an independently-signed
sub-receipt nor a daemon-reproducible verdict, or if receipt churn is
observed (second differing hash for the same key).

**BLOCKED** if a step's checker is not deterministically re-runnable
by the daemon in its environment (e.g. requires network/LLM) AND no
sub-receipt scheme exists for it — the step is then explicitly
recorded as *not independently verifiable* and may not be counted
toward a PASS (it routes to the human residual, not to green).

**MUST NOT claim.** C1 does not claim the manifest's *content* is
deep or correct — only that it was produced by the declared steps and
is immutable. Step-quality is RC-orthogonal and stays advisory/human.

**Kill-test (not-the-builder).** From a clean checkout: (a) submit a
fabricated `COMPLETE` manifest with no sub-receipts → must FAIL;
(b) submit a valid manifest, receipt it, then submit a second receipt
with mutated bytes → second must be rejected and close must still
verify the first; (c) a step whose checker needs the network → must
be BLOCKED, never silently PASS.

---

## Contract C2 — Operator-identity boundary (compose the judge-key pattern)

**Intent.** Operator-only transitions (`target_register`,
`admin_retire`, any human-approval) are authenticated by a signature
from a keypair **outside the agent's write boundary**, verified
against a pinned committed public anchor — exactly the existing
`ztare_judge` key pattern (`/srv/ztare_judge_keys/`, separate OS
identity, key mode `0400`, agent- and signer-unreadable), reused, not
reinvented.

**PASS iff** the operator transition carries an ed25519 signature
over the canonical payload (`statement_text|label|env_hash` for
`target_register`; analogous tuple for others), the signature
verifies against the **pinned committed operator pubkey**, and the
signing key is provably unreadable by the agent and daemon-signer OS
identities (the deploy invariant the judge key already establishes).

**FAIL** if acceptance rests on an env flag / proposal boolean the
agent runtime could set, or on any unsigned path.

**BLOCKED** if the operator key/pinned anchor is not provisioned —
fail-closed: no operator transition is accepted (never "allow until
provisioned"; that is the P5 anti-pattern).

**MUST NOT claim.** C2 authenticates *who* registered a target, not
*whether the target is the Clay problem* (that is P16, out of scope).

**Kill-test (not-the-builder).** Agent-runtime attempts a
`target_register` with `i_am_operator=true` + env set but no operator
signature → FAIL. A signature by any non-pinned key → FAIL.
Unprovisioned anchor → BLOCKED, and no closure-claim can pass.

---

## Contract C3 — Lean-kernel statement identity (replace the regex tripwire)

**Intent.** Promote SM3's HARD path from regex text-hashing to Lean
elaboration: two statements are "the same target" iff they elaborate
to defeq types in a trusted, import-pinned Lean environment. The
regex tripwire remains only as a cheap advisory pre-filter.

**PASS iff** the proven theorem's elaborated type is defeq (in a
pinned-import environment whose hash is recorded) to the
operator-registered target's elaborated type.

**FAIL** if they are not defeq, or if the environment/import hash does
not match the one bound at registration (notation/instance drift is
caught, not laundered).

**BLOCKED** if a Lean toolchain is unavailable in the verifying
environment — SM3 then stays advisory-only (its current state) and
the closure claim routes to the human residual; it does **not**
silently pass on the regex tripwire.

**MUST NOT claim.** C3 establishes syntactic/defeq identity of the
proved statement to the registered one. It does not establish that
the registered statement captures the informal problem — P16, fenced.

**Kill-test (not-the-builder).** `(let n:=…; n)=0` faithful proof vs
same registered statement → PASS (the regex false-FAIL is gone).
`∀u,Pu→Qu` vs `(u)(h:Pu):Qu` → PASS. A weaker toy theorem with a
collision-crafted statement string → FAIL (defeq catches what the
regex collided). No toolchain → BLOCKED, not PASS.

---

## Acceptance protocol (precommitted)

1. The three contracts above are frozen as of this document's commit;
   implementation may not edit a contract to make its output pass
   (that is the paper-2 promotion-path-scoping invariant; a contract
   change is itself a reviewed event).
2. Implement C2 first (composes existing infra, lowest novelty), then
   C1, then C3 (heaviest; legitimately BLOCKED-tolerant).
3. Acceptance = each contract emits PASS or an honest BLOCKED **and**
   one independent cold kill-test (not-the-builder) reproduces the
   contract verdicts from a clean checkout. A builder self-review is
   recorded but is explicitly **not** acceptance.
4. Residual after all three PASS: exactly P16 and nothing larger.
   That is the defined terminal state (`epistemic_principles.md` P16:
   "ready when the largest remaining failure mode is exactly P16").
   No further contract is owed; further hardening of the
   formal↔informal gap is a category error.

## What this spec deliberately does not do

It does not promise the artifact reaches "done" by adding C1–C3. It
promises that, with C1–C3 PASS and the irreducible fenced, the
membrane's failure surface is provably the P16 residual — which is
the honest definition of finished for this class of system, and the
point at which engineering stops and human mathematical curation +
break-only adversarial review take over.

---

## Implementation status (2026-05-18, builder self-review — NOT acceptance)

Per the acceptance protocol above, this section is recorded, not
authoritative. Acceptance is the independent not-the-builder kill-test.

- **C2 (operator-identity) — IMPLEMENTED, fail-closed.** New
  `_daemon_sig.operator_*` (third peer key, mirrors the judge-key
  posture); `target_register` now requires an ed25519
  `operator_sig` over `f"{statement_sha256}|{label}|{env_hash}"`
  verified against the pinned `deploy/gp241_operator_pubkey.hex`.
  The env-flag / `i_am_operator` bypass is **removed**. Anchor is
  the unprovisioned placeholder ⇒ contract emits **BLOCKED**
  (fail-closed: no target registers until the operator provisions
  `/srv/ztare_operator_keys` + commits the real 64-hex pubkey).
  Verified: forged sig rejected, unprovisioned ⇒ BLOCKED. Remaining
  for PASS: operator key provisioning (deploy step) + kill-test.
- **C1 — PARTIAL.** First-receipt-wins / receipt-churn rejection +
  content-addressed daemon-owned copy: **IMPLEMENTED** (a second
  differing receipt for a (tick,kind) is rejected, not overwritten;
  identical is idempotent). Per-step independently-signed
  sub-receipts (the deeper "daemon re-derives or each hard step is
  separately signed" half): **NOT built** — it is its own reviewed
  unit, deliberately not hand-added mid-session (P15); recorded as
  debt, not absorbed into a C1-PASS claim.
- **C3 (Lean-kernel statement identity) — NOT blocked; OPEN, owned
  by the REPL track.** Correction (operator, 2026-05-18): the prior
  "environment-BLOCKED" claim was wrong — `lean`/`lake`/`elan` are on
  PATH, `vendor/lean_repl/` exists, and `src/ztare/formal/lean_repl.py`
  `check_lean(code, project_dir=…)` already elaborates a snippet in a
  pinned lake project. C3 is therefore *implementable by composition*:
  a bidirectional `example` defeq probe (registered-type ⊢ proven-type
  and converse) in the pinned `ztare_proofs` env, with the import/env
  hash bound at registration. It is **not** a daemon hand-patch — a
  separate agent currently owns the Lean toolchain/REPL surface, so
  C3 is sequenced behind/coordinated with that work to avoid a
  double-build collision (parallel-agent convergence discipline), and
  lands as its own precommitted-contract unit + the not-the-builder
  kill-test. Until then SM3 correctly stays the advisory regex
  tripwire and `lean_faithfulness` `gate_passed` is the HARD floor.
  Honest status: OPEN, composable, coordinated — not BLOCKED, not
  done.

**Net.** C2 BLOCKED-pending-provision, C1 partial (churn closed,
sub-receipts owed), C3 BLOCKED-by-environment. The ungated surface is
now: C1 sub-receipts + C3 elaboration + the irreducible P16. None of
these is closable by another mid-session patch; each is a precommitted
contract item awaiting its deterministic implementation + the
independent kill-test. This is the P15-correct terminal state.

---

## Status update (2026-05-18, cont.) — C3 wired + frozen-fixture kill-test

Per the external verdict (the next milestone is not more mechanism but
proving with frozen adversarial fixtures that this shape catches the
lived laundering), and respecting the constraint that another agent
owns the Lean/REPL surface and a daemon may be busy:

- **C3 IMPLEMENTED by composition (not BLOCKED).** New
  `src/ztare/gates/lean_statement_identity.py` *consumes*
  `lean_repl.check_lean` READ-ONLY (lean_repl.py / vendor / toolchain
  UNCHANGED). Bidirectional `example` defeq probe, 3-valued
  PASS/FAIL/BLOCKED, env_hash binding. `lean_proof_gate` now emits
  the canonical statement *text*; `target_register` signed row stores
  the registered text + env_hash; the daemon close runs the C3 probe
  — FAIL ⇒ HARD oblig_fail (sound: kernel defeq), BLOCKED ⇒ advisory
  (never silent PASS). Compiled + AST-clean. **Live Lean NOT run**
  (would contend with the parallel REPL test) — PASS-on-faithful is
  the not-the-builder kill-test.
- **Frozen-fixture kill-test SHIPPED:**
  `tests/gates/test_gp241_laundering_fixtures.py` — the lived
  laundering attempts as precommitted fixtures with frozen expected
  verdicts + benign FP controls + an explicit xfail boundary for the
  daemon/Lean legs (NOT faked green). 6/6 pure-primitive fixtures
  PASS here (cite-vs-prove discrimination, binder-colon, operator-
  flag-rejected, full-sha256, canonical parity, finding-5 regression).
  Runs as a plain script (pytest-optional) for the not-the-builder
  runner.

**Honest ledger.** Real (discriminator-passing) and in: C2 operator
signature, C1 first-receipt-wins, C3 kernel-defeq probe, the frozen
fixture suite. Owed: operator key provisioning (operator action),
C1 per-step sub-receipts (own reviewed unit), and the not-the-builder
run of the daemon-integration + Lean-live fixtures. None of the owed
items is "more cleverness" — they are the boring external-validation
package + one operator action. That is the spec-defined path to
"ready", and it is finite.

---

## ACCEPTANCE-HARNESS CAUGHT AS THEATRE (cold audit bmzfkze92, 2026-05-18)

A not-the-builder cold pass (gpt-5.5 medium) on the builder-written
live-daemon kill-test returned **NO-collapses-to-one-test**. Findings,
all sound:
- The 5 "distinct" laundering cases submit the SAME malformed
  tick_close (no frozen start) ⇒ rejected at one earliest invariant ⇒
  one defense tested 5×, mislabelled as 5. Theatre.
- Quarantine evidence has a stale-artifact false-pass: greps a marker
  with NO causal linkage (snapshot-before / proposal_id / created_at
  / expected-reason).
- Prod-store guard weak (literal path; no bind-mount/hardlink/env;
  --store not even passed to propose).
- It does NOT test the ACTUAL membrane risk: a well-formed envelope
  (valid frozen start + receipt chain + registered target + valid
  close) whose cited proof is a weaker / different-hash / vacuous
  (`True`) theorem. Garbage-rejection ≠ acceptance.

**Decisive conclusion (this is the session's sharpest result):**
*a builder cannot author its own acceptance harness* — the harness was
self-blessing theatre and only a not-the-builder pass caught it. This
is P15/P16/the discriminator proving itself recursively at the
acceptance layer. The kill-test file is downgraded in-place to
BUILDER-SMOKE-ONLY with this verdict in its header; it is explicitly
NOT an acceptance gate.

**Valid acceptance (unchanged in principle, now concretely specified)
— a NOT-the-builder unit in the provisioned VPS env:**
1. Distinct per-defense fixtures that each reach their SPECIFIC
   invariant (substrate-swap reaches the substrate check with an
   otherwise-valid frozen start; receipt-churn reaches C1 with a real
   first receipt; forged-operator-sig reaches C2 with a real
   registered-target attempt; etc.) — not all bouncing at "no frozen
   start".
2. Causally-linked fresh daemon artifacts: snapshot-before, submit,
   poll, accept only artifacts with created_at ≥ submit, matching
   proposal_id/hash + exact tick_id + the EXPECTED rejection reason
   (fail if quarantined for the wrong reason).
3. The well-formed-envelope / vacuous-or-unfaithful-claim fixture
   (the real risk) + the positive controls (real operator-sig PASS,
   faithful-Lean PASS, weaker-toy FAIL) — these need the operator key
   + live Lean + a real registered target, so they are inherently
   VPS + not-the-builder.
The builder's role ends at the spec + smoke; acceptance is authored
and run by not-the-builder, evidenced by daemon artifacts the
operator inspects.

---

## Contract C4 — admin_retire under the operator-identity boundary (close the last honor-system hatch)

**Why this contract exists.** `admin_retire_uncloseable_tick` is the
only liveness escape hatch for a jammed tick, and it is the LAST
consequential transition still gated by a forgeable env flag
(`ZTARE_OPERATOR_RETIRE=1` + `--i-am-operator`), both of which the
agent's own runtime can set. It also bypasses the daemon entirely
(writes a local tombstone `tick_close_gate` reads). It is RC2,
verbatim, and was never wired to C2. The operator demonstrated the
hole directly: running it required no key and no password.

**The decisive truth this contract must state, not paper over.**
Cryptography does NOT create the boundary. The OS privilege topology
does. A signing key is "taken away from the agent" ONLY if the
process the agent runs as is genuinely unprivileged and has NO
escalation path (no root, no sudo, no `sudo -u <key-identity>`) to the
key file. On a host where the agent shares the operator's privileges
(a single-user laptop), C4 is decorative — root reads any `0400`
file. The crypto makes the boundary *unforgeable given the topology*;
it cannot manufacture the topology. Therefore C4's acceptance is the
topology check, not the signature code.

**PASS iff** ALL of:
1. `admin_retire` requires an ed25519 `operator_sig` over the canon
   payload `f"{owner}|{tick_row}|{reason}|{ts}"` (ts present, bounded
   freshness, to kill replay), verified via
   `_daemon_sig.operator_verify` against the PINNED operator anchor.
   The `ZTARE_OPERATOR_RETIRE` / `--i-am-operator` path is DELETED,
   not deprecated — a forgeable path that still exists is still the
   hole.
2. The retire is materialized as a DAEMON-mediated signed transition
   (the membrane writes the tombstone after verifying the operator
   sig), NOT a local file any agent-writable process can emit. A
   local-tombstone-only implementation does NOT pass C4 (it leaves
   the daemon unmediated, which is the original defect).
3. **OS-precondition, verified by not-the-builder in the ACTUAL
   execution environment** (first-class, not an afterthought): the
   agent identity provably cannot read the operator key and has no
   sudo path to the key-owning identity. Concretely, all of these,
   run by not-the-builder on the host where the agent executes:
   `sudo -u <agent_user> test -r <operator_key>` ⇒ FAIL;
   `sudo -n -u <operator_identity> true` as the agent user ⇒ FAIL;
   agent user not in sudoers / no NOPASSWD. If any of these does not
   hold, C4 is **not** PASS in that environment regardless of the
   signature code being correct.

**FAIL** if acceptance rests on the env flag / a proposal boolean, on
a local tombstone the daemon did not sign, or if the OS-precondition
check is skipped or self-reported by the builder/agent.

**BLOCKED** if the operator anchor is unprovisioned. Honest, stated
consequence: with admin_retire BLOCKED, a genuinely jammed tick
cannot be retired and the RD loop can wedge until the operator
provisions the key and signs. **This is acceptable and intended**: a
wedged loop is safe (fail-closed); a forgeable liveness hatch is not.
Do not add a fallback that re-introduces an agent-satisfiable path
"so the loop doesn't wedge" — that fallback IS the vulnerability.

**The honest non-delegation fallback (the operator's own point).**
Where the OS-precondition cannot be met (e.g. a sudo-capable laptop),
the correct design is NOT "trust the C4 gate there." It is: the
consequential transition is **not delegated to that environment at
all**. admin_retire (and target_register, and tick_close) execute
ONLY on the host where the topology holds (the VPS, agent confined
unprivileged); the laptop agent is structurally incapable because it
has no path to the signing identity — enforced by the OS, not by a
flag the agent reads. C4's deployment section must name the single
sanctioned execution host and the membrane must refuse these
transitions proposed from anywhere the topology is unverified.

**MUST NOT claim.** A valid `operator_sig` proves the operator
*authorized this specific retire*. It does NOT prove the retire is
scientifically warranted (that a tick deserves debt-tombstoning vs a
real close vs a close-window policy fix is human judgement, P16-
adjacent), and it does NOT create the boundary (the OS topology
does). C4 closes a forgeability hole; it does not make a laptop
trustworthy and does not adjudicate research merit.

**Kill-test (not-the-builder, on the real execution host).**
(a) Agent attempts `admin_retire` with `ZTARE_OPERATOR_RETIRE=1
--i-am-operator` and NO operator_sig ⇒ MUST be refused (env path
deleted). (b) Agent attempts with a forged/garbage operator_sig ⇒
MUST be refused (sig-verify fail vs pinned anchor). (c) Agent, as its
own identity, attempts to read the operator key file and to
`sudo -u <operator_identity>` ⇒ BOTH must FAIL (the topology check;
if either succeeds, C4 is void here and the transition must not be
delegated to this host). (d) A real operator_sig ⇒ daemon-mediated
tombstone materializes and `tick_close_gate` consumes it. Evidence =
daemon artifacts + the OS-check exit codes, inspected by
not-the-builder; builder self-report does not count.

**Debt externalization (what C4 explicitly does NOT do).** It does
not retroactively secure tombstones already written via the env
flag (those are pre-C4 debt; they must be re-attested or quarantined,
not silently trusted). It does not fix the close-window policy that
made a disciplined aged tick need retiring in the first place — that
is a separate, reviewed policy decision, externalized here so a C4
PASS cannot be read as having addressed it.

---

## RCA — dual-module-identity launcher failure (2026-05-18)

**Symptom.** After a valid C4 operator-signed tick_retire, the gate
logic returned the correct (True, DEBT-BANNER) in EVERY isolated
reproduction (direct import, brief-sys.path repro, instrumented
runpy of the real script) — yet `python3 scripts/public/control/
rd_tick_brief.py` (bare launcher) returned (False, "stamped_state
unavailable"). Non-reproducible in isolation ⇒ a multi-turn debug
spiral (the exact P15 treadmill).

**Confirmed mechanism (probed, not guessed).** `rd_tick_brief.py`
puts BOTH repo-root (lines 917/1255: `sys.path.insert(0, str(REPO))`)
AND repo/src (line 1371) on sys.path, and imports the gate as
`ztare.validator.tick_close_gate` (line 1373) while the codebase
internally uses `from src.ztare.…`. `import ztare.gates.stamped_state`
and `import src.ztare.gates.stamped_state` are then **distinct module
objects from the same file** (`is` → False, probe-verified). Each
works in isolation (both `chain_valid` → 102 rows); the failure is
the dual-identity *interaction within the full launcher process*. The
daemon does NOT exhibit this — it is a single controlled entrypoint
with consistent `src.ztare.*` spelling ⇒ one identity. The vector is
ONLY: one process importing the same security module under BOTH
spellings.

**Fixed.** `tick_close_gate._imp_stamped` → `importlib.import_module(
"ztare.gates.stamped_state")` (canonical single identity, no `src.`
text). The proven-working invocation is `deploy/ns_brief.sh`
(canonical pre-import + runpy) — NS is unblocked through it.

**NOT fixed (honest, P15 — NOT a 6th live patch).** The precise
trigger inside the *bare* `rd_tick_brief.py` full execution (why it
still fails where the instrumented runpy of the same script passes)
is NOT root-caused after ~5 fixes. Per P15 this is a **reviewed-spec
item, not continued live patching**: rd_tick_brief must adopt a
single canonical sys.path discipline (repo/src only; never repo-root;
no mixed spelling) — specced here, not hacked mid-session. Until
then, `ns_brief.sh` is the sanctioned NS entrypoint; bare
rd_tick_brief is known-defective and must not be used for ticks.

**Mechanized prevention.** `tests/gates/test_no_src_prefixed_imports
.py` — deterministic guard (pytest + plain-script) failing if any
RUNTIME importable `src/ztare` module uses `from src.ztare.…`
(scoped to exclude test entrypoints, which are single-process and
not the vector). Current runtime blast radius: ~749 modules — that
is logged remediation DEBT, NOT swept mid-session (sweeping 749 files
now would be the treadmill); the daemon's usage is non-vector
(single entrypoint). The guard prevents NEW runtime offenders and
makes the existing debt visible/enforceable for a future reviewed
sweep. C5 (spec'd, not done): rd_tick_brief canonical-sys.path fix +
the runtime-import-spelling sweep, both as one reviewed unit.
