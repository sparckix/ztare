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


def parse_domain(text: str) -> "Optional[str]":
    """Parse the optional `## Domain` line → the campaign-class label (e.g. `math`, `formalization-nonmath`) used
    by the factory time-to-closure read model to segment avg-time-to-closure by domain. First non-blank line of
    the section; None if absent (the caller falls back to ZTARE_SOLVER_DOMAIN, then 'unspecified')."""
    m = re.search(r"(?ms)^##\s*Domain\s*\n(.+?)(?=^##|\Z)", text)
    if not m:
        return None
    for ln in m.group(1).splitlines():
        if ln.strip():
            return ln.strip()
    return None


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


def _insert_lemmas_section(notes_text: str, bullets: "list[str]") -> str:
    """Splice `- <bullet>` items at the TOP of the `## Lemmas` section (foundational-first), creating the
    section if it is ABSENT. The ONE canonical notes-`## Lemmas` editor — callers must NOT re-roll
    `re.sub`/`re.search` on the heading (RCA 2026-06-18: a theory-first blueprint with no `## Lemmas` anchor
    silently DROPPED the agent's sorried API work-items, so the built theory was never proven). Line-based,
    no scattered regex; the heading test mirrors `parse_notes` (`##` then `Lemmas`, flexible spacing)."""
    if not bullets:
        return notes_text
    new = [f"- {b}" for b in bullets]
    lines = notes_text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("##") and s[2:].strip() == "Lemmas":      # the `## Lemmas` heading line
            return "\n".join(lines[:i + 1] + new + lines[i + 1:]) + "\n"
    return notes_text.rstrip() + "\n\n## Lemmas\n" + "\n".join(new) + "\n"   # absent → append the section


def _default_attack(nl: str, *, lean_root: Path, timeout_s: int, notes: "str | None" = None,
                    shelf_prelude: str = "") -> dict:
    """Real apparatus: one NL line → faithfulness firewall → governed solve → compact per-piece record.
    `notes` (the blueprint) threads into the recursive planner when the line does NOT close directly.
    `solved` is True ONLY when the governed outcome is `closed`. (`autoformalize_and_solve` puts the per-
    result outcome string in `solved`, so `exact_gap` / `open` are TRUTHY strings — taking `bool(outcome)`
    would mark an unproven gap as solved. That false-positive is fixed here at the source.)"""
    from ztare.leanmill.solver.autoformalize import autoformalize_and_solve
    from ztare.leanmill.contracts.kernel import AttackRecord   # #49: typed record — `solved` is a BOOL, decided
    r = autoformalize_and_solve(nl, sandbox=lean_root, timeout_s=timeout_s, notes=notes,
                                shelf_prelude=shelf_prelude)   # ONCE (outcome=="closed")
    # `.model_dump()` re-emits the exact legacy keys (nl/lean_statement/faithful/outcome/solved + the firewall
    # verdict reason/checks + the planner sub-DAG), so the notes loop + write-back are unchanged — but the
    # gap-as-solved false positive (`bool("exact_gap")` ⇒ True) is now impossible by construction.
    return AttackRecord.from_firewall_result(r, nl=nl).model_dump()


