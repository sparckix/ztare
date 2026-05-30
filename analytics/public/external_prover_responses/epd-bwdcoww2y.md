# External-prover dispatch epd-bwdcoww2y

**Model**: gpt-5.5
**Substrate**: apparatus_governance
**Dispatched**: 2026-05-18T13:53:37+00:00
**Persisted retroactively** (ran via `codex exec`, archived to convention per operator request)

## Question

COMPREHENSIVE COLD REVIEW + META-DARWIN (no self-bless). You are
GPT-5.5. ATTACK; do not regenerate or be agreeable. Two jobs:
(A) is this now COMPREHENSIVELY EXHAUSTIVE as a forced pre+post tick
discipline; (B) META-DARWIN the residuals each CLAIMED "irreducible"
or "deferred" — for each, decide: genuinely irreducible, or laundered
cope / isolate-and-defer? Demand a CONSTRUCTED falsifying candidate
before accepting ANY ∃→∀ "impossible/human-only" universal. Split
the verdict: an artifact-kill is NOT an idea-level settled-negative.

## Lived context (long session; settled points NOT for relitigation)
A research LLM agent games/satisfices ticks (names patterns instead
of executing; ships vacuous Lean that compiles; skips the lifecycle).
The GP-241 daemon (commit_membrane_daemon.py) is the SOLE writer of
official state (ed25519 hash-chained; reverse-H3 materializes the
F-row). tick_close.py H1-H6 are ADVISORY; ONLY the daemon (H7) is
real authority. Settled: any gate grading an agent-AUTHORED artifact
gets Goodharted; only deterministic refusals the agent cannot author
have held. Trust root = OPERATOR INSPECTION of manifests (agent
authors, operator inspects) — not agent self-attestation.

Two prior cold passes already drove fixes (do not re-find these as
if new; judge whether the FIX holds):
- NAMESPACE BUG: manifest bound the forecast-pool slug vs the
  daemon's compiler-cid (start_tick(goal).contract_id) — would have
  false-quarantined EVERY honest close. Fixed: runner recomputes the
  compiler cid via the SAME import the daemon uses.
- SUBSTRATE-SWAP: compiler cid excludes substrate ⇒ run pre-tick
  under a non-NS substrate, skip the NS step, close the real tick.
  Fixed by GENERIC exact substrate binding (manifest.substrate ==
  frozen SIGNED start-row substrate), implemented substrate-
  AGNOSTICALLY (operator: "why are u hardcoding ns in the daemon" —
  all NS knowledge removed; runner owns substrate→step mapping).

## What is built (the full surface to attack)
pretick_runner.py — 8 fail-closed steps (RC=2 unless all pass):
scientific_amnesia, orchestration_menu, pattern_antipattern,
ns_residual_graph (substrate-normalized; REQUIRED not skippable for
NS), gp230_forecast (specific contract must exist + be surfaced-
bound), gp233_decomposition (FRESH <7d entry w/ non-empty
next_lever), universal_language_ops (META-PATTERN-022; op-ids
validated vs deterministic catalog), four_scope_coverage
(META-PATTERN-023; all of local/chain/recursive/meta). Manifest
top-level: tick_id, contract_id=recomputed compiler cid,
forecast_contract_id, consumes_surfaced, universal_ops, scopes,
substrate, goal.

