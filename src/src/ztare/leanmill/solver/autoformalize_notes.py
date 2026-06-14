#!/usr/bin/env python3
"""Autoformalize + attack a proof FROM RESEARCH NOTES — a blueprint-decomposition loop over the canonical
`autoformalize_and_solve` (NL → faithfulness firewall → solve_adhoc_governed + governance kernel). This is
the LEAP / DeepSeek-Prover-V2 blueprint-decomposition pattern with the blueprint supplied as NOTES.

WHY this is solver SOURCE (not an experiment): formalizing a NL blueprint, proving each lemma through the
firewall+kernel, accumulating a citable proven-lemma SHELF, and attacking the target is GENERAL apparatus.
Specific problem corpora are the experiment-specific INPUTS that feed this loop; the loop is reusable and
belongs next to the `autoformalize_and_solve` it orchestrates.

The decomposition lives INSIDE leanmill at TWO levels — this is the LITE design (no autoresearch
evidence-mutation machinery, no `orchestrator.mutator_briefing`; that does open-ended DISCOVERY, this
PROVES a known blueprint):
  • TOP level (this module): the notes ARE the coarse decomposition (lemmas in dependency order). The agent
    does not have to invent the breakdown — a human / research-director blueprint supplies it.
  • RECURSIVE retry (INHERITED, no new engine): each line is attacked through `autoformalize_and_solve` →
    `default_solve` → `solve_adhoc`, and `solve_adhoc` already routes an HONEST non-closure (exact_gap /
    open / failed) to the recursive planner `isomorphism_decompose.route_and_solve` under
    `ZTARE_LEANMILL_ISO_ROUTE` (default-on): the warm leaf GENERATES a sub-decomposition, the KERNEL audits
    it, each sub-lemma re-enters the route (depth-guarded), then composite-ratifies. So the notes loop gets
    the agent's recursive re-decomposition for free — it does NOT fork a recursion engine or an assembler.

Notes format (markdown, dependency order — most foundational lemma first):
    ## Target
    <one NL sentence: the theorem to ultimately prove>
    ## Lemmas
    - <NL lemma 1>
    - <NL lemma 2>

Each line runs through `autoformalize_and_solve`: the firewall GATES it (unfaithful / vacuous / trivial →
rejected before any solve), an admitted statement is attacked by the kernel. Lemmas that CLOSE accumulate as
a citable SHELF (only `outcome == "closed"` counts — `exact_gap` / `open` do NOT, see `_default_attack`).

SERIAL Lean (every `_compile_probe` is a fresh Mathlib reload; no parallel compiles on one box).
CLI:  PYTHONPATH=src python -m ztare.leanmill.solver.autoformalize_notes <notes.md>
      PYTHONPATH=src python -m ztare.leanmill.solver.autoformalize_notes --selftest
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parents[4]
LEAN_ROOT_DEFAULT = (REPO / "ztare_proofs").resolve()


def parse_notes(text: str) -> "tuple[str, list[str]]":
    """Parse the `## Target` paragraph + the `- ` bullets under `## Lemmas`. Deterministic markdown-STRUCTURE
    parsing (not agent-output parsing — those use `agent_output`); the value is the formalize+attack loop, not
    a notes DSL. Tolerates `*` bullets and blank lines."""
    target = ""
    m = re.search(r"(?ms)^##\s*Target\s*\n(.+?)(?=^##|\Z)", text)
    if m:
        target = " ".join(l.strip() for l in m.group(1).strip().splitlines() if l.strip())
    lemmas: "list[str]" = []
    lm = re.search(r"(?ms)^##\s*Lemmas\s*\n(.+?)(?=^##|\Z)", text)
    if lm:
        lemmas = [re.sub(r"^[-*]\s*", "", l).strip() for l in lm.group(1).splitlines()
                  if l.strip().startswith(("-", "*"))]
    return target, lemmas


def _default_attack(nl: str, *, lean_root: Path, timeout_s: int, notes: "str | None" = None) -> dict:
    """Real apparatus: one NL line → faithfulness firewall → governed solve → compact per-piece record.
    `notes` (the blueprint) threads into the recursive planner when the line does NOT close directly.
    `solved` is True ONLY when the governed outcome is `closed`. (`autoformalize_and_solve` puts the per-
    result outcome string in `solved`, so `exact_gap` / `open` are TRUTHY strings — taking `bool(outcome)`
    would mark an unproven gap as solved. That false-positive is fixed here at the source.)"""
    from ztare.leanmill.solver.autoformalize import autoformalize_and_solve
    r = autoformalize_and_solve(nl, sandbox=lean_root, timeout_s=timeout_s, notes=notes)
    return {"nl": nl, "lean_statement": (r.get("lean_statement") or ""),
            "faithful": r.get("faithful"), "outcome": r.get("outcome"),
            "solved": (r.get("solved") == "closed"),
            # OBSERVABILITY: keep the firewall's verdict REASON + per-leg checks — without these a
            # `faithful=False` is a black box (you can't tell compile-fail vs round-trip vs structural).
            # They were dropped here, so neither the log nor the .autoformalize_result.json artifact had them.
            "faithfulness_reason": r.get("faithfulness_reason"),
            "faithfulness_checks": r.get("faithfulness_checks"),
            "decomposition": r.get("decomposition")}   # #81: the planner's actual sub-DAG (route_and_solve)


def autoformalize_from_notes(notes_text: str, *, lean_root: Optional[Path] = None,
                             lemma_timeout_s: "Optional[int]" = None, target_timeout_s: "Optional[int]" = None,
                             attack_fn: Optional[Callable[..., dict]] = None,
                             notes_path: Optional[Path] = None,
                             on_progress: Optional[Callable[[str], None]] = None) -> dict:
    """Blueprint-decomposition loop: parse notes → prove each lemma through the firewall+kernel → accumulate
    a citable proven-lemma SHELF → attack the target. Every leg is injectable so the selftest is hermetic:
    `attack_fn(nl, *, lean_root, timeout_s, notes) -> record` defaults to `_default_attack` (the real apparatus);
    `on_progress(msg)` defaults to print. Returns
        {target_nl, lemmas:[record], target:record|None, shelf:[lean_statement of CLOSED lemmas], summary}.
    Wiring the shelf into the target solve as cited premises is the planner / composite-ratification path."""
    lean_root = Path(lean_root) if lean_root is not None else LEAN_ROOT_DEFAULT
    attack_fn = attack_fn or _default_attack
    log = on_progress or (lambda m: print(m, flush=True))
    # GENEROUS whole-attack wallclocks from the central factory (NOT hardcoded 400/600 — those guillotined a
    # codex run that had an audit-passing DAG ready). The planner draws from these (no arbitrary sub-cap);
    # env-tunable + self-learnable. Caller can still override explicitly.
    if lemma_timeout_s is None or target_timeout_s is None:
        from ztare.common.timeouts import timeout_s as _tbudget
        lemma_timeout_s = _tbudget("notes_lemma") if lemma_timeout_s is None else lemma_timeout_s
        target_timeout_s = _tbudget("notes_target") if target_timeout_s is None else target_timeout_s

    target, lemmas = parse_notes(notes_text)
    try:                                          # record the in-force time budgets up front (observability:
        from ztare.common.timeouts import budgets_report   # a stalled run's banner shows which budget governed)
        log(f"[budgets] {budgets_report()}")
    except Exception:  # noqa: BLE001
        pass
    log(f"[notes] target: {target!r}")
    log(f"[notes] {len(lemmas)} lemma(s) (foundational first)")

    out: dict = {"target_nl": target, "lemmas": [], "shelf": []}
    for i, lem in enumerate(lemmas):
        log(f"[notes] lemma {i + 1}/{len(lemmas)}: {lem!r}")
        # the WHOLE blueprint is the planner context for each lemma (the surrounding lemmas are scaffold)
        rec = attack_fn(lem, lean_root=lean_root, timeout_s=lemma_timeout_s, notes=notes_text)
        out["lemmas"].append(rec)
        if rec.get("solved"):
            out["shelf"].append(rec.get("lean_statement") or "")
        log(f"  -> faithful={rec.get('faithful')} outcome={rec.get('outcome')} solved={rec.get('solved')}"
            + (f" | reason={str(rec.get('faithfulness_reason'))[:200]}" if rec.get('faithful') is not True else ""))
        if notes_path is not None:               # INCREMENTAL write-back — survive a timeout/kill. The end-of-run
            try:                                 # write was LOST when the 100-min budget killed the run mid-solve;
                write_refined_notes(out, notes_path)   # this re-emits the deterministic ✅-closed shelf after every
            except Exception:  # noqa: BLE001    # lemma (cheap; no warm-agent synthesis — main() adds that at the end).
                pass

    # the TARGET gets the blueprint PLUS the proven shelf — the planner sees which lemmas are already citable
    target_notes = notes_text
    if out["shelf"]:
        target_notes = (notes_text.rstrip() + "\n\n## Proven lemmas (citable):\n"
                        + "\n".join(f"- {s}" for s in out["shelf"] if s))
    log(f"[notes] TARGET: {target!r}")
    out["target"] = (attack_fn(target, lean_root=lean_root, timeout_s=target_timeout_s, notes=target_notes)
                     if target else None)
    if out["target"]:
        t = out["target"]
        log(f"  -> faithful={t.get('faithful')} outcome={t.get('outcome')} solved={t.get('solved')}"
            + (f" | reason={str(t.get('faithfulness_reason'))[:200]}" if t.get('faithful') is not True else ""))

    n_ok = sum(1 for l in out["lemmas"] if l.get("solved"))
    target_closed = bool((out["target"] or {}).get("solved"))
    out["summary"] = (f"{n_ok}/{len(lemmas)} lemmas formalized+closed; shelf={len(out['shelf'])}; "
                      f"target {'closed' if target_closed else 'open'}")
    return out


def write_refined_notes(result: dict, notes_path: "Path", *, dispatch: "Optional[Callable]" = None) -> "Path":
    """The APPARATUS updates its own research notes — the operator should NOT re-draft. GOLDILOCKS split:
      • DETERMINISTIC (this code) owns the GOVERNED FACTS — which lemmas KERNEL-CLOSED + the proven shelf. The
        agent must never author these or it could write down a closure that never happened (fake closure).
      • The WARM AGENT authors the SYNTHESIS — for each still-OPEN lemma it proposes a DEEPER decomposition
        (the next sub-lemmas to attempt). Research-notes authoring is creative, not a mechanical dump.
    Gated by `ZTARE_LEANMILL_AGENT_REFINE_NOTES` (default-off ⇒ deterministic factual fallback, parity). The
    next run reads `<name>.refined.md` and compounds (cites the shelf, attacks the agent's finer breakdown);
    the operator's seed is preserved. This closes the loop — the planner drafts+refines, no human in it."""
    import os as _os
    closed = [l for l in result.get("lemmas", []) if l.get("solved")]
    open_ = [l for l in result.get("lemmas", []) if not l.get("solved")]
    shelf = [s for s in (result.get("shelf") or []) if s]
    # ── DETERMINISTIC governed-facts section (the agent CANNOT fabricate a closure) ──
    det = [f"# {(result.get('target_nl') or '')[:90]} — apparatus-refined",
           f"<!-- {result.get('summary', '')} -->", "", "## Target", (result.get("target_nl") or ""), "",
           "## Proven this run (✅ kernel-closed — citable):"]
    det += ([f"- ✅ {l.get('nl', '')}" for l in closed] or ["- (none kernel-closed this run)"])
    if shelf:
        det += ["", "## Proven shelf (cite these):"] + [f"- {s}" for s in shelf]
    # ── Open-lemma synthesis. PREFER the PLANNER's ACTUAL sub-DAG (route_and_solve's decomposition — the same
    #    agent's mid-proof breakdown, already in the result); deterministically RENDER it (rendering the agent's
    #    own output is not authoring). Only lemmas the planner did NOT decompose get a fresh re-proposal dispatch. ──
    agent_md = ""
    if open_:
        open_md = ["## Open frontier — refined decomposition (attempt next)"]
        no_dag = []
        for l in open_:
            dec = l.get("decomposition") or {}
            sub = dec.get("lemmas") or []
            if sub:                                  # the planner already decomposed this lemma — persist its sub-DAG
                tag = " [kernel-audited]" if dec.get("audited") else ""
                open_md.append(f"\n### ⬜ {l.get('nl', '')}{tag} — planner sub-decomposition:")
                open_md += [f"- {str(s)[:220]}" for s in sub]
            else:
                no_dag.append(l)
        if no_dag and dispatch is not None and _os.environ.get("ZTARE_LEANMILL_AGENT_REFINE_NOTES") == "1":
            facts = "\n".join(f"- OPEN: {l.get('nl', '')} | outcome: {l.get('outcome')}" for l in no_dag)
            prompt = ("You are a research mathematician REFINING your proof blueprint. These lemmas did NOT close "
                      "and the planner produced no sub-decomposition:\n" + facts + "\n\nFor EACH, propose a DEEPER "
                      "decomposition — 2–4 smaller, foundational-first sub-lemmas whose conjunction proves it, for "
                      "the prover to attempt next. Output ONLY markdown bullets. Do NOT claim anything is proven.")
            from ztare.common.timeouts import timeout_s   # central budget factory (byte-parity: notes_refine defaults to the prior 240)
            try:
                extra = (dispatch(prompt, repo=LEAN_ROOT_DEFAULT, timeout=timeout_s("notes_refine")) or "").strip()
                if extra:
                    open_md += ["", extra]
            except Exception:  # noqa: BLE001 — best-effort
                pass
        elif no_dag:
            open_md += [f"\n- ⬜ {l.get('nl', '')} (outcome: {l.get('outcome')}; no planner decomposition)" for l in no_dag]
        agent_md = "\n".join(open_md)
    refined = notes_path.with_suffix(".refined.md")
    refined.write_text("\n".join(det) + "\n\n" + agent_md + "\n", encoding="utf-8")
    return refined


def _self_test() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # --- parse ---
    NOTES = "## Target\nFor all n, P n.\n## Lemmas\n- Lemma A.\n* Lemma B.\n"
    tgt, lems = parse_notes(NOTES)
    ok("parse_target", tgt == "For all n, P n.")
    ok("parse_lemmas_dash_and_star", lems == ["Lemma A.", "Lemma B."])
    ok("parse_no_lemmas_section", parse_notes("## Target\nX.\n")[1] == [])
    ok("parse_multiline_target",
       parse_notes("## Target\nline one\nline two\n## Lemmas\n- L.\n")[0] == "line one line two")

    # --- hermetic loop: Lemma A closes, Lemma B exact_gaps, target opens ---
    seen_notes: dict = {}

    def mock_attack(nl, *, lean_root, timeout_s, notes=None):
        seen_notes[nl] = notes
        closed = nl == "Lemma A."
        return {"nl": nl, "lean_statement": f"theorem t : {nl} := by sorry", "faithful": True,
                "outcome": "admitted_and_closed" if closed else "admitted_and_exact_gap",
                "solved": closed}

    res = autoformalize_from_notes(NOTES, attack_fn=mock_attack, on_progress=lambda m: None)
    ok("loop_runs_all_lemmas", len(res["lemmas"]) == 2)
    ok("shelf_only_closed_lemmas", res["shelf"] == ["theorem t : Lemma A. := by sorry"])
    ok("summary_counts", res["summary"].startswith("1/2 lemmas formalized+closed; shelf=1;"))
    ok("target_attacked", res["target"] is not None and res["target"]["nl"] == "For all n, P n.")
    # the blueprint is threaded as planner context for every line (the #81 uplevel)
    ok("notes_threaded_to_lemmas", "## Lemmas" in (seen_notes.get("Lemma A.") or ""))
    ok("target_notes_carry_shelf",
       "Proven lemmas (citable)" in (seen_notes.get("For all n, P n.") or "")
       and "theorem t : Lemma A." in (seen_notes.get("For all n, P n.") or ""))

    # --- the false-positive guard: a non-'closed' truthy outcome must NOT count as solved ---
    def gap_attack(nl, *, lean_root, timeout_s, notes=None):
        return {"nl": nl, "lean_statement": "", "faithful": True,
                "outcome": "admitted_and_exact_gap", "solved": False}

    r2 = autoformalize_from_notes("## Target\nG.\n## Lemmas\n- A.\n",
                                  attack_fn=gap_attack, on_progress=lambda m: None)
    ok("exact_gap_not_in_shelf", r2["shelf"] == [])
    ok("exact_gap_zero_closed", r2["summary"].startswith("0/1 lemmas"))

    # --- empty target → no target attack, loop still runs lemmas ---
    r3 = autoformalize_from_notes("## Lemmas\n- A.\n", attack_fn=mock_attack, on_progress=lambda m: None)
    ok("empty_target_no_attack", r3["target"] is None and r3["summary"].endswith("target open"))

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


def compound_into_original_notes(result: dict, notes_path: "Optional[Path]") -> "Optional[Path]":
    """COMPOUND the PLANNER's own generated decomposition back into the ORIGINAL notes (#97, operator vision:
    the agent adds the breakdown itself — "in the original file", not just .refined.md). Source = the
    `decomposition` sub-DAG `route_and_solve` already stashes in each attack record (the TARGET's, for a minimal
    seed, plus any per-lemma sub-DAGs) — NOT human-authored. Rewrites ONLY the `## Lemmas` section, PRESERVING
    the human `## Target` / `## Idea` (everything before `## Lemmas`); the next run's parser then attacks the
    agent's OWN breakdown → the compounding loop closes with no human in it. Deterministic render of the agent's
    output (not authoring), so no fake-closure risk. SAFE + gated `ZTARE_LEANMILL_COMPOUND_ORIGINAL` (default-OFF
    until validated on a real run); no-op when the planner produced no decomposition (never clobbers the seed) or
    the file is not a parseable `## Target` seed."""
    import os as _os
    if _os.environ.get("ZTARE_LEANMILL_COMPOUND_ORIGINAL", "0") != "1" or notes_path is None:
        return None
    gen: "list[str]" = []
    def _collect(rec: "Optional[dict]") -> None:
        dec = (rec or {}).get("decomposition") or {}
        for s in (dec.get("lemmas") or []):
            t = " ".join(str(s).split()).strip()
            if t and t not in gen:
                gen.append(t)
    _collect(result.get("target"))
    for l in (result.get("lemmas") or []):
        _collect(l)
    if not gen:
        return None   # planner produced no decomposition ⇒ nothing to compound; leave the seed untouched
    try:
        text = notes_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not re.search(r"(?m)^##\s*Target\s*$", text):
        return None   # not a parseable seed ⇒ refuse (never clobber an unexpected file)
    head = re.split(r"(?m)^##\s*Lemmas\s*$", text)[0].rstrip()
    marker = ("<!-- ## Lemmas below: auto-compounded from the planner's OWN decomposition (route_and_solve, #97). "
              "Reseed by editing ## Target / ## Idea above; this section is regenerated each run. -->")
    notes_path.write_text(head + "\n\n" + marker + "\n## Lemmas\n"
                          + "\n".join(f"- {g}" for g in gen) + "\n", encoding="utf-8")
    return notes_path


def main(argv: "Optional[list[str]]" = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        return _self_test()
    if not argv:
        print("usage: python -m ztare.leanmill.solver.autoformalize_notes <notes.md> | --selftest")
        return 2
    from ztare.leanmill.preflight_carriers import assert_carriers_live
    assert_carriers_live()
    notes_path = Path(argv[0])
    # RUN ATTRIBUTION: tag this run's attempts-DB rows + forecast ledger so the compounder/forecast-router can
    # SLICE by run — the DB showed run_tag=NULL for notes runs (#92 said it should feed the substrate, but the
    # notes entry never set the env), making a run unattributable. setdefault RESPECTS an explicit A/B arm
    # (ZTARE_SOLVER_RUN_TAG=<arm>); otherwise defaults to the notes stem + a per-run stamp.
    import os as _os
    from datetime import datetime as _dt
    _os.environ.setdefault("ZTARE_SOLVER_RUN_TAG", f"notes_{notes_path.stem}_{_dt.now().strftime('%m%dT%H%M')}")
    print(f"[notes] run_tag = {_os.environ['ZTARE_SOLVER_RUN_TAG']}", flush=True)
    res = autoformalize_from_notes(notes_path.read_text(encoding="utf-8"), notes_path=notes_path)  # notes_path ⇒ incremental write-back (timeout-safe)
    artifact = notes_path.with_suffix(".autoformalize_result.json")
    artifact.write_text(json.dumps(res, indent=2, default=str))
    from ztare.leanmill.solver.agentic_leaf import default_dispatch  # the WARM AGENT authors the synthesis
    refined = write_refined_notes(res, notes_path, dispatch=default_dispatch)  # apparatus updates its OWN notes
    compounded = compound_into_original_notes(res, notes_path)  # #97: planner's decomposition → ORIGINAL notes (gated)
    print(f"\n[notes] {res['summary']}")
    print(f"[notes] artifact: {artifact}")
    print(f"[notes] refined blueprint (apparatus-updated, compounds next run): {refined}")
    if compounded:
        print(f"[notes] ORIGINAL notes compounded with the planner's decomposition: {compounded}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
