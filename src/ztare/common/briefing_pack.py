from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ponytail: files larger than this are hardlinked (same-device) instead of copied;
# fallback to copy on cross-device or permission error. 5MB threshold keeps small
# files (JSON, py, md) as copies for isolation while skipping the 149MB episode copy.
_HARDLINK_SIZE_THRESHOLD_BYTES = 5 * 1024 * 1024

from ztare.common.cegis_membrane import DISCOVERY, EVALUATION, HARNESS_DEBUG
from ztare.common.science_output_policy import SCIENCE_OUTPUT_POLICY
from ztare.common.ask_spec import (
    AskSpec,
    render_ask_spec_markdown,
    worldmodel_candidate_ask_spec,
)
from ztare.common.strategy_card_roles import (
    META_HARDENING_LANE,
    strategy_card_lane,
)

_COMPACT_VISIBLE_WORKBENCH_REFS = (
    # Loop-control sufficient statistics. P0 search-policy observations stay
    # outside the leaf prompt; once control-ready they may alter allocator
    # weights or structural constraints, never semantic advice.
    "workspace/latest_information_yield.json",
    # object-level fiber effects with evidence refs (2026-07-12): the leaf's
    # keyhole onto interior dynamics — written-but-unstaged was the third
    # dead-channel instance of the week
    "workspace/latest_fiber_effect_table.json",
    # ponytail: project-local champion — the patch base the leaf must start from.
    # Resolved via _resolve_visible_artifact which checks project/ prefix first.
    "test_model.py",
)

_VISIBLE_ARTIFACT_REF_KEYS = frozenset(
    {
        "candidate_path",
        "diagnostics_ref",
        "evidence_ref",
        "path",
        "producer_receipt",
        "receipt_ref",
        "replay_diagnostics_ref",
        "seed_path",
        "source",
        "source_log",
        "source_receipt",
        "source_ref",
        "submission",
    }
)
_VISIBLE_ARTIFACT_REF_KEY_SUFFIXES = ("_ref", "_path")
_VISIBLE_ARTIFACT_REF_LIST_KEYS = frozenset(
    {
        "evidence_refs",
        "new_evidence_refs",
        "source_refs",
        "visible_artifacts",
    }
)


@dataclass(frozen=True)
class BriefingPack:
    """File-backed renderer for agentic workers.

    The API renderer remains a self-contained prompt. This pack is the
    agentic renderer: small entry prompt, authenticated files, visible tools,
    and no promotion authority.
    """

    workbench: Path
    entry_prompt: str
    manifest: dict[str, Any]


@dataclass(frozen=True)
class ToolSource:
    ref: str
    source: Path
    authority_level: str = "visible_diagnostic_tool_source"


@dataclass(frozen=True)
class BriefingPackRequest:
    repo: Path
    agent_id: str
    task: str
    context: str
    briefing: str | None = None
    sealed_boundary_present: bool = False
    run_role: str = EVALUATION
    tool_sources: tuple[ToolSource, ...] = ()
    ask_specs: tuple[AskSpec, ...] = ()
    root_env_var: str = "ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT"


def _gc_old_packs(root: Path, safe_agent: str) -> None:
    """Delete packs older than ZTARE_PACK_TTL_HOURS (default 48h) for this agent prefix.

    # ponytail: called at pack-build time so GC is free-riding on existing I/O;
    # no daemon needed. Best-effort — any OSError is silently swallowed so a
    # permissions race never blocks the build.
    """
    try:
        raw_ttl = os.environ.get("ZTARE_PACK_TTL_HOURS", "48")
        ttl_s = max(1.0, float(raw_ttl)) * 3600
    except ValueError:
        ttl_s = 48 * 3600
    cutoff = time.time() - ttl_s
    if not root.is_dir():
        return
    for d in root.iterdir():
        if not d.is_dir():
            continue
        if not d.name.startswith(safe_agent):
            continue
        try:
            if d.stat().st_mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


def build_briefing_pack(request: BriefingPackRequest) -> BriefingPack:
    safe_agent = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in request.agent_id)[:80] or "agent"
    digest = hashlib.sha256(request.context.encode("utf-8", errors="ignore")).hexdigest()[:12]
    root = Path(os.environ.get(request.root_env_var) or Path(tempfile.gettempdir()) / "ztare_visible_workbench")
    _gc_old_packs(root, safe_agent)
    workbench = root / f"{safe_agent}_{digest}"
    if workbench.exists():
        shutil.rmtree(workbench)
    workbench.mkdir(parents=True, exist_ok=True)

    records_payload = _records_doc(repo=request.repo, briefing=request.briefing, agent_id=request.agent_id)
    structured_records = records_payload.get("structured_records") or []
    task_spec = request.ask_specs[0] if request.ask_specs else _ask_spec(request.task, structured_records)
    artifacts = _materialize_structured_visible_artifacts(
        repo=request.repo,
        workbench=workbench,
        agent_id=request.agent_id,
        records=structured_records,
        run_role=request.run_role,
    )
    artifacts.extend(_materialize_tool_sources(workbench=workbench, sources=request.tool_sources))
    task_text = _task_doc(
        request.task,
        structured_records,
        spec=task_spec,
        run_role=request.run_role,
        artifacts=artifacts,
    )
    attention_text = _attention_doc(
        briefing=request.briefing,
        context=request.context,
        records=structured_records,
        run_role=request.run_role,
        artifacts=artifacts,
    )
    _write_text(workbench / "TASK.md", task_text)
    _write_json(workbench / "ASKS.json", {"schema": "ztare-ask-spec-index-v1", "asks": [task_spec.to_dict()]})
    _write_text(workbench / "ATTENTION.md", attention_text)
    _write_json(workbench / "RECORDS.json", records_payload)
    _write_text(workbench / "CONTEXT.md", request.context)
    _write_text(workbench / "WORKBENCH_TOOLS.md", _tools_doc(run_role=request.run_role, is_worldmodel=_looks_like_worldmodel_payload_task(request.task)))
    _write_text(
        workbench / "README.md",
        visible_workbench_contract_text() + "\n",
    )

    authority_project_ref, authority_project_path = _infer_authority_project(records_payload, request.repo)
    manifest = {
        "schema": "ztare-visible-agent-workbench-v1",
        "agent_id": request.agent_id,
        "source_repo_name": request.repo.name,
        "source_repo_path": str(request.repo.resolve()),
        "authority_project_ref": authority_project_ref,
        "authority_project_path": str(authority_project_path) if authority_project_path else "",
        "context_sha256": _sha_text(request.context),
        "task_sha256": _sha_text(request.task),
        "briefing_sha256": _sha_text(request.briefing or ""),
        "sealed_boundary_present": request.sealed_boundary_present,
        "run_role": request.run_role,
        "holdout_visibility": "sealed_requires_explicit_evidence_role_transition",
        "front_door": ["TASK.md", "ASKS.json", "ATTENTION.md", "RECORDS.json", "WORKBENCH_TOOLS.md"],
        "background": ["CONTEXT.md"],
        "policy": (
            "This cwd contains prompt-visible artifacts only. Active holdout "
            "artifacts stay sealed in every run role; a counterexample becomes "
            "visible only through an explicit evidence-role transition that also "
            "binds a successor withheld slice. "
            "Environment actions and authority gates must be requested through "
            "typed workbench actions."
        ),
        "pack_files": _pack_file_records(workbench),
        "visible_artifacts": artifacts,
        "projection_receipt": _pack_projection_receipt(
            records_payload=records_payload,
            task_text=task_text,
            attention_text=attention_text,
        ),
    }
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    _write_text(workbench / "visible_manifest.json", manifest_text)
    _write_text(workbench / "MANIFEST.json", manifest_text)
    return BriefingPack(
        workbench=workbench,
        entry_prompt=entry_prompt(),
        manifest=manifest,
    )


