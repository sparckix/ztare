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


def parse_theory_file(text: str) -> "Optional[str]":
    """Parse the optional `## Theory file` section → the campaign-owned .lean path (#123, theory-first
    campaigns): the file the agent CREATES AND EXTENDS with definitions + API lemmas that Mathlib lacks —
    definitions as first-class work items (the NS-track manifest pattern transported to leanmill)."""
    m = re.search(r"(?ms)^##\s*Theory file\s*\n\s*(\S+\.lean)\s*$", text)
    return m.group(1) if m else None


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
    from ztare.leanmill.contracts.kernel import AttackRecord   # #49: typed record — `solved` is a BOOL, decided
    r = autoformalize_and_solve(nl, sandbox=lean_root, timeout_s=timeout_s, notes=notes)   # ONCE (outcome=="closed")
    # `.model_dump()` re-emits the exact legacy keys (nl/lean_statement/faithful/outcome/solved + the firewall
    # verdict reason/checks + the planner sub-DAG), so the notes loop + write-back are unchanged — but the
    # gap-as-solved false positive (`bool("exact_gap")` ⇒ True) is now impossible by construction.
    return AttackRecord.from_firewall_result(r, nl=nl).model_dump()


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
    # GLOBAL CAMPAIGN WALL (2026-06-13 — the "v6 ran 6 hours" RCA): the per-lemma/per-target budgets are
    # GENEROUS by design, but with deep recursion (ZTARE_ISO_MAX_DEPTH) their SUM across the tree is
    # effectively unbounded — v6 closed the easy rungs in 3h then ground the open-math crux for 3 more
    # (7 codex timeouts, 0 closures). This caps TOTAL wall: once the deadline passes, remaining lemmas/
    # target are SKIPPED as deferred (recorded honestly, never a fake closure). The earned rungs are
    # already kill-safe (incremental write-back below). 0 = disabled (parity). Default = generous so a
    # healthy run is never guillotined, but a grind-on-the-wall run STOPS instead of burning the night.
    import os as _os_w
    import time as _time_w
    _wall_s = int(_os_w.environ.get("ZTARE_LEANMILL_CAMPAIGN_WALL_S", "14400") or 0)   # 4h default
    _deadline = (_time_w.monotonic() + _wall_s) if _wall_s > 0 else None

    def _wall_exceeded() -> bool:
        return _deadline is not None and _time_w.monotonic() >= _deadline
    try:                                          # record the in-force time budgets up front (observability:
        from ztare.common.timeouts import budgets_report   # a stalled run's banner shows which budget governed)
        log(f"[budgets] {budgets_report()}")
        if _deadline is not None:
            log(f"[notes] global campaign wall: {_wall_s}s (deferred-skip past it; 0 disables)")
    except Exception:  # noqa: BLE001
        pass
    log(f"[notes] target: {target!r}")
    log(f"[notes] {len(lemmas)} lemma(s) (foundational first)")

    from datetime import datetime as _dt2, timezone as _tz2
    out: dict = {"target_nl": target, "lemmas": [], "shelf": [],
                 # cert-ledger watermark for the KILL-SAFE incremental deep-rung surfacing (same ISO-UTC
                 # format solve_adhoc stamps cert `ts` with — lexicographic compare is valid)
                 "run_started": _dt2.now(_tz2.utc).isoformat()}
    out["wall_deferred"] = []
    for i, lem in enumerate(lemmas):
        if _wall_exceeded():
            log(f"[notes] *** CAMPAIGN WALL reached — deferring lemma {i + 1}/{len(lemmas)} and the rest "
                f"(earned rungs already written back; not a failure) ***")
            out["wall_deferred"] = [str(x) for x in lemmas[i:]]
            break
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
                # KILL-SAFE deep rungs (v3/v4 lesson: killed runs are the NORM, not the exception): surface
                # all-depth kernel closures so far + compound the rungs-only section into the ORIGINAL notes
                # NOW (idempotent, sha-deduped, never clobbers ## Lemmas) — a kill after this point loses
                # nothing. The in-flight run is unaffected (it parsed notes_text at entry).
                out["deep_closures"] = deep_closures_since(out["run_started"])
                write_refined_notes(out, notes_path)   # re-emits the deterministic ✅-closed shelf after every
                if out["deep_closures"]:               # lemma (cheap; no warm-agent synthesis — main() adds that).
                    compound_into_original_notes({"target": None, "lemmas": [],
                                                  "deep_closures": out["deep_closures"]}, notes_path)
            except Exception:  # noqa: BLE001
                pass

    # AGENCY (#132 skip-and-return): a lemma that failed EARLY may close now that LATER lemmas proved —
    # their closures grew the citable shelf, which can unblock the earlier wall (a mathematician returns
    # to a stuck lemma after proving its neighbours). The fixed-order single pass couldn't do this. ONE
    # retry pass over the still-open lemmas, with the GROWN shelf in context, wall-respecting. Default-on
    # (sound knob — every retry still goes through the full firewall+kernel); ZTARE_LEANMILL_NOTES_RETRY=0
    # reverts to the single pass. Bounded (one pass) so it can't loop; the campaign wall caps total time.
    if _os_w.environ.get("ZTARE_LEANMILL_NOTES_RETRY", "1") != "0" and out["shelf"] and not _wall_exceeded():
        _open_idx = [i for i, l in enumerate(out["lemmas"]) if not l.get("solved")]
        if _open_idx:
            _shelf_notes = (notes_text.rstrip() + "\n\n## Proven lemmas (citable):\n"
                            + "\n".join(f"- {s}" for s in out["shelf"] if s))
            log(f"[notes] skip-and-return: retrying {len(_open_idx)} still-open lemma(s) with the grown "
                f"shelf ({len(out['shelf'])} proven) — a neighbour's closure may unblock them")
            for i in _open_idx:
                if _wall_exceeded():
                    log("[notes] skip-and-return: wall reached — stopping retries (earned rungs written back)")
                    break
                rec2 = attack_fn(lemmas[i], lean_root=lean_root, timeout_s=lemma_timeout_s, notes=_shelf_notes)
                if rec2.get("solved"):
                    out["lemmas"][i] = rec2
                    out["shelf"].append(rec2.get("lean_statement") or "")
                    log(f"[notes] *** skip-and-return CLOSED lemma {i + 1}/{len(lemmas)} on retry "
                        f"(unblocked by the grown shelf) ***")
                    if notes_path is not None:                 # kill-safe incremental write-back (as main loop)
                        try:
                            out["deep_closures"] = deep_closures_since(out["run_started"])
                            write_refined_notes(out, notes_path)
                            if out["deep_closures"]:
                                compound_into_original_notes({"target": None, "lemmas": [],
                                                              "deep_closures": out["deep_closures"]}, notes_path)
                        except Exception:  # noqa: BLE001
                            pass

    # the TARGET gets the blueprint PLUS the proven shelf — the planner sees which lemmas are already citable
    target_notes = notes_text
    if out["shelf"]:
        target_notes = (notes_text.rstrip() + "\n\n## Proven lemmas (citable):\n"
                        + "\n".join(f"- {s}" for s in out["shelf"] if s))
    if target and _wall_exceeded():
        log("[notes] *** CAMPAIGN WALL reached — deferring the TARGET attack (proven rungs are written "
            "back; the target stays HONESTLY OPEN, never a fake closure) ***")
        out["wall_deferred"].append(str(target))
        out["target"] = {"deferred": "campaign_wall", "solved": False}
    else:
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


