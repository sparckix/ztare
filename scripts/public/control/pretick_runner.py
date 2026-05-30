#!/usr/bin/env python3
"""pretick_runner — FORCES the pre-tick (the thing the agent kept
naming-not-doing), as the autoresearch SHAPE applied to the FRONT of
a tick.

Operator scope (2026-05-18): the agent AUTHORS this; the OPERATOR
INSPECTS it. Inspection — not operator-authoring — is the
non-self-bless trust root (cheap, the irreducible human role finally
located correctly). This is NOT a Lean gate (that is one optional
downstream part); it forces the PRE-TICK steps the brief surfaced and
the agent satisficed all session:

  1 scientific amnesia precheck   (deterministic: overlap_detected)
  2 orchestration-menu compose    (problem_class -> sub_class -> chain)
  3 pattern / anti-pattern surface (the obligated chain, from catalog)
  3b pattern action contract       (routed carriers + typed receipt fields)
  4 (NS) residual graph / void-audit consume (surfaced source-void id)
  5 GP-230 forecast contract       (consumes-surfaced bound;
                                    independent-agent warm wake)
  6 GP-233 yield-decomposition scaffold (residual_to_lever record stub)

Each step RUNS the EXISTING tool (composed, not reinvented) and emits
a receipt. The runner FAILS CLOSED if any step's receipt is absent or
empty: no COMPLETE pretick_manifest -> the tick may not proceed and
tick_close must refuse. The agent cannot satisfy this by narrating
"I considered the patterns": the receipts are tool stdout/artifacts,
not agent prose. Faking is strictly dominated (autoresearch lesson):
the only path through is to actually run the pre-tick.

Honest bound (carried, not hidden): this forces the pre-tick is
EXECUTED. It does not — cannot — certify the resulting research
insight is deep; that residual is the operator inspecting this
manifest + the genuinely-open-math human review. The runner shrinks
the ungated surface to its true size; it does not eliminate the
human. Composes: ns_scientific_amnesia_precheck, orchestration_menu
.yaml, the void-audit json, forecast_pool.py, residual_to_lever.py.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
PY = sys.executable


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()[:16]


def _run(cmd: list[str], timeout: int = 240) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=str(REPO), capture_output=True,
                            text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 99, f"__RUN_ERROR__ {type(e).__name__}: {e}"


def _step(name: str, ok: bool, receipt: dict) -> dict:
    return {"step": name, "ok": bool(ok),
            "receipt": receipt,
            "receipt_sha": _sha(json.dumps(receipt, sort_keys=True,
                                           ensure_ascii=False))}


HARD_MATH_QUALIFIERS = {
    "clay",
    "conjecture",
    "estimate",
    "formal",
    "frontier",
    "hard mathematical",
    "hard research",
    "lean",
    "lemma",
    "mathematical",
    "millennium",
    "navier",
    "pde",
    "proof",
    "theorem",
}

NON_MATH_RECEIPT_META_TERMS = {
    "catalog",
    "confuser",
    "downstream action",
    "evidence carrier",
    "gp-216",
    "gp-219",
    "operator",
    "portable receipt",
    "primitive",
    "receipt fields",
    "routing",
    "schema",
    "typed fields",
}

RECURRENCE_MEMORY_TERMS = {
    "amnesia",
    "killed vector",
    "killed-vector",
    "memory",
    "recurrence",
    "recurring",
    "rediscover",
    "rediscovery",
}


def _norm_goal(text: str) -> str:
    return " ".join(text.replace("-", " ").replace("_", " ").lower().split())


def _contains_any(text: str, needles: set[str]) -> bool:
    return any(needle in text for needle in needles)


def _has_recurrence_memory_risk(goal: str) -> bool:
    return _contains_any(_norm_goal(goal), RECURRENCE_MEMORY_TERMS)


def _repair_shallow_menu_choice(
    *,
    goal: str,
    pc: str | None,
    menu_scores: dict[str, int],
) -> tuple[str | None, dict]:
    """Prevent generic residual language from masquerading as hard math.

    The orchestration menu is a coarse surface selector. The old scoring let the
    bare word "residual" select hard_mathematical_residual even for catalogue,
    receipt-schema, or apparatus-routing questions. Keep hard-math routing when
    the goal has hard/formal/math qualifiers; otherwise redirect receipt/meta
    residuals to apparatus_self_audit so the typed pattern-action contract can
    do the finer classification.
    """
    gnorm = _norm_goal(goal)
    hard_qualified = _contains_any(gnorm, HARD_MATH_QUALIFIERS)
    receipt_meta = _contains_any(gnorm, NON_MATH_RECEIPT_META_TERMS)
    repaired = False
    repair_reason = ""
    original_pc = pc
    if pc == "hard_mathematical_residual" and receipt_meta and not hard_qualified:
        if menu_scores.get("apparatus_self_audit", 0) <= 0:
            menu_scores["apparatus_self_audit"] = 1
        pc = "apparatus_self_audit"
        repaired = True
        repair_reason = (
            "generic residual/schema/operator wording without hard-math "
            "qualifier; routed to apparatus_self_audit instead of hard math"
        )
    open_set_refusal = False
    if pc is None:
        pc = "outside_menu"
        repaired = True
        open_set_refusal = True
        repair_reason = (
            "no source-supported orchestration menu class matched; emit "
            "outside_menu so the RD agent defers to a new residual class "
            "instead of forcing a known research-evidence class"
        )
    return pc, {
        "version": "orchestration-menu-open-set-guard/v2",
        "original_problem_class": original_pc,
        "selected_problem_class": pc,
        "hard_math_qualified": hard_qualified,
        "receipt_meta_surface": receipt_meta,
        "open_set_refusal": open_set_refusal,
        "new_residual_class_candidate": "unmapped_by_orchestration_menu" if open_set_refusal else "",
        "repaired": repaired,
        "repair_reason": repair_reason,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal", required=True)
    ap.add_argument("--substrate", required=True)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--tick-id", required=True)
    ap.add_argument("--contract-id", required=True,
                    help="the GP-230 forecast contract THIS tick will "
                         "consume — must already exist (created via "
                         "forecast_pool) and be surfaced-bound; lifted "
                         "to manifest.contract_id so the GP-241 daemon "
                         "can mutually-bind the manifest to the frozen "
                         "signed start row (presence≠this-tick).")
    ap.add_argument("--universal-ops", required=True,
                    help="comma-sep structural-language op-ids the "
                         "tick translates the problem into (≥1; "
                         "META-PATTERN-022). Each MUST resolve in the "
                         "deterministic v5 or meta-meta op catalog — "
                         "same shape as --contract-id: a concrete "
                         "selection the runner validates, not free "
                         "narration.")
    ap.add_argument("--scopes", required=True,
                    help="comma-sep of the 4 scopes covered "
                         "(META-PATTERN-023): local,chain,recursive,"
                         "meta — ALL FOUR required or the step fails.")
    # GP-241 #61 — STRUCTURAL amnesia anchor (substrate-AGNOSTIC core;
    # all substrate specifics come from the org/structural_anchors/
    # registry.yaml PLUGIN — NEVER hardcoded here, mirroring the
    # kernel-app config model). Lexical step 1 (overlap_detected) is
    # necessary-not-sufficient: it catches vocabulary recurrence, NOT
    # "which registered route-invariant residual_target is this tick
    # addressing + did it traverse to the registered anchor source".
    # Enforced only for substrates that have REGISTERED an anchor
    # (same honest-N/A shape as step 4 — unregistered substrates and
    # legacy invocations stay backward-compatible).
    ap.add_argument("--residual-target", default="",
                    help="(REQUIRED iff the substrate is registered) "
                         "the route-invariant residual target this "
                         "tick addresses; must resolve to a target "
                         "id OR alias in org/structural_anchors/"
                         "registry.yaml for this substrate (name-the-"
                         "target — a registry-membership-checked "
                         "selection, not prose).")
    ap.add_argument("--anchor-files", default="",
                    help="(REQUIRED iff the substrate is registered) "
                         "comma-sep source files the structural-"
                         "anchor traversal actually visited; each "
                         "must exist AND (if the registry declares "
                         "anchor_visit_required for this substrate) "
                         "that file MUST be among them.")
    a = ap.parse_args()

    rdir = REPO / "analytics" / "public" / "pretick" / a.tick_id
    rdir.mkdir(parents=True, exist_ok=True)
    steps: list[dict] = []

    # 1 — scientific amnesia precheck (deterministic overlap signal).
    amn = REPO / ("projects/ns_millennium_hunt/scripts/"
                  "ns_scientific_amnesia_precheck.py")
    if not amn.is_file():
        amn = (REPO / "scripts/public/control/"
               "scientific_amnesia_precheck.py")
    rc, out = _run([PY, str(amn), "--query", a.goal])
    overlap = "overlap_detected: True" in out
    steps.append(_step("scientific_amnesia",
                        rc == 0 and ("overlap_detected" in out),
                        {"overlap_detected": overlap,
                         "head": out[:1500]}))

    # 2 — orchestration-menu compose (problem_class -> sub_class).
    menu = REPO / "org" / "menu" / "orchestration_menu.yaml"
    mtext = menu.read_text(encoding="utf-8") if menu.is_file() else ""
    g = a.goal.lower()
    pc = None
    selected_subclasses: list[str] = []
    selected_chain: list[str] = []
    applicable_patterns: list[str] = []
    always_on_patterns: list[str] = []
    menu_scores: dict[str, int] = {}
    try:
        import yaml as _menu_yaml  # noqa: E402
        _menu = _menu_yaml.safe_load(mtext) or {}
        _pcs = _menu.get("problem_classes", {}) or {}
        # Top-level `always_on`: standing-discipline patterns that apply on
        # EVERY tick regardless of which problem_class is routed. Distinct
        # from the routed chain — surfaced separately, never class-gated.
        for _ao in (_menu.get("always_on") or []):
            _ao_tok = str(_ao).split()[0].strip()
            if _ao_tok:
                always_on_patterns.append(_ao_tok)
        for _class_id, _class_body in _pcs.items():
            if not isinstance(_class_body, dict):
                continue
            _score = 0
            _triggers = _class_body.get("triggers", {}) or {}
            for _kind in ("lexical", "structural"):
                for _tok in _triggers.get(_kind, []) or []:
                    _needle = str(_tok).replace("-", " ").replace("_", " ").lower()
                    if _needle and _needle in g.replace("-", " ").replace("_", " "):
                        _score += 2 if _kind == "lexical" else 1
            for _sub_id, _sub_body in (_class_body.get("sub_classes", {}) or {}).items():
                if not isinstance(_sub_body, dict):
                    continue
                _sub_score = 0
                _sub_triggers = _sub_body.get("triggers", {}) or {}
                for _kind in ("lexical", "structural"):
                    for _tok in _sub_triggers.get(_kind, []) or []:
                        _needle = str(_tok).replace("-", " ").replace("_", " ").lower()
                        if _needle and _needle in g.replace("-", " ").replace("_", " "):
                            _sub_score += 2 if _kind == "lexical" else 1
                if _sub_score:
                    _score += _sub_score
            if str(_class_id).replace("_", " ") in g.replace("_", " "):
                _score += 3
            menu_scores[str(_class_id)] = _score
        if menu_scores:
            pc = max(menu_scores.items(), key=lambda kv: (kv[1], kv[0]))[0]
            if menu_scores.get(pc, 0) <= 0:
                pc = None
        pc, _menu_guard = _repair_shallow_menu_choice(
            goal=a.goal,
            pc=pc,
            menu_scores=menu_scores,
        )
        if pc and pc != "outside_menu":
            _body = _pcs.get(pc) or {}
            selected_chain.extend(str(x) for x in (_body.get("default_chain") or []))
            # v0.2.0: `applicable` lists patterns that declare this class but
            # are not part of the default spine — surface them as available
            # (distinct from the default chain), not as chain members.
            applicable_patterns.extend(
                str(x) for x in (_body.get("applicable") or []))
            for _sub_id, _sub_body in (_body.get("sub_classes", {}) or {}).items():
                if not isinstance(_sub_body, dict):
                    continue
                _sub_triggers = _sub_body.get("triggers", {}) or {}
                _sub_hit = False
                for _kind in ("lexical", "structural"):
                    for _tok in _sub_triggers.get(_kind, []) or []:
                        _needle = str(_tok).replace("-", " ").replace("_", " ").lower()
                        if _needle and _needle in g.replace("-", " ").replace("_", " "):
                            _sub_hit = True
                if _sub_hit:
                    selected_subclasses.append(str(_sub_id))
                    selected_chain.extend(str(x) for x in (_sub_body.get("chain_addition") or []))
    except Exception:
        pc = None
        _menu_guard = {
            "version": "orchestration-menu-shallow-guard/v1",
            "error": "orchestration menu classification exception",
        }
    # `applicable` patterns that already sit on the default chain are not
    # also surfaced as "extra available" — keep the two sets disjoint.
    _default_chain = list(dict.fromkeys(selected_chain))
    _applicable = [p for p in dict.fromkeys(applicable_patterns)
                   if p not in _default_chain]
    # always_on patterns apply regardless of the selected problem_class —
    # carried as a distinct receipt field, never folded into the routed chain.
    _always_on = list(dict.fromkeys(always_on_patterns))
    _recurrence_risk = _has_recurrence_memory_risk(a.goal)
    steps.append(_step("orchestration_menu",
                        bool(pc and mtext),
                        {"problem_class": pc,
                         "sub_classes": selected_subclasses,
                         "selected_chain": _default_chain,
                         "applicable_patterns": _applicable,
                         "always_on_patterns": _always_on,
                         "surfaced_pattern_set": _default_chain + _applicable,
                         "class_scores": menu_scores,
                         "classification_guard": _menu_guard,
                         "policy_role": "compact_checked_execution_with_open_set_refusal",
                         "orchestration_active_controller_surface": [
                             "accepted_residual_class",
                             "source_cue_check_status",
                             "action_program",
                             "current_action_index",
                             "required_next_action",
                             "program_counter_rule",
                             "open_set_refusal_status",
                         ],
                         "outside_menu_action_program": [
                             "defer_to_new_residual_class",
                             "stop_or_repair",
                         ],
                         "open_set_refusal_status": "outside_menu" if pc == "outside_menu" else "in_menu",
                         "new_residual_class_candidate": _menu_guard.get("new_residual_class_candidate", ""),
                         "specific_outside_residual_class": _menu_guard.get("new_residual_class_candidate", ""),
                         "known_class_first_check": "shadow-only after H47; log proposed known class, outside candidate, cue checks, invariant result, final action, and later outcome before enforcing outside-specific expansion",
                         "source_contract_alignment_check": "required before accepting compact orchestration contracts",
                         "wrong_contract_repair_or_refusal": "if source_contract_alignment_check fails, repair/refuse before executing action_program",
                         "deterministic_lowering_result": "required; free-form action-program synthesis remains experimental-only",
                         "program_order_check": "verify action_program order against accepted_residual_class before execution",
                         "stop_condition_check": "verify terminal proceed/stop condition against accepted_residual_class before execution",
                         "orchestration_contract_gate": "src/ztare/research_director/orchestration_contract_gate.py",
                         "orchestration_contract_gate_cli": "python -m src.ztare.research_director.orchestration_contract_gate <contract.json> --source-facts-file <source.txt>",
                         "orchestration_shadow_log": "src/ztare/research_director/orchestration_shadow_log.py",
                         "orchestration_shadow_log_cli": "python -m src.ztare.research_director.orchestration_shadow_log <event.json> --append",
                         "evidence_basis": "H31-H47: labels are insufficient; corrected checked pipeline works; flat outside expansion can hurt in-menu accuracy; H44 program invariant gate catches subtle wrong contracts; H47 says naive known-first outside failover is not safe without drift evidence",
                         "recurrence_risk": _recurrence_risk,
                         "requires_project_memory_pairing": _recurrence_risk,
                         "evidence_note": (
                             "2026-05-24 menu evidence: deterministic memory_plus_menu screen was positive, "
                             "but live transparent-packet rerun did not show incremental gain"),
                         "menu_present": bool(mtext),
                         "menu_sha": _sha(mtext)}))

    # 3 — pattern / anti-pattern surfacing (the obligated chain).
    catr = REPO / "org" / "catalog_routing"
    pats, antis = [], []
    try:
        import yaml as _y
        for f in catr.glob("l*_activation.y*ml"):
            d = _y.safe_load(f.read_text(encoding="utf-8")) or []
            ids = [x.get("item_id") for x in d
                   if isinstance(x, dict) and x.get("item_id")]
            (antis if "l3" in f.name else pats).extend(ids)
    except Exception:
        pass
    steps.append(_step("pattern_antipattern",
                        bool(pats or antis),
                        {"patterns_available": pats[:20],
                         "antipatterns_to_check": antis[:20]}))

    # 3b — pattern action contract (research_log V97-V103 discipline).
    #      The catalog/menu step above proves availability. This step
    #      materializes the selected carrier contract: required carrier
    #      slots plus typed fields. It is substrate-agnostic and additive:
    #      close still accepts legacy carrier_artifacts, while the new
    #      carrier_schema_receipts mode can pay the schema directly.
    try:
        from dataclasses import asdict as _asdict  # noqa: PLC0415

        sys.path.insert(0, str(REPO))
        from src.ztare.research_director.pattern_action_contract import (  # noqa: E402
            build_pattern_action_contract as _build_pattern_action_contract,
        )

        _contract = _build_pattern_action_contract(
            scope=a.substrate,
            goal=a.goal,
        )
        _carriers = [
            {
                "name": c.name,
                "required": c.required,
                "artifact_slot": c.artifact_slot,
                "required_fields": list(c.required_fields),
                "schema_mode": c.schema_mode,
            }
            for c in _contract.evidence_carriers
        ]
        _contract_payload = _asdict(_contract)
        _contract_path = rdir / "pattern_action_contract.json"
        _contract_path.write_text(
            json.dumps(_contract_payload, indent=1, ensure_ascii=False),
            encoding="utf-8",
        )
        _pac_ok = bool(_contract.problem_surfaces and _contract.evidence_carriers)
        _pac_receipt = {
            "artifact": str(_contract_path.relative_to(REPO)),
            "problem_surfaces": _contract.problem_surfaces,
            "pattern_chain": _contract.pattern_chain[:12],
            "anti_patterns": _contract.anti_patterns[:12],
            "required_carriers": [
                c for c in _carriers if c["required"]
            ],
            "close_modes_supported": [
                "legacy: research_done.carrier_artifacts",
                "typed: research_done.carrier_schema_receipts",
            ],
            "why": (
                "Materializes the causal-edge/schema carrier before "
                "research starts; catalog labels alone are advisory."
            ),
        }
    except Exception as e:  # noqa: BLE001
        _pac_ok = False
        _pac_receipt = {
            "error": f"{type(e).__name__}: {e}",
            "why": "pattern action contract generation failed",
        }
    steps.append(_step("pattern_action_contract", _pac_ok, _pac_receipt))

    # 4 — (NS) residual graph / void-audit consume.
    #     COLD REVIEW bvs1b6d43 Angle 1 (self-caught: the E2E demo
    #     passed substrate "ns" and SILENTLY skipped this NS step).
    #     Fix: normalize the substrate; if the tick IS NS, the graph
    #     step is REQUIRED (no skip-pass). Only a genuinely non-NS
    #     substrate is honestly N/A.
    _sub = str(a.substrate).strip().lower()
    _is_ns = _sub in {"ns", "ns_millennium_hunt", "navier_stokes",
                      "navier-stokes", "nsm"} or "navier" in _sub
    if _is_ns:
        va = (REPO / "projects/ns_millennium_hunt/workspace/queries/"
              "ns_trackb_residual_void_audit.json")
        ids = []
        try:
            vd = json.loads(va.read_text(encoding="utf-8"))
            ids = list(vd.get("source_void_nodes", []))[:10]
            mincuts = [c[0] for c in vd.get("min_vertex_cuts", [])
                       if c]
        except Exception:
            mincuts = []
        steps.append(_step("ns_residual_graph",
                            bool(ids),
                            {"normalized_substrate": _sub,
                             "ns_required": True,
                             "source_void_nodes": ids,
                             "min_vertex_cuts": mincuts,
                             "consumes_surfaced_candidates": ids}))
    else:
        steps.append(_step("ns_residual_graph", True,
                            {"normalized_substrate": _sub,
                             "skipped": "genuinely non-NS substrate "
                             "(NS aliases are normalized + REQUIRED)"}))

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

    # 6 — GP-233 yield-decomposition (residual_to_lever).
    #     COLD REVIEW bvs1b6d43 Angle 1: "any file present passes" is
    #     vacuous. Tightened (no ledger-schema change — that owner/
    #     contract-bound rewrite is a specced residual, not a mid-
    #     session treadmill): require a residual_to_lever ledger with
    #     >=1 entry carrying a NON-EMPTY next_lever AND freshness
    #     (mtime within RESIDUAL_FRESH_DAYS) so a stale months-old
    #     artifact cannot satisfy this tick.
    import time as _time
    _rdir = REPO / "analytics/public/ledgers/residual_to_lever"
    RESIDUAL_FRESH_DAYS = 7
    _g233_ok = False
    _g233_why = "no residual_to_lever ledger dir"
    _fresh_levers = 0
    if _rdir.is_dir():
        _now_s = _time.time()
        for _lf in _rdir.glob("*.jsonl"):
            try:
                _age_d = (_now_s - _lf.stat().st_mtime) / 86400.0
                if _age_d > RESIDUAL_FRESH_DAYS:
                    continue
                for _ln in _lf.read_text(
                        encoding="utf-8").splitlines():
                    _ln = _ln.strip()
                    if not _ln:
                        continue
                    try:
                        _e = json.loads(_ln)
                    except Exception:
                        continue
                    if str(_e.get("next_lever", "")).strip():
                        _fresh_levers += 1
            except Exception:
                continue
        _g233_ok = _fresh_levers > 0
        _g233_why = (f"{_fresh_levers} fresh (<{RESIDUAL_FRESH_DAYS}d) "
                     f"entries with non-empty next_lever"
                     if _g233_ok else
                     "ledger dir present but NO fresh entry with a "
                     "non-empty next_lever (stale/empty ⇒ fail)")
    steps.append(_step("gp233_decomposition", _g233_ok,
                        {"fresh_next_lever_entries": _fresh_levers,
                         "fresh_window_days": RESIDUAL_FRESH_DAYS,
                         "why": _g233_why}))

    # 7 — structural-language op enumeration (META-PATTERN-022). The
    #     agent supplies concrete op-ids; the runner validates each
    #     against the deterministic universal_research_ops catalog:
    #     v5 move-layer ops plus meta-meta game-layer ops. Same anti-
    #     narration shape as the
    #     contract step: a checkable selection, not prose. Recorded
    #     into the manifest so the post-tick can verify the closure
    #     consumed the translation it claimed.
    uops = [o.strip() for o in str(a.universal_ops).split(",")
            if o.strip()]
    uop_valid, uop_unknown = [], []
    try:
        sys.path.insert(0, str(REPO))
        from src.ztare.research_director import (  # noqa: E402
            universal_research_ops as _uro)
        for o in uops:
            resolver = getattr(_uro, "get_structural_language_op", _uro.get)
            (uop_valid if resolver(o) is not None else uop_unknown).append(o)
        uro_ok = bool(uop_valid) and not uop_unknown
    except Exception as e:  # noqa: BLE001
        uro_ok = False
        uop_unknown = uops
        uop_valid = [f"__IMPORT_ERROR__ {type(e).__name__}"]
    steps.append(_step("universal_language_ops",
                        uro_ok,
                        {"ops_declared": uops,
                         "ops_valid": uop_valid,
                         "ops_unknown": uop_unknown,
                         "note": ("≥1 op-id must resolve in the "
                                  "deterministic v5/meta-meta catalog; "
                                  "unknown ids fail (META-PATTERN-022)")}))

    # 8 — 4-scope coverage (META-PATTERN-023): local/chain/recursive/
    #     meta must ALL be declared. Deterministic set check.
    _need = {"local", "chain", "recursive", "meta"}
    _have = {s.strip().lower() for s in str(a.scopes).split(",")
             if s.strip()}
    steps.append(_step("four_scope_coverage",
                        _need.issubset(_have),
                        {"scopes_declared": sorted(_have),
                         "scopes_required": sorted(_need),
                         "missing": sorted(_need - _have)}))

    # 9 — STRUCTURAL amnesia anchor (GP-241 #61). Substrate-AGNOSTIC:
    #     the runner contains ZERO substrate strings. It loads the
    #     org/structural_anchors/registry.yaml PLUGIN, looks up the
    #     entry for this substrate, and enforces the registry's own
    #     HARD RULE generically: the tick must NAME a residual_target
    #     that resolves (id OR alias) in that substrate's registered
    #     target set, the registered source_ref doc must exist, and
    #     the declared anchor traversal must include the registry's
    #     anchor_visit_required file (if it declares one). A substrate
    #     with no registry entry → honest N/A pass (mirrors step 4):
    #     it simply has not registered an anchor. All NS/Clay specifics
    #     live in the registry, not here.
    _reg_path = REPO / "org/structural_anchors/registry.yaml"
    _reg_entry = None
    try:
        import yaml as _ry  # noqa: E402
        _reg = _ry.safe_load(
            _reg_path.read_text(encoding="utf-8")) or {}
        for _k, _v in _reg.items():
            if not isinstance(_v, dict):
                continue
            _kl = str(_k).strip().lower()
            if _kl == _sub or _kl.startswith(_sub) or _sub in (
                    _kl.split("_")):
                _reg_entry = (_k, _v)
                break
    except Exception:
        _reg_entry = None
    if _reg_entry is None:
        steps.append(_step("structural_amnesia_anchor", True,
                            {"normalized_substrate": _sub,
                             "skipped": "substrate has no entry in "
                             "org/structural_anchors/registry.yaml "
                             "(no registered anchor ⇒ honest N/A)"}))
    else:
        _rk, _rv = _reg_entry
        _names = set()
        for _t in (_rv.get("targets") or []):
            if not isinstance(_t, dict):
                continue
            if _t.get("id"):
                _names.add(str(_t["id"]).strip())
            for _al in (_t.get("aliases") or []):
                _names.add(str(_al).strip())
        _decl = str(a.residual_target).strip()
        _tgt_ok = bool(_decl) and _decl in _names
        _src_ref = str(_rv.get("source_ref", "")).strip()
        _src_ok = bool(_src_ref) and (REPO / _src_ref).is_file()
        _need_visit = str(
            _rv.get("anchor_visit_required", "")).strip()
        _af = [x.strip() for x in str(a.anchor_files).split(",")
               if x.strip()]
        _af_missing = [f for f in _af
                       if not (REPO / f).is_file()
                       and not (REPO / "ztare_proofs" / f).is_file()]
        _visit_ok = (True if not _need_visit
                     else any(_need_visit in f
                              or f in _need_visit for f in _af))
        _struct_ok = (_tgt_ok and _src_ok and bool(_af)
                       and not _af_missing and _visit_ok)
        steps.append(_step("structural_amnesia_anchor", _struct_ok, {
            "registry_substrate": _rk,
            "residual_target": _decl,
            "registered_target_set": sorted(_names),
            "target_resolves": _tgt_ok,
            "source_ref": _src_ref,
            "source_ref_present": _src_ok,
            "anchor_visit_required": _need_visit or None,
            "anchor_files_declared": _af,
            "anchor_files_missing": _af_missing,
            "required_anchor_visited": _visit_ok,
            "why": ("PASS iff: residual_target ∈ registry id|alias "
                    "set AND source_ref doc present AND ≥1 declared "
                    "anchor file all-existing AND (registry's "
                    "anchor_visit_required, if any) among them — "
                    "structural, registry-driven, not lexical")}))

    # DAEMON-NAMESPACE BINDING (cold review bvs1b6d43, Angle 2 — a
    # correctness fix, not hardening). The GP-241 daemon freezes the
    # signed start row's `contract_id` as the COMPILER cid =
    # start_tick(goal).contract_id (sha256 of normalized goal +
    # catalog hashes + extractor version) — NOT the forecast-pool
    # slug. Binding manifest.contract_id to the slug compared two
    # different id-spaces ⇒ would false-quarantine EVERY honest
    # close. manifest.contract_id MUST be the recomputed compiler
    # cid so the daemon's `_mc == _sc` is same-namespace and
    # un-forgeable (it folds in goal + catalog + extractor version,
    # strictly stronger than goal-string equality). The forecast-pool
    # slug is kept separately as forecast_contract_id (step 5's own
    # check; never the daemon mutual-bind key).
    try:
        sys.path.insert(0, str(REPO))
        from src.ztare.surfacing.pre_tick_obligation_compiler import (  # noqa: E402
            start_tick as _start_tick)
        _compiler_cid = str(_start_tick(a.goal).contract_id)
    except Exception as e:  # noqa: BLE001
        _compiler_cid = f"__CID_RECOMPUTE_ERROR__ {type(e).__name__}"
        steps.append(_step("daemon_cid_binding", False,
                            {"error": _compiler_cid}))
    complete = all(s["ok"] for s in steps)
    manifest = {
        "tick_id": a.tick_id, "goal": a.goal,
        "substrate": a.substrate, "owner": a.owner,
        "contract_id": _compiler_cid,
        "forecast_contract_id": a.contract_id,
        "consumes_surfaced": this_consumes,
        "universal_ops": uops,
        "scopes": sorted(_have),
        "residual_target": str(a.residual_target).strip(),
        "anchor_files": [x.strip() for x in
                         str(a.anchor_files).split(",")
                         if x.strip()],
        "ts": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "authored_by": "agent",
        "trust_root": "operator_inspection (NOT operator-authored; "
                       "operator 2026-05-18)",
        "status": "COMPLETE" if complete else "INCOMPLETE",
        "steps": steps,
        "honest_bound": ("forces the pre-tick is EXECUTED via tool "
                         "receipts; does NOT certify insight depth — "
                         "that is operator inspection of this "
                         "manifest + human review of open-math."),
    }
    (rdir / "pretick_manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False),
        encoding="utf-8")
    # R2: register the manifest with the daemon (tamper-evident).
    # Only meaningful when COMPLETE (the daemon refuses a receipt for
    # an incomplete manifest). Fail-closed: COMPLETE but unreceipted
    # ⇒ RC=3 (the pre-tick is not done until the daemon has signed a
    # receipt binding the manifest hash; the close gate enforces it).
    _receipt_ok = False
    if complete:
        import base64 as _b64
        _mbytes = (rdir / "pretick_manifest.json").read_bytes()
        _rc, _ro = _run([PY, "-m", "src.ztare.gates.propose",
                         "--type", "manifest_receipt",
                         "--text", f"pretick manifest receipt {a.tick_id}",
                         "--goal", a.tick_id,
                         "--close", json.dumps(
                             {"tick_id": a.tick_id,
                              "manifest_kind": "pretick",
                              # F1 remote transport: carry the bytes so
                              # the daemon hashes what it RECEIVED, not
                              # a VPS-local path that never existed.
                              "manifest_b64": _b64.b64encode(
                                  _mbytes).decode("ascii")})],
                        timeout=180)
        _receipt_ok = (_rc == 0)
    print(json.dumps({"status": manifest["status"],
                       "manifest": str(
                           (rdir / "pretick_manifest.json"
                            ).relative_to(REPO)),
                       "receipt_registered": _receipt_ok,
                       "failed_steps": [s["step"] for s in steps
                                        if not s["ok"]]}, indent=1))
    # FAIL-CLOSED: COMPLETE manifest AND a daemon-signed receipt.
    if not complete:
        return 2
    return 0 if _receipt_ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