def _infer_authority_project(records_payload: dict[str, Any], repo: Path) -> tuple[str, Path | None]:
    source_ref = str(records_payload.get("source_ref") or "").strip()
    parts = Path(source_ref).parts
    if len(parts) >= 3 and parts[0] == "projects" and parts[2] == "workspace":
        project_ref = str(Path(parts[0]) / parts[1])
        project_path = (repo / project_ref).resolve()
        if (project_path / "gate_harness.py").exists():
            return project_ref, project_path
        return project_ref, None
    return "", None


def entry_prompt() -> str:
    return visible_workbench_contract_text()


def visible_workbench_contract_text() -> str:
    """Single owner for the staged visible-workbench execution contract."""

    return (
        "You are in a staged visible workbench. Read `TASK.md`, `ASKS.json`, and "
        "`ATTENTION.md` first; use `RECORDS.json` for exact refs/hashes and "
        "`CONTEXT.md` only as background. Run local shell commands in this cwd "
        "to use the staged visible probe tools in `WORKBENCH_TOOLS.md`; "
        "temporary scratch files are allowed inside this staged workbench only. "
        "Follow `MANIFEST.json.run_role`: DISCOVERY may "
        "consume staged holdout/counterexample evidence but must label it as "
        "discovery, not clean transfer; EVALUATION must keep holdout sealed. Do "
        "not modify source artifacts, spend environment actions, or run authority "
        "gates unless the task explicitly grants that capability. Return exactly "
        "the typed contract requested in `TASK.md` as your final answer."
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


_EVIDENCE_DIGEST_START = "<!-- EVIDENCE_DIGEST_START -->"
_EVIDENCE_DIGEST_END = "<!-- EVIDENCE_DIGEST_END -->"


def _strip_evidence_digest(task_text: str) -> str:
    """FIX 4: remove the evidence digest block from TASK.md and replace with a one-line pointer.

    The full digest lives in CONTEXT.md (background authority). TASK.md carries
    only the pointer so the digest is never duplicated across the two files.
    RECORDS.json still carries the structured form (unaffected — built from
    _records_doc separately).
    """
    start = task_text.find(_EVIDENCE_DIGEST_START)
    end = task_text.find(_EVIDENCE_DIGEST_END)
    if start < 0 or end < 0 or end <= start:
        return task_text  # sentinel not present — no-op (legacy / non-loop paths)
    end_full = end + len(_EVIDENCE_DIGEST_END)
    pointer = "Full quotiented evidence digest: CONTEXT.md §GROUNDING DATA"
    return task_text[:start].rstrip() + "\n    " + pointer + "\n" + task_text[end_full:].lstrip("\n")


def _task_doc(
    task: str,
    records: list[Any] | None = None,
    *,
    spec: AskSpec | None = None,
    run_role: str = EVALUATION,
    artifacts: list[dict[str, Any]] | None = None,
) -> str:
    task_text = str(task or "")
    # FIX 4: strip the evidence digest sentinel block before rendering TASK.md.
    # The full digest is kept in CONTEXT.md; TASK.md gets a one-line pointer.
    task_text = _strip_evidence_digest(task_text)
    if _looks_like_worldmodel_payload_task(task_text):
        return _worldmodel_task_doc(
            task_text,
            records or [],
            spec=spec,
            run_role=run_role,
            artifacts=artifacts or [],
        )
    ask = spec or AskSpec(
        contract_id="generic-typed-contract-v1",
        objective="Return exactly the typed contract requested below. Do not replace it with a status note or file summary.",
        target_surface="advisory",
        expected_output_schema="task_declared",
        validator="task_declared",
        authority_level="routing_only",
        blocking_policy="advisory",
        source_file="src/ztare/common/briefing_pack.py",
        source_function="_task_doc",
    )
    return (
        "# Task\n\n"
        + render_ask_spec_markdown(ask)
        + "\n"
        f"{task_text.rstrip()}\n"
    )


def _ask_spec(task: str, records: list[Any]) -> AskSpec:
    if _looks_like_worldmodel_payload_task(str(task or "")):
        if _worldmodel_turn_focus() == "task_hypothesis":
            return AskSpec(
                contract_id="worldmodel-task-hypothesis-v1",
                objective=_worldmodel_task_hypothesis_objective(),
                target_surface="candidate",
                expected_output_schema="worldmodel_typed_payload",
                validator=(
                    "ztare.validator.worldmodel_typed_payload."
                    "parse_worldmodel_typed_payload_text"
                ),
                authority_level="routing_only",
                blocking_policy="blocks_candidate",
                source_file="src/ztare/common/briefing_pack.py",
                source_function="_worldmodel_task_doc",
                examples=(
                    "Keep the staged transition carrier behavior unchanged.",
                    "Append one falsifiable GOAL_PREDICATE over the transition state.",
                    "Name a rival and a discriminating intervention in thesis_markdown.",
                    "The registered task adjudicator retains discharge authority.",
                ),
                current_refs=tuple(
                    f"routing_record_sha256:{sha}"
                    for sha in _task_hypothesis_strategy_shas(records)
                ),
            )
        return worldmodel_candidate_ask_spec(
            objective=_worldmodel_induction_objective(),
            current_refs=_worldmodel_current_refs(records),
        )
    return AskSpec(
        contract_id="generic-typed-contract-v1",
        objective="Return exactly the typed contract requested below. Do not replace it with a status note or file summary.",
        target_surface="advisory",
        expected_output_schema="task_declared",
        validator="task_declared",
        authority_level="routing_only",
        blocking_policy="advisory",
        source_file="src/ztare/common/briefing_pack.py",
        source_function="_task_doc",
    )


def _looks_like_worldmodel_payload_task(task: str) -> bool:
    text = str(task or "")
    if "WORLDMODEL TYPED PAYLOAD CONTRACT:" in text:
        return True
    return (
        "RESUBMIT ONLY ONE RAW JSON OBJECT" in text
        and "`test_model_py`" in text
        and (
            "LEAF_WORKBENCH" in text
            or "CARRIED RECEIPT FACTS" in text
            or "SEALED BOUNDARY-CEGAR" in text
        )
    )


def _worldmodel_task_doc(
    task: str,
    records: list[Any],
    *,
    spec: AskSpec | None = None,
    run_role: str = EVALUATION,
    artifacts: list[dict[str, Any]] | None = None,
) -> str:
    hypothesis_focus = _worldmodel_turn_focus() == "task_hypothesis"
    active_shas = (
        _task_hypothesis_strategy_shas(records)
        if hypothesis_focus
        else _strategy_failure_shas(records)
    )
    shas_text = "\n".join(f"- {sha}" for sha in active_shas) if active_shas else "- See ATTENTION.md / RECORDS.json."
    evidence_lines = _evidence_status_lines(
        run_role=run_role,
        artifacts=artifacts or [],
        records=records,
    )
    induction_objective = (
        _worldmodel_task_hypothesis_objective()
        if hypothesis_focus
        else _worldmodel_induction_objective()
    )
    science_contract = (
        "Hypothesis-first policy: preserve accepted transition behavior; spend "
        "this turn only on a falsifiable task predicate and its discriminator. "
        "A predicate can steer acquisition but cannot discharge the task or "
        "amend the transition law."
        if hypothesis_focus
        else _compact_science_contract_text()
    )
    work_loop = (
        "Hold the staged transition carrier fixed. Treat task-open observations "
        "as negative examples; compare surviving task predicates, choose one "
        "falsifiable rival, and return a standalone top-level "
        "`GOAL_PREDICATE(state) -> bool` module. Do not repeat or import the "
        "transition carrier; the kernel binds the predicate to its immutable "
        "carrier companion. State the role, relation, or certified invariant "
        "that makes the proposed condition an identity; coordinates, labels, "
        "and other presentation properties may locate evidence but cannot by "
        "themselves define the task. A prior-chart task edge may be proposed "
        "only as a falsifiable invariant-level transport with a target-chart "
        "discriminator, never as inherited authority. The "
        "input is the same substrate state consumed by the transition carrier, "
        "never a report, receipt, score, task-adjudicator field, or lifecycle "
        "counter. Do not add or modify transition operations. The predicate is "
        "acquisition steering; the registered task adjudicator disposes it."
        if hypothesis_focus
        else (
            "Search locally in the CEGIS loop: evidence -> quotient/roles -> "
            "executable transition law -> visible score/preflight -> repair or "
            "typed obstruction. Scratch code and local probes are part of thinking; "
            "receipts are citations, not the target. If you stop with an obstruction "
            "after consuming staged counterexamples, cite the derived scratch "
            "artifact, visible diagnostic receipt, or scored candidate that connects "
            "those refs to the obstruction. Stop only when the next visible local "
            "action is no longer worth doing in this turn; if it is cheap, executable, "
            "and informative, run it."
        )
    )
    return (
        "# Task\n\n"
        + render_ask_spec_markdown(
            spec
            or worldmodel_candidate_ask_spec(
                objective=induction_objective,
                current_refs=_worldmodel_current_refs(records),
            )
        )
        + "\n"
        "Use `ATTENTION.md` and `RECORDS.json` as evidence indexes. Treat Strategy "
        "cards as routing records, not as the law to fit. Use `CONTEXT.md` only "
        "as background.\n\n"
        f"{science_contract}\n\n"
        "## Evidence Status\n\n"
        f"- run_role: `{run_role}`\n"
        + "\n".join(evidence_lines)
        + "\n\n"
        "## Work Loop\n\n"
        f"{work_loop}\n\n"
        "## Final Answer Contract\n\n"
        f"{SCIENCE_OUTPUT_POLICY.final_contract_text()}\n"
        "All Strategy-card, workbench, tool-gap, and action-request objects belong in `control_receipts`. "
        "Never put receipts in prose, YAML, comments, docstrings, or `test_model_py`.\n\n"
        "## Interaction Rule\n\n"
        "Before final submission, use `WORKBENCH_TOOLS.md` for leaf-local checks. "
        "Run `route-action` before emitting a workbench action request. If it returns `in_turn_cli`, run the suggested "
        "visible command in this same turn. If it returns `parent_kernel`, include the action request in "
        "`control_receipts` and leave `test_model_py` empty unless you already have the required kernel receipt.\n\n"
        "Do not use Strategy-card prose or the tool menu as a substitute for "
        "candidate search. Rerunning the same gate without a changed candidate "
        "or a registered workbench action is a no-op.\n\n"
        "For executable candidates, run `check-worldmodel-carrier` locally before final submission. "
        "Run `check-receipt --kind worldmodel-payload` over the final JSON when possible.\n\n"
        "## Current Routing Record SHAs\n\n"
        f"{shas_text}\n"
    )


def _worldmodel_induction_objective() -> str:
    return (
        "Compress the staged transition evidence into the simplest transportable "
        "executable worldmodel law you can justify. Return a candidate when the "
        "visible evidence permits; otherwise return a receipt-bound "
        "LOWERABILITY_BLOCKED obstruction."
    )


def _worldmodel_task_hypothesis_objective() -> str:
    return (
        "Refine the current task-hypothesis version space while preserving the "
        "accepted transition carrier. Return a standalone "
        "`GOAL_PREDICATE(state) -> bool` module, plus a concise rival "
        "and discriminating intervention. Do not repair or extend transition laws."
    )


def _worldmodel_turn_focus() -> str:
    return str(os.environ.get("ZTARE_WORLDMODEL_TURN_FOCUS") or "").strip().lower()


def _compact_science_contract_text() -> str:
    return (
        "Candidate-first policy: propose a transportable executable law whenever "
        "visible evidence permits. Tool gaps are second-order and do not satisfy "
        "the science turn by themselves. In DISCOVERY, staged counterexamples may "
        "be used to repair alpha/gamma, but any consumed verifier slice must be "
        "labeled as evidence rather than clean transfer."
    )


def _evidence_status_lines(
    *,
    run_role: str,
    artifacts: list[dict[str, Any]],
    records: list[Any],
) -> list[str]:
    counterexample_refs = _counterexample_evidence_refs(
        artifacts=artifacts,
        records=records,
    )
    if run_role in {DISCOVERY, HARNESS_DEBUG}:
        if counterexample_refs:
            refs = ", ".join(f"`{ref}`" for ref in counterexample_refs[:8])
            return [
                "- staged counterexample refs are consumable evidence for alpha/gamma repair, not fresh verifier proof.",
                f"- counterexample_refs: {refs}",
                "- final blockers should include `evidence_statuses`: `consumed_counterexample` for inspected refs and `used_for_abduction` for refs used to form the law.",
            ]
        return [
            "- no staged counterexample refs were materialized; final blockers may state that absence.",
        ]
    return [
        "- fresh verifier refs, if present, are for gate/promotion measurement; do not inspect hidden holdout outside declared visible artifacts.",
    ]


def _worldmodel_current_refs(records: list[Any], *, limit: int = 8) -> tuple[str, ...]:
    """Return the active consumer's work objects without relabeling their type."""

    refs: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        projection = record.get("consumer_projection")
        if not isinstance(projection, dict):
            continue
        for donor in projection.get("archived_residual_donors") or []:
            if not isinstance(donor, dict):
                continue
            ref = str(donor.get("candidate_ref") or "").strip()
            sha = str(donor.get("candidate_sha256") or "").strip()
            if ref:
                refs.append(
                    f"artifact_ref:{ref}" + (f"#sha256={sha}" if sha else "")
                )
        source_ref = str(record.get("source_ref") or "").strip()
        source_sha = str(record.get("source_sha") or "").strip()
        if source_ref:
            refs.append(
                f"receipt_ref:{source_ref}"
                + (f"#sha256={source_sha}" if source_sha else "")
            )
        observation_sha = str(projection.get("observation_sha256") or "").strip()
        if observation_sha:
            refs.append(f"observation_sha256:{observation_sha}")
    if not refs:
        refs.extend(
            f"routing_record_sha256:{sha}" for sha in _strategy_failure_shas(records)
        )
    return tuple(dict.fromkeys(refs))[:limit]


def _counterexample_evidence_refs(
    *,
    artifacts: list[dict[str, Any]],
    records: list[Any],
) -> list[str]:
    visible = {
        str(row.get("ref") or row.get("source_ref") or "").strip()
        for row in artifacts
        if isinstance(row, dict) and row.get("status") == "materialized"
    }
    refs = [
        ref
        for ref in visible
        if "holdout" in ref or "episode_002" in ref or "counterexample" in ref
    ]
    for record in records:
        if not isinstance(record, dict):
            continue
        projection = record.get("consumer_projection")
        if not isinstance(projection, dict) or not (
            projection.get("observation_sha256")
            or projection.get("archived_residual_donors")
        ):
            continue
        candidates = [record.get("source_ref")]
        candidates.extend(
            donor.get("candidate_ref")
            for donor in projection.get("archived_residual_donors") or []
            if isinstance(donor, dict)
        )
        refs.extend(str(ref) for ref in candidates if str(ref or "") in visible)
    return list(dict.fromkeys(refs))


def _single_line(value: Any, *, limit: int = 480) -> str:
    text = _compact_field(value)
    return text[:limit]


def _strategy_failure_shas(records: list[Any], *, limit: int = 8) -> list[str]:
    shas: list[str] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        if _record_lane(record) == META_HARDENING_LANE:
            continue
        for key in ("failure_family_sha", "sha"):
            raw = str(record.get(key) or "").strip()
            if len(raw) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in raw):
                lowered = raw.lower()
                if lowered not in seen:
                    seen.add(lowered)
                    shas.append(lowered)
                break
        if len(shas) >= limit:
            break
    return shas


