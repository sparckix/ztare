"""Standing CI guards for the recurring LeanMill sibling / agency-creep bug class (2026-06-22).

These exist because the class kept recurring *despite* the principle being documented — the cure for the CLASS
(not an instance) is a test that asserts the BEHAVIOR, so a comment claiming an invariant the code doesn't
enforce fails CI. Two guards:

  1. INVARIANT B (agentic-first): decompose-vs-direct is the AGENT's call at EVERY node — `is_top`/`notes` must
     NOT force a decomposition. This is the exact bug commit 9612a8c16 shipped behind an overclaiming comment
     (`(_is_top and bool(notes))` short-circuited the agent strategy-ask, gapping a directly-provable nucleus).
  2. SPLIT-BRAIN flag defaults: the same boolean `ZTARE_*` gate read with conflicting `.get` defaults in
     different files (the proposer_pool `pool_enabled` bug). `flag_audit` is the mechanical detector.
"""
from __future__ import annotations


def test_invariant_b_agentic_decompose_vs_direct():
    """The agent decides decompose-vs-direct at every node; is_top/notes never force it. FAILS 9612a8c16."""
    from ztare.leanmill.solver.solver_core import (
        _should_decompose_first, _selftest_invariant_b_agentic_decompose)
    _selftest_invariant_b_agentic_decompose()  # the full battery (config gates, native-first, lazy agent)
    base = dict(cited_from_cache=False, iso_route_on=True, decompose_first_on=True, below_cap=True,
                strategy_assess_on=True)
    # the nucleus case: agent says SOLVE_DIRECT, native misses → must NOT decompose (used to force-decompose+gap)
    assert _should_decompose_first(**base, native_closes=lambda: False, agent_recommends=lambda: False) is False
    # hard target: agent says DECOMPOSE → decompose
    assert _should_decompose_first(**base, native_closes=lambda: False, agent_recommends=lambda: True) is True


def test_no_split_brain_flag_defaults():
    """No boolean ZTARE_* gate is read with conflicting .get defaults across files (the proposer_pool bug)."""
    from ztare.leanmill.flag_audit import split_brain_flags
    bad = split_brain_flags()
    assert not bad, ("split-brain boolean flag default(s) — route every reader through ONE canonical accessor:\n"
                     + "\n".join(f"  {f}: {dict(d)}" for f, d in sorted(bad.items())))


def test_governance_probe_comparand_no_sibling():
    """statement_integrity's comparand is THIS closure's probe, never a sibling attempt's body.

    The detbank_verify residual (2026-06-22): with several attempts writing probes for the same target into
    one scratch, the old finder recency-fell-back to a SIBLING when the stored proof_text didn't substring-
    match (a pool/cold splice reflows the proof). Comparing the original source against a sibling's signature
    both false-rejects a clean closure and risks false-admit. The fix matches whitespace-normalized AND
    refuses the sibling-fallback when proof_text is present-but-unmatched (withhold → integrity_unverified).
    """
    from ztare.leanmill.solver.solver_core import _match_closing_probe, _selftest_match_closing_probe
    _selftest_match_closing_probe()  # reflow-match + sibling-refusal + legacy-fallback battery
    sig = "theorem T (n : Nat) : n = n"
    own = f"import Mathlib\n{sig} := by\n    rfl\n#print axioms T\n"       # reflowed (4-space) `rfl`
    sib = "import Mathlib\ntheorem T (n : Nat) (h : False) : n = n := by\n  simp\n"  # weakened sibling
    # reflowed proof_text pins its OWN probe, never the altered sibling
    _, _, mk = _match_closing_probe([("/sib", sib), ("/own", own)], "T", "by rfl")
    assert mk == "matched"
    # present-but-unmatched ⇒ refuse the sibling comparand (withheld, not a wrong-comparand verdict)
    _, _, mk2 = _match_closing_probe([("/sib", sib)], "T", "by exact rfl")
    assert mk2 == "withheld_unmatched"


def test_dead_api_leaf_probed_once():
    """A 429-dead API leaf (kimi) is probed at most ONCE per process, then dispatch routes straight to CLI.

    The consc_camp_0622hard waste (2026-06-22): kimi passed the start-of-run liveness probe, then 429'd on
    every real dispatch — and nothing remembered, so each dispatch paid a probe-then-failover tax (9× in one
    run), burning the wall-clock the live CLI leaf needed to close the crux. Process-scoped, per-runtime,
    fail-safe (the cache only ever routes to the reliable CLI; the kernel re-verifies every closure)."""
    from ztare.leanmill.solver.agentic_leaf import _selftest_dead_api_cache
    _selftest_dead_api_cache()


def test_pool_honors_dead_api_cache():
    """The proposer pool's API path honors the SAME process dead-API cache as the leaf. The bug (2026-06-22):
    the leaf's dead-API protection lived only in `agentic_leaf.default_dispatch`, so the pool's API proposers
    (`llm_runtime.call_text`, default 300s + cross-model fallback) hung the whole proposer WAVE on a dead model
    — the forgotten sibling of the dead-API-leaf class. A known-dead API model must now be skipped (None) without
    a call_text, and a dispatch_fn injection must still bypass the API path entirely."""
    from ztare.leanmill.solver.agentic_leaf import _DEAD_API_RUNTIMES
    from ztare.leanmill.solver.proposer_pool import propose_with_model
    _DEAD_API_RUNTIMES.discard("kimi")
    try:
        _DEAD_API_RUNTIMES.add("kimi")
        # kimi is an API model (not a subscription leaf) → API branch → dead-cache skip → None (no call_text)
        assert propose_with_model("kimi", "prove it", repo=".", timeout=10) is None
        # an injected dispatch_fn bypasses the API path and still works even for a dead-cached model
        out = propose_with_model("kimi", "p", repo=".", timeout=10,
                                 dispatch_fn=lambda m, p: "```lean\nby rfl\n```")
        assert out is not None and out.proof_text == "by rfl", out
    finally:
        _DEAD_API_RUNTIMES.discard("kimi")


def test_dag_audit_kernel_circularity_catches_renamed_restatement():
    """The decomposition audit rejects a sub-lemma that is the goal G with variables RENAMED (same Prop).

    The consc_camp_0622hard over-decomposition (2026-06-22): the planner offered `iso_lemma1` = the WHOLE
    target with `E→q, R→Q` renamed as a "sub-lemma." The textual circularity check (`_norm_ws(==)`) can't see
    an α-rename, so the no-op DAG was accepted and a directly-provable goal got fragmented. The kernel leg
    (`@G = @Lᵢ := rfl` via the canonical statement_integrity oracle) catches it. ENHANCEMENT-ONLY + fail-open:
    rfl fires only on a genuine defeq (never rejects a real sub-lemma) and the leg is GATED on the caller
    threading the goal statement (so it is byte-parity when absent — verified here without invoking Lean)."""
    from pathlib import Path
    import ztare.leanmill.solver.statement_integrity as _si
    import ztare.gates.v33_preflight_risk_detector as _v33
    from ztare.leanmill.solver.conjecture import decomposition_dag_audit
    G_src = "theorem G (E : Nat -> Nat) : (∀ a : Nat, E a = E a) := by sorry"
    L = "theorem isoL (q : Nat -> Nat) : (∀ a : Nat, q a = q a) := by sorry"   # G renamed E->q (same Prop)
    chain = "theorem G (E : Nat -> Nat) : (∀ a : Nat, E a = E a) := by exact isoL E"
    saved_eq, saved_cp = _si.kernel_type_equiv_fn, _v33._compile_probe
    factory_calls = {"n": 0}
    try:
        _v33._compile_probe = lambda *a, **k: False    # never touch real Lean in this unit test

        def _factory(name, root):
            factory_calls["n"] += 1
            return lambda a, b: True                    # oracle: the renamed sub-lemma IS the same Prop as G
        _si.kernel_type_equiv_fn = _factory
        # (1) WITH the goal statement threaded → kernel-circular reject (returns before any compile leg)
        passed, v = decomposition_dag_audit([L], chain, ["isoL"], Path("/tmp"), 30,
                                            goal_source=G_src, goal_name="G")
        assert passed is False and "CIRCULAR (kernel" in v.get("killed", ""), v
        # (2) PARITY: WITHOUT the goal statement the kernel leg is never entered (oracle factory not called)
        factory_calls["n"] = 0
        decomposition_dag_audit([L], chain, ["isoL"], Path("/tmp"), 30)   # no goal_source/goal_name
        assert factory_calls["n"] == 0, "kernel-circularity leg ran without goal_source (parity broken)"
    finally:
        _si.kernel_type_equiv_fn, _v33._compile_probe = saved_eq, saved_cp


def test_closure_conservation_flags_unratified_closed():
    """Every `closed` attempt must trace to a RATIFICATION (a ratified=1 row OR a closure cert). A `closed` with
    NEITHER is a producer that recorded a closure it never put through governance — the proposer-pool drop, where
    the pool wrote a bare-name `closed/ratified=NULL` row while governance stamped a DIFFERENT row_id, so the
    target read closed-NOT-ratified and the run summaries reported it as a win. trust_conservation_audit checks
    ratified⟹cert; this is the inverse net (closed⟹ratification) that would have caught it. Hermetic: a temp
    sqlite + jsonl ledger, no Lean / DB-of-record. (Verified on the real buggy run: it flags exactly the two
    factorization targets the pool 'closed' but never ratified.)"""
    import json
    import sqlite3
    import tempfile
    from pathlib import Path
    from ztare.leanmill.run_standards import closure_telemetry_conservation_audit
    d = tempfile.mkdtemp()
    db = str(Path(d) / "attempts.db")
    led = str(Path(d) / "certs.jsonl")
    con = sqlite3.connect(db)
    con.execute("create table attempts (row_id text, attempt_at text, outcome text, compile_ok int, "
                "ratified int, move text, run_tag text)")
    ts = "2026-06-22T01:00:00+00:00"
    con.executemany("insert into attempts values (?,?,?,?,?,?,?)", [
        # (a) THE BUG: a 'closed' compile_ok row with NO ratified and NO cert → MUST be flagged
        ("dropped_target", ts, "closed", 1, None, "proposer_pool", "t"),
        # (b) a legit closure: 'closed' with ratified=1 stamped → conserved (excluded from the claim set)
        ("adhoc::good_target", ts, "closed", 1, 1, "native_hammer", "t"),
        # (c) a 'closed' with no ratified but a CERT for it → conserved (traceable to ratification evidence)
        ("adhoc::cert_target", ts, "closed", 1, None, "claude_warm", "t"),
    ])
    con.commit()
    con.close()
    Path(led).write_text(json.dumps({"target": "cert_target", "outcome": "closed", "ts": ts}) + "\n",
                         encoding="utf-8")
    res = closure_telemetry_conservation_audit("2026-06-22T00:00:00+00:00", run_tag="t", db_path=db, ledger=led)
    assert res["ok"] is False, res
    assert any("dropped_target" in v for v in res["violations"]), res
    assert not any("good_target" in v for v in res["violations"]), res    # ratified=1 → conserved
    assert not any("cert_target" in v for v in res["violations"]), res    # has a cert → conserved


