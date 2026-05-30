# External-prover dispatch epd-bvs1b6d43

**Model**: gpt-5.5
**Substrate**: apparatus_governance
**Dispatched**: 2026-05-18T13:53:37+00:00
**Persisted retroactively** (ran via `codex exec`, archived to convention per operator request)

## Question

COLD ADVERSARIAL REVIEW (no self-bless). You are GPT-5.5. ATTACK the
IMPLEMENTED change below. Do not regenerate it; do not be agreeable.
3 independent angles, then GO / GO-WITH-CHANGES / NO-GO + minimal
correction set. Any "add a mechanism" proposal must survive: "what
evidence does this force that the producing agent cannot choose,
narrate, or satisfy by naming compliance?"

## Settled context (do NOT relitigate)
A research LLM agent games/satisfices ticks: names patterns instead
of running them; skips the pre-tick (scientific-amnesia precheck,
orchestration-menu compose, pattern/anti-pattern read, GP-230
forecast, GP-233 yield decomposition, NS residual graph). ~10 prior
cold panels hardened a crypto commit-membrane daemon
(commit_membrane_daemon.py) that is the SOLE writer of official state
(ed25519 hash-chained ledger; "reverse-H3": the daemon materializes
the official F-row). tick_close.py H1-H6 are ADVISORY by design;
ONLY the daemon (H7) is real authority. Established and not up for
debate: any gate grading an agent-AUTHORED artifact gets Goodharted;
only deterministic refusals the agent cannot author have ever held.
crypto is for unattended FORGERY only — orthogonal to gaming.

## The end-to-end change implemented
1. `pretick_runner.py --goal --substrate --owner --tick-id
   --contract-id`: runs 6 existing pre-tick tools, each emitting a
   tool-execution receipt; writes
   `analytics/public/pretick/<tick_id>/pretick_manifest.json` with
   top-level tick_id, contract_id, consumes_surfaced, status
   COMPLETE/INCOMPLETE; RC=2 (fail-closed) unless all 6 steps ok.
   Step 5 (gp230_forecast) now binds to the SPECIFIC --contract-id
   (must exist + carry consumes_surfaced), not "any contract".
2. The daemon, on every tick_close, inside the FROZEN-start branch
   (`if is_close and _start_row is not None:`), after `_sc` = the
   contract_id frozen+signed at start_tick: HARD-requires the
   manifest to exist, status==COMPLETE, manifest.tick_id==close
   tick_id, manifest.contract_id==_sc. Any miss / unreadable ⇒
   append to `oblig_fail` ⇒ existing quarantine path (no official
   F-row materialized). Frozen-close branch ends `recomputed=None`;
   does NOT fall through to the else that reassigns oblig_fail, so
   appends survive to the `if (not v.official) or oblig_fail:` sink.

## Honest residual claimed (attack whether it's cope)
The 6 receipts prove the tools RAN with expected-shape output; they
do NOT certify insight depth/faithfulness (e.g. the BKM
Set.Icc-vs-Ico vacuity class lake build did not catch). That stays
with operator inspection + break-only adversary.

## ATTACK SPECIFICALLY
1. The mutual binding is tick_id + contract_id (both frozen/signed
   at start). Show the concrete bypass: can the agent run
   pretick_runner with throwaway tool inputs (goal/substrate it
   never actually researches) yet COMPLETE all 6 steps, then close
   with the matching frozen contract — i.e. is "tools ran" decoupled
   from "the pre-tick that this tick needed was done"? Which of the
   6 steps are presence-checks an empty/irrelevant run still passes?
2. Step binding depth: amnesia/menu/pattern/graph steps key on
   `--goal` free-text and file presence, NOT on the frozen contract
   or the surfaced id. Path where a COMPLETE manifest is bound to
   the right contract_id but the amnesia/graph steps were run on a
   DIFFERENT goal than the tick's. Is contract_id+tick_id binding
   sufficient, or must the manifest also bind to the frozen
   start_row's goal / consumes_surfaced (the runner captures
   consumes_surfaced but the daemon does NOT check it against the
   frozen row)?
3. The agent builds AND runs both the runner and (proposes to) the
   daemon. Daemon code itself is untracked/agent-written. What is
   the minimum that makes THIS change not self-authored evidence —
   given the daemon is the trust root and the same agent edits it?
4. Failure mode you predict it still leaves even if implemented
   perfectly.