def _task_hypothesis_strategy_shas(records: list[Any]) -> list[str]:
    """Keep the focused ask bound only to task-specification residues."""

    selected = [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("kind") == "search_control_residue_repair"
    ]
    return _strategy_failure_shas(selected, limit=2)


def _attention_doc(
    *,
    briefing: str | None,
    context: str,
    records: list[Any],
    run_role: str = EVALUATION,
    artifacts: list[dict[str, Any]] | None = None,
) -> str:
    agenda = _extract_markdown_section(
        briefing or context,
        heading="## Briefing Attention Agenda",
    )
    record_lines = _record_attention_lines(records)
    evidence_lines = _attention_evidence_lines(
        run_role=run_role,
        artifacts=artifacts or [],
        records=records,
    )
    if record_lines:
        text = (
            "# Attention\n\n"
            "Sufficient-statistics front door derived from structured records. "
            "Use `RECORDS.json` for exact refs and full fields.\n\n"
            + ("\n".join(evidence_lines) + "\n\n" if evidence_lines else "")
            + "\n".join(record_lines)
            + "\n"
        )
        if agenda:
            text += (
                "\n## Background Agenda\n\n"
                "Older rendered agenda retained for context only; the ordered structured-record lines above are the working surface.\n"
            )
        return text
    if agenda:
        return (
            "# Attention\n\n"
            + ("\n".join(evidence_lines) + "\n\n" if evidence_lines else "")
            + agenda.rstrip()
            + "\n"
        )
    return (
        "# Attention\n\n"
        + ("\n".join(evidence_lines) + "\n\n" if evidence_lines else "")
        +
        "No separate structured attention agenda was present at dispatch. Use "
        "`TASK.md` as the front door, `RECORDS.json` for exact staged metadata, "
        "and `CONTEXT.md` only when the task needs background details.\n"
    )