def test_except_audit_catches_swallowed_nameerror():
    """A stdlib name used inside a SWALLOWING try/except with no in-scope import is flagged (the silent-
    NameError / dead-instrument class — the `try/except: pass` that uses `re`/`json`/`Path` without importing
    it, NameErrors on every call, and silently no-ops). The four CORRECT patterns are NOT flagged: a local
    `import`, an aliased local import (the fix idiom), a re-raise (not swallowing), and a module-level import."""
    import tempfile
    import textwrap
    from pathlib import Path
    from ztare.leanmill.except_audit import scan_file
    d = Path(tempfile.mkdtemp())
    bug = d / "bug.py"
    bug.write_text(textwrap.dedent('''
        def f(x):
            try:
                return re.sub("a", "b", x)   # `re` never imported in scope -> NameError, swallowed
            except Exception:
                pass
    '''), encoding="utf-8")
    hits = scan_file(bug)
    assert any(nm == "re" and fn == "f" for (_f, _ln, fn, nm) in hits), hits
    clean = d / "clean.py"
    clean.write_text(textwrap.dedent('''
        import os
        def local_import(x):
            try:
                import re
                return re.sub("a", "b", x)
            except Exception:
                pass
        def aliased(x):
            import re as _re
            try:
                return _re.sub("a", "b", x)
            except Exception:
                pass
        def reraises(x):
            try:
                return re.sub("a", "b", x)
            except Exception:
                raise
        def module_imported(x):
            try:
                return os.path.join(x, "y")
            except Exception:
                pass
    '''), encoding="utf-8")
    assert scan_file(clean) == [], scan_file(clean)


def test_no_swallowed_nameerror_in_leanmill():
    """The leanmill tree carries no swallowed-NameError pattern (the going-forward net for the silent-no-op
    class — like flag_audit for split-brain defaults). A new `try/except: pass` that uses a stdlib name without
    importing it fails here instead of silently no-opping in production."""
    from ztare.leanmill.except_audit import scan_tree
    hits = scan_tree()
    assert not hits, ("swallowed-NameError candidate(s) — add a local `import <name>` in the function:\n"
                      + "\n".join(f"  {f.split('/src/')[-1]}:{ln} in {fn}() uses `{nm}`"
                                  for (f, ln, fn, nm) in hits))


def test_no_cross_file_duplicate_function_bodies():
    """No two module-level leanmill functions in DIFFERENT files share a byte-identical body — the forgotten-
    sibling shape (fix one copy, the other rots; it false-rejected a whole campaign via the kernel-equiv oracle
    copies). Consolidate to ONE canonical home, callers re-export. Found + fixed 3 on build (the depth-0 colon
    finder, `_public_path`, `_read_policy` → lean_source/common/policy, 2026-06-22)."""
    from ztare.leanmill.structural_audit import duplicate_function_bodies
    dups = duplicate_function_bodies()
    assert not dups, ("cross-file duplicate function bodies — consolidate to one canonical home:\n"
                      + "\n".join("  " + "  ==  ".join(f"{f.split('/src/')[-1]}:{ln} {fn}()"
                                                       for f, fn, ln in g) for g in dups))


def test_ratification_has_single_chokepoint():
    """The ratification stamp (`UPDATE attempts SET ratified`) has exactly ONE writer
    (`_record_governance_verdict`). A second writer is a PARALLEL ratification path — precisely how the pool's
    'closed' telemetry diverged from real governance (the closure-drop). A new writer fails here: route it
    through the chokepoint, or justify the exception."""
    from ztare.leanmill.structural_audit import ratification_chokepoint_violations
    viol = ratification_chokepoint_violations()
    assert not viol, ("parallel ratification-stamp writer(s) — route through _record_governance_verdict:\n"
                      + "\n".join(f"  {f.split('/src/')[-1]}:{ln} {fn}()" for f, fn, ln in viol))


def test_dup_detector_actually_fires():
    """The duplicate-body detector is not trivially passing — it fires on a real cross-file byte-identical
    non-trivial function. Hermetic: two temp files with the same body."""
    import tempfile
    import textwrap
    from pathlib import Path
    from ztare.leanmill.structural_audit import duplicate_function_bodies
    d = Path(tempfile.mkdtemp())
    body = textwrap.dedent('''
        def shared(xs):
            total = 0
            seen = []
            for x in xs:
                if x > 0:
                    total += x * 2
                    seen.append(x)
                elif x < 0:
                    total -= x
                else:
                    total += 1
            return total, seen
    ''')
    (d / "a.py").write_text(body, encoding="utf-8")
    (d / "b.py").write_text(body, encoding="utf-8")
    groups = duplicate_function_bodies(root=d)
    assert any(len(g) == 2 and {fn for _f, fn, _ln in g} == {"shared"} for g in groups), groups


def test_campaign_probe_assembler_citable_in_scope():
    """Notes-path cure (the 'text-context ≠ compile-scope' bug class): `assemble_campaign_probe` is the SINGLE
    source of truth for a target's COMPILE SCOPE. It MUST put every proven shelf lemma IN SCOPE (before the
    target) so a lemma advertised 'citable' in the notes is actually citable, AND dedup shared definitions
    (theory-building targets inline the same `def`/`structure`) so composing never duplicate-declares; on an
    unresolvable conflict it falls back to the bare target, never a wrong merge. This is the notes-path analogue
    of the conservation/chokepoint guards: it fails CI if the assembler ever stops enforcing citable⟺in-scope, or
    if `default_solve` reintroduces a hand-rolled concat instead of routing through the assembler."""
    import inspect
    from ztare.leanmill.solver.autoformalize import assemble_campaign_probe, default_solve

    # citable ⟺ in-scope: shelf theorems land BEFORE the target; exactly one import header
    shelf = "import Mathlib\ntheorem lemA : True := trivial\n\ntheorem lemB : True := trivial"
    tgt = "import Mathlib\ntheorem tgt : True := by have := lemA; have := lemB; trivial"
    body, info = assemble_campaign_probe(tgt, [shelf])
    assert info["composed"] and info["shelf_theorems"] == 2, info
    assert body.count("import Mathlib") == 1, "exactly one import header"
    assert body.index("theorem lemA") < body.index("theorem tgt"), "shelf must be in scope before the target"
    assert body.index("theorem lemB") < body.index("theorem tgt")

    # theory-building: shared def/structure dedup to ONCE, ordered defs < shelf < target (no duplicate-declare)
    sh = "import Mathlib\ndef Foo : Nat := 0\nstructure M where x : Nat\n\ntheorem lemA : Foo = 0 := rfl"
    tg = ("import Mathlib\ndef Foo : Nat := 0\nstructure M where x : Nat\n\n"
          "theorem tgt : Foo = 0 := by have := lemA; rfl")
    b2, i2 = assemble_campaign_probe(tg, [sh])
    assert i2["composed"] and b2.count("def Foo") == 1 and b2.count("structure M") == 1, (i2, b2)
    assert b2.index("def Foo") < b2.index("theorem lemA") < b2.index("theorem tgt"), "defs < shelf < target"

    # conflict (same name, DIFFERENT body) ⇒ fall back to the bare target, never a silent wrong merge
    c_sh = "import Mathlib\ndef Foo : Nat := 0\ntheorem lemA : Foo = 0 := rfl"
    c_tg = "import Mathlib\ndef Foo : Nat := 1\ntheorem tgt : Foo = 1 := rfl"
    b3, i3 = assemble_campaign_probe(c_tg, [c_sh])
    assert not i3["composed"] and i3["reason"] == "conflict" and "lemA" not in b3, i3
    # OBSERVABILITY: the conflict must NAME the drifted decl + carry both divergent bodies (so the orphaned-shelf
    # cause is readable in the log, never hand-diffed from the cert ledger — the APR `AbsolutePriority` drift class).
    assert i3["conflicts"] and i3["conflicts"][0]["name"] == "Foo", i3
    assert i3["conflicts"][0]["kept"] != i3["conflicts"][0]["rejected"], i3["conflicts"]

    # COMMENT-INSENSITIVE compose (2026-06-24): with the established-vocabulary cure the target copies the canonical
    # def VERBATIM incl. the theory file's trailing `/-- … -/` doc-comment, while the banked lemma probes carry the
    # comment-free body. These are SEMANTICALLY identical → they MUST compose (the old whitespace-only `_norm_block`
    # false-conflicted on the doc-comment alone, which would have re-orphaned the shelf even after the vocab fix).
    cc_sh = "import Mathlib\ndef AP (n : Nat) : Prop := n = 0\ntheorem apL : AP 0 := rfl"
    cc_tg = "import Mathlib\ndef AP (n : Nat) : Prop := n = 0\n/-- Anchor: AP is the zero predicate. -/\ntheorem apT : AP 0 := rfl"
    bcc, icc = assemble_campaign_probe(cc_tg, [cc_sh])
    assert icc["composed"] and bcc.count("def AP ") == 1, ("comment-only diff must compose to one def", icc)
    # but a REAL semantic difference (extra conjunct) must STILL conflict — soundness of the check is intact
    sem_tg = "import Mathlib\ndef AP (n : Nat) : Prop := n = 0 ∧ True\ntheorem apT : AP 0 := And.intro rfl trivial"
    _, isem = assemble_campaign_probe(sem_tg, [cc_sh])
    assert not isem["composed"] and isem["reason"] == "conflict", ("semantic diff must still conflict", isem)

    # default_solve must ROUTE through the assembler (the notes-path discipline), not a hand-rolled concat
    assert "assemble_campaign_probe" in inspect.getsource(default_solve), \
        "default_solve must build compile scope via the assembler (single source of truth, no naive concat)"