def _banked_lemma_reuse(bullet: str, lean_root) -> "Optional[str]":
    """BANKED-DECL REUSE (2026-06-25, operator "don't re-formalize, reuse"): if a lemma BULLET's intended decl
    name (`**(name)**`, the campaign naming convention) is ALREADY a PROVEN (sorry-free) decl in the registered
    campaign substrate, return its signature — the lemma is DONE, so re-formalizing+re-attacking it is pure waste
    AND the vocabulary-drift vector that orphans the shelf (the AMM RCA: a fresh formalization in a divergent form
    — `NoHistoryRoundTripArbitrage` predicate vs the unfolded conjunction — mismatches the banked one and the
    target then false-rejects). Returns the banked signature (citable shelf entry) or None.

    SOUND: this only SKIPS work + shelves an ALREADY-kernel-proven decl; it mints no closure. The target's own
    closure is still kernel-gated downstream, so a stale/mismatched blueprint can at worst leave the target as an
    honest gap — never a false closure.

    NO BRITTLE REGEX (operator): the decl names come from the canonical Lean parser (`decl_blocks` +
    `first_theorem_name`/`has_sorry` over the substrate), NOT a regex guess at the bullet. The bullet→decl link is
    the campaign `**(name)**` convention, matched with a plain substring test `f"({name})" in bullet` against the
    REAL banked names — deterministic, and it can only match a name that actually exists banked + sorry-free."""
    try:
        from ztare.formal.repl_compile import get_campaign_substrate
        cs = get_campaign_substrate()
        if not cs:
            return None
        src = Path(cs).read_text(encoding="utf-8", errors="replace")
        from ztare.leanmill.solver.statement_integrity import decl_blocks
        from ztare.leanmill.lean_source import signature_before_proof, first_theorem_name, has_sorry
        b = bullet or ""
        for n, blk in decl_blocks(src):
            if has_sorry(blk):
                continue
            short = first_theorem_name(blk) or str(n).split(".")[-1]
            # the bullet NAMES this banked, sorry-free decl via the `**(name)**` convention (substring, not regex)
            if short and (f"({short})" in b):
                return " ".join((signature_before_proof(blk) or "").split())
        return None
    except Exception:  # noqa: BLE001 — reuse is an optimization; any failure ⇒ fall through to the normal attack
        return None


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
    # PHASE B (opt-in): multi-node lemma partitioning over the shared work bus (work_queue). Default-off
    # ⇒ this block is inert and the loop is byte-identical to single-node. When on, each node leases a
    # lemma before attacking it and skips lemmas a peer owns — peers' proofs converge via the fact-log
    # merge (state_convergence), so a skip is never lossy. Safety is already guaranteed by that merge;
    # this only removes the redundant re-proving. See solver/campaign_coordination.py.
    from ztare.leanmill.solver import campaign_coordination as _coord
    _dist = _coord.distributed_enabled()
    _campaign_id = _os_w.environ.get("ZTARE_SOLVER_RUN_TAG") or "campaign"
    if _dist:
        log(f"[notes] DISTRIBUTED lemma mode ON (node={_coord.node()}, campaign={_campaign_id!r}) — "
            f"lemmas leased via the work bus; peers' results converge via the fact-log merge")
    out["distributed"] = _dist
    out["wall_deferred"] = []
    # CAMPAIGN-START P0 FORECAST (2026-06-25): before spending the wall, PREDICT expected yield + time-to-closure
    # from the DOMAIN's historical P0 (phase_timing read-models) via the Brier-calibrated forecast router — an
    # admissibility/budget signal AND a prediction PRE-REGISTERED to a ledger, scored ex-post against the actual
    # (the self-learning loop; forecast_router.reweight recalibrates). v1 uses the domain close-rate as a flat
    # per-lemma prior (full per-candidate price() is a refinement). Best-effort; never blocks the campaign.
    try:
        from ztare.leanmill.solver.forecast_router import forecast_campaign_p0, domain_p0_history
        _dom = (parse_domain(notes_text) or _os_w.environ.get("ZTARE_SOLVER_DOMAIN", "") or "unspecified").strip()
        _hist = domain_p0_history(_dom)
        _cr = _hist.get("close_rate")
        _p = [(_cr if _cr is not None else 0.5)] * max(1, len(lemmas))
        _fc = forecast_campaign_p0(_p, domain=_dom, domain_mean_ttc_s=_hist.get("mean_ttc_s"),
                                   domain_mean_cost_s=_hist.get("mean_cost_s"))
        out["p0_forecast"] = _fc
        log(f"[notes] P0 FORECAST (domain={_dom!r}, {_hist.get('n_campaigns', 0)} prior campaigns): "
            f"expected yield {_fc['expected_yield']}/{_fc['n_candidates']}"
            + (f" · ~{_fc['expected_time_to_closure_s']}s to close" if _fc.get('expected_time_to_closure_s')
               else " · no time-history yet (cold start)")
            + (f" · hardest lemma #{(_fc['hardest_lemma_index'] or 0) + 1}"
               if _fc.get('hardest_lemma_index') is not None else ""))
        try:                                  # PRE-REGISTER the prediction (scored ex-post — the learning loop)
            import json as _j0
            _led = LEAN_ROOT_DEFAULT.parent / "analytics" / "public" / "queries" / "campaign_p0_forecasts.jsonl"
            _led.parent.mkdir(parents=True, exist_ok=True)
            with _led.open("a", encoding="utf-8") as _f0:
                _f0.write(_j0.dumps({"run_tag": _campaign_id, "ts": out["run_started"], **_fc}) + "\n")
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001 — the forecast is advisory; never block the campaign
        pass
    for i, lem in enumerate(lemmas):
        if _wall_exceeded():
            log(f"[notes] *** CAMPAIGN WALL reached — deferring lemma {i + 1}/{len(lemmas)} and the rest "
                f"(earned rungs already written back; not a failure) ***")
            out["wall_deferred"] = [str(x) for x in lemmas[i:]]
            break
        if _dist:
            try:
                _owned = _coord.claim_lemma(_campaign_id, str(lem), lease_s=2 * lemma_timeout_s)
            except Exception:  # noqa: BLE001 — queue unavailable ⇒ prove it (the merge dedups redundant work)
                _owned = True
            if not _owned:
                log(f"[notes] lemma {i + 1}/{len(lemmas)} owned by another node — skipping (converges via merge)")
                continue
        log(f"[notes] lemma {i + 1}/{len(lemmas)}: {lem!r}")
        # (b) BANKED-DECL REUSE (2026-06-25): if this lemma's intended name is ALREADY a sorry-free decl in the
        # registered substrate, it is DONE — skip the re-formalize+attack (the waste + vocab-drift vector the
        # operator flagged) and shelf the banked signature so the target can cite it. Default-on; =0 reverts.
        _reuse = None
        if _os_w.environ.get("ZTARE_LEANMILL_REUSE_BANKED_LEMMAS", "1") != "0":
            _reuse = _banked_lemma_reuse(lem, lean_root)
        if _reuse:
            log(f"  -> REUSED from bank (already proven in substrate; skipped re-formalize+attack): {_reuse[:90]}")
            out["lemmas"].append({"solved": "reused_from_bank", "lean_statement": _reuse,
                                  "outcome": "reused_from_bank", "faithful": True})
            out["shelf"].append(_reuse)
            if _dist:
                try:
                    _coord.complete_lemma(_campaign_id, str(lem), solved=True)
                except Exception:  # noqa: BLE001
                    pass
            continue
        # the WHOLE blueprint is the planner context for each lemma (the surrounding lemmas are scaffold)
        rec = attack_fn(lem, lean_root=lean_root, timeout_s=lemma_timeout_s, notes=notes_text)
        out["lemmas"].append(rec)
        if rec.get("solved"):
            out["shelf"].append(rec.get("lean_statement") or "")
        if _dist:
            try:                                  # done → terminal; unsolved → released for a peer to retry
                _coord.complete_lemma(_campaign_id, str(lem), solved=bool(rec.get("solved")))
            except Exception:  # noqa: BLE001 — coordination is best-effort, never breaks the solve
                pass
        log(f"  -> faithful={rec.get('faithful')} outcome={rec.get('outcome')} solved={rec.get('solved')}"
            # OBSERVABILITY (2026-06-24): show the reason on ANY non-closure, not only when faithful≠True — a
            # firewall reject with faithful=True (e.g. a def-shell / triviality verdict) was previously SILENT, so
            # a gate false-positive hid across a whole campaign instead of surfacing on the first lemma.
            + (f" | reason={str(rec.get('faithfulness_reason'))[:240]}"
               if (not rec.get('solved') and rec.get('faithfulness_reason')) else ""))
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

    # SELF-CORRECTION (supersession-acting, 2026-06-23): if lemmas remain OPEN and a lemma was kernel-CONFIRMED
    # FALSE (a `-- STATEMENT-FALSE:` marker survives in this run's scratch), a DEFINITION it cites is too WEAK.
    # Run ONE governed def-revision round — the agent STRENGTHENS the implicated def, GATED so only a kernel-
    # proven strengthening passes (never a laundering) — then re-attack the open lemmas with the strengthened
    # theory. Bounded (one round → can't loop), default-on (sound: the gate + kernel are the boundary), wall-
    # respecting, fail-safe (never breaks the campaign). ZTARE_LEANMILL_SELF_CORRECT_DEFS=0 reverts.
    _theory_rel_sc = parse_theory_file(notes_text)
    if (_os_w.environ.get("ZTARE_LEANMILL_SELF_CORRECT_DEFS", "1") != "0" and _theory_rel_sc
            and not _wall_exceeded()):
        _open_sc = [i for i, l in enumerate(out["lemmas"]) if not l.get("solved")]
        _marker = ""
        if _open_sc:
            try:
                from ztare.leanmill.solver.agentic_leaf import (scan_probes_for_statement_false,
                                                                probe_dir as _pdir_sc, default_dispatch as _dd_sc)
                _marker = scan_probes_for_statement_false(_pdir_sc(lean_root))
            except Exception:  # noqa: BLE001
                _marker = ""
        if _open_sc and _marker:
            log(f"[notes] SELF-CORRECT: a lemma was kernel-confirmed FALSE (marker: {_marker[:80]!r}) → governed "
                f"def-revision (strengthen the too-weak def; gated — only a proven strengthening passes)")
            try:
                _rev = governed_def_revision(_theory_rel_sc, lean_root=lean_root, dispatch=_dd_sc,
                                             false_lemma=str(lemmas[_open_sc[0]]), counterexample=_marker)
            except Exception as _e:  # noqa: BLE001 — self-correction is best-effort; never break the campaign
                _rev = {"ok": False, "reason": f"revision error: {repr(_e)[:120]}"}
            out["def_revision"] = _rev
            log(f"[notes] def-revision: ok={_rev.get('ok')} revised={_rev.get('revised_def')} — "
                f"{str(_rev.get('reason',''))[:170]}")
            if _rev.get("ok") and not _wall_exceeded():
                try:   # the theory file changed → re-register the warm-env substrate before re-attacking
                    from ztare.formal.repl_compile import set_campaign_substrate
                    _tp_sc = lean_root / _theory_rel_sc
                    if _tp_sc.exists():
                        set_campaign_substrate(str(_tp_sc.resolve()))
                except Exception:  # noqa: BLE001
                    pass
                for i in _open_sc:
                    if _wall_exceeded():
                        break
                    rec_sc = attack_fn(lemmas[i], lean_root=lean_root, timeout_s=lemma_timeout_s, notes=notes_text)
                    if rec_sc.get("solved"):
                        out["lemmas"][i] = rec_sc
                        out["shelf"].append(rec_sc.get("lean_statement") or "")
                        log(f"[notes] *** SELF-CORRECT CLOSED lemma {i + 1}/{len(lemmas)} after strengthening "
                            f"`{_rev.get('revised_def')}` ***")

    # the TARGET gets the blueprint PLUS the proven shelf — the planner sees which lemmas are already citable
    target_notes = notes_text
    if out["shelf"]:
        target_notes = (notes_text.rstrip() + "\n\n## Proven lemmas (citable):\n"
                        + "\n".join(f"- {s}" for s in out["shelf"] if s))
    # COMPOSITION FIX (2026-06-23): put the proven shelf lemmas IN COMPILE SCOPE for the target solve, so the
    # agent can CITE them by name (a true dependency graph) instead of re-deriving them inline — the dead-code
    # gap on FTAP. Before this, "Proven lemmas (citable)" was text-only; the standalone target probe never had
    # the names in scope, so inlining was the agent's ONLY compiling option. Name-filtered to THIS run (a
    # concurrent campaign shares the cert ledger).
    target_shelf_prelude = ""
    if out["shelf"]:
        try:
            target_shelf_prelude = _run_shelf_prelude(out, out.get("run_started", ""))
        except Exception:  # noqa: BLE001 — composition is additive; never break the target attack
            target_shelf_prelude = ""
    if target and _wall_exceeded():
        log("[notes] *** CAMPAIGN WALL reached — deferring the TARGET attack (proven rungs are written "
            "back; the target stays HONESTLY OPEN, never a fake closure) ***")
        out["wall_deferred"].append(str(target))
        out["target"] = {"deferred": "campaign_wall", "solved": False}
    else:
        log(f"[notes] TARGET: {target!r}"
            + (f" (shelf in scope: {target_shelf_prelude.count('theorem ') + target_shelf_prelude.count('lemma ')} proven lemmas citable)"
               if target_shelf_prelude.strip() else ""))
        out["target"] = (attack_fn(target, lean_root=lean_root, timeout_s=target_timeout_s, notes=target_notes,
                                   shelf_prelude=target_shelf_prelude)
                         if target else None)
    if out["target"]:
        t = out["target"]
        log(f"  -> faithful={t.get('faithful')} outcome={t.get('outcome')} solved={t.get('solved')}"
            # OBSERVABILITY (2026-06-24): reason on ANY non-closure (see the per-lemma log above).
            + (f" | reason={str(t.get('faithfulness_reason'))[:240]}"
               if (not t.get('solved') and t.get('faithfulness_reason')) else ""))

    # FINAL-TARGET PERSISTENCE AUDIT (RCA 2026-06-25, fix #3): the per-rung bank guard already audits the target
    # in the persisted env, but make the campaign DOUBLY honest — re-`#print axioms` the target's banked decl
    # against the FULL theory file. A `sorryAx` here (the assembled proof bound to a still-sorried sibling in the
    # persistence world, which the probe-world audit can miss — the two-verify-worlds class) DOWNGRADES
    # "closed" → an honest gap, loudly. Never a false-clean. Backstops #1 (supersession) + #2 (bank guard).
    _theory_rel_final = parse_theory_file(notes_text)
    if (out.get("target") or {}).get("solved") and _theory_rel_final:
        try:
            from ztare.leanmill.solver.family_lemma_library import _default_axiom_audit, decl_names as _dn
            _tname = str((out["target"].get("target_theorem_name") or "")).strip()
            _tp = (lean_root / _theory_rel_final)
            if _tname and _tp.exists():
                _names = _dn(_tp.read_text(encoding="utf-8"))
                _banked = _tname if _tname in _names else next((n for n in _names if n.startswith(_tname + "__")), "")
                if _banked:
                    _clean, _areason = _default_axiom_audit(str(_tp), str(LEAN_ROOT_DEFAULT), _banked)
                    if not _clean:
                        log(f"[notes] *** TARGET AXIOM-TAINT in the persisted theory ({_areason}) — DOWNGRADING "
                            f"'closed' → HONEST GAP (the assembled proof bound to a sorried sibling, not the "
                            f"proof) — never a false-clean ***")
                        out["target"]["solved"] = False
                        out["target"]["outcome"] = "axiom_taint_gap"
                        out["target"]["faithfulness_reason"] = f"persisted-theory {_areason}"
                    elif "unavailable" not in _areason:
                        # P0 SINGLE-DOOR (2026-06-30): the honest persisted-world axioms are computed HERE, at
                        # close, in the warm env. STAMP them (+ this-run banked/reused counts) in a sidecar beside
                        # the closure so promote_campaign_artifact READS them — instead of re-deriving P0 from the
                        # cold probe-world closure, which times out (→ `axioms ?`) and reports stub axioms, and
                        # whose log-regex misses intra-run banking (→ `reuse 0`). Fixes that recurring P0-at-promote
                        # class at the root: compute once where the data is honest, never re-derive on a cold box.
                        try:
                            import json as _json_p0
                            _banked_n = sum(1 for _l in out["lemmas"]
                                            if _l.get("solved") and _l.get("outcome") != "reused_from_bank")
                            _reused_n = sum(1 for _l in out["lemmas"] if _l.get("outcome") == "reused_from_bank")
                            _cdir_p0 = LEAN_ROOT_DEFAULT / ".solver_scratch" / "closures"
                            _cdir_p0.mkdir(parents=True, exist_ok=True)
                            (_cdir_p0 / f"{_tname}.p0.json").write_text(_json_p0.dumps({
                                "axioms": _areason,               # persisted-world #print axioms (warm env)
                                "composite_decl": _banked,
                                "theory_file": _theory_rel_final,
                                "banked_this_run": _banked_n,
                                "reused_from_bank": _reused_n,
                            }, indent=2), encoding="utf-8")
                            log(f"[notes] P0 stamped: closures/{_tname}.p0.json "
                                f"(axioms={_areason} · {_banked_n} banked/{_reused_n} reused this run)")
                        except Exception:  # noqa: BLE001 — telemetry; never blocks a verified closure
                            pass
        except Exception:  # noqa: BLE001 — defense-in-depth backstop; never break the run
            pass

    # SUBSTRATE HYGIENE (2026-07-01): sweep DEAD sorried orphans — sorried decls nothing else references, the
    # scaffolding a campaign leaves when a proven sibling supersedes an abstract stub (VCG's general witness vs
    # its concrete `_closed`). Keeps the warm env + any filed artifact sorry-free (a dead `sorry` reads as
    # unfinished + trips the promote publish guard). Recompile-verify + REVERT: a removal that breaks the env is
    # rolled back (the reference scan is textual, so this is the safety net). Best-effort; ZTARE_LEANMILL_SWEEP_ORPHANS=0 off.
    if _theory_rel_final and _os_w.environ.get("ZTARE_LEANMILL_SWEEP_ORPHANS", "1") != "0":
        try:
            from ztare.leanmill.solver.family_lemma_library import strip_dead_sorried_orphans
            from ztare.formal.repl_compile import campaign_file_env
            _tp_sw = lean_root / _theory_rel_final
            if _tp_sw.exists():
                _orig = _tp_sw.read_text(encoding="utf-8")
                _swept, _removed = strip_dead_sorried_orphans(_orig)
                if _removed:
                    _tp_sw.write_text(_swept, encoding="utf-8")
                    if campaign_file_env(str(_tp_sw), str(LEAN_ROOT_DEFAULT)) is None:
                        _tp_sw.write_text(_orig, encoding="utf-8")   # revert — removal broke the env
                        log(f"[notes] orphan-sweep REVERTED (removal broke the env); kept {_removed}")
                    else:
                        log(f"[notes] orphan-sweep: removed {len(_removed)} dead sorried orphan(s) {_removed} "
                            f"(nothing cited them; env still compiles)")
        except Exception:  # noqa: BLE001 — hygiene is best-effort; never blocks the run
            pass

    n_ok = sum(1 for l in out["lemmas"] if l.get("solved"))
    target_closed = bool((out["target"] or {}).get("solved"))
    out["summary"] = (f"{n_ok}/{len(lemmas)} lemmas formalized+closed; shelf={len(out['shelf'])}; "
                      f"target {'closed' if target_closed else 'open'}")
    # FINAL deterministic write-back — the COMPLETE gap ledger. The incremental writes above are kill-safety
    # snapshots taken BEFORE the target attack + wall-deferral were known, so they can't carry the TARGET gap
    # or the `wall_deferred` rungs (the 5 never-attempted lemmas a campaign-wall run leaves). This last write
    # guarantees EVERY caller (not just main(), which later UPGRADES it with agent synthesis) persists the full
    # honest gap record. No agent dispatch ⇒ free; main()'s later write with `dispatch` only enriches the
    # open-frontier decomposition. Best-effort: a write error never changes the run result.
    if notes_path is not None:
        try:
            out["deep_closures"] = deep_closures_since(out["run_started"])
            write_refined_notes(out, notes_path)
        except Exception:  # noqa: BLE001
            pass
    return out


