"""Activation-bound successor projects for prospective market-flow research."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue

from .autoresearch_subscription_job import enqueue_autoresearch_project_job
from .newton_candidate_provenance import resolve_newton_candidate_provenance


MODEL_BUNDLE_CAPSULE_SCHEMA = "jaggedthoughts-market-flow-model-bundle-capsule-v1"
SUCCESSOR_LINEAGE_SCHEMA = "jaggedthoughts-market-flow-successor-lineage-v1"
SUCCESSOR_HANDOFF_SCHEMA = "jaggedthoughts-market-flow-successor-handoff-v1"
SUCCESSOR_RESULT_SCHEMA = "jaggedthoughts-market-flow-successor-result-v1"
_RUN_SCHEMA = "jaggedthoughts-market-flow-shadow-run-v1"
_ACTIVATION_SCHEMA = "jaggedthoughts-model-research-activation-v1"
_RESEARCH_RESIDUAL_SCHEMA = "jaggedthoughts-market-flow-research-residual-v1"
_CANDIDATE_ID = "lagrangian_probability_current_rejected_shadow"
_PROJECT_FILES = (
    "gate_harness.py",
    "evidence_source_receipt.json",
    "evidence.txt",
    "evidence_holdout.txt",
    "evidence_farther_tail.txt",
    "project_charter.md",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verified(payload: Mapping[str, Any], schema: str, hash_field: str) -> dict[str, Any]:
    body = dict(payload)
    declared = str(body.pop(hash_field, ""))
    if body.get("schema") != schema or declared != stable_sha256(body):
        raise ValueError(f"{schema} content identity mismatch")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any], *, immutable: bool = False) -> None:
    rendered = json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists() and path.read_text(encoding="utf-8") != rendered:
        raise ValueError(f"content-addressed artifact changed: {path}")
    path.write_text(rendered, encoding="utf-8")


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"successor input already exists with different bytes: {path}")
        return
    path.write_bytes(payload)


def capture_market_flow_project_inputs(
    project_dir: str | Path, candidate_path: str | Path,
) -> dict[str, Any]:
    """Capture the carrier bytes and hashes needed to fork an exact successor."""
    project = Path(project_dir).expanduser().resolve()
    candidate = Path(candidate_path).expanduser().resolve()
    candidate.relative_to(project)
    repo = Path(__file__).resolve().parents[3]
    project.relative_to(repo / "projects")
    rubric = repo / "rubrics" / f"{project.name}.json"
    paths = {name: project / name for name in _PROJECT_FILES}
    paths["rubric.json"] = rubric
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ValueError(f"market-flow successor inputs are missing: {missing}")
    return {
        "candidate_source": candidate.read_text(encoding="utf-8"),
        "candidate_source_sha256": _sha256(candidate),
        "project_input_sha256": {name: _sha256(path) for name, path in paths.items()},
    }


def freeze_market_flow_model_bundle_capsule(
    run: Mapping[str, Any], *, project_dir: str | Path, output_dir: str | Path,
) -> dict[str, Any]:
    """Persist one immutable carrier/evidence capsule per exact model bundle."""
    frozen = _verified(run, _RUN_SCHEMA, "run_sha256")
    project = Path(project_dir).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    source = str(frozen.get("candidate_source") or "")
    hashes = dict(frozen.get("project_input_sha256") or {})
    if not source or not hashes:
        raise ValueError("sealed run predates exact successor-carrier preservation")
    source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if source_sha != frozen.get("candidate_sha256"):
        raise ValueError("sealed candidate source differs from its declared identity")
    capsule = output / "model_bundles" / str(frozen["model_bundle_sha256"])
    manifest_path = capsule / "manifest.json"
    if manifest_path.is_file():
        existing = _verified(
            json.loads(manifest_path.read_text(encoding="utf-8")),
            MODEL_BUNDLE_CAPSULE_SCHEMA, "capsule_sha256",
        )
        if not (
            existing.get("model_bundle_sha256") == frozen.get("model_bundle_sha256")
            and existing.get("candidate_sha256") == frozen.get("candidate_sha256")
            and existing.get("input_file_sha256", {}).get("test_model.py") == source_sha
        ):
            raise ValueError("existing model-bundle capsule has a different identity")
        return existing
    copied_hashes: dict[str, str] = {}
    for name in _PROJECT_FILES:
        path = project / name
        if not path.is_file() or _sha256(path) != hashes.get(name):
            raise ValueError(f"project input changed before bundle capsule freeze: {name}")
        destination = capsule / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(path, destination)
        if _sha256(destination) != hashes[name]:
            raise ValueError(f"bundle capsule input hash mismatch: {name}")
        copied_hashes[name] = hashes[name]
    rubric = Path(__file__).resolve().parents[3] / "rubrics" / f"{project.name}.json"
    if _sha256(rubric) != hashes.get("rubric.json"):
        raise ValueError("project rubric changed before bundle capsule freeze")
    if not (capsule / "rubric.json").exists():
        shutil.copy2(rubric, capsule / "rubric.json")
    if _sha256(capsule / "rubric.json") != hashes["rubric.json"]:
        raise ValueError("bundle capsule rubric hash mismatch")
    _write_bytes(capsule / "test_model.py", source.encode("utf-8"))
    body = {
        "schema": MODEL_BUNDLE_CAPSULE_SCHEMA,
        "source_project_id": frozen["project_id"],
        "originating_run_sha256": frozen["run_sha256"],
        "model_bundle_sha256": frozen["model_bundle_sha256"],
        "candidate_sha256": frozen["candidate_sha256"],
        "input_file_sha256": {
            "test_model.py": source_sha,
            **copied_hashes,
            "rubric.json": hashes["rubric.json"],
        },
        "automatic_model_mutation": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    manifest = {**body, "capsule_sha256": stable_sha256(body)}
    _write_json(manifest_path, manifest, immutable=True)
    return manifest


def _successor_rubric(payload: Mapping[str, Any], successor: str) -> dict[str, Any]:
    rubric = json.loads(json.dumps(dict(payload)))
    rubric["project"] = successor
    contract = rubric.get("evidence_contract")
    if isinstance(contract, dict):
        contract["format_provenance"] = (
            f"projects/{successor}/evidence_source_receipt.json"
        )
    return rubric


def _successor_seed(successor: str, activation: Mapping[str, Any]) -> str:
    residual = dict(activation["research_residual"])
    compact = {
        key: residual.get(key) for key in (
            "research_residual_sha256", "tournament_sha256",
            "inference_block_count", "min_inference_blocks",
            "candidate_survived", "candidate_on_point_estimate_frontier",
            "baseline_model_id", "candidate_improvement_over_baseline",
            "next_permitted_action", "search_question",
        )
    }
    return (
        f"# {successor}: prospective survivor successor\n\n"
        "## Status\n\n"
        "Unadmitted research seed. It has no paper-policy, portfolio, or capital "
        "authority.\n\n"
        "## Search instruction\n\n"
        "Find a compact executable mechanism that explains the prospective survivor "
        "without copying its rejected ancestor. Preserve the frozen evidence, controls, "
        "chronology, density ABI, and deterministic gates.\n\n"
        "Work on the measured residual below; do not broaden the target or weaken a "
        "control. The complete typed residual is in `research_residual.json`.\n\n"
        f"```json\n{json.dumps(compact, indent=2, sort_keys=True)}\n```\n\n"
        f"Source activation: `{activation['activation_sha256']}`.\n"
    )


def enqueue_market_flow_successor(
    *, workspace: str | Path, project_dir: str | Path, output_dir: str | Path,
    run: Mapping[str, Any], tournament: Mapping[str, Any],
    activation: Mapping[str, Any],
) -> dict[str, Any]:
    """Fork and queue one exact activation-bound Newton successor."""
    frozen = _verified(run, _RUN_SCHEMA, "run_sha256")
    activated = _verified(activation, _ACTIVATION_SCHEMA, "activation_sha256")
    tournament_body = dict(tournament)
    tournament_sha = str(tournament_body.pop("tournament_sha256", ""))
    if not tournament_sha or stable_sha256(tournament_body) != tournament_sha:
        raise ValueError("market-flow tournament content identity mismatch")
    residual = dict(activated.get("research_residual") or {})
    residual_body = dict(residual)
    residual_sha = str(residual_body.pop("research_residual_sha256", ""))
    if not (
        activated.get("action") == "successor_research_due"
        and activated.get("source_run_sha256") == frozen.get("run_sha256")
        and activated.get("project_id") == frozen.get("project_id")
        and activated.get("candidate_sha256") == frozen.get("candidate_sha256")
        and activated.get("model_bundle_sha256") == frozen.get("model_bundle_sha256")
        and activated.get("tournament_sha256") == tournament_sha
        and tournament.get("inference_sufficient") is True
        and _CANDIDATE_ID in set(tournament.get("survivor_model_ids") or ())
        and "empirical_markov" in set(frozen.get("forecasts") or {})
        and f"run:{frozen['run_sha256']}" in set(tournament.get("source_refs") or ())
        and frozen.get("prospective_promotion_eligible") is False
        and frozen.get("paper_policy_authority") is False
        and frozen.get("capital_authority") is False
        and tournament.get("paper_policy_authority") is False
        and tournament.get("capital_authority") is False
        and activated.get("agent_authority") == "propose_evidence_bound_project_only"
        and activated.get("automatic_model_mutation") is False
        and activated.get("capital_authority") is False
        and residual.get("schema") == _RESEARCH_RESIDUAL_SCHEMA
        and residual_sha == stable_sha256(residual_body)
        and residual.get("tournament_sha256") == tournament_sha
        and residual.get("source_run_sha256") == frozen.get("run_sha256")
        and residual.get("model_bundle_sha256") == frozen.get("model_bundle_sha256")
        and residual.get("candidate_sha256") == frozen.get("candidate_sha256")
        and residual.get("next_permitted_action") == "successor_research_due"
        and residual.get("automatic_model_mutation") is False
        and residual.get("capital_authority") is False
    ):
        raise ValueError("successor handoff is not bound to an eligible exact activation")

    project = Path(project_dir).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    handoff_path = output / "handoffs" / f"{activated['activation_sha256']}.json"
    if handoff_path.is_file():
        return _verified(
            json.loads(handoff_path.read_text(encoding="utf-8")),
            SUCCESSOR_HANDOFF_SCHEMA, "handoff_sha256",
        )
    capsule_path = output / "model_bundles" / str(frozen["model_bundle_sha256"])
    capsule = _verified(
        json.loads((capsule_path / "manifest.json").read_text(encoding="utf-8")),
        MODEL_BUNDLE_CAPSULE_SCHEMA, "capsule_sha256",
    )
    if not (
        capsule.get("candidate_sha256") == frozen.get("candidate_sha256")
        and capsule.get("model_bundle_sha256") == frozen.get("model_bundle_sha256")
    ):
        raise ValueError("model-bundle capsule differs from the activated lineage")

    repo = Path(__file__).resolve().parents[3]
    project.relative_to(repo / "projects")
    successor = f"{project.name}_successor_{activated['activation_sha256'][:12]}"
    successor_root = repo / "projects" / successor
    successor_root.mkdir(parents=True, exist_ok=True)
    for name, expected in dict(capsule["input_file_sha256"]).items():
        if name == "rubric.json":
            continue
        source = capsule_path / name
        if _sha256(source) != expected:
            raise ValueError(f"successor capsule source hash mismatch: {name}")
        payload = source.read_bytes()
        if name == "project_charter.md":
            payload += (
                "\n## Prospective successor identity\n\n"
                f"This is `{successor}`, a distinct research project created from "
                f"activation `{activated['activation_sha256']}`. The ancestor remains "
                "unchanged. Admission and every downstream authority remain false.\n"
            ).encode("utf-8")
        _write_bytes(successor_root / name, payload)
    seed = _successor_seed(successor, activated)
    _write_bytes(successor_root / "thesis.md", seed.encode("utf-8"))
    _write_bytes(successor_root / "current_iteration.md", seed.encode("utf-8"))
    _write_json(successor_root / "research_residual.json", residual, immutable=True)
    (successor_root / "workspace").mkdir(exist_ok=True)

    rubric_payload = json.loads((capsule_path / "rubric.json").read_text(encoding="utf-8"))
    _write_json(
        repo / "rubrics" / f"{successor}.json",
        _successor_rubric(rubric_payload, successor), immutable=True,
    )
    lineage_body = {
        "schema": SUCCESSOR_LINEAGE_SCHEMA,
        "source_project_id": frozen["project_id"],
        "successor_project_id": successor,
        "source_run_sha256": frozen["run_sha256"],
        "source_candidate_sha256": frozen["candidate_sha256"],
        "trial_family_id": frozen["trial_family_id"],
        "model_bundle_sha256": frozen["model_bundle_sha256"],
        "tournament_sha256": tournament_sha,
        "activation_sha256": activated["activation_sha256"],
        "research_residual_sha256": residual_sha,
        "capsule_sha256": capsule["capsule_sha256"],
        "source_input_file_sha256": capsule["input_file_sha256"],
        "successor_input_file_sha256": {
            path.name: _sha256(path) for path in (
                successor_root / "test_model.py",
                successor_root / "gate_harness.py",
                successor_root / "evidence_source_receipt.json",
                successor_root / "evidence.txt",
                successor_root / "evidence_holdout.txt",
                successor_root / "evidence_farther_tail.txt",
                successor_root / "project_charter.md",
                successor_root / "thesis.md",
                successor_root / "current_iteration.md",
                successor_root / "research_residual.json",
                repo / "rubrics" / f"{successor}.json",
            )
        },
        "ancestor_mutated": False,
        "registration_authority": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    lineage = {**lineage_body, "lineage_sha256": stable_sha256(lineage_body)}
    _write_json(successor_root / "source_activation.json", lineage, immutable=True)
    queued = enqueue_autoresearch_project_job(
        workspace, project=successor, rubric=successor,
        research_trigger={
            "schema": "jaggedthoughts-market-flow-successor-trigger-v1",
            "activation_sha256": activated["activation_sha256"],
            "lineage_sha256": lineage["lineage_sha256"],
            "research_residual_sha256": residual_sha,
            "research_residual": residual,
            "automatic_model_mutation": False,
            "signal_authority": False,
            "paper_policy_authority": False,
            "capital_authority": False,
        },
    )
    handoff_body = {
        "schema": SUCCESSOR_HANDOFF_SCHEMA,
        "status": "queued_distinct_successor",
        "source_project_id": frozen["project_id"],
        "successor_project_id": successor,
        "activation_sha256": activated["activation_sha256"],
        "lineage_sha256": lineage["lineage_sha256"],
        "request_sha256": queued["request_sha256"],
        "work_id": queued["work_id"],
        "ancestor_mutated": False,
        "registration_authority": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    handoff = {**handoff_body, "handoff_sha256": stable_sha256(handoff_body)}
    _write_json(handoff_path, handoff, immutable=True)
    return handoff


def classify_market_flow_successor(
    workspace: str | Path, handoff: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify one queued successor without granting downstream authority."""
    frozen_handoff = _verified(
        handoff, SUCCESSOR_HANDOFF_SCHEMA, "handoff_sha256",
    )
    root = Path(workspace).expanduser().resolve()
    repo = Path(__file__).resolve().parents[3]
    successor = str(frozen_handoff["successor_project_id"])
    project = (repo / "projects" / successor).resolve()
    project.relative_to(repo / "projects")
    lineage = _verified(
        json.loads((project / "source_activation.json").read_text(encoding="utf-8")),
        SUCCESSOR_LINEAGE_SCHEMA, "lineage_sha256",
    )
    if not (
        lineage["lineage_sha256"] == frozen_handoff["lineage_sha256"]
        and lineage["activation_sha256"] == frozen_handoff["activation_sha256"]
        and lineage["successor_project_id"] == successor
        and lineage.get("capital_authority") is False
    ):
        raise ValueError("successor handoff and project lineage differ")

    result_dir = project / "workspace" / "prospective_admission"
    result_path = result_dir / f"{frozen_handoff['activation_sha256']}.json"
    if result_path.is_file():
        existing = _verified(
            json.loads(result_path.read_text(encoding="utf-8")),
            SUCCESSOR_RESULT_SCHEMA, "successor_result_sha256",
        )
        if existing.get("candidate_sha256"):
            archived = project / str(existing.get("candidate_path") or "")
            archived.relative_to(project)
            if not archived.is_file() or _sha256(archived) != existing["candidate_sha256"]:
                raise ValueError("archived successor candidate differs from its result")
        return existing

    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    try:
        row = connection.execute(
            "SELECT * FROM work_items WHERE work_id=?",
            (str(frozen_handoff["work_id"]),),
        ).fetchone()
        job = work_queue.row_to_dict(row) if row else None
    finally:
        connection.close()
    if not job:
        raise ValueError("successor work item is missing")
    payload = dict(job.get("payload") or {})
    if not (
        job.get("kind") == "jaggedthoughts_autoresearch_project"
        and payload.get("request_sha256") == frozen_handoff["request_sha256"]
        and payload.get("project") == successor
    ):
        raise ValueError("successor work item differs from its handoff")
    queue_status = str(job.get("status") or "")
    if queue_status not in {"done", "failed", "dead_letter", "retired"}:
        return {
            "schema": SUCCESSOR_RESULT_SCHEMA,
            "status": "research_running" if queue_status in {"claimed", "running"} else "research_queued",
            "queue_status": queue_status,
            "successor_project_id": successor,
            "activation_sha256": frozen_handoff["activation_sha256"],
            "work_id": frozen_handoff["work_id"],
            "prospective_shadow_eligible": False,
            "paper_policy_authority": False,
            "capital_authority": False,
        }

    terminal_status = "typed_failure"
    reason = str(payload.get("error") or payload.get("stage") or queue_status)
    candidate_sha = None
    gate_sha = None
    job_result_sha = None
    completed_at = datetime.fromtimestamp(
        int(job.get("updated_at") or 0), timezone.utc,
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    evidence_receipt_sha = None
    partition_hashes: dict[str, str] = {}
    provenance: dict[str, Any] | None = None
    failed_gates: list[str] = []
    if queue_status == "done" and payload.get("result_path"):
        request_path = (root / str(payload.get("request_path") or "")).resolve()
        request_path.relative_to(root)
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request_body = dict(request)
        request_sha = str(request_body.pop("request_sha256", ""))
        trigger = dict(request.get("research_trigger") or {})
        if not (
            request_sha == stable_sha256(request_body)
            and request_sha == frozen_handoff["request_sha256"]
            and request.get("schema") == "jaggedthoughts-autoresearch-project-request-v1"
            and request.get("project") == successor
            and request.get("rubric") == successor
            and request.get("runtime") == "codex"
            and request.get("transport") == "operator_subscription_cli"
            and request.get("iters") == 1
            and trigger.get("activation_sha256") == frozen_handoff["activation_sha256"]
            and trigger.get("lineage_sha256") == lineage["lineage_sha256"]
            and trigger.get("research_residual_sha256")
            == lineage.get("research_residual_sha256")
            and trigger.get("research_residual")
            == json.loads((project / "research_residual.json").read_text(encoding="utf-8"))
            and trigger.get("automatic_model_mutation") is False
            and trigger.get("signal_authority") is False
            and trigger.get("paper_policy_authority") is False
            and trigger.get("capital_authority") is False
            and request.get("signal_authority") is False
        ):
            raise ValueError("successor request lineage is invalid")
        artifact_path = (root / str(payload.get("result_path") or "")).resolve()
        artifact_path.relative_to(root)
        job_result = _verified(
            json.loads(artifact_path.read_text(encoding="utf-8")),
            "jaggedthoughts-autoresearch-project-result-v1", "result_sha256",
        )
        if not (
            job_result["result_sha256"] == payload.get("result_sha256")
            and job_result["request_sha256"] == request_sha
            and (
                (job_result.get("status") == "completed" and job_result.get("returncode") == 0)
                or (
                    job_result.get("status") == "typed_failure"
                    and int(job_result.get("returncode") or 0) != 0
                )
            )
            and job_result.get("transport") == "operator_subscription_cli"
            and job_result.get("api_key_environment_removed") is True
            and job_result.get("signal_authority") is False
            and job_result.get("capital_authority") is False
        ):
            raise ValueError("successor job result differs from its queue receipt")
        job_result_sha = str(job_result["result_sha256"])
        completed_at = str(job_result.get("completed_at") or "")
        if not completed_at:
            raise ValueError("successor job result lacks completion time")
        if job_result.get("status") == "completed":
            candidate = project / "test_model.py"
            gate_path = project / "latest_gate_results.json"
            receipt_path = project / "evidence_source_receipt.json"
            rubric_path = repo / "rubrics" / f"{successor}.json"
            outputs = dict(job_result.get("output_file_sha256") or {})
            for name, path in {
                "test_model.py": candidate,
                "latest_gate_results.json": gate_path,
            }.items():
                if not path.is_file() or _sha256(path) != outputs.get(name):
                    raise ValueError(f"successor output hash mismatch: {name}")
            eval_path = project / "latest_eval_results.json"
            if "latest_eval_results.json" in outputs and (
                not eval_path.is_file()
                or _sha256(eval_path) != outputs["latest_eval_results.json"]
            ):
                raise ValueError("successor output hash mismatch: latest_eval_results.json")
            inputs = dict(request.get("input_file_sha256") or {})
            for name, path in {
                "gate_harness": project / "gate_harness.py",
                "evidence_receipt": receipt_path,
                "rubric": rubric_path,
            }.items():
                if not path.is_file() or _sha256(path) != inputs.get(name):
                    raise ValueError(f"successor fixed input changed during research: {name}")
            successor_inputs = dict(lineage.get("successor_input_file_sha256") or {})
            partitions = {
                "visible": project / "evidence.txt",
                "holdout": project / "evidence_holdout.txt",
                "farther_tail": project / "evidence_farther_tail.txt",
            }
            for path in partitions.values():
                if _sha256(path) != successor_inputs.get(path.name):
                    raise ValueError(f"successor evidence partition changed: {path.name}")
            residual_path = project / "research_residual.json"
            if (
                not residual_path.is_file()
                or _sha256(residual_path)
                != successor_inputs.get("research_residual.json")
            ):
                raise ValueError("successor research residual changed during research")
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            candidate_sha = _sha256(candidate)
            gate_sha = _sha256(gate_path)
            evidence_receipt_sha = _sha256(receipt_path)
            partition_hashes = {name: _sha256(path) for name, path in partitions.items()}
            provenance = resolve_newton_candidate_provenance(project, candidate)
            if not (
                gate.get("schema") == "jaggedthoughts-probability-current-newton-gates-v1"
                and gate.get("authority") == "retrospective_survivorship_exposed_diagnostic"
                and gate.get("harness_ok") is True
                and gate.get("candidate_sha256") == candidate_sha
                and gate.get("evidence_receipt_sha256") == evidence_receipt_sha
                and gate.get("partition_file_sha256s") == partition_hashes
                and gate.get("candidate_provenance") == provenance
                and gate.get("capital_authority") is False
                and provenance.get("status") == "resolved"
                and provenance.get("origin") == "subscription_newton_submission"
                and provenance.get("run_id") is not None
            ):
                raise ValueError("successor gate is not bound to a subscription candidate")
            failed_gates = [
                str(row.get("name") or "unknown") for row in gate.get("gates") or ()
                if row.get("passed") is False
            ]
            terminal_status = (
                "admission_candidate"
                if gate.get("screen_pass") is True else "screen_rejected"
            )
            reason = (
                "subscription successor passed its frozen retrospective screen"
                if gate.get("screen_pass") is True else
                "subscription successor failed its frozen retrospective screen"
            )
            candidate_archive = result_dir / "candidates" / f"{candidate_sha}.py"
            _write_bytes(candidate_archive, candidate.read_bytes())
        else:
            reason = f"subscription autoresearch exited {job_result.get('returncode')}"
    elif queue_status == "done":
        reason = f"subscription job ended without a result artifact: {reason}"

    body = {
        "schema": SUCCESSOR_RESULT_SCHEMA,
        "status": terminal_status,
        "reason": reason[:1_000],
        "queue_status": queue_status,
        "source_project_id": lineage["source_project_id"],
        "successor_project_id": successor,
        "source_run_sha256": lineage["source_run_sha256"],
        "trial_family_id": lineage["trial_family_id"],
        "model_bundle_sha256": lineage["model_bundle_sha256"],
        "tournament_sha256": lineage["tournament_sha256"],
        "source_candidate_sha256": lineage["source_candidate_sha256"],
        "research_residual_sha256": lineage["research_residual_sha256"],
        "activation_sha256": frozen_handoff["activation_sha256"],
        "lineage_sha256": lineage["lineage_sha256"],
        "request_sha256": frozen_handoff["request_sha256"],
        "work_id": frozen_handoff["work_id"],
        "job_result_sha256": job_result_sha,
        "completed_at": completed_at,
        "candidate_sha256": candidate_sha,
        "candidate_path": (
            f"workspace/prospective_admission/candidates/{candidate_sha}.py"
            if candidate_sha else None
        ),
        "gate_result_sha256": gate_sha,
        "evidence_receipt_sha256": evidence_receipt_sha,
        "partition_file_sha256s": partition_hashes,
        "candidate_provenance": provenance,
        "failed_gate_names": failed_gates,
        "admission_scope": "prospective_shadow_only" if terminal_status == "admission_candidate" else None,
        "prospective_shadow_eligible": terminal_status == "admission_candidate",
        "registration_authority": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    result = {**body, "successor_result_sha256": stable_sha256(body)}
    _write_json(result_path, result, immutable=True)
    return result


def compile_market_flow_successor_memory(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt one terminal successor result to the existing research-memory leaf."""
    terminal = _verified(result, SUCCESSOR_RESULT_SCHEMA, "successor_result_sha256")
    status = str(terminal.get("status") or "")
    interpretations = {
        "typed_failure": "search_process_failure_only",
        "screen_rejected": "exact_candidate_counterexample_only",
        "admission_candidate": "prospective_shadow_candidate_only",
    }
    if status not in interpretations:
        raise ValueError("successor research memory requires a terminal result")
    evaluated_at = str(terminal.get("completed_at") or "")
    if not evaluated_at:
        raise ValueError("terminal successor result lacks completion time")
    result_sha = str(terminal["successor_result_sha256"])
    source_refs = [
        f"successor-result:{result_sha}",
        f"activation:{terminal['activation_sha256']}",
        f"lineage:{terminal['lineage_sha256']}",
        f"request:{terminal['request_sha256']}",
    ]
    source_refs.extend(
        f"{label}:{value}" for label, value in (
            ("job-result", terminal.get("job_result_sha256")),
            ("candidate", terminal.get("candidate_sha256")),
            ("gate", terminal.get("gate_result_sha256")),
            ("evidence", terminal.get("evidence_receipt_sha256")),
            ("tournament", terminal.get("tournament_sha256")),
            ("source-run", terminal.get("source_run_sha256")),
            ("research-residual", terminal.get("research_residual_sha256")),
        ) if value
    )
    body = {
        "schema": "jaggedthoughts-mechanism-research-result-v1",
        "project_id": str(terminal["successor_project_id"]),
        "label": "Market-flow subscription successor",
        "mode": "subscription_newton_successor",
        "project_path": f"projects/{terminal['successor_project_id']}",
        "evaluated_at": evaluated_at,
        "evidence_epoch": terminal.get("evidence_receipt_sha256"),
        "source_url": None,
        "row_counts": {},
        "point_in_time_authority": "retrospective_survivorship_exposed_diagnostic",
        "iteration_count": 1,
        "source_result_schema": SUCCESSOR_RESULT_SCHEMA,
        "source_successor_result_sha256": result_sha,
        "source_project_id": terminal.get("source_project_id"),
        "source_run_sha256": terminal.get("source_run_sha256"),
        "trial_family_id": terminal.get("trial_family_id"),
        "model_bundle_sha256": terminal.get("model_bundle_sha256"),
        "tournament_sha256": terminal.get("tournament_sha256"),
        "source_candidate_sha256": terminal.get("source_candidate_sha256"),
        "research_residual_sha256": terminal.get("research_residual_sha256"),
        "candidate_sha256": terminal.get("candidate_sha256"),
        "gate_result_sha256": terminal.get("gate_result_sha256"),
        "evidence_receipt_sha256": terminal.get("evidence_receipt_sha256"),
        "partition_file_sha256s": dict(terminal.get("partition_file_sha256s") or {}),
        "failed_gate_names": list(terminal.get("failed_gate_names") or ()),
        "terminal_status": status,
        "status": status,
        "learning_interpretation": interpretations[status],
        "family_retirement_authority": False,
        "harness_ok": status in {"screen_rejected", "admission_candidate"},
        "screen_pass": status == "admission_candidate",
        "promotion_eligible": False,
        "source_refs": source_refs,
        "authority": "experiment_only",
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "research_result_sha256": stable_sha256(body)}


__all__ = [
    "MODEL_BUNDLE_CAPSULE_SCHEMA", "SUCCESSOR_HANDOFF_SCHEMA",
    "SUCCESSOR_LINEAGE_SCHEMA", "SUCCESSOR_RESULT_SCHEMA",
    "capture_market_flow_project_inputs", "classify_market_flow_successor",
    "compile_market_flow_successor_memory",
    "enqueue_market_flow_successor", "freeze_market_flow_model_bundle_capsule",
]
