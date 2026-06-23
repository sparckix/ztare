"""Research Director live frontier runner (RD-1.12, 2026-05-02).

Watches project artifacts and emits typed events for the iter_action_policy
dispatcher. This module owns the DETECTION layer; iter_action_policy.py
owns the WHAT-TO-DO-WHEN layer; iter_action_executor.py owns the
HOW-TO-EXECUTE-IT layer. Three modules, three responsibilities.

Watched artifacts per project:

    projects/<slug>/workspace/eval_history.jsonl       — per-iter eval results
    projects/<slug>/latest_eval_results.json           — current eval snapshot
    projects/<slug>/latest_probability_dag.json        — current DAG
    projects/<slug>/debate_log_iter_*.md               — judge debate logs
    projects/<slug>/history/<ts>_iter*_score_*.md      — promoted iter snapshots
    projects/<slug>/verified_axioms.json               — verified axioms (RD trigger)
    projects/<slug>/workspace/skeptic_verdict.md       — skeptic verdict (RD output)

Detected events (emitted to dispatch_event):

    obstruction_detected            — same gate fails N consecutive iters
    verified_axiom_emitted          — new axiom in verified_axioms.json
    native_route_collapse           — route's native claim refuted
    champion_promoted               — new champion outranks old
    gate_failed                     — specific gate failed (with name)
    stagnation_detected             — N consecutive zero-scores
    budget_warn_threshold_tripped   — spend or utilization warn fired

The runner is IDEMPOTENT: it advances frontier_state.last_iter_observed
each tick so the same event is never emitted twice.

Usage from agent_daemon.py tick:
    from ztare.role_extensions.frontier_runner import scan_project
    events = scan_project("gp154_inversion_alpha_from_dimension")
    for ev in events:
        from ztare.role_extensions.iter_action_policy import dispatch_event
        dispatch_event(ev)
"""
from __future__ import annotations

import glob
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from ztare.role_extensions import frontier_state as fs

log = logging.getLogger(__name__)

PROJECTS_ROOT = Path("projects")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_eval_history(project_dir: Path) -> list[dict]:
    """Parse workspace/eval_history.jsonl into list of iter records."""
    p = project_dir / "workspace" / "eval_history.jsonl"
    if not p.exists():
        return []
    rows: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return rows


def _read_latest_eval(project_dir: Path) -> Optional[dict]:
    p = project_dir / "latest_eval_results.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _read_verified_axioms(project_dir: Path) -> list[dict]:
    p = project_dir / "verified_axioms.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return list(data.get("axioms") or [])
        if isinstance(data, list):
            return data
    except Exception:  # noqa: BLE001
        return []
    return []


def _detect_iter_score_history(eval_history: list[dict]) -> list[dict]:
    """Sort + dedup by iteration; latest entry per iter wins. Returns
    chronologically-ordered list of {iteration, score, parametric_form,
    weakest_point, gate_verdicts, timestamp}."""
    by_iter: dict[int, dict] = {}
    for row in eval_history:
        try:
            n = int(row.get("iteration"))
        except (TypeError, ValueError):
            continue
        prev = by_iter.get(n)
        # Prefer the entry with the latest timestamp.
        if prev is None or str(row.get("timestamp", "")) > str(prev.get("timestamp", "")):
            by_iter[n] = row
    return [by_iter[k] for k in sorted(by_iter.keys())]


def _extract_gate_failures(row: dict) -> list[str]:
    """Pull the names of any gates that failed in this iter from
    weakest_point text + gate_verdicts dict."""
    failed: list[str] = []
    gv = row.get("gate_verdicts") or {}
    if isinstance(gv, dict):
        for name, verdict in gv.items():
            if isinstance(verdict, dict) and verdict.get("passed") is False:
                failed.append(str(name))
    weakest = (row.get("weakest_point") or "").upper()
    # Some gate names are mentioned in prose (e.g. "AMBIENT-CONTROL FAILED")
    for known in ("AMBIENT_CONTROL", "AMBIENT-CONTROL", "HOLDOUT", "FARTHER_TAIL",
                  "PSLQ_CONSTANT_RECOVERY", "KEPLER_BASELINE_BEAT"):
        if known in weakest and known.replace("-", "_") not in failed:
            failed.append(known.replace("-", "_"))
    return failed