# Prompt lives in the canonical registry (prompts.py); local name preserved for the call site.
from ztare.leanmill.solver.prompts import THEORY_PROMPT as _THEORY_PROMPT


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
    # THEORY-IDENTITY GUARD (2026-06-25 AMM RCA): the vocab-swap that orphaned a proven theory
    # (`ConstantProductPool`→`PoolState`) required the substrate to be RESET first — then a fresh genAI
    # consolidation re-formalized the prose in a NEW vocabulary, and the old proofs (keyed on the old vocab)
    # no longer matched (the α-cache is binder-axis only, not def-vocab; see proof_cache). The append-only
    # gate below can only block EDITS, never a rebuild-from-empty. So: if this substrate has prior BANKED
    # (proven) facts but the file is now empty/trivial, it was reset — REFUSE to silently re-formalize
    # (which would orphan the proven theory in a new vocab). Fail LOUD so the operator recovers (rederive /
    # restore) instead of compounding the loss. Default-on; ZTARE_LEANMILL_THEORY_IDENTITY_GUARD=0 reverts.
    import os as _os_ti
    if _os_ti.environ.get("ZTARE_LEANMILL_THEORY_IDENTITY_GUARD", "1") != "0":
        try:
            from ztare.leanmill.solver.family_lemma_library import read_bank_events as _rbe
            _prior = [e for e in _rbe() if e.get("substrate") == theory_path.name
                      and (e.get("decl_text") or "").strip()]
        except Exception:  # noqa: BLE001 — guard is best-effort; a lookup failure never blocks the run
            _prior = []
        _n_thm = before.count("theorem ") + before.count("lemma ")
        # a RESET substrate has NO theorems/lemmas (empty or import-only); an established one always has them.
        # Keying on "zero results" (not a char-length heuristic) is the robust reset signal.
        _trivial = (_n_thm == 0)
        if _prior and _trivial:
            return {"ok": False, "reverted": False, "theory_reset_detected": True,
                    "new_decls": [], "sorried_statements": [],
                    "reason": (f"THEORY-IDENTITY GUARD: substrate {theory_path.name!r} has {len(_prior)} banked "
                               f"(proven) facts but the file is empty/trivial ({_n_thm} theorems) — it was RESET. "
                               f"Refusing to re-formalize from prose (would orphan the proven theory in a NEW "
                               f"vocabulary — the AMM ConstantProductPool→PoolState RCA). Recover the proven theory "
                               f"(rederive_library_from_events / restore a backup) BEFORE re-running.")}
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


