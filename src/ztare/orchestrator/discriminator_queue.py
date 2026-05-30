"""Post-run discriminator queue and background-debt ladder.

GP-190 turns the operator-supervisor "what should we test next?" move
into a typed artifact. This module deliberately does not run experiments
and does not call an LLM. It only validates and writes proposals.

Artifacts:
    projects/<slug>/workspace/next_discriminator_queue.jsonl
    projects/<slug>/workspace/background_debt_ladder_<label>.json

The queue is the boundary object between:
    - GP-119 Inverter proposals,
    - post-run meta-audits,
    - manual Codex/operator sessions,
    - future deterministic auto-test dispatch.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.ztare.common.paths import PROJECTS_DIR


QUEUE_FILENAME = "next_discriminator_queue.jsonl"

SHORTCUT_LABELS = {
    "local_positive_to_universal_claim",
    "static_snapshot_to_dynamic_claim",
    "scalar_proxy_to_tensor_claim",
    "aligned_state_to_stable_attractor",
    "analogy_to_isomorphism",
    "instrument_null_to_physics_null",
    "score_gain_to_discovery_claim",
    "local_gain_without_background_debt",
    "unspecified_promotion_shortcut",
}

LICENSE_STAGES = {"scratchpad", "commit"}


def severity_label(level: int) -> str:
    if level <= 1:
        return "L1_smoke"
    if level == 2:
        return "L2_sanity"
    if level == 3:
        return "L3_local_falsifier"
    if level == 4:
        return "L4_hostile_control"
    return "L5_decisive_ladder"


def clamp_severity(value: Any) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        level = 3
    return max(1, min(5, level))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def project_dir_from_slug(project: str | Path) -> Path:
    path = Path(project)
    if path.exists() or "/" in str(project):
        return path
    return PROJECTS_DIR / str(project)


def queue_path(project_dir: Path | str) -> Path:
    return Path(project_dir) / "workspace" / QUEUE_FILENAME


def _clean_text(value: Any, *, limit: int = 1200) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _clean_list(values: Iterable[Any] | None, *, limit: int = 20) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    for value in values:
        item = _clean_text(value)
        if item and item not in out:
            out.append(item)
        if len(out) >= limit:
            break
    return out


def infer_narrative_shortcut(*texts: str) -> str:
    """Best-effort label for the promotion risk a discriminator attacks.

    This is intentionally conservative. Unknown cases become
    ``unspecified_promotion_shortcut`` rather than hallucinating precision.
    """
    joined = " ".join(t.lower() for t in texts if t)
    if not joined.strip():
        return "unspecified_promotion_shortcut"
    if any(k in joined for k in ("isomorphism", "dual", "same equation", "same operator")):
        return "analogy_to_isomorphism"
    if any(k in joined for k in ("static", "snapshot", "fixed point", "equilibrium")) and any(
        k in joined for k in ("dynamic", "trajectory", "evolution", "admissib", "time")
    ):
        return "static_snapshot_to_dynamic_claim"
    if any(k in joined for k in ("scalar", "magnitude", "1d", "row-wise")) and any(
        k in joined for k in ("tensor", "orientation", "shear", "gradient", "quadrupole")
    ):
        return "scalar_proxy_to_tensor_claim"
    if any(k in joined for k in ("aligned", "orientation", "0 degree", "0°")) and any(
        k in joined for k in ("stable", "attractor", "forced", "torque", "hessian", "tumble")
    ):
        return "aligned_state_to_stable_attractor"
    if any(k in joined for k in ("instrument", "solver", "grid", "boundary", "residual", "launch")) and any(
        k in joined for k in ("physics", "law", "discovery", "falsif")
    ):
        return "instrument_null_to_physics_null"
    if any(k in joined for k in ("score", "mre", "fit", "loss", "improvement")) and any(
        k in joined for k in ("discovery", "law", "truth", "finding")
    ):
        return "score_gain_to_discovery_claim"
    if any(k in joined for k in ("debt", "halo", "off-core", "background", "cleanup", "saturation", "liability")):
        return "local_gain_without_background_debt"
    if any(k in joined for k in ("local", "sample", "one case", "positive", "mechanism")) and any(
        k in joined for k in ("universal", "global", "theorem", "law")
    ):
        return "local_positive_to_universal_claim"
    return "unspecified_promotion_shortcut"


@dataclass(frozen=True)
class DiscriminatorProposal:
    project: str
    trigger_artifact: str
    claim_under_pressure: str
    cheapest_discriminator: str
    kill_condition: str
    rival_explanations: list[str] = field(default_factory=list)
    required_artifacts: list[str] = field(default_factory=list)
    narrative_shortcut: str = "unspecified_promotion_shortcut"
    instrument_risk: str = ""
    cost_estimate: dict[str, Any] = field(default_factory=dict)
    auto_testable: bool = False
    needs_human: bool = True
    source: str = "manual"
    priority: str = "normal"
    status: str = "proposed"
    severity_level: int = 3
    promotion_blocking: bool = True
    license_stage: str = "commit"
    weak_test_risk: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now)

    def normalized(self) -> "DiscriminatorProposal":
        shortcut = self.narrative_shortcut
        if shortcut not in SHORTCUT_LABELS or shortcut == "unspecified_promotion_shortcut":
            shortcut = infer_narrative_shortcut(
                self.claim_under_pressure,
                " ".join(self.rival_explanations),
                self.cheapest_discriminator,
                self.kill_condition,
            )
        return DiscriminatorProposal(
            project=_clean_text(self.project, limit=160),
            trigger_artifact=_clean_text(self.trigger_artifact, limit=600),
            claim_under_pressure=_clean_text(self.claim_under_pressure),
            cheapest_discriminator=_clean_text(self.cheapest_discriminator),
            kill_condition=_clean_text(self.kill_condition),
            rival_explanations=_clean_list(self.rival_explanations),
            required_artifacts=_clean_list(self.required_artifacts),
            narrative_shortcut=shortcut,
            instrument_risk=_clean_text(self.instrument_risk),
            cost_estimate=dict(self.cost_estimate or {}),
            auto_testable=bool(self.auto_testable),
            needs_human=bool(self.needs_human),
            source=_clean_text(self.source, limit=120),
            priority=_clean_text(self.priority, limit=40) or "normal",
            status=_clean_text(self.status, limit=40) or "proposed",
            severity_level=clamp_severity(self.severity_level),
            promotion_blocking=bool(self.promotion_blocking),
            license_stage=(
                self.license_stage
                if self.license_stage in LICENSE_STAGES
                else "commit"
            ),
            weak_test_risk=_clean_text(self.weak_test_risk),
            metadata=dict(self.metadata or {}),
            timestamp=self.timestamp or utc_now(),
        )

    def validate(self) -> None:
        missing = [
            name
            for name in (
                "project",
                "claim_under_pressure",
                "cheapest_discriminator",
                "kill_condition",
            )
            if not getattr(self, name)
        ]
        if missing:
            raise ValueError(f"missing required discriminator fields: {', '.join(missing)}")
        if self.narrative_shortcut not in SHORTCUT_LABELS:
            raise ValueError(f"unknown narrative_shortcut: {self.narrative_shortcut}")
        if self.license_stage not in LICENSE_STAGES:
            raise ValueError(f"unknown license_stage: {self.license_stage}")
        if not 1 <= int(self.severity_level) <= 5:
            raise ValueError(f"severity_level must be 1..5, got {self.severity_level!r}")

    def to_record(self) -> dict[str, Any]:
        normalized = self.normalized()
        normalized.validate()
        can_support_promotion = (
            normalized.promotion_blocking
            and normalized.license_stage == "commit"
            and normalized.severity_level >= 4
        )
        return {
            "schema_version": 2,
            "timestamp": normalized.timestamp,
            "project": normalized.project,
            "trigger_artifact": normalized.trigger_artifact,
            "claim_under_pressure": normalized.claim_under_pressure,
            "narrative_shortcut": normalized.narrative_shortcut,
            "rival_explanations": normalized.rival_explanations,
            "cheapest_discriminator": normalized.cheapest_discriminator,
            "kill_condition": normalized.kill_condition,
            "instrument_risk": normalized.instrument_risk,
            "required_artifacts": normalized.required_artifacts,
            "cost_estimate": normalized.cost_estimate,
            "auto_testable": normalized.auto_testable,
            "needs_human": normalized.needs_human,
            "source": normalized.source,
            "priority": normalized.priority,
            "status": normalized.status,
            "severity_level": normalized.severity_level,
            "severity_label": severity_label(normalized.severity_level),
            "promotion_blocking": normalized.promotion_blocking,
            "can_support_promotion": can_support_promotion,
            "license_stage": normalized.license_stage,
            "weak_test_risk": normalized.weak_test_risk,
            "metadata": normalized.metadata,
        }


def append_discriminator(project_dir: Path | str, proposal: DiscriminatorProposal) -> Path:
    path = queue_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(proposal.to_record(), sort_keys=True) + "\n")
    return path


def append_discriminators(project_dir: Path | str, proposals: Iterable[DiscriminatorProposal]) -> tuple[Path, int]:
    path = queue_path(project_dir)
    count = 0
    for proposal in proposals:
        append_discriminator(project_dir, proposal)
        count += 1
    return path, count


def update_discriminator_status(
    queue_file: Path,
    *,
    status: str,
    template: str | None = None,
    source: str | None = None,
    evidence_artifacts: Iterable[str] | None = None,
    note: str = "",
) -> int:
    """Update matching queue records in place.

    Matching is deliberately narrow: callers must provide a replay template
    name and/or source. This avoids silent bulk promotion of unrelated tests.
    """
    if not template and not source:
        raise ValueError("status update requires --template and/or --source")
    if not queue_file.exists():
        raise FileNotFoundError(queue_file)
    rows: list[dict[str, Any]] = []
    for line in queue_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            rows.append({"_raw_unparseable": line})
            continue
        rows.append(row)

    evidence = _clean_list(evidence_artifacts or [], limit=20)
    count = 0
    for row in rows:
        if "_raw_unparseable" in row:
            continue
        metadata = row.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            row["metadata"] = metadata
        if template and metadata.get("replay_template") != template:
            continue
        if source and row.get("source") != source:
            continue
        row["status"] = _clean_text(status, limit=40) or "closed_passed"
        row["status_updated_at"] = utc_now()
        if evidence:
            metadata["status_evidence_artifacts"] = evidence
        if note:
            metadata["status_note"] = _clean_text(note)
        count += 1

    with queue_file.open("w", encoding="utf-8") as f:
        for row in rows:
            if "_raw_unparseable" in row:
                f.write(row["_raw_unparseable"] + "\n")
            else:
                f.write(json.dumps(row, sort_keys=True) + "\n")
    return count


def proposals_from_inverter_result(
    *,
    project: str,
    trigger_artifact: str,
    claim_under_pressure: str,
    inverter_result: dict[str, Any],
) -> list[DiscriminatorProposal]:
    proposals: list[DiscriminatorProposal] = []
    for idx, test in enumerate(inverter_result.get("tests") or [], start=1):
        if not isinstance(test, dict):
            continue
        inversion = _clean_text(
            test.get("munger_inversion")
            or test.get("rival_explanation")
            or test.get("category")
        )
        discriminator = _clean_text(
            test.get("popper_test")
            or test.get("procedure")
            or test.get("description")
        )
        kill = _clean_text(test.get("fail_criterion") or test.get("kill_condition"))
        if not discriminator or not kill:
            continue
        texts = [claim_under_pressure, inversion, discriminator, kill]
        required = _clean_list(test.get("required_artifacts") or [], limit=12)
        if not required:
            required = [
                "workspace/inverter_review.json",
                "workspace/champion_eval_results.json",
                "workspace/eval_history.jsonl",
            ]
        proposals.append(
            DiscriminatorProposal(
                project=project,
                trigger_artifact=trigger_artifact,
                claim_under_pressure=claim_under_pressure,
                narrative_shortcut=infer_narrative_shortcut(*texts),
                rival_explanations=[inversion] if inversion else [],
                cheapest_discriminator=discriminator,
                kill_condition=kill,
                instrument_risk=_clean_text(test.get("instrument_risk")),
                required_artifacts=required,
                cost_estimate={"tier": _clean_text(test.get("estimated_cost"), limit=60) or "unknown"},
                auto_testable=bool(test.get("auto_testable", False)),
                needs_human=not bool(test.get("auto_testable", False)),
                source="gp119_inverter",
                severity_level=clamp_severity(test.get("severity_level", test.get("discriminator_level", 3))),
                license_stage=_clean_text(test.get("license_stage"), limit=40)
                if test.get("license_stage") in LICENSE_STAGES
                else "commit",
                weak_test_risk=_clean_text(test.get("weak_test_risk")),
                metadata={
                    "inverter_test_index": idx,
                    "category": _clean_text(test.get("category"), limit=80),
                    "pass_criterion": _clean_text(test.get("pass_criterion")),
                    "procedure": _clean_text(test.get("procedure")),
                },
            )
        )
    return proposals


def proposals_from_meta_audit(
    *,
    project: str,
    trigger_artifact: str,
    audit_verdict: dict[str, Any],
) -> list[DiscriminatorProposal]:
    """Translate post-run meta-audit recommendations into queue rows."""
    cap_pattern = _clean_text(audit_verdict.get("cap_pattern")) or "post-run cap pattern"
    recommendations = audit_verdict.get("detection_recommendations") or []
    if not isinstance(recommendations, list):
        recommendations = [recommendations]
    proposals: list[DiscriminatorProposal] = []
    for idx, rec in enumerate(recommendations, start=1):
        discriminator = _clean_text(rec)
        if not discriminator:
            continue
        narrow = audit_verdict.get("narrow_scoped_gate")
        narrow_text = ""
        if isinstance(narrow, dict) and (narrow.get("gate_name") or narrow.get("scope_extension")):
            narrow_text = f"{narrow.get('gate_name', '')}: {narrow.get('scope_extension', '')}"
        rivals = [
            "apparatus-side detection missing or scoped too narrowly",
            *(_clean_list(audit_verdict.get("gates_engaged_not_flagged") or [], limit=6)),
        ]
        if narrow_text:
            rivals.append(narrow_text)
        proposals.append(
            DiscriminatorProposal(
                project=project,
                trigger_artifact=trigger_artifact,
                claim_under_pressure=cap_pattern,
                narrative_shortcut="instrument_null_to_physics_null",
                rival_explanations=rivals,
                cheapest_discriminator=discriminator,
                kill_condition=(
                    "If the proposed detector/gate extension is backtested on "
                    "the closed workspace and does not identify a materially "
                    "different cap cause, the apparatus explanation is demoted."
                ),
                instrument_risk=_clean_text(audit_verdict.get("error")),
                required_artifacts=[
                    "workspace/post_run_meta_audit.json",
                    "workspace/eval_history.jsonl",
                    "workspace/cage_engagement.jsonl",
                    "workspace/iteration_telemetry.jsonl",
                ],
                cost_estimate={"mode": "offline_backtest", "tier": "cheap"},
                auto_testable=True,
                needs_human=False,
                source="post_run_meta_audit",
                severity_level=2,
                promotion_blocking=False,
                weak_test_risk=(
                    "Offline detector backtests are instrumentation checks. "
                    "They can repair the telescope but cannot by themselves "
                    "promote a scientific finding."
                ),
                metadata={"meta_audit_recommendation_index": idx},
            )
        )
    return proposals


def proposals_from_cold_shot_result(
    *,
    project: str,
    trigger_artifact: str,
    claim_under_pressure: str,
    cold_shot_result: dict[str, Any],
) -> list[DiscriminatorProposal]:
    """Translate a strict-JSON cold-shot critique into queue rows.

    This accepts the JSON shape used in recent frontier cold shots:
    ``tightened_eigenquestion``, ``single_best_next_discriminator``,
    ``main_risk``, ``do_not_do_next``, and optional exact-run fields.
    """
    discriminator = _clean_text(
        cold_shot_result.get("single_best_next_discriminator")
        or cold_shot_result.get("cheapest_discriminator")
        or cold_shot_result.get("next_discriminator")
    )
    exact_run = _clean_text(
        cold_shot_result.get("if_more_gpu_what_exact_run")
        or cold_shot_result.get("if_more_compute_what_exact_run")
        or cold_shot_result.get("exact_run")
    )
    if exact_run:
        discriminator = f"{discriminator} Exact run: {exact_run}" if discriminator else exact_run
    kill = _clean_text(
        cold_shot_result.get("kill_condition")
        or cold_shot_result.get("falsifier")
        or cold_shot_result.get("failure_condition")
    )
    if not kill:
        kill = (
            "If the proposed discriminator does not separate the live rival "
            "explanations under its stated controls, do not promote the claim."
        )
    if not discriminator:
        return []

    rivals = _clean_list(cold_shot_result.get("data_does_not_say") or [], limit=8)
    main_risk = _clean_text(cold_shot_result.get("main_risk"))
    if main_risk:
        rivals.append(main_risk)
    eigenquestion = _clean_text(cold_shot_result.get("tightened_eigenquestion"))
    claim = claim_under_pressure or eigenquestion or _clean_text(cold_shot_result.get("answer")) or "cold-shot claim"
    texts = [
        claim,
        eigenquestion,
        discriminator,
        kill,
        " ".join(rivals),
        " ".join(_clean_list(cold_shot_result.get("data_says") or [], limit=8)),
    ]
    required_artifacts = _clean_list(cold_shot_result.get("required_artifacts") or [], limit=12)
    if not required_artifacts:
        required_artifacts = [
            "cold_shot_raw_response",
            "source artifacts named in the cold-shot prompt",
            "discriminator output summary",
        ]
    return [
        DiscriminatorProposal(
            project=project,
            trigger_artifact=trigger_artifact,
            claim_under_pressure=claim,
            narrative_shortcut=_clean_text(cold_shot_result.get("narrative_shortcut"), limit=80)
            if cold_shot_result.get("narrative_shortcut") in SHORTCUT_LABELS
            else infer_narrative_shortcut(*texts),
            rival_explanations=rivals,
            cheapest_discriminator=discriminator,
            kill_condition=kill,
            instrument_risk=main_risk,
            required_artifacts=required_artifacts,
            cost_estimate={
                "mode": "from_cold_shot",
                "exact_run": exact_run,
            },
            auto_testable=False,
            needs_human=True,
            source="cold_shot_discriminator",
            priority="high",
            severity_level=clamp_severity(
                cold_shot_result.get("severity_level")
                or cold_shot_result.get("discriminator_level")
                or 4
            ),
            license_stage=(
                cold_shot_result.get("license_stage")
                if cold_shot_result.get("license_stage") in LICENSE_STAGES
                else "commit"
            ),
            weak_test_risk=_clean_text(cold_shot_result.get("weak_test_risk")),
            metadata={
                "answer": _clean_text(cold_shot_result.get("answer"), limit=160),
                "tightened_eigenquestion": eigenquestion,
                "do_not_do_next": _clean_list(cold_shot_result.get("do_not_do_next") or [], limit=12),
                "handoff": _clean_text(
                    cold_shot_result.get("if_not_more_gpu_what_exact_handoff")
                    or cold_shot_result.get("if_not_more_compute_what_exact_handoff")
                ),
            },
        )
    ]


@dataclass(frozen=True)
class DebtRatioPoint:
    label: str
    local_gain: float
    background_debt: float
    axis: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        debt = float(self.background_debt)
        gain = float(self.local_gain)
        ratio = gain / debt if debt != 0.0 else None
        return {
            "label": _clean_text(self.label, limit=160),
            "axis": _clean_text(self.axis, limit=160),
            "local_gain": gain,
            "background_debt": debt,
            "gain_debt_ratio": ratio,
            "metadata": dict(self.metadata or {}),
        }


def write_background_debt_ladder(
    project_dir: Path | str,
    *,
    label: str,
    claim_under_pressure: str,
    debt_proxy: str,
    points: Iterable[DebtRatioPoint],
    source: str = "manual",
) -> Path:
    """Persist a domain-neutral local-gain/background-debt ladder."""
    project_dir = Path(project_dir)
    workspace = project_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", label).strip("_") or "ladder"
    out = workspace / f"background_debt_ladder_{safe_label}.json"
    records = [p.to_record() for p in points]
    payload = {
        "schema_version": 1,
        "timestamp": utc_now(),
        "project": project_dir.name,
        "label": safe_label,
        "claim_under_pressure": _clean_text(claim_under_pressure),
        "debt_proxy": _clean_text(debt_proxy),
        "source": _clean_text(source, limit=120),
        "points": records,
        "promotion_rule": (
            "A local gain is not promotable unless its gain/debt ratio remains "
            "interpretable across the declared sweep axes."
        ),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def _parse_debt_point(raw: str) -> DebtRatioPoint:
    parts = raw.split(":")
    if len(parts) < 3:
        raise ValueError("--point must be label:gain:debt[:axis]")
    label, gain_s, debt_s = parts[0], parts[1], parts[2]
    axis = parts[3] if len(parts) > 3 else ""
    return DebtRatioPoint(label=label, local_gain=float(gain_s), background_debt=float(debt_s), axis=axis)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GP-190 discriminator queue utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)

    append = sub.add_parser("append", help="append one discriminator proposal")
    append.add_argument("--project", required=True)
    append.add_argument("--trigger-artifact", default="")
    append.add_argument("--claim", required=True)
    append.add_argument("--rival", action="append", default=[])
    append.add_argument("--test", required=True)
    append.add_argument("--kill", required=True)
    append.add_argument("--artifact", action="append", default=[])
    append.add_argument("--instrument-risk", default="")
    append.add_argument("--source", default="manual")
    append.add_argument("--auto-testable", action="store_true")
    append.add_argument("--severity-level", type=int, default=3, choices=range(1, 6))
    append.add_argument("--license-stage", default="commit", choices=sorted(LICENSE_STAGES))
    append.add_argument("--weak-test-risk", default="")

    from_inv = sub.add_parser("from-inverter", help="translate workspace/inverter_review.json into queue rows")
    from_inv.add_argument("--project", required=True)
    from_inv.add_argument("--claim", default="")

    from_cold = sub.add_parser("from-cold-shot", help="translate a strict-JSON cold-shot critique into queue rows")
    from_cold.add_argument("--project", required=True)
    from_cold.add_argument("--artifact", required=True)
    from_cold.add_argument("--claim", default="")

    debt = sub.add_parser("debt-ladder", help="write a background-debt ladder")
    debt.add_argument("--project", required=True)
    debt.add_argument("--label", required=True)
    debt.add_argument("--claim", required=True)
    debt.add_argument("--debt-proxy", required=True)
    debt.add_argument("--source", default="manual")
    debt.add_argument("--point", action="append", required=True, help="label:gain:debt[:axis]")

    mark = sub.add_parser("mark-status", help="mark matching queue records with a closure/status")
    mark.add_argument("--project", required=True)
    mark.add_argument("--queue-file", default="", help="Queue path; default workspace/next_discriminator_queue.jsonl")
    mark.add_argument("--status", required=True)
    mark.add_argument("--template", default="", help="Match metadata.replay_template")
    mark.add_argument("--source", default="", help="Match row.source")
    mark.add_argument("--evidence-artifact", action="append", default=[])
    mark.add_argument("--note", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = project_dir_from_slug(args.project)
    if args.cmd == "append":
        proposal = DiscriminatorProposal(
            project=project_dir.name,
            trigger_artifact=args.trigger_artifact,
            claim_under_pressure=args.claim,
            rival_explanations=args.rival,
            cheapest_discriminator=args.test,
            kill_condition=args.kill,
            narrative_shortcut=infer_narrative_shortcut(args.claim, " ".join(args.rival), args.test, args.kill),
            instrument_risk=args.instrument_risk,
            required_artifacts=args.artifact,
            source=args.source,
            auto_testable=args.auto_testable,
            needs_human=not args.auto_testable,
            severity_level=args.severity_level,
            license_stage=args.license_stage,
            weak_test_risk=args.weak_test_risk,
        )
        path = append_discriminator(project_dir, proposal)
        print(f"appended 1 discriminator proposal: {path}")
        return 0
    if args.cmd == "from-inverter":
        inv_path = project_dir / "workspace" / "inverter_review.json"
        data = json.loads(inv_path.read_text(encoding="utf-8"))
        claim = args.claim or _clean_text(data.get("overall_assessment")) or "champion thesis"
        proposals = proposals_from_inverter_result(
            project=project_dir.name,
            trigger_artifact=str(inv_path.relative_to(project_dir)),
            claim_under_pressure=claim,
            inverter_result=data,
        )
        path, count = append_discriminators(project_dir, proposals)
        print(f"appended {count} discriminator proposal(s): {path}")
        return 0
    if args.cmd == "from-cold-shot":
        artifact_path = Path(args.artifact)
        if not artifact_path.is_absolute():
            artifact_path = project_dir / artifact_path
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
        proposals = proposals_from_cold_shot_result(
            project=project_dir.name,
            trigger_artifact=str(artifact_path),
            claim_under_pressure=args.claim,
            cold_shot_result=data,
        )
        path, count = append_discriminators(project_dir, proposals)
        print(f"appended {count} discriminator proposal(s): {path}")
        return 0
    if args.cmd == "debt-ladder":
        points = [_parse_debt_point(raw) for raw in args.point]
        path = write_background_debt_ladder(
            project_dir,
            label=args.label,
            claim_under_pressure=args.claim,
            debt_proxy=args.debt_proxy,
            points=points,
            source=args.source,
        )
        print(f"wrote background-debt ladder: {path}")
        return 0
    if args.cmd == "mark-status":
        qf = Path(args.queue_file) if args.queue_file else queue_path(project_dir)
        if not qf.is_absolute():
            qf = project_dir / qf
        count = update_discriminator_status(
            qf,
            status=args.status,
            template=args.template or None,
            source=args.source or None,
            evidence_artifacts=args.evidence_artifact,
            note=args.note,
        )
        print(f"updated {count} discriminator record(s): {qf}")
        return 0 if count else 1
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
