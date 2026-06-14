#!/usr/bin/env python3
"""
rd_tick_brief.py — kernel-tick surfacing for Research Director discipline.

Operator catch 2026-05-09 ~20:15 UTC: "maybe for the kernel every time it
'ticks' we have to bring to the surface the key things related to the
research director... org/ seems more 'tacklable' even if u still commit
the mistakes i want the VPS agents to do it well."

Diagnosis: the apparatus has org/mandates/, org/patterns/INDEX.md,
org/anti-patterns/INDEX.md, the deployment ledger, the diversity scorer,
and the predispatch_check.py gate. Free-recall RD-agent dispatch ignores
all of this. The mandate that was supposed to enforce discipline doesn't
have a kernel-tick hook.

This script is the kernel-tick brief: every RD agent (this session,
or VPS agents on Hetzner) MUST run this at session-start (or tick-start)
and read the output before any dispatch decision. The brief is
deterministic, short, and pulls from on-disk state (no agent
invention).

Usage:
  python scripts/public/control/rd_tick_brief.py
  python scripts/public/control/rd_tick_brief.py --short    # one-screen scan
  python scripts/public/control/rd_tick_brief.py --vps      # for VPS-agent launch wrapper

Output sections:
  §1. Active mandates (org/mandates/research_director_mandate.md)
  §1b. Tenant overlay precheck (split-repo symlink drift detector)
  §2. Pattern catalog state (counts of patterns + anti-patterns; recent mintings)
  §3. Diversity scorer state (monoculture flag + blind spots)
  §4. Last 5 catches (analytics/public/ledgers/catch/catch_ledger.jsonl tail)
  §5. Last 5 unresolved PLs (analytics/public/ledgers/prediction/prediction_ledger.jsonl pending resolution)
  §6. PL calibration state
  §7. Pre-dispatch checklist reminder
  §8. Prediction logging discriminator
  §8b. External GPU/API run surface
  §8e. Autoresearch workbench router
  §9. Primitive discoverability surface
  §9b. Pattern activation guard (negative-to-object trigger)
  §9c. Problem-surface → primitive-chain routing
  §9d. Pattern action contract (evidence-carrier forcing + compact operator card)
  §9e. Structural vocabulary fingerprint (v5 + TB/PS + GP-219 routing)
  §10. Substrate graph precheck (mandatory when a graph runner is registered)

Going forward: the VPS-agent launch wrapper (e.g., the SRO daemon's
iter-tick prelude) should invoke this script and FAIL to dispatch if
the brief was not read in the current tick.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
MANDATE_FILE = REPO / "org/mandates/research_director_mandate.md"
PATTERN_INDEX = REPO / "org/patterns/INDEX.md"
ANTI_PATTERN_INDEX = REPO / "org/anti-patterns/INDEX.md"
SCORER_SUMMARY = REPO / "analytics/public/ledgers/pattern_deployment/pattern_deployment_diversity.json"
CATCH_LEDGER = REPO / "analytics/public/ledgers/catch/catch_ledger.jsonl"
PL_LEDGER = REPO / "analytics/public/ledgers/prediction/prediction_ledger.jsonl"
ACTION_IMPACT_LEDGER = REPO / "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl"
BIFURCATION_REPORT = REPO / "analytics/public/ledgers/reflexive/bifurcation_report.json"
FORECAST_POOL = REPO / "analytics/public/forecast_pool"
FORECASTING_CHANNEL = REPO / "org/channels/forecasting_agent"
EXPERIMENT_TRACK_RECORD = REPO / "research_areas/EXPERIMENT_TRACK_RECORD.md"
PROBLEM_CLASS_TAXONOMY = REPO / "docs/concepts/problem_class_taxonomy.md"
GP149_INTERVENTIONS = REPO / "research_areas/seams/engine/diagnostics/GP-149_mining_findings_and_interventions_seam.md"
GATE_PACKAGE_RECOMMENDER = REPO / "src/ztare/validator/gate_package_recommender.py"
ANTI_PATTERN_CATALOG = REPO / "docs/concepts/anti_pattern_catalog.md"
ORCHESTRATION_MENU = REPO / "org/menu/orchestration_menu.yaml"
PATTERN_CATALOG = REPO / "org/runtime/pattern_catalog.yaml"
STRUCTURAL_LANGUAGE_CATALOG = REPO / "docs/concepts/structural_language_catalog.md"
UNIVERSAL_RESEARCH_OPS = REPO / "src/ztare/research_director/universal_research_ops.py"
THEORY_BUILDING_OPS = REPO / "src/ztare/research_director/theory_building_ops.py"
PROBLEM_SOLVING_OPS = REPO / "src/ztare/research_director/problem_solving_ops.py"
PDE_ESTIMATE_CRAFT_OPS = REPO / "src/ztare/research_director/pde_estimate_craft_ops.py"
TWO_CULTURES = REPO / "src/ztare/research_director/two_cultures.py"
SCORER_SCRIPT = REPO / "scripts/public/analytics_shared/score_pattern_deployment_diversity.py"
ZTARE_TENANT_ROOT = REPO.parent / "ztare-research-co" / "tenants" / "ztare"
EXTERNAL_RUNS_KERNEL = REPO / "src/ztare/orchestration/external_runs.py"
EXTERNAL_RUN_MONITOR = REPO / "scripts/public/control/external_run_monitor.py"
GPU_UTILITIES = REPO / "scripts/public/utilities/gpu"


def _env_bool(name: str) -> bool | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _resolve_project_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        direct = REPO / path
        if direct.exists():
            return direct
        return REPO / "projects" / value
    return path


def _resolve_rubric_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    candidates: list[Path]
    if path.is_absolute():
        candidates = [path]
    else:
        candidates = [REPO / path, REPO / "rubrics" / value]
        if path.suffix == "":
            candidates.append(REPO / "rubrics" / f"{value}.json")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1] if candidates else None


def _read_json_object(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def section(title: str) -> None:
    print()
    print(f"## §{title}")
    print()


def run_scorer() -> dict:
    """Run scorer; return summary."""
    if not SCORER_SCRIPT.exists():
        return {}
    subprocess.run(
        [sys.executable, str(SCORER_SCRIPT), "--window", "15"],
        capture_output=True, text=True,
    )
    if SCORER_SUMMARY.exists():
        try:
            return json.loads(SCORER_SUMMARY.read_text())
        except Exception:
            return {}
    return {}


def mandate_excerpt(short: bool) -> None:
    if not MANDATE_FILE.exists():
        print(f"  (no {MANDATE_FILE})")
        return
    text = MANDATE_FILE.read_text().splitlines()
    if short:
        # First 30 lines
        for line in text[:30]:
            print(f"  {line}")
        if len(text) > 30:
            print(f"  ... ({len(text) - 30} more lines)")
    else:
        for line in text[:80]:
            print(f"  {line}")


def _version_label(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        first = path.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
    except Exception:  # noqa: BLE001
        return "unreadable"
    match = re.search(r"\bv\d+(?:\.\d+)?\b", first)
    return match.group(0) if match else "version_unknown"


def _overlay_target_for(path: Path) -> str:
    try:
        return path.readlink().as_posix()
    except OSError:
        return ""


def _read_json_silent(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _read_jsonl_silent(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    rows: list[dict] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def tenant_overlay_precheck() -> None:
    """Surface split-repo tenant overlay drift without mutating symlinks."""
    root_label = (
        ZTARE_TENANT_ROOT.relative_to(REPO.parent)
        if ZTARE_TENANT_ROOT.exists()
        else "missing"
    )
    print(f"  tenant root: {root_label}")
    checks = [
        (
            "research_director role",
            REPO / "org/roles/research_director.yaml",
            ZTARE_TENANT_ROOT / "roles/research_director.yaml",
        ),
        (
            "principal preferences",
            REPO / "org/preferences/principal.yaml",
            ZTARE_TENANT_ROOT / "preferences/principal.yaml",
        ),
        (
            "manager mandate",
            REPO / "org/mandates/manager_mandate.md",
            ZTARE_TENANT_ROOT / "mandates/manager_mandate.md",
        ),
        (
            "research_director mandate",
            MANDATE_FILE,
            ZTARE_TENANT_ROOT / "mandates/research_director_mandate.md",
        ),
    ]
    for label, active, tenant in checks:
        active_kind = "symlink" if active.is_symlink() else "regular" if active.exists() else "missing"
        target = _overlay_target_for(active)
        print(f"  - {label}: active={active_kind}{f' -> {target}' if target else ''}")
        if active.suffix == ".md" or tenant.suffix == ".md":
            drift = "n/a"
            if tenant.exists() and active.exists():
                try:
                    drift = (
                        "same"
                        if active.read_text(encoding="utf-8", errors="ignore")
                        == tenant.read_text(encoding="utf-8", errors="ignore")
                        else "differs"
                    )
                except Exception:  # noqa: BLE001
                    drift = "unknown"
            print(
                f"    versions: active={_version_label(active)}, "
                f"tenant={_version_label(tenant)}, content={drift}"
            )
    if MANDATE_FILE.exists() and not MANDATE_FILE.is_symlink():
        active_v = _version_label(MANDATE_FILE)
        tenant_v = _version_label(ZTARE_TENANT_ROOT / "mandates/research_director_mandate.md")
        if active_v != tenant_v:
            print(
                "  WARN: RD mandate overlay is not a symlink and versions differ; "
                "do not run tenant setup blindly without reconciling the newer mandate."
            )


def pattern_state() -> None:
    if not PATTERN_INDEX.exists():
        print("  (no pattern index)")
        return
    text = PATTERN_INDEX.read_text()
    # Count PATTERN-XXX entries
    pat_count = sum(1 for line in text.splitlines()
                    if line.strip().startswith("| PATTERN-"))
    meta_count = sum(1 for line in text.splitlines()
                     if line.strip().startswith("| META-PATTERN-"))
    print(f"  Patterns: {pat_count} regular + {meta_count} meta")
    if ANTI_PATTERN_INDEX.exists():
        ap_text = ANTI_PATTERN_INDEX.read_text()
        ap_count = sum(1 for line in ap_text.splitlines()
                       if line.strip().startswith("| ANTI-PATTERN-"))
        print(f"  Anti-patterns: {ap_count}")


def routine_review_state() -> None:
    """Surface the rd_routine_review reconciliation summary (read-only).

    Ports the standing pattern-catalog reconciliation signal into the tick
    brief: count of overdue pattern reviews, count missing a falsifiable_test,
    and a catalog/menu drift flag (catalog patterns not wired into
    org/menu/orchestration_menu.yaml, or vice versa). The full per-pattern
    table stays in `rd_routine_review.py`; this is a compact pointer.
    """
    import datetime as _dt
    import importlib.util as _ilu

    rr_path = REPO / "scripts/public/control/rd_routine_review.py"
    if not rr_path.is_file():
        print("  (rd_routine_review.py not found — routine review unavailable)")
        return
    try:
        _spec = _ilu.spec_from_file_location("rd_routine_review_brief", rr_path)
        _rr = _ilu.module_from_spec(_spec)
        assert _spec.loader is not None
        _spec.loader.exec_module(_rr)
        patterns = _rr.load_catalog(_rr.CATALOG_PATH)
        counts = _rr.load_deployment_counts(_rr.LEDGER_PATH)
    except SystemExit as e:
        print(f"  (routine review degraded: {e})")
        return
    except Exception as e:  # noqa: BLE001
        print(f"  (routine review degraded: {type(e).__name__}: {e})")
        return

    today = _dt.date.today()
    overdue = []
    no_test = 0
    for pid, p in patterns.items():
        due = _rr.parse_due(p.get("review_due"))
        if due is not None and due < today:
            overdue.append((pid, due))
        if not str(p.get("falsifiable_test", "")).strip():
            no_test += 1

    # Catalog/menu drift: patterns in the catalog vs patterns wired anywhere
    # in the orchestration menu (default_chain + applicable + always_on +
    # meta_layer + unassigned_defect, plus legacy sub_classes).
    drift_msg = ""
    try:
        import yaml as _yaml
        menu = _yaml.safe_load(ORCHESTRATION_MENU.read_text(encoding="utf-8")) or {}
        wired: set[str] = set()
        for _body in (menu.get("problem_classes") or {}).values():
            if not isinstance(_body, dict):
                continue
            for _key in ("default_chain", "applicable"):
                for _x in (_body.get(_key) or []):
                    wired.add(str(_x).split()[0].strip())
            for _sc in (_body.get("sub_classes") or {}).values():
                if isinstance(_sc, dict):
                    for _x in (_sc.get("chain_addition") or []):
                        wired.add(str(_x).split()[0].strip())
        for _key in ("always_on", "meta_layer", "unassigned_defect", "library_unwired"):
            for _x in (menu.get(_key) or []):
                wired.add(str(_x).split()[0].strip())
        catalog_ids = {str(p).split()[0].strip() for p in patterns}
        in_catalog_not_menu = sorted(catalog_ids - wired)
        in_menu_not_catalog = sorted(wired - catalog_ids)
        if in_catalog_not_menu or in_menu_not_catalog:
            parts = []
            if in_catalog_not_menu:
                parts.append(f"{len(in_catalog_not_menu)} catalog pattern(s) "
                             f"not wired in menu: {in_catalog_not_menu}")
            if in_menu_not_catalog:
                parts.append(f"{len(in_menu_not_catalog)} menu id(s) absent "
                              f"from catalog: {in_menu_not_catalog}")
            drift_msg = "; ".join(parts)
    except Exception as e:  # noqa: BLE001
        drift_msg = f"(drift check degraded: {type(e).__name__}: {e})"

    print(f"  catalog: {len(patterns)} patterns | "
          f"ledger dispatches: {sum(counts.values())}")
    print(f"  overdue reviews: {len(overdue)} | "
          f"missing falsifiable_test: {no_test}")
    if overdue:
        for pid, due in sorted(overdue, key=lambda x: x[1])[:8]:
            print(f"    - {pid} (due {due.isoformat()})")
        if len(overdue) > 8:
            print(f"    … +{len(overdue) - 8} more")
    if drift_msg:
        print(f"  DRIFT FLAG: {drift_msg}")
    else:
        print("  catalog/menu drift: none detected")
    print("  Full per-pattern table: python3 scripts/public/control/"
          "rd_routine_review.py")


def closure_claim_discipline_state() -> None:
    """Surface state of the closure-claim discipline linter.

    Implements pre-tick surfacing for ANTI-PATTERN-012 + META-PATTERN-022 +
    META-PATTERN-023 discipline. Auto-fires reminders about the four
    discipline checks available before agent dispatch.
    """
    linter_script = REPO / "scripts/public/control/closure_claim_discipline_linter.py"
    if not linter_script.exists():
        print("  (closure-claim discipline linter not found)")
        return
    print("  Discipline checks available (run per closure-claim artifact):")
    print("    1. ANTI-PATTERN-012 — per-step explicit verification (6-point)")
    print("    2. META-PATTERN-022 — universal-language op enumeration")
    print("    3. META-PATTERN-023 — 4-scope coverage (local/chain/recursive/meta)")
    print("    4. ANTI-PATTERN-012-explicit — explicit reference in artifact")
    print("  Run:  python3 scripts/public/control/closure_claim_discipline_linter.py")
    print("        check <path-to-artifact>")
    print("  Status / summary:")
    print("        python3 scripts/public/control/closure_claim_discipline_linter.py")
    print("        status")


def diversity_state(summary: dict) -> int:
    """Surface pattern-monoculture risk.

    The RD brief is a state surface, not the dispatch gate.  A monoculture
    warning should steer the next pattern choice, but it should not make a
    substrate-scoped brief exit nonzero by itself; `predispatch_check.py`
    remains the enforcement point before an actual dispatch.
    """
    if not summary:
        print("  (scorer summary unavailable)")
        return 0
    metrics = summary.get("metrics", {})
    flag = metrics.get("monoculture_flag", False)
    max_p = metrics.get("monoculture_max_pattern", "NA")
    max_s = metrics.get("monoculture_max_share", 0)
    print(f"  monoculture_flag = {flag}")
    print(f"    max share: {max_s:.3f} on {max_p}")
    print(f"  audit_share: {metrics.get('audit_share', 0):.3f}")
    print(f"  external_share: {metrics.get('external_share', 0):.3f}")
    print(f"  eigenquestion_share: {metrics.get('eigenquestion_share', 0):.3f}")

    blind = [p for p, _ in summary.get("blind_spots", [])]
    if blind:
        print(f"  blind spots (under-deployed): {', '.join(blind[:6])}")
        if len(blind) > 6:
            print(f"    ...and {len(blind) - 6} more")
    if flag:
        print()
        print(f"  !!! MONOCULTURE FLAG FIRING — DEPLOY DIVERSE PATTERN NEXT !!!")
    return 0


def recent_catches(n: int) -> None:
    if not CATCH_LEDGER.exists():
        print("  (no catch ledger)")
        return
    rows = []
    try:
        for line in CATCH_LEDGER.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception as e:
        print(f"  (catch ledger read error: {e})")
        return

    print(f"  Total catches: {len(rows)}")
    print(f"  Last {n}:")
    for r in rows[-n:]:
        cid = r.get("catch_id", "NA")
        title = (r.get("title", "") or "")[:140]
        status = r.get("status", "NA")
        print(f"    {cid} [{status}] {title}")


def _resolved_prediction_ids(row: dict) -> list[str]:
    if not row.get("resolved_at"):
        return []
    ids: list[str] = []
    pid = row.get("prediction_id")
    if isinstance(pid, str) and pid:
        ids.append(pid)
    resolves = row.get("resolves")
    if isinstance(resolves, str) and resolves:
        ids.append(resolves)
    elif isinstance(resolves, list):
        ids.extend(x for x in resolves if isinstance(x, str) and x)
    return ids


def _norm_scope(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def _substrate_in_scope(substrate: str | None, scope: str | None) -> bool:
    scope_norm = _norm_scope(scope)
    if not scope_norm or scope_norm in {"all", "global"}:
        return True
    substrate_norm = _norm_scope(substrate)
    if not substrate_norm:
        return False
    return scope_norm in substrate_norm


def open_pl_rows(n: int, *, scope: str | None = None) -> None:
    if not PL_LEDGER.exists():
        print("  (no PL ledger)")
        return
    pl_predicted = {}
    pl_resolved = set()
    try:
        for line in PL_LEDGER.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                pid = row.get("prediction_id")
                if not pid:
                    continue
                resolved = _resolved_prediction_ids(row)
                if resolved:
                    pl_resolved.update(resolved)
                else:
                    if pid not in pl_predicted:
                        pl_predicted[pid] = row
            except Exception:
                continue
    except Exception as e:
        print(f"  (PL ledger read error: {e})")
        return

    open_pls = [(pid, row) for pid, row in pl_predicted.items()
                if pid not in pl_resolved
                and _substrate_in_scope(row.get("substrate"), scope)]
    open_pls.sort(key=lambda x: x[1].get("predicted_at", ""), reverse=True)

    if scope and _norm_scope(scope) not in {"", "all", "global"}:
        print(f"  Open PLs in scope `{scope}`: {len(open_pls)}")
    else:
        print(f"  Open PLs: {len(open_pls)}")
    print(f"  Last {n}:")
    for pid, row in open_pls[:n]:
        substrate = row.get("substrate", "NA")[:60]
        question = (row.get("question", "") or "")[:120]
        print(f"    {pid} [{substrate}]")
        print(f"      Q: {question}")


def _parse_iso_utc(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    if "<" in value or ">" in value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def prediction_closure_hygiene(hours: int = 36, *, blocking_scope: str | None = None) -> int:
    """Return 1 if there is fresh Tier-1 unresolved prediction debt.

    Historical malformed rows are surfaced as warning-only debt so the tick can
    enforce discipline going forward without bricking on legacy schema noise.
    """
    if not PL_LEDGER.exists():
        print("  (no PL ledger)")
        return 0

    predicted_rows: dict[str, dict] = {}
    resolved_ids: set[str] = set()
    malformed_open: list[tuple[str, str, str]] = []
    fresh_open: list[tuple[str, str, str, str]] = []
    fresh_cross_scope: list[tuple[str, str, str, str]] = []
    stale_open: list[tuple[str, str, str, str]] = []
    now = datetime.now(timezone.utc)
    horizon = timedelta(hours=hours)

    for raw in PL_LEDGER.read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except Exception:
            continue
        pid = row.get("prediction_id")
        if not pid:
            continue
        resolved = _resolved_prediction_ids(row)
        if resolved:
            resolved_ids.update(resolved)
            continue
        predicted_rows.setdefault(pid, row)

    for pid, row in predicted_rows.items():
        if pid in resolved_ids:
            continue
        if row.get("tier") != 1:
            continue
        substrate = (row.get("substrate") or "NA")[:70]
        predictor = row.get("predictor") or "NA"
        ts = row.get("predicted_at")
        parsed = _parse_iso_utc(ts)
        if parsed is None:
            malformed_open.append((pid, substrate, str(ts)))
            continue
        age = now - parsed
        item = (pid, substrate, predictor, parsed.isoformat())
        if age <= horizon and _substrate_in_scope(row.get("substrate"), blocking_scope):
            fresh_open.append(item)
        elif age <= horizon:
            fresh_cross_scope.append(item)
        else:
            stale_open.append(item)

    if blocking_scope and _norm_scope(blocking_scope) not in {"", "all", "global"}:
        print(f"  Blocking scope: `{blocking_scope}`")
    else:
        print("  Blocking scope: global")

    print(f"  Fresh unresolved Tier-1 PLs in blocking scope (<= {hours}h): {len(fresh_open)}")
    for pid, substrate, predictor, ts in fresh_open[:5]:
        print(f"    {pid} [{predictor}] {substrate}")
        print(f"      predicted_at: {ts}")
    if len(fresh_open) > 5:
        print(f"    ...and {len(fresh_open) - 5} more")

    print(f"  Fresh unresolved Tier-1 PLs outside blocking scope (warning-only): {len(fresh_cross_scope)}")
    for pid, substrate, predictor, ts in fresh_cross_scope[:5]:
        print(f"    {pid} [{predictor}] {substrate}")
        print(f"      predicted_at: {ts}")
    if len(fresh_cross_scope) > 5:
        print(f"    ...and {len(fresh_cross_scope) - 5} more")

    print(f"  Older unresolved Tier-1 PLs (> {hours}h): {len(stale_open)}")
    for pid, substrate, predictor, ts in stale_open[:3]:
        print(f"    {pid} [{predictor}] {substrate}")
        print(f"      predicted_at: {ts}")
    if len(stale_open) > 3:
        print(f"    ...and {len(stale_open) - 3} more")

    print(f"  Malformed unresolved Tier-1 timestamps: {len(malformed_open)}")
    for pid, substrate, ts in malformed_open[:3]:
        print(f"    {pid} [{substrate}] predicted_at={ts}")
    if len(malformed_open) > 3:
        print(f"    ...and {len(malformed_open) - 3} more")

    if fresh_open:
        print()
        print("  !!! PREDICTION CLOSURE DEBT FIRING — resolve fresh in-scope Tier-1 PL rows")
        print("  !!! before new in-scope dispatch / spend / route-commitment.")
        return 1
    return 0


def calibration_state() -> None:
    """Surface PL calibration state. Added 2026-05-10 per operator catch
    'I haven't seen u update the predictions in terms of estimation etc.'"""
    scorer = REPO / "scripts/public/control/forecast/score_prediction_ledger_calibration.py"
    summary_path = REPO / "analytics/public/ledgers/prediction/prediction_ledger_calibration_summary.json"
    if not scorer.exists():
        print("  (no calibration scorer)")
        return
    try:
        subprocess.run([sys.executable, str(scorer)],
                       capture_output=True, text=True, timeout=30)
    except Exception:
        pass
    if not summary_path.exists():
        print("  (calibration summary unavailable)")
        return
    try:
        s = json.loads(summary_path.read_text())
    except Exception:
        print("  (calibration summary parse failed)")
        return
    n_scored = s.get("n_rows_brier_scored", 0)
    cross = s.get("cross_predictor", {})
    effort = s.get("effort_ratio", {})
    cost = s.get("cost_ratio", {})
    print(f"  N resolved scored: {n_scored} (gate: 20)")
    if cross:
        print(f"  Cross-predictor Brier: best {cross.get('best_predictor','NA')}={cross.get('best_brier_mean',0):.3f}, "
              f"worst {cross.get('worst_predictor','NA')}={cross.get('worst_brier_mean',0):.3f}")
    print(f"  Effort-ratio (predicted_min/actual_min) mean={effort.get('mean',0):.2f} median={effort.get('median',0):.2f} (in-band [0.5, 2.0])")
    out_of_band = [p for p, d in (effort.get('per_predictor') or {}).items()
                   if isinstance(d, dict) and d.get('out_of_band')]
    if out_of_band:
        print(f"  Predictors OUT-OF-BAND on effort: {', '.join(out_of_band[:3])}")
    print(f"  Cost-ratio mean={cost.get('mean',0):.2f} (in-band [0.5, 2.0])")
    if s.get('demote_now'):
        print(f"  !!! DEMOTION RULE TRIGGERED — review before more PL forecasts !!!")
    # §6b: own-work signed forecast-bias (recurring-pessimism / optimism
    # trend monitor on data we already collect). DIAGNOSTIC ONLY — prints
    # a number, emits NO directive (an auto "override your pessimism"
    # would induce optimism-gaming; human/Meta-Darwin judges). n-gated.
    try:
        fp = REPO / "scripts/public/control/forecast/pool.py"
        code = ("import json,importlib.util as u;"
                f"s=u.spec_from_file_location('fp',r'{fp}');"
                "m=u.module_from_spec(s);s.loader.exec_module(m);"
                "print(json.dumps(m.signed_calibration_bias()))")
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True, timeout=30)
        b = json.loads(r.stdout.strip().splitlines()[-1])
        if b.get("status") == "ok":
            print(f"  §6b own-work signed bias = {b['mean_signed_bias']:+.3f} "
                  f"(n={b['n']}; <0 pessimism / >0 optimism; |·|<0.15 "
                  f"calibrated) — {b['interpretation']}")
        else:
            print(f"  §6b own-work signed bias: {b.get('status')} "
                  f"(n={b.get('n',0)}/{b.get('min_n','?')}) — advisory only, "
                  "not an override")
    except Exception as e:
        print(f"  §6b own-work signed bias: degraded ({e}) — advisory")