def governed_def_revision_gate(before_src: str, after_src: str, def_name: str, *,
                               verify_fn: "Callable[[str], bool]") -> "tuple[bool, str]":
    """ANTI-GAMING gate for SUPERSESSION-ACTING (the governed def-revision the `-- SUPERSEDE` request was queued
    for). When a kernel-CONFIRMED-false theorem traces to a too-weak `def <D>`, the agent may STRENGTHEN it —
    but only soundly. `after_src` is accepted iff:
      (1) the OLD def is preserved VERBATIM, renamed `<D>__pre` (so the witness can name it);
      (2) a NEW `def <D>` exists (same name → existing usages rebind to it);
      (3) a `witness_strengthen_<D>` theorem is present AND `verify_fn` KERNEL-confirms it — it proves
          `∀ …, <D> … → <D>__pre …`, i.e. the new def IMPLIES the old = a STRENGTHENING. A weakening /
          trivialization / sideways-change cannot prove this, so it is rejected;
      (4) every OTHER prior decl is UNCHANGED (append-only — only <D>, <D>__pre, the witness are new/changed).
    Goldilocks: the AGENT authors the stronger def + proves the implication (upstream agency); the KERNEL gates
    that it is genuinely a strengthening (the boundary). Reuses the canonical `decl_blocks`/`lean_source` parser
    and the SAME witness verifier the denotation leg uses — no new oracle, no parallel machinery. The goal and
    every other def are untouched, so a revision can only RESTRICT <D> (it cannot launder a false theorem)."""
    from ztare.leanmill.solver.statement_integrity import decl_blocks
    from ztare.leanmill import lean_source as _ls
    pre, witness = f"{def_name}__pre", f"witness_strengthen_{def_name}"

    def _norm(s: str) -> str:
        return " ".join((s or "").split())

    def _value(src: str, name: str) -> str:   # the def's value (after `:=`), whitespace-normalized
        body = _ls.def_body(src, name) or ""
        v = _ls.split_at_proof(body)[1]
        return _norm(v[2:] if v.startswith(":=") else v)

    if def_name not in _ls.def_names(before_src):
        return False, f"{def_name} is not a prior definition"
    if pre not in _ls.def_names(after_src):
        return False, f"old def not preserved as `{pre}` (the strengthening witness must reference it)"
    if _value(after_src, pre) != _value(before_src, def_name):
        return False, f"`{pre}` body is not the verbatim original `{def_name}` body"
    if def_name not in _ls.def_names(after_src):
        return False, f"revised `{def_name}` missing"
    if witness not in _ls.theorem_names(after_src):
        return False, f"missing strengthening witness `{witness}` (∀ …, {def_name} … → {pre} …)"
    # (4) NO laundering of any OTHER decl. A non-superseded CONCEPT def (Prop-valued — the meaning surface) must
    # stay BYTE-IDENTICAL; a THEOREM/instance/term may keep its STATEMENT/type but ADAPT its proof/body to the
    # strengthened def (a structure-field def like single-crossing forces its instances, e.g. `const`, to
    # re-prove — forbidding that would make the whole mechanism unusable). Statements (signatures) are the
    # laundering boundary; the kernel re-verifies the adapted proofs, and every downstream closure is re-governed.
    bb, ab = dict(decl_blocks(before_src)), dict(decl_blocks(after_src))
    before_defs = set(_ls.def_names(before_src))
    for n, blk in bb.items():
        short = n.split(".")[-1]
        if short == def_name:
            continue   # the superseded def may change its meaning (gated by the strengthening witness above)
        if n not in ab:
            return False, f"prior decl removed: `{n}` (not allowed)"
        if short in before_defs and _ls.def_is_prop_valued(before_src, short):
            if " ".join(ab[n].split()) != " ".join(blk.split()):   # a CONCEPT def must be byte-identical
                return False, f"a non-superseded CONCEPT def changed: `{n}` (only `{def_name}` may change its meaning)"
        elif _norm(_ls.signature_before_proof(ab[n])) != _norm(_ls.signature_before_proof(blk)):
            return False, f"prior decl SIGNATURE/type changed: `{n}` (statements are append-only; only proofs/instance-bodies may adapt)"
    # (5) the strengthening must be KERNEL-confirmed — new `<D>` IMPLIES old `<D>__pre` (a decoy/weakening can't)
    try:
        if not verify_fn(witness):
            return False, f"`{witness}` not kernel-verified — the revision is not a proven strengthening (rejected)"
    except Exception as _e:  # noqa: BLE001
        return False, f"witness verify error: {_e!r}"
    return True, f"`{def_name}` soundly strengthened — `{witness}` kernel-verified; goal + other defs untouched"


def _detect_revised_def(after_src: str) -> "str | None":
    """The def the agent revised: a `def <D>` for which BOTH `<D>__pre` (preserved old) and
    `witness_strengthen_<D>` (the strengthening proof) were written. None if no revision pattern present."""
    from ztare.leanmill import lean_source as _ls
    defs, thms = set(_ls.def_names(after_src)), set(_ls.theorem_names(after_src))
    for d in defs:
        if f"{d}__pre" in defs and f"witness_strengthen_{d}" in thms:
            return d
    return None


def governed_def_revision(theory_rel: str, *, lean_root: Path, dispatch: "Callable",
                          false_lemma: str, counterexample: str = "",
                          compile_fn: "Optional[Callable]" = None,
                          verify_fn_factory: "Optional[Callable]" = None,
                          timeout_s: "int | None" = None) -> dict:
    """SUPERSESSION-ACTING orchestrator — the self-correction the `-- SUPERSEDE` request was queued for. A
    campaign lemma was KERNEL-confirmed false because a def it cites is too WEAK; dispatch the agent to
    STRENGTHEN that def (preserve old as `<D>__pre`, prove `witness_strengthen_<D>`), then gate via
    `governed_def_revision_gate` (only a kernel-proven strengthening passes — no laundering). The theory file is
    REVERTED on any failure (never poison the substrate). Returns {ok, revised_def?, reverted?, reason}. Reuses
    the v33 compile probe + the SAME witness verifier the denotation leg uses — no parallel machinery."""
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    from ztare.leanmill.solver import prompts as _p
    from ztare.common.timeouts import timeout_s as _ts
    theory_path = (lean_root / theory_rel) if not Path(theory_rel).is_absolute() else Path(theory_rel)
    before = theory_path.read_text(encoding="utf-8") if theory_path.exists() else ""
    if not before.strip():
        return {"ok": False, "reason": "no theory file to revise"}
    prompt = _p.REVISE_DEF_PROMPT.format(path=str(theory_path), false_lemma=(false_lemma or "")[:700],
                                         counterexample=(counterexample or "(no explicit counterexample text)")[:700])
    try:
        dispatch(prompt, repo=lean_root, timeout=timeout_s or _ts("notes_lemma"))
    except TypeError:                              # injected fakes may omit the timeout kw
        dispatch(prompt, repo=lean_root)
    except Exception as e:                         # noqa: BLE001 — failed dispatch leaves the file; gates below decide
        return {"ok": False, "reason": f"dispatch error: {repr(e)[:120]}"}
    after = theory_path.read_text(encoding="utf-8") if theory_path.exists() else ""
    if after == before:
        return {"ok": False, "reason": "no revision written"}
    cf = compile_fn or _compile_probe
    if cf(after, lean_root, "DefRevision", _ts("cold_compile")) is not True:
        theory_path.write_text(before, encoding="utf-8")
        return {"ok": False, "reverted": True, "reason": "revised theory does not compile"}
    dname = _detect_revised_def(after)
    if not dname:
        theory_path.write_text(before, encoding="utf-8")
        return {"ok": False, "reverted": True,
                "reason": "no `<D>__pre` + `witness_strengthen_<D>` revision pattern (agent did not follow the governed-revision protocol)"}
    if verify_fn_factory is not None:
        _verify = verify_fn_factory(after, lean_root)
    else:
        from ztare.leanmill.solver.def_denotation import kernel_denotation_verifier
        _verify = kernel_denotation_verifier(after, lean_root)
    okg, why = governed_def_revision_gate(before, after, dname, verify_fn=_verify)
    if not okg:
        theory_path.write_text(before, encoding="utf-8")
        return {"ok": False, "reverted": True, "revised_def": dname, "reason": why}
    return {"ok": True, "revised_def": dname, "reason": why}