_THEORY_PROMPT = (
    "THEORY CONSOLIDATION (definitions are first-class deliverables). You own the campaign theory file "
    "`{path}` in the Lean project `{root}`. The campaign target:\n{target}\n\nBlueprint notes follow at the "
    "end. Your job THIS dispatch: EXTEND the theory file with the missing FORMAL SUBSTRATE the blueprint "
    "needs and Mathlib lacks.\n"
    "DEFINITION DISCIPLINE — a definition has NO kernel oracle; it is judged by WORKABILITY, so work "
    "like a library designer, not a prover: (1) DIVERGE: for each needed concept draft 2-3 candidate "
    "formalizations (different shapes: a def via derivatives vs via coefficients vs via an existing "
    "Mathlib structure). (2) TRIAL: for each candidate, try to prove its MODEL-CASE sanity lemmas "
    "IMMEDIATELY (e.g. the concept evaluated on the simplest known instance gives the known answer; "
    "consistency with already-proven campaign rungs). (3) SELECT the candidate whose sanity lemmas "
    "PROVED — workability evidence, never taste — and ship: the chosen `def`/`structure`, its PROVEN "
    "sanity lemmas (no sorry on these), and the deeper API lemma STATEMENTS (those may be `sorry`; each "
    "becomes a solver work item). Prefer Mathlib-idiomatic shapes (typeclasses, existing algebraic "
    "structures) so library lemmas apply — search before inventing. (4) KILL LEG: if a candidate (or an "
    "EXISTING campaign structure) resists EVERY sanity instance, suspect it is UNINHABITED — try to PROVE "
    "`<name>_impossible` (its hypothesis set implies False / no instance exists). A COMPILED impossibility "
    "is a first-class deliverable: it kernel-certifies the route correction, and nothing may be built on "
    "that structure afterward. Prefer definitional bundling over compatibility hypotheses (fields "
    "definitionally equal to the source formula beat `h_compat : a = b` side-conditions — fewer "
    "assumptions to kill later). CREDIT: definitions earn through USE — your proven sanity lemmas count "
    "as rungs now; the definition itself is credited when campaign lemmas cite it.\n"
    "APPEND-ONLY THIS DISPATCH: never modify or delete existing content (governance reverts the round if "
    "existing bytes change). If an EXISTING definition is wrong-shaped, do not edit it — state "
    "`-- SUPERSEDE: <name>: <why>` and the harness routes a governed revision. Verify the file COMPILES "
    "(sorry allowed only on deep API) with the warm checker before finishing. Quality bar: minimal, "
    "citable, foundational-first — a library others build on.\n\nBLUEPRINT:\n{notes}\n")


def _anti_unify_block(lean_root: Path) -> str:
    """Advisory anti-unification leads (#124) for the theory-consolidation prompt: the top mined schema
    over OUR proven-rung corpus, rendered as a 'consider the common generalization' suggestion. Empty
    string on the kill-switch, no corpus, or no sibling pair found — never blocks the round."""
    import os as _os
    if _os.environ.get("ZTARE_LEANMILL_ANTIUNIFY", "1") == "0":
        return ""
    try:
        from ztare.leanmill.solver.anti_unify import mine_cert_pairs
        leads = mine_cert_pairs(max_pairs=2)
    except Exception:  # noqa: BLE001 — advisory; never fail the consolidation round
        return ""
    if not leads:
        return ""
    out = ["\n\n## Anti-unification leads (advisory — proven sibling rungs that may share one general lemma):"]
    for m in leads:
        out.append(f"- `{m['name_a']}` and `{m['name_b']}` instantiate a common schema "
                   f"({m['n_vars']} hole(s)): consider STATING + proving the general lemma, then deriving "
                   f"both as instances. Schema: {m['schema'][:160]}")
    out.append("(Only if it genuinely generalizes — if the holes force incompatible types, ignore this lead.)")
    return "\n".join(out)