def _attention_evidence_lines(
    *,
    run_role: str,
    artifacts: list[dict[str, Any]],
    records: list[Any],
) -> list[str]:
    lines: list[str] = []
    if run_role in {DISCOVERY, HARNESS_DEBUG}:
        refs = _counterexample_evidence_refs(artifacts=artifacts, records=records)
        if refs:
            lines.append(
                "- evidence_status: DISCOVERY counterexamples are visible learning evidence; "
                "consume them for alpha/gamma repair, not clean-transfer promotion."
            )
            lines.append("- counterexample_refs: " + ", ".join(f"`{ref}`" for ref in refs[:8]))
        else:
            lines.append("- evidence_status: DISCOVERY mode; no staged counterexample refs were materialized.")
    elif run_role == EVALUATION:
        lines.append("- evidence_status: EVALUATION mode; fresh verifier evidence is gate-owned.")
    return lines


def _records_doc(*, repo: Path, briefing: str | None, agent_id: str = "") -> dict[str, Any]:
    text = briefing or ""
    latest = _load_latest_mutator_briefing_records(repo, agent_id=agent_id)
    if latest:
        return {
            "schema": "ztare-visible-workbench-records-v1",
            "source": latest.get("source") or "mutator_briefing_records",
            "source_ref": latest.get("source_ref") or "",
            "source_sha256": latest.get("source_sha256") or "",
            "briefing_sha256": _sha_text(text),
            "structured_records": latest.get("records") or [],
            "note": (
                "Structured provider records are copied from the latest persisted "
                "mutator briefing record file. They are evidence refs, not gate authority."
            ),
        }
    return {
        "schema": "ztare-visible-workbench-records-v1",
        "source": "dispatch_model",
        "briefing_sha256": _sha_text(text),
        "structured_records": [],
        "note": (
            "Structured provider records were not passed across this dispatch "
            "boundary. Use staged artifact refs in MANIFEST.json and visible "
            "probe receipts for exact observations."
        ),
    }