def forecast_market_state() -> None:
    """Surface GP-230 market transport debt before the RD consumes it."""
    model_path = FORECAST_POOL / "market_state" / "global_health.json"
    model = _read_json_silent(model_path)
    if model:
        resolved_debt = model.get("resolved_without_score") or {}
        aggregate_missing = model.get("aggregate_missing") or {}
        awaiting = model.get("awaiting_forecasts") or {}
        transport = model.get("transport") or {}
        decision_use = model.get("decision_use") or {}
        reliability = model.get("reliability") or {}
        insights_path = FORECAST_POOL / "market_state" / "reflexive_insights.json"
        insights = _read_json_silent(insights_path)
        print("  GP-230 materialized read model:")
        print(f"    path={model_path.relative_to(REPO)}")
        print(f"    contracts={model.get('contract_count')} "
              f"actions={model.get('action_counts')}")
        print(f"    lifecycle={model.get('lifecycle_counts')}")
        print(f"    resolved_without_score={resolved_debt.get('count')} "
              f"aggregate_missing={aggregate_missing.get('count')} "
              f"awaiting_forecasts={awaiting.get('count')}")
        print("  decision-use ledger:")
        print(f"    rows={decision_use.get('rows')} "
              f"changed={decision_use.get('decision_changed_rows')} "
              f"used_for={decision_use.get('used_for_counts')}")
        if reliability:
            print("  reliability model:")
            print(f"    path={reliability.get('path')} "
                  f"summary={reliability.get('summary')}")
        if insights:
            print("  reflexive insights:")
            print(f"    path={insights_path.relative_to(REPO)} "
                  f"count={insights.get('insight_count')}")
            counts = insights.get("counts") if isinstance(insights.get("counts"), dict) else {}
            if counts:
                print(f"    thin_independence={counts.get('thin_independence_contracts')} "
                      f"forecast_updates={counts.get('forecast_update_files')}")
            for item in (insights.get("insights") or [])[:3]:
                print(f"    - [{item.get('severity')}] {item.get('title')}")
        maintenance_path = FORECAST_POOL / "market_state" / "maintenance_plan.json"
        maintenance = _read_json_silent(maintenance_path)
        if maintenance:
            counts = maintenance.get("counts") if isinstance(maintenance.get("counts"), dict) else {}
            print("  maintenance plan:")
            print(f"    path={maintenance_path.relative_to(REPO)} counts={counts}")
        print("  forecasting_agent transport:")
        print(f"    inbox_messages={transport.get('inbox_messages')} "
              f"open={transport.get('open_messages')} "
              f"open_for_resolved_contracts="
              f"{transport.get('open_for_resolved_contracts')} "
              f"fulfilled_missing_aggregate="
              f"{transport.get('fulfilled_messages_missing_aggregate')}")
        samples = resolved_debt.get("samples") or []
        if samples[:5]:
            print("  score debt sample:")
            for cid in samples[:5]:
                print(f"    - {cid}")
        print("  RD fast path: read market_state/contracts/<cid>.json, "
              "then record one decision-use row if the forecast changed, "
              "confirmed, or was intentionally ignored.")
        print("  Refresh when stale: "
              "python scripts/public/control/forecast/pool.py "
              "materialize-state")
        return

    contracts = sorted((FORECAST_POOL / "contracts").glob("*.json"))
    outcomes = sorted((FORECAST_POOL / "outcomes").glob("*.json"))
    scores = sorted((FORECAST_POOL / "scores").glob("*.json"))
    aggregates = sorted((FORECAST_POOL / "aggregates").glob("*.json"))
    contract_ids = {p.stem for p in contracts}
    resolved_ids = {p.stem for p in outcomes}
    scored_ids = {p.stem for p in scores}
    aggregate_ids = {p.stem for p in aggregates}
    resolved_unscored = sorted(resolved_ids - scored_ids)
    aggregate_missing = sorted(contract_ids - aggregate_ids)

    messages = []
    for path in sorted((FORECASTING_CHANNEL / "inbox").glob("*.json")):
        payload = _read_json_silent(path)
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        messages.append({
            "path": path,
            "message_id": str(payload.get("message_id") or path.stem),
            "contract_id": str(metadata.get("contract_id")
                               or payload.get("contract_id") or ""),
            "status": str(payload.get("status") or "missing"),
            "obligation_state": str(payload.get("obligation_state")
                                    or "missing"),
        })
    claim_ids = {
        p.stem for p in (FORECASTING_CHANNEL / "claims").glob("*.json")
    }
    response_ids = {
        p.stem for p in (FORECASTING_CHANNEL / "responses").glob("*.json")
    }

    status_counts = Counter(m["status"] for m in messages)
    obligation_counts = Counter(m["obligation_state"] for m in messages)
    open_messages = [
        m for m in messages
        if m["status"] != "closed"
        and m["obligation_state"] not in {"fulfilled", "refused", "expired"}
    ]
    claimed_without_response = [
        m for m in messages
        if m["message_id"] in claim_ids and m["message_id"] not in response_ids
    ]
    open_resolved = [
        m for m in open_messages
        if m["contract_id"] and m["contract_id"] in resolved_ids
    ]
    fulfilled_missing_aggregate = [
        m for m in messages
        if m["contract_id"]
        and m["contract_id"] not in aggregate_ids
        and m["obligation_state"] == "fulfilled"
    ]

    print("  GP-230 artifact state:")
    print(f"    contracts={len(contracts)} outcomes={len(outcomes)} "
          f"aggregates={len(aggregates)} scores={len(scores)}")
    print(f"    resolved_without_score={len(resolved_unscored)} "
          f"contracts_without_aggregate={len(aggregate_missing)}")
    print("  forecasting_agent channel state:")
    print(f"    inbox_messages={len(messages)} claim_files={len(claim_ids)} "
          f"response_files={len(response_ids)} open={len(open_messages)} "
          f"open_for_resolved_contracts={len(open_resolved)}")
    print(f"    claimed_without_response={len(claimed_without_response)}")
    print(f"    status_counts={dict(status_counts)}")
    print(f"    obligation_state_counts={dict(obligation_counts)}")
    print(f"    fulfilled_messages_missing_aggregate="
          f"{len(fulfilled_missing_aggregate)}")
    if resolved_unscored[:5]:
        print("  score debt sample:")
        for cid in resolved_unscored[:5]:
            print(f"    - {cid}")
    if open_resolved[:5]:
        print("  stale transport sample:")
        for msg in open_resolved[:5]:
            try:
                rel = msg["path"].relative_to(REPO)
            except ValueError:
                rel = msg["path"]
            print(f"    - {rel} ({msg['contract_id']})")
    print("  RD rule: consume an aggregate/status artifact, not raw "
          "channel chatter. If the aggregate is absent, record an "
          "explicit timeout/no-update/override.")