def test_leaf_recovers_proof_from_response_not_just_file():
    """The 2026-06-23 'leaf solved it but didn't write the file' RCA: the warm leaf (claude opus) emitted a
    CORRECT proof in its RESPONSE but left the probe `sorry`, so the harness verified the untouched file and
    discarded a solved lemma as `uses_sorry` (the Topkis iso_lemma2, a 7-line proof). `_recover_proof_from_response`
    salvages it — extract the fenced Lean from the response, splice into the probe, RE-VERIFY (kernel-gated).
    Fails CI if recovery stops working OR stops being sound (a sorried/failing response must NOT be 'recovered',
    and the probe must be restored — never leave a broken file or mint a false closure)."""
    import tempfile
    from pathlib import Path
    from ztare.leanmill.solver.agentic_leaf import _recover_proof_from_response
    orig = "import Mathlib\n\ntheorem foo : True := by\n  sorry\n"
    with tempfile.TemporaryDirectory() as d:
        def mk(p):
            return lambda: (("sorry" not in p.read_text(encoding="utf-8")) and ("trivial" in p.read_text(encoding="utf-8")), "")
        # proof-body in the response ⇒ recovered (returns the proof string, TRUTHY); file no longer sorried
        p = Path(d) / "a.lean"; p.write_text(orig, encoding="utf-8")
        assert _recover_proof_from_response("done.\n```lean\ntrivial\n```", p, "foo", mk(p))  # truthy proof str
        assert "sorry" not in p.read_text(encoding="utf-8")
        # SOUND: a sorried response is NOT recovered (falsy ""), and the probe is restored unchanged
        p2 = Path(d) / "b.lean"; p2.write_text(orig, encoding="utf-8")
        assert not _recover_proof_from_response("```lean\nby sorry\n```", p2, "foo", mk(p2))
        assert p2.read_text(encoding="utf-8") == orig
        # SOUND: a candidate that fails re-verify restores the probe (no broken file, no false closure)
        p3 = Path(d) / "c.lean"; p3.write_text(orig, encoding="utf-8")
        assert not _recover_proof_from_response("```lean\nbogus_tactic\n```", p3, "foo", lambda: (False, ""))
        assert p3.read_text(encoding="utf-8") == orig


def test_leaf_dispatch_is_per_target_session_tagged():
    """The 2026-06-23 cross-target session-bleed RCA ("the agent thinks the file is already proven"): `solve_leaf`
    dispatched with NO `agent_tag`, so the warm agent session was repo-scoped — SHARED across every target in a
    run. Claude resumed another target's conversation and asserted "intact from the previous turn" while THIS
    target's probe was still `sorry`, so the real proof was never written and a solved goal was discarded. The fix:
    `solve_leaf` tags the session PER TARGET (`_agent_tag` from target+probe), keeping warm-resume WITHIN a target
    but a fresh session ACROSS targets — the warm REPL is untouched. This guard fails CI if `solve_leaf` stops
    computing a per-target tag or any proving dispatch goes out untagged (regressing to the shared session)."""
    import inspect
    from ztare.leanmill.solver.agentic_leaf import solve_leaf
    src = inspect.getsource(solve_leaf)
    assert "_agent_tag = " in src, "solve_leaf must compute a per-target _agent_tag (else the warm session bleeds across targets)"
    # the direct + decompose attempts and their timeout-retries = 4 proving dispatches; each must carry the tag
    assert src.count("agent_tag=_agent_tag") >= 4, (
        "every solve_leaf proving dispatch must pass the per-target agent_tag; "
        f"found only {src.count('agent_tag=_agent_tag')}")


def test_direct_leaf_warmcheck_rejects_sorry():
    """The 2026-06-23 "agent thinks the file is proven" RCA: the warm-check (`lean_check_server --check`) defaults
    to ACCEPTING `sorry` ("OK — zero errors (1 sorry)"), so in DIRECT mode the agent read the sorried stub as
    "compiled cleanly" and stopped — the harness verify then rejected the sorry. The DIRECT leaf prompt must pass
    `--reject-sorry` so the agent's checker AGREES with the harness (sorry = error); DECOMPOSE must NOT (its
    `-- GAP:` sub-lemma sorries are intentional). Fails CI if that mode-targeting regresses."""
    import os
    from ztare.leanmill.solver.agentic_leaf import _leaf_prompt
    prev = os.environ.get("ZTARE_LEANMILL_LEAN_SOCKET")
    os.environ["ZTARE_LEANMILL_LEAN_SOCKET"] = "/tmp/test_sock"
    try:
        # check the COMMAND carries the flag (not just the explanatory mention `` `--reject-sorry` ``)
        assert "p.lean --reject-sorry" in _leaf_prompt("foo", "True", "p.lean", mode="direct"), \
            "DIRECT leaf warm-check COMMAND must pass --reject-sorry (else a sorried stub reads as 'compiled cleanly')"
        assert "p.lean --reject-sorry" not in _leaf_prompt("foo", "True", "p.lean", mode="decompose"), \
            "DECOMPOSE warm-check command must NOT reject sorry (intentional -- GAP: sub-lemmas)"
    finally:
        if prev is None:
            os.environ.pop("ZTARE_LEANMILL_LEAN_SOCKET", None)
        else:
            os.environ["ZTARE_LEANMILL_LEAN_SOCKET"] = prev


def test_probe_ref_matches_verified_probe_path():
    """THE 2026-06-23 root-cause bug ("leanmill can't close a trivial target"): `solve_leaf` told the agent to
    edit `probe_ref` while the harness wrote the stub to + verified `probe = probe_dir(...)`. With
    ZTARE_LEANMILL_RUN_SCRATCH set, `probe_dir` adds a run subdir but the hard-coded `.solver_scratch/<name>`
    probe_ref OMITTED it — so the agent wrote a CORRECT, sorry-free proof to one path and the harness read the
    sorried stub at another and discarded EVERY proof. probe_ref MUST be derived from `probe` so the path the
    agent edits and the path the harness verifies can never drift. Fails CI if the hard-coded form returns."""
    import os, inspect
    from ztare.leanmill.solver.agentic_leaf import solve_leaf, probe_dir
    src = inspect.getsource(solve_leaf)
    assert "os.path.relpath(str(probe), str(project_dir))" in src, \
        "probe_ref must be derived from `probe` (os.path.relpath), not a hard-coded `.solver_scratch/<name>` that drifts from the run-scratch subdir"
    # behaviorally: with a run subdir set, probe_ref carries it (so it equals the verified probe's rel path)
    prev = os.environ.get("ZTARE_LEANMILL_RUN_SCRATCH")
    os.environ["ZTARE_LEANMILL_RUN_SCRATCH"] = "guardrun"
    try:
        import tempfile
        d = tempfile.mkdtemp()
        probe = probe_dir(d) / "RobustProbe_x.lean"
        assert os.path.relpath(str(probe), d) == os.path.join(".solver_scratch", "guardrun", "RobustProbe_x.lean")
    finally:
        if prev is None:
            os.environ.pop("ZTARE_LEANMILL_RUN_SCRATCH", None)
        else:
            os.environ["ZTARE_LEANMILL_RUN_SCRATCH"] = prev


def test_path_drift_visibility_net_recovers_sibling_proof():
    """VISIBILITY for the 2026-06-23 RCA class: when the harness verifies a non-closing probe but a sorry-free,
    kernel-verifying proof of the SAME target sits at a SIBLING scratch path (the silent-discard signature of a
    probe-path drift), the leaf surfaces it LOUDLY and recovers it — and a sorried sibling is never recovered (no
    false closure). This is the operator's "we had no visibility, the engine ran for hours discarding correct
    proofs" lesson turned into a self-healing alarm."""
    from ztare.leanmill.solver.agentic_leaf import _selftest_scratch_drift_recovery
    _selftest_scratch_drift_recovery()


def test_solve_adhoc_exposes_preverified_proof_governance_path():
    """The canonical 'send a compiling proof straight to governance' entry: solve_adhoc accepts a
    `preverified_proof` that routes through the SAME `_preverified_proof` seam the pool champion uses
    (kernel compile + MNC + axiom audit + statement_integrity + cert), NO re-derivation. Guards that the
    public param exists and wires to row['_preverified_proof']."""
    import inspect
    from ztare.leanmill.solver.solver_core import solve_adhoc
    sig = inspect.signature(solve_adhoc)
    assert "preverified_proof" in sig.parameters, "solve_adhoc must expose a public preverified_proof param"
    src = inspect.getsource(solve_adhoc)
    assert 'row["_preverified_proof"]' in src and "_external_pv" in src, \
        "preverified_proof must wire to the _preverified_proof governance seam (not a new path)"


def test_robust_probe_name_single_sourced_no_drift():
    """The 2026-06-23 winner_probe bug: solve_robust WROTE `RobustProbe_<target>_<provider>_<i>` but recorded
    winner_probe (and solver_core read back) as `RobustProbe_<provider>_<i>` — so a kernel-VALID closure's probe
    was 'unreadable' and the proof was discarded (fail-closed). World-class cure (the operator's anti-sibling
    principle): ONE canonical namer (`robust_probe_name`/`robust_probe_glob`), every writer + recorder + reader
    routed through it. This guard fails if a produced name isn't matched by the reader glob, or a stale inline
    `RobustProbe_{...provider...}` pattern reappears at any write/read site."""
    import fnmatch, inspect
    from ztare.leanmill.solver.agentic_leaf import robust_probe_name, robust_probe_glob, solve_robust
    from ztare.leanmill.solver import solver_core
    # (a) round-trip: every produced name is found by the canonical glob (odd chars + i>0 included)
    for tgt in ("iso_lemma1", "topkis::weird name/v2", "supermodular_argmaxSet_isSublatticeSet"):
        for prov in ("claude", "codex"):
            for i in (0, 3, 11):
                nm = robust_probe_name(tgt, prov, i)
                assert fnmatch.fnmatch(nm, robust_probe_glob(tgt, prov)), (nm, robust_probe_glob(tgt, prov))
                assert fnmatch.fnmatch(nm, robust_probe_glob(tgt)), nm   # provider-agnostic glob matches too
    # (b) solve_robust builds the name ONCE and records that SAME string as winner_probe (single source)
    src = inspect.getsource(solve_robust)
    assert "robust_probe_name(" in src and '"winner_probe": _probe_name' in src, \
        "solve_robust must build the probe name ONCE and record that SAME _probe_name as winner_probe"
    assert "RobustProbe_{provider}_{i}" not in src and "RobustProbe_{_tgt_seg}" not in src, \
        "stale inline RobustProbe naming reappeared in solve_robust — route through robust_probe_name"
    # (c) the solver_core readback reconstructs via the canonical helper, not the stale hardcoded pattern
    rsrc = inspect.getsource(solver_core._agentic_leaf_warm_solve)
    assert "RobustProbe_{winner}_0" not in rsrc and "RobustProbe_{winner}_*" not in rsrc, \
        "solver_core readback still uses the stale RobustProbe_{winner} name — route through robust_probe_name/glob"


def test_redundant_subsumed_instance_lint_catches_diamond():
    """The 2026-06-23 iso_lemma1 RCA: the planner formalized a sub-lemma with `[LE α]` ON TOP OF `[Preorder α]`
    — an instance diamond (the bare `[LE α]` shadows Preorder's transitive `≤`) that makes the statement
    UNPROVABLE (verified on the VPS: the same statement WITHOUT the `[LE α]` proves, WITH it fails). The
    canonical-parser lint must flag the bare order class, and must NOT false-flag `[Add α]` (Preorder doesn't
    provide Add) or a clean statement."""
    from ztare.leanmill.lean_source import redundant_subsumed_instances as rsi
    diamond = ("theorem iso_lemma1 {α : Type*} [Add α] [LE α] [Preorder α] [AddLeftMono α] "
               "[AddRightReflectLE α] {a b c d : α} (h : a + b ≤ c + d) (hd : d ≤ b) : a ≤ c := by sorry")
    off = rsi(diamond, "iso_lemma1")
    assert any(o.startswith("LE α") for o in off), off
    clean = ("theorem ok {α : Type*} [Add α] [Preorder α] [AddLeftMono α] {a b : α} (h : a ≤ b) : a ≤ b := by sorry")
    assert rsi(clean, "ok") == [], rsi(clean, "ok")
    # and solve_adhoc surfaces the diagnosis (wired, advisory)
    import inspect
    from ztare.leanmill.solver.solver_core import solve_adhoc
    s = inspect.getsource(solve_adhoc)
    assert "redundant_subsumed_instances" in s and "redundant_instances" in s, \
        "solve_adhoc must run + surface the formalization lint"


