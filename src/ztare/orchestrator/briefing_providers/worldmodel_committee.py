"""Briefing provider: world-model committee state (GP-250 P1).

Applies on interactive-environment projects (rubric declares
`fit_expression_grammar: "grid_dsl"`). Renders the committee read model the
adapter maintains at `workspace/worldmodel_committee.json`: committee size,
the MDL champion, closing guard families, witnessed contexts, and — on a
grammar-ceiling event — the explicit statement that the mutator's job is a
grammar *extension* through the promotion contract, never a free-form world
model. The provider reads the read model only; it never touches an
environment or the episode log.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ztare.common.kernel_admissibility import validate_kernel_change_admissibility
from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class WorldmodelCommitteeProvider(BriefingProvider):
    name = "worldmodel_committee"
    max_fragment_chars = 1800

    def applies(self, ctx: BriefingContext) -> bool:
        if (ctx.rubric or {}).get("fit_expression_grammar") != "grid_dsl":
            return False
        try:
            from ztare.common.leaf_workbench_executor import (
                active_workbench_task_capability_scope,
            )

            task_scope, _task = active_workbench_task_capability_scope(
                ctx.project_dir
            )
            if task_scope:
                # Committee projections are broad read models.  A selected
                # task owns the current evidence topology and reaches the leaf
                # through its task-bound kernel receipt instead.
                return False
        except Exception:  # noqa: BLE001
            pass
        return (ctx.project_dir / "workspace" / "worldmodel_committee.json").exists()

    def fragment(self, ctx: BriefingContext) -> str:
        path = ctx.project_dir / "workspace" / "worldmodel_committee.json"
        try:
            model = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            return f"## World-model committee\n(unreadable read model: {exc})\n"

        lines = ["## World-model committee"]
        status = model.get("status")
        lines.append(f"- status: {status}; committee size {model.get('committee_size')} "
                     f"over {model.get('transitions')} logged transitions "
                     f"(evidence {str(model.get('evidence_hash'))[:12]})")
        if model.get("guard_families"):
            lines.append(f"- closing guard families: {model['guard_families']}")
        if model.get("champion") is not None:
            lines.append(f"- MDL champion: `{model['champion']}`")
        witnessed = model.get("witnessed_contexts") or []
        lines.append(f"- witnessed guard contexts (action, t%2, t%3): {len(witnessed)}")
        sat = _saturation_block(ctx.project_dir)
        if sat:
            lines.append(sat)
        harvest = _level_boundary_harvest_block(ctx.project_dir)
        if harvest:
            lines.append(harvest)
        residual_classes = _residual_class_receipt_block(ctx.project_dir)
        if residual_classes:
            lines.append(residual_classes)
        transfer_receipts = _level_transfer_receipt_block(ctx.project_dir)
        if transfer_receipts:
            lines.append(transfer_receipts)
        replay_diag = _replay_diagnostics_block(ctx.project_dir)
        if replay_diag:
            lines.append(replay_diag)
        turn_focus = os.environ.get("ZTARE_WORLDMODEL_TURN_FOCUS", "").strip()
        task_hypothesis_ceiling = _task_hypothesis_ceiling_block(ctx.project_dir)
        if task_hypothesis_ceiling:
            lines.append(task_hypothesis_ceiling)
            lines.append(_goal_exemplar_block(ctx.project_dir))
        if status == "grammar_ceiling" and turn_focus != "task_hypothesis":
            from ztare.worldmodel.spec_catalog import render_catalog_contract
            lines.append("- " + render_catalog_contract())
            lines.append(_abduced_core_block(ctx.project_dir))
            lines.append(
                "- GRAMMAR CEILING: no program in the seed grammar survives the log. "
                "FALLBACK CARRIAGE (only for dynamics the operator catalog cannot express): "
                "a direct executable world model — define step(grid, action, t) returning "
                "the predicted next grid as a tuple of tuples of ints (aliases "
                "f/model/I_model accepted). It must be deterministic and total. The "
                "gates score it by exact replay over the visible log + full-depth "
                "held-out rollout — the SAME gates as the DSL path. Alternatively, for "
                "a minimal symbolic extension, define EXTENSIONS_SRC = "
                "{\"<snake_case_name>\": \"def extension(grid):\\n    ...\"} (pure "
                "grid->grid, no imports/IO) and use [\"ext\", \"<name>\", <grid-expr>] "
                "nodes in a PROGRAM AST. Either carrier passes the same replay + "
                "rollout gates; a bare seed-grammar PROGRAM cannot pass at a ceiling. "
                "OPTIONAL goal-cue: you MAY also define progress(grid)->float — a "
                "heuristic inferred from the OBSERVED frames estimating how close a "
                "state is to a task-discharge event. It is NOT scored and NOT a success "
                "claim; it only STEERS the planner's exploration, and the "
                "registered adapter adjudicator is the sole judge of success. Higher = "
                "closer. Omit it if the frames give no usable cue. You MAY also "
                "define GOAL_PREDICATE(grid)->bool — your falsifiable HYPOTHESIS of "
                "the task-discharge configuration, inferred from observed frames "
                "(state its rival and what observation would refute it in your "
                "thesis). The planner searches directly for states satisfying it; "
                "the registered adapter adjudicator remains the sole judge — a wrong "
                "predicate costs search time, never a false success."
            )
            if not task_hypothesis_ceiling:
                try:
                    lines.append(_goal_exemplar_block(ctx.project_dir))
                except Exception as exc:  # noqa: BLE001 (SystemExit not caught)
                    # Surface, never silently omit: a malformed exemplar record
                    # must not vanish the GOAL_PREDICATE ground truth silently.
                    lines.append(f"- goal exemplars: DEGRADED — {type(exc).__name__}: {exc}")
        return "\n".join(lines) + "\n"

    def structured_records(self, ctx: BriefingContext) -> list[dict]:
        """Expose worldmodel receipts to the generic attention agenda.

        This stays reader-only: prompt assembly consumes persisted summaries
        produced by play loops/probes; it does not run abduction, gates, or
        environment calls.
        """
        project = Path(ctx.project_dir)
        records: list[dict] = []
        records.extend(_kernel_role_binding_records(project))
        records.extend(_planner_anomaly_records(project))
        records.extend(_loop_control_records(project))
        records.extend(_compressed_counterexample_records(project))
        records.extend(_level_boundary_harvest_records(project))
        records.extend(_residual_class_receipt_records(project))
        records.extend(_level_transfer_receipt_records(project))
        return records[:16]


_ROLE_SURFACES = (
    "workspace/latest_loop_event.json",
    "workspace/latest_sprint_receipt.json",
    "workspace/latest_level_transfer_probe.json",
    "workspace/arc3_play_loop_report.json",
    "workspace/mutator_briefing_projection_latest.json",
)

_KERNEL_ROLES = {
    "verification",
    "representation",
    "compression",
    "counterexample_routing",
    "memory",
    "search_control",
    "model_update",
    "selection",
    "write_back",
}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _kernel_role_binding_records(project: Path) -> list[dict]:
    records: list[dict] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    for rel in _ROLE_SURFACES:
        path = project / rel
        payload = _read_json(path)
        if payload is None:
            continue
        for binding in _extract_kernel_role_bindings(payload):
            term = str(binding.get("term") or "").strip()
            roles = sorted(_coerce_roles(binding.get("roles") or binding.get("kernel_roles")))
            if not term or len(roles) < 2:
                continue
            key = (term.lower(), tuple(roles), rel)
            if key in seen:
                continue
            seen.add(key)
            records.append({
                "source_type": "kernel_role_binding",
                "term": term,
                "kernel_roles": roles,
                "source_ref": rel,
                "action": "compile into substrate-neutral invariant/test before adding machinery",
            })
    return records


def _planner_anomaly_records(project: Path) -> list[dict]:
    payload = _read_json(project / "workspace" / "arc3_play_loop_report.json")
    if not isinstance(payload, dict):
        return []
    records = []
    for entry in payload.get("cycles") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("pursuit") != "plan_exhausted":
            continue
        if int(entry.get("levels_gained") or 0) != 0:
            continue
        if int(entry.get("evidence_grown_by") or 0) != 0:
            continue
        records.append({
            "source_type": "planner_anomaly",
            "anomaly_class": "plan_exhausted_without_task_progress_or_new_evidence",
            "expected_next_kernel_action": "goal-cue synthesis, compressed counterexample repair, or targeted evidence request",
            "observed_next_action": (
                f"cycle={entry.get('cycle')} exhausted {entry.get('steps')} steps "
                f"with played={entry.get('played') or '?'}"
            ),
            "source_ref": "workspace/arc3_play_loop_report.json",
            "action": "route through Strategy Office before another broad sweep",
        })
    return records[-3:]


def _loop_control_records(project: Path) -> list[dict]:
    payload = _read_json(project / "workspace" / "latest_information_yield.json")
    if not isinstance(payload, dict):
        return []
    signal = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    weakest = str(signal.get("weakest_point") or "")
    action = str(decision.get("action") or "")
    lower = weakest.lower()
    tags = []
    if signal.get("mutation_r1_mismatch") or "r1" in lower:
        tags.append("r1_declaration_mismatch")
    if "pre_judge" in lower or "pre-judge" in lower:
        tags.append("pre_judge_gate_loop")
    if "patch_base" in lower or "strictly improve" in lower:
        tags.append("patch_base_no_improvement")
    if "strategy_card" in lower:
        tags.append("strategy_card_attention_failure")
    if action == "REFRESH_SPECIALISTS" and not tags:
        tags.append("low_yield_specialist_refresh")
    if not tags:
        return []
    return [{
        "source_type": "scheduler_counterexample",
        "anomaly_class": "low_yield_loop_control",
        "scheduler_tags": tags,
        "decision_action": action,
        "stagnant_window": decision.get("stagnant_window"),
        "summary": weakest[:360],
        "expected_next_kernel_action": (
            "compile routing failure into quotient repair, typed card discharge, "
            "targeted evidence request, or kernel-improvement receipt"
        ),
        "source_ref": "workspace/latest_information_yield.json",
        "action": (
            "require typed scheduler-disposition receipt before retrying the "
            "same lineage"
        ),
    }]


def _compressed_counterexample_records(project: Path) -> list[dict]:
    payload = _read_json(project / "workspace" / "latest_level_transfer_probe.json")
    if not isinstance(payload, dict):
        return []
    q = payload.get("residue_quotient") or {}
    cert = payload.get("repair_certificate") or {}
    local = payload.get("local_transfer") or {}
    if not isinstance(q, dict) or not q.get("residue_class"):
        return []
    return [{
        "source_type": "compressed_counterexample",
        "residue_class": q.get("residue_class"),
        "cell_count": q.get("cell_count"),
        "repair_class": cert.get("repair_class"),
        "repair_sufficient_for_first_step": bool(cert.get("sufficient_for_first_step")),
        "post_depth": payload.get("post_depth"),
        "local_steps_tested": local.get("steps_tested"),
        "exact_steps_after_first_step_repair": local.get("exact_steps_after_first_step_repair"),
        "first_step_repair_generalizes_to_depth": local.get("first_step_repair_generalizes_to_depth"),
        "source_ref": "workspace/latest_level_transfer_probe.json",
        "action": "repair or explicitly waive the quotient class before broad exploration",
    }]


def _latest_level_boundary_harvest(project: Path) -> tuple[Path, dict] | None:
    workspace = project / "workspace"
    candidates = sorted(
        workspace.glob("level_boundary_harvest_episode_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        payload = _read_json(path)
        if not (
            isinstance(payload, dict)
            and payload.get("schema") == "ztare-arc3-level-boundary-harvest-v1"
        ):
            continue
        source_name = Path(str(payload.get("episode_path") or "")).name
        if source_name == "episode_002.jsonl" or path.stem.endswith("_002"):
            # A derived presentation retains its source evidence role.  Run
            # mode cannot demote an active holdout; a lawful transition must
            # mint a separately visible artifact and a successor withheld slice.
            continue
        return path, payload
    return None


def _level_boundary_harvest_records(project: Path) -> list[dict]:
    latest = _latest_level_boundary_harvest(project)
    if latest is None:
        return []
    path, payload = latest
    rel = f"workspace/{path.name}"
    post_depth = int(payload.get("post_depth") or 0)
    transitions = int(payload.get("transitions") or 0)
    branches = payload.get("branches") or []
    seed_path = payload.get("seed_path")
    seed_snapshot_ref = payload.get("seed_snapshot_ref")
    seed_candidates = []
    if isinstance(seed_path, str) and seed_path:
        seed_candidates.append(project / seed_path)
    if isinstance(seed_snapshot_ref, str) and seed_snapshot_ref:
        seed_candidates.append(project / seed_snapshot_ref)
    seed_available = any(path.exists() for path in seed_candidates)
    return [{
        "source_type": "level_boundary_harvest",
        "schema": payload.get("schema"),
        "source_ref": rel,
        "episode_path": payload.get("episode_path"),
        "content_hash": payload.get("content_hash"),
        "seed_path": seed_path,
        "seed_sha256": payload.get("seed_sha256"),
        "seed_snapshot_ref": seed_snapshot_ref,
        "seed_available": seed_available,
        "transitions": transitions,
        "post_depth": post_depth,
        "branches": len(branches) if isinstance(branches, list) else None,
        "authority": "observed transitions only; use as abduction evidence, not as model adoption",
        "action": (
            "include this harvested boundary episode when fitting or testing transfer laws"
            if seed_available
            else "seed bytes are missing; use the harvested episode as evidence, but rerun/transfer probes need a fresh replayable boundary seed"
        ),
    }]


def _latest_residual_class_receipt(project: Path) -> tuple[Path, dict] | None:
    workspace = project / "workspace"
    candidates = sorted(
        workspace.glob("*residual_classes_receipt.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        payload = _read_json(path)
        if (
            isinstance(payload, dict)
            and payload.get("schema") == "ztare-worldmodel-residual-class-receipt-v1"
        ):
            return path, payload
    return None


def _compact_residual_classes(payload: dict, *, limit: int = 3) -> list[dict]:
    classes = payload.get("top_residual_classes") or []
    if not isinstance(classes, list):
        return []
    out: list[dict] = []
    for item in classes[:limit]:
        if not isinstance(item, dict):
            continue
        out.append({
            "rank": item.get("rank"),
            "count": item.get("count"),
            "first_t": item.get("first_t"),
            "action": item.get("action"),
            "cell_count": item.get("cell_count"),
            "t_values": item.get("t_values") or [],
            "first_witnesses": (item.get("first_witnesses") or [])[:4],
        })
    return out


def _residual_class_receipt_records(project: Path) -> list[dict]:
    latest = _latest_residual_class_receipt(project)
    if latest is None:
        return []
    path, payload = latest
    admissibility = validate_kernel_change_admissibility(payload.get("kernel_admissibility"))
    return [{
        "source_type": "residual_class_receipt",
        "schema": payload.get("schema"),
        "source_ref": f"workspace/{path.name}",
        "source_receipt": payload.get("source_receipt"),
        "source_log": payload.get("source_log"),
        "status": payload.get("status"),
        "matched_transitions": payload.get("matched_transitions"),
        "transitions": payload.get("transitions"),
        "residual_class_count": payload.get("residual_class_count"),
        "top_residual_classes": _compact_residual_classes(payload),
        "admissibility_passed": admissibility.passed,
        "admissibility_failures": list(admissibility.failures),
        "authority": payload.get(
            "authority",
            "descriptive residual quotient only; raw gates remain authority",
        ),
        "action": (
            "route the top residual quotient classes before broad mutation; "
            "preserve raw witnesses and require replay/holdout gates for adoption"
        ),
    }]


def _latest_level_transfer_receipt(project: Path) -> tuple[Path, dict] | None:
    workspace = project / "workspace"
    candidates: list[Path] = []
    latest_probe = workspace / "latest_level_transfer_probe.json"
    if latest_probe.exists():
        candidates.append(latest_probe)
    for path in workspace.glob("level*_transfer*.json"):
        if path.name != "latest_level_transfer_probe.json":
            candidates.append(path)
    if not candidates:
        return None
    path = max(candidates, key=lambda p: p.stat().st_mtime)
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return None
    return path, payload


def _level_transfer_verdict_numbers(payload: dict) -> object:
    verdict = payload.get("verdict")
    if isinstance(verdict, dict):
        for key in ("numbers", "score", "verdict_numbers"):
            if key in verdict:
                return verdict.get(key)
    for key in ("verdict_numbers", "numbers", "score"):
        if key in payload:
            return payload.get(key)
    return None


def _level_transfer_receipt_records(project: Path) -> list[dict]:
    latest = _latest_level_transfer_receipt(project)
    if latest is None:
        return []
    path, payload = latest
    return [{
        "source_type": "level_transfer_receipt",
        "schema": payload.get("schema"),
        "source_ref": f"workspace/{path.name}",
        "verdict_numbers": _level_transfer_verdict_numbers(payload),
        "refinement_hint": payload.get("refinement_hint"),
        "authority": payload.get(
            "authority",
            "descriptive cross-level transfer evidence only; raw gates remain authority",
        ),
        "action": "route transfer evidence alongside residual-class receipts; do not promote on this read model",
    }]


def _level_transfer_receipt_block(project: Path) -> str:
    latest = _latest_level_transfer_receipt(project)
    if latest is None:
        return ""
    path, payload = latest
    verdict_numbers = _level_transfer_verdict_numbers(payload)
    refinement_hint = payload.get("refinement_hint")
    authority = payload.get(
        "authority",
        "descriptive cross-level transfer evidence only; raw gates remain authority",
    )
    lines = [
        "## Cross-level transfer receipt",
        f"- latest receipt: workspace/{path.name}",
    ]
    if verdict_numbers is not None:
        lines.append(f"- verdict numbers: {verdict_numbers}")
    if refinement_hint is not None:
        lines.append(f"- refinement_hint: {refinement_hint}")
    lines.append(f"- authority: {authority}")
    lines.append(
        "- descriptive cross-level transfer evidence only; route it adjacent to residual-class receipts and do not promote on this read model"
    )
    return "\n".join(lines)


def _extract_kernel_role_bindings(obj) -> list[dict]:
    out: list[dict] = []
    if isinstance(obj, dict):
        for key in ("kernel_role_bindings", "semantic_deanchor_bindings"):
            val = obj.get(key)
            if isinstance(val, list):
                out.extend(x for x in val if isinstance(x, dict))
        term = obj.get("term") or obj.get("local_term") or obj.get("concept")
        roles = obj.get("kernel_roles") or obj.get("roles")
        if term and roles:
            out.append({"term": term, "roles": roles})
        for val in obj.values():
            if isinstance(val, (dict, list)):
                out.extend(_extract_kernel_role_bindings(val))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_extract_kernel_role_bindings(item))
    return out


def _coerce_roles(raw) -> set[str]:
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        return set()
    return {str(x).strip() for x in items if str(x).strip() in _KERNEL_ROLES}


def _saturation_block(project_dir) -> str:
    """Surface the sprint's CEGAR trigger: when the latest sprint round saturated
    (every reachable object-state under the current physics already visited),
    exploration cannot progress without new physics or an out-of-model goal."""
    import json
    from pathlib import Path
    path = Path(project_dir) / "workspace" / "latest_sprint_receipt.json"
    if not path.exists():
        return ""
    try:
        r = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return ""
    if not r.get("saturated"):
        return ""
    n = int(r.get("n_candidates", 0) or 0)
    return ("## Exploration saturation\n"
            f"- EXPLORATION SATURATED under current physics; {n} structural goal "
            f"candidates ({n} untested). The residual is either un-modeled physics "
            "or an environment-judged goal outside modeled dynamics.")


def _task_hypothesis_ceiling_block(project_dir) -> str:
    """Render a task-hypothesis obligation independently of transition fit."""

    try:
        from ztare.worldmodel.strategy_battery import WorldmodelBattery

        pressure = WorldmodelBattery().run_audits(project_dir).get(
            "goal_hypothesis_pressure"
        ) or {}
    except Exception as exc:  # noqa: BLE001
        return f"## Task-hypothesis state\n- DEGRADED: {type(exc).__name__}: {exc}"
    status = pressure.get("status")
    if status not in {"version_space_empty", "version_space_stalled"}:
        return ""
    active = int(pressure.get("active_hypotheses") or 0)
    state = (
        "has no surviving predicate"
        if status == "version_space_empty"
        else (
            f"has {active} surviving predicate(s), but the bound planner receipt "
            "found no discriminating intervention within its declared budget"
        )
    )
    return (
        "## Task-hypothesis refinement obligation\n"
        f"- source epoch: {pressure.get('active_epoch')}; the current version space "
        f"{state}. The transition carrier and the task-hypothesis "
        "version space are separate objects.\n"
        "- Preserve the current transition behavior. Propose one falsifiable "
        "standalone adapter-lowered `GOAL_PREDICATE(observation) -> bool` "
        "module from current "
        "visible evidence, together with its rival and a discriminating "
        "intervention. The predicate only steers acquisition; the registered "
        "task adjudicator disposes it. Do not import or repeat the transition "
        "carrier; the kernel binds its immutable companion. Task-open states "
        "are behavioral no-goods: a predicate already true on one remains "
        "refuted under a syntactic rewrite. Do not import a prior-epoch "
        "terminal presentation. A prior task edge may transfer only as a "
        "falsifiable role/invariant hypothesis with a target-chart "
        "discriminator; it carries no discharge authority."
    )


def _level_boundary_harvest_block(project_dir) -> str:
    latest = _latest_level_boundary_harvest(Path(project_dir))
    if latest is None:
        return ""
    path, payload = latest
    transitions = int(payload.get("transitions") or 0)
    post_depth = int(payload.get("post_depth") or 0)
    branches = payload.get("branches") or []
    branch_count = len(branches) if isinstance(branches, list) else 0
    seed_ref = payload.get("seed_snapshot_ref") or payload.get("seed_path") or ""
    seed_available = bool(seed_ref) and (Path(project_dir) / str(seed_ref)).exists()
    seed_clause = (
        f" seed={seed_ref}."
        if seed_available
        else " seed bytes missing; rerun/transfer probes require a fresh boundary seed."
    )
    return (
        "## Level-boundary harvest\n"
        f"- latest receipt: workspace/{path.name}; {transitions} observed "
        f"post-boundary transitions across {branch_count} branches at depth {post_depth}; "
        "authority: observed transitions only, no model adoption. Include it when fitting "
        "or testing transfer laws before relying on stale pre-boundary evidence."
        f"{seed_clause}"
    )


def _residual_class_receipt_block(project_dir) -> str:
    latest = _latest_residual_class_receipt(Path(project_dir))
    if latest is None:
        return ""
    path, payload = latest
    admissibility = validate_kernel_change_admissibility(payload.get("kernel_admissibility"))
    matched = int(payload.get("matched_transitions") or 0)
    total = int(payload.get("transitions") or 0)
    class_count = int(payload.get("residual_class_count") or 0)
    lines = [
        "## Residual class receipt",
        f"- latest receipt: workspace/{path.name}; core replay {matched}/{total}; "
        f"{class_count} residual quotient classes; "
        f"admissibility={'pass' if admissibility.passed else 'fail'}"
        + (
            ""
            if admissibility.passed
            else f" ({', '.join(admissibility.failures)})"
        ),
        "- authority: descriptive quotient surface only; preserve raw witnesses and "
        "use replay/holdout gates for adoption.",
    ]
    for item in _compact_residual_classes(payload):
        witnesses = "; ".join(str(w) for w in item.get("first_witnesses") or [])
        lines.append(
            f"  class #{item.get('rank')}: count={item.get('count')}, "
            f"first_t={item.get('first_t')}, action={item.get('action')}, "
            f"cells={item.get('cell_count')}, t_values={item.get('t_values')}; "
            f"witnesses: {witnesses}"
        )
    return "\n".join(lines)


def _goal_exemplar_block(project_dir) -> str:
    """Labeled task edges scoped to the lifecycle that produced them."""
    import json
    from pathlib import Path
    path = Path(project_dir) / "workspace" / "goal_exemplars.jsonl"
    if not path.exists():
        return "- current-epoch task exemplars: none witnessed."
    try:
        from ztare.worldmodel.strategy_battery import _active_epoch

        active_epoch = _active_epoch(project_dir)
    except Exception:  # noqa: BLE001
        active_epoch = None
    try:
        raw = path.read_text().splitlines()
    except OSError as exc:
        return f"- goal exemplars: DEGRADED — unreadable exemplar log ({exc})."
    ex, skipped = [], []
    for n, l in enumerate(raw, 1):
        if not l.strip():
            continue
        try:
            row = json.loads(l)
        except json.JSONDecodeError:
            skipped.append(n)  # skip+count+name; never drop the whole block
            continue
        if (
            isinstance(row, dict)
            and row.get("schema") == "ztare-goal-exemplar-v2"
            and row.get("source_epoch") == active_epoch
        ):
            ex.append(row)
    if not ex:
        if skipped and len(skipped) == len([line for line in raw if line.strip()]):
            return (
                f"- current-epoch task exemplars: DEGRADED — all {len(skipped)} "
                f"non-blank line(s) unparseable (lines {skipped})."
            )
        return (
            f"- current-epoch task exemplars: none for source epoch {active_epoch}; "
            "prior-epoch presentations have no transport authority."
        )
    out = [f"- CURRENT-EPOCH TASK EXEMPLARS ({len(ex)} adapter-attested edges; "
           "any GOAL_PREDICATE proposed for this epoch must hold on their s_next):"]
    if skipped:
        out.append(f"  NOTE: skipped {len(skipped)} corrupt exemplar line(s) "
                   f"(lines {skipped}); good exemplars below.")
    for e in ex[:2]:
        d = [(y, x, e["s"][y][x], e["s_next"][y][x])
             for y in range(len(e["s"])) for x in range(len(e["s"][0]))
             if e["s"][y][x] != e["s_next"][y][x]]
        cells = "; ".join(f"({y},{x}):{a}->{b}" for y, x, a, b in d[:30])
        out.append(f"  exemplar (action={e['action']}, t={e['t']}, {len(d)} cells): {cells}")
    return "\n".join(out)


def _replay_diagnostics_block(project_dir) -> str:
    """Surface the current residual quotient from the last abduce pass (Axis 6 dead-letter fix).

    Reads workspace/latest_replay_diagnostics_after_abduce.json (bounded summary
    only — the full file stays in workspace for leaf workbench capability input).
    Returns "" when absent so the caller can append unconditionally."""
    import json
    from pathlib import Path

    path = Path(project_dir) / "workspace" / "latest_replay_diagnostics_after_abduce.json"
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    # ponytail: surface class_count + representative mismatch only; full detail via capability
    class_count = payload.get("class_count") or payload.get("residual_class_count")
    summary = str(payload.get("summary") or payload.get("outcome_summary") or "")[:200]
    if not class_count and not summary:
        return ""
    bits = [f"- replay residual (post-abduce): class_count={class_count}"]
    if summary:
        bits.append(f"  summary: {summary}")
    bits.append(
        "  full quotient: workspace/latest_replay_diagnostics_after_abduce.json "
        "(inspect_replay_residual_quotient capability)"
    )
    return "\n".join(bits)


def _abduced_core_block(project_dir) -> str:
    import json
    from pathlib import Path

    path = Path(project_dir) / "workspace" / "abduced_core.json"
    if not path.exists():
        return "- abduced core: no persisted receipt yet; briefing will not run abduction."
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return f"- abduced core: unreadable persisted receipt ({exc})."

    spec = payload.get("spec")
    if not spec:
        return "- abduction: no catalog-expressible core found; full law is yours."
    total = int(payload.get("transitions") or 0)
    matched = int(payload.get("matched_transitions") or 0)
    residuals = payload.get("residuals") or []
    if total and matched == total:
        return ("- ABDUCED SPEC (machine-verified, full replay): "
                + json.dumps(spec)[:1200]
                + " — submit it as WORLD_MODEL_SPEC unless you can beat its MDL.")
    out = ["- ABDUCED CORE (machine-verified on "
           f"{matched}/{total} transitions): "
           + json.dumps(spec)[:1200],
           f"- RESIDUAL — the {max(total - matched, 0)} transitions the core cannot explain "
           "(your job: extend the spec with when_count guards / a new rule, or "
           "carry a step() only for this mechanic):"]
    for r in residuals[:3]:
        cells = "; ".join(str(c) for c in (r.get("cells") or [])[:40])
        extra = int(r.get("cell_count") or 0) - 40
        out.append(
            f"  residual (t={r.get('t')}, action={r.get('action')}, "
            f"{r.get('cell_count')} cells): {cells}"
            + (f" ...+{extra}" if extra > 0 else "")
        )
    try:
        from ztare.worldmodel.spec_catalog import calibration_summary
        cal = calibration_summary(Path(project_dir).parent)
        if cal:
            out.append("- catalog calibration (ratified uses across games): "
                       + json.dumps(cal))
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(out)