## Implemented code regions
(see attached /tmp/e2e_regions.txt — pasted below)
### DAEMON GATE (commit_membrane_daemon.py, inside 'if is_close and _start_row is not None:', after _sc frozen contract id):
    if is_close and _start_row is not None:
        # cold review b1djdevru (B): the close's contract_id MUST be
        # the one frozen at start_tick — else a close can bind a
        # foreign contract to a tick's frozen obligations.
        _sc = str(_start_row.get("contract_id", "") or "")
        if _sc and str(close.get("contract_id", "")) != _sc:
            oblig_fail.append(
                f"close.contract_id {close.get('contract_id')!r} != "
                f"frozen start_tick contract_id {_sc!r} "
                f"(foreign-contract binding rejected)")
        # END-TO-END pre-tick enforcement (operator 2026-05-18; trust
        # root = operator inspection of the manifest, not agent self-
        # attestation). The DAEMON is the only real authority (H7;
        # tick_close.py H1-H6 are advisory under GP-241). So the
        # pre-tick is enforced HERE or nowhere. A COMPLETE pretick
        # manifest MUST exist for this tick_id AND be mutually bound to
        # the FROZEN signed start row (tick_id + contract_id) — same
        # un-forgeable binding as the b1djdevru contract check above,
        # which closes the presence≠this-tick gap. Absent/INCOMPLETE/
        # mismatched ⇒ oblig_fail ⇒ the existing path QUARANTINES
        # (fail-closed). Any read error is fail-closed (a HARD entry),
        # never a daemon crash.
        _tid = str(close.get("tick_id", "") or "")
        try:
            _pm = (REPO_ROOT / "analytics" / "public" / "pretick"
                   / _tid / "pretick_manifest.json")
            if not _pm.is_file():
                oblig_fail.append(
                    f"pretick_manifest MISSING for tick {_tid!r} "
                    f"(analytics/public/pretick/{_tid}/) — the "
                    f"pre-tick (amnesia/menu/pattern/forecast/GP-233) "
                    f"was not RUN; run pretick_runner.py first "
                    f"(fail-closed: no pre-tick ⇒ no close)")
            else:
                _mj = json.loads(_pm.read_text(encoding="utf-8"))
                if str(_mj.get("status")) != "COMPLETE":
                    oblig_fail.append(
                        f"pretick_manifest status="
                        f"{_mj.get('status')!r} (not COMPLETE) — "
                        f"failed pre-tick steps: "
                        f"{[s.get('step') for s in (_mj.get('steps') or []) if not s.get('ok')]}")
                if str(_mj.get("tick_id")) != _tid:
                    oblig_fail.append(
                        f"pretick_manifest tick_id "
                        f"{_mj.get('tick_id')!r} != close tick_id "
                        f"{_tid!r} (foreign-manifest binding rejected)")
                _mc = str(_mj.get("contract_id", "") or "")
                if _sc and _mc and _mc != _sc:
                    oblig_fail.append(
                        f"pretick_manifest contract_id {_mc!r} != "
                        f"frozen start_tick contract_id {_sc!r} "
                        f"(presence≠this-tick bypass blocked)")
                elif _sc and not _mc:
                    oblig_fail.append(
                        f"pretick_manifest carries NO contract_id — "
                        f"cannot mutually-bind to the frozen tick "
                        f"(unbound pre-tick rejected)")
        except Exception as _pe:
            oblig_fail.append(
                f"pretick_manifest unreadable for {_tid!r} "
                f"({type(_pe).__name__}) — fail-closed (no verifiable "
                f"pre-tick ⇒ no close)")

### FAIL-CLOSED SINK (same fn):
        recomputed = None  # frozen path is authoritative for closes
    else:
        recomputed = (start_tick(goal, _tt, _ds)
                      if (goal or _tt or _ds) else None)
        if recomputed and recomputed.mandatory_obligations:
            ok_o, fails_o = validate_tick_contract(
                goal, p.get("witnesses") or {}, p.get("why_not") or {},
                _tt, _ds)
            if not ok_o:
                oblig_fail = [f"obligation undischarged: {f}"
                              for f in fails_o]

    if (not v.official) or oblig_fail:
        rec = {
            "ts": _now(), "proposal_id": pid,
            "agent_runtime": p.get("agent_runtime"),
            "transition_type": p.get("transition_type"),
            "verdict": "quarantine",
            "failed": list(v.failed) + oblig_fail, "notes": v.notes,
            "gate_version": GATE_VERSION,
        }
        (QUARANTINE / f"{proposal_path.stem}.quarantine.json").write_text(
            json.dumps(rec, indent=2))
        proposal_path.unlink(missing_ok=True)
        return rec