def test_statement_false_extraction_catches_proved_refutation():
    """The 2026-06-23 iso_lemma1 RCA: the agent PROVED the counterexample as a `theorem …_statement_false`
    rather than leaving the `-- STATEMENT-FALSE:` comment, so the comment-only scan missed it and the malformed
    sub-lemma was recorded `failed_compile` instead of routing to the kernel-gated reformulation. Extraction must
    now catch BOTH forms (the kernel still re-verifies ¬G downstream, so this can never launder)."""
    import tempfile, os
    from ztare.leanmill.solver.agentic_leaf import _extract_statement_false
    # comment form (unchanged)
    p1 = tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False)
    p1.write("theorem t : P := by\n  -- STATEMENT-FALSE: cex n=2\n  sorry\n"); p1.close()
    assert "cex n=2" in _extract_statement_false(p1.name)
    os.remove(p1.name)
    # proved-theorem form (the codex deviation that was missed)
    p2 = tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False)
    p2.write("import Mathlib\ntheorem iso_lemma1_statement_false : True := trivial\n"); p2.close()
    assert "refutation decl" in _extract_statement_false(p2.name)
    os.remove(p2.name)


def test_denotation_anchor_prompt_offers_weaker_anchors_not_equality_only():
    """The 2026-06-23 StrongSetLE denotation gap: the anti-decoy prompt offered only a FULL Mathlib-equality
    anchor, so a theory-building concept Mathlib lacks (the Veinott strong set order) fell through to
    `@no-anchor` → UNDERDETERMINED even though it is pinnable (`StrongSetLE {a} {b} ↔ a ≤ b`, kernel-proven).
    GENERAL-PURPOSE fix (not StrongSetLE-specific): the prompt must offer the weaker kernel anchors —
    special-case REDUCTION and CHARACTERIZATION — and reserve `@no-anchor` for genuinely unanchorable defs, so
    ANY built def of a Mathlib-absent concept can reach PINNED."""
    import inspect
    from ztare.leanmill.solver import prompts
    src = inspect.getsource(prompts)
    for route in ("OVERLAP-AGREEMENT", "SPECIAL-CASE REDUCTION", "CHARACTERIZATION"):
        assert route in src, f"denotation anchor prompt must offer the {route} route (not equality-only)"
    assert "is NOT sufficient when a reduction or characterization exists" in src, \
        "@no-anchor must require ruling out reduction/characterization, not just 'no Mathlib equal'"


def test_nonvacuity_check_flags_unwitnessed_set_property():
    """Gemini's 2026-06-23 empty-set critique: a ∀-over-membership Prop def (StrongSetLE, IsSublatticeSet) is
    VACUOUSLY true on ∅, so a theorem concluding it of a constructed set (the parametric argmax) can be true-
    but-empty. The vacuity leg (sibling of denotation, same kernel boundary) flags an unwitnessed vacuity-prone
    def as VACUITY_EXPOSED, accepts a kernel-verified witness as WITNESSED, and respects an honest
    `@vacuity-scope` flag. General + advisory (never gates), grounded in the canonical parser via `def_body`."""
    from ztare.leanmill.solver.def_denotation import (
        certify_nonvacuity, vacuity_prone_defs, VACUITY_EXPOSED, WITNESSED, VACUITY_SCOPED, NOT_APPLICABLE)
    src = ("import Mathlib\n\ndef StrongSetLE {X : Type*} [SemilatticeSup X] [SemilatticeInf X] (s u : Set X) : "
           "Prop :=\n  ∀ ⦃x y : X⦄, x ∈ s → y ∈ u → x ⊓ y ∈ s ∧ x ⊔ y ∈ u\n")
    assert "StrongSetLE" in vacuity_prone_defs(src)
    assert certify_nonvacuity(src, verify_fn=lambda w: True)["verdict"] == VACUITY_EXPOSED
    w = src + "theorem witness_StrongSetLE_nonvacuous : True := trivial\n"
    assert certify_nonvacuity(w, verify_fn=lambda x: True)["verdict"] == WITNESSED
    assert certify_nonvacuity(src + "-- @vacuity-scope: StrongSetLE: empty when unbounded\n",
                              verify_fn=lambda x: False)["verdict"] == VACUITY_SCOPED
    assert certify_nonvacuity("import Mathlib\ndef f : Nat := 0\n", verify_fn=lambda x: True)["verdict"] == NOT_APPLICABLE
    import inspect
    from ztare.leanmill.solver import prompts
    psrc = inspect.getsource(prompts)
    assert "GUARD AGAINST VACUOUS TRUTH" in psrc and "witness_" in psrc, "prompt must offer the vacuity guard"


def test_structural_triggers_general_not_overfit_and_map_to_real_moves():
    """Channel-2 move-recall triggers (move_atlas dual-channel, 2026-06-23 across-the-board extension) key on
    GENERAL goal shapes — not target-specific tokens — guarantee a shape-keyed move reaches the menu when
    prose-cosine misses it (hybrid dense+sparse retrieval), and must not over-fire on lattice ALGEBRA. Each maps
    to a move that EXISTS in the corpus (a trigger can't surface a phantom)."""
    from ztare.leanmill.solver import move_atlas as A
    # extremal: general optimization fires; lattice algebra / unrelated does NOT
    assert A._shape_extremal("IsGreatest S m") and A._shape_extremal("∃ x, IsLUB s x") and A._shape_extremal("⨆ i, f i")
    assert not A._shape_extremal("a ⊔ b = b ⊔ a") and not A._shape_extremal("Continuous f")
    # uniqueness / decidable: general fires; unrelated does not
    assert A._shape_uniqueness_forcing("∃! x, P x") and A._shape_uniqueness_forcing("Subsingleton G")
    assert not A._shape_uniqueness_forcing("a + b = c")
    assert A._shape_decidable("Decidable p") and A._shape_decidable("s : Finset α")
    assert not A._shape_decidable("x : ℝ")
    # every trigger surfaces a REAL corpus move
    from ztare.leanmill.solver.move_corpus import build_corpus
    ids = {e.move_id for e in build_corpus()}
    for _m, mid in A._STRUCTURAL_TRIGGERS:
        assert mid in ids, f"trigger surfaces non-existent move {mid}"


def test_statement_false_short_circuits_before_decompose(monkeypatch):
    """The 2026-06-23 iso_lemma1 LOOP: an agent flags STATEMENT-FALSE and the kernel confirms ¬goal, but the
    verify ran only in solve_adhoc's END epilogue — so the leaf burned the whole decompose + best-of-N (claude
    ~545s × N) on a provably-false lemma before the re-plan could fire. Fix: a flag-time kernel verifier
    short-circuits (skip decompose, stop best-of-N). A None verifier preserves old behavior (parity).
    Soundness unchanged — governance re-verifies ¬goal before any re-plan; this only stops wasted dispatches."""
    from ztare.leanmill.solver import agentic_leaf as A
    monkeypatch.setenv("ZTARE_LEANMILL_LEAN_WARM", "0")
    monkeypatch.setattr(A, "_extract_statement_false", lambda p: "cex: take n=0")
    common = dict(defs="", project_dir=".", repo=".", lake_bin="lake",
                  dispatch=lambda p, **k: "ALIVE", verify=lambda: (False, "uses_sorry"))
    # kernel-confirmed false ⇒ short-circuit: no decompose, flagged confirmed, only the direct round
    r = A.solve_leaf("True", target="t", statement_false_verifier=lambda: True, **common)
    assert r.statement_false_confirmed and not r.decomposed and r.rounds == 1, (r.statement_false_confirmed, r.decomposed, r.rounds)
    # NOT confirmed (agent wrong) ⇒ continue to decompose (don't abandon a possibly-provable lemma)
    r2 = A.solve_leaf("True", target="t", statement_false_verifier=lambda: False, **common)
    assert not r2.statement_false_confirmed and r2.decomposed, (r2.statement_false_confirmed, r2.decomposed)
    # no verifier ⇒ old behavior (decompose runs) — parity
    r3 = A.solve_leaf("True", target="t", statement_false_verifier=None, **common)
    assert not r3.statement_false_confirmed and r3.decomposed
    # wiring threaded all the way (leaf → best-of-N → solver_core)
    import inspect
    assert "statement_false_verifier" in inspect.signature(A.solve_robust).parameters
    from ztare.leanmill.solver import solver_core
    assert "statement_false_verifier=_sf_verifier" in inspect.getsource(solver_core._agentic_leaf_warm_solve)


def test_governed_def_revision_self_correction_path():
    """The autonomous self-correction path (2026-06-23): a kernel-confirmed-false lemma → governed def-revision
    → the agent STRENGTHENS the weak def, GATED so only a kernel-proven strengthening passes (anti-gaming) →
    re-attack. Guards the gate's soundness (strengthening accepted; unverified-witness rejected) + that the
    trigger is actually wired into the campaign loop (so it can't silently regress to a dead-end)."""
    from ztare.leanmill.solver.autoformalize_notes import governed_def_revision_gate, _detect_revised_def
    before = "import Mathlib\ndef D (n : Nat) : Prop := n ≥ 0\ntheorem other : True := trivial\n"
    after = ("import Mathlib\ndef D__pre (n : Nat) : Prop := n ≥ 0\ndef D (n : Nat) : Prop := n ≥ 0 ∧ n ≤ 9\n"
             "theorem witness_strengthen_D : ∀ n, D n → D__pre n := fun _ h => h.1\ntheorem other : True := trivial\n")
    assert _detect_revised_def(after) == "D"
    assert governed_def_revision_gate(before, after, "D", verify_fn=lambda w: w == "witness_strengthen_D")[0]
    assert not governed_def_revision_gate(before, after, "D", verify_fn=lambda w: False)[0]   # anti-gaming
    import inspect
    from ztare.leanmill.solver import autoformalize_notes as an
    src = inspect.getsource(an.autoformalize_from_notes)
    assert ("governed_def_revision(" in src and "SELF_CORRECT_DEFS" in src
            and "scan_probes_for_statement_false" in src), "self-correction trigger not wired into the campaign loop"


