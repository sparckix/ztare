"""End-of-phase audit for typed producer-to-consumer routes.

The operational route registry owns the check.  This module adds only the two
cross-run behaviors that the registry does not own:

* remember anomaly -> recovery -> anomaly lifecycles; and
* on such a recurrence, surface alternative abstractions for the existing
  forced-REFRAME briefing consumer.

It does not translate apparatus findings into scientific proposals.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


STATE_FILE = "trace_auditor_state.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_state(workspace: Path) -> dict:
    path = workspace / STATE_FILE
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_state(workspace: Path, state: dict) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / STATE_FILE).write_text(
        json.dumps(state, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _finding(check_id: str, verdict: str, witness: dict, note: str) -> dict:
    return {
        "check_id": check_id,
        "verdict": verdict,
        "witness": witness,
        "note": note,
        "recurrence": False,
    }


def check_schema_route_ledger(project_dir: str | Path, state: dict | None = None) -> dict:
    """Render the shared schema-route audit as an end-of-phase finding."""
    del state  # compatibility with the former detector signature
    try:
        from ztare.common.schema_routes import audit_project_schema_routes

        audit = audit_project_schema_routes(project_dir)
    except Exception as exc:  # noqa: BLE001 - inability to run the fence blocks
        return _finding(
            "schema_route_ledger",
            "anomaly",
            {"audit_error": f"{type(exc).__name__}:{exc}", "halt_required": True},
            "Typed schema-route audit could not run.",
        )

    errors = list(audit.get("errors") or [])
    warnings = list(audit.get("warnings") or [])
    if errors:
        note = (
            f"{len(errors)} operational route error(s); mutation and task-discharge "
            "claims are fenced until the registered consumer fires."
        )
    elif warnings:
        note = f"{len(warnings)} cold route-debt item(s); no scientific authority."
    else:
        note = "Every produced operational carrier has a registered consequence."
    return _finding(
        "schema_route_ledger",
        "anomaly" if errors or warnings else "ok",
        {
            "halt_required": bool(audit.get("halt_required")),
            "errors": errors,
            "warnings": warnings,
            "route_count": len(audit.get("routes") or []),
        },
        note,
    )


def _scope_finding(finding: dict) -> dict:
    blocking = bool((finding.get("witness") or {}).get("halt_required"))
    return {
        **finding,
        "routing_scope": "active_apparatus" if blocking else "catalog_advisory",
        "proposal_authority": "none",
    }


def check_recurrence(findings: list[dict], state: dict) -> list[dict]:
    """Tag only anomaly -> recovery -> anomaly lifecycles as recurrences."""
    last_verdicts = dict(state.get("last_verdicts") or {})
    seen_anomaly = dict(state.get("seen_anomaly_checks") or {})
    recovered = dict(state.get("recovered_checks") or {})
    out: list[dict] = []
    for finding in findings:
        check_id = str(finding["check_id"])
        verdict = str(finding["verdict"])
        recurrence = bool(recovered.get(check_id) and verdict == "anomaly")
        out.append({**finding, "recurrence": recurrence})
        last_verdicts[check_id] = verdict
        if verdict == "anomaly":
            seen_anomaly[check_id] = True
            recovered[check_id] = False
        elif verdict == "ok" and seen_anomaly.get(check_id):
            recovered[check_id] = True
    state["last_verdicts"] = last_verdicts
    state["seen_anomaly_checks"] = seen_anomaly
    state["recovered_checks"] = recovered
    # Initial OK observations populated this legacy property, so it cannot be
    # migrated into event history without inventing a prior anomaly.
    state.pop("fixed_checks", None)
    return out


def fire_conjecture_rung(project_dir: str | Path, findings: list[dict]) -> list[dict]:
    """Surface alternative abstractions once per recurring blocking route."""
    if os.environ.get("ZTARE_CONJECTURE_RUNG", "1") == "0":
        return []
    recurring = [
        finding
        for finding in findings
        if finding.get("recurrence")
        and finding.get("verdict") == "anomaly"
        and finding.get("routing_scope") == "active_apparatus"
    ]
    if not recurring:
        return []

    workspace = Path(project_dir) / "workspace"
    ledger = workspace / "conjecture_rung_ledger.jsonl"
    fired_ids: set[str] = set()
    if ledger.is_file():
        for line in ledger.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("check_id"):
                fired_ids.add(str(row["check_id"]))

    rows: list[dict] = []
    for finding in recurring:
        check_id = str(finding["check_id"])
        if check_id in fired_ids:
            continue
        try:
            from ztare.research_director.primitive_amnesia import precheck

            owned = [
                {
                    "name": result.get("name"),
                    "module": result.get("module"),
                    "when_to_use": result.get("when_to_use"),
                    "score": result.get("score"),
                }
                for result in (precheck(
                    f"{check_id}: {str(finding.get('note') or '')[:200]}"
                ) or [])[:3]
            ]
        except Exception:  # noqa: BLE001 - optional retrieval aid
            owned = []
        try:
            from ztare.research_director.research_isomorphism import (
                surface_for_research_ceiling,
            )

            candidates = surface_for_research_ceiling(
                {
                    "constraint_class": (
                        f"recurring apparatus route failure '{check_id}': "
                        f"{str(finding.get('note') or '')[:300]}"
                    ),
                    "abstract_form": (
                        "an operational producer-to-consumer route failed, recovered, "
                        "and failed again; identify the unmodeled governing identity"
                    ),
                    "home_field": "program synthesis and evaluation harnesses",
                    "witness": json.dumps(finding.get("witness") or {})[:400],
                },
                n=3,
            )
            row = {
                "schema": "ztare.conjecture_rung.v1",
                "check_id": check_id,
                "owned_primitives_first": owned,
                "surfaced": len(candidates or []),
                "candidates": [
                    {
                        "theorem": candidate.theorem,
                        "field": candidate.field,
                        "mechanism": (candidate.mechanism or "")[:200],
                    }
                    for candidate in (candidates or [])
                ],
            }
        except Exception as exc:  # noqa: BLE001 - receipt records failed surface
            row = {
                "schema": "ztare.conjecture_rung.v1",
                "check_id": check_id,
                "surfaced": 0,
                "error": f"{type(exc).__name__}: {str(exc)[:150]}",
            }
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        rows.append(row)
    return rows


def run_audit(project: str | Path) -> dict:
    """Run the single decision-bearing end-of-phase apparatus audit."""
    project_dir = Path(project).resolve()
    workspace = project_dir / "workspace"
    state = _read_state(workspace)
    state["audit_count"] = int(state.get("audit_count") or 0) + 1

    findings = check_recurrence(
        [_scope_finding(check_schema_route_ledger(project_dir))],
        state,
    )
    fire_conjecture_rung(project_dir, findings)

    state["last_audit_ts"] = _now_utc()
    state["last_audit_findings"] = [
        f"{finding['check_id']}={finding['verdict']}" for finding in findings
    ]
    _write_state(workspace, state)
    return {
        "schema": "ztare-trace-auditor-v1",
        "audit_count": state["audit_count"],
        "audited_utc": state["last_audit_ts"],
        "project": str(project_dir),
        "findings": findings,
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(
        prog="ztare.orchestrator.trace_auditor",
        description="Audit typed operational producer-to-consumer routes.",
    )
    parser.add_argument("--project", required=True, help="Path to project directory")
    args = parser.parse_args()
    result = run_audit(args.project)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    anomalies = [row for row in result["findings"] if row["verdict"] == "anomaly"]
    print(
        f"\n-- {len(result['findings'])} check: "
        f"{len(result['findings']) - len(anomalies)} ok / {len(anomalies)} anomaly",
        file=sys.stderr,
    )


if __name__ == "__main__":
    _cli()