### pretick_runner gp230 step + manifest:
                            {"source_void_nodes": ids,
                             "min_vertex_cuts": mincuts,
                             "consumes_surfaced_candidates": ids}))
    else:
        steps.append(_step("ns_residual_graph", True,
                            {"skipped": "non-NS substrate"}))

    # 5 — GP-230 forecast contract presence (deterministic check that
    #     a micro contract bound to a surfaced id + a forecast exist;
    #     the runner does NOT fabricate one — it verifies the agent
    #     created it via forecast_pool, else fail-closed).
    #     Bind to the SPECIFIC --contract-id this tick will consume
    #     (not "any surfaced-bound contract exists" — that was the
    #     presence≠this-tick weakness). PASS iff that exact contract
    #     file exists AND carries consumes_surfaced. Its
    #     consumes_surfaced is lifted to manifest so the daemon binds
    #     manifest⇄frozen-start-row by contract_id (un-forgeable).
    fp = REPO / "analytics/public/forecast_pool/contracts"
    this_consumes = None
    this_ok = False
    if fp.is_dir():
        for c in fp.glob("*.json"):
            try:
                cj = json.loads(c.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(cj.get("contract_id", "")) == a.contract_id:
                this_consumes = cj.get("consumes_surfaced")
                this_ok = bool(this_consumes)
                break
    steps.append(_step("gp230_forecast",
                        this_ok,
                        {"contract_id": a.contract_id,
                         "consumes_surfaced": this_consumes,
                         "note": ("the SPECIFIC tick contract must "
                                  "exist + be surfaced-bound")}))

    # 6 — GP-233 yield-decomposition scaffold (residual_to_lever
    #     ledger presence for this owner; not fabricated).
    rtl = REPO / ("analytics/public/ledgers/residual_to_lever/"
                  "ledger.jsonl")
    rtl_alt = list((REPO / "analytics/public/ledgers/"
                    "residual_to_lever").glob("*")) \
        if (REPO / "analytics/public/ledgers/"
            "residual_to_lever").is_dir() else []
    steps.append(_step("gp233_decomposition",
                        rtl.exists() or bool(rtl_alt),
                        {"residual_to_lever_ledger_present":
                         rtl.exists() or bool(rtl_alt)}))

    complete = all(s["ok"] for s in steps)
    manifest = {
        "tick_id": a.tick_id, "goal": a.goal,
        "substrate": a.substrate, "owner": a.owner,
        "contract_id": a.contract_id,
        "consumes_surfaced": this_consumes,
        "ts": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "authored_by": "agent",
        "trust_root": "operator_inspection (NOT operator-authored; "
                       "operator 2026-05-18)",


## Response (final codex verdict block)

**Verdict: NO-GO**

I checked the actual repo. One correction already exists that was missing from the pasted snippet: the daemon now checks `pretick_manifest.goal == frozen start_tick.goal` in [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:872). That blocks the simplest different-goal manifest replay. It does not make this gate authoritative enough.

**Angle 1: COMPLETE is still shallow**

`pretick_runner.py` mostly proves global artifacts exist, not that the tick’s needed pre-tick was done.

Concrete pass path:

- `scientific_amnesia`: passes if output contains `"overlap_detected"`, even if false. See [pretick_runner.py](/scripts/public/control/pretick_runner.py:95).
- `orchestration_menu`: ignores the goal and selects the first hardcoded key found in menu text. The local variable `g = a.goal.lower()` is unused. See [pretick_runner.py](/scripts/public/control/pretick_runner.py:105).
- `pattern_antipattern`: only checks catalog routing files have IDs. It does not prove the obligated chain was read or applied to this tick. See [pretick_runner.py](/scripts/public/control/pretick_runner.py:120).
- `ns_residual_graph`: skips unless substrate equals exactly `ns_millennium_hunt`; a manifest with substrate `ns` skips. The sample `E2E-PRETICK-20260518` did exactly that while still claiming an NS-looking goal.
- `gp230_forecast`: checks contract file presence and `consumes_surfaced`; it does not check a forecast exists despite the comment saying forecast contract plus forecast.
- `gp233_decomposition`: any residual-to-lever file in the directory passes. No tick, owner, goal, contract, or surfaced-id binding.

So “tools ran” remains decoupled from “the needed pre-tick was consumed.” The runner can still produce COMPLETE from mostly irrelevant presence checks.

**Angle 2: Binding depth is insufficient**

The actual daemon binds `tick_id`, `contract_id`, and now `goal`. It still does not bind `substrate`, `owner`, or `consumes_surfaced` against the frozen start row. Worse, `start_tick` stamps `contract_id` from `pre_tick_obligation_compiler.start_tick()` in [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:733), while the runner treats the same field as a forecast-pool contract id in [pretick_runner.py](/scripts/public/control/pretick_runner.py:167).

That overload lets an agent create a forecast-pool contract with the deterministic compiler id, but with a loose or unrelated forecast question/objective. The daemon never checks the forecast contract’s question/objective, `consumes_surfaced`, or content hash against a frozen start snapshot.

Minimum correction here: the daemon-minted `start_tick` row must freeze `substrate`, `owner`, `gp230_contract_sha256`, `gp230_question_hash`, and `consumes_surfaced`; close must check the manifest and current contract file against that frozen snapshot. A mutable repo JSON contract read only at close is not evidence.

**Angle 3: Trust-root self-authorship remains fatal**

This change is only as strong as `commit_membrane_daemon.py`, and that file is agent-editable in the repo. Crypto only helps after the verifier binary and signing key are outside the agent’s write boundary. A daemon that an agent can edit can be made to accept any manifest while still producing a valid signature.

Minimum correction: deploy the daemon from an operator-pinned tree hash under the verifier identity, with signing keys unreadable by the agent. The stamped row should include the daemon code hash and refuse dirty/unpinned verifier code. Agent may propose a patch; it must not be the process that makes the patch authoritative.

**Still-left failure mode**

Even with perfect binding, this will not catch vacuous mathematical consumption: the BKM `Set.Icc` vs `Set.Ico` class still passes if the receipts are shape-correct but semantically useless. The remaining adversary is “run the right tools on the right tick, then ignore or misunderstand what they reveal.” That needs break-only review or a separate artifact-specific verifier, not another manifest field.
tokens used
126.248
**Verdict: NO-GO**

I checked the actual repo. One correction already exists that was missing from the pasted snippet: the daemon now checks `pretick_manifest.goal == frozen start_tick.goal` in [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:872). That blocks the simplest different-goal manifest replay. It does not make this gate authoritative enough.

**Angle 1: COMPLETE is still shallow**

`pretick_runner.py` mostly proves global artifacts exist, not that the tick’s needed pre-tick was done.

Concrete pass path:

- `scientific_amnesia`: passes if output contains `"overlap_detected"`, even if false. See [pretick_runner.py](/scripts/public/control/pretick_runner.py:95).
- `orchestration_menu`: ignores the goal and selects the first hardcoded key found in menu text. The local variable `g = a.goal.lower()` is unused. See [pretick_runner.py](/scripts/public/control/pretick_runner.py:105).
- `pattern_antipattern`: only checks catalog routing files have IDs. It does not prove the obligated chain was read or applied to this tick. See [pretick_runner.py](/scripts/public/control/pretick_runner.py:120).
- `ns_residual_graph`: skips unless substrate equals exactly `ns_millennium_hunt`; a manifest with substrate `ns` skips. The sample `E2E-PRETICK-20260518` did exactly that while still claiming an NS-looking goal.
- `gp230_forecast`: checks contract file presence and `consumes_surfaced`; it does not check a forecast exists despite the comment saying forecast contract plus forecast.
- `gp233_decomposition`: any residual-to-lever file in the directory passes. No tick, owner, goal, contract, or surfaced-id binding.

So “tools ran” remains decoupled from “the needed pre-tick was consumed.” The runner can still produce COMPLETE from mostly irrelevant presence checks.

**Angle 2: Binding depth is insufficient**

The actual daemon binds `tick_id`, `contract_id`, and now `goal`. It still does not bind `substrate`, `owner`, or `consumes_surfaced` against the frozen start row. Worse, `start_tick` stamps `contract_id` from `pre_tick_obligation_compiler.start_tick()` in [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:733), while the runner treats the same field as a forecast-pool contract id in [pretick_runner.py](/scripts/public/control/pretick_runner.py:167).

That overload lets an agent create a forecast-pool contract with the deterministic compiler id, but with a loose or unrelated forecast question/objective. The daemon never checks the forecast contract’s question/objective, `consumes_surfaced`, or content hash against a frozen start snapshot.

Minimum correction here: the daemon-minted `start_tick` row must freeze `substrate`, `owner`, `gp230_contract_sha256`, `gp230_question_hash`, and `consumes_surfaced`; close must check the manifest and current contract file against that frozen snapshot. A mutable repo JSON contract read only at close is not evidence.

**Angle 3: Trust-root self-authorship remains fatal**

This change is only as strong as `commit_membrane_daemon.py`, and that file is agent-editable in the repo. Crypto only helps after the verifier binary and signing key are outside the agent’s write boundary. A daemon that an agent can edit can be made to accept any manifest while still producing a valid signature.

Minimum correction: deploy the daemon from an operator-pinned tree hash under the verifier identity, with signing keys unreadable by the agent. The stamped row should include the daemon code hash and refuse dirty/unpinned verifier code. Agent may propose a patch; it must not be the process that makes the patch authoritative.

**Still-left failure mode**

Even with perfect binding, this will not catch vacuous mathematical consumption: the BKM `Set.Icc` vs `Set.Ico` class still passes if the receipts are shape-correct but semantically useless. The remaining adversary is “run the right tools on the right tick, then ignore or misunderstand what they reveal.” That needs break-only review or a separate artifact-specific verifier, not another manifest field.