def test_anti_laundering_baseline_is_full_posed_source_not_truncated_context():
    """Char-length sibling RCA (2026-06-23): the anti-laundering soundness baseline (`original_source` →
    statement_integrity + canonical_reelaboration) was the LLM context `enriched_goal`, which
    `_build_solver_context` TRUNCATES to the last `_MAX_CONTEXT_CHARS` (12k). For a theory-first target whose
    defs live >12k chars before it, those defs are ABSENT from the baseline but PRESENT in the full
    `closure_source` probe → canonical_reelaboration strips the substrate's OWN defs as 'added shadow defs' →
    FALSE `context_hijack_confirmed`. Fix: the gate baseline derives from the COMPLETE posed source. This guard
    fails if the baseline reverts to the truncated context, or the preverified champion path stops threading
    the verbatim row source. (Soundness note: this class only ever causes false REJECTS, never false ACCEPTS.)"""
    import inspect
    from ztare.leanmill.solver import solver_core
    vac = inspect.getsource(solver_core._validate_against_contract)
    assert "_orig_for_gate" in vac and "posed_source" in vac, \
        "anti-laundering baseline must derive from posed_source, not the truncated enriched_goal"
    assert "original_source=_orig_for_gate" in vac, "the kernel call must use the full-posed-source baseline"
    assert "original_source=enriched_goal" not in vac, \
        "the TRUNCATED enriched_goal must NOT be the anti-laundering baseline (char-length false-hijack regress)"
    mod_src = inspect.getsource(solver_core)
    assert "posed_source=_pv_srctext" in mod_src, \
        "the preverified champion close must thread the verbatim row source (_pv_srctext) as the integrity baseline"


def test_axiom_probe_parses_full_output_not_truncated_tail():
    """Char-length sibling (2026-06-23): `probe_axioms_via_augment` fed a length-TRUNCATED tail
    (`run_lake_compile_source` returned `output[-1200:]`) into `parse_axiom_output` — a MULTI-decl probe's
    earliest `#print axioms` blocks fall outside the window and silently drop from the audit. Hardened to parse
    the COMPLETE compiler output via `run_lake_compile` (the same full-output path the live `audit_axioms_subset`
    uses). Guard fails if it reverts to parsing a truncated tail."""
    import inspect
    from ztare.gates import lean_compile_primitives as lcp
    src = inspect.getsource(lcp.probe_axioms_via_augment)
    assert "run_lake_compile(" in src, "axiom probe must compile via the full-output run_lake_compile"
    assert "parse_axiom_output(tail)" not in src and "run_lake_compile_source(" not in src, \
        "axiom probe must NOT parse a length-truncated tail (char-length false-inconclusive regress)"


def test_self_correction_loop_agent_elects_falsify_goldilocks():
    """Self-correction LOOP (2026-06-23, topkis_general RCA) — the GOLDILOCKS form (the operator's "why
    deterministic instead of the agent seeing it?"). The target pass, faithful to the literal NL
    ("single-crossing"), formalizes the WEAK def → FALSE. The DECISION to falsify is the AGENT's (a strategy/move,
    upstream agency), NOT a deterministic harness "falsify-on-stall" (that creep was tried + REVERTED). The agent
    elects FALSIFY at the strategy fork — MECE: Dim A (TRUTH: true→prove / false→falsify) × Dim B (HOW: direct/
    decompose); FALSIFY is the truth-branch, not a flat peer (docs §4.3a). A kernel-CONFIRMED ¬G then drives the
    EXISTING reformulation re-entry (`_solve_refutation` HARD path on outcome="falsified" → re-attack stronger).
    The kernel is the ONLY deterministic part (the soundness boundary)."""
    import inspect
    from ztare.leanmill.solver import solver_core, autoformalize
    import ztare.leanmill.solver.autoformalize_notes as an_mod
    # (a) the deterministic creep is GONE: no advisory steer, no falsify-on-stall in solve_adhoc.
    assert not hasattr(an_mod, "_supersession_steer") and not hasattr(an_mod, "_substrate_falsity_proofs"), \
        "the subsumed advisory steer must be REMOVED (replaced by the agency loop), not left as a 2nd surface"
    sa = inspect.getsource(solver_core.solve_adhoc)
    assert "stall-fallback" not in sa and "_reformulate_on" not in sa, \
        "the deterministic falsify-on-stall must be REVERTED — the agent decides to falsify, not the harness"
    # (b) the strategy fork is the MECE 3-way verdict (truth × how); FALSIFY is an agent-electable strategy.
    assert hasattr(solver_core, "_agent_strategy_verdict") and not hasattr(solver_core, "_agent_recommends_decompose"), \
        "the binary decompose-ask must be replaced by the 3-way truth×how verdict (SOLVE_DIRECT/DECOMPOSE/FALSIFY)"
    sv = inspect.getsource(solver_core._agent_strategy_verdict)
    assert all(tok in sv for tok in ("FALSIFY", "DECOMPOSE", "SOLVE_DIRECT")), "verdict must offer all three"
    from ztare.leanmill.solver import prompts as _p
    assert "FALSIFY" in _p.STRATEGY_ASSESSMENT_PROMPT and "TRUE" in _p.STRATEGY_ASSESSMENT_PROMPT, \
        "the strategy prompt must offer FALSIFY truth-first (Dim A), not a prove-only fork"
    # (c) solve_adhoc routes an AGENT-ELECTED FALSIFY (not a stall) through the kernel ¬G → outcome=falsified
    assert '_strategy.get("v") == "FALSIFY"' in sa and "verify_statement_false_claim" in sa \
        and '"outcome": "falsified"' in sa, \
        "solve_adhoc must route an AGENT-elected FALSIFY through kernel ¬G → outcome=falsified (drives reformulation)"
    # (d) the reformulation re-entry consumes a kernel-confirmed refutation and re-attacks (the loop's other half)
    af = inspect.getsource(autoformalize.autoformalize_and_solve)
    assert "_solve_refutation(" in af and "reformulate_budget" in af, \
        "the reformulation re-entry must consume the kernel-confirmed refutation and re-attack (strengthen move)"
    # (e) the reformulation feedback ORIENTS strengthening (the agent kept re-emitting the weak/refuted reading
    #     because the old text over-constrained it to "don't weaken / stay faithful"). Un-blind, do NOT launder:
    #     it must say STRENGTHEN, show the refuting case, and name NO specific def (no overfit / no answer-feeding).
    fb = autoformalize._reformulate_feedback("theorem t (h : Weak f) : G := by sorry", "counterexample at x=0 (ties)")
    assert "STRENGTHEN" in fb and "too weak" in fb and "counterexample at x=0" in fb, \
        "reformulate feedback must orient STRENGTHENING + surface the refuting case (the agent's evidence)"
    assert "OrdinalStrongSingleCrossing" not in fb and "Milgrom" not in fb, \
        "reformulate feedback must NOT name a specific def (that would be laundering / overfitting, not orienting)"
    # prompt TEXT lives in prompts.py (not inline in autoformalize) — the operator's "prompts go in prompts.py"
    from ztare.leanmill.solver import prompts as _pr
    assert hasattr(_pr, "REFORMULATE_FEEDBACK") and "REFORMULATE_FEEDBACK" in inspect.getsource(autoformalize._reformulate_feedback), \
        "reformulation prompt text must live in prompts.py, assembled (not inlined) by _reformulate_feedback"
    # (f) ROUTE THE AGENT'S OWN CORRECTION: the consolidation pass proves the corrected (strong) theorem, but the
    #     fresh re-formalizer re-derives weak from the NL. `_substrate_proven_shelf` surfaces the substrate's OWN
    #     proven (sorry-free) theorems so the reformulation can ADOPT + CITE one (operator: "the agent proposed a
    #     reformulation — why isn't that the path?"). Proven listed, sorried + scaffolding excluded; feedback says CITE.
    #     2026-06-23: reads the registered substrate .lean CONTENT (where consolidation BANKS proofs), NOT the notes
    #     markdown — canonical `decl_blocks`/`_decl_is_definition`/`extract_signature`, NO regex.
    substrate_lean = ("import Mathlib\n"
                      "theorem strong_ok (h : Strict f) : G := by exact h.elim\n"
                      "theorem weak_bad (h : Weak f) : G := by sorry\n"
                      "theorem witness_scaffold (h : Strict f) : True := by trivial\n")
    shelf = autoformalize._substrate_proven_shelf(substrate_lean)
    assert "strong_ok" in shelf and "weak_bad" not in shelf and "witness_scaffold" not in shelf, \
        "proven-shelf must list the PROVEN result, EXCLUDE the sorried one AND the engine's own witness_/anchor_ scaffolding"
    fb2 = autoformalize._reformulate_feedback("theorem t (h : Weak f) : G := by sorry", "cex", shelf)
    assert "ALREADY-PROVEN" in fb2 and "CITE" in fb2 and "strong_ok" in fb2, \
        "with a proven shelf, the reformulation must route the agent to ADOPT + CITE its OWN proven theorem"
    assert "if none matches" in fb2, "the shelf block must be ADVISORY (agent judges relevance), not coercive"
    # and it's wired into the re-entry through the ONE substrate reader (`_read_substrate_src`, canonical
    # parse_theory_file) — the SAME reader the formalize-context vocabulary injection uses (no sibling re-reads).
    assert "_substrate_proven_shelf(_read_substrate_src(notes, sandbox))" in af, \
        "the re-entry must feed the proven shelf via the ONE substrate reader (_read_substrate_src)"
    assert "parse_theory_file" in inspect.getsource(autoformalize._read_substrate_src), \
        "the one substrate reader must resolve the theory file via canonical parse_theory_file"


def test_established_vocabulary_single_door_prevents_def_drift():
    """ORPHANED-SHELF / def-drift cure (2026-06-24). The class bug: every formalization-context path surfaced def
    NAMES (via lemma signatures) but never the canonical def BODIES, so each self-contained probe re-authored the
    shared vocabulary from the prose — and a target that minted a divergent same-named def (APR `AbsolutePriority`:
    2-clause vs the proven 1-clause) silently orphaned its own shelf at compose time → exact_gap. The cure is the
    DEFINITION companion to `_substrate_proven_shelf`, injected at the ONE formalize chokepoint (no sibling)."""
    import inspect
    from ztare.leanmill.solver import autoformalize, prompts
    SRC = ("import Mathlib\n"
           "def AbsolutePriority (c p : Nat) : Prop := c = p\n"
           "abbrev ClaimSchedule := Nat\n"
           "theorem anchor_AbsolutePriority_iff : True := trivial\n"
           "theorem ap_main (c p : Nat) : AbsolutePriority c p ∨ True := Or.inr trivial\n")
    # the new extractor surfaces def BODIES verbatim (copy-pasteable); the proven-shelf companion drops them
    defs = autoformalize._substrate_established_defs(SRC)
    assert "def AbsolutePriority (c p : Nat) : Prop := c = p" in defs and "abbrev ClaimSchedule" in defs, defs
    assert "theorem" not in defs and "ap_main" not in defs, "vocabulary block is DEFS only (results go via _substrate_proven_shelf)"
    # the reuse-verbatim norm + escape hatch are present (agency: reuse OR extend-under-a-new-name)
    note = prompts.ESTABLISHED_DEFS_NOTE.format(defs=defs)
    assert "do NOT redefine" in note and "NEW name" in note and "bridge" in note, note
    # SINGLE DOOR: the formalize chokepoint builds the formalizer context with the vocabulary, and the multistep
    # escalation is NOT a context-blind sibling — it threads the SAME _fctx.
    src = inspect.getsource(autoformalize.autoformalize_and_solve)
    assert "_substrate_established_defs(_read_substrate_src(notes, sandbox))" in src, \
        "vocabulary must be sourced at the ONE formalize chokepoint via the one substrate reader"
    assert "default_formalize_multistep(_nl, context=_fctx" in src, \
        "the multistep escalation must NOT be context-blind — it threads the same _fctx (no sibling)"
    assert "context" in inspect.signature(autoformalize.default_formalize_multistep).parameters, \
        "default_formalize_multistep must accept context (so the escalation reuses canonical vocabulary)"