def predispatch_reminder() -> None:
    print("  Before any dispatch (cold-shot or internal agent):")
    print("    1. Run: python scripts/public/control/predispatch_check.py \\")
    print("              --pattern-id PATTERN-XXX \\")
    print("              --mode {audit,construct,scope,calibrate} \\")
    print("              --internal-or-external {internal,external_via_api,external_via_operator} \\")
    print("              --substrate <substrate-name>")
    print("    2. If gate refuses (monoculture firing), pivot to a blind-spot pattern.")
    print("    3. Pre-register PL row with conditional odds in analytics/public/ledgers/prediction/prediction_ledger.jsonl.")
    print("    3b. MANDATORY (micro layer): init a MICRO forecast contract")
    print("        `forecast_pool.py init-contract --layer micro … "
          "--emit-warm-wake --warm-forecasters "
          "<runtime>:<independent_agent_id>:forecasting_agent`")
    print("        so an independent agent prices the contract")
    print("        (cross-agent forecast diversity —")
    print("        a same-runtime/self forecast alone is NOT sufficient); add")
    print("        the RD conditional-odds + agent-effort forecast;")
    print("        macro/meso discretionary, micro contract MANDATORY.")
    print("    4. Dispatch.")
    print("    5. Log to analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl with task_id.")
    print("    6. Resolve PL row when result lands.")
    print("    7. Tick-close: `export RD_OWNER=<this RD's created_by>` once "
          "per session so post_tick_check.py is owner-scoped (multi-RD "
          "isolation: only THIS RD's debt HARD-blocks; others advisory). "
          "Unset = legacy global.")