def theory_consolidation(notes_text: str, theory_rel: str, *, lean_root: Path,
                         dispatch: "Optional[Callable]" = None,
                         compile_fn: "Optional[Callable]" = None) -> dict:
    """Phase 0 of a theory-first campaign (#123): the agent CREATES/EXTENDS the campaign-owned theory file;
    deterministic gates decide whether the round counts (Goldilocks: authorship is the agent's, the gates
    are mechanical):
      • APPEND-ONLY integrity — the prior content must appear VERBATIM in the new content (definition
        EDITING is the laundering surface statement_integrity exists for; here the baseline is the file
        itself, checked byte-level). Violation ⇒ file reverted, round rejected.
      • KERNEL COMPILE (sorry-tolerant) — the extended file must elaborate; a non-compiling theory round
        is reverted (never poison the campaign substrate).
    Returns {ok, reverted?, reason?, new_decls, sorried_statements} — `sorried_statements` (full theorem
    text) feed the run's lemma queue: API lemmas become ordinary governed work items."""
    theory_path = (lean_root / theory_rel) if not Path(theory_rel).is_absolute() else Path(theory_rel)
    theory_path.parent.mkdir(parents=True, exist_ok=True)
    before = theory_path.read_text(encoding="utf-8") if theory_path.exists() else ""
    if dispatch is not None:
        target, _ = parse_notes(notes_text)
        # ANTI-UNIFICATION LEADS (#124 consumer wiring): the library editor is exactly where mined schema
        # seeds belong — proven sibling rungs that instantiate one unstated general lemma become a
        # "consider stating the common generalization" advisory. Comment-style/advisory, fail-open,
        # ZTARE_LEANMILL_ANTIUNIFY=0 reverts; the kernel still gates anything the agent writes.
        _notes = notes_text[:8000] + _anti_unify_block(lean_root)
        # REAL timeout (bug 2026-06-13: passed timeout=None → default_dispatch does int(None) → crash; the
        # mock-only selftest never hit it). Theory-building is substantial — use the per-lemma budget.
        from ztare.common.timeouts import timeout_s as _ts_theory
        _theory_to = _ts_theory("notes_lemma")
        _prompt = _THEORY_PROMPT.format(path=str(theory_path), root=str(lean_root), target=target, notes=_notes)
        try:
            dispatch(_prompt, repo=lean_root, timeout=_theory_to)
        except TypeError:   # dispatch signatures vary (timeout kw optional on injected fakes)
            dispatch(_prompt, repo=lean_root)
        except Exception as e:  # noqa: BLE001 — a failed dispatch leaves the file as-is; gates decide below
            return {"ok": False, "reason": f"dispatch error: {repr(e)[:120]}"}
    after = theory_path.read_text(encoding="utf-8") if theory_path.exists() else ""
    if after == before:
        return {"ok": True, "unchanged": True, "new_decls": [], "sorried_statements": []}
    # GATE 1: append-only (baseline integrity — additions may interleave imports at top, so the check is:
    # every prior NON-IMPORT line present verbatim AS A WHOLE LINE and in order; imports may be added).
    # 2026-06-13 audit (BUG 1): this was a SUBSTRING match (`_a_text.find(l)`), so an IN-PLACE edit whose
    # old text is a prefix of the new line (`def A := True` → `def A := True ∧ True`) passed the
    # anti-laundering wall — a definition edit is exactly what this gate exists to reject. Whole-line,
    # in-order matching closes it (GATE 2's sorry-tolerant compile can't catch an edited def — it still
    # compiles). Soundness boundary: a silently-edited def could invalidate a previously-proven rung.
    _b_lines = [l for l in before.splitlines() if l.strip() and not l.strip().startswith("import ")]
    _a_lines = [l for l in after.splitlines() if l.strip() and not l.strip().startswith("import ")]
    _pos = 0
    for l in _b_lines:
        try:
            _pos = _a_lines.index(l, _pos) + 1   # whole-line, in order; not a substring
        except ValueError:
            theory_path.write_text(before, encoding="utf-8")   # REVERT — definition editing rejected
            return {"ok": False, "reverted": True,
                    "reason": f"append-only violated: prior line altered/removed: {l[:80]!r}"}
    # GATE 2: kernel compile, sorry-tolerant (the canonical v33 probe — same oracle the solver trusts)
    if compile_fn is None:
        from ztare.gates.v33_preflight_risk_detector import _compile_probe as compile_fn  # type: ignore
    from ztare.common.timeouts import timeout_s as _ts
    ok = compile_fn(after, lean_root, "TheoryConsolidation", _ts("cold_compile"))
    if ok is not True:
        theory_path.write_text(before, encoding="utf-8")
        return {"ok": False, "reverted": True, "reason": "extended theory file does not compile"}
    # extract the NEW sorried API statements → solver work items. "Is this decl OPEN?" is a KERNEL fact,
    # NOT a lexical grep (the operator's "fix once and for all"): the file just compiled, so ask the
    # elaborator which NEW decls carry `sorryAx` (`kernel_structure.sorried_names`). This CANNOT be fooled
    # by a `sorry` in a section comment — the 2026-06-13 bug that queued an already-proven `by simp` lemma
    # and burned ~25min. Lexical `has_sorry` (now nested-comment-aware) is only the FALLBACK when no live
    # REPL exists here. (Canonical decl parser throughout — no module re-rolls a Lean-source regex.)
    from ztare.leanmill.solver.statement_integrity import decl_blocks
    from ztare.leanmill.lean_source import strip_comments as _sc, has_sorry as _has_sorry, split_at_proof as _sap
    before_names = {n for n, _ in decl_blocks(before)}
    after_blocks = [(n, b) for n, b in decl_blocks(after) if n not in before_names]
    new_decls = [n for n, _ in after_blocks]
    from ztare.leanmill.solver.kernel_structure import sorried_names as _ksorried
    _kernel_open = _ksorried(after, lean_root, names=new_decls)   # set[name] | None (None ⇒ fall back)
    new_sorried = []
    for name, block in after_blocks:
        _clean = _sc(block)
        _open = (name in _kernel_open) if _kernel_open is not None else _has_sorry(_sap(_clean)[1])  # proof-body, binder-safe
        if _open:
            new_sorried.append(" ".join(_clean.split()))   # clean signature, no comment/proof cruft
    # SUPERSESSION REQUESTS (captured, not auto-applied): the agent may flag a wrong-shaped EXISTING
    # definition with `-- SUPERSEDE: <name>: <why>`. Editing is still forbidden this round (append-only
    # stands); the request is surfaced in the result/receipt and queued for a governed revision — the
    # rewrite-and-revalidate machinery is a trust-surface change shipped separately, but the agent's
    # revision signal is never silently dropped.
    supersede = [{"name": m.group(1).strip(), "why": m.group(2).strip()[:200]}
                 for m in re.finditer(r"--\s*SUPERSEDE:\s*([^:]+):\s*(.+)", after)]
    out = {"ok": True, "new_decls": new_decls, "sorried_statements": new_sorried}
    if supersede:
        out["supersession_requests"] = supersede
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
        if no_dag and dispatch is not None and _os.environ.get("ZTARE_LEANMILL_AGENT_REFINE_NOTES", "1") != "0":   # DEFAULT-ON 2026-06-12 (advisory notes, kernel gates downstream; =0 reverts)
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
    # ALSO persist the TARGET's OWN route_and_solve decomposition: a notes file may carry NO `## Lemmas` (just a
    # `## Target`, e.g. P1 n=1), so the agent's breakdown lives ONLY on result['target'] — which the per-lemma loop
    # above never sees. Without this the `.refined.md` drops the target's whole sub-DAG (the other half of the
    # self-evolving-loop amnesia). Mirrors the open-lemma rendering; deterministic (rendering the agent's output).
    _tgt = result.get("target") or {}
    if _tgt and not _tgt.get("solved"):
        _tdec = _tgt.get("decomposition") or {}
        _tsub = _tdec.get("lemmas") or []
        if _tsub:
            if not agent_md:
                agent_md = "## Open frontier — refined decomposition (attempt next)"
            _tag = " [kernel-audited]" if _tdec.get("audited") else ""
            agent_md += (f"\n\n### ⬜ {str(_tgt.get('nl', ''))[:120]}{_tag} — planner sub-decomposition (the TARGET):\n"
                         + "\n".join(f"- {str(s)[:220]}" for s in _tsub))
    # ── DEEP RUNGS (v3 RCA 2026-06-12): kernel-closed sub-lemmas from the WHOLE recursion tree. The
    #    per-lemma records above only see TOP-level outcomes (`solve_decomposition` keeps {name, outcome}
    #    of its DIRECT children), so a depth≥2 closure was INVISIBLE here — v3 closed 2 deep rungs while
    #    this file said "(none kernel-closed this run)" and the next run had to re-derive them. Governed
    #    facts (cert-ledger render), so it lives in the deterministic section. ──
    deep = result.get("deep_closures") or []
    if deep:
        det += ["", "## Kernel-closed sub-lemmas this run (deep rungs — citable):"]
        for d in deep:
            flag = " ⚠️ integrity-unverified (NOT auto-citable)" if d.get("integrity_unverified") else ""
            if d.get("fragile") and not flag:
                flag = " ⚠️ fragile (margin battery: kernel-true, weakened signals)"
            loc = f" ({d.get('closure_lean')})" if d.get("closure_lean") else ""
            det.append(f"- ✅ {d.get('target')} [sha:{d.get('goal_sha')}] {d.get('statement', '')}{flag}{loc}")
    refined = notes_path.with_suffix(".refined.md")
    refined.write_text("\n".join(det) + "\n\n" + agent_md + "\n", encoding="utf-8")
    return refined