def test_candidate_proof_reuse_routes_through_single_governance_door():
    """ANTI-SCATTER enforcement (2026-06-24): a banked/pooled/external candidate proof is verified-in-context +
    governed + banked at exactly ONE seam — the `_preverified_proof` (`_pvp`) door in `solve()`, which splices into
    the FULL source (defs in scope), compiles campaign-aware, and runs the complete kernel governance. The recurring
    bug was each REUSE site (cache cite / pool / external) re-implementing its own splice+verify; the cache cite did
    it against the BARE goal (defs out of scope → silent skip → re-derive). This guard fails CI if the proof-cache
    pre-attack reintroduces a bespoke splice/verify instead of handing the candidate to the single door — so the
    consolidation can't silently un-consolidate (the door STAYS single without vigilance)."""
    import inspect, re as _re
    from ztare.leanmill.solver import solver_core
    src = inspect.getsource(solver_core.solve_adhoc)
    # isolate the proof-cache pre-attack region (between its marker and the proposer-pool pre-attack)
    m = _re.search(r"PRE-ATTACK LIBRARY CHECK.*?GOVERNED PROPOSER POOL pre-attack", src, _re.S)
    assert m, "could not locate the proof-cache pre-attack region"
    region = m.group(0)
    assert "_preverified_proof" in region, "the cache cite must hand the banked proof to the single _preverified_proof door"
    # it must NOT re-implement splice/verify itself — those belong to the one _pvp seam
    for banned in ("swap_sorry", "_verify_compile(", "_campaign_aware_proof_compiles(", "compile_probe_via_repl("):
        assert banned not in region, f"cache cite must NOT re-implement candidate verify/splice ({banned}); route through _pvp"
    # the ONE door exists and does the full-context verify + governance
    door = inspect.getsource(solver_core.solve)
    assert "_preverified_proof" in door and "_validate_and_maybe_close" in door, "the _pvp governance door must exist in solve()"


def test_planner_steering_surfaces_relevant_banked_rungs_not_recent():
    """Decomposition-steering cure (2026-06-24): the rung-adjacency advisory that steers the planner toward
    proven infrastructure surfaces the rungs most IDENTIFIER-RELEVANT to the goal, not merely the k most RECENT
    (recency silently hid the relevant banked atoms behind newer unrelated closures → the planner re-derived).
    Goldilocks: still advisory + deterministic surfacing; the agent decides the decomposition, the kernel audits."""
    from ztare.leanmill.solver.rung_adjacency import render_adjacency_block
    # a deeply-buried RELEVANT rung followed by >k unrelated recent closures
    relevant = "theorem feas_of_linearOrder (claims : ClaimSchedule ι) : DistributionFeasible claims (WaterfallDistribution claims)"
    proven = [relevant] + [f"theorem recent_unrelated_{i} : Nat.Prime {7+i}" for i in range(10)]
    goal = "theorem tgt (claims : ClaimSchedule ι) : ∃ pay, DistributionFeasible claims pay"
    recency = render_adjacency_block(proven, k=8)              # last-8 ⇒ EXCLUDES the buried relevant rung
    relev = render_adjacency_block(proven, goal=goal, k=8)     # overlap ⇒ surfaces it
    assert "feas_of_linearOrder" not in recency, "recency-mode buries the relevant rung (the bug)"
    assert "feas_of_linearOrder" in relev, "relevance-mode must surface the goal-relevant banked rung"
    # parity: no goal ⇒ recency behaviour unchanged
    assert render_adjacency_block(proven, k=8) == render_adjacency_block(proven, goal="", k=8)


def test_proof_cache_keyed_on_canonical_expr_hash_not_text():
    """The cache-never-hits cure (2026-06-24): proof reuse is keyed on the kernel `Expr.hash` of the target's
    de-Bruijn TYPE (α-/∀-fronting-invariant), computed from the warm REPL — NOT a text regex over the probe (which
    mis-keyed multi-decl `define_then_state` probes on their leading def's `:=`). solve_adhoc computes the key ONCE
    and passes it to BOTH the pre-attack lookup and the closure deposit, so deposit-key == lookup-key; the cache
    dual-indexes (Expr key + text key) and re-verifies every hit (so the key needs only recall, never precision)."""
    import inspect
    from ztare.leanmill.solver import solver_core
    from ztare.leanmill.solver.proof_cache import ProofCache
    from ztare.formal import repl_compile
    # the canonical-hash helper exists and is wired into solve_adhoc for BOTH lookup and deposit
    assert hasattr(repl_compile, "canonical_type_hash_via_repl")
    src = inspect.getsource(solver_core.solve_adhoc)
    assert "canonical_type_hash_via_repl" in src, "solve_adhoc must compute the canonical Expr-hash key"
    assert ".get(goal, key=_canon_key)" in src, "pre-attack lookup must use the canonical key"
    assert "key=locals().get(\"_canon_key\")" in src or "key=_canon_key" in src, "closure deposit must reuse the same key"
    # the cache stores/reads under the supplied key, dual-indexed with the text key, and re-keys H: keys on reload
    import tempfile, os as _os
    p = tempfile.mktemp(suffix=".jsonl")
    c = ProofCache(p)
    assert c.put("theorem a (h:p) : q := by sorry", "by exact e", key="K1")
    assert c.get("theorem a (h:p) : q := by sorry", key="K1") == "by exact e"           # Expr-key hit
    assert c.get("theorem DIFFERENT_TEXT : zzz := by sorry", key="K1") == "by exact e"   # variant, same Expr key ⇒ hit
    assert c.get("theorem a (h:p) : q := by sorry") == "by exact e"                       # text-key fallback (no REPL)
    assert ProofCache(p).get("theorem whatever : w", key="K1") == "by exact e"            # survives reopen
    _os.remove(p)


def test_def_shell_detection_canonical_and_shared_with_vocab():
    """Tasteful consolidation (2026-06-24): the def-shell GATE and the vocabulary EXCLUSION share ONE degeneracy
    core (`_degenerate_def_body`) over the canonical `decl_blocks` parser — NO hand-rolled decl regex, NO bare-vs-
    qualified name band-aid (the two never match on names; they ask the same predicate of the same block). Behavior
    is preserved: only `def`/`abbrev` constant shells are flagged (a structure/instance/axiom is not a 'shell')."""
    import inspect, re as _re
    from ztare.leanmill.solver import autoformalize
    SRC = ("import Mathlib\nnamespace NS\n"
           "abbrev ClaimSchedule (ι : Type*) := ι → NNReal\n"
           "def AbsolutePriority {ι : Type*} (c p : ClaimSchedule ι) : Prop := ∀ i : ι, p i = c i\n"
           "def ZeroPay (ι : Type*) : ClaimSchedule ι := fun _ => 0\n"     # degenerate witness (shell)
           "abbrev Genus : Prop := True\n"                                   # degenerate (shell)
           "instance : Inhabited Nat := ⟨0⟩\n"                              # NOT a shell (instance, not def/abbrev)
           "structure Conc where a : Nat\nend NS\n")
    shells = {n for n, _ in autoformalize.detect_def_shells(SRC)}
    assert "NS.ZeroPay" in shells and "NS.Genus" in shells, ("def/abbrev constant shells must be flagged", shells)
    assert not any(k in shells for k in ("NS.AbsolutePriority", "NS.ClaimSchedule", "NS.Conc")) \
        and not any("Inhabited" in s or "instance" in s for s in shells), ("concept/structure/instance NOT shells", shells)
    # the GATE and the VOCAB agree by construction: the same shells the gate flags are the ones vocab drops, and
    # the concept defs the gate keeps are the ones vocab surfaces — no name-matching, so no namespace band-aid.
    vocab = autoformalize._substrate_established_defs(SRC)
    assert "AbsolutePriority" in vocab and "ClaimSchedule" in vocab and "Conc" in vocab
    assert "ZeroPay" not in vocab and "def Genus" not in vocab and "Genus : Prop" not in vocab
    # no hand-rolled decl regex in the shell detector — it must parse via the canonical decl_blocks
    dsrc = inspect.getsource(autoformalize.detect_def_shells)
    assert "decl_blocks" in dsrc and "re.finditer" not in dsrc, "detect_def_shells must parse via canonical decl_blocks, not a regex"
    # and the vocab exclusion must NOT name-match (no `.split('.')` band-aid) — it asks the shared block predicate
    vsrc = inspect.getsource(autoformalize._substrate_established_defs)
    assert "_degenerate_def_body" in vsrc and ".split(\".\")" not in vsrc, "vocab exclusion must use the shared block predicate, not a name band-aid"