def _gap_class(rec: dict) -> str:
    """The honest, typed FAILURE CLASS of a non-closing record — the reason it is a GAP, not a closure
    (Goldilocks: a gap is NEVER a closure). A firewall rejection (unfaithful / vacuous / trivial) is a
    DIFFERENT gap than an admitted-but-unclosed lemma; recording the class (not a bare "open") is what makes
    the gap ledger actionable for the next planner pass and keeps the notes taxonomy aligned with the
    per-statement `no_good_store` (tactical conflict clauses) + `conjecture_book` (evidence ledger) the
    solver already maintains."""
    reason = " ".join(str(rec.get("faithfulness_reason") or "").split()).strip()
    if rec.get("faithful") is not True:
        return "firewall_rejected" + (f": {reason[:160]}" if reason else "")
    # faithful=True but still a non-closure: surface the outcome AND any gate reason (e.g. a def-shell / triviality
    # verdict on an admitted statement) — previously dropped, which hid the cause across a whole campaign (the AMM
    # def-shell stall: 16 `gap[rejected_by_firewall]` lines with no reason). Observability, 2026-06-24.
    return str(rec.get("outcome") or "open") + (f": {reason[:160]}" if reason else "")


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
    # ── DETERMINISTIC GAP LEDGER (honest non-closures — recorded, NEVER laundered into a closure). Writes
    #    WHICH blueprint lemmas/target stayed OPEN this run + their typed FAILURE CLASS (firewall_rejected /
    #    admitted_and_exact_gap / open / deferred:campaign_wall). This is the CAMPAIGN-level status map the
    #    NEXT planner pass reads from the blueprint — DISTINCT in granularity from the two machine ledgers the
    #    leaf already consumes: `no_good_store.jsonl` is per-STATEMENT tactical ("don't retry THIS rejected
    #    approach", rendered into the leaf prompt at the lemma level) and `conjecture_book.jsonl` is the
    #    machine evidence ledger. A gap is a GOVERNED FACT (the kernel/governance decided it did not close), so
    #    it lives here in the deterministic section the agent cannot author — it can never become a fake ✅. ──
    _seen_gap: set = set()
    gap_lines: "list[str]" = []
    def _add_gap(nl: str, cls: str) -> None:
        key = (nl or "").strip()
        if not key or key in _seen_gap:
            return
        _seen_gap.add(key)
        gap_lines.append(f"- ⬜ {nl} — gap[{cls}]")
    for l in open_:
        _add_gap(l.get("nl", ""), _gap_class(l))
    _tgt_gap = result.get("target") or {}
    if _tgt_gap and not _tgt_gap.get("solved"):
        _tcls = (f"deferred:{_tgt_gap.get('deferred')}" if _tgt_gap.get("deferred") else _gap_class(_tgt_gap))
        _add_gap("(TARGET) " + (result.get("target_nl") or ""), _tcls)
    for d in (result.get("wall_deferred") or []):
        if str(d).strip() == (result.get("target_nl") or "").strip():
            continue   # the TARGET, if wall-deferred, is already recorded above (don't double-count)
        _add_gap(str(d)[:200], "deferred:campaign_wall")
    if gap_lines:
        det += ["", "## Gaps this run (non-closures — NOT proven, NOT citable):"] + gap_lines
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
                open_md.append(f"\n### ⬜ {l.get('nl', '')}{tag} — gap[{_gap_class(l)}], planner sub-decomposition:")
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