def deep_closures_since(since_iso: str, *, ledger: "Optional[Path]" = None) -> "list[dict]":
    """Kernel-closed targets ratified at ANY recursion depth since `since_iso`, read from the durable
    closure-cert ledger — the single source of truth EVERY depth's `solve_adhoc` already appends to.
    WHY (v3 RCA 2026-06-12): `solve_decomposition` returns only {name, outcome} for its DIRECT children,
    so depth≥2 closures never reached the notes write-back — proven rungs were lost to the compounding
    loop (re-derived next run = the amnesia disease, paid in tokens). Returns
    [{target, goal_sha, statement, closure_lean, integrity_unverified}], deduped by goal identity;
    `statement` is extracted from the recompilable probe via the canonical decl parser."""
    if ledger is None:
        from ztare.leanmill.solver.solver_core import ADHOC_CLOSURE_CERTIFICATES as _L
        ledger = _L
    out: "list[dict]" = []
    seen: set = set()
    try:
        lines = Path(ledger).read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for ln in lines:
        try:
            c = json.loads(ln)
        except ValueError:
            continue
        if c.get("outcome") != "closed" or str(c.get("ts") or "") < since_iso:
            continue
        stmt = ""
        probe = c.get("recompilable_probe") or ""
        if probe:
            try:   # canonical decl parser (statement_integrity) — never a re-rolled regex
                from ztare.leanmill.solver.statement_integrity import decl_blocks
                blocks = dict(decl_blocks(probe))
                stmt = blocks.get(c.get("target")) or next(iter(blocks.values()), "")
            except Exception:  # noqa: BLE001 — best-effort render; the cert itself stays authoritative
                stmt = probe
            from ztare.leanmill.lean_source import signature_before_proof   # canonical binder-safe head extractor
            stmt = " ".join(signature_before_proof(stmt).split())[:300]
        key = c.get("goal_sha") or (c.get("target"), stmt)
        if key in seen:
            continue
        seen.add(key)
        out.append({"target": c.get("target"), "goal_sha": c.get("goal_sha"), "statement": stmt,
                    "closure_lean": c.get("closure_lean"),
                    "integrity_unverified": bool((c.get("governance") or {}).get("integrity_unverified")),
                    # margin-of-safety tier (differential re-verification battery): fragile = kernel-TRUE
                    # but weakened signals (decorative hypotheses etc.) — still citable, flagged honestly
                    "fragile": ((c.get("governance") or {}).get("margin_of_safety") or {})
                    .get("overall") == "fragile_advisory"})
    return out


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

    # --- compound_into_original_notes (#97): regenerate ## Lemmas from the planner's decomposition, PRESERVE the rest ---
    import os as _os, tempfile as _tf, shutil as _sh
    _td = _tf.mkdtemp(prefix="leanmill_compound_")
    np = Path(_td) / "seed.md"
    # ## Idea is BEFORE ## Lemmas; ## References is AFTER it — the order-robust case the prior split-on-Lemmas dropped.
    SEED = ("## Target\nFor all n, P n.\n## Idea\nUse induction.\n## Lemmas\n- human seed lemma\n"
            "## References\n- Foo 2020\n")
    decomp = {"target": {"decomposition": {"lemmas": ["base case P 0", "step P k -> P (k+1)"]}}, "lemmas": []}
    _prev = _os.environ.get("ZTARE_LEANMILL_COMPOUND_ORIGINAL")
    try:
        np.write_text(SEED, encoding="utf-8")
        _os.environ["ZTARE_LEANMILL_COMPOUND_ORIGINAL"] = "0"   # explicit =0 still reverts (the A/B baseline)
        ok("compound_explicit_off_noop",
           compound_into_original_notes(decomp, np) is None and np.read_text(encoding="utf-8") == SEED)
        _os.environ.pop("ZTARE_LEANMILL_COMPOUND_ORIGINAL", None)   # DEFAULT (unset) now COMPOUNDS (default-on)
        out = compound_into_original_notes(decomp, np)
        txt = np.read_text(encoding="utf-8")
        ok("compound_writes_and_returns_path", out == np)
        ok("compound_has_planner_lemmas", "- base case P 0" in txt and "- step P k -> P (k+1)" in txt)
        ok("compound_regenerates_old_lemma_body", "- human seed lemma" not in txt)  # ## Lemmas body is regenerated by design
        ok("compound_preserves_pre_lemmas_sections", "## Target" in txt and "Use induction." in txt)
        ok("compound_preserves_post_lemmas_section", "## References" in txt and "Foo 2020" in txt)  # the order-robust fix
        # idempotent: a SECOND compound on the already-compounded file must not STACK markers
        compound_into_original_notes(decomp, np)
        txt2 = np.read_text(encoding="utf-8")
        ok("compound_idempotent_single_marker", txt2.count("auto-compounded from the planner") == 1)
        ok("compound_idempotent_still_preserves", "## References" in txt2 and "Use induction." in txt2)
        np.write_text(SEED, encoding="utf-8")
        ok("compound_no_decomp_never_clobbers",
           compound_into_original_notes({"target": None, "lemmas": []}, np) is None
           and np.read_text(encoding="utf-8") == SEED)
        nf = Path(_td) / "notseed.md"; nf.write_text("just prose\n", encoding="utf-8")
        ok("compound_refuses_non_seed_file",
           compound_into_original_notes(decomp, nf) is None and nf.read_text(encoding="utf-8") == "just prose\n")

        # --- deep rungs (v3 RCA): cert-ledger → refined notes + accumulated auto-section in the ORIGINAL ---
        ledger = Path(_td) / "certs.jsonl"
        _c = {"ts": "2026-06-12T16:29:02+00:00", "target": "iso_lemma1", "outcome": "closed",
              "goal_sha": "abcd1234abcd1234", "recompilable_probe":
              "import Mathlib\n\ntheorem iso_lemma1 : 1 + 1 = 2 := by norm_num\n",
              "closure_lean": "ztare_proofs/closures/iso_lemma1.lean", "governance": {}}
        _unv = dict(_c, target="iso_lemma2", goal_sha="ffff0000ffff0000",
                    governance={"integrity_unverified": True}, recompilable_probe="")
        _old = dict(_c, ts="2026-06-11T00:00:00+00:00", goal_sha="0ld0000000000000")
        ledger.write_text("\n".join(json.dumps(x) for x in (_c, _unv, _old,
                          dict(_c, outcome="rejected_governance", goal_sha="rej0000000000000"))) + "\n",
                          encoding="utf-8")
        dc = deep_closures_since("2026-06-12T00:00:00+00:00", ledger=ledger)
        ok("deep_closures: closed-in-window only (old + rejected excluded)",
           {d["goal_sha"] for d in dc} == {"abcd1234abcd1234", "ffff0000ffff0000"})
        ok("deep_closures: statement via canonical decl parser (no proof tail)",
           any(d["statement"].startswith("theorem iso_lemma1 : 1 + 1 = 2") and ":= by" not in d["statement"]
               for d in dc))
        ok("deep_closures: integrity_unverified FLAGGED",
           any(d["integrity_unverified"] for d in dc if d["target"] == "iso_lemma2"))
        # refined render: verified rung cited, unverified marked not-citable
        r_deep = {"target_nl": "T", "summary": "s", "lemmas": [], "shelf": [], "deep_closures": dc}
        rp = write_refined_notes(r_deep, Path(_td) / "deep.md")
        rt = rp.read_text(encoding="utf-8")
        ok("refined: deep-rungs section rendered",
           "deep rungs" in rt and "iso_lemma1 [sha:abcd1234abcd1234]" in rt)
        ok("refined: unverified rung marked NOT auto-citable", "NOT auto-citable" in rt)
        # compound: only VERIFIED rungs reach the original; accumulates + dedupes by sha across runs
        np.write_text(SEED, encoding="utf-8")
        compound_into_original_notes(dict(decomp, deep_closures=dc), np)
        t1 = np.read_text(encoding="utf-8")
        ok("compound: verified rung in ORIGINAL notes; unverified excluded",
           "iso_lemma1 [sha:abcd1234abcd1234]" in t1 and "ffff0000ffff0000" not in t1)
        compound_into_original_notes(dict(decomp, deep_closures=dc), np)   # idempotent re-run
        t2 = np.read_text(encoding="utf-8")
        ok("compound: rungs accumulate WITHOUT duplication (sha-dedup)",
           t2.count("abcd1234abcd1234") == 1 and t2.count("proven-rungs:auto") >= 1
           and "## References" in t2)
        # rungs-only update (planner produced NO decomposition) must not clobber ## Lemmas
        compound_into_original_notes({"target": None, "lemmas": [], "deep_closures": dc}, np)
        t3 = np.read_text(encoding="utf-8")
        ok("compound: rungs-only update preserves ## Lemmas body",
           "- base case P 0" in t3 and t3.count("abcd1234abcd1234") == 1)

        # --- THEORY CONSOLIDATION (#123): append-only + compile gates, sorried-API extraction ---
        troot = Path(_td) / "lroot"; troot.mkdir()
        tfile = troot / "T.lean"
        tfile.write_text("import Mathlib\n\ndef GoodDef (n : Nat) : Prop := n = n\n", encoding="utf-8")
        ok("theory: parse_theory_file finds the section",
           parse_theory_file("## Target\nX.\n## Theory file\nZtareProofs/T.lean\n") == "ZtareProofs/T.lean")

        def disp_extend(prompt, *, repo=None, timeout=None):
            tfile.write_text(tfile.read_text(encoding="utf-8")
                             + "\ndef NewDef (n : Nat) : Prop := 0 < n\n"
                             + "theorem newdef_api (n : Nat) (h : NewDef n) : 0 < n := by sorry\n",
                             encoding="utf-8")
        r_ok = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot,
                                    dispatch=disp_extend, compile_fn=lambda *a: True)
        ok("theory: extension accepted; new decls + sorried API extracted",
           r_ok["ok"] and "NewDef" in r_ok["new_decls"]
           and any("newdef_api" in s for s in r_ok["sorried_statements"]))

        def disp_edit(prompt, *, repo=None, timeout=None):   # REWRITES an existing line — the launder
            tfile.write_text(tfile.read_text(encoding="utf-8")
                             .replace("def GoodDef (n : Nat) : Prop := n = n",
                                      "def GoodDef (n : Nat) : Prop := True"), encoding="utf-8")
        before_edit = tfile.read_text(encoding="utf-8")
        r_edit = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot,
                                      dispatch=disp_edit, compile_fn=lambda *a: True)
        ok("theory: definition EDIT rejected + file reverted (append-only integrity)",
           r_edit["ok"] is False and r_edit.get("reverted")
           and tfile.read_text(encoding="utf-8") == before_edit)

        def disp_broken(prompt, *, repo=None, timeout=None):
            tfile.write_text(tfile.read_text(encoding="utf-8") + "\ndef Broken : := :=\n", encoding="utf-8")
        r_bad = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot,
                                     dispatch=disp_broken, compile_fn=lambda *a: False)
        ok("theory: non-compiling extension reverted",
           r_bad["ok"] is False and "Broken" not in tfile.read_text(encoding="utf-8"))
        r_same = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot,
                                      dispatch=lambda p, **k: None, compile_fn=lambda *a: True)
        ok("theory: unchanged file ⇒ ok/unchanged (no spurious receipt work)",
           r_same["ok"] and r_same.get("unchanged"))

        def disp_supersede(prompt, *, repo=None, timeout=None):
            tfile.write_text(tfile.read_text(encoding="utf-8")
                             + "\n-- SUPERSEDE: GoodDef: wrong-shaped, API lemma unprovable\n"
                             + "def BetterDef (n : Nat) : Prop := 0 < n + 1\n", encoding="utf-8")
        r_sup = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot,
                                     dispatch=disp_supersede, compile_fn=lambda *a: True)
        ok("theory: SUPERSEDE request captured (queued, file NOT rewritten, additions accepted)",
           r_sup["ok"] and r_sup.get("supersession_requests", [{}])[0].get("name") == "GoodDef"
           and "def GoodDef (n : Nat) : Prop := n = n" in tfile.read_text(encoding="utf-8"))
    finally:
        if _prev is None:
            _os.environ.pop("ZTARE_LEANMILL_COMPOUND_ORIGINAL", None)
        else:
            _os.environ["ZTARE_LEANMILL_COMPOUND_ORIGINAL"] = _prev
        _sh.rmtree(_td, ignore_errors=True)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