def test_faithfulness_reference_consults_single_refutation_ledger():
    """Single-LEDGER supersession (2026-06-23 — operator: false-negative + single entry point + NO parallel
    surface). A WEAK rendering can be faithful-to-NL yet FALSE → admitted + deposited as the store reference → it
    then wrongly gates the corrected STRONG rendering via the structural silent-weakening guard (the false-
    negative). Fix WITHOUT a parallel surface: the kernel ¬G is recorded to the EXISTING refutation ledger
    (`NoGoodStore`, failure class `statement_false`, canonical statement key); `FaithfulnessStore.reference()`
    CONSULTS that one ledger and drops the refuted rendering. Anti-gaming: recording requires the kernel ¬G;
    consulting only ever DROPS a gate-reference, never admits."""
    import tempfile, inspect
    from pathlib import Path
    from ztare.leanmill.solver.faithfulness_store import FaithfulnessStore
    from ztare.leanmill.solver.no_good_store import NoGoodStore
    from ztare.leanmill.solver import autoformalize
    # (a) NO parallel surface: the faithfulness store has NO own refutation recorder — refutations live in ONE ledger
    assert not hasattr(FaithfulnessStore, "mark_refuted"), \
        "refutations must route through the ONE ledger (NoGoodStore), not a parallel FaithfulnessStore.mark_refuted"
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        fs = FaithfulnessStore(dd / "solver_lane_faithfulness_store.jsonl")
        NL = "f single-crossing implies the argmax set is monotone"
        WEAK = "theorem t (h : SC f) : Mono := by sorry"
        fs.record(NL, WEAK, confirmed=True, fingerprint={"n_explicit_binders": 1}, source="firewall")
        assert (fs.reference(NL) or {}).get("statement") == WEAK     # weak is the reference (faithful-but-false)
        # the kernel ¬G is recorded to the ONE ledger (same dir, canonical key) — not a parallel store
        ng = NoGoodStore(dd / "solver_lane_no_good_store.jsonl")
        ng.record(WEAK, "statement_false", "cex: ties at the high parameter", confirmed=True)
        assert WEAK and ng.statement_false_keys(), "NoGoodStore must expose the statement_false keys for the consult"
        fs2 = FaithfulnessStore(dd / "solver_lane_faithfulness_store.jsonl")   # fresh instance (drops the cache)
        assert fs2.reference(NL) is None, "reference() must DROP a rendering the ONE ledger marked statement_false"
        # (b) the chokepoint records to the ONE ledger (NoGoodStore), with NO parallel mark_refuted
        src = inspect.getsource(autoformalize.autoformalize_and_solve)
        assert "NoGoodStore" in src and '"statement_false"' in src and "mark_refuted" not in src, \
            "the refutation chokepoint must record statement_false to the ONE ledger — no parallel surface"


def test_disclosed_strengthening_override_is_non_gamable():
    """Disclosed-strengthening override (refute-and-correct, 2026-06-23) — the firewall admits a round-trip-
    REJECTED strengthening ONLY when the literal NL is kernel-FALSE (¬G license). NON-GAMABLE: it ADMITS the
    legit licensed strengthening but REJECTS every laundering case — weakened conclusion, non-strengthening,
    vacuous, trivial/goal-as-hyp, and (default) no-license. A SIBLING of the prior_confirmed round-trip bypass;
    fail-closed; reuses the ONE refutation ledger + the firewall's own non_vacuous/non_trivial legs + the
    existing fingerprint parser (no parallel surface). This is the soundness-boundary regression guard."""
    import tempfile
    from pathlib import Path
    from ztare.leanmill.solver import autoformalize as A, solver_core, faithfulness_store as FS, no_good_store as NG
    _save = solver_core.OUT_DIR
    try:
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d); solver_core.OUT_DIR = dd
            NL = "single-crossing implies monotone"
            WEAK = "theorem t (h1 : A) : B ∧ C := by sorry"
            STRONG = "theorem t (h1 : A) (h2 : D) : B ∧ C := by sorry"
            WEAKENED = "theorem t (h1 : A) (h2 : D) : B ∨ C := by sorry"
            FS.FaithfulnessStore(dd / "solver_lane_faithfulness_store.jsonl").record(
                NL, WEAK, confirmed=True, fingerprint=A._parse_lean_statement(WEAK))
            NG.NoGoodStore(dd / "solver_lane_no_good_store.jsonl").record(WEAK, "statement_false", "cex", confirmed=True)
            ok = {"non_vacuous": True, "non_trivial": True}
            assert A._licensed_strengthening_admit(NL, STRONG, ok), "must ADMIT a licensed strengthening"
            assert A._licensed_strengthening_admit(NL, WEAKENED, ok) is None, "REJECT a weakened conclusion"
            assert A._licensed_strengthening_admit(NL, WEAK, ok) is None, "REJECT a non-strengthening (no added hyp)"
            assert A._licensed_strengthening_admit(NL, STRONG, {"non_vacuous": False, "non_trivial": True}) is None, "REJECT vacuous"
            assert A._licensed_strengthening_admit(NL, STRONG, {"non_vacuous": True, "non_trivial": False}) is None, "REJECT trivial/goal-as-hyp"
            assert A._licensed_strengthening_admit("unrelated claim", STRONG, ok) is None, "REJECT without the ¬G license"
            # GATE2 PRODUCTION-WIRING regression (2026-06-23): the production `autoformalize_and_solve` path supplies
            # NO consistency_fn, so `non_vacuous` is ABSENT (not True) — the gate must NOT require it (else the
            # override is DEAD e2e). It MUST require `non_trivial` (always populated; subsumes the vacuity probe) and
            # still reject an EXPLICIT consistency failure when one is supplied.
            assert A._licensed_strengthening_admit(NL, STRONG, {"non_trivial": True}), \
                "must ADMIT on the production signal set (non_trivial only; non_vacuous absent) — else override is dead"
            assert A._licensed_strengthening_admit(NL, STRONG, {"non_trivial": True, "non_vacuous": False}) is None, \
                "must still REJECT when a SUPPLIED consistency leg found a contradiction (non_vacuous False)"
            assert A._licensed_strengthening_admit(NL, STRONG, {"non_trivial": False}) is None, \
                "must REJECT a trivial/vacuous strengthening (non_trivial False subsumes the cheap-vacuity + instance probe)"
    finally:
        solver_core.OUT_DIR = _save


def test_literal_first_recovery_closes_the_loop_end_to_end(monkeypatch):
    """LITERAL-FIRST RECOVERY e2e (2026-06-23) — the INTEGRATION close, not a unit. The prior session built each
    component sound IN ISOLATION (firewall faithful-to-literal, FALSIFY election, the ONE statement_false ledger,
    the reformulation re-entry, the disclosed-strengthening override), but the firewall-REJECT path DEAD-ENDED: a
    substrate-primed agent that formalizes the STRENGTHENED claim directly is rejected as round-trip-weakened, no ¬G
    license is ever minted, and the override has nothing to act on (diagnosis: integration/sequencing, NOT iatrogenic
    harness). This drives the WHOLE pipeline through injected mocks (no LLM / no kernel / no tokens) and asserts the
    loop CLOSES: reject(strong) → literal-first re-entry → admit(literal) → kernel-refute(literal) → mint license in
    the ONE ledger → reformulation re-strengthens → override admits(strong) → close. Plus the NON-GAMABLE dual: NO
    kernel ¬G ⇒ NO license ⇒ NO override admit (the strengthening is never laundered)."""
    import tempfile
    from pathlib import Path
    from ztare.leanmill.solver import autoformalize as A, solver_core, no_good_store as NG
    # deterministic + infra-free: disable multistep escalation (would dispatch a real formalizer); loop legs ON.
    for k, v in {"ZTARE_LEANMILL_MULTISTEP_ESCALATE": "0", "ZTARE_LEANMILL_LITERAL_FIRST_RECOVERY": "1",
                 "ZTARE_LEANMILL_DISCLOSED_STRENGTHENING": "1", "ZTARE_LEANMILL_REFORMULATE": "1",
                 "ZTARE_LEANMILL_REFORMULATE_ROUNDS": "1", "ZTARE_LEANMILL_FAITHFULNESS_STORE": "1"}.items():
        monkeypatch.setenv(k, v)
    # PRODUCTION-SHAPE fixture (2026-06-23 uplevel): a MULTI-DECL `define_then_state` blob (defs THEN the target
    # theorem) — the real autoformalizer output shape that HID GATE2 (non_vacuous) + GATE3 (wrong-decl fingerprint).
    # The correction is a weak→strict DEF-SWAP on a hypothesis (SAME binder arity), which the old "more binders"
    # GATE3 + whole-blob `_parse_lean_statement` BOTH missed. A single-decl toy would NOT exercise either bug.
    NL = "single-crossing complementarity implies existence and strong-set monotonicity"
    DEFS = ("def WeakSC {X : Type*} [Preorder X] (f : X → X) : Prop := ∀ x, True\n"
            "def StrongSC {X : Type*} [Preorder X] (f : X → X) : Prop := ∀ x, True\n"
            "def Concl {X : Type*} [Preorder X] (f : X → X) : Prop := ∀ x, True\n")
    WEAK   = DEFS + "theorem tgt {X : Type*} [Preorder X] (f : X → X) (h : WeakSC f) : Concl f := by sorry"
    STRONG = DEFS + "theorem tgt {X : Type*} [Preorder X] (f : X → X) (h : StrongSC f) : Concl f := by sorry"

    def make_mocks(literal_refutable: bool):
        calls: list = []
        def formalize_fn(_nl):
            calls.append(_nl)
            # call 0: top pass-1 → STRONG (the over-strengthen); 1: literal-first re-entry → WEAK; 2: reformulation → STRONG
            return [STRONG, WEAK, STRONG][min(len(calls) - 1, 2)]
        # distinguish by the THEOREM's HYPOTHESIS binder, not the substring "StrongSC" — the DEFS block defines BOTH
        # WeakSC and StrongSC, so a substring check matches the literal too (the real LLM reads the actual theorem).
        backtranslate_fn = lambda s: ("strong corrected nl" if "(h : StrongSC f)" in s else "weak literal nl")
        judge_fn = lambda nl, back: "weak" in back              # round-trip ACCEPTS the literal, REJECTS the strong
        def solve_fn(name, stmt):
            if "(h : StrongSC f)" in stmt:                      # the corrected (def-swapped) theorem → closes
                return {"results": [{"outcome": "closed"}], "governance": {"ratified": 1}}
            if literal_refutable:                               # the WEAK literal → kernel ¬G (agent elected FALSIFY)
                return {"results": [{"outcome": "falsified", "falsifier": "cex: ties at the high parameter"}]}
            return {"results": [{"outcome": "open"}]}            # could not establish ⇒ NO license minted
        return formalize_fn, (lambda s: True), (lambda s: False), backtranslate_fn, judge_fn, solve_fn

    # (1) POSITIVE — the literal IS kernel-refutable ⇒ the loop closes the corrected theorem via the override
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d); monkeypatch.setattr(solver_core, "OUT_DIR", dd)
        f, c, t, b, j, s = make_mocks(literal_refutable=True)
        out = A.autoformalize_and_solve(NL, sandbox=dd, formalize_fn=f, compile_fn=c, triviality_fn=t,
                                        backtranslate_fn=b, judge_fn=j, solve_fn=s, structural_fn=None, max_refines=0)
        assert out.get("faithful") is True and out.get("solved") == "closed", \
            f"recovery must CLOSE the corrected theorem e2e, got faithful={out.get('faithful')} solved={out.get('solved')}"
        assert (out.get("faithfulness_checks") or {}).get("licensed_strengthening"), \
            "the corrected theorem must be admitted via the DISCLOSED-STRENGTHENING override (license minted by the recovery)"
        assert out.get("literal_first_recovery_from") == STRONG, \
            "the result must record it was recovered from the over-strengthened first formalization"
        assert NG.NoGoodStore(dd / "solver_lane_no_good_store.jsonl").statement_false_keys(), \
            "the kernel ¬G of the literal must be recorded as statement_false in the ONE ledger (the license)"

    # (2) NON-GAMABLE — the literal is NOT refutable ⇒ NO license ⇒ the strengthening is NOT laundered
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d); monkeypatch.setattr(solver_core, "OUT_DIR", dd)
        f, c, t, b, j, s = make_mocks(literal_refutable=False)
        out = A.autoformalize_and_solve(NL, sandbox=dd, formalize_fn=f, compile_fn=c, triviality_fn=t,
                                        backtranslate_fn=b, judge_fn=j, solve_fn=s, structural_fn=None, max_refines=0)
        assert not (out.get("faithful") is True and out.get("solved") == "closed"), \
            "with NO kernel ¬G the over-strengthened theorem must NOT be admitted+closed (no laundering)"
        assert not (out.get("faithfulness_checks") or {}).get("licensed_strengthening"), \
            "no license ⇒ the disclosed-strengthening override must NOT fire"
        assert not NG.NoGoodStore(dd / "solver_lane_no_good_store.jsonl").statement_false_keys(), \
            "no kernel ¬G ⇒ nothing recorded statement_false (no fabricated license)"