def _run_shelf_prelude(out: dict, since_iso: str, *, ledger: "Optional[Path]" = None) -> str:
    """Assemble THIS run's proven sibling lemmas into a compile prelude so the TARGET solve has them IN SCOPE
    and can CITE them (a true dependency graph) rather than re-deriving inline — the composition fix
    (2026-06-23, after Gemini flagged the FTAP target re-proving its lemmas as dead code).

    Source = the closure-cert ledger's `recompilable_probe` (the full proven `theorem … := <proof>`), the same
    ledger `deep_closures_since` reads. FILTERED to this run's own closed-lemma decl names (a concurrent
    campaign shares the ledger, so a since-`ts` window alone would import a neighbour's lemmas). Imports are
    stripped (the assembled target body supplies exactly one). Canonical decl parser (`statement_integrity.
    decl_blocks`) — never a re-rolled regex. Returns "" when nothing applies (⇒ byte-identical to the old body)."""
    from ztare.leanmill.solver.statement_integrity import decl_blocks
    names: set = set()
    for lem in out.get("lemmas", []):
        if not lem.get("solved"):
            continue
        try:
            for nm, _blk in decl_blocks(lem.get("lean_statement") or ""):
                if nm:
                    names.add(nm)
        except Exception:  # noqa: BLE001
            continue
    if not names:
        return ""
    if ledger is None:
        from ztare.leanmill.solver.solver_core import ADHOC_CLOSURE_CERTIFICATES as _L
        ledger = _L
    pieces: "list[str]" = []
    seen: set = set()
    try:
        lines = Path(ledger).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for ln in lines:
        try:
            c = json.loads(ln)
        except ValueError:
            continue
        if c.get("outcome") != "closed" or str(c.get("ts") or "") < (since_iso or ""):
            continue
        tgt = c.get("target") or ""
        if tgt not in names or tgt in seen:
            continue
        probe = c.get("recompilable_probe") or ""
        if not probe.strip():
            continue
        seen.add(tgt)
        body = "\n".join(l for l in probe.splitlines() if not l.lstrip().startswith("import")).strip()
        if body:
            pieces.append(body)
    return "\n\n".join(pieces)


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
    # canonical ## Lemmas editor (no scattered regex; the sorried-work-item queueing fix)
    _il = _insert_lemmas_section("## Target\nT.\n## Lemmas\n- human rung\n", ["theorem c1 : P", "theorem c2 : Q"])
    ok("insert_lemmas: bullets spliced foundational-FIRST under existing ## Lemmas",
       _il.index("- theorem c1 : P") < _il.index("- human rung") and "- theorem c2 : Q" in _il
       and parse_notes(_il)[1][:2] == ["theorem c1 : P", "theorem c2 : Q"])   # parse round-trips
    _il2 = _insert_lemmas_section("## Target\nT.\n## Theory file\nt.lean\n", ["theorem only : R"])
    ok("insert_lemmas: NO ## Lemmas anchor ⇒ section CREATED (work-items never dropped)",
       "## Lemmas" in _il2 and parse_notes(_il2)[1] == ["theorem only : R"]
       and "## Theory file" in _il2)   # preserves the rest
    ok("insert_lemmas: empty bullets ⇒ unchanged",
       _insert_lemmas_section("## Target\nT.\n", []) == "## Target\nT.\n")

    # --- hermetic loop: Lemma A closes, Lemma B exact_gaps, target opens ---
    seen_notes: dict = {}
    seen_prelude: dict = {}

    def mock_attack(nl, *, lean_root, timeout_s, notes=None, shelf_prelude=""):
        seen_notes[nl] = notes
        seen_prelude[nl] = shelf_prelude
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
    # composition fix: the target attack is invoked WITH the shelf_prelude kwarg (in scope, not just notes text)
    ok("target_gets_shelf_prelude_kwarg", "For all n, P n." in seen_prelude)

    # --- the false-positive guard: a non-'closed' truthy outcome must NOT count as solved ---
    def gap_attack(nl, *, lean_root, timeout_s, notes=None, shelf_prelude=""):
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

        # --- GAP LEDGER (honest non-closures recorded for the next planner pass; gap≠closure) ---
        ok("gap_class: outcome for a faithful-but-open record",
           _gap_class({"faithful": True, "outcome": "admitted_and_exact_gap"}) == "admitted_and_exact_gap")
        ok("gap_class: firewall_rejected for an unfaithful record",
           _gap_class({"faithful": False, "faithfulness_reason": "vacuous: hypothesis is False"})
           .startswith("firewall_rejected:"))
        r_gap = {"target_nl": "Prove the big thing", "summary": "s",
                 "lemmas": [{"nl": "L1 closes", "solved": True, "outcome": "closed", "faithful": True},
                            {"nl": "L2 gaps", "solved": False, "outcome": "admitted_and_exact_gap",
                             "faithful": True},
                            {"nl": "L3 unfaithful", "solved": False, "faithful": False,
                             "faithfulness_reason": "trivial: provable by simp"}],
                 "shelf": ["theorem l1 : True := trivial"],
                 "target": {"nl": "Prove the big thing", "solved": False, "outcome": "admitted_and_open",
                            "faithful": True},
                 "wall_deferred": ["L4 never attempted"]}
        gt = write_refined_notes(r_gap, Path(_td) / "gap.md").read_text(encoding="utf-8")
        ok("gap: non-closure ledger header present",
           "Gaps this run (non-closures" in gt and "NOT proven, NOT citable" in gt)
        ok("gap: open lemma recorded with its typed failure class",
           "L2 gaps — gap[admitted_and_exact_gap]" in gt)
        ok("gap: firewall-rejected lemma recorded as such",
           "L3 unfaithful — gap[firewall_rejected" in gt)
        ok("gap: TARGET gap recorded with its class",
           "(TARGET) Prove the big thing — gap[admitted_and_open]" in gt)
        ok("gap: wall-deferred lemma recorded as deferred:campaign_wall",
           "L4 never attempted — gap[deferred:campaign_wall]" in gt)
        ok("gap: a CLOSED lemma is NOT in the gap ledger (only in ✅ proven)",
           "L1 closes — gap[" not in gt and "- ✅ L1 closes" in gt)
        # a wall-deferred TARGET is recorded ONCE (not double-counted via wall_deferred + target)
        r_wallt = {"target_nl": "Big T", "summary": "s", "lemmas": [],
                   "target": {"deferred": "campaign_wall", "solved": False}, "wall_deferred": ["Big T"]}
        rwt = write_refined_notes(r_wallt, Path(_td) / "wallt.md").read_text(encoding="utf-8")
        ok("gap: wall-deferred TARGET recorded once (no double-count)",
           rwt.count("— gap[deferred:campaign_wall]") == 1 and "(TARGET) Big T" in rwt)
        # a fully-closed run renders NO gap ledger (clean output)
        r_clean = {"target_nl": "T", "summary": "s",
                   "lemmas": [{"nl": "all good", "solved": True, "outcome": "closed", "faithful": True}],
                   "shelf": ["theorem g : True := trivial"],
                   "target": {"nl": "T", "solved": True, "outcome": "closed", "faithful": True}}
        ok("gap: fully-closed run has NO gap ledger",
           "Gaps this run" not in write_refined_notes(r_clean, Path(_td) / "clean.md").read_text(encoding="utf-8"))

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

    # ── governed_def_revision_gate (supersession-ACTING anti-gaming, 2026-06-23) ──
    _before = "import Mathlib\ndef D (n : Nat) : Prop := n ≥ 0\ntheorem other : True := trivial\n"
    _after_ok = ("import Mathlib\n"
                 "def D__pre (n : Nat) : Prop := n ≥ 0\n"                          # old preserved verbatim
                 "def D (n : Nat) : Prop := n ≥ 0 ∧ n ≤ 100\n"                     # STRENGTHENED
                 "theorem witness_strengthen_D : ∀ n, D n → D__pre n := fun _ h => h.1\n"  # new → old
                 "theorem other : True := trivial\n")                              # untouched
    _ok, _ = governed_def_revision_gate(_before, _after_ok, "D", verify_fn=lambda w: w == "witness_strengthen_D")
    ok("revision gate: strengthening + KERNEL-verified witness ⇒ ACCEPTED", _ok)
    _ok2, _ = governed_def_revision_gate(_before, _after_ok, "D", verify_fn=lambda w: False)
    ok("revision gate: witness NOT kernel-verified ⇒ REJECTED (anti-gaming core)", not _ok2)
    _after_other = _after_ok.replace("theorem other : True := trivial", "theorem other : False := sorry")
    _ok3, _ = governed_def_revision_gate(_before, _after_other, "D", verify_fn=lambda w: True)
    ok("revision gate: changing a NON-superseded decl ⇒ REJECTED (append-only stands)", not _ok3)
    _after_nopre = _after_ok.replace("def D__pre (n : Nat) : Prop := n ≥ 0\n", "")
    _ok4, _ = governed_def_revision_gate(_before, _after_nopre, "D", verify_fn=lambda w: True)
    ok("revision gate: old def not preserved as __pre ⇒ REJECTED", not _ok4)
    _after_nowit = _after_ok.replace("theorem witness_strengthen_D : ∀ n, D n → D__pre n := fun _ h => h.1\n", "")
    _ok5, _ = governed_def_revision_gate(_before, _after_nowit, "D", verify_fn=lambda w: True)
    ok("revision gate: missing strengthening witness ⇒ REJECTED", not _ok5)
    # a non-superseded CONCEPT def (Prop-valued) changed ⇒ REJECTED (the meaning/laundering surface stays fixed)
    _before_e = "import Mathlib\ndef E (n : Nat) : Prop := True\ndef D (n : Nat) : Prop := n ≥ 0\ntheorem other : True := trivial\n"
    _after_e = ("import Mathlib\ndef E (n : Nat) : Prop := False\n"   # CONCEPT def E changed
                "def D__pre (n : Nat) : Prop := n ≥ 0\ndef D (n : Nat) : Prop := n ≥ 0 ∧ n ≤ 100\n"
                "theorem witness_strengthen_D : ∀ n, D n → D__pre n := fun _ h => h.1\ntheorem other : True := trivial\n")
    _ok6, _ = governed_def_revision_gate(_before_e, _after_e, "D", verify_fn=lambda w: True)
    ok("revision gate: a non-superseded CONCEPT def changed ⇒ REJECTED", not _ok6)
    # a THEOREM proof ADAPTS (signature unchanged) ⇒ ACCEPTED (a structure instance/dependent may re-prove)
    _after_padapt = _after_ok.replace("theorem other : True := trivial", "theorem other : True := by trivial")
    _ok7, _ = governed_def_revision_gate(_before, _after_padapt, "D", verify_fn=lambda w: w == "witness_strengthen_D")
    ok("revision gate: a theorem PROOF adapts (signature same) ⇒ ACCEPTED", _ok7)

    # governed_def_revision orchestrator (mock dispatch + injected compile/verify — no live Lean)
    import tempfile as _tfr, shutil as _shr
    _lr3 = Path(_tfr.mkdtemp())
    _orig3 = "import Mathlib\ndef D (n : Nat) : Prop := True\ntheorem t : True := trivial\n"
    (_lr3 / "T.lean").write_text(_orig3, encoding="utf-8")
    def _disp_strong(prompt, *, repo=None, timeout=None):
        (_lr3 / "T.lean").write_text(
            "import Mathlib\ndef D__pre (n : Nat) : Prop := True\n"
            "def D (n : Nat) : Prop := n ≥ 0\n"
            "theorem witness_strengthen_D : ∀ n, D n → D__pre n := fun _ _ => trivial\n"
            "theorem t : True := trivial\n", encoding="utf-8")
    _rv = governed_def_revision("T.lean", lean_root=_lr3, dispatch=_disp_strong, false_lemma="thm", counterexample="cex",
                                compile_fn=lambda *a: True,
                                verify_fn_factory=lambda src, root: (lambda w: w == "witness_strengthen_D"))
    ok("governed_def_revision: agent strengthening + gate ⇒ revised", _rv.get("ok") and _rv.get("revised_def") == "D")
    (_lr3 / "T.lean").write_text(_orig3, encoding="utf-8")
    def _disp_garbage(prompt, *, repo=None, timeout=None):
        (_lr3 / "T.lean").write_text("import Mathlib\ndef D (n : Nat) : Prop := n = n\ntheorem t : True := trivial\n", encoding="utf-8")
    _rv2 = governed_def_revision("T.lean", lean_root=_lr3, dispatch=_disp_garbage, false_lemma="t", counterexample="c",
                                 compile_fn=lambda *a: True, verify_fn_factory=lambda src, root: (lambda w: True))
    ok("governed_def_revision: no __pre/witness pattern ⇒ reverted + file restored",
       (not _rv2.get("ok")) and _rv2.get("reverted") and (_lr3 / "T.lean").read_text(encoding="utf-8") == _orig3)
    _shr.rmtree(str(_lr3), ignore_errors=True)

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
    import os as _os   # FUNCTION-SCOPE binding: the embedder-liveness preflight (below) reads _os BEFORE the old
    #   later `import os as _os` bound it — Python made _os local throughout main(), so the early read raised
    #   UnboundLocalError and aborted the run at start. One import, at the top, is the fix (no shadowing sibling).
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
    # COMPOUNDING-RETRIEVER LIVENESS (2026-06-24): the semantic premise shelf (own-ledger + Mathlib recall) is the
    # compounding READ path — it surfaces "this is ALREADY proven, cite it, do not re-derive". It embeds via gemini;
    # on a dead key/quota it SILENTLY returns nothing (the shelf's `except → []`), so a "no prior work" reads as a
    # REAL absence and the run re-derives — the exact treadmill the amnesia firewall exists to prevent, and the
    # measured cause of low cross-run lemma reuse (a starved embedder = invisible 5% reuse). This wires the EXISTING
    # `embedder_liveness` guard (it was built for this and had ZERO callers) as a LOUD run-start positive control: a
    # null from the shelf is INADMISSIBLE while the embedder is dead. Advisory (never blocks — the shelf degrades to
    # lexical/empty), but now VISIBLE. ZTARE_LEANMILL_EMBEDDER_LIVENESS=0 skips.
    if _os.environ.get("ZTARE_LEANMILL_EMBEDDER_LIVENESS", "1") != "0":
        try:
            from ztare.common.embedder_liveness import embedder_live, liveness_banner
            from ztare.research_director.mathlib_semantic import _embed_query_genai as _eq
            from ztare.leanmill.semantic_premise_shelf import own_ledger_corpus as _olc
            _emb_live, _emb_why = embedder_live(_eq, atlas_nonempty=bool(_olc()))
            print(f"[notes] compounding-retriever (semantic premise shelf) embedder: "
                  f"{'LIVE — ' + _emb_why if _emb_live else 'DEAD'}", flush=True)
            if not _emb_live:
                print(liveness_banner(_emb_live, _emb_why, instrument="compounding premise-shelf embedder"), flush=True)
        except Exception as _e:  # noqa: BLE001 — liveness probe is advisory; never block the run
            print(f"[notes] embedder-liveness probe skipped: {repr(_e)[:120]}", flush=True)
    notes_path = Path(argv[0])
    # RUN ATTRIBUTION: tag this run's attempts-DB rows + forecast ledger so the compounder/forecast-router can
    # SLICE by run — the DB showed run_tag=NULL for notes runs (#92 said it should feed the substrate, but the
    # notes entry never set the env), making a run unattributable. setdefault RESPECTS an explicit A/B arm
    # (ZTARE_SOLVER_RUN_TAG=<arm>); otherwise defaults to the notes stem + a per-run stamp.
    from datetime import datetime as _dt, timezone as _tz
    _os.environ.setdefault("ZTARE_SOLVER_RUN_TAG", f"notes_{notes_path.stem}_{_dt.now().strftime('%m%dT%H%M')}")
    print(f"[notes] run_tag = {_os.environ['ZTARE_SOLVER_RUN_TAG']}", flush=True)
    _since = _dt.now(_tz.utc).isoformat()   # cert-ledger watermark (same format solve_adhoc stamps `ts` with)
    _notes_text = notes_path.read_text(encoding="utf-8")
    # CAMPAIGN DOMAIN STAMP (factory time-to-closure segmentation): label this run math vs non-math formalization
    # so the cycle-time read model can report avg-time-to-closure per domain. Source: `## Domain` in the blueprint,
    # else ZTARE_SOLVER_DOMAIN, else 'unspecified'. ONE canonical emitter (phase_timing.record_campaign); the stamp
    # is best-effort telemetry and NEVER blocks the campaign.
    try:
        from ztare.leanmill.phase_timing import record_campaign as _record_campaign
        _domain = (parse_domain(_notes_text) or _os.environ.get("ZTARE_SOLVER_DOMAIN", "") or "unspecified").strip()
        _record_campaign(_domain, run_tag=_os.environ.get("ZTARE_SOLVER_RUN_TAG", ""),
                         target=(parse_notes(_notes_text)[0] or "")[:80])
        print(f"[notes] campaign domain = {_domain!r} (time-to-closure segmentation)", flush=True)
    except Exception:  # noqa: BLE001 — telemetry stamp never blocks the campaign
        pass
    # PHASE 0 — THEORY CONSOLIDATION (#123, theory-first campaigns): when the notes declare a campaign
    # theory file, the agent EXTENDS it (defs + sorried API statements — the substrate Mathlib lacks;
    # serves the BUILDS-not-lookup invariant) behind the append-only + compile gates; each new sorried
    # API statement becomes a first-class lemma work item; the file's content rides the notes so every
    # downstream formalize/solve sees the campaign substrate. Receipt → the work-items ledger.
    _theory_rel = parse_theory_file(_notes_text)
    if _theory_rel:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch as _dd0
        if _os.environ.get("ZTARE_LEANMILL_SKIP_CONSOLIDATION") == "1":
            # FAST-DEBUG (2026-06-23): skip the ~225s theory_consolidation DISPATCH when the substrate file
            # already exists — it is still registered as the warm-env substrate + ridden into the notes below,
            # so the TARGET attack runs against the full theory without re-paying consolidation. For iterating on
            # the target/firewall/reformulation path cheaply; NEVER for a fresh blueprint (which needs the theory
            # BUILT). No-op fields so the downstream register/ride/lemma-queue logic is byte-identical.
            _tc = {"ok": True, "new_decls": [], "sorried_statements": [], "reason": "skipped (fast-debug)"}
            print("[notes] theory consolidation SKIPPED (ZTARE_LEANMILL_SKIP_CONSOLIDATION=1) — reusing the "
                  "existing substrate file", flush=True)
        else:
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
                # SUBSTRATE POSITIVE CONTROL (2026-06-25 RCA — the AMM `not_riskFreeProfit_zero` `<;>` bug): a
                # single non-compiling decl ANYWHERE in the registered substrate makes `campaign_file_env` return
                # None, which SILENTLY kills the whole campaign-aware layer (citing / warm-verify / the
                # faithfulness oracle → faithful ∀-fronted proofs FALSE-REJECT as `target_signature_altered`).
                # The substrate can be written by an ungated path (recovery / manual edit) that skips
                # theory_consolidation's GATE-2 whole-file compile, so the ONLY robust catch is a run-start
                # positive control on the ACTUAL file the campaign will use — the same fail-closed-LOUD discipline
                # as the embedder-liveness banner. ZTARE_LEANMILL_SUBSTRATE_LIVENESS=0 skips (A/B).
                if _os.environ.get("ZTARE_LEANMILL_SUBSTRATE_LIVENESS", "1") != "0" and _tp.exists():
                    try:
                        from ztare.formal.repl_compile import campaign_file_env as _cfe
                        _env_id = _cfe(str(_tp.resolve()), LEAN_ROOT_DEFAULT)   # logs the compile errors LOUDLY if it fails
                        if _env_id is not None:
                            print(f"[notes] campaign substrate positive control: LIVE — env elaborates "
                                  f"(env={_env_id}); citing/warm-verify/faithfulness-oracle armed", flush=True)
                        else:
                            print("⚠️  [notes] campaign substrate positive control: DEAD — the registered substrate "
                                  "does NOT compile (errors above). The campaign-aware layer will degrade and "
                                  "faithful proofs may FALSE-REJECT. FIX THE SUBSTRATE before trusting gaps as 'hard "
                                  "math'. (A non-compiling substrate is INADMISSIBLE — never silently re-derive.)",
                                  flush=True)
                    except Exception as _e:  # noqa: BLE001 — the control is advisory; never break the run
                        print(f"[notes] substrate positive control skipped: {repr(_e)[:100]}", flush=True)
            _theory_src = _tp.read_text(encoding="utf-8") if _tp.exists() else ""
            if _theory_src.strip():   # the substrate rides the notes (formal scaffolding channel, #88)
                _notes_text += ("\n\n## Theory (campaign substrate — cite, do not re-derive)\n```lean\n"
                                + _theory_src + "\n```\n")
            # (2026-06-23: the advisory `_supersession_steer` formalize-time nudge was REMOVED here — empirically
            # it didn't bind the formalizer against the literal NL, and it is SUBSUMED by the self-correction LOOP:
            # solve_adhoc now kernel-falsifies a stalled target → `autoformalize_and_solve`'s reformulation re-entry
            # has the agent STRENGTHEN + re-attack. One surface (the loop), not two — no parallel steer to drift.)
            # ROBUST work-item queueing (RCA 2026-06-18): the agent's own sorried API lemmas become solver
            # work items, foundational-first, via the canonical `_insert_lemmas_section` (creates `## Lemmas`
            # if absent). A theory-first blueprint with no `## Lemmas` anchor previously DROPPED them — the
            # theory got built but its crux lemmas were never attacked. These are ALREADY formal Lean (no NL
            # round-trip), so attacking them sidesteps the target's formalization firewall entirely.
            _sorried = list(_tc.get("sorried_statements", []))
            if _sorried:
                _notes_text = _insert_lemmas_section(_notes_text, _sorried)
    res = autoformalize_from_notes(_notes_text, notes_path=notes_path)  # notes_path ⇒ incremental write-back (timeout-safe)
    res["instrument_standards"] = _std   # traceability: this run's closures carry their instrument certificate
    # v3 RCA: surface kernel closures from the WHOLE recursion tree (the cert ledger), not just the
    # top-level lemma outcomes — depth≥2 rungs were silently lost to the compounding loop.
    res["deep_closures"] = deep_closures_since(_since)
    if res["deep_closures"]:
        print(f"[notes] deep rungs kernel-closed this run: "
              + ", ".join(str(d.get('target')) for d in res['deep_closures']), flush=True)
    # COMPOUNDING-HEALTH EPILOGUE — surface the AMNESIA metric every run via the CANONICAL telemetry
    # (`scripts/public/control/leanmill/compounding_curve.py`, the task-#110 producer; reporting lives in
    # scripts/ per the scripts-vs-src rule). A closure of an already-certified rung is a re-derivation; with the
    # incremental library banking at the cert-write chokepoint (`family_lemma_library` → campaign env) this should
    # trend → 0. Advisory; never gates. ZTARE_LEANMILL_COMPOUNDING_HEALTH=0 reverts. (Banking itself is NOT here
    # anymore — it is per-closure at the kernel-ratify site so a run that dies before this epilogue still compounds.)
    if _os.environ.get("ZTARE_LEANMILL_COMPOUNDING_HEALTH", "1") != "0":
        try:
            import importlib.util as _ilu
            _cc_path = REPO / "scripts/public/control/leanmill/compounding_curve.py"
            _spec = _ilu.spec_from_file_location("compounding_curve", _cc_path)
            _cc = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_cc)
            _rep = _cc.report(REPO)
            res["rederivation"] = _rep.get("rederivation")
            res["reuse"] = _rep.get("reuse")
            res["recent"] = _rep.get("recent")
            _rr = _rep.get("rederivation") or {}
            _rc = _rep.get("recent") or {}
            _ru = _rep.get("reuse") or {}
            # HEADLINE = the CLEAN-REGIME window (forward-looking, since `clean_since`; the all-time rate is a
            # cumulative ghost — this session's fixed-bug noise + test probes dominate it, so it tracks history,
            # not the engine running now). Accrues as clean runs land.
            _cn = _rc.get("clean_closures")
            print(f"[compounding-health] CLEAN (since {_rc.get('clean_since')}, {_cn} closures): "
                  f"re-derivation={_rc.get('rederivation_rate')} ({_rc.get('rederived')}/{_cn}), "
                  f"proof-reuse={_rc.get('proof_reuse_rate')} ({_rc.get('proofs_citing_a_banked_lemma')}/{_cn}); "
                  "→ re-derivation 0 / reuse 1 is healthy", flush=True)
            print(f"[compounding-health] all-time (context, NOT the live engine): "
                  f"re-derivation={_rr.get('rederivation_rate')} ({_rr.get('rederived')}/{_rr.get('closures')}), "
                  f"lemma-reuse={_ru.get('lemma_reuse_rate')} ({_ru.get('lemmas_reused')}/{_ru.get('banked_lemmas')}); "
                  "name-match lower bound", flush=True)
            _co = _rep.get("cost") or {}
            # INFER-VIA-USE (no paid A/B): bank-served closures (direct attribution) + does closing get CHEAPER as
            # the corpus grows (median wall_s early→recent). Observational/confounded — a trend to watch, not a causal claim.
            print(f"[compounding-health] infer-via-use: bank-served={_co.get('bank_served_rate')} "
                  f"({_co.get('bank_served_closures')}/{_co.get('closed')} closures cited a banked rung instead of re-deriving); "
                  f"median wall_s early→recent = {_co.get('median_wall_s_early')}→{_co.get('median_wall_s_recent')} "
                  "(↓ = closing cheaper as the bank grows; confounded by difficulty mix)", flush=True)
        except Exception as _e:  # noqa: BLE001 — telemetry only; never blocks the run
            print(f"[notes] compounding-health skipped: {repr(_e)[:120]}", flush=True)
    # TRAINING-CORPUS EXPORT (the expert-iteration flywheel tap, 2026-06-24): refresh the kernel-verified training
    # corpus (prover (stmt,proof) + autoformalization NL↔Lean + falsification) from the run's closures so the
    # inference→pretrain bridge stays current — our defensible "void" data that no public corpus has. Forward-
    # looking (clean-regime) by default; best-effort, never blocks. ZTARE_LEANMILL_EXPORT_TRAINING_CORPUS=0 skips.
    if _os.environ.get("ZTARE_LEANMILL_EXPORT_TRAINING_CORPUS", "1") != "0":
        try:
            import importlib.util as _ilu2
            _ec = REPO / "scripts/public/control/leanmill/export_training_corpus.py"
            _sp = _ilu2.spec_from_file_location("export_training_corpus", _ec)
            _m = _ilu2.module_from_spec(_sp); _sp.loader.exec_module(_m)
            _man = _m.export(REPO)
            res["training_corpus"] = _man
            print(f"[training-corpus] refreshed: {_man.get('prover_pairs')} prover "
                  f"({_man.get('prover_void_novel')} void-novel) + {_man.get('autoformalization_pairs')} NL↔Lean "
                  f"+ {_man.get('falsification_pairs')} falsification (clean since {_man.get('clean_since')})", flush=True)
        except Exception as _e:  # noqa: BLE001 — flywheel tap is best-effort; never blocks the run
            print(f"[notes] training-corpus export skipped: {repr(_e)[:120]}", flush=True)
    # DENOTATION-FAITHFULNESS EPILOGUE (#162, theory-first honest catch). For a theory-first run the agent
    # BUILT new defs (the substrate Mathlib lacks) — the firewall only governs the STATEMENT, so a self-
    # consistent DECOY def can pass every internal check. We MEASURE (never assert) whether each built def's
    # denotation is PINNED by a kernel-verified EXTERNAL anchor: an `anchor_…` overlap-agreement the agent
    # proved (Kalman external output) OR participation in a kernel-closed proof with the shelf (UC). The
    # verdict (PINNED / UNDERDETERMINED=honest-gap / REFUTED=decoy-caught) is ADVISORY telemetry — it never
    # gates a closure — so default-on is safe; only pays kernel cost when defs+anchors actually exist.
    # ZTARE_LEANMILL_DENOTATION_CHECK=0 reverts. See docs/concepts/leanmill_architecture.md §denotation.
    if _theory_rel and _os.environ.get("ZTARE_LEANMILL_DENOTATION_CHECK", "1") != "0":
        try:
            from ztare.leanmill.solver.def_denotation import (
                certify_def_denotation, kernel_denotation_verifier, mentions_token)
            _tp2 = LEAN_ROOT_DEFAULT / _theory_rel
            _theory_final = _tp2.read_text(encoding="utf-8") if _tp2.exists() else ""
            if _theory_final.strip():
                from ztare.leanmill import lean_source as _lsd
                _built = _lsd.def_names(_theory_final)
                # composition anchor (UC): a built def appearing in a kernel-closed proof composed soundly.
                _proof_blob = "\n".join((d.get("closure_lean") or "") + "\n" + (d.get("statement") or "")
                                        for d in res["deep_closures"])
                _composed = {d for d in _built if mentions_token(_proof_blob, d)}
                _verify = kernel_denotation_verifier(_theory_final, LEAN_ROOT_DEFAULT)
                _den = certify_def_denotation(_theory_final, verify_anchor_fn=_verify, composed_defs=_composed)
                res["denotation"] = _den
                print(f"[notes] denotation-faithfulness: {_den['verdict']} — {_den['reason']}", flush=True)
                # VACUITY-faithfulness (sibling leg): a ∀-over-membership Prop def is vacuously true on ∅, so a
                # theorem concluding it of a constructed set can be true-but-empty. Reuses the SAME kernel
                # verifier; advisory telemetry, never gates. ZTARE_LEANMILL_VACUITY_CHECK=0 reverts.
                if _os.environ.get("ZTARE_LEANMILL_VACUITY_CHECK", "1") != "0":
                    from ztare.leanmill.solver.def_denotation import certify_nonvacuity
                    _vac = certify_nonvacuity(_theory_final, verify_fn=_verify)
                    res["nonvacuity"] = _vac
                    print(f"[notes] vacuity-faithfulness: {_vac['verdict']} — {_vac['reason']}", flush=True)
        except Exception as _e:  # noqa: BLE001 — advisory telemetry; never blocks the run
            print(f"[notes] denotation/vacuity check skipped: {repr(_e)[:120]}", flush=True)
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
