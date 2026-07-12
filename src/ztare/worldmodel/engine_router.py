"""Engine router for GP-250 arc3_play_loop (hybrid mode).

Deterministic routing: reads receipts → emits engine decision → appends
workspace/engine_routing.jsonl.  No LLM calls; no promotion authority.

Receipt schema: ztare.engine_routing.v1

Routing table
─────────────
1. not has_champion OR not champion_explains_visible
   → autoresearch   (unshaped frontier or visible residual present: open science)

2. has_champion AND champion_explains_visible AND holdout_residual_bits > 0
   AND unresolved_disagreement_targets > 0
   → version_space / distinguishing_play  (play to disagreement targets)

3. has_champion AND champion_explains_visible AND holdout_residual_bits > 0
   AND population_collapsed (n_distinct_fingerprints <= 1)
   AND unresolved_disagreement_targets == 0
   → version_space / enumerate  (diversify population, then report)

4. has_champion AND champion_explains_visible AND holdout_residual_bits > 0
   AND NOT population_collapsed (n_distinct_fingerprints > 1 OR no vs ledger)
   AND stagnation < STAGNATION_THRESHOLD
   → specialists  (mechanism duel on witnessed frontier)

5. holdout_residual_bits == 0
   → closure_check  (no engine; emit receipt — closure candidate)

6. (fallback) stagnation >= STAGNATION_THRESHOLD AND no prior branch matched
   → autoresearch  (re-open science to break stagnation)
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

# Stagnation ceiling: at or above this count route back to autoresearch
# ponytail: constant, env-overridable; upgrade to per-project config if needed
_STAGNATION_THRESHOLD = int(os.environ.get("ZTARE_ROUTER_STAGNATION_THRESHOLD", "4"))

# Open-world escape: stagnation rounds needed to trigger hypothesis-class escape
# ponytail: separate from _STAGNATION_THRESHOLD; escape is a stronger signal
_ESCAPE_STAGNATION = int(os.environ.get("ZTARE_ESCAPE_STAGNATION", "3"))

# Livelock guard: K zero-reach attempts on a target → mark UNREACHABLE
# ponytail: env-overridable; upgrade to per-target config if needed
_TARGET_MAX_ATTEMPTS = int(os.environ.get("ZTARE_TARGET_MAX_ATTEMPTS", "2"))

# K-line prior kill-switch: ZTARE_KLINE_PRIOR=0 disables all prior influence
_KLINE_PRIOR_ENABLED = os.environ.get("ZTARE_KLINE_PRIOR", "1") != "0"

# Counterfactual audit cadence: every Nth prior application, record the
# counterfactual route (what would have been chosen WITHOUT the prior).
# Data only — no analysis here; analysis is a later card.
_KLINE_COUNTERFACTUAL_N = int(os.environ.get("ZTARE_KLINE_COUNTERFACTUAL_N", "5"))

# Tracks applications since last counterfactual record (module-level, survives
# within a process; resets at interpreter restart — intentional: per-run count).
_kline_prior_application_count = 0

# ── fix_class → engine bias map ───────────────────────────────────────────────
# Derived from the 9 fix_classes in projects/arc3_ls20_gov/workspace/k_lines.jsonl.
# Mapping is conceptual: which engine class is most suited to enact this fix?
#
# contract_surface_routing        → autoresearch  (routing contract redesign: re-open science)
# recategorize_cause_not_attribute → autoresearch  (category error: re-frame the science)
# targeted_evidence_acquisition   → version_space  (need to play to acquire specific evidence)
# residual_scaling_warmstart      → specialists    (residual warm-start: mechanism duel)
# clone_and_reuse_real_organ      → specialists    (run the real organ: specialist dispatch)
# typed_goal_category_contract    → specialists    (goal contract fix: specialist checks it)
# feedback_channel_audit_before_complexity_escalation → autoresearch (harness audit: re-open)
# gate_achievability_audit        → autoresearch   (gate is suspect: re-open science)
# goal_ontology_extension         → autoresearch   (goal space underdimensioned: re-open)
#
# ponytail: coarse; one fix_class may fit multiple engines. Bias-only, never
# overrides hard routing rules. Extend when new fix_classes enter the ledger.
_FIX_CLASS_ENGINE_MAP: dict[str, str] = {
    "contract_surface_routing": "autoresearch",
    "recategorize_cause_not_attribute": "autoresearch",
    "targeted_evidence_acquisition": "version_space",
    "residual_scaling_warmstart": "specialists",
    "clone_and_reuse_real_organ": "specialists",
    "typed_goal_category_contract": "specialists",
    "feedback_channel_audit_before_complexity_escalation": "autoresearch",
    "gate_achievability_audit": "autoresearch",
    "goal_ontology_extension": "autoresearch",
}


# ── Signal extraction ─────────────────────────────────────────────────────────


def _has_champion(project_dir: Path) -> bool:
    """True iff test_model.py AND at least one champion_materialization row exist."""
    if not (project_dir / "test_model.py").exists():
        return False
    cm = project_dir / "workspace" / "champion_materialization.jsonl"
    if not cm.exists():
        return False
    # at least one parseable row
    for line in cm.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip():
            try:
                json.loads(line)
                return True
            except Exception:  # noqa: BLE001
                pass
    return False


def _champion_explains_visible(project_dir: Path) -> bool:
    """True iff the champion has no wrong rows on the visible episode.

    Uses evidence_consolidation.build_row_bitmap — content-addressed, cheap.
    Returns False on any failure (safe: routes to autoresearch).
    """
    try:
        from ztare.worldmodel.evidence_consolidation import (
            build_row_bitmap,
            resolve_episode_paths,
        )
        champ = project_dir / "test_model.py"
        ep = resolve_episode_paths(project_dir).get("visible")
        if ep is None or not (champ.exists() and ep.exists()):
            return False
        bm = build_row_bitmap(champ, ep, project_dir=project_dir)
        return len(bm.get("wrong_rows", [])) == 0
    except Exception:  # noqa: BLE001
        return False


def _holdout_residual_bits(project_dir: Path) -> int:
    """Unexplained holdout steps (= holdout_total - champion_holdout_depth).

    Reuses width_allocator._unexplained_holdout_bits — single pricing door.
    Returns 0 when champion explains full holdout (closure candidate).
    """
    try:
        from ztare.common.width_allocator import _unexplained_holdout_bits
        bits, _total = _unexplained_holdout_bits(project_dir)
        return max(0, int(bits))
    except Exception:  # noqa: BLE001
        return 1   # unknown → assume residual present (safe: no false closure)


def _population_stats(project_dir: Path) -> dict:
    """Load version space survivors. Returns {n_survivors, n_distinct_fingerprints}.

    No ledger → both 0 (treated as no-ledger by route()).
    """
    try:
        from ztare.worldmodel.version_space import load as vs_load
        survivors = vs_load(project_dir)
        fps = {s.get("fingerprint") for s in survivors if s.get("fingerprint")}
        return {"n_survivors": len(survivors), "n_distinct_fingerprints": len(fps)}
    except Exception:  # noqa: BLE001
        return {"n_survivors": 0, "n_distinct_fingerprints": 0}


def _mark_target_unreachable(project_dir: Path, target_id: str) -> None:
    """Append a resolution row marking target_id as unreachable.

    Uses the same _RESOLUTION_FILE / schema as distinguishing_play._mark_resolved
    so that load_targets() automatically filters it out on next call.
    """
    # ponytail: import at call time to avoid circular import; this is rare path
    try:
        from ztare.worldmodel.distinguishing_play import _append_jsonl, _RESOLUTION_FILE, _RESOLUTION_SCHEMA  # type: ignore[attr-defined]
    except ImportError:
        _RESOLUTION_FILE = "distinguishing_play_resolved.jsonl"
        _RESOLUTION_SCHEMA = "ztare.distinguishing_play.resolution.v1"
        def _append_jsonl(path: Path, row: dict) -> None:  # type: ignore[misc]
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, default=str) + "\n")

    row = {
        "schema": _RESOLUTION_SCHEMA,
        "target_id": target_id,
        "resolution": "unreachable",
        "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
    }
    _append_jsonl(project_dir / "workspace" / _RESOLUTION_FILE, row)


def _resolve_unreachable_targets(project_dir: Path) -> None:
    """Scan distinguishing_play.jsonl session rows; mark any target with
    >= _TARGET_MAX_ATTEMPTS zero-reach sessions as UNREACHABLE.

    A zero-reach session: target appears in targets_attempted but NOT in
    targets_reached for that session row.  Counts are per-target across ALL
    session rows (not per-session).
    """
    session_file = project_dir / "workspace" / "distinguishing_play.jsonl"
    if not session_file.exists():
        return

    # tally per target_id: {target_id: {attempted, reached}}
    counts: dict[str, dict[str, int]] = {}
    for line in session_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        reached_in_row: set[str] = set()
        for entry in row.get("targets_reached") or []:
            tid = entry.get("target_id")
            if tid:
                reached_in_row.add(str(tid))
        for entry in row.get("targets_attempted") or []:
            tid = entry.get("target_id")
            if not tid:
                continue
            tid = str(tid)
            rec = counts.setdefault(tid, {"attempted": 0, "reached": 0})
            rec["attempted"] += 1
            if tid in reached_in_row:
                rec["reached"] += 1

    # collect already-resolved target ids so we don't double-mark
    resolved_file = project_dir / "workspace" / "distinguishing_play_resolved.jsonl"
    already_resolved: set[str] = set()
    if resolved_file.exists():
        for line in resolved_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                tid = row.get("target_id")
                if tid:
                    already_resolved.add(str(tid))
            except Exception:  # noqa: BLE001
                pass

    for tid, rec in counts.items():
        if tid in already_resolved:
            continue
        if rec["reached"] == 0 and rec["attempted"] >= _TARGET_MAX_ATTEMPTS:
            _mark_target_unreachable(project_dir, tid)


def _unresolved_disagreement_targets(project_dir: Path) -> int:
    """Count unresolved disagreement targets from version_space_disagreements.jsonl
    minus the resolution ledger in distinguishing_play.

    Pre-step: mark any target attempted K times with 0 reaches as UNREACHABLE
    (livelock guard — prevents infinite routing to an unreachable target).

    Reuses distinguishing_play.load_targets — already does the subtraction.
    """
    # Livelock guard: resolve stuck targets before counting live ones
    try:
        _resolve_unreachable_targets(project_dir)
    except Exception:  # noqa: BLE001
        pass
    try:
        from ztare.worldmodel.distinguishing_play import load_targets
        return len(load_targets(project_dir))
    except Exception:  # noqa: BLE001
        return 0


def _stagnation(project_dir: Path) -> int:
    """Consecutive non-promotion runs (reuses width_allocator._stagnation)."""
    try:
        from ztare.common.width_allocator import _stagnation as _stag
        return int(_stag(project_dir))
    except Exception:  # noqa: BLE001
        return 0


def _unreachable_targets(project_dir: Path) -> bool:
    """True iff every unresolved distinguishing target has been attempted at least
    once but accumulated zero observations across ALL session rows.

    Reads workspace/distinguishing_play.jsonl to find per-target observation
    counts (targets_reached is the already-filtered list of targets that produced
    ≥1 observation; targets_attempted lists everything tried). A target is
    'unreachable' when it appears in targets_attempted across ≥1 sessions but
    never appears in any targets_reached.

    Returns False (safe: no escape) when the ledger is missing or no unresolved
    targets exist.
    """
    try:
        # PERSISTED unreachability: a target RESOLVED as unreachable is the
        # strongest escape evidence — it must not be consumed by its own
        # resolution (run-11 lesson: the livelock fix cleared the unresolved
        # set, which zeroed this signal and starved the escape a second time).
        res_file = project_dir / "workspace" / "distinguishing_play_resolved.jsonl"
        if res_file.exists():
            import json as _json
            for line in res_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    if _json.loads(line).get("resolution") == "unreachable":
                        return True
                except Exception:  # noqa: BLE001
                    pass

        from ztare.worldmodel.distinguishing_play import load_targets
        unresolved = {t["_target_id"] for t in load_targets(project_dir)}
        if not unresolved:
            return False

        session_file = project_dir / "workspace" / "distinguishing_play.jsonl"
        if not session_file.exists():
            return False

        attempted: set[str] = set()
        reached: set[str] = set()
        for line in session_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            for entry in row.get("targets_attempted") or []:
                tid = entry.get("target_id")
                if tid:
                    attempted.add(str(tid))
            for entry in row.get("targets_reached") or []:
                tid = entry.get("target_id")
                if tid:
                    reached.add(str(tid))

        # All unresolved targets must have been attempted AND never reached
        return (
            unresolved.issubset(attempted)
            and unresolved.isdisjoint(reached)
        )
    except Exception:  # noqa: BLE001
        return False


def _last_enumeration_futile(project_dir, current_n_fp: int) -> bool:
    """True when the most recent enumeration run added no new distinct
    fingerprints to the population (receipts: population_enumeration.jsonl)."""
    import json as _json
    from pathlib import Path as _Path
    p = _Path(project_dir) / "workspace" / "population_enumeration.jsonl"
    if not p.exists():
        return False
    last = None
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line:
            try:
                last = _json.loads(line)
            except Exception:  # noqa: BLE001
                pass
    if not last:
        return False
    # futile = the enumeration ran but the version-space distinct-fingerprint
    # count did not grow beyond what routing currently sees
    vs_fp = last.get("vs_distinct_fingerprints")
    return isinstance(vs_fp, int) and vs_fp <= max(1, current_n_fp)


def _signature_from_state(state: dict) -> dict:
    """Map router knowledge-state signals to the 6-axis K-line signature.

    HONEST MAPPING NOTES (coarsest parts documented with 'unknown' fallback):

    warrant_stratum: derived from champion existence + residual.
      has_champion=False → "visible" (we haven't cleared visible yet)
      hrb==0 → "holdout" (no visible residual, broke at holdout)
      otherwise → "holdout" (champion explains visible, fighting holdout)
      CAVEAT: "transfer" is never reachable from router signals alone.

    contradiction_topology: UNMAPPABLE from router signals.
      Router sees component counts in version space, not witness-hypergraph
      component counts. Filed as "unknown" always.

    residual_localization: UNMAPPABLE — router has no divergent-cell adjacency.
      Filed as "unknown" always.

    input_conditionality: partially inferred from unresolved_disagreement_targets.
      udt > 0 implies action-conditioned disagreement → "mixed"
      else "uniform" (coarse: stagnation could hide mixed; acceptable bias risk)

    regime_position: inferred from escape_unreachable signal.
      escape_unreachable=True → we're at a regime boundary (class misspecified)
      else "interior"

    epistemic_state: mapped from stagnation + population collapse.
      stagnation==0 and n_fp>1 → "diverse"
      stagnation==0 and n_fp<=1 → "collapsed-0"
      stagnation in [1,3] → "collapsed-1-3"  (coarse: stagnation!=elimination count)
      stagnation>=4 → "collapsed-4+"
    """
    hc = state.get("has_champion", False)
    hrb = state.get("holdout_residual_bits", 1)
    udt = state.get("unresolved_disagreement_targets", 0)
    stag = state.get("stagnation", 0)
    ps = state.get("population_stats") or {}
    n_fp = ps.get("n_distinct_fingerprints", 0)
    escape = state.get("escape_unreachable", False)

    # warrant_stratum
    if not hc:
        ws = "visible"
    elif hrb == 0:
        ws = "holdout"  # at closure boundary
    else:
        ws = "holdout"

    # input_conditionality
    ic = "mixed" if udt > 0 else "uniform"

    # regime_position
    rp = "boundary" if escape else "interior"

    # epistemic_state (ponytail: stagnation≠elimination count; acceptable coarseness)
    if stag == 0 and n_fp > 1:
        es = "diverse"
    elif stag == 0:
        es = "collapsed-0"
    elif stag <= 3:
        es = "collapsed-1-3"
    else:
        es = "collapsed-4+"

    return {
        "warrant_stratum": ws,
        "contradiction_topology": "unknown",   # unmappable from router signals
        "residual_localization": "unknown",     # unmappable from router signals
        "input_conditionality": ic,
        "regime_position": rp,
        "epistemic_state": es,
    }


def _write_open_world_brief(project_dir: Path, signals: dict) -> None:
    """Append one row to workspace/open_world_brief.jsonl as the receipt-seam."""
    ws = project_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "ztare.open_world_brief.v1",
        "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "trigger_signals": signals,
        "instruction": (
            "propose NEW state variables or law FORMS outside the current carrier "
            "vocabulary; the current class is suspected misspecified"
        ),
    }
    with (ws / "open_world_brief.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


# ── Public API ────────────────────────────────────────────────────────────────


def _refresh_challenger_portfolio(project_dir: Path) -> None:
    """Wire challenger_portfolio into the routing preamble.

    Calls refresh() then propose_distinguishing_targets() so that portfolio-sourced
    disagreement targets exist in version_space_disagreements.jsonl BEFORE routing
    counts unresolved_disagreement_targets.  Failure is non-fatal (safe: routing
    proceeds without portfolio targets).
    """
    try:
        from ztare.worldmodel.challenger_portfolio import (
            refresh as _cp_refresh,
            propose_distinguishing_targets as _cp_propose,
        )
        _cp_refresh(project_dir)
        _cp_propose(project_dir)
    except Exception:  # noqa: BLE001
        pass


def knowledge_state(project_dir: "str | Path") -> dict:
    """Compute all receipt-derived routing signals for project_dir.

    Preamble: refreshes the challenger portfolio so portfolio-sourced
    disagreement targets are populated before routing counts them.

    Returns:
        has_champion: bool
        champion_explains_visible: bool
        holdout_residual_bits: int
        population_stats: {n_survivors, n_distinct_fingerprints}
        unresolved_disagreement_targets: int
        stagnation: int
        escape_unreachable: bool  (unresolved targets attempted but never reached)
        _ledger_exists: bool  (version_space.jsonl present)
        _current_signature: dict  (6-axis K-line signature mapped from signals)
        _routing_prior: dict|None  (K-line forward-edge prior, or None)
    """
    project_dir = Path(project_dir).resolve()

    # Portfolio preamble: ensure challenger targets exist before routing
    _refresh_challenger_portfolio(project_dir)

    hc = _has_champion(project_dir)
    cev = _champion_explains_visible(project_dir) if hc else False
    hrb = _holdout_residual_bits(project_dir)
    ps = _population_stats(project_dir)
    udt = _unresolved_disagreement_targets(project_dir)
    stag = _stagnation(project_dir)
    ledger_exists = (project_dir / "workspace" / "version_space.jsonl").exists()
    escape_unreachable = _unreachable_targets(project_dir)
    enumeration_futile = _last_enumeration_futile(
        project_dir, (ps or {}).get("n_distinct_fingerprints", 0)
    )

    base_state = {
        "has_champion": hc,
        "champion_explains_visible": cev,
        "holdout_residual_bits": hrb,
        "population_stats": ps,
        "unresolved_disagreement_targets": udt,
        "stagnation": stag,
        "escape_unreachable": escape_unreachable,
        "enumeration_futile": enumeration_futile,
        "_ledger_exists": ledger_exists,
    }

    # K-line forward edge: compute signature + prior (non-fatal; never blocks routing)
    current_sig = _signature_from_state(base_state)
    prior: "dict | None" = None
    if _KLINE_PRIOR_ENABLED:
        try:
            from ztare.common.k_line import routing_prior as _routing_prior
            prior = _routing_prior(project_dir, current_sig)
        except Exception:  # noqa: BLE001
            pass  # prior is advisory; failure must never block routing

    base_state["_current_signature"] = current_sig
    base_state["_routing_prior"] = prior
    return base_state


def route(state: dict) -> dict:
    """Deterministic routing from receipt signals.

    Returns {"engine": str, "phase": str|None, "reason": str}.
    Engine values: "autoresearch" | "specialists" | "version_space" | "closure_check"

    K-LINE FORWARD EDGE: The state may carry _routing_prior (from knowledge_state).
    The prior biases only the DEFAULT/TIE branches (branches 4 and 6) — it never
    overrides a hard routing rule (branches 0–3, 5).  When a hard rule fires,
    the decision carries _overridden_by_rule=True in metadata so the prior receipt
    can record it.
    """
    hc = state["has_champion"]
    cev = state["champion_explains_visible"]
    hrb = state["holdout_residual_bits"]
    ps = state["population_stats"]
    udt = state["unresolved_disagreement_targets"]
    stag = state["stagnation"]
    ledger_exists = state.get("_ledger_exists", False)
    escape_unreachable = state.get("escape_unreachable", False)

    n_fp = ps.get("n_distinct_fingerprints", 0)
    population_collapsed = ledger_exists and n_fp <= 1

    # Extract prior (advisory only; may be None or disabled)
    prior = state.get("_routing_prior")  # dict|None
    prior_engine = (
        _FIX_CLASS_ENGINE_MAP.get(prior["fix_class"])
        if prior and isinstance(prior, dict) and prior.get("fix_class")
        else None
    )

    # Branch 0 — open-world escape: hypothesis class is suspected misspecified.
    # Fires when the version space is collapsed (or all survivors share one
    # fingerprint) AND stagnation has crossed the escape threshold AND every
    # unresolved distinguishing target has been attempted but never reached —
    # meaning the current play machinery cannot generate new evidence even with
    # a functioning distinguishing plan.
    # Escape trigger is TWO-PATH because stagnation's only writer is the
    # materializer, which the very failure modes this branch guards against
    # can silence (run-10 livelock: 13/13 distinguishing routes, stagnation
    # frozen at 2, escape unreachable forever). Path 2 = enumeration
    # futility: we enumerated, nothing new joined the population, and the
    # distinguishing targets are unreachable — class suspect regardless of
    # the frozen counter. A progress metric must never depend solely on
    # writers that failure modes can silence.
    enum_futile = state.get("enumeration_futile", False)
    if (
        hc and cev and hrb > 0
        and (population_collapsed or n_fp <= 1)
        and (stag >= _ESCAPE_STAGNATION or enum_futile)
        and escape_unreachable
    ):
        reason = (
            f"hypothesis-class escape: population_collapsed={population_collapsed}, "
            f"n_distinct_fingerprints={n_fp}, stagnation={stag}>={_ESCAPE_STAGNATION}, "
            f"distinguishing targets unresolved-but-unreachable; "
            f"current hypothesis class is suspected misspecified"
        )
        return {
            "engine": "autoresearch",
            "phase": "open_world",
            "reason": reason,
            "_overridden_by_rule": True,
        }

    # Branch 1 — open science: no valid champion or champion still mispredicts visible
    if not hc or not cev:
        reason = (
            "no champion" if not hc
            else "champion mispredicts visible episode"
        )
        return {
            "engine": "autoresearch",
            "phase": None,
            "reason": f"autoresearch: {reason}",
            "_overridden_by_rule": True,
        }

    # Branch 5 — closure candidate: zero unexplained holdout bits
    if hrb == 0:
        return {
            "engine": "closure_check",
            "phase": None,
            "reason": "closure_check: holdout_residual_bits==0; full closure gates required",
            "_overridden_by_rule": True,
        }

    # Champion explains visible, residual > 0 — now discriminate by population shape

    # Branch 2 — distinguishing play: unresolved disagreement targets exist
    if udt > 0:
        return {
            "engine": "version_space",
            "phase": "distinguishing_play",
            "reason": (
                f"version_space/distinguishing_play: {udt} unresolved disagreement "
                f"targets; play to resolve population before enumerate"
            ),
            "_overridden_by_rule": True,
        }

    # Branch 3 — enumerate: population is behaviorally collapsed (monoculture)
    if population_collapsed:
        return {
            "engine": "version_space",
            "phase": "enumerate",
            "reason": (
                f"version_space/enumerate: champion perfect on visible; "
                f"population collapsed (n_distinct_fingerprints={n_fp}); "
                f"diversify before distinguishing-play can prune"
            ),
            "_overridden_by_rule": True,
        }

    # Branch 4 — specialists: distinct mechanisms exist to duel on frontier
    # K-LINE BIAS: prior may promote this branch or demote to fallback.
    # If prior says "specialists" and we're in the default window (stag<threshold),
    # run specialists first with budget +1 (budget_bonus field in receipt).
    if not ledger_exists or n_fp > 1:
        if stag < _STAGNATION_THRESHOLD:
            decision: dict = {
                "engine": "specialists",
                "phase": None,
                "reason": (
                    f"specialists: champion explains visible; holdout_residual_bits={hrb}; "
                    f"n_distinct_fingerprints={n_fp}; stagnation={stag} < {_STAGNATION_THRESHOLD}; "
                    f"mechanism duel on witnessed frontier"
                ),
                "_overridden_by_rule": False,
            }
            # Apply prior bias: if prior agrees (specialists), add budget bonus
            if prior_engine == "specialists":
                decision["budget_bonus"] = 1
                decision["reason"] += f"; kline_prior={prior['fix_class']} agrees"
            elif prior_engine is not None:
                # Prior disagrees but hard rule chose specialists; note it
                decision["reason"] += f"; kline_prior={prior['fix_class']} suggested {prior_engine} (overridden by rule)"
            return decision

    # Branch 6 — fallback: stagnation threshold crossed or unexpected state
    # K-LINE BIAS: if prior maps to a specific engine, try it first (order bias).
    # This is the only branch where prior can actually change the engine chosen.
    # Prior still cannot override: if prior_engine == "closure_check" we ignore it
    # (that engine has hard preconditions); we only allow autoresearch / specialists /
    # version_space as prior overrides at the fallback.
    _BIASABLE_ENGINES = {"autoresearch", "specialists", "version_space"}
    if prior_engine in _BIASABLE_ENGINES:
        return {
            "engine": prior_engine,
            "phase": None,
            "reason": (
                f"kline_prior_bias: fallback biased to {prior_engine} "
                f"by fix_class={prior['fix_class']} (support={prior['support']}); "
                f"stagnation={stag}>={_STAGNATION_THRESHOLD}"
            ),
            "_overridden_by_rule": False,
        }

    return {
        "engine": "autoresearch",
        "phase": None,
        "reason": (
            f"autoresearch: stagnation={stag} >= {_STAGNATION_THRESHOLD} "
            f"or no routing branch matched; re-open science"
        ),
        "_overridden_by_rule": False,
    }


def _append_routing_receipt(
    project_dir: Path,
    state: dict,
    decision: dict,
) -> None:
    ws = project_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "ztare.engine_routing.v1",
        "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "signals": {k: v for k, v in state.items() if not k.startswith("_")},
        "engine": decision["engine"],
        "phase": decision.get("phase"),
        "reason": decision["reason"],
    }
    with (ws / "engine_routing.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def execute(
    engine_decision: dict,
    project_dir: "str | Path",
    env: "dict | None" = None,
) -> "dict | None":
    """Thin dispatcher: run the routed engine inside a phase_timing span.

    "autoresearch" → returns sentinel {"autoresearch": True}; caller
      drives its existing governed-loop path unchanged.
    "closure_check" → returns {"closure_check": True}; no engine launched.
    "version_space"/enumerate → enumerate_population(project_dir)
    "version_space"/distinguishing_play → run_distinguishing_session(project_dir)
    "specialists" → run_specialists(project_dir)
    """
    project_dir = Path(project_dir).resolve()
    ws = project_dir / "workspace"
    engine = engine_decision["engine"]
    phase_val = engine_decision.get("phase")

    from ztare.common.phase_timing import phase as _phase

    if engine == "autoresearch":
        return {"autoresearch": True}

    if engine == "closure_check":
        return {"closure_check": True}

    if engine == "version_space":
        if phase_val == "enumerate":
            with _phase("engine.version_space.enumerate", ws):
                from ztare.worldmodel.population_enumerator import enumerate_population
                return enumerate_population(project_dir)
        else:
            # distinguishing_play (default for version_space non-enumerate)
            with _phase("engine.version_space.distinguishing_play", ws):
                from ztare.worldmodel.distinguishing_play import run_distinguishing_session
                receipt = run_distinguishing_session(project_dir)
                # SessionReceipt is a dataclass; convert to dict for uniform return
                return (receipt.__dict__ if hasattr(receipt, "__dict__")
                        else {"result": str(receipt)})

    if engine == "specialists":
        with _phase("engine.specialists", ws):
            from ztare.worldmodel.residual_specialists import run_specialists
            return run_specialists(project_dir)

    return {"error": f"unknown engine: {engine}"}


# ── Convenience: state + route + log in one call ───────────────────────────────


def _append_prior_receipt(
    project_dir: Path,
    signature: dict,
    prior: "dict | None",
    decision: dict,
    counterfactual_decision: "dict | None",
) -> None:
    """Append one row to workspace/router_prior_receipts.jsonl.

    Emitted every time a prior exists (applied or not) — silent priors are
    unauditable.  Includes counterfactual_decision when cadence fires.
    """
    global _kline_prior_application_count  # noqa: PLW0603

    applied = prior is not None and not decision.get("_overridden_by_rule", False)
    overridden = prior is not None and decision.get("_overridden_by_rule", False)

    if applied:
        _kline_prior_application_count += 1

    row: dict = {
        "schema": "ztare.kline_routing_prior.v1",
        "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "signature": signature,
        "prior": prior,
        "applied": applied,
        "overridden_by_rule": overridden,
        "chosen_engine": decision.get("engine"),
        "chosen_phase": decision.get("phase"),
    }
    if counterfactual_decision is not None:
        row["prior_choice"] = decision.get("engine")
        row["counterfactual_choice"] = counterfactual_decision.get("engine")
        row["diverged"] = decision.get("engine") != counterfactual_decision.get("engine")

    ws = project_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    with (ws / "router_prior_receipts.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def decide(project_dir: "str | Path") -> "tuple[dict, dict]":
    """Compute knowledge_state, route, append receipt. Returns (state, decision)."""
    global _KLINE_PRIOR_ENABLED, _KLINE_COUNTERFACTUAL_N, _kline_prior_application_count  # noqa: PLW0603

    # Re-read kill-switch each call (allows runtime env changes in tests)
    kline_prior_active = os.environ.get("ZTARE_KLINE_PRIOR", "1") != "0"
    counterfactual_n = int(os.environ.get("ZTARE_KLINE_COUNTERFACTUAL_N", "5"))

    project_dir = Path(project_dir).resolve()
    state = knowledge_state(project_dir)
    decision = route(state)
    _append_routing_receipt(project_dir, state, decision)

    if decision.get("engine") == "autoresearch" and decision.get("phase") == "open_world":
        _write_open_world_brief(project_dir, {
            k: v for k, v in state.items() if not k.startswith("_")
        })

    # K-line prior receipt: emit whenever a prior exists
    prior = state.get("_routing_prior")
    if prior is not None and kline_prior_active:
        # Counterfactual audit: every Nth application, route without the prior
        counterfactual_decision: "dict | None" = None
        applied = not decision.get("_overridden_by_rule", False)
        if applied:
            _kline_prior_application_count += 1
            if _kline_prior_application_count % counterfactual_n == 0:
                # Route a state copy with prior stripped
                state_no_prior = dict(state, _routing_prior=None)
                counterfactual_decision = route(state_no_prior)

        _append_prior_receipt(
            project_dir,
            state.get("_current_signature", {}),
            prior,
            decision,
            counterfactual_decision,
        )

    return state, decision