# ── Detection passes ────────────────────────────────────────────────

def _detect_obstructions(history: list[dict],
                          last_seen: Optional[int]) -> list[dict]:
    """Emit obstruction_detected events when a gate fails twice consecutively
    on the SAME route. We don't currently have an explicit route_id per iter
    in eval_history, so for now we use 'gate_<name>' as a proxy route key.
    """
    events: list[dict] = []
    consecutive: dict[str, int] = {}
    for row in history:
        n = row.get("iteration")
        if last_seen is not None and isinstance(n, int) and n <= last_seen:
            # Still walk it to keep the consecutive counters warm; just
            # don't emit (avoid duplicate events).
            walk_only = True
        else:
            walk_only = False
        failed = _extract_gate_failures(row)
        for gate in failed:
            consecutive[gate] = consecutive.get(gate, 0) + 1
        # Reset gates that didn't fail this iter
        for gate in list(consecutive.keys()):
            if gate not in failed:
                consecutive[gate] = 0
        # Emit if any gate hit ≥2 consecutive AND we're past last_seen
        if not walk_only:
            for gate, count in consecutive.items():
                if count >= 2:
                    events.append({
                        "kind": "obstruction_detected",
                        "iter_index": n,
                        "route_id": f"gate_{gate}",
                        "gate_name": gate,
                        "consecutive_count": count,
                        "ts": _utc_now_iso(),
                    })
    return events


def _detect_stagnation(history: list[dict],
                        last_seen: Optional[int]) -> list[dict]:
    """Emit stagnation_detected when ≥3 consecutive iters score 0."""
    events: list[dict] = []
    streak = 0
    for row in history:
        n = row.get("iteration")
        score = row.get("score")
        try:
            score_num = int(score) if score is not None else None
        except (TypeError, ValueError):
            score_num = None
        if score_num == 0:
            streak += 1
        else:
            streak = 0
        if streak >= 3 and (last_seen is None or (isinstance(n, int) and n > last_seen)):
            events.append({
                "kind": "stagnation_detected",
                "iter_index": n,
                "consecutive_zeros": streak,
                "ts": _utc_now_iso(),
            })
    return events


def _detect_gate_repeats(history: list[dict],
                          last_seen: Optional[int]) -> list[dict]:
    """Emit gate_failed events tagged with gate_name + consecutive_count.
    Distinct from obstruction_detected because this fires per individual
    gate failure regardless of "obstruction" framing."""
    events: list[dict] = []
    consec: dict[str, int] = {}
    for row in history:
        n = row.get("iteration")
        failed = _extract_gate_failures(row)
        for gate in failed:
            consec[gate] = consec.get(gate, 0) + 1
        for gate in list(consec.keys()):
            if gate not in failed:
                consec[gate] = 0
        if last_seen is not None and isinstance(n, int) and n <= last_seen:
            continue
        for gate, count in consec.items():
            if count > 0:
                events.append({
                    "kind": "gate_failed",
                    "iter_index": n,
                    "gate_name": gate,
                    "consecutive_count": count,
                    "ts": _utc_now_iso(),
                })
    return events


def _detect_verified_axioms(project_dir: Path,
                             last_seen_axiom_count: int) -> tuple[list[dict], int]:
    """Emit verified_axiom_emitted for each new axiom since last scan.
    Returns (events, new_total_count)."""
    axioms = _read_verified_axioms(project_dir)
    new_total = len(axioms)
    if new_total <= last_seen_axiom_count:
        return [], new_total
    events: list[dict] = []
    for axiom in axioms[last_seen_axiom_count:]:
        events.append({
            "kind": "verified_axiom_emitted",
            "axiom_label": axiom.get("label") or axiom.get("id"),
            "axiom_statement": axiom.get("statement", "")[:500],
            "external_consistency_checks_present": bool(axiom.get("external_consistency_checks")),
            "ts": _utc_now_iso(),
        })
    return events, new_total


