"""Read-only audit for Newton/Kepler/calibration rubric-mode coherence.

The launch path validates one rubric at a time. This report scans the rubric
corpus and answers the operator question: which rubrics have coherent mode
contracts, and which ones need review before the next run?
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ztare.validator.rubric_mode_resolver import validate_rubric_mode_contract


REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class RubricModeAuditRow:
    rubric_path: str
    project_slug: str
    project_path: str | None
    mode: str
    status: str
    contract_ok: bool
    has_generative_yield: bool
    generative_yield_weight: float
    charter_secondary_observable: str
    latest_run_timestamp: str | None
    recent_run: bool
    notes: tuple[str, ...]
    repair_hint: str
    validation_command: str


def _relative(path: Path, repo: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"__load_error__": f"{type(exc).__name__}: {exc}"}
    return data if isinstance(data, dict) else {"__load_error__": "top-level JSON is not an object"}


def _project_for_rubric(rubric_path: Path, repo: Path) -> tuple[str, Path | None]:
    stem = rubric_path.stem
    candidates = [stem]
    if stem.startswith("dynamic_"):
        candidates.append(stem.removeprefix("dynamic_"))
    for slug in candidates:
        project_dir = repo / "projects" / slug
        if project_dir.exists():
            return slug, project_dir
    return stem, None


def _generative_yield_weight(rubric: dict[str, Any]) -> float:
    weight = 0.0
    for dimension in rubric.get("dimensions", []) or []:
        if not isinstance(dimension, dict):
            continue
        if "generative yield" not in str(dimension.get("name", "")).lower():
            continue
        try:
            weight = max(weight, float(dimension.get("weight", 0) or 0))
        except (TypeError, ValueError):
            continue
    return weight


def _rubric_secondary_observable_contract(rubric: dict[str, Any]) -> bool:
    contract = rubric.get("secondary_observable_contract")
    if not isinstance(contract, dict):
        return False
    required = ("observable", "measurement", "expected_range", "falsifier")
    return all(str(contract.get(key, "") or "").strip() for key in required)


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_run_timestamp(project_dir: Path | None) -> str | None:
    if project_dir is None:
        return None
    candidates = (
        project_dir / "workspace" / "eval_history.jsonl",
        project_dir / "workspace" / "iteration_telemetry.jsonl",
    )
    latest: datetime | None = None
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            ts = _parse_timestamp(row.get("timestamp") or row.get("timestamp_utc"))
            if ts is not None and (latest is None or ts > latest):
                latest = ts
    if latest is None:
        return None
    return latest.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_recent(timestamp: str | None, *, freshness_days: int) -> bool:
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return False
    age_seconds = datetime.now(timezone.utc).timestamp() - parsed.timestamp()
    return age_seconds <= freshness_days * 86400


def _secondary_observable_contract_errors(rubric: dict[str, Any]) -> tuple[str, ...]:
    contract = rubric.get("secondary_observable_contract")
    if contract is None:
        return ()
    if not isinstance(contract, dict):
        return ("secondary_observable_contract must be an object",)
    required = ("observable", "measurement", "expected_range", "falsifier")
    missing = tuple(
        key for key in required if not str(contract.get(key, "") or "").strip()
    )
    if missing:
        return (
            "secondary_observable_contract missing non-empty field(s): "
            + ", ".join(missing),
        )
    return ()


def _secondary_observable_status(
    *,
    project_dir: Path | None,
    rubric: dict[str, Any],
    notes: list[str],
) -> str:
    if _rubric_secondary_observable_contract(rubric):
        notes.append("secondary observable contract present in rubric")
        return "present"
    if project_dir is None:
        return "project_missing"
    charter = project_dir / "project_charter.md"
    if not charter.exists():
        return "charter_missing"
    text = charter.read_text(encoding="utf-8", errors="ignore").lower()
    return "present" if "secondary observable" in text else "missing"


def _repair_hint(*, status: str, project_slug: str, rubric_path: str) -> str:
    if status == "invalid_json":
        return f"fix JSON syntax, then run python -m json.tool {rubric_path}"
    if status == "invalid_contract":
        return (
            "align rubric_mode with the shared launch contract; for newton, "
            "Generative Yield must be present with weight >= 15"
        )
    if status == "newton_project_missing":
        return (
            "create or recover the matching project directory, or retire or archive "
            "the rubric if the project is no longer runnable"
        )
    if status == "newton_charter_missing":
        return (
            "create projects/{project_slug}/project_charter.md with the Newton "
            "question, primary metric, and Secondary observable section"
        ).format(project_slug=project_slug)
    if status == "newton_secondary_observable_missing":
        return (
            "add a charter section named 'Secondary observable' that states the "
            "distinct observable, measurement method, expected range, and falsifying observation"
        )
    if status == "kepler_with_generative_yield":
        return (
            "either promote the rubric to rubric_mode='newton' with charter support "
            "or remove/rename the Generative Yield dimension"
        )
    if status == "do_not_run_live":
        return "leave dormant unless the project is recovered with a complete run surface"
    if status == "legacy_unset":
        return "decide whether the rubric is kepler, newton, or calibration before new serious runs"
    if status == "sealed_holdout":
        return "leave sealed unless the holdout is explicitly unlocked"
    if status == "test_fixture":
        return "leave as fixture unless it is promoted to a real project"
    return "no action"


def _validation_command(*, project_slug: str, rubric_path: str) -> str:
    return (
        "python scripts/public/validators/validate_rubric.py "
        f"{project_slug} --rubric {rubric_path} --verbose"
    )


def _is_test_fixture(rubric_path: Path, project_slug: str) -> bool:
    return rubric_path.stem.startswith("__test_") or project_slug.startswith("__test_")


def _is_committee_panel_rubric(rubric_path: Path, rubric: dict[str, Any]) -> bool:
    """Return whether this JSON is a dynamic critic panel, not a scoring rubric."""

    if not rubric_path.stem.startswith("dynamic_"):
        return False
    committee = rubric.get("committee")
    if not isinstance(committee, (dict, list)):
        return False
    return not isinstance(rubric.get("dimensions"), list) and not rubric.get("rubric_mode")


def _resolve_rubric_path(rubric: str | Path, *, repo: Path) -> Path:
    path = Path(rubric)
    if path.is_absolute():
        return path
    if path.suffix == ".json" or len(path.parts) > 1:
        return repo / path
    return repo / "rubrics" / f"{path}.json"


def audit_rubric_mode_corpus(
    *,
    repo: Path = REPO,
    rubric: str | Path | None = None,
    freshness_days: int = 30,
) -> dict[str, Any]:
    repo = repo.resolve()
    if rubric:
        rubric_path = _resolve_rubric_path(rubric, repo=repo)
        rubric_paths = (rubric_path,)
    else:
        rubric_paths = tuple(sorted((repo / "rubrics").glob("*.json")))

    rows: list[RubricModeAuditRow] = []
    status_counts: dict[str, int] = {}
    mode_counts: dict[str, int] = {}

    for path in rubric_paths:
        rubric_data = _load_json(path)
        project_slug, project_dir = _project_for_rubric(path, repo)
        notes: list[str] = []
        mode = str(rubric_data.get("rubric_mode", "") or "").strip().lower()
        gy_weight = _generative_yield_weight(rubric_data)
        has_gy = gy_weight > 0
        latest_run_timestamp = _latest_run_timestamp(project_dir)
        recent_run = _is_recent(latest_run_timestamp, freshness_days=freshness_days)
        secondary_contract_errors = _secondary_observable_contract_errors(rubric_data)
        charter_status = _secondary_observable_status(
            project_dir=project_dir,
            rubric=rubric_data,
            notes=notes,
        )
        contract = validate_rubric_mode_contract(rubric_data)

        if "__load_error__" in rubric_data:
            status = "invalid_json"
            notes.append(str(rubric_data["__load_error__"]))
        elif _is_test_fixture(path, project_slug):
            status = "test_fixture"
            notes.append("synthetic rubric fixture; excluded from operator attention")
        elif _is_committee_panel_rubric(path, rubric_data):
            status = "committee_panel"
            notes.append("dynamic committee panel; excluded from rubric-mode attention")
        elif rubric_data.get("__do_not_run_live") is True and mode == "sealed_holdout":
            status = "sealed_holdout"
            notes.append("rubric is intentionally marked do-not-run-live")
        elif rubric_data.get("__do_not_run_live") is True:
            status = "do_not_run_live"
            reason = str(rubric_data.get("__do_not_run_live_reason", "") or "").strip()
            notes.append("rubric is intentionally marked do-not-run-live")
            if reason:
                notes.append(reason)
        elif not mode:
            status = "legacy_unset"
            notes.append("rubric_mode is unset; launch path accepts this as legacy")
        elif not contract.ok:
            status = "invalid_contract"
            notes.append(contract.message)
        elif mode == "newton" and secondary_contract_errors:
            status = "invalid_contract"
            notes.extend(secondary_contract_errors)
        elif mode == "newton" and charter_status == "project_missing":
            status = "newton_project_missing"
            notes.append("newton rubric has no matching project directory")
        elif mode == "newton" and charter_status == "charter_missing":
            status = "newton_charter_missing"
            notes.append("newton rubric has no project_charter.md")
        elif mode == "newton" and charter_status == "missing":
            status = "newton_secondary_observable_missing"
            notes.append("newton rubric charter lacks a Secondary observable section")
        elif mode == "kepler" and has_gy:
            status = "kepler_with_generative_yield"
            notes.append("kepler rubric carries Generative Yield; check whether it should be newton")
        else:
            status = "ok"

        if project_dir is None:
            notes.append("no matching project directory found")
        relative_rubric = _relative(path, repo)

        row = RubricModeAuditRow(
            rubric_path=relative_rubric,
            project_slug=project_slug,
            project_path=_relative(project_dir, repo) if project_dir else None,
            mode="committee_panel" if status == "committee_panel" else mode or "legacy_unset",
            status=status,
            contract_ok=contract.ok,
            has_generative_yield=has_gy,
            generative_yield_weight=gy_weight,
            charter_secondary_observable=charter_status,
            latest_run_timestamp=latest_run_timestamp,
            recent_run=recent_run,
            notes=tuple(notes),
            repair_hint=_repair_hint(
                status=status,
                project_slug=project_slug,
                rubric_path=relative_rubric,
            ),
            validation_command=_validation_command(
                project_slug=project_slug,
                rubric_path=relative_rubric,
            ),
        )
        rows.append(row)
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
        mode_counts[row.mode] = mode_counts.get(row.mode, 0) + 1

    legacy_rows = [row for row in rows if row.status == "legacy_unset"]
    recent_legacy_rows = [row for row in legacy_rows if row.project_path and row.recent_run]
    legacy_summary = {
        "count": len(legacy_rows),
        "with_project_count": sum(1 for row in legacy_rows if row.project_path),
        "without_project_count": sum(1 for row in legacy_rows if not row.project_path),
        "recent_with_project_count": len(recent_legacy_rows),
        "freshness_days": freshness_days,
        "recent_examples": [
            {
                "rubric_path": row.rubric_path,
                "project_slug": row.project_slug,
                "latest_run_timestamp": row.latest_run_timestamp,
                "repair_hint": row.repair_hint,
            }
            for row in sorted(
                recent_legacy_rows,
                key=lambda row: row.latest_run_timestamp or "",
                reverse=True,
            )[:10]
        ],
        "charter_status_counts": dict(
            sorted(
                {
                    status: sum(
                        1 for row in legacy_rows if row.charter_secondary_observable == status
                    )
                    for status in {row.charter_secondary_observable for row in legacy_rows}
                }.items()
            )
        ),
    }
    attention_statuses = {
        "invalid_json",
        "invalid_contract",
        "newton_project_missing",
        "newton_charter_missing",
        "newton_secondary_observable_missing",
        "kepler_with_generative_yield",
    }
    if rubric:
        attention_statuses.add("legacy_unset")
    attention = [
        asdict(row)
        for row in rows
        if row.status in attention_statuses
        or (row.status == "legacy_unset" and row.recent_run and row.project_path)
    ]
    return {
        "schema": "ztare-rubric-mode-corpus-audit-v1",
        "scope": {
            "repo": str(repo),
            "rubric": str(rubric) if rubric else None,
        },
        "summary": {
            "rubric_count": len(rows),
            "mode_counts": dict(sorted(mode_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "attention_count": len(attention),
            "legacy_unset": legacy_summary,
        },
        "attention": attention,
        "rows": [asdict(row) for row in rows],
    }


def render_text(report: dict[str, Any], *, limit: int = 40) -> str:
    summary = report["summary"]
    lines = [
        "Rubric-mode corpus audit",
        f"rubrics={summary['rubric_count']} attention={summary['attention_count']}",
        "modes=" + json.dumps(summary["mode_counts"], sort_keys=True),
        "statuses=" + json.dumps(summary["status_counts"], sort_keys=True),
        "legacy_unset=" + json.dumps(summary.get("legacy_unset", {}), sort_keys=True),
    ]
    rows = report["attention"][:limit]
    if not rows:
        lines.append("attention: none")
    for row in rows:
        note_text = "; ".join(row["notes"]) if row["notes"] else "none"
        lines.append(
            "- {status}: {rubric_path} mode={mode} project={project_slug} "
            "gy={generative_yield_weight:g} charter={charter_secondary_observable}; "
            "notes={note_text}; repair={repair_hint}; check={validation_command}".format(
                note_text=note_text,
                **row,
            )
        )
    remaining = len(report["attention"]) - len(rows)
    if remaining > 0:
        lines.append(f"... {remaining} more attention rows omitted; rerun with --json.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rubric", help="Audit one rubric path instead of rubrics/*.json.")
    parser.add_argument("--limit", type=int, default=40, help="Text attention row limit.")
    parser.add_argument(
        "--freshness-days",
        type=int,
        default=30,
        help="Treat legacy rubrics with run telemetry inside this window as active debt.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument(
        "--fail-on-attention",
        action="store_true",
        help="Exit 1 when attention rows are present.",
    )
    args = parser.parse_args(argv)

    report = audit_rubric_mode_corpus(
        repo=REPO,
        rubric=args.rubric,
        freshness_days=args.freshness_days,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report, limit=args.limit))
    return 1 if args.fail_on_attention and report["summary"]["attention_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