def compound_into_original_notes(result: dict, notes_path: "Optional[Path]") -> "Optional[Path]":
    """COMPOUND the PLANNER's own generated decomposition back into the ORIGINAL notes (#97, operator vision:
    the agent adds the breakdown itself — "in the original file", not just .refined.md). Source = the
    `decomposition` sub-DAG `route_and_solve` already stashes in each attack record (the TARGET's, for a minimal
    seed, plus any per-lemma sub-DAGs) — NOT human-authored. Rewrites ONLY the `## Lemmas` BODY, PRESERVING every
    other section in place — the human `## Target` / `## Idea` above AND any section that follows `## Lemmas`
    (e.g. `## References`); only the auto-generated bullet list is regenerated. The next run's parser then attacks the
    agent's OWN breakdown → the compounding loop closes with no human in it. Deterministic render of the agent's
    output (not authoring), so no fake-closure risk. SOUND ⇒ **DEFAULT-ON** (`ZTARE_LEANMILL_COMPOUND_ORIGINAL`, `=0`
    reverts): a deterministic render of the agent's own decomposition has NO soundness surface, so leaving it off only
    threw away the agent's work between runs (the loop never compounded). No-op when the planner produced no decomposition (never clobbers the seed) or
    the file is not a parseable `## Target` seed."""
    import os as _os
    if _os.environ.get("ZTARE_LEANMILL_COMPOUND_ORIGINAL", "1") == "0" or notes_path is None:
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
    # Deep rungs (v3 RCA 2026-06-12): integrity-VERIFIED kernel closures from the whole recursion tree —
    # these must reach the ORIGINAL notes (the file the next run parses + threads as planner context), or
    # the next run re-derives them (the amnesia disease). Unverified ones are EXCLUDED — never teach the
    # agent to cite a rung whose statement integrity the organs could not check.
    rungs = [d for d in (result.get("deep_closures") or []) if not d.get("integrity_unverified")]
    if not gen and not rungs:
        return None   # nothing to compound; leave the seed untouched
    try:
        text = notes_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not re.search(r"(?m)^##\s*Target\s*$", text):
        return None   # not a parseable seed ⇒ refuse (never clobber an unexpected file)
    # ACCUMULATE the auto proven-rungs section across runs: lift the prior marker-delimited block out of the
    # text (so the ## Lemmas split below never mistakes it for human tail content), union its bullets with
    # this run's rungs by [sha:…] identity, and re-append fresh at the end. Idempotent by construction.
    _rung_lines: "list[str]" = []
    _rung_block = re.search(r"(?s)<!-- proven-rungs:auto -->\n?(.*?)<!-- /proven-rungs:auto -->\n?", text)
    if _rung_block:
        _rung_lines = [l for l in _rung_block.group(1).splitlines() if l.lstrip().startswith("- ")]
        text = text[:_rung_block.start()] + text[_rung_block.end():]
    _have_shas = {m.group(1) for l in _rung_lines for m in [re.search(r"\[sha:([0-9a-f]+)\]", l)] if m}
    for d in rungs:
        if d.get("goal_sha") and d["goal_sha"] in _have_shas:
            continue
        loc = f" ({d.get('closure_lean')})" if d.get("closure_lean") else ""
        _rung_lines.append(f"- ✅ {d.get('target')} [sha:{d.get('goal_sha')}] {d.get('statement', '')}{loc}")
    parts = re.split(r"(?m)^##\s*Lemmas\s*$", text, maxsplit=1)
    # strip any PRIOR auto-compound marker so re-runs don't STACK markers (it lives just above ## Lemmas ⇒ lands in head)
    head = re.sub(r"(?m)^<!-- ## Lemmas below: auto-compounded.*?-->[ \t]*\n?", "", parts[0]).rstrip()
    tail = ""   # PRESERVE any human section AFTER ## Lemmas (e.g. ## References, or a post-Lemmas ## Idea): only the
    if len(parts) > 1:   # old auto-generated bullet body is regenerated; the next `## ` heading onward is human content.
        nxt = re.search(r"(?m)^##\s+\S", parts[1])
        if nxt:
            tail = parts[1][nxt.start():].rstrip()
    marker = ("<!-- ## Lemmas below: auto-compounded from the planner's OWN decomposition (route_and_solve, #97). "
              "Reseed by editing ## Target / ## Idea above; this section is regenerated each run. -->")
    if gen:
        body = (head + "\n\n" + marker + "\n## Lemmas\n"
                + "\n".join(f"- {g}" for g in gen) + "\n")
        if tail:
            body += "\n" + tail + "\n"
    else:
        body = text.rstrip() + "\n"   # rungs-only update: NEVER regenerate ## Lemmas to empty (would clobber)
    if _rung_lines:
        body += ("\n<!-- proven-rungs:auto -->\n## Proven rungs (kernel-closed, auto — citable)\n"
                 + "\n".join(_rung_lines) + "\n<!-- /proven-rungs:auto -->\n")
    notes_path.write_text(body, encoding="utf-8")
    return notes_path