def prediction_logging_discriminator_brief() -> None:
    print("  PATTERN-012 discriminator:")
    print("    Tier 1 MUST log before action: agent/external dispatch, parallel swarm,")
    print("      promote/demote/kill, escalation, paid spend, pre-registered experiment,")
    print("      route commitment, or anything that gates a typed action.")
    print("    Tier 2 SHOULD log: prioritization/atom-ordering/campaign triage with")
    print("      observable outcome and nontrivial effort.")
    print("    Tier 3 DO NOT log by default: housekeeping, read-only orientation,")
    print("      idle hypotheses. If it later gates action, that is retrospective")
    print("      Tier promotion and should be caught.")
    print("    CLI: ./venv/bin/python scripts/public/control/prediction_logging_discriminator.py --action-kind agent_dispatch")
    print("  --- UNIVERSAL MICRO PREDICTION-MARKET MANDATE (KERNEL — all agents/roles/substrates) ---")
    print("    Macro/meso forecasts are agent-discretionary. The MICRO")
    print("    contract is MANDATORY for any tick that gates a typed")
    print("    commitment, IN ORDER, BEFORE tick work:")
    print("      1) forecast_pool.py init-contract --layer micro "
          "--created-by <rd_agent> … --emit-warm-wake "
          "--warm-forecasters "
          "<runtime>:<independent_agent_id>:forecasting_agent")
    print("      2) add-forecast --agent-id <rd_agent> --p-success "
          "<RD CONDITIONAL ODDS> --expected-cost-agent-minutes <effort>")
    print("      3) (recover if init'd w/o wake) forecast_pool.py "
          "warm-daemon-once --contract-id <id> --forecasters "
          "<runtime>:<independent_agent_id>:forecasting_agent")
    print("    --emit-warm-wake ⇒ an independent agent prices the contract")
    print("    (cross-agent diversity; an RD self-forecast ALONE is")
    print("    INSUFFICIENT).")
    print("    ORDERING: an independent agent cannot price a RESOLVED")
    print("    contract — NEVER resolve before the wake is emitted & consumed.")
    print("    POST-tick MECE legs (all, or PROTOCOL-INCOMPLETE): Tier-1 ·")
    print("    Tier-3 pattern_026 · Tier-3 closure_claim (if closure-")
    print("    adjacent) · adversarial steelman-kill (if closure-adjacent)")
    print("    · RESOLVE the micro contract (after independent forecast) ·")
    print("    post_tick_check.py · F-row · manifest maintenance · memory.")
    print("    Substrate-specific surfacing (amnesia/anchor/manifest) is")
    print("    loaded as the RD-role substrate MODULE in §8c — NOT here")
    print("    (kernel/role-module split; canonical, no drift).")
    print("  --- AGENT-DISPATCH ECONOMY (KERNEL — all agents; PATTERN-011) ---")
    print("    Do depth-n recursive work (math/derivation/construction)")
    print("    DIRECTLY in-thread. Dispatch an Agent ONLY for (1)")
    print("    ADVERSARIAL testing — independent cold agent to kill your")
    print("    OWN construction (the sole real independence benefit) — or")
    print("    (2) genuine DIVIDE-AND-CONQUER of independent subtasks.")
    print("    Do NOT outsource forward work you can do yourself (lossy")
    print("    hand-off, no independence gain). Generative-diversity gate")
    print("    [5] = you (in-thread) + ONE independent adversary, NOT")
    print("    outsourced generation. **CARVE-OUT (3): when STUCK on a")
    print("    residual (≥2 killed attempts / recurrence), dispatch a")
    print("    COLD de-anchored agent given ONLY the residual doc + the")
    print("    open ask 'what structural CLASS is missing / give the")
    print("    proof route' (PATTERN-014 cold_shot). This IS a real")
    print("    independence benefit: you are anchored on the grind, a")
    print("    cold agent is not — empirically reaches the reframe you")
    print("    cannot from inside. Anchoring is the discriminant, not")
    print("    'can I do it'.** Canonical: org/patterns/swarm_dispatch.md")
    print("    (PATTERN-011) + cold_shot_dispatch.md (PATTERN-014).")
    print("  --- PDE-NODE ESTIMATE-DEPTH FORCING (KERNEL — all agents) ---")
    print("    If THIS tick claims a PDE estimate / inequality on a PDE")
    print("    node (C3/C5/C7/BKM/Prodi-Serrin/…), the §9 primitive")
    print("    discoverability surface is ADVISORY — that is NOT enough")
    print("    (RCA 2026-05-16: surfaced-but-not-forced ⇒ read past under")
    print("    pressure; shipped tick608 with dimensional/endpoint errors")
    print("    a 0-cost gate would have hard-blocked). FORCING: before")
    print("    asserting any estimate you MUST have RUN the deterministic")
    print("    preflight on the candidate inequality —")
    print("      ./venv/bin/python src/ztare/research_director/"
          "pde_estimate_workbench.py --target … --candidate-inequality …")
    print("    (it invokes src/ztare/gates/pde_inequality_dimensional_"
          "gate.py + auxiliary_object/limit_passage gates; ALSO invoked")
    print("    in-loop via the typed-endpoint pack — same primitive, both")
    print("    paths). A hard_fail (dimensional incoherence / endpoint-")
    print("    unbound) BLOCKS the estimate claim until the inequality is")
    print("    re-formed. This is the DEPTH counterpart to the §3b")
    print("    adversarial-survival gate (dimensional/endpoint here;")
    print("    math-soundness there) — pass BOTH, not one. Reuse the")
    print("    EXISTING src/ primitives (registered in the architecture")
    print("    index); do NOT rebuild (check-before-duplicating).")


def external_gpu_run_surface() -> None:
    """Surface generic GPU run utilities without substrate-specific policy."""
    print("  kernel registry:")
    if EXTERNAL_RUNS_KERNEL.exists():
        print(f"    - {EXTERNAL_RUNS_KERNEL.relative_to(REPO)}")
    else:
        print("    - MISSING: src/ztare/orchestration/external_runs.py")
    print("  monitor:")
    if EXTERNAL_RUN_MONITOR.exists():
        print(f"    - {EXTERNAL_RUN_MONITOR.relative_to(REPO)}")
    else:
        print("    - MISSING: scripts/public/control/external_run_monitor.py")
    utilities = [
        GPU_UTILITIES / "lambda_olmes_vllm_bootstrap.sh",
        GPU_UTILITIES / "patch_lm_eval_vllm_prompt_tokens.py",
        GPU_UTILITIES / "run_oe_eval_checkpoint_sequence.py",
        GPU_UTILITIES / "register_external_gpu_run.py",
    ]
    print("  reusable launch helpers:")
    for path in utilities:
        label = path.relative_to(REPO)
        print(f"    - {label}" if path.exists() else f"    - MISSING: {label}")
    print("  rule: paid GPU/API runs should register a contract/state/event record")
    print("    under ztare_workspace/external_runs so later agents can reattach.")


NEGATIVE_ROW_TERMS = (
    "failed",
    "fails",
    "falsified",
    "negative",
    "reject",
    "rejects",
    "weakened",
    "weaken",
    "demote",
    "demoted",
    "null",
    "0/",
)

OBJECT_DISCOVERY_TERMS = (
    "de-anchor",
    "deanchor",
    "reframe",
    "residual",
    "void",
    "negative-to-object",
    "state variable",
    "hidden axis",
    "coordinate",
    "mode flow",
    "response-mode",
    "response mode",
    "repair",
    "repairs",
    "high-contrast",
    "schema-calibration",
)


def _experiment_rows_for_scope(scope: str | None) -> list[tuple[int, str]]:
    if not EXPERIMENT_TRACK_RECORD.exists():
        return []
    rows: list[tuple[int, str]] = []
    try:
        lines = EXPERIMENT_TRACK_RECORD.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    for lineno, line in enumerate(lines, start=1):
        if not line.startswith("| E-") and not line.startswith("| F-"):
            continue
        if scope and _norm_scope(scope) not in {"", "all", "global"}:
            if _norm_scope(scope) not in _norm_scope(line):
                continue
        rows.append((lineno, line))
    return rows


def pattern_activation_guard(scope: str | None = None, *, lookback: int = 16) -> int:
    """Stop repeated negative routes from bypassing object-discovery primitives."""
    rows = _experiment_rows_for_scope(scope)[-lookback:]
    if not rows:
        print("  No recent experiment rows in scope; no activation.")
        return 0

    negative_rows: list[tuple[int, str]] = []
    for lineno, line in rows:
        low = line.lower()
        if any(term in low for term in NEGATIVE_ROW_TERMS):
            negative_rows.append((lineno, line))

    object_rows_after_or_at_last_negative: list[tuple[int, str]] = []
    if negative_rows:
        last_negative_lineno = negative_rows[-1][0]
        for lineno, line in rows:
            if lineno < last_negative_lineno:
                continue
            low = line.lower()
            if any(term in low for term in OBJECT_DISCOVERY_TERMS):
                object_rows_after_or_at_last_negative.append((lineno, line))

    print(f"  recent rows scanned: {len(rows)}")
    print(f"  negative/failed-route rows: {len(negative_rows)}")
    for lineno, line in negative_rows[-3:]:
        cells = [c.strip(" `") for c in line.strip().strip("|").split("|")]
        rid = cells[0] if cells else f"line {lineno}"
        print(f"    - {rid} (line {lineno})")

    if len(negative_rows) < 2:
        print("  No repeated negative-route pattern detected.")
        return 0

    if object_rows_after_or_at_last_negative:
        print("  negative-to-object conversion detected after latest negative:")
        for lineno, line in object_rows_after_or_at_last_negative[-3:]:
            cells = [c.strip(" `") for c in line.strip().strip("|").split("|")]
            rid = cells[0] if cells else f"line {lineno}"
            print(f"    - {rid} (line {lineno})")
        print("  activation satisfied: continue, but cite the object-discovery chain in closure.")
        return 0

    print()
    print("  !!! PATTERN ACTIVATION GUARD FIRING — repeated negative routes without")
    print("  !!! a later object-discovery / residual-void conversion.")
    print("  Required chain before new dispatch:")
    print("    1. PATTERN-014 cold_shot_dispatch / de-anchor")
    print("    2. src/ztare/orchestrator/briefing_providers/forced_reframe.py")
    print("    3. src/ztare/gates/negative_space_extractor.py or a substrate residual-void audit")
    print("    4. PATTERN-018 structural_residual_analogy")
    print("    5. PATTERN-015 eigenquestion phrasing discipline")
    print("  Required artifact: negative-to-object checkpoint with failed object,")
    print("  residual structure, candidate state variable, and cheapest discriminator.")
    print("  Deviation must be recorded in the F-row / closure artifact.")
    return 1


def problem_surface_primitive_routing(scope: str | None = None) -> int:
    """Surface the existing problem-surface -> primitive-chain menu.

    This is the meta-primitive-use layer: given the shape of the problem,
    choose from the existing orchestration patterns instead of free-recalling
    or inventing a new catalogue.
    """
    status = 0
    print("  canonical files:")
    for path in (ORCHESTRATION_MENU, PATTERN_CATALOG):
        rel = path.relative_to(REPO)
        exists = path.exists()
        print(f"    - {rel}: {'present' if exists else 'MISSING'}")
        if not exists:
            status = 1

    if ORCHESTRATION_MENU.exists():
        text = ORCHESTRATION_MENU.read_text(encoding="utf-8", errors="ignore")
        problem_classes: list[str] = []
        in_problem_classes = False
        for line in text.splitlines():
            if line.startswith("problem_classes:"):
                in_problem_classes = True
                continue
            if line.startswith("cross_cutting_patterns:"):
                in_problem_classes = False
            if not in_problem_classes:
                continue
            match = re.match(r"^  ([a-z][a-z0-9_]+):\s*$", line)
            if match:
                problem_classes.append(match.group(1))
        print(f"  top-level problem surfaces: {len(problem_classes)}")
        if problem_classes:
            print(f"    {', '.join(problem_classes)}")
        if "negative_result_object_discovery" in text:
            print("  includes negative_result_object_discovery -> PATTERN-014 + PATTERN-018 + PATTERN-015")
        if "HONESTY" in text and "ADVISORY only" in text:
            print("  warning from menu: recommendation keys were advisory until tick/runtime enforcement is wired.")
        print("  H31-H47 compiler policy: labels are not the action unit; use compact checked contracts.")
        print("    active fields: accepted_residual_class, source_cue_check_status, action_program, current_action_index, required_next_action, program_counter_rule, open_set_refusal_status")
        print("    audit fields: requested_residual_class, selected_residual_edge, rejected_nearest_confuser_edge, edge_source_evidence, source_cue_receipts_ref, missing_source_cues_ref, source_contract_alignment_check, deterministic_lowering_result")
        print("    H47: do not enforce outside-specific class expansion yet; shadow-log known-class proposal, outside candidate, cue checks, invariant result, action, and later outcome.")
        print("    shadow logger: python -m src.ztare.research_director.orchestration_shadow_log <event.json> --append")
        print("    if no source-supported class matches, route outside_menu -> specific new_residual_class_candidate -> defer_to_new_residual_class -> stop_or_repair; do not force a closed menu class.")
        print("    validate compact contracts before execution: python -m src.ztare.research_director.orchestration_contract_gate <contract.json> --source-facts-file <source.txt>")
        print("    if compact contract conflicts with source cues, program order, deterministic lowering, outside handoff, or stop/proceed scope, repair/refuse before executing its action_program.")

        # Deepened surfacing (2026-05-15): top-level names alone left every
        # sub_class's hand-authored routing (triggers / chain / dispatch)
        # authored-but-dead at precheck. Render leaf/candidate sub_classes
        # with their actionable routing so the RD sees what to dispatch,
        # not just a bare class token. Fail-soft: degrade to names-only.
        try:
            import yaml  # type: ignore
            menu = yaml.safe_load(text) or {}
            pcs = menu.get("problem_classes", {})
            shown = 0
            CAP = 40
            print("  sub-class routing (leaf/candidate, actionable at dispatch):")
            for cls, body in pcs.items():
                if not isinstance(body, dict):
                    continue
                subs = body.get("sub_classes", {}) or {}
                actionable = {
                    sn: sb for sn, sb in subs.items()
                    if isinstance(sb, dict)
                    and str(sb.get("confidence", "")).lower() in ("leaf", "candidate")
                }
                if not actionable:
                    continue
                print(f"    {cls}:")
                for sn, sb in actionable.items():
                    if shown >= CAP:
                        break
                    conf = str(sb.get("confidence", "?"))
                    trig = sb.get("triggers", {}) or {}
                    lex = trig.get("lexical", []) if isinstance(trig, dict) else []
                    lex_s = ", ".join(str(t) for t in lex[:4])
                    chain = sb.get("chain_addition", []) or []
                    chain_s = ", ".join(str(c) for c in chain[:4])
                    cmds = sb.get("mechanical_dispatch_commands", []) or []
                    cmd0 = ""
                    for c in cmds:
                        cs = str(c).strip()
                        if cs and not cs.startswith("#"):
                            cmd0 = cs[:110]
                            break
                    print(f"      - {sn} [{conf}]"
                          + (f"  triggers: {lex_s}" if lex_s else ""))
                    if chain_s:
                        print(f"        chain: {chain_s}")
                    if cmd0:
                        print(f"        run: {cmd0}")
                    shown += 1
                if shown >= CAP:
                    print(f"    ... ({CAP} sub-class cap reached)")
                    break
            if shown == 0:
                print("    (no leaf/candidate sub_classes parsed)")
        except ImportError:
            print("  (sub-class routing unavailable: pyyaml not installed; names-only)")
        except Exception as exc:
            print(f"  (sub-class routing parse degraded: {exc}; names-only)")

    if PATTERN_CATALOG.exists():
        text = PATTERN_CATALOG.read_text(encoding="utf-8", errors="ignore")
        pattern_count = len(re.findall(r"^  (?:META-)?PATTERN-\d+:", text, flags=re.MULTILINE))
        print(f"  generated pattern catalog entries: {pattern_count}")

    print("  RD rule: before dispatch, classify the problem surface against this menu, then compile it to a checked action contract.")
    print("  Use the recommended primitive chain or record a deviation in the closure artifact; if the surface is outside-menu, record the new residual class candidate instead of forcing a known class.")
    return status


