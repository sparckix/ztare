"""Configured System-1 candidate producers for interactive substrates.

The play loop sees only typed candidate proposals.  Substrate profiles choose
which registered producer runs and provide input artifact refs; producer
results pass through the project gate harness and candidate pool unchanged.
No producer may edit the champion or candidate prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pprint
import sys
from typing import Any, Callable


@dataclass(frozen=True)
class DeterministicCandidateProposal:
    producer_id: str
    candidate_path: Path
    candidate_sha256: str
    input_sha256s: dict[str, str]


@dataclass(frozen=True)
class GatedDeterministicCandidate:
    proposal: DeterministicCandidateProposal
    gate_payload: dict[str, Any]
    gate_pass: bool


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append_receipt(project: Path, row: dict[str, Any]) -> None:
    from ztare.common.schema_routes import append_schema_route_event, assert_schema_route

    route = assert_schema_route(
        str(row.get("schema") or ""), category="operational_carrier"
    )
    append_schema_route_event(
        project,
        schema_id=route.schema_id,
        event=str(row.get("event") or ""),
        join_values={field: row.get(field) for field in route.join_fields},
        payload={
            key: value
            for key, value in row.items()
            if key not in {"schema", "event", *route.join_fields}
        },
    )


def _counterexample_layer_retraction(
    project: Path,
    *,
    task_source: Path,
    operation_sha256: str,
    inspection: dict[str, Any],
    declaration: dict[str, Any],
) -> DeterministicCandidateProposal | None:
    """Retract one provenance-bound layer that worsens the counterexample.

    This is the negative dual of adding a catalog operation.  It is available
    only when the literal composition identifies exactly one layer whose
    application increases disagreement with the observed consequence.  The
    ordinary project gate remains the only adoption authority.
    """

    observation = inspection.get("counterexample_observation")
    if not isinstance(observation, dict):
        return None
    observation_ref = str(observation.get("observation_ref") or "")
    marker = "#transition:"
    if marker not in observation_ref:
        return None
    episode_ref, row_text = observation_ref.rsplit(marker, 1)
    try:
        row_index = int(row_text)
    except ValueError:
        return None
    task_sha = _sha_file(task_source)
    proposal_identity = observation.get("proposal_identity")
    if (
        not isinstance(proposal_identity, dict)
        or str(proposal_identity.get("carrier_sha") or "") != task_sha
    ):
        return None

    from ztare.worldmodel.carrier_loader import load_carrier_path
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import as_predictor
    from ztare.worldmodel.patch_base_carrier import (
        literal_patch_prefix_layers,
        materialize_immutable_patch_base,
        render_literal_patch_layers,
        rewrite_patch_base_source,
    )
    from ztare.worldmodel.spec_catalog import lower_patch_delta_spec

    episode = (project / episode_ref).resolve()
    if project != episode and project not in episode.parents:
        return None
    log = EpisodeLog.read_jsonl(episode)
    transitions = log.transitions()
    if not (0 <= row_index < len(transitions)):
        return None
    transition = transitions[row_index]
    base_path, layers = literal_patch_prefix_layers(
        task_source,
        project_dir=project,
    )
    base_program, _kind, _sha = load_carrier_path(
        base_path,
        project_dir=project,
        attach_projection=False,
    )
    current = as_predictor(base_program)(
        transition.s,
        transition.a,
        transition.t,
    )
    if current is None:
        return None

    def wrong_cells(candidate: Any) -> int:
        try:
            return sum(
                candidate[row][col] != transition.s_next[row][col]
                for row in range(len(transition.s_next))
                for col in range(len(transition.s_next[row]))
            )
        except (IndexError, TypeError):
            return 10**12

    harmful_indices: list[int] = []
    for index, layer in enumerate(layers):
        spec = layer.get("spec")
        delta, error = lower_patch_delta_spec(spec)
        if delta is None or error:
            return None
        before_wrong = wrong_cells(current)
        successor = delta(current, transition.s, transition.a, transition.t)
        if successor is None:
            return None
        provenance = layer.get("provenance")
        if (
            isinstance(provenance, dict)
            and provenance.get("operation_identity_sha256") == operation_sha256
            and successor != current
            and wrong_cells(successor) > before_wrong
        ):
            harmful_indices.append(index)
        current = successor
    retracted_base_path = base_path
    removed: dict[str, Any]
    if len(harmful_indices) == 1:
        removed_index = harmful_indices[0]
        kept_layers = tuple(
            layer for index, layer in enumerate(layers) if index != removed_index
        )
        removed = dict(layers[removed_index])
    elif not harmful_indices:
        # Migration path for a legacy untyped layer immediately beneath the
        # typed prefix.  Its parent and child are both executable carriers, so
        # the counterexample can identify the unique harmful composition edge
        # without interpreting the layer's source vocabulary.
        from ztare.common.patch_base_identity import (
            patch_base_fields_from_source,
            resolve_patch_base_ref,
            verify_patch_base_digest,
        )
        from ztare.worldmodel.patch_base_carrier import carrier_provenance_from_source

        base_source = base_path.read_text(encoding="utf-8")
        base_fields = patch_base_fields_from_source(base_source)
        if base_fields is None:
            return None
        legacy_path = resolve_patch_base_ref(project, base_fields[0])
        verify_patch_base_digest(legacy_path, base_fields[1])
        legacy_source = legacy_path.read_text(encoding="utf-8")
        legacy_provenance = carrier_provenance_from_source(legacy_source)
        legacy_operation = str(
            legacy_provenance.get("operation_identity_sha256") or ""
        )
        if legacy_operation and legacy_operation != operation_sha256:
            return None
        parent_fields = patch_base_fields_from_source(legacy_source)
        if parent_fields is None:
            return None
        parent_path = resolve_patch_base_ref(project, parent_fields[0])
        parent_sha = verify_patch_base_digest(parent_path, parent_fields[1])
        parent_program, _parent_kind, _parent_loaded_sha = load_carrier_path(
            parent_path,
            project_dir=project,
            attach_projection=False,
        )
        legacy_program, _legacy_kind, _legacy_loaded_sha = load_carrier_path(
            legacy_path,
            project_dir=project,
            attach_projection=False,
        )
        parent_output = as_predictor(parent_program)(
            transition.s, transition.a, transition.t
        )
        legacy_output = as_predictor(legacy_program)(
            transition.s, transition.a, transition.t
        )
        if (
            parent_output is None
            or legacy_output is None
            or wrong_cells(legacy_output) <= wrong_cells(parent_output)
        ):
            return None
        rebased_source = rewrite_patch_base_source(
            base_source,
            source_ref=str(parent_path.relative_to(project)),
            source_sha256=parent_sha,
        )
        rebased_ref, _rebased_sha = materialize_immutable_patch_base(
            project,
            rebased_source,
            prefix="retracted_base",
        )
        retracted_base_path = project / rebased_ref
        kept_layers = layers
        removed = {
            "source_ref": str(legacy_path.relative_to(project)),
            "source_sha256": _sha_file(legacy_path),
            "provenance": legacy_provenance,
        }
    else:
        return None

    if not kept_layers:
        return None
    source = render_literal_patch_layers(
        base_path=retracted_base_path,
        layers=kept_layers,
        project_dir=project,
    )
    source = (
        "CARRIER_RETRACTION = "
        + pprint.pformat(
            {
                "operation_identity_sha256": operation_sha256,
                "retracted_source_ref": removed.get("source_ref"),
                "retracted_source_sha256": removed.get("source_sha256"),
                "counterexample_ref": observation_ref,
            },
            sort_dicts=True,
            width=100,
        )
        + "\n"
        + source
    )
    candidate_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    output = (
        project
        / "workspace"
        / "submissions"
        / f"compiled_retraction_{candidate_sha[:16]}.py"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and _sha_file(output) != candidate_sha:
        raise ValueError("content-addressed layer-retraction path collision")
    if not output.exists():
        temporary = output.with_suffix(".tmp")
        temporary.write_text(source, encoding="utf-8")
        temporary.replace(output)
    return DeterministicCandidateProposal(
        producer_id=str(
            declaration.get("producer_id")
            or "worldmodel_catalog_operation_patch_compiler.v1"
        ),
        candidate_path=output,
        candidate_sha256=candidate_sha,
        input_sha256s={
            str(task_source.relative_to(project)): task_sha,
            str(episode.relative_to(project)): _sha_file(episode),
            str(Path(__file__).resolve()): _sha_file(Path(__file__).resolve()),
        },
    )
def _catalog_operation_patch_compiler(
    project: Path,
    declaration: dict[str, Any],
) -> DeterministicCandidateProposal | None:
    """Compile a task-bound registered operation without another model call.

    The counterexample workbench owns adapter vocabulary and emits a literal
    lowering.  This producer only preserves the current carrier identity and
    applies that lowering through the already-registered catalog compiler.  A
    diagnostic receipt still has no promotion authority: the unchanged project
    gates decide whether the compiled conjecture survives.
    """

    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_capability_scope,
        active_workbench_task_receipt_family,
    )
    from ztare.worldmodel.patch_base_carrier import (
        compact_literal_patch_prefix,
        materialize_immutable_patch_base,
    )
    from ztare.worldmodel.spec_catalog import validate_patch_delta_spec

    task_scope, task = active_workbench_task_capability_scope(
        project,
        adapter_id="worldmodel",
    )
    task_id = str(task.get("task_id") or "")
    if not task_scope or not task_id:
        return None

    receipt_family = active_workbench_task_receipt_family(
        project,
        adapter_id="worldmodel",
        materialize=True,
    )
    inspection_receipt = receipt_family.get(
        "inspect_worldmodel_counterexample_context"
    )
    selector_receipt = receipt_family.get("mine_worldmodel_lowerable_selectors")
    if not isinstance(inspection_receipt, dict) or not isinstance(
        selector_receipt, dict
    ):
        return None

    def receipt_summary(receipt: dict[str, Any]) -> dict[str, Any] | None:
        summary: Any = receipt.get("output_summary")
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except json.JSONDecodeError:
                return None
        return summary if isinstance(summary, dict) else None

    inspection = receipt_summary(inspection_receipt)
    selector = receipt_summary(selector_receipt)
    if inspection is None or selector is None:
        return None
    candidates = inspection.get("catalog_residual_event_candidates")
    operation_sha = str(selector.get("operation_identity_sha256") or "")
    compiled_lowering = selector.get("candidate_lowering")
    event = next(
        (
            candidate
            for candidate in (candidates if isinstance(candidates, list) else ())
            if isinstance(candidate, dict)
            and str(candidate.get("operation_identity_sha256") or "")
            == operation_sha
        ),
        None,
    )
    identity = selector.get("operation_identity")
    if not isinstance(identity, dict) and event is not None:
        identity = event.get("operation_identity")
    event_lowering = event.get("lowering") if event is not None else None
    if event_lowering is None and isinstance(compiled_lowering, dict):
        event_lowering = compiled_lowering
    if not isinstance(identity, dict) or not isinstance(event_lowering, dict):
        return None
    computed_operation_sha = hashlib.sha256(
        json.dumps(
            identity,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    if not operation_sha or operation_sha != computed_operation_sha:
        raise ValueError("catalog operation identity digest does not match")
    if (
        selector.get("schema") != "ztare-worldmodel-operation-domain-selector-v1"
        or str(selector.get("task_id") or "") != task_id
        or str(selector.get("task_source_sha256") or "")
        != str(task.get("source_sha256") or "")
        or str(selector.get("operation_identity_sha256") or "") != operation_sha
    ):
        return None

    from ztare.common.artifact_refs import resolve_project_artifact_ref

    task_source_ref = str(task.get("source_ref") or "").strip()
    task_source = resolve_project_artifact_ref(project, task_source_ref)
    if task_source is None or not task_source.is_file():
        return None
    retraction = _counterexample_layer_retraction(
        project,
        task_source=task_source,
        operation_sha256=operation_sha,
        inspection=inspection,
        declaration=declaration,
    )
    if retraction is not None:
        return retraction
    if selector.get("candidate_delta_admissible") is not True:
        return None
    if isinstance(compiled_lowering, dict):
        lowering = dict(compiled_lowering)
    else:
        operation_guard = selector.get("operation_guard")
        guard_lowering = (
            operation_guard.get("lowering")
            if isinstance(operation_guard, dict)
            else None
        )
        if not isinstance(guard_lowering, dict):
            return None
        lowering = dict(event_lowering)
        for key, value in guard_lowering.items():
            if key in lowering and lowering[key] != value:
                raise ValueError("operation-domain guard conflicts with event lowering")
            lowering[key] = value
    lowering_kind = str(
        (event.get("lowering_kind") if event is not None else None)
        or event_lowering.get("op")
        or ""
    )
    if lowering_kind != str(lowering.get("op") or ""):
        raise ValueError("catalog operation changed lowering family")

    # A lowering is an adapter presentation of the carried operation.  Trace
    # coordinates are evidence locators, not lawful selector fields.
    forbidden_properties = {"action", "intervention", "row", "t", "frame"}
    leaked = forbidden_properties & set(lowering)
    if leaked:
        raise ValueError(
            "catalog operation lowering contains diagnostic properties: "
            + ",".join(sorted(leaked))
        )
    patch_spec = {"actions": {}, "always": [dict(lowering)]}
    error = validate_patch_delta_spec(patch_spec)
    if error:
        raise ValueError(f"catalog operation receipt is not lowerable: {error}")

    # Compose over the carrier named by the active task, never over the mutable
    # project root.  The task-scope door already verifies that this source's
    # digest equals the active frontier identity; selecting test_model.py here
    # would silently drop intervening PATCH_BASE layers.
    current_source = task_source.read_text(encoding="utf-8")
    replacement_base = selector.get("replacement_base")
    if isinstance(replacement_base, dict):
        from ztare.common.patch_base_identity import (
            patch_base_fields_from_source,
            resolve_patch_base_ref,
            verify_patch_base_digest,
        )

        if (
            replacement_base.get("operation_identity_sha256") != operation_sha
            or replacement_base.get("replaces_source_sha256")
            != _sha_file(task_source)
        ):
            raise ValueError("same-operation replacement changed carrier identity")
        parent_fields = patch_base_fields_from_source(current_source)
        declared = (
            str(replacement_base.get("source_ref") or ""),
            replacement_base.get("sha256"),
        )
        if parent_fields != declared:
            raise ValueError("same-operation replacement is not the task parent")
        parent_path = resolve_patch_base_ref(project, declared[0])
        base_sha = verify_patch_base_digest(parent_path, declared[1])
        base_ref = declared[0]
    else:
        compacted_source = compact_literal_patch_prefix(
            task_source,
            project_dir=project,
        )
        base_ref, base_sha = materialize_immutable_patch_base(
            project,
            compacted_source or current_source,
            prefix=(
                "compacted_frontier" if compacted_source else "governed_frontier"
            ),
        )
    receipt_refs: list[str] = []
    for family_receipt in (inspection_receipt, selector_receipt):
        receipt_hashes = family_receipt.get("input_hashes")
        receipt_hashes = receipt_hashes if isinstance(receipt_hashes, dict) else {}
        receipt_ref = str(receipt_hashes.get("kernel_receipt_ref") or "")
        if receipt_ref and receipt_ref not in receipt_refs:
            receipt_refs.append(receipt_ref)
    source = (
        f"# TaskIdentity: {task_id}\n"
        f"# OperationIdentity: {operation_sha}\n"
        f"# ReceiptRefs: {','.join(receipt_refs)}\n"
        "CARRIER_PROVENANCE = "
        + pprint.pformat(
            {
                "task_id": task_id,
                "operation_identity_sha256": operation_sha,
                "receipt_refs": receipt_refs,
            },
            sort_dicts=True,
            width=100,
        )
        + "\n\n"
        "PATCH_BASE = "
        + pprint.pformat(
            {"source_ref": base_ref, "sha256": base_sha},
            sort_dicts=True,
            width=100,
        )
        + "\n\nPATCH_DELTA_SPEC = "
        + pprint.pformat(patch_spec, sort_dicts=True, width=100)
        + "\n"
    )
    candidate_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    output = project / "workspace" / "submissions" / f"compiled_op_{candidate_sha[:16]}.py"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and _sha_file(output) != candidate_sha:
        raise ValueError("content-addressed catalog-operation path collision")
    if not output.exists():
        temporary = output.with_suffix(".tmp")
        temporary.write_text(source, encoding="utf-8")
        temporary.replace(output)

    input_sha256s = {
        base_ref: base_sha,
        task_source_ref: _sha_file(task_source),
        str(Path(__file__).resolve()): _sha_file(Path(__file__).resolve()),
    }
    for receipt_ref in receipt_refs:
        receipt_path = project / receipt_ref
        if receipt_path.is_file():
            input_sha256s[receipt_ref] = _sha_file(receipt_path)
    weakness = project / "workspace" / "latest_harness_weakness.json"
    if weakness.is_file():
        input_sha256s["workspace/latest_harness_weakness.json"] = _sha_file(weakness)
    return DeterministicCandidateProposal(
        producer_id=str(
            declaration.get("producer_id")
            or "worldmodel_catalog_operation_patch_compiler.v1"
        ),
        candidate_path=output,
        candidate_sha256=candidate_sha,
        input_sha256s=input_sha256s,
    )


CandidateProducer = Callable[
    [Path, dict[str, Any]], DeterministicCandidateProposal | None
]


def _residual_pattern_delta_compiler(
    project: Path,
    declaration: dict[str, Any],
) -> "DeterministicCandidateProposal | None":
    """RESIDUAL-SCOPED restoration-law compiler (the scale-lawful route).

    Full-bank re-abduction cannot carry the pattern_write family at scale
    (measured 2026-07-20: 43-min budget_exit on 16,506 rows, pipeline cut
    before the conditional-always door, six identical retries). This producer
    obeys the residual scaling law instead: mine guarded pattern_write rules
    from ONLY the incumbent's wrong rows (the content-addressed row bitmap),
    learn the firing guard on the full bank via the same effect-split used by
    abduction, and compose a PATCH_BASE + PATCH_DELTA_SPEC candidate over the
    incumbent. No adoption authority: the project gate harness and the
    row-dominance promotion door decide, exactly as for every other producer.
    Kill-switch: ZTARE_PATTERN_WRITE=0 disables (same flag as the miner).
    """
    import os as _os

    if _os.environ.get("ZTARE_PATTERN_WRITE", "1") == "0":
        return None
    from collections import Counter as _Counter

    from ztare.common.candidate_memory import (
        best_admissible_candidate_memory_record,
    )
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.evidence_consolidation import build_row_bitmap
    from ztare.worldmodel.spec_abduction import (
        _abduce_pattern_write,
        _diff,
        _effect_present,
        _freeze,
        _separating_count,
        _thaw,
    )
    from ztare.worldmodel.spec_catalog import validate_patch_delta_spec

    episode = project / "raw" / "episodes" / "episode_001.jsonl"
    if not episode.is_file():
        return None
    record = best_admissible_candidate_memory_record(
        project, require_submission_source=True
    )
    incumbent_ref = str((record or {}).get("submission") or "").strip()
    incumbent_sha = str((record or {}).get("sha") or "").strip()
    incumbent_path = project / incumbent_ref if incumbent_ref else None
    if not (incumbent_ref and incumbent_sha and incumbent_path and incumbent_path.is_file()):
        # Candidate memory is epoch-scoped; after evidence growth every record
        # is stale and admissible rows are empty (measured live). Fall back to
        # the current root carrier: snapshot its BYTES into the immutable
        # submissions namespace (content-addressed) and chain the delta over
        # that snapshot — mutable-root identity never enters the patch chain,
        # and the loader composes nested PATCH_BASE chains natively.
        root = project / "test_model.py"
        if not root.is_file():
            return None
        root_bytes = root.read_bytes()
        incumbent_sha = hashlib.sha256(root_bytes).hexdigest()
        snapshot = (
            project
            / "workspace"
            / "submissions"
            / f"pattern_delta_base_{incumbent_sha[:16]}.py"
        )
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if not snapshot.exists():
            temporary = snapshot.with_suffix(".tmp")
            temporary.write_bytes(root_bytes)
            temporary.replace(snapshot)
        elif _sha_file(snapshot) != incumbent_sha:
            raise ValueError("content-addressed pattern-delta base collision")
        incumbent_path = snapshot
        incumbent_ref = str(snapshot.relative_to(project))
    bitmap = build_row_bitmap(incumbent_path, episode, project_dir=project)
    wrong = [int(i) for i in bitmap.get("wrong_rows") or []]
    if not wrong or bitmap.get("load_error"):
        return None
    log = EpisodeLog.read_jsonl(episode)
    rows = list(log)
    from ztare.worldmodel.gates import env_frame_indices

    # Guards are laws about PHYSICS rows: learn them on gate-scored rows only.
    # Env-frames (deaths, level boundaries) are excluded from scoring, so a
    # guard needs no opinion there — and learning on them made every guard
    # unlearnable (measured: 46 of the 149 count-guard blockers were env rows).
    scored = [tr for i, tr in enumerate(rows) if i not in set(env_frame_indices(log))]
    def _mine_pool(wrong_indices):
        # Multi-family residual mining: compound rows (a restoration plus a
        # depletion landing on the same frame) need rules from more than one
        # family before the ROW count can converge — measured: the bar
        # pattern alone fixed cells on ~330 rows but flipped only the 6 rows
        # where it was the sole diff. Same proposal miners abduction uses.
        from ztare.worldmodel.spec_abduction import (
            _abduce_accumulate_extremal,
            _abduce_consume_extremal,
        )

        pool: _Counter = _Counter()
        for i in wrong_indices[:512]:
            if not (0 <= i < len(rows)):
                continue
            tr = rows[i]
            d = _diff(tr.s, tr.s_next)
            for rule in (
                _abduce_pattern_write(tr.s, tr.s_next, d)
                + _abduce_consume_extremal(tr.s, tr.s_next, d)
                + _abduce_accumulate_extremal(tr.s, tr.s_next, d)
            ):
                pool[_freeze(rule)] += 1
        return pool

    def _cell_stump(fired, paused):
        """One-cell decision stump: a (y, x, value) whose step-start content
        holds on EVERY fired row and on as few paused rows as possible.
        Substrate-general: the learner picks whichever cell the data
        separates on (a regime indicator emerges from evidence rather than
        being named). Returns (when_region_guard, remaining_paused)."""
        if not fired:
            return None, paused
        h, w = len(fired[0].s), len(fired[0].s[0])
        best = None
        for y in range(h):
            for x in range(w):
                v = fired[0].s[y][x]
                if any(tr.s[y][x] != v for tr in fired):
                    continue
                keep = [tr for tr in paused if tr.s[y][x] == v]
                if best is None or len(keep) < best[0]:
                    best = (len(keep), y, x, v, keep)
        if best is None or best[0] >= len(paused):
            return None, paused
        _, y, x, v, keep = best
        return [int(y), int(x), int(y), int(x), [int(v)]], keep

    def _guarded_rule_for(key, pool):
        rule = _thaw(key)
        fired = [tr for tr in scored if _effect_present(rule, tr)]
        paused = [tr for tr in scored if not _effect_present(rule, tr)]
        if not fired or not paused:
            return None
        guarded = dict(rule)
        guard = _separating_count(fired, paused)
        if guard is None:
            # SEQUENTIAL COVERING, most-intrinsic guard first. (1) The
            # RESTORATION PRECONDITION (when_overlap AND-veto): a restoration
            # fires only while the target region LACKS its restored content —
            # veto colors are pattern values absent from every fired row's
            # step-start rect. Data-derived, no substrate nouns, and it
            # eliminates the bulk of paused rows so the later learners face a
            # small remainder instead of the whole bank (greedy-stump myopia
            # measured: stump-first picked a weak cell against 16k paused and
            # the cascade died). (2) A one-cell when_region stump on the
            # remainder. (3) A count threshold on what is left. All three
            # compose as AND in the executor.
            remaining = list(paused)
            is_pattern = rule.get("op") == "pattern_write"
            if is_pattern:
                ry0, rx0, ry1, rx1 = (int(v) for v in rule["rect"])
                pat_colors = sorted(set(int(v) for v in rule["pattern"]))
            else:
                ry0 = rx0 = ry1 = rx1 = 0
                pat_colors = []

            def _rect_colors(tr):
                h, w = len(tr.s), len(tr.s[0])
                return {
                    int(tr.s[y][x])
                    for y in range(ry0, ry1 + 1)
                    for x in range(rx0, rx1 + 1)
                    if 0 <= y < h and 0 <= x < w
                }

            # MAJORITY veto (>=95% of fired lack the color in-rect): a small
            # minority of fired rows may complete the pattern from a partial
            # pre-state; a guard that skips them leaves those rows exactly as
            # wrong as the incumbent (no regression under the row-dominance
            # door) while the majority still gets fixed. Downstream learners
            # then use only the veto-compatible fired subset, so their
            # constants stay consistent.
            fired_v = list(fired)
            veto = []
            for c in pat_colors:
                lacking = [tr for tr in fired if c not in _rect_colors(tr)]
                if len(lacking) >= max(1, int(0.90 * len(fired))):
                    veto.append(c)
                    fired_v = [tr for tr in fired_v if c not in _rect_colors(tr)]
            if veto and fired_v:
                guarded["when_overlap"] = [veto, ry0, rx0, ry1, rx1]
                remaining = [
                    tr for tr in remaining
                    if not (_rect_colors(tr) & set(veto))
                ]
            else:
                fired_v = fired
            if remaining:
                region_guard, remaining = _cell_stump(fired_v, remaining)
                if region_guard is not None:
                    guarded["when_region"] = region_guard
            if remaining:
                guard = _separating_count(fired_v, remaining)
                if guard is None:
                    # ACTION CESSION (last resort, dominance-shaped): when the
                    # final blockers share an action footprint the fired set
                    # does not exhaust, restrict the rule to the unblocked
                    # actions. The ceded rows stay exactly as wrong as the
                    # incumbent (no regression); the kept actions' rows get
                    # fixed — a strict row-subset improvement. Perfection is
                    # not required per step: the next producer round attacks
                    # the ceded remainder against the NEW, smaller residual.
                    blocker_actions = {int(tr.a) for tr in remaining}
                    kept_actions = sorted(
                        {int(tr.a) for tr in fired_v} - blocker_actions
                    )
                    if not kept_actions:
                        return None
                    guarded["when_action"] = kept_actions
                    remaining = [
                        tr for tr in remaining if int(tr.a) in kept_actions
                    ]
                    if remaining:
                        return None
                    guard = None
        if guard is not None:
            guarded["when_count"] = guard
        return guarded

    # GREEDY DELTA CHAIN: accept a rule only if the COMPOSED candidate's row
    # bitmap is a strict subset of the current composition's wrong rows with
    # zero regressions (the same relation the promotion door checks). Refill
    # rows are compound (bar + reserve pips + sprites change together), so a
    # single pattern rarely flips whole rows; chaining lets each layer claim
    # its cells and the ROW count converges. Every acceptance is re-verified
    # by the shared evaluator on a materialized temp candidate — no in-memory
    # shortcut can diverge from what the gate will later see.
    chain: list[dict] = []
    cur_wrong = set(wrong)
    last_accepted = None
    for _round in range(4):
        pool = _mine_pool(sorted(cur_wrong))
        if not pool:
            break

        def _support(key) -> int:
            rule = _thaw(key)
            return pool[key] * max(1, len(rule.get("pattern") or ()))

        accepted = None
        for key in sorted(pool, key=_support, reverse=True)[:6]:
            guarded = _guarded_rule_for(key, pool)
            if guarded is None:
                continue
            trial = chain + [guarded]
            delta_spec = {"actions": {}, "always": trial}
            if validate_patch_delta_spec(delta_spec) is not None:
                continue
            trial_source = (
                "PATCH_BASE = "
                + pprint.pformat(
                    {"sha256": incumbent_sha, "source_ref": incumbent_ref},
                    sort_dicts=True, width=100,
                )
                + "\n\nPATCH_DELTA_SPEC = "
                + pprint.pformat(delta_spec, sort_dicts=True, width=100)
                + "\n"
            )
            trial_sha = hashlib.sha256(trial_source.encode("utf-8")).hexdigest()
            trial_path = (
                project / "workspace" / "submissions"
                / f"pattern_delta_{trial_sha[:16]}.py"
            )
            if not trial_path.exists():
                tmp = trial_path.with_suffix(".tmp")
                tmp.write_text(trial_source, encoding="utf-8")
                tmp.replace(trial_path)
            trial_bm = build_row_bitmap(trial_path, episode, project_dir=project)
            trial_wrong = set(int(v) for v in trial_bm.get("wrong_rows") or [])
            if trial_bm.get("load_error") or not (trial_wrong < cur_wrong):
                try:
                    trial_path.unlink()
                except OSError:
                    pass
                continue
            chain, cur_wrong = trial, trial_wrong
            accepted = (trial_path, trial_sha)
            last_accepted = accepted
            break
        if accepted is None:
            break
    if not chain or last_accepted is None:
        return None
    output, candidate_sha = last_accepted
    guarded = chain[-1]
    rule = guarded
    # Receipt + proposal for the accepted chain (file already materialized
    # and dominance-verified by the chain driver above).
    _receipt_path = project / "workspace" / "residual_pattern_delta_receipts.jsonl"
    _receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with _receipt_path.open("a") as _rf:
        _rf.write(json.dumps(
            {
                "schema": "ztare-residual-pattern-delta-proposal-v1",
                "producer_id": str(
                    declaration.get("producer_id")
                    or "worldmodel_residual_pattern_delta.v1"
                ),
                "candidate_sha256": candidate_sha,
                "incumbent_sha256": incumbent_sha,
                "chain_length": len(chain),
                "incumbent_wrong_rows": len(wrong),
                "chain_wrong_rows": len(cur_wrong),
                "rows_fixed": len(set(wrong) - cur_wrong),
                "rules": [
                    {
                        "rect": r.get("rect"),
                        "pattern_cells": len(r.get("pattern") or ()),
                        "when_count": r.get("when_count"),
                        "when_region": r.get("when_region"),
                        "when_overlap": r.get("when_overlap"),
                        "when_action": r.get("when_action"),
                    }
                    for r in chain
                ],
                "ts": datetime.now(timezone.utc).isoformat(),
            }) + "\n")
        return DeterministicCandidateProposal(
            producer_id=str(
                declaration.get("producer_id")
                or "worldmodel_residual_pattern_delta.v1"
            ),
            candidate_path=output,
            candidate_sha256=candidate_sha,
            input_sha256s={
                str(episode.relative_to(project)): _sha_file(episode),
                incumbent_ref: incumbent_sha,
                str(Path(__file__).resolve()): _sha_file(Path(__file__).resolve()),
            },
        )
    return None


_PRODUCERS: dict[str, CandidateProducer] = {
    "worldmodel.catalog_operation_patch_compiler.v1": _catalog_operation_patch_compiler,
    "worldmodel.residual_pattern_delta.v1": _residual_pattern_delta_compiler,
}


def configured_proposals(
    project_dir: str | Path,
    play_config: dict[str, Any],
    *,
    phase: str,
) -> list[DeterministicCandidateProposal]:
    project = Path(project_dir).resolve()
    declarations = play_config.get("deterministic_candidate_producers") or []
    if not isinstance(declarations, list):
        raise ValueError("deterministic_candidate_producers must be a list")
    proposals: list[DeterministicCandidateProposal] = []
    for declaration in declarations:
        if not isinstance(declaration, dict) or declaration.get("phase") != phase:
            continue
        kind = str(declaration.get("kind") or "")
        producer = _PRODUCERS.get(kind)
        if producer is None:
            raise ValueError(f"unregistered deterministic candidate producer: {kind!r}")
        proposal = producer(project, declaration)
        if proposal is None:
            continue
        proposals.append(proposal)
    return proposals


def evaluate_configured_candidates(
    project_dir: str | Path,
    play_config: dict[str, Any],
    *,
    phase: str,
) -> list[GatedDeterministicCandidate]:
    """Materialize proposals and return every project-gate consequence.

    Rejected proposals remain first-class consequences: a localized residual
    can be a better repair frontier than restarting discovery over the raw
    bank.  This function grants no adoption authority; ``gate_pass`` is the
    only promotion boundary.
    """
    from ztare.validator.core.pre_judge_gate import (
        consume_pre_judge_gate_receipt,
        run_pre_judge_gate_harness,
    )

    project = Path(project_dir).resolve()
    assessed: list[GatedDeterministicCandidate] = []
    for proposal in configured_proposals(project, play_config, phase=phase):
        _append_receipt(
            project,
            {
                "schema": "ztare-deterministic-candidate-producer-receipt-v1",
                "event": "materialized",
                "phase": phase,
                "producer_id": proposal.producer_id,
                "candidate_ref": str(proposal.candidate_path.relative_to(project)),
                "candidate_sha256": proposal.candidate_sha256,
                "input_sha256s": proposal.input_sha256s,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
        result = run_pre_judge_gate_harness(
            enabled=True,
            project_dir=project,
            latest_eval_results_path=project / "latest_eval_results.json",
            python_executable=sys.executable,
            candidate_path=proposal.candidate_path,
        )
        payload = result.payload if isinstance(result.payload, dict) else {}
        gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
        consumed = consume_pre_judge_gate_receipt(
            payload,
            candidate_path=proposal.candidate_path,
        )
        authorized = bool(result.ran and consumed["evaluator_authorized"])
        _append_receipt(
            project,
            {
                "schema": "ztare-deterministic-candidate-producer-receipt-v1",
                "event": "consumed_by_project_gate",
                "phase": phase,
                "producer_id": proposal.producer_id,
                "candidate_sha256": proposal.candidate_sha256,
                "gate_engine": payload.get("engine"),
                "gate_pass": authorized,
                "raw_gate_failures": consumed["failed_gates"],
                "pre_judge_decision_consumed": True,
                "gate_names": sorted(gates),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
        assessed.append(GatedDeterministicCandidate(proposal, payload, authorized))
    return assessed


__all__ = [
    "DeterministicCandidateProposal",
    "GatedDeterministicCandidate",
    "configured_proposals",
    "evaluate_configured_candidates",
]