def _detect_champion_promotion(history: list[dict],
                                state: fs.FrontierState) -> list[dict]:
    """Emit champion_promoted when the highest-scored iter in history is
    different from the prior champion AND has a non-zero score."""
    if not history:
        return []
    best = max(history, key=lambda r: r.get("score") or 0)
    best_score = best.get("score") or 0
    if best_score <= 0:
        return []
    best_form = best.get("parametric_form") or ""
    if state.champion_meaning and best_form == state.champion_meaning:
        return []
    return [{
        "kind": "champion_promoted",
        "iter_index": best.get("iteration"),
        "score": best_score,
        "parametric_form": best_form[:300],
        "ts": _utc_now_iso(),
    }]


# ── Public entry point ─────────────────────────────────────────────

def scan_project(project_slug: str,
                 *, project_dir: Optional[Path] = None) -> list[dict]:
    """Run all detection passes for one project; emit events; advance
    the iteration cursor. Returns list of fresh events emitted this scan
    (NOT accumulated history).

    Idempotent: subsequent scans will not re-emit already-seen iters.
    """
    fs._validate_slug(project_slug)
    if project_dir is None:
        project_dir = PROJECTS_ROOT / project_slug
    if not project_dir.exists():
        log.debug("scan_project: %s does not exist; nothing to scan", project_dir)
        return []

    state = fs.load_state(project_slug)
    last_seen = state.last_iter_observed
    last_seen_axioms = sum(
        1 for h in state.history if h.get("event") == "verified_axiom_emitted"
    )

    eval_history = _read_eval_history(project_dir)
    history = _detect_iter_score_history(eval_history)

    events: list[dict] = []
    events.extend(_detect_obstructions(history, last_seen))
    events.extend(_detect_stagnation(history, last_seen))
    events.extend(_detect_gate_repeats(history, last_seen))
    events.extend(_detect_champion_promotion(history, state))
    axiom_events, _new_axiom_total = _detect_verified_axioms(project_dir, last_seen_axioms)
    events.extend(axiom_events)

    # Stamp every event with project_slug
    for ev in events:
        ev["project_slug"] = project_slug

    # Advance iter cursor to highest seen
    if history:
        latest_iter = max(int(r.get("iteration", -1)) for r in history)
        if latest_iter >= 0 and (last_seen is None or latest_iter > last_seen):
            fs.set_last_iter(state, latest_iter)

    return events


def scan_all_active_projects(*, project_slugs: Iterable[str] | None = None) -> dict[str, list[dict]]:
    """Walk projects/ directory; scan each project that has a workspace/
    folder. Returns {project_slug: [events]}.

    If project_slugs is provided, only those exact project slugs are scanned.
    This matters for scoped role ticks: scanning advances frontier cursors and
    may enqueue follow-up actions, so out-of-scope projects must not be touched.
    """
    out: dict[str, list[dict]] = {}
    if not PROJECTS_ROOT.exists():
        return out
    allowed = set(project_slugs) if project_slugs is not None else None
    for child in sorted(PROJECTS_ROOT.iterdir()):
        if not child.is_dir():
            continue
        if allowed is None and child.is_symlink():
            continue
        if not (child / "workspace").exists():
            continue
        try:
            slug = child.name
            fs._validate_slug(slug)  # skip invalid slugs (e.g. with slashes)
        except ValueError:
            continue
        if allowed is not None and slug not in allowed:
            continue
        try:
            events = scan_project(slug, project_dir=child)
            if events:
                out[slug] = events
        except Exception as exc:  # noqa: BLE001
            log.warning("scan_project %s failed: %s", slug, exc)
    return out