def pattern_action_contract_surface(scope: str | None = None) -> int:
    """Surface a pattern-to-action contract, not just pattern labels."""
    try:
        from src.ztare.research_director.pattern_action_contract import (
            build_pattern_action_contract,
        )
        from src.ztare.research_director.primitive_operator_cards import (
            render_obligation_classes,
            render_operator_cards,
            route_obligation_classes,
            route_operator_cards,
        )
        goal = os.environ.get("ZTARE_TICK_GOAL") or os.environ.get("RD_TICK_GOAL")
        contract = build_pattern_action_contract(scope=scope, goal=goal)
        context = " ".join(part for part in (scope or "", goal or "") if part)
        obligations = route_obligation_classes(context=context, top_n=2)
        cards = route_operator_cards(context=context, top_n=2)
    except Exception as exc:
        print(f"  ERROR: pattern action contract unavailable: {exc}")
        return 1

    print("  kernel action contract:")
    print("    source: src/ztare/research_director/pattern_action_contract.py")
    print("    close payload artifact: generate with "
          "`python -m src.ztare.research_director.pattern_action_contract "
          "--out <payload>/artifacts/pattern_action_contract.json`")
    print(f"    problem surfaces: {', '.join(contract.problem_surfaces)}")
    if getattr(contract, "obligation_spine", None):
        print(f"    obligation spine: {', '.join(contract.obligation_spine)}")
    print("    pattern chain:")
    for item in contract.pattern_chain[:8]:
        print(f"      - {item}")
    if contract.anti_patterns:
        print("    anti-pattern guards:")
        for item in contract.anti_patterns[:8]:
            print(f"      - {item}")
    print("    route tests:")
    for item in contract.route_tests[:4]:
        print(f"      - {item}")
    print("    required evidence carriers before close:")
    for carrier in contract.evidence_carriers:
        req = "required" if carrier.required else "optional"
        print(f"      - {carrier.name} ({req}) -> {carrier.artifact_slot}: "
              f"{carrier.acceptance_check}")
        if getattr(carrier, "required_fields", None):
            print("        action-constraint fields: "
                  f"{', '.join(carrier.required_fields)}")
            print("        close mode: prefer carrier_schema_receipts structured "
                  "object; legacy carrier_artifacts ref is fallback only")
    print("    decision rule:")
    print(f"      {contract.decision_rule}")
    print("    stop rule:")
    print(f"      {contract.stop_rule}")
    print("    evidence-backed surfacing rule:")
    print("      Use this as an artifact-field compiler and consumer handoff; "
          "do not treat menu labels as proof of better first-action routing.")
    print("      H35-H47: expose compact execution fields to RD agents; keep full "
          "source-cue receipts in audit metadata; shadow outside-specific "
          "expansion with orchestration_shadow_log.py until drift/refusal is "
          "measured, and run orchestration_contract_gate.py before executing "
          "compact contracts.")
    print("      Menu policy is currently only deterministic-screening-positive as memory+sequencing; live transparent-packet and cue-stripped reruns did not show incremental gain, so "
          "for recurrence risk, pair it with project memory instead of using it standalone.")
    print("      Anti-patterns are pre-mortem guards: require exact missing-or-paid "
          "preventive receipts, nearest-confuser rejection, minimal preventive "
          "artifacts, and clean-proceed conditions, not blanket stops.")
    print("      Boundary-card validation: python -m "
          "src.ztare.research_director.boundary_card_gate <card.json> "
          "--source-facts-file <source.txt>")
    print("      Boundary-card repair tracing after rejection: python -m "
          "src.ztare.research_director.boundary_card_repair_trace "
          "<trace.json> --append")
    print("      PDE work-unit validation: python -m "
          "src.ztare.research_director.pde_work_unit_gate <payload.json>")
    print("  V128 coarse obligation spine:")
    print(render_obligation_classes(obligations))
    print("  compact operator-card routing (fine handles; contract above enforces evidence):")
    print(render_operator_cards(cards))
    print("  anti-sprawl rule: keep old catalog surfacing as recall/coverage; "
          "tighten existing cards/contracts before adding new surfaces.")
    print("  V128 primitive policy:")
    print("    route machinery on coarse obligation classes; use fine op/card")
    print("    labels as human recognition, retrieval, and confuser handles.")
    print("    GP-219 pec_a/pec_b/pec_e remain frozen portable receipt schemas;")
    print("    cand_g is not promoted while it remains confused with core_01.")
    print("  receipt-gate discipline:")
    print("    route <=3 candidate operators, select one, name the nearest")
    print("    confuser, fill required receipts, and mark repair_required")
    print("    action target must be inferred from source facts; do not")
    print("    let proposed-update/check-menu wording supply the route.")
    print("    on receipt misses before continuing.")
    print("    hard reject only when a named wrong-path confuser is followed")
    print("    or repair exposes a blocking missing discriminator.")
    print("    MM/self-referential repairs need explicit nearest-confuser")
    print("    rejection before downstream acceptance.")
    print("  evidence basis: epistemic-generation/research_log.md")
    print("    V54/MM-V7: target receipt gates rejected polished near-misses")
    print("    that generic quality gates accepted.")
    print("    V55/MM-V8: target receipt feedback repaired wrong-path")
    print("    artifacts better than generic repair.")
    print("    V183b: V128 lowered near-miss false accepts but over-rejected")
    print("    positives as a hard gate; use it as nudge/repair trigger.")
    print("    V183b-light: repair-oriented V128 restored positive recall,")
    print("    but became too permissive on MM near-misses without the")
    print("    nearest-confuser check.")
    print("    2026-05-23 HES: proposed-update/check-menu wording collapsed")
    print("    V35 typed/generic/placebo separation to a 9/9 ceiling in all")
    print("    arms; hide the action-family shortcut in future endpoints.")
    print("    V177/V177R: downstream-action payment came from source-bound")
    print("    action-constraint content; schema names help as scaffold but")
    print("    did not beat delabeled constraint values in that packet.")
    print("    Operational reading: use small routed operator sets +")
    print("    nearest-confuser receipts plus action-constraint fields, not")
    print("    larger menus or vocabulary blocks.")
    return 0 if cards else 1


def structural_vocabulary_fingerprint(scope: str | None = None) -> int:
    """Surface the structural mechanism language RD must use in closure.

    The pattern menu chooses the next move. This layer names the mechanism:
    universal research ops for all substrates, TB/PS culture split when the
    work is mathematical or method-building, GP-219 estimate-craft ops when
    the substrate is PDE / analysis leaning, and portable GP-219 receipt
    candidates when their schema appears outside PDE.
    """
    status = 0
    print("  canonical files:")
    for path in (
        STRUCTURAL_LANGUAGE_CATALOG,
        UNIVERSAL_RESEARCH_OPS,
        THEORY_BUILDING_OPS,
        PROBLEM_SOLVING_OPS,
        PDE_ESTIMATE_CRAFT_OPS,
        TWO_CULTURES,
    ):
        rel = path.relative_to(REPO)
        exists = path.exists()
        print(f"    - {rel}: {'present' if exists else 'MISSING'}")
        if not exists:
            status = 1

    try:
        sys.path.insert(0, str(REPO))
        from src.ztare.research_director.structural_fingerprint import (
            build_structural_fingerprint,
            fingerprint_to_dict,
        )
        from src.ztare.research_director.pde_estimate_craft_ops import (
            VOCABULARY_GP219,
            portable_receipt_candidates,
        )
        from src.ztare.research_director.problem_solving_ops import VOCABULARY_PS_V1
        from src.ztare.research_director.theory_building_ops import VOCABULARY_V3
        from src.ztare.research_director.two_cultures import CROSS_DISTRIBUTION_2X2
        from src.ztare.research_director.universal_research_ops import (
            META_META_VOCABULARY,
            VOCABULARY_V4,
        )
        print("  vocabulary counts:")
        print(f"    universal v5/v4 ops: {len(VOCABULARY_V4)}")
        print(f"    meta-meta reframe ops: {len(META_META_VOCABULARY)}")
        print(f"    theory-building ops: {len(VOCABULARY_V3)}")
        print(f"    problem-solving ops: {len(VOCABULARY_PS_V1)}")
        print(f"    PDE estimate-craft ops: {len(VOCABULARY_GP219)}")
        print(f"    portable estimate-craft receipt candidates: "
              f"{len(portable_receipt_candidates())}")
        sample = build_structural_fingerprint(
            "NS closure attempt with bound chain, potential function, "
            "auxiliary defect measure, threshold dichotomy, and limit passage.",
            substrate=scope or "global",
            evidence_pointer="rd_tick_brief_sample",
            next_move_effect="select workbench gates before Director dispatch",
            max_ops=3,
        )
        sample_dict = fingerprint_to_dict(sample)
        print("  executable fingerprint sample:")
        print(f"    universal_ops: {[op['op_id'] for op in sample_dict['universal_ops']]}")
        pde_ops = sample_dict["pde_ops_or_not_applicable"]
        if isinstance(pde_ops, list):
            print(f"    pde_ops: {[op['op_id'] for op in pde_ops]}")
        else:
            print(f"    pde_ops: {pde_ops}")
        print("    portable_receipt_ops: "
              f"{[op['op_id'] for op in sample_dict['portable_receipt_ops']]}")
        for op in sample_dict["portable_receipt_ops"][:3]:
            if op.get("nearest_universal_ops"):
                print(
                    "      overlap "
                    f"{op['op_id']} -> {op['nearest_universal_ops']} "
                    f"status={op.get('overlap_status') or 'unknown'}"
                )
        print(f"    placement: {sample_dict['mechanization_placement'][:3]}")
        print("  empirical TB/PS split:")
        print(
            "    TB vocab: "
            f"{CROSS_DISTRIBUTION_2X2['tb_vocab']['tb_corpus_pct']}% on TB corpus, "
            f"{CROSS_DISTRIBUTION_2X2['tb_vocab']['ps_corpus_pct']}% on PS corpus"
        )
        print(
            "    PS vocab: "
            f"{CROSS_DISTRIBUTION_2X2['ps_vocab']['tb_corpus_pct']}% on TB corpus, "
            f"{CROSS_DISTRIBUTION_2X2['ps_vocab']['ps_corpus_pct']}% on PS corpus"
        )
    except Exception as e:
        print(f"  WARN: structural vocabulary import failed: {e}")
        status = 1

    scope_norm = _norm_scope(scope)
    pde_scope = any(
        token in scope_norm
        for token in (
            "ns",
            "navier",
            "stokes",
            "pde",
            "millennium",
            "geometric_flow",
            "analysis",
            "harmonic",
        )
    )
    print("  RD closure rule:")
    print("    Every F-row / closure artifact should include `structural_language_fingerprint`.")
    print("    Minimum fields: universal_ops, tb_ps_culture, pde_ops_or_not_applicable,")
    print("      portable_receipt_ops, evidence_pointer, and why the vocabulary changes the next move.")

    if pde_scope:
        print("  scope hint for PDE/analysis substrate:")
        print("    Use universal v5 + GP-219 together. Do not use v5 alone when estimate craft")
        print("    is the mechanism. If pec_a / pec_c / pec_d appears, run or cite the shipped")
        print("    auxiliary-object, threshold-dichotomy, or limit-passage gate.")
    else:
        print("  scope hint for non-PDE substrate:")
        print("    Use universal v5 + TB/PS split. GP-219 is not required wholesale.")
        print("    pec_a/pec_b/pec_e/cand_g may be cited only as portable receipt")
        print("    schemas when the artifact fills their action-constraint fields and rejects the")
        print("    nearest confuser.")

    print("  portable-receipt boundary rule:")
    print("    Treat pec_a/pec_b/pec_e/cand_g as schema add-ons over GP-216 until")
    print("    a consequence endpoint proves a universal-op gap. Record nearest")
    print("    universal op, nearest pec/cand confuser, action-constraint fields, and promotion")
    print("    test in the structural_language_fingerprint.")

    print("  substrate-specific fingerprints:")
    print("    Keep current-state substrate fingerprints in substrate graphs, ledgers,")
    print("    and closure artifacts. This tick only surfaces generic vocabulary rules.")

    print("  RD rule: pattern choice and structural-language fingerprint are separate.")
    print("  Pattern = how to move next; structural language = what mechanism was found.")
    return status