def regenerate_dashboard(repo_root, runner=None) -> "str | None":
    """#119 post-run hook: regenerate the ONE leanmill dashboard (scripts/public/control/leanmill/
    leanmill_dashboard.py) so every run ends with fresh artifacts — no more stale post-run reviews.
    Best-effort observability: bounded by the `dashboard_regen` factory budget (=0 disables), runs as a
    SUBPROCESS (src/ must not import scripts/ — the standing boundary), fail-quiet-loud (one line,
    never affects the run result). Returns the dashboard path on success, None otherwise."""
    from pathlib import Path as _P
    from ztare.common.timeouts import timeout_s as _ts_dash
    budget = _ts_dash("dashboard_regen")
    if not budget:
        return None
    script = _P(repo_root) / "scripts" / "public" / "control" / "leanmill" / "leanmill_dashboard.py"
    if not script.exists():
        print(f"[notes] dashboard regen skipped: {script} absent", flush=True)
        return None
    import subprocess as _sp
    import sys as _sys
    run = runner or _sp.run
    try:
        proc = run([_sys.executable, str(script)], cwd=str(repo_root), timeout=budget,
                   capture_output=True, text=True)
        if getattr(proc, "returncode", 1) == 0:
            tail = (getattr(proc, "stdout", "") or "").strip().splitlines()
            print(f"[notes] dashboard regenerated{(': ' + tail[-1]) if tail else ''}", flush=True)
            return str(script)
        print(f"[notes] dashboard regen FAILED rc={getattr(proc, 'returncode', '?')}: "
              f"{(getattr(proc, 'stderr', '') or '')[-200:]}", flush=True)
    except Exception as _e:  # noqa: BLE001 — observability must never mask the run result
        print(f"[notes] dashboard regen error: {_e!r}"[:200], flush=True)
    return None