def _pack_projection_receipt(
    *,
    records_payload: dict[str, Any],
    task_text: str,
    attention_text: str,
) -> dict[str, Any]:
    records = records_payload.get("structured_records") or []
    record_count = len(records) if isinstance(records, list) else 0
    task_has_contract = (
        "Return only one raw JSON object" in task_text
        or "Return exactly the typed contract requested below" in task_text
    )
    return {
        "schema": "ztare-briefing-pack-projection-receipt-v1",
        "status": "pass" if task_has_contract else "warn",
        "records_source_ref": records_payload.get("source_ref") or "",
        "records_source_sha256": records_payload.get("source_sha256") or "",
        "structured_records_count": record_count,
        "records_projected_to": ["RECORDS.json"],
        "asks_projected_to": ["ASKS.json", "TASK.md"],
        "task_contract_projected": task_has_contract,
        "attention_sha256": _sha_text(attention_text),
        "task_sha256": _sha_text(task_text),
        "attention_record_lines": attention_text.count("\n- "),
    }


def _pack_file_records(workbench: Path) -> list[dict[str, Any]]:
    authority = {
        "TASK.md": "task_contract",
        "ASKS.json": "ask_contract_index",
        "ATTENTION.md": "sufficient_statistics",
        "RECORDS.json": "structured_record_index",
        "CONTEXT.md": "background_context",
        "WORKBENCH_TOOLS.md": "visible_diagnostic_tools",
        "README.md": "navigation",
    }
    records: list[dict[str, Any]] = []
    for rel, level in authority.items():
        path = workbench / rel
        if not path.is_file():
            records.append(
                {
                    "ref": rel,
                    "status": "missing",
                    "visible_status": "missing",
                    "authority_level": level,
                }
            )
            continue
        data = path.read_bytes()
        records.append(
            {
                "ref": rel,
                "status": "materialized",
                "visible_status": "visible",
                "authority_level": level,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return records


def _load_latest_mutator_briefing_records(repo: Path, *, agent_id: str = "") -> dict[str, Any] | None:
    roots: list[Path] = []
    project_name = _project_name_from_agent_id(agent_id)
    if project_name:
        roots.append(repo / "projects" / project_name / "workspace")
    roots.append(repo / "workspace")
    projects_dir = repo / "projects"
    if not project_name and projects_dir.is_dir():
        roots.extend(child / "workspace" for child in projects_dir.iterdir() if child.is_dir())
    candidates: list[Path] = []
    for root in roots:
        try:
            candidates.extend(root.glob("mutator_briefing_iter_*_records.json"))
        except OSError:
            continue
    candidates = [p for p in candidates if p.is_file()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    try:
        data = latest.read_bytes()
        payload = json.loads(data.decode("utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return None
    try:
        source_ref = str(latest.relative_to(repo))
    except ValueError:
        source_ref = str(latest)
    return {
        "source": "mutator_briefing_records",
        "source_ref": source_ref,
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "records": [record for record in records if isinstance(record, dict)],
    }


def _record_attention_lines(records: list[Any], *, limit: int = 8) -> list[str]:
    ordered = [
        record
        for record in sorted(
            records,
            key=lambda row: _attention_priority(row) if isinstance(row, dict) else 99,
        )
        if isinstance(record, dict)
        and record.get("record_role") != "stale_meta_hardening"
    ]
    # ATTENTION.md is a route index, not a leaderboard of individual rows.
    # Preserve one record from every active producer before allowing a prolific
    # producer to occupy the remaining slots.  The complete rows remain in
    # RECORDS.json; this projection only protects producer-category coverage.
    producer_heads: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    seen_producers: set[str] = set()
    for record in ordered:
        producer = str(
            record.get("provider")
            or record.get("source_type")
            or record.get("type")
            or "unknown"
        )
        if producer in seen_producers:
            deferred.append(record)
            continue
        seen_producers.add(producer)
        producer_heads.append(record)
    # Producer coverage and control priority are independent constraints. Keep
    # the best row for every producer, order those representatives by control
    # priority, then append duplicate rows in their original priority order.
    # This prevents a prolific producer from hiding a category without making
    # a lower-priority category precede an active frontier.
    selected = sorted(producer_heads, key=_attention_priority)
    selected.extend(deferred)

    lines: list[str] = []
    for record in selected:
        provider = _compact_field(record.get("provider") or "unknown")
        record_role = _compact_field(record.get("record_role") or "")
        source_type = _compact_field(
            record_role
            or record.get("source_type")
            or record.get("type")
            or record.get("kind")
            or "record"
        )
        source_ref = _compact_field(record.get("source_ref") or record.get("submission") or record.get("path") or "")
        summary = _record_attention_summary(record)
        action = _compact_field(record.get("action") or record.get("next_action") or record.get("recommendation") or "")
        bits = [f"provider={provider}", f"type={source_type}"]
        kind = _compact_field(record.get("kind") or "")
        if kind and kind != source_type:
            bits.append(f"kind={kind}")
        if source_ref:
            bits.append(f"source={source_ref}")
        if action:
            bits.append(f"action={action[:160]}")
        if summary:
            # A producer may declare the smallest typed object its consumer
            # needs.  Preserve that object as a unit instead of truncating it
            # into a provenance-only summary.  Its vocabulary remains opaque
            # to this substrate-neutral projection owner.
            summary_limit = 1200 if isinstance(record.get("consumer_projection"), dict) else 260
            bits.append(summary[:summary_limit])
        lines.append("- " + "; ".join(bits))
        if len(lines) >= limit:
            break
    return lines


def _record_attention_summary(record: dict[str, Any]) -> str:
    """Put a consumer-ready identity before verbose diagnostic coordinates."""
    consumer_projection = record.get("consumer_projection")
    if isinstance(consumer_projection, dict) and consumer_projection:
        projection = _compact_field(consumer_projection)
        summary = _compact_field(record.get("summary") or "")
        return (
            f"consumer_projection={projection}; {summary}"
            if summary
            else f"consumer_projection={projection}"
        )
    summary = _compact_field(
        record.get("summary")
        or record.get("title")
        or record.get("weakest_point")
        or record.get("falsifiable_prediction")
        or record.get("contract_rejection_reason")
        or record.get("required_next_gate")
        or ""
    )
    fiber = record.get("behavioral_fiber")
    if not isinstance(fiber, dict) or int(fiber.get("member_count") or 0) < 2:
        return summary
    operation_classes = sorted(
        {
            str(family.get("operation", {}).get("op") or "")
            for family in fiber.get("operation_families") or []
            if isinstance(family, dict)
            and isinstance(family.get("operation"), dict)
            and str(family.get("operation", {}).get("op") or "")
        }
    )
    identity = _compact_field(
        "behavioral_fiber "
        f"members={fiber.get('member_rows') or []}; "
        f"interventions={fiber.get('interventions') or []}; "
        f"relation={fiber.get('observed_relation') or ''}/"
        f"{fiber.get('intervention_relation') or ''}; "
        f"source_ops={operation_classes}; "
        f"unresolved_source_relations={fiber.get('unresolved_source_relation_rows') or []}; "
        "promotion_authorized="
        f"{bool(fiber.get('carrier_promotion_authorized'))}; "
        "shared_consequence="
        f"{str(fiber.get('shared_observed_consequence_sha256') or '')[:16]}"
    )
    return f"{identity}; {summary}" if summary else identity


def _attention_priority(record: dict[str, Any]) -> int:
    provider = str(record.get("provider") or "")
    source_type = str(record.get("source_type") or record.get("type") or "")
    # ponytail: live_champion is Tier-0; it must appear in ATTENTION.md before
    # surviving_candidates floods the 8-record limit (observed: 8 near-miss rows
    # displaced the champion mandate entirely from the front-door file).
    if provider == "live_champion" or source_type == "live_champion_receipt":
        return 1
    if isinstance(record.get("consumer_projection"), dict):
        # A first-fired task output changes the consumer's initial state.  It
        # must win over the instruction that caused it and over provenance-only
        # records from the same producer.
        return -1
    if isinstance(record.get("behavioral_fiber"), dict):
        # A materialized observation is the active task's consumed output.  If
        # the task row wins the one-row-per-producer projection instead, the
        # worker sees an instruction to inspect while the inspection result is
        # stranded later in RECORDS.json.
        return -1
    if record.get("record_role") == "diagnostic_rejected_witness":
        # A contract-rejected carrier is a historical counterexample.  It may
        # inform a discriminator, but it cannot displace the active admissible
        # frontier at the prompt front door.
        return 4
    if record.get("record_role") == "stale_meta_hardening":
        return 9
    if provider == "strategy_experiments" or source_type == "strategy_experiment":
        if _record_lane(record) != "skill_acquisition":
            return 5
        return 0
    if provider in {"leaf_workbench", "surviving_candidates", "worldmodel_committee"}:
        return 2
    if provider == "operator_proposals":
        return 3
    if provider == "leanmill_proof_jobs":
        return 4
    return 3


def _record_lane(record: dict[str, Any]) -> str:
    if isinstance(record.get("lane"), str) and record["lane"].strip():
        return record["lane"].strip()
    card_like = {
        "kind": record.get("kind"),
        "action_plan": {
            "required_next_gate": record.get("required_next_gate") or record.get("next_gate"),
            "mutable_surface": record.get("mutable_surface"),
            "target_artifact": record.get("target_artifact"),
        },
    }
    return strategy_card_lane(card_like)


def _compact_field(value: Any) -> str:
    if isinstance(value, (dict, list)):
        try:
            value = json.dumps(value, sort_keys=True, default=str)
        except TypeError:
            value = str(value)
    return " ".join(str(value or "").split())


def _extract_markdown_section(text: str, *, heading: str) -> str:
    body = str(text or "")
    start = body.find(heading)
    if start < 0:
        return ""
    next_heading = re.search(r"\n##\s+", body[start + len(heading) :])
    if not next_heading:
        return body[start:]
    end = start + len(heading) + next_heading.start()
    return body[start:end]


def _tools_doc(*, run_role: str = EVALUATION, is_worldmodel: bool = False) -> str:
    visibility_line = (
        "These commands read staged visible files or stdin. In DISCOVERY, staged "
        "holdout/counterexample files are consumable evidence for alpha/gamma repair; "
        "in EVALUATION they remain absent unless explicitly staged. These tools do "
        "not grant promotion gates or live environment authority."
        if run_role in {DISCOVERY, HARNESS_DEBUG}
        else (
            "These commands read only staged visible files or stdin. They do not "
            "expose hidden holdout, promotion gates, or live environment authority."
        )
    )
    # ponytail: episode-analysis tools are worldmodel-only; gate on is_worldmodel so
    # prose/numeric substrates in DISCOVERY don't see arc-specific tool names.
    probe_tools_block = ""
    if is_worldmodel and run_role in {DISCOVERY, HARNESS_DEBUG}:
        probe_tools_block = (
            "Episode-analysis tools (run via `run-action` with a "
            "`LEAF_WORKBENCH_ACTION_REQUEST`; these are the intended path for "
            "analyzing the large raw episode jsonl files):\n\n"
            "- `inspect_worldmodel_event_timeline`: group cell-change events across "
            "time for an episode.\n"
            "- `contrast_worldmodel_episodes`: compare two episodes' states.\n"
            "- `run_worldmodel_evidence_probe`: author an arbitrary read-only "
            "`probe(episodes) -> dict` analysis over the raw transitions.\n\n"
            "Leaf-authored scratch analysis code over the raw jsonl is explicitly "
            "allowed: write and run your own scratch scripts in this staged cwd to "
            "study the episodes before authoring a candidate.\n\n"
        )
    return (
        "# Visible Workbench Tools\n\n"
        f"{visibility_line}\n\n"
        f"{probe_tools_block}"
        "Use this as the leaf-local loop: route an action, run in-turn diagnostics "
        "when the route is `in_turn_cli`, preflight receipts/carriers, then return "
        "the final typed contract. Only `parent_kernel` routes should be submitted "
        "as `LEAF_WORKBENCH_ACTION_REQUEST`. If the route is `capability_proposal`, "
        "treat it as a tool-gap observation in science mode; submit an executable "
        "candidate or `LOWERABILITY_BLOCKED`, not a direct tool proposal; "
        "do not submit it as an action request. If the route is "
        "`invalid_action_request`, repair the request shape or submit a candidate; "
        "do not submit the invalid request as final output. Combining visible "
        "receipt facts is leaf-local candidate reasoning, not a parent-kernel "
        "action; candidate truth is still decided by replay/holdout gates.\n\n"
        f"{SCIENCE_OUTPUT_POLICY.local_stopping_text()}\n\n"
        "List commands:\n\n"
        "```sh\n"
        "PYTHONPATH=src python3 -m ztare.common.visible_workbench_cli manifest\n"
        "```\n\n"
        + _visible_workbench_command_doc()
    )


def _visible_workbench_command_doc() -> str:
    from ztare.common.visible_workbench_cli import manifest_payload

    payload = manifest_payload()
    lines = [
        "Available commands are generated from the CLI manifest; run `manifest` for full input details.\n"
    ]
    persistent_receipts = str(payload.get("persistent_receipts") or "").strip()
    if persistent_receipts:
        lines.append(persistent_receipts + "\n")
    for row in payload.get("commands") or []:
        if not isinstance(row, dict):
            continue
        command = str(row.get("command") or "").strip()
        if not command:
            continue
        lines.append(
            f"- `{command}`: authority={row.get('authority')}; "
            f"secret_policy={row.get('secret_policy')}; output={row.get('output')}"
        )
    routes = payload.get("capability_routes") if isinstance(payload.get("capability_routes"), dict) else {}
    if routes:
        lines.append(
            "\nAdvanced registered actions are available through `manifest`, "
            "`route-action`, and `run-action`. They are affordances for hypotheses "
            "you choose, not a menu that must be exhausted. Parameterized actions "
            "expose their executable `parameter_domains` in the manifest; a "
            "verification-only value outside that domain remains candidate-bound.\n"
        )
    lines.append(
        "\nCanonical loop: write and probe a candidate locally; use `route-action` only "
        "when you already intend to emit a workbench action request or run a named "
        "advanced action. Execute only routes marked `in_turn_cli` with `run-action` "
        "or the command named in the manifest; submit `parent_kernel` routes as typed "
        "action requests only after `route-action` validates their parameters; repair "
        "`invalid_action_request` before final output. "
        "`capability_proposal` routes are cold meta-work and should be reported through "
        "`LOWERABILITY_BLOCKED` in science mode.\n"
    )
    return "\n".join(lines)


_VISIBLE_STAGE_DENY_FILENAMES = {
    ".env",
    "evidence_holdout.txt",
    "episode_002.jsonl",
    "sealed_holdout.json",
    "ground_truth.json",
}

_VISIBLE_ARTIFACT_EXT_RE = re.compile(
    r"^(.*?\.(?:csv|json|jsonl|lean|md|py|toml|tsv|txt|ya?ml))(?:[:#].*)?$"
)


def _materialize_structured_visible_artifacts(
    *,
    repo: Path,
    workbench: Path,
    agent_id: str,
    records: list[Any],
    run_role: str = EVALUATION,
) -> list[dict[str, Any]]:
    refs = sorted(set(_structured_visible_artifact_refs(records)))
    seen_refs = set(refs)
    artifacts: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(refs):
        ref = refs[cursor]
        cursor += 1
        record: dict[str, Any] = {
            "ref": ref,
            "authority_level": "visible_context_artifact",
        }
        if not _visible_artifact_ref_allowed(ref, run_role=run_role):
            record["status"] = "withheld"
            record["visible_status"] = "hidden_or_disallowed"
            record["reason"] = "path_not_visible"
            artifacts.append(record)
            continue
        resolved = _resolve_visible_artifact(repo=repo, ref=ref, agent_id=agent_id)
        if resolved is None:
            record["status"] = "missing"
            record["visible_status"] = "missing"
            artifacts.append(record)
            continue
        if isinstance(resolved, list):
            record["status"] = "ambiguous"
            record["visible_status"] = "withheld"
            record["candidates"] = [str(path.relative_to(repo)) for path in resolved[:8]]
            artifacts.append(record)
            continue
        try:
            size = resolved.stat().st_size
        except OSError:
            record["status"] = "unreadable"
            record["visible_status"] = "withheld"
            artifacts.append(record)
            continue
        max_bytes = _visible_artifact_byte_cap(ref)
        if size > max_bytes:
            record["status"] = "withheld"
            record["visible_status"] = "withheld"
            record["reason"] = "too_large"
            record["bytes"] = size
            record["max_bytes"] = max_bytes
            artifacts.append(record)
            continue
        target = workbench / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        link_mode = "copy"
        if size >= _HARDLINK_SIZE_THRESHOLD_BYTES:
            try:
                os.link(resolved, target)
                link_mode = "hardlink"
            except OSError:
                pass  # cross-device or permissions — fall through to copy
        if link_mode == "copy":
            try:
                shutil.copy2(resolved, target)
            except OSError:
                record["status"] = "unreadable"
                record["visible_status"] = "withheld"
                artifacts.append(record)
                continue
        # ponytail: skip SHA on large hardlinked files (no data read needed);
        # small files already read, but here we use copy2 so we compute SHA from source.
        artifact_record: dict[str, Any] = {
            "status": "materialized",
            "visible_status": "visible",
            "source_ref": str(resolved.relative_to(repo)),
            "bytes": size,
            "link_mode": link_mode,
        }
        if size < _HARDLINK_SIZE_THRESHOLD_BYTES:
            try:
                artifact_record["sha256"] = hashlib.sha256(resolved.read_bytes()).hexdigest()
            except OSError:
                pass
        record.update(artifact_record)
        artifacts.append(record)
        # Receipt envelopes are evidence graphs.  Stage their visible local
        # dependencies to a fixed point so a typed ref does not become dead
        # text at the sandbox boundary.  The ordinary visibility and byte
        # gates above still govern every discovered child.
        if resolved.suffix == ".json" and size <= max_bytes:
            try:
                nested_payload = json.loads(resolved.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                nested_payload = None
            if isinstance(nested_payload, (dict, list)):
                for nested_ref in sorted(
                    set(_iter_structured_visible_artifact_refs(nested_payload))
                ):
                    if nested_ref not in seen_refs:
                        refs.append(nested_ref)
                        seen_refs.add(nested_ref)
    return artifacts


def _structured_visible_artifact_refs(records: list[Any]) -> list[str]:
    refs: list[str] = list(_COMPACT_VISIBLE_WORKBENCH_REFS)
    for record in records:
        if not isinstance(record, dict):
            continue
        refs.extend(_iter_structured_visible_artifact_refs(record))
    return refs


def _iter_structured_visible_artifact_refs(value: Any, *, key: str = "") -> list[str]:
    refs: list[str] = []
    if key == "output_summary" and isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, (dict, list)):
            return _iter_structured_visible_artifact_refs(decoded)
    if isinstance(value, dict):
        for child_key, child in value.items():
            refs.extend(_iter_structured_visible_artifact_refs(child, key=str(child_key)))
        return refs
    if isinstance(value, list):
        if key in _VISIBLE_ARTIFACT_REF_LIST_KEYS:
            for child in value:
                ref = _canonical_visible_artifact_ref(str(child or ""))
                if ref:
                    refs.append(ref)
            return refs
        for child in value:
            refs.extend(_iter_structured_visible_artifact_refs(child, key=key))
        return refs
    if key in _VISIBLE_ARTIFACT_REF_KEYS or key.endswith(_VISIBLE_ARTIFACT_REF_KEY_SUFFIXES):
        ref = _canonical_visible_artifact_ref(str(value or ""))
        if ref and (
            _visible_artifact_ref_allowed(ref)
            or Path(ref).name in {"evidence_holdout.txt", "episode_002.jsonl"}
        ):
            refs.append(ref)
    return refs


def _canonical_visible_artifact_ref(raw: str) -> str:
    ref = (raw or "").strip().strip(".:,;")
    if not ref:
        return ""
    if "#" in ref:
        ref = ref.split("#", 1)[0].rstrip(".:,;")
    match = _VISIBLE_ARTIFACT_EXT_RE.match(ref)
    if match:
        ref = match.group(1)
    return ref.strip().strip(".:,;")


def _visible_workbench_max_artifact_bytes() -> int:
    raw = os.environ.get("ZTARE_AGENT_VISIBLE_WORKBENCH_MAX_ARTIFACT_BYTES", "2000000")
    try:
        parsed = int(raw)
    except ValueError:
        return 2_000_000
    return max(1, parsed)


def _visible_workbench_max_large_artifact_bytes() -> int:
    raw = os.environ.get("ZTARE_AGENT_VISIBLE_WORKBENCH_MAX_LARGE_ARTIFACT_BYTES", "268435456")
    try:
        parsed = int(raw)
    except ValueError:
        return 268_435_456
    return max(1, parsed)


def _visible_artifact_byte_cap(ref: str) -> int:
    path = Path(ref)
    if path.parts and path.parts[0] in {"raw", "evidence"} and path.suffix == ".jsonl":
        return _visible_workbench_max_large_artifact_bytes()
    return _visible_workbench_max_artifact_bytes()


def _visible_artifact_ref_allowed(ref: str, *, run_role: str = EVALUATION) -> bool:
    path = Path(ref)
    if path.is_absolute() or ".." in path.parts:
        return False
    if any(part.startswith(".") for part in path.parts):
        return False
    if path.name in _VISIBLE_STAGE_DENY_FILENAMES:
        return False
    # ponytail: eval_slices/ is a sealed holdout dir — never stage into packs
    if "eval_slices" in path.parts:
        return False
    return True


def _resolve_visible_artifact(
    *,
    repo: Path,
    ref: str,
    agent_id: str,
) -> Path | list[Path] | None:
    project_name = _project_name_from_agent_id(agent_id)
    if project_name:
        project_path = repo / "projects" / project_name / ref
        if project_path.is_file():
            return project_path
    if ref.startswith("workspace/"):
        projects_dir = repo / "projects"
        if projects_dir.is_dir():
            hits = [
                child / ref
                for child in projects_dir.iterdir()
                if child.is_dir() and (child / ref).is_file()
            ]
            if len(hits) == 1:
                return hits[0]
            if len(hits) > 1:
                return hits
    direct = repo / ref
    if direct.is_file():
        return direct
    return None


def _project_name_from_agent_id(agent_id: str) -> str:
    marker = "autoresearch_mutator_"
    if agent_id.startswith(marker):
        return agent_id[len(marker) :]
    return ""


def _materialize_tool_sources(*, workbench: Path, sources: tuple[ToolSource, ...]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source_spec in sources:
        record: dict[str, Any] = {
            "ref": source_spec.ref,
            "source_type": "visible_workbench_tool",
            "authority_level": source_spec.authority_level,
            "visible_status": "visible_tool_source",
        }
        if not source_spec.source.is_file():
            record["status"] = "missing"
            record["visible_status"] = "missing"
            records.append(record)
            continue
        data = source_spec.source.read_bytes()
        target = workbench / source_spec.ref
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        record.update(
            {
                "status": "materialized",
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
        records.append(record)
    return records