def ns_graph_precheck() -> int:
    """Refresh NS graph/miner triage for math-substrate RD ticks."""
    try:
        # NS-substrate policy (2026-05-17): NS files live in the
        # millennium-hunt project tree, not src/ztare/research_director.
        # That dir is not an importable package → load by path.
        import importlib.util
        _ngt = (REPO / "projects" / "ns_millennium_hunt" / "scripts"
                / "ns_graph_tick.py")
        if not _ngt.is_file():
            raise FileNotFoundError(
                f"ns_graph_tick.py not at {_ngt} (NS-substrate move)")
        _spec = importlib.util.spec_from_file_location(
            "ns_graph_tick", _ngt)
        _mod = importlib.util.module_from_spec(_spec)
        # Must be in sys.modules BEFORE exec: @dataclass resolves
        # cls.__module__ via sys.modules (else AttributeError on None).
        sys.modules["ns_graph_tick"] = _mod
        _spec.loader.exec_module(_mod)
        render_text = _mod.render_text
        run_ns_graph_tick = _mod.run_ns_graph_tick
        summary = run_ns_graph_tick()
        print(render_text(summary))
        return 0 if summary.ok else 1
    except Exception as e:
        print(f"  ERROR: NS graph precheck failed: {e}")
        return 1


def neural_hunt_graph_precheck() -> int:
    """Refresh and validate the neural_hunt basin graph for RD ticks."""
    script = REPO / "projects/neural_hunt/scripts/neural_hunt_basin_graph.py"
    graph_path = REPO / "analytics/public/queries/neural_hunt/neural_hunt_basin_graph.json"
    if not script.exists():
        print(f"  ERROR: neural_hunt graph builder missing: {script.relative_to(REPO)}")
        return 1

    proc = subprocess.run(
        [sys.executable, str(script), "build"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        print("  ERROR: neural_hunt graph build failed")
        if proc.stdout.strip():
            print(proc.stdout.strip()[:2000])
        if proc.stderr.strip():
            print(proc.stderr.strip()[:2000])
        return 1

    try:
        graph = json.loads(graph_path.read_text())
    except Exception as e:
        print(f"  ERROR: neural_hunt graph output unreadable: {e}")
        return 1

    queries = graph.get("queries") or {}
    frontier_query = queries.get("frontier") or {}
    frontier = frontier_query.get("next_action") or {}
    rotation_plan = frontier_query.get("rotation_plan") or {}
    source_acquisition_queue = frontier_query.get("source_acquisition_queue") or {}
    if_gpu_blocked = frontier_query.get("if_gpu_blocked") or []
    source_class_status = queries.get("source-class-status") or {}
    required_gates = queries.get("post-output-required-gates") or []
    branch_required_gates = queries.get("branch-required-gates") or {}
    law_forbidden = (queries.get("law-promotion-forbidden") or {}).get("verdict")
    dirty = graph.get("dirty_evidence") or {}
    dirty_projects = len(dirty.get("related_projects") or [])
    dirty_rows = len(dirty.get("ledger_rows") or [])

    print(f"  graph: {graph_path.relative_to(REPO)}")
    print(f"  status: {graph.get('status')}")
    print(f"  frontier: {frontier.get('id')} — {frontier.get('label')}")
    if frontier.get("path"):
        print(f"  frontier path: {frontier.get('path')}")
    if rotation_plan:
        print(f"  rotation plan: {rotation_plan.get('id')} — {rotation_plan.get('label')}")
    if source_acquisition_queue:
        print(
            "  source acquisition queue: "
            f"{source_acquisition_queue.get('id')} — {source_acquisition_queue.get('label')}"
        )
    if if_gpu_blocked:
        print("  if GPU blocked/null:")
        for item in if_gpu_blocked:
            print(f"    - {item.get('id')} — {item.get('label')}")
    if source_class_status:
        print("  source-class status:")
        for source_class, status in sorted(source_class_status.items()):
            print(f"    - {source_class}: {status}")
    print(f"  required post-output gates: {', '.join(required_gates)}")
    if branch_required_gates:
        print("  branch gates:")
        for action_id, gates in sorted(branch_required_gates.items()):
            print(f"    - {action_id}: {', '.join(gates)}")
    print(f"  law-promotion-forbidden: {law_forbidden}")
    print(f"  dirty evidence sources: {dirty_projects} projects, {dirty_rows} ledger rows")

    ok = (
        frontier.get("kind") == "next_action"
        and bool(frontier.get("id"))
        and bool(frontier.get("path"))
        and required_gates == ["gate.H23", "gate.H24"]
        and law_forbidden is True
    )
    if not ok:
        print("  ERROR: neural_hunt graph precheck failed invariant validation")
        return 1
    return 0


def ns_amnesia_anchor_module_precheck() -> int:
    """RD-role substrate MODULE (loaded because role=RD-for-NS in the
    ztare-research-co tenant overlay): NS amnesia basin + vocabulary-
    drift-proof structural anchor + O(1) residual manifest +
    pre-hard-claim gate. Kernel/role-module split (product thinking):
    the UNIVERSAL micro-forecast/MECE pre-post protocol lives in §8
    (kernel, all agents); this is ONLY the NS tenant module surfacing.
    Mirrors ns_graph_precheck's role-driven load pattern."""
    import subprocess
    try:
        r = subprocess.run(
            [sys.executable,
             str(REPO / "projects/ns_millennium_hunt/scripts/ns_scientific_amnesia_precheck.py"),
             "--query", "RD pre-tick NS module (amnesia + structural anchor + residual manifest)"],
            capture_output=True, text=True, timeout=60)
        print(r.stdout)
        return r.returncode
    except Exception as e:
        print(f"  ERROR: NS amnesia/anchor RD-role module failed: {e}")
        return 1


SUBSTRATE_MODULE_REGISTRY = [
    {
        "name": "NS amnesia/anchor/manifest RD-role module",
        "aliases": ("ns", "ns_track_b", "ns_cross_lane", "ns_millennium_hunt"),
        "runner": ns_amnesia_anchor_module_precheck,
    },
]


def substrate_module_precheck(scope: str | None) -> int:
    """Load the RD-role substrate MODULE for this scope (role-driven).

    Mirrors substrate_graph_precheck: the RD-role mandate surfaces the
    universal kernel (§8); the agent, by its role's substrate scope,
    loads the matching tenant module here. No registered module ⇒
    dispatch allowed (substrate declares none)."""
    scope_norm = _norm_scope(scope)
    global_scope = scope_norm in {"", "all", "global"}
    matched = [
        e for e in SUBSTRATE_MODULE_REGISTRY
        if global_scope or any(a in scope_norm for a in e["aliases"])
    ]
    if not matched:
        print(f"  No RD-role substrate module registered for scope `{scope or 'global'}`.")
        return 0
    status = 0
    for e in matched:
        print(f"  Loading {e['name']} (role-driven; kernel protocol in §8)")
        status = int(e["runner"]()) or status
    return status


GRAPH_PRECHECK_REGISTRY = [
    {
        "name": "NS graph/miner precheck",
        "aliases": ("ns", "ns_track_b", "ns_cross_lane", "ns_millennium_hunt"),
        "runner": ns_graph_precheck,
    },
    {
        "name": "neural_hunt basin graph precheck",
        "aliases": ("neural_hunt", "gp154"),
        "runner": neural_hunt_graph_precheck,
    },
]


def substrate_graph_precheck(scope: str | None) -> int:
    """Run graph prechecks registered for this substrate scope.

    Graph refreshes are mandatory when a substrate declares one, but they must
    be substrate-scoped. A neural_hunt tick should not run the NS graph unless
    neural_hunt explicitly registers that graph.
    """
    scope_norm = _norm_scope(scope)
    global_scope = scope_norm in {"", "all", "global"}
    matched = [
        entry for entry in GRAPH_PRECHECK_REGISTRY
        if global_scope or any(alias in scope_norm for alias in entry["aliases"])
    ]
    if not matched:
        print(f"  No registered graph precheck for scope `{scope or 'global'}`.")
        print("  Dispatch is allowed because no substrate graph runner is declared.")
        return 0

    status = 0
    for entry in matched:
        print(f"  Running {entry['name']}")
        status = int(entry["runner"]()) or status
    return status


def gnn_advisory_precheck(scope: str | None = None) -> int:
    """Surface frozen GNN lemma-ranker advisory state for RD ticks.

    Optional consumption: this section is intended to help the Director choose
    premises and local targets, but it must not hard-stop dispatch. Overfit,
    endpoint, or missing-artifact risks are warnings unless the operator
    explicitly promotes this lane to a mandatory gate later.
    """
    scope_norm = _norm_scope(scope)
    if scope_norm and not any(
        token in scope_norm
        for token in ("all", "global", "ns", "navier", "stokes", "lean", "math")
    ):
        print(f"  No registered GNN advisory precheck for scope `{scope}`.")
        return 0

    script = REPO / "scripts/public/control/rd_tick_gnn_precheck.py"
    if not script.exists():
        print(f"  WARN: GNN advisory precheck missing: {script.relative_to(REPO)}")
        return 0
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0:
        print("  WARN: GNN advisory precheck failed; continuing because consumption is optional")
        if proc.stderr.strip():
            print(proc.stderr.strip()[:2000])
        return 0
    if proc.stderr.strip():
        print(proc.stderr.strip()[:2000])
    return 0


def primitive_surface_precheck(scope: str | None = None) -> int:
    """Surface available ZTARE primitives for the current RD tick."""
    try:
        sys.path.insert(0, str(REPO))
        from src.ztare.research_director.primitive_tick_surface import (
            excluded_terms_for_scope,
            query_terms_for_scope,
            render_text,
            write_primitive_tick_surface,
        )
        surface = write_primitive_tick_surface(
            query_terms=query_terms_for_scope(scope),
            excluded_terms=excluded_terms_for_scope(scope),
        )
        print(render_text(surface))
        return 0 if surface.ok else 1
    except Exception as e:
        print(f"  ERROR: primitive surface failed: {e}")
        return 1


def post_tick_gate_precheck() -> int:
    """GAP-C (2026-05-15): mechanical teeth for the post-tick gate.

    Until now "post_tick_check exit 1 -> next pre-tick blocks dispatch"
    was mandate PROSE — rd_tick_brief never read post_tick_check. This
    reads the state post_tick_check.py persists and HARD-BLOCKS (return 1)
    the next dispatch when the previous tick's close-out did not clear.
    Missing/stale state -> advisory only (never brick on a first run /
    missing file; the FAILED case is the teeth).
    """
    state_p = REPO / "analytics/public/forecast_pool/status/post_tick_state.json"
    if not state_p.exists():
        print("  no prior post_tick_check state — run "
              "scripts/public/control/post_tick_check.py at tick close "
              "(advisory; not blocking a first run)")
        return 0
    try:
        st = json.loads(state_p.read_text())
    except Exception as e:
        print(f"  post_tick state unreadable ({e}) — advisory, not blocking")
        return 0
    ran = st.get("ran_at", "?")
    if not st.get("passed", True):
        print(f"  BLOCK: previous post_tick_check ({ran}) did NOT clear — "
              f"{st.get('hard_fail_count', 0)} hard obligation(s) open:")
        for x in st.get("hard_fail", [])[:6]:
            print(f"    - {x}")
        print("  Resolve them so post_tick_check exits 0 before new dispatch "
              "(GAP-C mechanical block).")
        return 1
    try:
        age_h = (datetime.now(timezone.utc)
                 - datetime.fromisoformat(ran)).total_seconds() / 3600
        msg = (f"stale ({age_h:.0f}h) — re-run at next close (advisory)"
               if age_h > 24 else "clean")
    except Exception:
        msg = "clean"
    print(f"  previous post_tick_check {msg} ({ran})")
    return 0


def autoresearch_workbench_router_surface(
    *,
    task: str | None = None,
    project: str | None = None,
    rubric: str | None = None,
    bounded_claim: bool | None = None,
    stable_evaluator: bool | None = None,
    rubric_ready: bool | None = None,
    artifact_surface: bool | None = None,
    subscription_worker_available: bool | None = None,
) -> int:
    """Surface the RD decision to use autoresearch as an in-loop workbench."""
    try:
        sys.path.insert(0, str(REPO))
        from src.ztare.research_director.autoresearch_workbench_router import (
            route_autoresearch_workbench_from_context,
        )
        from src.ztare.research_director.primitive_operator_cards import (
            render_operator_cards,
            route_operator_cards,
        )
    except Exception as exc:
        print(f"  ERROR: autoresearch workbench router unavailable: {exc}")
        return 1

    workbench_summary: dict | None = None
    try:
        from src.ztare.reports.operations_intelligence import summarize_agentic_workbench

        workbench_summary = summarize_agentic_workbench(
            _read_jsonl_silent(ACTION_IMPACT_LEDGER),
            bifurcation_report=_read_json_silent(BIFURCATION_REPORT),
        )
    except Exception as exc:
        print(f"  WARN: workbench route-coverage summary unavailable: {exc}")

    task = (
        task
        or _first_env("RD_WORKBENCH_TASK", "ZTARE_TICK_GOAL", "RD_TICK_GOAL")
        or "current RD task"
    )
    project = project or _first_env(
        "ZTARE_AUTORESEARCH_PROJECT",
        "RD_AUTORESEARCH_PROJECT",
        "PROJECT",
    )
    rubric = rubric or _first_env(
        "ZTARE_AUTORESEARCH_RUBRIC",
        "RD_AUTORESEARCH_RUBRIC",
        "RUBRIC",
    )
    project_path = _resolve_project_path(project)
    rubric_path = _resolve_rubric_path(rubric)

    env_bounded = _env_bool("ZTARE_WORKBENCH_BOUNDED_CLAIM")
    env_stable = _env_bool("ZTARE_WORKBENCH_STABLE_EVALUATOR")
    env_rubric = _env_bool("ZTARE_WORKBENCH_RUBRIC_READY")
    env_artifact = _env_bool("ZTARE_WORKBENCH_ARTIFACT_SURFACE")
    env_subscription = _env_bool("ZTARE_SUBSCRIPTION_WORKER_AVAILABLE")

    if bounded_claim is None:
        bounded_claim = env_bounded
    if stable_evaluator is None:
        stable_evaluator = env_stable
    if rubric_ready is None:
        rubric_ready = env_rubric
    if artifact_surface is None:
        artifact_surface = env_artifact
    if subscription_worker_available is None:
        subscription_worker_available = env_subscription
    subscription_worker_available = bool(subscription_worker_available)

    decision = route_autoresearch_workbench_from_context(
        task,
        project=project or "",
        rubric=rubric or "",
        stable_evaluator=stable_evaluator,
        bounded_claim=bounded_claim,
        rubric_ready=rubric_ready,
        artifact_surface=artifact_surface,
        subscription_worker_available=subscription_worker_available,
        repo_root=REPO,
    )
    print("  source: src/ztare/research_director/autoresearch_workbench_router.py")
    print(f"  task: {task}")
    print(f"  project: {project or '<unset>'}"
          + (f" ({project_path.relative_to(REPO)})" if project_path and project_path.exists() else ""))
    print(f"  rubric: {rubric or '<unset>'}"
          + (f" ({rubric_path.relative_to(REPO)})" if rubric_path and rubric_path.exists() else ""))
    print("  inferred/declared feature bits:")
    print(f"    bounded_claim={decision.bounded_claim}")
    print(f"    stable_evaluator={decision.stable_evaluator}")
    print(f"    rubric_ready={decision.rubric_ready}")
    print(f"    artifact_surface={decision.artifact_surface}")
    print(f"    subscription_worker_available={decision.subscription_worker_available}")
    print("  router decision:")
    print(f"    decision={decision.decision} confidence={decision.confidence:.2f}")
    if decision.reasons:
        print(f"    reasons={'; '.join(decision.reasons)}")
    if decision.missing:
        print(f"    missing={'; '.join(decision.missing)}")
    print(f"    next={decision.suggested_next_step}")
    card_context = " ".join(
        part
        for part in (
            "autoresearch_workbench_routing",
            task,
            project or "",
            rubric or "",
            decision.decision,
            " ".join(decision.missing),
        )
        if part
    )
    print("  typed operator-card surface:")
    print(render_operator_cards(route_operator_cards(context=card_context, top_n=2)))
    if decision.decision == "invoke_autoresearch" and project and rubric:
        print("  run surface:")
        print(f"    ztare autoresearch run --project {project} --rubric {rubric}")
        print(f"    ztare autoresearch projection --project {project}")
        print("  close receipt:")
        print("    workbench_evidence_ref=<autoresearch-run-or-projection-artifact>")
    elif decision.decision == "prepare_autoresearch_surface":
        print("  prepare surface before treating manual agent work as primary evidence:")
        print("    create/fix the missing evaluator, rubric, or artifact surface; then rerun this brief")
        if decision.surface_scaffold:
            print("  missing-surface scaffold:")
            for row in decision.surface_scaffold[:4]:
                fields = ", ".join(str(f) for f in row.get("required_fields", [])[:4])
                print(f"    - {row.get('surface')}: {row.get('artifact')}")
                print(f"      fields={fields}")
                print(f"      check={row.get('acceptance_check')}")
    else:
        print("  stay out of loop only for exploratory definition work; reroute once a bounded claim exists")
        if decision.surface_scaffold:
            print("  first surfaces to create before rerouting:")
            for row in decision.surface_scaffold[:2]:
                fields = ", ".join(str(f) for f in row.get("required_fields", [])[:3])
                print(f"    - {row.get('surface')}: {row.get('artifact')} ({fields})")

    if decision.decision == "invoke_autoresearch":
        print("  if the ready workbench is bypassed, record the bypass:")
        selected_action = "run_out_of_loop_agent"
        why_hint = "<cost-or-capability-reason-for-bypassing-ready-workbench>"
    elif decision.decision == "prepare_autoresearch_surface":
        print("  record the surface-preparation decision when it consumes RD/out-of-loop work:")
        selected_action = "prepare_autoresearch_surface"
        why_hint = "<missing-surface-being-prepared>"
    else:
        print("  record the exploratory stay-out decision:")
        selected_action = "stay_out_of_loop"
        why_hint = "<why-no-bounded-autoresearch-surface-yet>"
    print("    ztare autoresearch route \\")
    print(f"      --task {shlex.quote(task)} \\")
    if project:
        print(f"      --project {shlex.quote(project)} \\")
    if rubric:
        print(f"      --rubric {shlex.quote(rubric)} \\")
    print("      --record-decision-id DECISION_ID \\")
    print(f"      --selected-action {selected_action} \\")
    print(f"      --why-not-autoresearch {shlex.quote(why_hint)}")
    print("  fallback for a pre-saved route JSON:")
    print("    ztare autoresearch route \\")
    print(f"      --task {shlex.quote(task)} \\")
    if project:
        print(f"      --project {shlex.quote(project)} \\")
    if rubric:
        print(f"      --rubric {shlex.quote(rubric)} \\")
    print("      > /tmp/autoresearch_route.json")
    print("    ztare action-intel record-agentic-route \\")
    print("      --route-json /tmp/autoresearch_route.json --decision-id DECISION_ID \\")
    print(f"      --selected-action {selected_action} \\")
    print(f"      --why-not-autoresearch {shlex.quote(why_hint)}")
    if workbench_summary:
        bif = workbench_summary.get("reflexive_bifurcation") or {}
        coverage = workbench_summary.get("route_row_coverage") or {}
        out_share = bif.get("out_of_loop_share")
        in_share = bif.get("in_loop_share")
        ratio = coverage.get("route_rows_per_1k_agent_artifacts")
        print("  route logging coverage:")
        print(
            f"    route_rows={workbench_summary.get('rows', 0)} "
            f"out_of_loop_share={out_share if out_share is not None else '<unknown>'} "
            f"in_loop_share={in_share if in_share is not None else '<unknown>'} "
            f"rows_per_1k_agent_artifacts={ratio if ratio is not None else '<unknown>'}"
        )
        print(f"    status={coverage.get('status', 'unknown')}")
        if coverage.get("needs_logging_attention"):
            print(
                "    ATTENTION: reflexive mining shows substantial out-of-loop work, "
                "but agentic-workbench route rows are missing or sparse."
            )
            print(
                "    Before continuing out of loop, run the route command above and "
                "record the selected action unless the work is pure scratch."
            )
    return 0


def eigenquestion_rotation_surface(project: str | None) -> int:
    """Surface advisory eigenquestion proposals for the selected project.

    Eigenquestion generation is deliberately not an automatic charter rewrite.
    This brief section makes pending proposals visible so RD/operator work can
    decide whether to merge, reject, or supersede them before the next run.
    """

    project_path = _resolve_project_path(project)
    if project_path is None:
        print("  project: <not provided>")
        print("  status: skipped — pass --autoresearch-project to inspect proposals")
        return 0
    print(f"  project: {project_path}")
    if not project_path.exists():
        print("  status: project_missing")
        return 0

    proposals = sorted(
        project_path.glob("proposed_eigenquestion_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    charter = project_path / "project_charter.md"
    charter_mtime = charter.stat().st_mtime if charter.exists() else 0.0
    if not proposals:
        print("  status: no proposed_eigenquestion_*.md files")
        print(
            "  generate: ztare eigenquestion propose "
            f"--project {shlex.quote(project_path.name)}"
        )
        return 0

    now_ts = datetime.now(timezone.utc).timestamp()
    pending = [p for p in proposals if not charter.exists() or p.stat().st_mtime > charter_mtime]
    print(
        f"  proposals: {len(proposals)} "
        f"(pending_newer_than_charter={len(pending)}, charter_exists={charter.exists()})"
    )
    for path in proposals[:3]:
        age_h = max(0.0, (now_ts - path.stat().st_mtime) / 3600.0)
        status = (
            "pending_review"
            if (not charter.exists() or path.stat().st_mtime > charter_mtime)
            else "older_than_charter"
        )
        print(f"    - {path.name}: {status}, age={age_h:.1f}h")
    if len(proposals) > 3:
        print(f"    ...and {len(proposals) - 3} more")

    print("  discipline: advisory only; merge/reject/supersede in project_charter.md intentionally")
    print(
        "  validate explored-class negative-evidence rows before merge: "
        f"ztare eigenquestion validate --project {shlex.quote(project_path.name)}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--short", action="store_true",
                        help="One-screen scan (less mandate detail)")
    parser.add_argument("--vps", action="store_true",
                        help="VPS-agent launch wrapper format (machine-friendly)")
    parser.add_argument("--last-n-catches", type=int, default=5)
    parser.add_argument("--last-n-pls", type=int, default=5)
    parser.add_argument("--blocking-substrate", default=None,
                        help=(
                            "Only unresolved Tier-1 PL rows whose substrate contains "
                            "this identifier hard-stop dispatch. Other fresh Tier-1 "
                            "rows remain warning-only. Use all/global for legacy behavior."
                        ))
    parser.add_argument("--skip-substrate-graph-precheck", action="store_true",
                        help="Skip registered substrate graph prechecks.")
    parser.add_argument("--skip-ns-graph-precheck", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--skip-primitive-surface", action="store_true",
                        help="Skip RD primitive discoverability surface.")
    parser.add_argument("--skip-gnn-precheck", action="store_true",
                        help="Skip frozen GNN advisory precheck.")
    parser.add_argument("--skip-workbench-router", action="store_true",
                        help="Skip autoresearch workbench router surfacing.")
    parser.add_argument("--workbench-task",
                        help="Task text for the autoresearch workbench router.")
    parser.add_argument("--autoresearch-project",
                        help="Project slug/path for autoresearch router inference.")
    parser.add_argument("--autoresearch-rubric",
                        help="Rubric slug/path for autoresearch router inference.")
    parser.add_argument("--subscription-worker-available",
                        action=argparse.BooleanOptionalAction,
                        default=None,
                        help="Declare a subscription-backed fungible worker for autoresearch.")
    parser.add_argument("--workbench-bounded-claim",
                        action=argparse.BooleanOptionalAction,
                        default=None)
    parser.add_argument("--workbench-stable-evaluator",
                        action=argparse.BooleanOptionalAction,
                        default=None)
    parser.add_argument("--workbench-rubric-ready",
                        action=argparse.BooleanOptionalAction,
                        default=None)
    parser.add_argument("--workbench-artifact-surface",
                        action=argparse.BooleanOptionalAction,
                        default=None)
    parser.add_argument("--allow-no-owner", action="store_true",
                        help="Permit a non-owner-scoped brief for "
                             "NON-tick informational use ONLY. The tick "
                             "pre-brief path MUST set RD_OWNER; this "
                             "escape exists so bare doc/inspection runs "
                             "are not refused by the Tier-1 punisher.")
    args = parser.parse_args()

    # Tier-1 NEXT-TICK PUNISHER (2026-05-16): a fail-closed tick_close
    # the agent must voluntarily call guarantees nothing. This makes
    # SKIPPING it self-defeating — refuse to brief a new tick unless the
    # PREVIOUS tick was closed via tick_close.py (owner-keyed stamp).
    # Conservative: bootstrap / unreadable / no-owner-on-non-strict →
    # never false-block (degrade to advisory, mirrors codebase rule).
    try:
        import os as _os
        _owner = _os.environ.get("RD_OWNER")
        if not _owner:
            # RE-REVIEW must-fix: unset RD_OWNER must NOT silently
            # skip the punisher (that single env var was the bypass /
            # gloss one level up). Unset ⇒ REFUSE — making "don't set
            # RD_OWNER" itself self-defeating. (Bare informational
            # invocations should pass --allow-no-owner explicitly; the
            # tick pre-brief path must be owner-scoped.)
            if not getattr(args, "allow_no_owner", False):
                print("# RD-Tick Brief — REFUSED\n")
                print("🛑 PRE-TICK REFUSED (Tier-1): RD_OWNER unset. The "
                      "tick pre-brief MUST be owner-scoped (an unset "
                      "RD_OWNER was the one-env-var bypass of the "
                      "next-tick punisher). Set RD_OWNER=<id> (or pass "
                      "--allow-no-owner ONLY for non-tick informational "
                      "use).")
                return 1
        if _owner:
            _src = str(REPO / "src")
            if _src not in sys.path:
                sys.path.insert(0, _src)
            from ztare.validator.tick_close_gate import previous_tick_closed
            _ok, _why = previous_tick_closed(_owner)

            def _membrane_nudge(reason: str) -> None:
                # The NUDGE (2026-05-18): the gate refusal is opaque —
                # even the apparatus's own builder hand-cranked and hit
                # H4 because the EXACT next step was not surfaced at the
                # point of action. Run the read-only membrane_state
                # oracle on the owner's open tick and print STATE +
                # exact next legal step HERE, in the tick surface.
                # Advisory, read-only, fail-safe (never blocks).
                try:
                    import re as _re
                    import runpy as _rp
                    m = _re.search(r"F-row ['\"]([^'\"]+)['\"]", reason) \
                        or _re.search(r"['\"](F-[^'\" ]+)['\"]", reason)
                    if not m:
                        return
                    _tid = m.group(1)
                    _ms = _rp.run_path(
                        str(REPO / "scripts/public/control/"
                            "membrane_state.py"),
                        run_name="_ms")
                    _st = _ms["derive"](_tid, "", _owner)
                    print(f"  → NEXT-STEP NUDGE [{_tid}]: "
                          f"STATE={_st.get('current_state')} | "
                          f"NEXT={_st.get('next_legal_transition')}")
                    _seq = _st.get("remaining_sequence")
                    if _seq:
                        print(f"     do now: {_seq[0]}")
                    elif _st.get("exact_next_command"):
                        print(f"     do now: "
                              f"{_st.get('exact_next_command')}")
                except Exception as _ne:
                    print(f"  (membrane nudge unavailable, advisory: "
                          f"{_ne})")

            if not _ok:
                # HARD (exit 1): the real upstream over-trip is fixed at
                # source (tick_close_gate now keys on actual tick
                # activity = latest owner F-row vs stamp, NOT global
                # post_tick_state mtime — verification/dogfood post_tick
                # runs no longer trip it). So HARD is correct now, not
                # the GAP-H regression (which was caused by the
                # over-trip, now eliminated).
                print(f"# RD-Tick Brief — REFUSED\n")
                print(f"🛑 PRE-TICK REFUSED (Tier-1 next-tick punisher): "
                      f"{_why}")
                print(f"\nThe previous recorded tick was not closed via "
                      f"`tick_close.py`. Close it first; skipping the "
                      f"close gate blocks the next tick BY DESIGN.")
                _membrane_nudge(_why)
                return 1
            else:
                print(f"  (tick_close_gate: {_why})")
                _membrane_nudge(_why)
    except Exception as _e:
        print(f"  (tick_close_gate degraded, advisory — never "
              f"false-block: {_e})")

    now = datetime.now(timezone.utc).isoformat()
    print(f"# RD-Tick Brief — {now}")
    print()
    print("**This brief is auto-generated by `scripts/public/control/rd_tick_brief.py`.**")
    print("Every RD agent (this session, VPS agent on Hetzner) MUST read")
    print("this at session-start AND before any dispatch decision.")

    section("1. Active mandates")
    mandate_excerpt(args.short)

    section("1b. Tenant overlay precheck")
    tenant_overlay_precheck()

    section("2. Pattern catalog state")
    pattern_state()

    section("2b. Closure-claim discipline linter state")
    closure_claim_discipline_state()

    section("2c. Routine review state (pattern-catalog reconciliation)")
    routine_review_state()

    summary = run_scorer()
    section("3. Diversity scorer state")
    monoculture = diversity_state(summary)

    section(f"4. Last {args.last_n_catches} catches")
    recent_catches(args.last_n_catches)

    section(f"5. Last {args.last_n_pls} unresolved PLs")
    open_pl_rows(args.last_n_pls, scope=args.blocking_substrate)

    section("5b. Prediction closure hygiene")
    prediction_closure_debt = prediction_closure_hygiene(
        blocking_scope=args.blocking_substrate
    )

    section("5c. Post-tick gate (previous tick close-out — GAP-C mechanical block)")
    post_tick_block = post_tick_gate_precheck()

    section("6. PL calibration state")
    calibration_state()

    section("6c. GP-230 forecast-market transport state")
    forecast_market_state()

    section("7. Pre-dispatch checklist")
    predispatch_reminder()

    section("8. Prediction logging discriminator")
    prediction_logging_discriminator_brief()

    section("8b. External GPU/API run surface")
    external_gpu_run_surface()

    section("8c. RD-role substrate module (loaded by agent role)")
    substrate_module_status = substrate_module_precheck(args.blocking_substrate)

    section("8d. Prescription surfacing (gap list IS surfaced here, "
            "not merely counted — a buried gap list is itself the "
            "buried-prescription anti-pattern)")
    try:
        import subprocess as _sp
        _ps = _sp.run(
            [sys.executable, str(REPO / "scripts/public/validators/"
             "validate_prescription_surfacing.py"), "--skip-arch-self"],
            capture_output=True, text=True, timeout=30)
        _lines = [l for l in _ps.stdout.splitlines()
                  if l.startswith(("WARN: surfacing_gap", "INFO: PROMOTE-READY", "OK:"))]
        _gaps = [l for l in _lines if "surfacing_gap" in l]
        _promos = [l for l in _lines if "PROMOTE-READY" in l]
        print(f"  OBLIGATION (not advisory): any surfaced prescription "
              f"whose trigger matches THIS tick MUST be deployed AND "
              f"logged to analytics/public/ledgers/pattern_deployment/"
              f"pattern_deployment_ledger.jsonl this tick — use generates "
              f"the promotion evidence (≥3 distinct substrates ⇒ auto "
              f"PROMOTE-READY ⇒ flip confidence:leaf). Non-use of a "
              f"trigger-matched prescription REQUIRES a one-line deviation "
              f"reason in the F-row; silent non-use = buried-prescription "
              f"violation. If it helps, that IS the evidence to promote.")
        print(f"  {len(_promos)} PROMOTE-READY (flip confidence:leaf NOW), "
              f"{len(_gaps)} prescription(s) with no forcing surfacing — "
              f"BOTH listed so they are SEEN + obligated every pre-tick:")
        for l in _promos:
            print("   ", l.replace("INFO: ", ""))
        for l in _gaps[:40]:
            print("   ", l.replace("WARN: ", ""))
        if len(_gaps) > 40:
            print(f"    … +{len(_gaps)-40} more (run "
                  f"validate_prescription_surfacing.py)")
    except Exception as _e:
        print(f"  (prescription-surfacing surface degraded: {_e})")

    workbench_router_status = 0
    if not args.skip_workbench_router:
        section("8e. Autoresearch workbench router")
        workbench_router_status = autoresearch_workbench_router_surface(
            task=args.workbench_task,
            project=args.autoresearch_project,
            rubric=args.autoresearch_rubric,
            bounded_claim=args.workbench_bounded_claim,
            stable_evaluator=args.workbench_stable_evaluator,
            rubric_ready=args.workbench_rubric_ready,
            artifact_surface=args.workbench_artifact_surface,
            subscription_worker_available=args.subscription_worker_available,
        )

    section("8f. Eigenquestion rotation surface")
    eigenquestion_rotation_surface(args.autoresearch_project)

    primitive_status = 0
    if not args.skip_primitive_surface:
        section("9. Primitive discoverability surface")
        primitive_status = primitive_surface_precheck(args.blocking_substrate)

    section("9b. Pattern activation guard")
    pattern_activation_status = pattern_activation_guard(args.blocking_substrate)

    section("9c. Problem-surface primitive routing")
    primitive_routing_status = problem_surface_primitive_routing(args.blocking_substrate)

    section("9d. Pattern action contract")
    pattern_contract_status = pattern_action_contract_surface(args.blocking_substrate)

    section("9e. Structural vocabulary fingerprint")
    structural_vocabulary_status = structural_vocabulary_fingerprint(args.blocking_substrate)

    graph_status = 0
    if not args.skip_substrate_graph_precheck and not args.skip_ns_graph_precheck:
        section("10. Substrate graph precheck")
        graph_status = substrate_graph_precheck(args.blocking_substrate)

    gnn_status = 0
    if not args.skip_gnn_precheck:
        section("11. GNN advisory precheck (optional)")
        gnn_status = gnn_advisory_precheck(args.blocking_substrate)

    print()
    print("---")
    # RC2 FIX (2026-05-17): exit code is HARD-ONLY. Previously the
    # advisory-quality prechecks (primitive_status = the ~35% weak-prior
    # surface.ok; primitive_routing / structural_vocabulary / pattern_
    # activation / substrate-graph / GNN — all advisory/optional) were
    # OR'd into the exit, so the brief exited 1 on advisory conditions
    # almost every run ⇒ exit-1 became uninformative noise ⇒ the agent
    # learned to gloss it ⇒ never consumed the surfacing the brief
    # contains (the documented RC2 of the surfacing-underutilization
    # RCA). A forcing signal that fires on advisory conditions is
    # trained-noise. Exit 1 now ONLY on genuine HARD obligations
    # (fresh Tier-1 prediction-closure debt; post-tick GAP-C block).
    # Advisory statuses are surfaced as an explicit WARN so the agent
    # is told to CONSUME the surfacing — not blocked, not silent.
    _advisory = {
        "primitive_surface(§9, weak-prior)": primitive_status,
        "primitive_routing(§9c)": primitive_routing_status,
        "pattern_action_contract(§9d)": pattern_contract_status,
        "structural_vocab(§9e)": structural_vocabulary_status,
        "pattern_activation(§9b)": pattern_activation_status,
        "workbench_router(§8e)": workbench_router_status,
        "substrate_graph(§10)": graph_status,
        "gnn(§11,optional)": gnn_status,
    }
    _adv_hot = [k for k, v in _advisory.items() if v]
    if _adv_hot:
        print(f"  WARN (ADVISORY — NOT blocking; the surfacing IS "
              f"emitted above, §8d/§9/§9c/§9d/§9e — CONSUME it, do not "
              f"gloss): non-clean advisory prechecks: {_adv_hot}")
    print(f"_Brief end. Generated by rd_tick_brief.py at {now}._")
    if prediction_closure_debt or post_tick_block:
        return 1   # HARD only
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