def main(argv: "Optional[list[str]]" = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        return _self_test()
    if not argv:
        print("usage: python -m ztare.leanmill.solver.autoformalize_notes <notes.md> | --selftest")
        return 2
    from ztare.leanmill.preflight_carriers import assert_carriers_live
    assert_carriers_live()
    # #116 INTERNAL STANDARDS (isotope-dilution discipline): a known-positive must CLOSE + a canned cheat must
    # be REJECTED through the same pipeline BEFORE the run spends its wallclock — fail-closed on a dead
    # instrument; the certificate is stamped into the run artifact so every closure is traceable to a
    # demonstrably-live, demonstrably-refusing instrument. ZTARE_LEANMILL_RUN_STANDARDS=0 reverts.
    from ztare.leanmill.run_standards import run_instrument_standards
    _std = run_instrument_standards(LEAN_ROOT_DEFAULT)
    print(f"[notes] instrument standards: {_std.get('detail', 'skipped (=0)')}", flush=True)
    if not _std.get("ok"):
        print("[notes] ABORT — instrument standards FAILED (fail-closed: fix the instrument, do not burn the run)")
        return 3
    notes_path = Path(argv[0])
    # RUN ATTRIBUTION: tag this run's attempts-DB rows + forecast ledger so the compounder/forecast-router can
    # SLICE by run — the DB showed run_tag=NULL for notes runs (#92 said it should feed the substrate, but the
    # notes entry never set the env), making a run unattributable. setdefault RESPECTS an explicit A/B arm
    # (ZTARE_SOLVER_RUN_TAG=<arm>); otherwise defaults to the notes stem + a per-run stamp.
    import os as _os
    from datetime import datetime as _dt, timezone as _tz
    _os.environ.setdefault("ZTARE_SOLVER_RUN_TAG", f"notes_{notes_path.stem}_{_dt.now().strftime('%m%dT%H%M')}")
    print(f"[notes] run_tag = {_os.environ['ZTARE_SOLVER_RUN_TAG']}", flush=True)
    _since = _dt.now(_tz.utc).isoformat()   # cert-ledger watermark (same format solve_adhoc stamps `ts` with)
    _notes_text = notes_path.read_text(encoding="utf-8")
    # PHASE 0 — THEORY CONSOLIDATION (#123, theory-first campaigns): when the notes declare a campaign
    # theory file, the agent EXTENDS it (defs + sorried API statements — the substrate Mathlib lacks;
    # serves the BUILDS-not-lookup invariant) behind the append-only + compile gates; each new sorried
    # API statement becomes a first-class lemma work item; the file's content rides the notes so every
    # downstream formalize/solve sees the campaign substrate. Receipt → the work-items ledger.
    _theory_rel = parse_theory_file(_notes_text)
    if _theory_rel:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch as _dd0
        _tc = theory_consolidation(_notes_text, _theory_rel, lean_root=LEAN_ROOT_DEFAULT, dispatch=_dd0)
        print(f"[notes] theory consolidation: ok={_tc.get('ok')} new_decls={_tc.get('new_decls', [])} "
              f"sorried={len(_tc.get('sorried_statements', []))} {_tc.get('reason', '')}", flush=True)
        for _sr in _tc.get("supersession_requests", []):
            print(f"[notes] SUPERSESSION REQUESTED (queued for governed revision): "
                  f"{_sr['name']} — {_sr['why']}", flush=True)
        try:   # typed receipt — machine-consumed first (ledger), dashboard-rendered second
            from ztare.leanmill.contracts.work_items import WorkItem, WorkReceipt
            WorkReceipt(
                item=WorkItem(kind="theory_extension", statement=_theory_rel,
                              residual_class="library_gap",
                              consumer_check="campaign lemmas must cite these decls (stamped on use)",
                              campaign=_os.environ.get("ZTARE_SOLVER_RUN_TAG", "")),
                verdict=("completed" if _tc.get("ok") and not _tc.get("unchanged") else
                         "gap" if _tc.get("ok") else "rejected"),
                formal_leg={k: _tc.get(k) for k in ("ok", "reverted", "reason", "new_decls",
                                                     "supersession_requests") if k in _tc},
                ts=_since).append_to_ledger(REPO)
        except Exception as _e:  # noqa: BLE001 — receipt write never blocks the run
            print(f"[notes] work-receipt write failed: {repr(_e)[:100]}", flush=True)
        if _tc.get("ok"):
            _tp = (LEAN_ROOT_DEFAULT / _theory_rel)
            # WARM-ENV REGISTER (2026-06-14): the verify seam amortizes this heavy theory's decls into a warm
            # REPL env (elaborated ONCE, re-opened on mtime change) instead of re-inlining + re-elaborating them
            # PER probe — the v7 verify-starvation fix (592-1016s timeouts → ~0.04s/probe). Soundness unchanged:
            # the warm verify still runs the #print-axioms audit against that env.
            if _tp.exists():
                try:
                    from ztare.formal.repl_compile import set_campaign_substrate
                    set_campaign_substrate(str(_tp.resolve()))
                    print(f"[notes] campaign warm-env substrate registered: {_tp}", flush=True)
                except Exception as _e:  # noqa: BLE001 — registration is best-effort; verify falls back to inline
                    print(f"[notes] warm-env register skipped: {repr(_e)[:100]}", flush=True)
            _theory_src = _tp.read_text(encoding="utf-8") if _tp.exists() else ""
            if _theory_src.strip():   # the substrate rides the notes (formal scaffolding channel, #88)
                _notes_text += ("\n\n## Theory (campaign substrate — cite, do not re-derive)\n```lean\n"
                                + _theory_src + "\n```\n")
            for _s in reversed(_tc.get("sorried_statements", [])):   # API lemmas FIRST (foundational)
                _notes_text = re.sub(r"(?m)^(##\s*Lemmas\s*)$", r"\1\n- " + _s.replace("\\", "\\\\"),
                                     _notes_text, count=1)
    res = autoformalize_from_notes(_notes_text, notes_path=notes_path)  # notes_path ⇒ incremental write-back (timeout-safe)
    res["instrument_standards"] = _std   # traceability: this run's closures carry their instrument certificate
    # v3 RCA: surface kernel closures from the WHOLE recursion tree (the cert ledger), not just the
    # top-level lemma outcomes — depth≥2 rungs were silently lost to the compounding loop.
    res["deep_closures"] = deep_closures_since(_since)
    if res["deep_closures"]:
        print(f"[notes] deep rungs kernel-closed this run: "
              + ", ".join(str(d.get('target')) for d in res['deep_closures']), flush=True)
    # TRUST-CONSERVATION EPILOGUE (v3 RCA): the layers must AGREE — every ratified DB win has a verified,
    # recompilable cert. Read-only, seconds, fail-LOUD (the v3 disease was exactly a silent disagreement
    # between these layers that no layer-local selftest could see).
    try:
        from ztare.leanmill.run_standards import trust_conservation_audit
        _tc = trust_conservation_audit(_since, run_tag=_os.environ.get("ZTARE_SOLVER_RUN_TAG", ""))
        res["trust_conservation"] = _tc
        if _tc.get("ok"):
            print(f"[notes] trust-conservation: OK {_tc.get('counts')}", flush=True)
        else:
            print("[notes] *** TRUST-CONSERVATION VIOLATION ***", flush=True)
            for _v in _tc.get("violations", []):
                print(f"[notes]   {_v}", flush=True)
    except Exception as _e:  # noqa: BLE001 — the audit must never mask the run result itself
        res["trust_conservation"] = {"ok": None, "error": repr(_e)[:120]}
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
    regenerate_dashboard(REPO)   # #119: every run ends with fresh dashboard artifacts (best-effort)
    return 0


if __name__ == "__main__":
    sys.exit(main())