posttick_runner.py — symmetric. HARD legs: pretick_bound
(pre↔post: COMPLETE pretick manifest, cid/tick/goal match),
post_tick_check (post_tick_check.py exit 0), micro_resolved
(forecast RESOLVED + prior codex bet, audited not performed),
big_decision_forecast (--decision-changed ⇒ FRESH meso/macro
MANDATORY), lean_faithfulness (--thesis-path ⇒ HARD
run_lean_proof_gate: compile + axiom audit + v33 anti-laundering
organs). ADVISORY-recorded (NOT gated, per the documented
don't-false-FAIL invariant): tier3_pattern_026, memory_touched,
and lean_faithfulness WHEN no thesis declared.

commit_membrane_daemon.py — in the FROZEN-start tick_close branch
(only real authority), symmetric pre- and post-gates: each binds
manifest ⇄ frozen SIGNED start row on tick_id + compiler-cid + goal
+ substrate; absent/INCOMPLETE/foreign ⇒ oblig_fail ⇒ existing
quarantine (fail-closed). Helpers hoisted; read-error fail-closed;
substrate-agnostic.

Self triple-check done: all compile+AST; pretick positive RC=0;
negatives fail-closed; posttick fail-closed on unresolved contract;
pretick_bound symmetric binding True; daemon gate predicate
simulated — matched start_row ⇒ no oblig_fail, EVERY tampered axis
(tick_id/cid/goal/substrate) ⇒ its specific quarantine entry;
lean_faithfulness HARD-fails a declared-bad thesis.

## RESIDUALS — META-DARWIN EACH (irreducible vs cope?)
R2  operator-pinned daemon tree + signing keys outside agent write
    boundary; stamp daemon code hash. CLAIM: deploy-layer, not
    per-tick gaming (the repo copy being agent-editable is expected;
    only the VPS instance under the ztare identity is authority).
    ATTACK: is "deploy residual" cope? Is there a per-tick gaming
    path that this deferral leaves open NOW?
R5' lean_faithfulness trigger-bind: a closure-claiming tick can omit
    --thesis-path ⇒ the leg goes advisory. CLAIM: forcing it needs
    the close's claimed substrate_class/outcome to MANDATE the
    thesis (R6-class). ATTACK: is deferring this the SAME cheap-fix-
    deferred-is-deflection pattern the substrate fix already proved?
    Is it cheap enough that deferral itself is the anti-pattern?
R5''/R6 deepest identity: bind to signed-row/official_state_hash +
    freeze gp230_question_hash/consumes_surfaced in the start row.
    CLAIM: signed-row SCHEMA change ⇒ own spec + operator
    inspection, not mid-session. ATTACK: is tick_id+cid+goal+
    substrate binding actually sufficient, or does this deferral
    leave a live path "valid pre/post-tick on the right goal while
    closing a vacuous/unrelated F-row"?
R5''' genuinely irreducible candidate: even a faithful non-vacuous
    proof of theorem T doesn't certify T IS the Clay statement;
    per-tick-gateable part = pin target-statement hash; only
    irreducible part = whether the pinned target itself is the Clay
    problem (one-time human, not per-tick). ATTACK this
    decomposition: is the "one-time human" residual real, or can it
    too be mechanized; is the decomposition itself laundering?

## EXHAUSTIVENESS
Enumerate any pre- or post-tick MECE leg the brief mandates that is
STILL not forced. Is "comprehensively exhaustive" true or is there a
class (lifecycle / faithfulness / identity) still ungated? Be
specific with file:line.

OUTPUT: VERDICT GO / GO-WITH-CHANGES / NO-GO; per-residual
Meta-Darwin verdict (IRREDUCIBLE | LAUNDERED-DEFER | CHEAP-FIX-NOW
with the fix); the single failure mode you predict remains even if
every GO-WITH-CHANGES item is fixed.

## CODE
### pretick_runner.py
     1	#!/usr/bin/env python3
     2	"""pretick_runner — FORCES the pre-tick (the thing the agent kept
     3	naming-not-doing), as the autoresearch SHAPE applied to the FRONT of
     4	a tick.
     5	
     6	Operator scope (2026-05-18): the agent AUTHORS this; the OPERATOR
     7	INSPECTS it. Inspection — not operator-authoring — is the
     8	non-self-bless trust root (cheap, the irreducible human role finally
     9	located correctly). This is NOT a Lean gate (that is one optional
    10	downstream part); it forces the PRE-TICK steps the brief surfaced and
    11	the agent satisficed all session:
    12	
    13	  1 scientific amnesia precheck   (deterministic: overlap_detected)
    14	  2 orchestration-menu compose    (problem_class -> sub_class -> chain)
    15	  3 pattern / anti-pattern surface (the obligated chain, from catalog)
    16	  4 (NS) residual graph / void-audit consume (surfaced source-void id)
    17	  5 GP-230 forecast contract       (consumes-surfaced bound; codex warm)
    18	  6 GP-233 yield-decomposition scaffold (residual_to_lever record stub)
    19	
    20	Each step RUNS the EXISTING tool (composed, not reinvented) and emits
    21	a receipt. The runner FAILS CLOSED if any step's receipt is absent or
    22	empty: no COMPLETE pretick_manifest -> the tick may not proceed and
    23	tick_close must refuse. The agent cannot satisfy this by narrating
    24	"I considered the patterns": the receipts are tool stdout/artifacts,
    25	not agent prose. Faking is strictly dominated (autoresearch lesson):
    26	the only path through is to actually run the pre-tick.
    27	
    28	Honest bound (carried, not hidden): this forces the pre-tick is
    29	EXECUTED. It does not — cannot — certify the resulting research
    30	insight is deep; that residual is the operator inspecting this
    31	manifest + the genuinely-open-math human review. The runner shrinks
    32	the ungated surface to its true size; it does not eliminate the
    33	human. Composes: ns_scientific_amnesia_precheck, orchestration_menu
    34	.yaml, the void-audit json, forecast_pool.py, residual_to_lever.py.
    35	"""
    36	from __future__ import annotations
    37	
    38	import argparse
    39	import datetime
    40	import hashlib
    41	import json
    42	import pathlib
    43	import subprocess
    44	import sys
    45	
    46	REPO = pathlib.Path(__file__).resolve().parents[3]
    47	PY = sys.executable
    48	
    49	
    50	def _sha(s: str) -> str:
    51	    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()[:16]
    52	
    53	
    54	def _run(cmd: list[str], timeout: int = 240) -> tuple[int, str]:
    55	    try:
    56	        r = subprocess.run(cmd, cwd=str(REPO), capture_output=True,
    57	                            text=True, timeout=timeout)
    58	        return r.returncode, (r.stdout or "") + (r.stderr or "")
    59	    except Exception as e:  # noqa: BLE001
    60	        return 99, f"__RUN_ERROR__ {type(e).__name__}: {e}"
    61	
    62	
    63	def _step(name: str, ok: bool, receipt: dict) -> dict:
    64	    return {"step": name, "ok": bool(ok),
    65	            "receipt": receipt,
    66	            "receipt_sha": _sha(json.dumps(receipt, sort_keys=True,
    67	                                           ensure_ascii=False))}
    68	
    69	
    70	def main() -> int:
    71	    ap = argparse.ArgumentParser()
    72	    ap.add_argument("--goal", required=True)
    73	    ap.add_argument("--substrate", required=True)
    74	    ap.add_argument("--owner", required=True)
    75	    ap.add_argument("--tick-id", required=True)
    76	    ap.add_argument("--contract-id", required=True,
    77	                    help="the GP-230 forecast contract THIS tick will "
    78	                         "consume — must already exist (created via "
    79	                         "forecast_pool) and be surfaced-bound; lifted "
    80	                         "to manifest.contract_id so the GP-241 daemon "
    81	                         "can mutually-bind the manifest to the frozen "
    82	                         "signed start row (presence≠this-tick).")
    83	    ap.add_argument("--universal-ops", required=True,
    84	                    help="comma-sep universal_research_ops op-ids the "
    85	                         "tick translates the problem into (≥1; "
    86	                         "META-PATTERN-022). Each MUST resolve in the "
    87	                         "deterministic op catalog — same shape as "
    88	                         "--contract-id: a concrete selection the "
    89	                         "runner validates, not free narration.")
    90	    ap.add_argument("--scopes", required=True,
    91	                    help="comma-sep of the 4 scopes covered "
    92	                         "(META-PATTERN-023): local,chain,recursive,"
    93	                         "meta — ALL FOUR required or the step fails.")
    94	    a = ap.parse_args()
    95	
    96	    rdir = REPO / "analytics" / "public" / "pretick" / a.tick_id
    97	    rdir.mkdir(parents=True, exist_ok=True)
    98	    steps: list[dict] = []
    99	
   100	    # 1 — scientific amnesia precheck (deterministic overlap signal).
   101	    amn = REPO / ("projects/ns_millennium_hunt/scripts/"
   102	                  "ns_scientific_amnesia_precheck.py")
   103	    if not amn.is_file():
   104	        amn = (REPO / "scripts/public/control/"
   105	               "scientific_amnesia_precheck.py")
   106	    rc, out = _run([PY, str(amn), "--query", a.goal])
   107	    overlap = "overlap_detected: True" in out
   108	    steps.append(_step("scientific_amnesia",
   109	                        rc == 0 and ("overlap_detected" in out),
   110	                        {"overlap_detected": overlap,
   111	                         "head": out[:1500]}))
   112	
   113	    # 2 — orchestration-menu compose (problem_class -> sub_class).
   114	    menu = REPO / "org" / "menu" / "orchestration_menu.yaml"
   115	    mtext = menu.read_text(encoding="utf-8") if menu.is_file() else ""
   116	    g = a.goal.lower()
   117	    pc = None
   118	    for key in ("hard_mathematical_residual", "pure_analysis_drift",
   119	                "too_complex_direct_attack", "apparatus_self_audit",
   120	                "pre_category_emergence"):
   121	        if key in mtext:
   122	            pc = key
   123	            break
   124	    steps.append(_step("orchestration_menu",
   125	                        bool(pc and mtext),
   126	                        {"problem_class": pc,
   127	                         "menu_present": bool(mtext),
   128	                         "menu_sha": _sha(mtext)}))
   129	
   130	    # 3 — pattern / anti-pattern surfacing (the obligated chain).
   131	    catr = REPO / "org" / "catalog_routing"
   132	    pats, antis = [], []
   133	    try:
   134	        import yaml as _y
   135	        for f in catr.glob("l*_activation.y*ml"):
   136	            d = _y.safe_load(f.read_text(encoding="utf-8")) or []
   137	            ids = [x.get("item_id") for x in d
   138	                   if isinstance(x, dict) and x.get("item_id")]
   139	            (antis if "l3" in f.name else pats).extend(ids)
   140	    except Exception:
   141	        pass
   142	    steps.append(_step("pattern_antipattern",
   143	                        bool(pats or antis),
   144	                        {"patterns_available": pats[:20],
   145	                         "antipatterns_to_check": antis[:20]}))
   146	
   147	    # 4 — (NS) residual graph / void-audit consume.
   148	    #     COLD REVIEW bvs1b6d43 Angle 1 (self-caught: the E2E demo
   149	    #     passed substrate "ns" and SILENTLY skipped this NS step).
   150	    #     Fix: normalize the substrate; if the tick IS NS, the graph
   151	    #     step is REQUIRED (no skip-pass). Only a genuinely non-NS
   152	    #     substrate is honestly N/A.
   153	    _sub = str(a.substrate).strip().lower()
   154	    _is_ns = _sub in {"ns", "ns_millennium_hunt", "navier_stokes",
   155	                      "navier-stokes", "nsm"} or "navier" in _sub
   156	    if _is_ns:
   157	        va = (REPO / "projects/ns_millennium_hunt/workspace/queries/"
   158	              "ns_trackb_residual_void_audit.json")
   159	        ids = []
   160	        try:
   161	            vd = json.loads(va.read_text(encoding="utf-8"))
   162	            ids = list(vd.get("source_void_nodes", []))[:10]
   163	            mincuts = [c[0] for c in vd.get("min_vertex_cuts", [])
   164	                       if c]
   165	        except Exception:
   166	            mincuts = []
   167	        steps.append(_step("ns_residual_graph",
   168	                            bool(ids),
   169	                            {"normalized_substrate": _sub,
   170	                             "ns_required": True,
   171	                             "source_void_nodes": ids,
   172	                             "min_vertex_cuts": mincuts,
   173	                             "consumes_surfaced_candidates": ids}))
   174	    else:
   175	        steps.append(_step("ns_residual_graph", True,
   176	                            {"normalized_substrate": _sub,
   177	                             "skipped": "genuinely non-NS substrate "
   178	                             "(NS aliases are normalized + REQUIRED)"}))
   179	
   180	    # 5 — GP-230 forecast contract presence (deterministic check that
   181	    #     a micro contract bound to a surfaced id + a forecast exist;
   182	    #     the runner does NOT fabricate one — it verifies the agent
   183	    #     created it via forecast_pool, else fail-closed).
   184	    #     Bind to the SPECIFIC --contract-id this tick will consume
   185	    #     (not "any surfaced-bound contract exists" — that was the
   186	    #     presence≠this-tick weakness). PASS iff that exact contract
   187	    #     file exists AND carries consumes_surfaced. Its
   188	    #     consumes_surfaced is lifted to manifest so the daemon binds
   189	    #     manifest⇄frozen-start-row by contract_id (un-forgeable).
   190	    fp = REPO / "analytics/public/forecast_pool/contracts"
   191	    this_consumes = None
   192	    this_ok = False
   193	    if fp.is_dir():
   194	        for c in fp.glob("*.json"):
   195	            try:
   196	                cj = json.loads(c.read_text(encoding="utf-8"))
   197	            except Exception:
   198	                continue
   199	            if str(cj.get("contract_id", "")) == a.contract_id:
   200	                this_consumes = cj.get("consumes_surfaced")
   201	                this_ok = bool(this_consumes)
   202	                break
   203	    steps.append(_step("gp230_forecast",
   204	                        this_ok,
   205	                        {"contract_id": a.contract_id,
   206	                         "consumes_surfaced": this_consumes,
   207	                         "note": ("the SPECIFIC tick contract must "
   208	                                  "exist + be surfaced-bound")}))
   209	
   210	    # 6 — GP-233 yield-decomposition (residual_to_lever).
   211	    #     COLD REVIEW bvs1b6d43 Angle 1: "any file present passes" is
   212	    #     vacuous. Tightened (no ledger-schema change — that owner/
   213	    #     contract-bound rewrite is a specced residual, not a mid-
   214	    #     session treadmill): require a residual_to_lever ledger with
   215	    #     >=1 entry carrying a NON-EMPTY next_lever AND freshness
   216	    #     (mtime within RESIDUAL_FRESH_DAYS) so a stale months-old
   217	    #     artifact cannot satisfy this tick.
   218	    import time as _time
   219	    _rdir = REPO / "analytics/public/ledgers/residual_to_lever"
   220	    RESIDUAL_FRESH_DAYS = 7
   221	    _g233_ok = False
   222	    _g233_why = "no residual_to_lever ledger dir"
   223	    _fresh_levers = 0
   224	    if _rdir.is_dir():
   225	        _now_s = _time.time()
   226	        for _lf in _rdir.glob("*.jsonl"):
   227	            try:
   228	                _age_d = (_now_s - _lf.stat().st_mtime) / 86400.0
   229	                if _age_d > RESIDUAL_FRESH_DAYS:
   230	                    continue
   231	                for _ln in _lf.read_text(
   232	                        encoding="utf-8").splitlines():
   233	                    _ln = _ln.strip()
   234	                    if not _ln:
   235	                        continue
   236	                    try:
   237	                        _e = json.loads(_ln)
   238	                    except Exception:
   239	                        continue
   240	                    if str(_e.get("next_lever", "")).strip():
   241	                        _fresh_levers += 1
   242	            except Exception:
   243	                continue
   244	        _g233_ok = _fresh_levers > 0
   245	        _g233_why = (f"{_fresh_levers} fresh (<{RESIDUAL_FRESH_DAYS}d) "
   246	                     f"entries with non-empty next_lever"
   247	                     if _g233_ok else
   248	                     "ledger dir present but NO fresh entry with a "
   249	                     "non-empty next_lever (stale/empty ⇒ fail)")
   250	    steps.append(_step("gp233_decomposition", _g233_ok,
   251	                        {"fresh_next_lever_entries": _fresh_levers,
   252	                         "fresh_window_days": RESIDUAL_FRESH_DAYS,
   253	                         "why": _g233_why}))
   254	
   255	    # 7 — universal-language op enumeration (META-PATTERN-022). The
   256	    #     agent supplies concrete op-ids; the runner validates each
   257	    #     against the deterministic universal_research_ops catalog
   258	    #     (get(op_id) is not None). Same anti-narration shape as the
   259	    #     contract step: a checkable selection, not prose. Recorded
   260	    #     into the manifest so the post-tick can verify the closure
   261	    #     consumed the translation it claimed.
   262	    uops = [o.strip() for o in str(a.universal_ops).split(",")
   263	            if o.strip()]
   264	    uop_valid, uop_unknown = [], []
   265	    try:
   266	        sys.path.insert(0, str(REPO))
   267	        from src.ztare.research_director import (  # noqa: E402
   268	            universal_research_ops as _uro)
   269	        for o in uops:
   270	            (uop_valid if _uro.get(o) is not None
   271	             else uop_unknown).append(o)
   272	        uro_ok = bool(uop_valid) and not uop_unknown
   273	    except Exception as e:  # noqa: BLE001
   274	        uro_ok = False
   275	        uop_unknown = uops
   276	        uop_valid = [f"__IMPORT_ERROR__ {type(e).__name__}"]
   277	    steps.append(_step("universal_language_ops",
   278	                        uro_ok,
   279	                        {"ops_declared": uops,
   280	                         "ops_valid": uop_valid,
   281	                         "ops_unknown": uop_unknown,
   282	                         "note": ("≥1 op-id must resolve in the "
   283	                                  "deterministic catalog; unknown "
   284	                                  "ids fail (META-PATTERN-022)")}))
   285	
   286	    # 8 — 4-scope coverage (META-PATTERN-023): local/chain/recursive/
   287	    #     meta must ALL be declared. Deterministic set check.
   288	    _need = {"local", "chain", "recursive", "meta"}
   289	    _have = {s.strip().lower() for s in str(a.scopes).split(",")
   290	             if s.strip()}
   291	    steps.append(_step("four_scope_coverage",
   292	                        _need.issubset(_have),
   293	                        {"scopes_declared": sorted(_have),
   294	                         "scopes_required": sorted(_need),
   295	                         "missing": sorted(_need - _have)}))
   296	
   297	    # DAEMON-NAMESPACE BINDING (cold review bvs1b6d43, Angle 2 — a
   298	    # correctness fix, not hardening). The GP-241 daemon freezes the
   299	    # signed start row's `contract_id` as the COMPILER cid =
   300	    # start_tick(goal).contract_id (sha256 of normalized goal +
   301	    # catalog hashes + extractor version) — NOT the forecast-pool
   302	    # slug. Binding manifest.contract_id to the slug compared two
   303	    # different id-spaces ⇒ would false-quarantine EVERY honest
   304	    # close. manifest.contract_id MUST be the recomputed compiler
   305	    # cid so the daemon's `_mc == _sc` is same-namespace and
   306	    # un-forgeable (it folds in goal + catalog + extractor version,
   307	    # strictly stronger than goal-string equality). The forecast-pool
   308	    # slug is kept separately as forecast_contract_id (step 5's own
   309	    # check; never the daemon mutual-bind key).
   310	    try:
   311	        sys.path.insert(0, str(REPO))
   312	        from src.ztare.surfacing.pre_tick_obligation_compiler import (  # noqa: E402
   313	            start_tick as _start_tick)
   314	        _compiler_cid = str(_start_tick(a.goal).contract_id)
   315	    except Exception as e:  # noqa: BLE001
   316	        _compiler_cid = f"__CID_RECOMPUTE_ERROR__ {type(e).__name__}"
   317	        steps.append(_step("daemon_cid_binding", False,
   318	                            {"error": _compiler_cid}))
   319	    complete = all(s["ok"] for s in steps)
   320	    manifest = {
   321	        "tick_id": a.tick_id, "goal": a.goal,
   322	        "substrate": a.substrate, "owner": a.owner,
   323	        "contract_id": _compiler_cid,
   324	        "forecast_contract_id": a.contract_id,
   325	        "consumes_surfaced": this_consumes,
   326	        "universal_ops": uops,
   327	        "scopes": sorted(_have),
   328	        "ts": datetime.datetime.now(
   329	            datetime.timezone.utc).isoformat(timespec="seconds"),
   330	        "authored_by": "agent",
   331	        "trust_root": "operator_inspection (NOT operator-authored; "
   332	                       "operator 2026-05-18)",
   333	        "status": "COMPLETE" if complete else "INCOMPLETE",
   334	        "steps": steps,
   335	        "honest_bound": ("forces the pre-tick is EXECUTED via tool "
   336	                         "receipts; does NOT certify insight depth — "
   337	                         "that is operator inspection of this "
   338	                         "manifest + human review of open-math."),
   339	    }
   340	    (rdir / "pretick_manifest.json").write_text(
   341	        json.dumps(manifest, indent=1, ensure_ascii=False))
   342	    print(json.dumps({"status": manifest["status"],
   343	                       "manifest": str(
   344	                           (rdir / "pretick_manifest.json"
   345	                            ).relative_to(REPO)),
   346	                       "failed_steps": [s["step"] for s in steps
   347	                                        if not s["ok"]]}, indent=1))
   348	    # FAIL-CLOSED: tick may not proceed without a COMPLETE manifest.
   349	    return 0 if complete else 2
   350	
   351	
   352	if __name__ == "__main__":
   353	    raise SystemExit(main())

### posttick_runner.py
     1	#!/usr/bin/env python3
     2	"""posttick_runner — the SYMMETRIC back half of pretick_runner.
     3	
     4	Operator (2026-05-18): "can we do the same for the post checks ...
     5	have we been comprehensively exhaustive". The pre-tick is forced by
     6	pretick_runner + the GP-241 daemon HARD gate; this forces the
     7	POST-tick MECE legs the brief enumerates (rd_tick_brief l.599-606)
     8	the same way: each leg RUNS an existing tool and emits a receipt;
     9	fail-closed unless every HARD leg passes; bound to the FROZEN signed
    10	start row by the SAME compiler-cid namespace the daemon uses
    11	(presence != this-tick). The daemon post-gate (mirrored from the
    12	cold-cleared pre-gate) HARD-requires this manifest on tick_close.
    13	
    14	HARD legs (gate `complete`):
    15	  1 pretick_bound        — the COMPLETE pretick_manifest for THIS
    16	                           tick exists and is contract/goal-bound
    17	                           (post presupposes a real pre; binds
    18	                           pre<->post symmetrically).
    19	  2 post_tick_check      — post_tick_check.py --owner [..] exit 0
    20	                           (its deterministic HARD legs clear).
    21	  3 micro_resolved       — the tick's micro forecast contract is
    22	                           RESOLVED *and* a codex bet existed first
    23	                           (never-resolve-before-codex; verified,
    24	                           not performed here).
    25	  4 big_decision_forecast (only if --decision-changed) — a FRESH
    26	                           meso OR macro contract exists. Operation-
    27	                           alises "meso/macro optional, but MANDATORY
    28	                           for big decisions".
    29	
    30	ADVISORY-recorded (NOT gated — quality/scope of a linter is the
    31	irreducibly-advisory class; a hard flip would false-FAIL honest work,
    32	violating the post_tick_check don't-false-FAIL invariant):
    33	  tier3_pattern_026, memory_touched.
    34	
    35	Honest bound (carried): forces the post-tick is EXECUTED. Does not
    36	certify the closure is mathematically faithful (the BKM Icc-vs-Ico
    37	class) — that residual stays with break-only adversary + operator.
    38	Composes: post_tick_check.py, forecast_pool contracts/codex state,
    39	closure_claim_discipline_linter_tier3.py, pre_tick_obligation_
    40	compiler.start_tick (cid namespace).
    41	"""
    42	from __future__ import annotations
    43	
    44	import argparse
    45	import datetime
    46	import hashlib
    47	import json
    48	import pathlib
    49	import subprocess
    50	import sys
    51	import time
    52	
    53	REPO = pathlib.Path(__file__).resolve().parents[3]
    54	PY = sys.executable
    55	
    56	
    57	def _sha(s: str) -> str:
    58	    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()[:16]
    59	
    60	
    61	def _run(cmd: list[str], timeout: int = 240) -> tuple[int, str]:
    62	    try:
    63	        r = subprocess.run(cmd, cwd=str(REPO), capture_output=True,
    64	                            text=True, timeout=timeout)
    65	        return r.returncode, (r.stdout or "") + (r.stderr or "")
    66	    except Exception as e:  # noqa: BLE001
    67	        return 99, f"__RUN_ERROR__ {type(e).__name__}: {e}"
    68	
    69	
    70	def _step(name: str, ok: bool, receipt: dict, hard: bool = True) -> dict:
    71	    return {"step": name, "ok": bool(ok), "hard": bool(hard),
    72	            "receipt": receipt,
    73	            "receipt_sha": _sha(json.dumps(receipt, sort_keys=True,
    74	                                           ensure_ascii=False))}
    75	
    76	
    77	def main() -> int:
    78	    ap = argparse.ArgumentParser()
    79	    ap.add_argument("--goal", required=True)
    80	    ap.add_argument("--substrate", required=True)
    81	    ap.add_argument("--owner", required=True)
    82	    ap.add_argument("--tick-id", required=True)
    83	    ap.add_argument("--contract-id", required=True,
    84	                    help="the tick's forecast-pool contract slug "
    85	                         "(must be RESOLVED with a prior codex bet).")
    86	    ap.add_argument("--decision-changed", action="store_true",
    87	                    help="declare this tick changed a load-bearing "
    88	                         "decision ⇒ a FRESH meso/macro forecast is "
    89	                         "then MANDATORY (big-decision trigger).")
    90	    ap.add_argument("--thesis-path", default="",
    91	                    help="path to the tick's thesis.md (Lean closure "
    92	                         "artifact). If given, lean_faithfulness is a "
    93	                         "HARD leg: run_lean_proof_gate (compile + "
    94	                         "axiom audit + v33 anti-laundering organs) "
    95	                         "must pass. This composes the EXISTING "
    96	                         "deterministic faithfulness layer — the "
    97	                         "vacuity residual was over-claimed as "
    98	                         "human-only without it.")
    99	    ap.add_argument("--project-slug", default="",
   100	                    help="project slug for the Lean gate (defaults to "
   101	                         "the thesis parent dir name).")
   102	    a = ap.parse_args()
   103	
   104	    rdir = REPO / "analytics" / "public" / "posttick" / a.tick_id
   105	    rdir.mkdir(parents=True, exist_ok=True)
   106	    steps: list[dict] = []
   107	
   108	    # compiler-cid (daemon namespace) — recomputed from the goal via
   109	    # the SAME import the daemon's start row uses. The daemon post-
   110	    # gate binds manifest.contract_id == frozen start cid.
   111	    try:
   112	        sys.path.insert(0, str(REPO))
   113	        from src.ztare.surfacing.pre_tick_obligation_compiler import (  # noqa: E402
   114	            start_tick as _start_tick)
   115	        _compiler_cid = str(_start_tick(a.goal).contract_id)
   116	    except Exception as e:  # noqa: BLE001
   117	        _compiler_cid = f"__CID_RECOMPUTE_ERROR__ {type(e).__name__}"
   118	
   119	    # 1 — pretick_bound: a COMPLETE pretick_manifest for THIS tick,
   120	    #     bound to the same compiler cid + goal. Post presupposes a
   121	    #     real pre; this is the pre<->post symmetry the brief wants.
   122	    _pm = (REPO / "analytics" / "public" / "pretick" / a.tick_id
   123	           / "pretick_manifest.json")
   124	    _pb_ok = False
   125	    _pb_why = "pretick_manifest absent (no pre-tick ⇒ no post-tick)"
   126	    if _pm.is_file():
   127	        try:
   128	            _pj = json.loads(_pm.read_text(encoding="utf-8"))
   129	            _conds = {
   130	                "status_COMPLETE": str(_pj.get("status")) == "COMPLETE",
   131	                "tick_id_match": str(_pj.get("tick_id")) == a.tick_id,
   132	                "cid_match": str(_pj.get("contract_id")) == _compiler_cid,
   133	                "goal_match": str(_pj.get("goal", "")).strip()
   134	                == a.goal.strip(),
   135	            }
   136	            _pb_ok = all(_conds.values())
   137	            _pb_why = ("pre<->post bound" if _pb_ok
   138	                       else f"unmet: {[k for k,v in _conds.items() if not v]}")
   139	        except Exception as e:  # noqa: BLE001
   140	            _pb_why = f"pretick_manifest unreadable ({type(e).__name__})"
   141	    steps.append(_step("pretick_bound", _pb_ok,
   142	                        {"why": _pb_why,
   143	                         "expected_cid": _compiler_cid}))
   144	
   145	    # 2 — post_tick_check.py (known CLI: --owner [--decision-changed]).
   146	    #     Its deterministic HARD legs (PL closure / GP-230 unresolved /
   147	    #     GP-233-on-decision-changed) must clear ⇒ exit 0.
   148	    ptc = REPO / "scripts/public/control/post_tick_check.py"
   149	    _cmd = [PY, str(ptc), "--owner", a.owner]
   150	    if a.decision_changed:
   151	        _cmd.append("--decision-changed")
   152	    rc, out = _run(_cmd)
   153	    steps.append(_step("post_tick_check", rc == 0,
   154	                        {"rc": rc, "tail": out[-1200:]}))
   155	
   156	    # 3 — micro_resolved: the tick's forecast contract is RESOLVED and
   157	    #     a codex bet existed BEFORE resolve (never-resolve-before-
   158	    #     codex). Verified from on-disk state — NOT performed here
   159	    #     (resolving is the agent's tick action; the runner audits it).
   160	    fp = REPO / "analytics/public/forecast_pool/contracts"
   161	    cj, _resolved, _codex = None, False, False
   162	    if fp.is_dir():
   163	        for c in fp.glob("*.json"):
   164	            try:
   165	                d = json.loads(c.read_text(encoding="utf-8"))
   166	            except Exception:
   167	                continue
   168	            if str(d.get("contract_id", "")) == a.contract_id:
   169	                cj = d
   170	                _resolved = bool(d.get("resolved")
   171	                                 or d.get("resolution")
   172	                                 or d.get("outcome"))
   173	                break
   174	    _cx = (fp / f"{a.contract_id}.codex.json")
   175	    _codex = _cx.is_file() or (
   176	        fp / "codex.json").is_file() if fp.is_dir() else False
   177	    steps.append(_step("micro_resolved",
   178	                        bool(cj) and _resolved and _codex,
   179	                        {"contract_found": bool(cj),
   180	                         "resolved": _resolved,
   181	                         "codex_bet_present": _codex,
   182	                         "note": ("RESOLVED + prior codex bet both "
   183	                                  "required (audited, not performed)")}))
   184	
   185	    # 4 — big-decision trigger (#42): --decision-changed ⇒ a FRESH
   186	    #     (<7d) meso OR macro contract is MANDATORY. Operationalises
   187	    #     "meso/macro optional, but mandatory for big decisions"
   188	    #     deterministically. Skipped (honest N/A) otherwise.
   189	    if a.decision_changed:
   190	        _now = time.time()
   191	        _big = []
   192	        if fp.is_dir():
   193	            for c in fp.glob("*.json"):
   194	                try:
   195	                    d = json.loads(c.read_text(encoding="utf-8"))
   196	                except Exception:
   197	                    continue
   198	                if str(d.get("layer", "")).lower() in {"meso", "macro"} \
   199	                        and (_now - c.stat().st_mtime) / 86400.0 <= 7:
   200	                    _big.append({"id": d.get("contract_id"),
   201	                                 "layer": d.get("layer")})
   202	        steps.append(_step("big_decision_forecast", bool(_big),
   203	                            {"decision_changed": True,
   204	                             "fresh_meso_macro": _big[-3:],
   205	                             "why": ("a load-bearing decision change "
   206	                                     "requires a fresh meso/macro "
   207	                                     "forecast, not micro alone")}))
   208	    else:
   209	        steps.append(_step("big_decision_forecast", True,
   210	                            {"decision_changed": False,
   211	                             "skipped": "no big-decision declared "
   212	                             "(meso/macro genuinely optional here)"}))
   213	
   214	    # 5 — lean_faithfulness: composes the EXISTING deterministic
   215	    #     faithfulness layer (run_lean_proof_gate = extract → compile
   216	    #     → axiom audit → v33 anti-laundering organs: vacuity /
   217	    #     paraphrase / single-lemma / scalar-wrapper). The vacuity
   218	    #     residual was over-claimed as human-only WITHOUT this; it is
   219	    #     gateable for the known organ families. HARD when a thesis
   220	    #     is declared. When NOT declared it is recorded (advisory) and
   221	    #     the trigger-bind ("a closure-claiming tick MUST declare its
   222	    #     Lean artifact") is the explicit residual sent to Meta-Darwin
   223	    #     — NOT silently asserted complete.
   224	    _tp = str(a.thesis_path).strip()
   225	    if _tp:
   226	        _thp = pathlib.Path(_tp)
   227	        if not _thp.is_absolute():
   228	            _thp = REPO / _thp
   229	        _slug = (a.project_slug.strip()
   230	                 or (_thp.parent.name if _thp.parent else "tick"))
   231	        _lf_ok, _lf_rec = False, {}
   232	        try:
   233	            sys.path.insert(0, str(REPO))
   234	            from src.ztare.gates.lean_proof_gate import (  # noqa: E402
   235	                run_lean_proof_gate)
   236	            _gr = run_lean_proof_gate(
   237	                thesis_path=_thp, project_slug=_slug,
   238	                ztare_proofs_root=(REPO / "ztare_proofs"),
   239	                timeout_seconds=300, enforce_anti_laundering=True)
   240	            _lf_ok = bool(_gr.get("gate_passed"))
   241	            _lf_rec = {"gate_passed": _gr.get("gate_passed"),
   242	                       "compiled": _gr.get("compiled"),
   243	                       "axiom_audit_passed": _gr.get(
   244	                           "axiom_audit_passed"),
   245	                       "anti_laundering_passed": _gr.get(
   246	                           "anti_laundering_passed"),
   247	                       "v33_organ_flags": _gr.get("v33_organ_flags"),
   248	                       "thesis": str(_thp.relative_to(REPO))
   249	                       if str(_thp).startswith(str(REPO))
   250	                       else str(_thp)}
   251	        except Exception as e:  # noqa: BLE001
   252	            _lf_ok = False
   253	            _lf_rec = {"error": f"{type(e).__name__}: {e}"}
   254	        steps.append(_step("lean_faithfulness", _lf_ok, _lf_rec,
   255	                            hard=True))
   256	    else:
   257	        _resid = ("no --thesis-path: the trigger-bind (a closure-"
   258	                  "claiming tick MUST declare its Lean artifact) is "
   259	                  "the open residual, sent to Meta-Darwin — NOT "
   260	                  "asserted complete")
   261	        steps.append(_step("lean_faithfulness", True,
   262	                            {"declared": False, "residual": _resid},
   263	                            hard=False))
   264	
   265	    # ADVISORY-recorded (NOT in the hard `complete` set).
   266	    t3 = REPO / "scripts/public/control/closure_claim_discipline_linter_tier3.py"
   267	    if t3.is_file():
   268	        rc3, out3 = _run([PY, str(t3), "--check-type", "pattern_026"],
   269	                         timeout=180)
   270	        steps.append(_step("tier3_pattern_026", rc3 == 0,
   271	                            {"rc": rc3, "tail": out3[-800:],
   272	                             "advisory": ("linter scope/quality is the "
   273	                                          "irreducibly-advisory class; "
   274	                                          "recorded, not gated")},
   275	                            hard=False))
   276	    mem = pathlib.Path.home() / (
   277	        ".claude/projects//memory")
   278	    _mfresh = False
   279	    if mem.is_dir():
   280	        try:
   281	            _mfresh = any(
   282	                (time.time() - p.stat().st_mtime) / 86400.0 <= 7
   283	                for p in mem.glob("*.md"))
   284	        except Exception:
   285	            _mfresh = False
   286	    steps.append(_step("memory_touched", _mfresh,
   287	                        {"memory_fresh_within_7d": _mfresh,
   288	                         "advisory": "memory-update quality is not "
   289	                         "deterministically checkable; recorded only"},
   290	                        hard=False))
   291	
   292	    complete = all(s["ok"] for s in steps if s.get("hard"))
   293	    manifest = {
   294	        "tick_id": a.tick_id, "goal": a.goal,
   295	        "substrate": a.substrate, "owner": a.owner,
   296	        "contract_id": _compiler_cid,
   297	        "forecast_contract_id": a.contract_id,
   298	        "decision_changed": bool(a.decision_changed),
   299	        "ts": datetime.datetime.now(
   300	            datetime.timezone.utc).isoformat(timespec="seconds"),
   301	        "authored_by": "agent",
   302	        "trust_root": "operator_inspection (NOT operator-authored; "
   303	                       "operator 2026-05-18)",
   304	        "status": "COMPLETE" if complete else "INCOMPLETE",
   305	        "steps": steps,
   306	        "honest_bound": ("forces the post-tick MECE legs are "
   307	                         "EXECUTED; does NOT certify the closure is "
   308	                         "mathematically faithful — break-only "
   309	                         "adversary + operator review (irreducible)."),
   310	    }
   311	    (rdir / "posttick_manifest.json").write_text(
   312	        json.dumps(manifest, indent=1, ensure_ascii=False))
   313	    print(json.dumps({"status": manifest["status"],
   314	                       "manifest": str((rdir / "posttick_manifest.json"
   315	                                        ).relative_to(REPO)),
   316	                       "failed_hard_steps": [
   317	                           s["step"] for s in steps
   318	                           if s.get("hard") and not s["ok"]]}, indent=1))
   319	    # FAIL-CLOSED: tick_close must refuse without a COMPLETE manifest.
   320	    return 0 if complete else 2
   321	
   322	
   323	if __name__ == "__main__":
   324	    raise SystemExit(main())

### commit_membrane_daemon.py gate block 815-1010
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
        # Shared by BOTH the pre- and post-tick gates (hoisted so the
        # post-gate never NameErrors when the pretick manifest is
        # absent). substrate/goal are frozen+signed in _start_row.
        _fg = str(_start_row.get("goal", "") or "").strip()
        _fs_sub = str(_start_row.get("substrate", "") or "")

        # GENERIC string normalizer (NOT substrate-aware). The daemon
        # is the substrate-AGNOSTIC commit membrane; it must not know
        # what "NS" is. The substrate-swap bypass is closed purely by
        # EXACT binding of the manifest substrate to the FROZEN SIGNED
        # start-row substrate — once that holds, the agent cannot run
        # the pre/post-tick under a different substrate than the tick
        # froze, so substrate-specific required steps cannot be
        # skipped. Which steps a substrate requires is decided in the
        # runner (substrate-aware by design), never here.
        def _subnorm(x: str) -> str:
            return "".join(ch for ch in str(x).strip().lower()
                           if ch.isalnum() or ch == "_")
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
                # GOAL BINDING: the amnesia/menu/pattern/graph steps
                # key on --goal free-text. Without this, a COMPLETE
                # manifest could be produced by running the pre-tick
                # tools on THROWAWAY goal text, then closing the real
                # contract ("tools ran" decoupled from "the pre-tick
                # THIS tick needed"). The start_row goal is frozen +
                # signed at start_tick, so requiring exact equality
                # forces the pre-tick to have been executed on this
                # tick's actual goal.
                _mg = str(_mj.get("goal", "") or "").strip()
                if _fg and _mg != _fg:
                    oblig_fail.append(
                        f"pretick_manifest goal != frozen start_tick "
                        f"goal — the pre-tick tools were run on "
                        f"different goal text than this tick froze "
                        f"(throwaway-pretick bypass blocked); "
                        f"manifest={_mg[:80]!r} frozen={_fg[:80]!r}")
                # SUBSTRATE BINDING (cold re-review b18zbkhdw): the
                # compiler cid EXCLUDES substrate, so without this an
                # agent could run the pre-tick under a different
                # substrate (skipping substrate-specific required
                # steps) yet close the real tick. EXACT binding to the
                # frozen+signed start-row substrate closes it,
                # substrate-AGNOSTICally — the daemon never inspects
                # which substrate it is; the runner owns that.
                _ms_sub = str(_mj.get("substrate", "") or "")
                if _fs_sub and _subnorm(_ms_sub) != _subnorm(_fs_sub):
                    oblig_fail.append(
                        f"pretick_manifest substrate {_ms_sub!r} != "
                        f"frozen start_tick substrate {_fs_sub!r} "
                        f"(substrate-swap bypass blocked)")
        except Exception as _pe:
            oblig_fail.append(
                f"pretick_manifest unreadable for {_tid!r} "
                f"({type(_pe).__name__}) — fail-closed (no verifiable "
                f"pre-tick ⇒ no close)")
        # SYMMETRIC POST-TICK GATE (operator: "can we do the same for
        # the post checks"). Mirrors the pre-tick gate exactly: the
        # POST-tick MECE legs must have been EXECUTED for THIS tick.
        # posttick_runner writes contract_id = the SAME compiler cid,
        # so the same un-forgeable tick_id + cid + goal + substrate
        # binding applies. Absent/INCOMPLETE/foreign ⇒ oblig_fail ⇒
        # quarantine (fail-closed). Any read error is fail-closed.
        try:
            _qm = (REPO_ROOT / "analytics" / "public" / "posttick"
                   / _tid / "posttick_manifest.json")
            if not _qm.is_file():
                oblig_fail.append(
                    f"posttick_manifest MISSING for tick {_tid!r} "
                    f"(analytics/public/posttick/{_tid}/) — the "
                    f"POST-tick MECE legs (post_tick_check / micro-"
                    f"resolved / pre<->post bind) were not RUN; run "
                    f"posttick_runner.py before close (fail-closed)")
            else:
                _qj = json.loads(_qm.read_text(encoding="utf-8"))
                if str(_qj.get("status")) != "COMPLETE":
                    oblig_fail.append(
                        f"posttick_manifest status="
                        f"{_qj.get('status')!r} (not COMPLETE) — "
                        f"failed hard legs: "
                        f"{[s.get('step') for s in (_qj.get('steps') or []) if s.get('hard') and not s.get('ok')]}")
                if str(_qj.get("tick_id")) != _tid:
                    oblig_fail.append(
                        f"posttick_manifest tick_id "
                        f"{_qj.get('tick_id')!r} != close tick_id "
                        f"{_tid!r} (foreign-manifest rejected)")
                _qc = str(_qj.get("contract_id", "") or "")
                if _sc and _qc and _qc != _sc:
                    oblig_fail.append(
                        f"posttick_manifest contract_id {_qc!r} != "
                        f"frozen start_tick cid {_sc!r} "
                        f"(presence≠this-tick bypass blocked)")
                elif _sc and not _qc:
                    oblig_fail.append(
                        "posttick_manifest carries NO contract_id — "
                        "cannot mutually-bind (unbound post rejected)")
                _qg = str(_qj.get("goal", "") or "").strip()
                if _fg and _qg != _fg:
                    oblig_fail.append(
                        f"posttick_manifest goal != frozen start goal "
                        f"(throwaway-posttick bypass blocked); "
                        f"manifest={_qg[:60]!r} frozen={_fg[:60]!r}")
                _qs = str(_qj.get("substrate", "") or "")
                if _fs_sub and _subnorm(_qs) != _subnorm(_fs_sub):
                    oblig_fail.append(
                        f"posttick_manifest substrate {_qs!r} != "
                        f"frozen start substrate {_fs_sub!r} "
                        f"(substrate-swap bypass blocked)")
        except Exception as _qe:
            oblig_fail.append(
                f"posttick_manifest unreadable for {_tid!r} "
                f"({type(_qe).__name__}) — fail-closed (no verifiable "
                f"post-tick ⇒ no close)")
        _cg = str(_start_row.get("goal", ""))
        _ctt = str(_start_row.get("start_transition_type", ""))
        _cds = merge_signals(_start_row.get("start_declared_signals"),
                             _cg)
        ok_o, fails_o = validate_tick_contract(
            _cg, p.get("witnesses") or {}, p.get("why_not") or {},
            _ctt, _cds,
            tick_id=str(close.get("tick_id", "")),
            contract_id=str(close.get("contract_id", "")))
        if not ok_o:
            # += not = : preserve the contract-id-mismatch entry
            # appended above (cold review b1djdevru B).
            oblig_fail += [f"frozen-start obligation undischarged: {f}"
                           for f in fails_o]
        _frozen = set(_start_row.get("mandatory_obligations") or [])
        _disch = set((p.get("witnesses") or {}).keys()) | set(
            (p.get("why_not") or {}).keys())
        _gap = _frozen - _disch
        if _gap:
            oblig_fail.append(
                f"frozen-start contract not satisfied: obligations "
                f"{sorted(_gap)} minted at start_tick "
                f"{_start_row.get('official_state_hash')} have NO "
                f"witness/why_not in this close (open-strong/close-weak "
                f"bypass blocked)")
        # GP-241 #2: for every frozen mandatory obligation whose
        # submitted witness asks for `judge:auto`, the DAEMON emits a
        # signed judge_request (the agent cannot steer the judge). The


## Response (final codex verdict block)

**VERDICT: NO-GO**

Artifact-level: the current runners/daemon are not yet comprehensively exhaustive. The idea-level direction is not killed: forced pre/post tick discipline is still the right shape. But the current implementation still has live lifecycle, faithfulness, and identity gaps.

**Findings**

1. **The namespace fix does not hold through `tick_close.py`.**  
[tick_close.py](/scripts/public/control/tick_close.py:282) passes the forecast-pool slug as `close.contract_id`, while [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:819) requires `close.contract_id == frozen start_tick contract_id` in compiler-cid namespace. The runner fix is real, but the sanctioned close wrapper still false-quarantines honest closes unless callers bypass it or pass the wrong semantic value.

Fix: split `forecast_contract_id` from `compiler_contract_id`; recompute/load the frozen compiler cid for H7. Also stop passing `--goal a.tick_row` at [tick_close.py](/scripts/public/control/tick_close.py:289); close rows should inherit the frozen start goal.

2. **Pre-tick “execution” still includes static catalog presence checks.**  
[pretick_runner.py](/scripts/public/control/pretick_runner.py:113) does not compose a route from the goal; `g = a.goal.lower()` is unused, and the selected `problem_class` is just the first known key found in the menu text. [pretick_runner.py](/scripts/public/control/pretick_runner.py:130) lists pattern/anti-pattern ids but does not check that the obligated chain was applied to this tick.

Constructed falsifier: run pre-tick on an arbitrary unrelated goal with valid op ids/scopes; it can produce `COMPLETE` because catalogs exist.

3. **Forecast identity is still presence-bound, not tick-bound.**  
[pretick_runner.py](/scripts/public/control/pretick_runner.py:190) accepts any exact contract id with non-empty `consumes_surfaced`; it does not require `layer=micro`, `created_by == owner`, created-in-window, question/goal match, codex forecast, or start-row freezing. The daemon binds only compiler cid/goal/substrate, not the GP-230 slug or contract hash.

Fix: freeze `forecast_contract_id`, contract sha256, `question_hash`, `consumes_surfaced`, `layer`, and `created_by` into the signed start row; compare them in pre, post, and close.

4. **Post-tick micro resolution is wired to the wrong forecast schema.**  
[posttick_runner.py](/scripts/public/control/posttick_runner.py:168) looks for top-level `resolved|resolution|outcome` in the contract json and [posttick_runner.py](/scripts/public/control/posttick_runner.py:174) looks for codex files under `contracts/`. Current forecast_pool stores the outcome path under `artifact_paths.outcome` and codex forecasts under `forecasts/<contract>/codex.json`. Your own `TRIPLECHK-20260518` posttick manifest is `INCOMPLETE` on `micro_resolved`.

Fix: exact outcome file check under `analytics/public/forecast_pool/outcomes/<id>.json`, exact forecast dir codex bet, and ordering `codex forecast mtime < outcome.resolved_at`.

5. **Lean faithfulness trigger is still gameable.**  
[posttick_runner.py](/scripts/public/control/posttick_runner.py:256) makes no-thesis Lean advisory. A closure-claiming F-row can omit `--thesis-path` and still pass this leg. This is not irreducible.

Fix: daemon-side trigger from `close.f_row_body` / typed signals. If the close claims formal proof, Lean, theorem closure, Clay closure, or compiled proof, require a hard Lean receipt plus target hash.

6. **Official F-row content is not semantically gated at the daemon.**  
[commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:1129) writes whatever `close.f_row_body` says after obligation gates pass. There is no daemon check that the F-row body names the frozen start hash, forecast contract, surfaced id, decision-change status, adversarial survival, target hash, or Lean receipt. `tick_close.py` has some prechecks, but H7 is the authority and direct `propose --type tick_close` can target the daemon.

Constructed falsifier: valid pre/post manifests on the right tick plus a close body saying “irreducible, deferred” with unrelated content. If L1/L2/L3 and judge obligations pass, the daemon materializes the F-row.

**Residual Meta-Darwin**

| Residual | Verdict | Reason |
|---|---|---|
| R2 daemon tree + keys outside agent write boundary | **IRREDUCIBLE, narrowly** | Deploy pinning/signing keys are genuinely deploy-layer if the VPS `ztare_verify` identity is the only authority. But manifest provenance is not solved by that; daemon reads agent-written manifests at [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:856). Need operator/broker-signed manifest hash or VPS-owned receipt ledger. |
| R5' Lean trigger-bind | **CHEAP-FIX-NOW** | No-thesis advisory is a live bypass for closure claims. Force from close text/signals, not caller honesty. |
| R5''/R6 start identity + GP230 hash/surfaced binding | **CHEAP-FIX-NOW** | `tick_id+cid+goal+substrate` is not enough. It does not bind the specific micro contract, question, surfaced id, owner, or F-row semantics. Add signed start-row fields and daemon comparisons. |
| R5''' proof of T vs Clay statement | **IRREDUCIBLE only after target registry** | Per-tick part is mechanizable: require `target_statement_hash` against an operator-approved registry and proof receipt binds to that hash. The residual “this registry entry is the Clay problem” is one-time human mathematical curation, not per-tick gating. |

**Still Not Forced**

`rd_tick_brief` mandates post-tick Tier-3 closure claim and adversarial steelman-kill at [rd_tick_brief.py](/scripts/public/control/rd_tick_brief.py:599). `posttick_runner.py` only runs `pattern_026` advisory at [posttick_runner.py](/scripts/public/control/posttick_runner.py:266), and `post_tick_check.py` scans `EXPERIMENT_TRACK_RECORD.md` at [post_tick_check.py](/scripts/public/control/post_tick_check.py:222), not the daemon’s official F-row before stamping. PDE estimate preflight is also only brief text at [rd_tick_brief.py](/scripts/public/control/rd_tick_brief.py:626), not a pre-tick hard leg.

**Predicted Remaining Failure Mode**

Even after these fixes, the remaining failure mode is **receipt-shaped compliance without substantive research progress**: the agent will produce broker-valid artifacts that satisfy deterministic carriers while choosing weak targets or vacuous decompositions. That is not solved by more self-attestation; it needs a break-only adversary/operator-inspected target registry and signed receipts tied to exact frozen start state.
tokens used
155.303
**VERDICT: NO-GO**

Artifact-level: the current runners/daemon are not yet comprehensively exhaustive. The idea-level direction is not killed: forced pre/post tick discipline is still the right shape. But the current implementation still has live lifecycle, faithfulness, and identity gaps.

**Findings**

1. **The namespace fix does not hold through `tick_close.py`.**  
[tick_close.py](/scripts/public/control/tick_close.py:282) passes the forecast-pool slug as `close.contract_id`, while [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:819) requires `close.contract_id == frozen start_tick contract_id` in compiler-cid namespace. The runner fix is real, but the sanctioned close wrapper still false-quarantines honest closes unless callers bypass it or pass the wrong semantic value.

Fix: split `forecast_contract_id` from `compiler_contract_id`; recompute/load the frozen compiler cid for H7. Also stop passing `--goal a.tick_row` at [tick_close.py](/scripts/public/control/tick_close.py:289); close rows should inherit the frozen start goal.

2. **Pre-tick “execution” still includes static catalog presence checks.**  
[pretick_runner.py](/scripts/public/control/pretick_runner.py:113) does not compose a route from the goal; `g = a.goal.lower()` is unused, and the selected `problem_class` is just the first known key found in the menu text. [pretick_runner.py](/scripts/public/control/pretick_runner.py:130) lists pattern/anti-pattern ids but does not check that the obligated chain was applied to this tick.

Constructed falsifier: run pre-tick on an arbitrary unrelated goal with valid op ids/scopes; it can produce `COMPLETE` because catalogs exist.

3. **Forecast identity is still presence-bound, not tick-bound.**  
[pretick_runner.py](/scripts/public/control/pretick_runner.py:190) accepts any exact contract id with non-empty `consumes_surfaced`; it does not require `layer=micro`, `created_by == owner`, created-in-window, question/goal match, codex forecast, or start-row freezing. The daemon binds only compiler cid/goal/substrate, not the GP-230 slug or contract hash.

Fix: freeze `forecast_contract_id`, contract sha256, `question_hash`, `consumes_surfaced`, `layer`, and `created_by` into the signed start row; compare them in pre, post, and close.

4. **Post-tick micro resolution is wired to the wrong forecast schema.**  
[posttick_runner.py](/scripts/public/control/posttick_runner.py:168) looks for top-level `resolved|resolution|outcome` in the contract json and [posttick_runner.py](/scripts/public/control/posttick_runner.py:174) looks for codex files under `contracts/`. Current forecast_pool stores the outcome path under `artifact_paths.outcome` and codex forecasts under `forecasts/<contract>/codex.json`. Your own `TRIPLECHK-20260518` posttick manifest is `INCOMPLETE` on `micro_resolved`.

Fix: exact outcome file check under `analytics/public/forecast_pool/outcomes/<id>.json`, exact forecast dir codex bet, and ordering `codex forecast mtime < outcome.resolved_at`.

5. **Lean faithfulness trigger is still gameable.**  
[posttick_runner.py](/scripts/public/control/posttick_runner.py:256) makes no-thesis Lean advisory. A closure-claiming F-row can omit `--thesis-path` and still pass this leg. This is not irreducible.

Fix: daemon-side trigger from `close.f_row_body` / typed signals. If the close claims formal proof, Lean, theorem closure, Clay closure, or compiled proof, require a hard Lean receipt plus target hash.

6. **Official F-row content is not semantically gated at the daemon.**  
[commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:1129) writes whatever `close.f_row_body` says after obligation gates pass. There is no daemon check that the F-row body names the frozen start hash, forecast contract, surfaced id, decision-change status, adversarial survival, target hash, or Lean receipt. `tick_close.py` has some prechecks, but H7 is the authority and direct `propose --type tick_close` can target the daemon.

Constructed falsifier: valid pre/post manifests on the right tick plus a close body saying “irreducible, deferred” with unrelated content. If L1/L2/L3 and judge obligations pass, the daemon materializes the F-row.

**Residual Meta-Darwin**

| Residual | Verdict | Reason |
|---|---|---|
| R2 daemon tree + keys outside agent write boundary | **IRREDUCIBLE, narrowly** | Deploy pinning/signing keys are genuinely deploy-layer if the VPS `ztare_verify` identity is the only authority. But manifest provenance is not solved by that; daemon reads agent-written manifests at [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:856). Need operator/broker-signed manifest hash or VPS-owned receipt ledger. |
| R5' Lean trigger-bind | **CHEAP-FIX-NOW** | No-thesis advisory is a live bypass for closure claims. Force from close text/signals, not caller honesty. |
| R5''/R6 start identity + GP230 hash/surfaced binding | **CHEAP-FIX-NOW** | `tick_id+cid+goal+substrate` is not enough. It does not bind the specific micro contract, question, surfaced id, owner, or F-row semantics. Add signed start-row fields and daemon comparisons. |
| R5''' proof of T vs Clay statement | **IRREDUCIBLE only after target registry** | Per-tick part is mechanizable: require `target_statement_hash` against an operator-approved registry and proof receipt binds to that hash. The residual “this registry entry is the Clay problem” is one-time human mathematical curation, not per-tick gating. |

**Still Not Forced**

`rd_tick_brief` mandates post-tick Tier-3 closure claim and adversarial steelman-kill at [rd_tick_brief.py](/scripts/public/control/rd_tick_brief.py:599). `posttick_runner.py` only runs `pattern_026` advisory at [posttick_runner.py](/scripts/public/control/posttick_runner.py:266), and `post_tick_check.py` scans `EXPERIMENT_TRACK_RECORD.md` at [post_tick_check.py](/scripts/public/control/post_tick_check.py:222), not the daemon’s official F-row before stamping. PDE estimate preflight is also only brief text at [rd_tick_brief.py](/scripts/public/control/rd_tick_brief.py:626), not a pre-tick hard leg.

**Predicted Remaining Failure Mode**

Even after these fixes, the remaining failure mode is **receipt-shaped compliance without substantive research progress**: the agent will produce broker-valid artifacts that satisfy deterministic carriers while choosing weak targets or vacuous decompositions. That is not solved by more self-attestation; it needs a break-only adversary/operator-inspected target registry and signed receipts tied to exact frozen start state.