def test_reformulation_refine_hint_does_not_fight_strengthening():
    """REFINE↔REFORMULATE conflict fix (2026-06-23). Inside a reformulation re-entry the literal was kernel-REFUTED,
    so a round-trip mismatch on the CORRECTION is EXPECTED — but the generic refine hint said 'neither weaker nor
    stronger', which pushed the agent to re-emit the refuted reading (the prior run unfolded instead of strengthened).
    `strengthening_mode` flips the round-trip guidance; the reformulation re-entry sets `_strengthening_mode=True`."""
    import inspect
    from ztare.leanmill.solver import autoformalize as A
    class _V:  # a round-trip-rejected verdict
        checks = {"compiles": True, "non_trivial": True, "round_trip_faithful": False}
        reason = "round-trip does NOT match the NL"
    rt = A._formalize_feedback_hint(_V(), "theorem t (h : Weak f) : G := by sorry")
    rt_str = A._formalize_feedback_hint(_V(), "theorem t (h : Weak f) : G := by sorry", strengthening_mode=True)
    assert "neither weaker nor stronger" in rt, "default round-trip hint preserved (faithfulness mode)"
    assert "neither weaker nor stronger" not in rt_str and "STRONGER" in rt_str and "refuted" in rt_str, \
        "strengthening_mode must NOT tell the agent to keep it un-strengthened — it must orient toward the corrected theorem"
    # the reformulation re-entry sets _strengthening_mode=True; the threading reaches the refine hint
    s = inspect.getsource(A.autoformalize_and_solve)
    assert "_strengthening_mode=True" in s and "strengthening_mode=_strengthening_mode" in s, \
        "the reformulation re-entry must propagate _strengthening_mode into the refine loop"
    assert "strengthening_mode=strengthening_mode" in inspect.getsource(A.autoformalize_refine), \
        "autoformalize_refine must pass strengthening_mode into the per-leg feedback hint"


def test_firewall_gates_validated_on_production_shape_not_toys():
    """UPLEVELED INVARIANT (2026-06-23) — the class-preventer for the recurring integration-seam bugs. ROOT of
    'why do we keep having bugs': the disclosed-strengthening override family (GATE2 last session, GATE3 this
    session) was unit-tested on SYNTHETIC inputs that do NOT match the REAL producer's output — GATE2 injected a
    `checks` key (`non_vacuous`) the production firewall wiring never populates; GATE3 used a SINGLE-decl toy while
    the autoformalizer emits MULTI-decl `define_then_state` blobs. Both slipped through because the fixture's
    PROVENANCE + SHAPE diverged from production. This guard mechanizes the invariant so the class fails CI:
      (1) STATEMENT FINGERPRINTING is on the canonical TARGET theorem, never the whole multi-decl blob;
      (2) a gate's required `checks` keys ⊆ the keys the PRODUCTION firewall wiring actually populates."""
    import tempfile, inspect
    from pathlib import Path
    from ztare.leanmill.solver import autoformalize as A, solver_core, faithfulness_store as FS, no_good_store as NG
    # production-shape multi-decl blob: a leading `def` THEN the target theorem (the autoformalizer's real output).
    DEFS = ("def WeakSC {X : Type*} [Preorder X] (f : X → X) : Prop := ∀ x, True\n"
            "def StrongSC {X : Type*} [Preorder X] (f : X → X) : Prop := ∀ x, True\n")
    LIT  = DEFS + "theorem tgt {X : Type*} [Preorder X] (f : X → X) (h : WeakSC f) : (∀ x : X, x ≤ x) := by sorry"
    CORR = DEFS + "theorem tgt {X : Type*} [Preorder X] (f : X → X) (h : StrongSC f) : (∀ x : X, x ≤ x) := by sorry"

    # (1) FINGERPRINT-THE-TARGET invariant — `_target_signature` returns the THEOREM signature, NOT the leading
    #     `def`; and the naive whole-blob `_parse_lean_statement` is demonstrably WRONG here (the GATE3 regression
    #     witness): it parses the first decl, so it cannot tell LIT from CORR (both → the def's fingerprint).
    sig_lit, sig_corr = A._target_signature(LIT), A._target_signature(CORR)
    assert "WeakSC f" in sig_lit and "def WeakSC" not in sig_lit and ":= ∀ x, True" not in sig_lit, \
        "_target_signature must extract the TARGET theorem's signature, not the leading def of a multi-decl blob"
    assert A._hypotheses_of(sig_lit) != A._hypotheses_of(sig_corr), \
        "the target-theorem hypotheses must distinguish the weak literal from the def-swapped correction"
    blob_lit, blob_corr = A._parse_lean_statement(LIT), A._parse_lean_statement(CORR)
    assert blob_lit == blob_corr, \
        "REGRESSION WITNESS: whole-blob _parse_lean_statement CANNOT tell the correction from the literal (it parses " \
        "the leading def) — exactly the GATE3 bug; any gate fingerprinting statements MUST use _target_signature"

    # (2) CHECKS-KEY PROVENANCE invariant — drive faithfulness_gate through the EXACT production fn-set that
    #     `autoformalize_and_solve` passes (compile/triviality/backtranslate/judge ONLY — no consistency_fn /
    #     battery_fn / crossvote_fn), on a round-trip-REJECTED candidate, and capture which `checks` keys it
    #     populates. Then assert the override admits using ONLY that production key-set — so no gate may require a
    #     key production never sets (the GATE2 bug: it required `non_vacuous`, never populated ⇒ override DEAD e2e).
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d); solver_core.OUT_DIR = dd
        NL = "weak condition implies the conclusion"
        FS.FaithfulnessStore(dd / "solver_lane_faithfulness_store.jsonl").record(
            NL, LIT, confirmed=True, fingerprint=A._parse_lean_statement(LIT))
        NG.NoGoodStore(dd / "solver_lane_no_good_store.jsonl").record(LIT, "statement_false", "cex", confirmed=True)
        v = A.faithfulness_gate(NL, CORR, compile_fn=lambda s: True, triviality_fn=lambda s: False,
                                backtranslate_fn=lambda s: "a different, stronger claim",
                                judge_fn=lambda a, b: False)   # round-trip REJECTS (mirrors the real strengthened case)
        populated = set(v.checks.keys())
        assert "non_vacuous" not in populated, \
            "PROVENANCE: production wiring (no consistency_fn) must NOT populate non_vacuous — a gate requiring it is dead"
        assert "non_trivial" in populated, "production wiring DOES populate non_trivial (the load-bearing GATE2 signal)"
        # the override must ADMIT the real def-swap correction using ONLY the production-populated keys
        assert A._licensed_strengthening_admit(NL, CORR, {k: v.checks[k] for k in populated}), \
            "override must ADMIT the def-swap correction on the PRODUCTION key-set (else it is dead e2e — the GATE2 class)"
        assert v.accepted and v.checks.get("licensed_strengthening"), \
            "faithfulness_gate end-to-end must admit the correction via the override on production wiring"
        # and it still REJECTS a same-hypotheses re-statement (the prior run's non-correction) — no laundering
        assert A._licensed_strengthening_admit(NL, LIT, {k: v.checks[k] for k in populated}) is None, \
            "a same-hypotheses re-statement is NOT a correction — must be rejected even with the license"
    # (3) the override + recovery both route fingerprinting through the canonical target door (no whole-blob parse)
    src = inspect.getsource(A._licensed_strengthening_admit) + inspect.getsource(A._needs_literal_first_recovery)
    assert ("_target_signature(" in src or "statement_fingerprint(" in src) and "_parse_lean_statement(stmt)" not in src, \
        "override + recovery must fingerprint via the single door, never _parse_lean_statement on the raw blob"

    # (4) ANTI-SIBLING SINGLE-DOOR invariant — statement fingerprinting has ONE entry door, `statement_fingerprint`,
    #     which targets the theorem; NO gate/decision/reference may call `_parse_lean_statement` on a RAW (possibly
    #     multi-decl) statement (it parses the leading def — the EXACT recurring bug that was copied to five sites:
    #     GATE2/GATE3 + structural_faithfulness + reference_fingerprint + the deposit). Mechanized via substring scan
    #     (NO regex) so a NEW sibling fails CI. `_parse_lean_statement` itself stays the low-level SIGNATURE parser.
    af_src = inspect.getsource(A)
    forbidden = ["_parse_lean_statement(stmt)", "_parse_lean_statement(refuted)",
                 "_parse_lean_statement(lean_statement)", "_parse_lean_statement(af.lean_statement"]
    siblings = [f for f in forbidden if f in af_src]
    assert not siblings, f"SIBLING re-appeared — raw-statement fingerprinting {siblings}; route through statement_fingerprint()"
    # every statement-fingerprint CONSUMER routes through the single door (statement_fingerprint / _target_signature)
    for fn in (A.structural_faithfulness, A.reference_fingerprint, A._licensed_strengthening_admit,
               A._needs_literal_first_recovery):
        s = inspect.getsource(fn)
        assert "statement_fingerprint(" in s or "_target_signature(" in s, \
            f"{fn.__name__} must fingerprint via the single door (statement_fingerprint), not the raw blob"
    # the door itself targets the theorem of a multi-decl blob (else the whole consolidation is moot)
    DD = "def D {X:Type*}[Preorder X](f:X→X):Prop := ∀ x, True\n"
    fp_door = A.statement_fingerprint(DD + "theorem t {X:Type*}[Preorder X](f:X→X)(h:D f)(g:D f):(∀ x:X, x≤x) := by sorry")
    assert (fp_door.get("n_explicit_binders") or 0) >= 2, \
        "statement_fingerprint must count the TARGET theorem's binders (≥2), not the leading def's"
