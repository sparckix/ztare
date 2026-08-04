"""Lower an accepted rendered-effect carrier into a factored search problem.

This module lowers accepted rendered-effect namespaces only; the search
algorithm and factor identities live in ``ztare.common.factored_search`` and
remain opaque to the substrate.

The lowering reads constants carried by the accepted program.  It does not
inspect a game implementation, introduce a route, or alter a prompt.  The
target comes from adapter-attested terminal-edge witnesses, while the adapter
remains the task-discharge authority after execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Callable, Hashable, Iterable, Mapping

from ztare.common.equivariance import stable_sha256


_REQUIRED_NAMESPACE_KEYS = frozenset({
    "SPRITE_RENDERING",
    "DISPLAY_CELLS",
    "ROTATION_RENDERINGS",
    "ROTATION_NEXT",
    "TIMER_GROUPS",
    "TIMER_TICK_VALUE",
    "OBJECT_RULES",
})


def _tuple_rows(value: Any) -> tuple[tuple[Any, ...], ...]:
    return tuple(tuple(row) for row in value)


def _prediction_key(state: Any, intervention: Any, time_value: Any) -> Hashable:
    """Use native carrier identity when available; digest only opaque states."""
    key = (state, intervention, time_value)
    try:
        hash(key)
    except TypeError:
        return stable_sha256({
            "state": state,
            "intervention": intervention,
            "time": time_value,
        })
    return key


def _partition_presentation(values: tuple[Any, ...]) -> tuple[tuple[int, ...], tuple[Any, ...]]:
    """Separate equality structure from the labels used to present it.

    The first-occurrence labels are a canonical representative of the finite
    set partition induced by ``==``.  Renaming values preserves the partition
    while changing only the returned presentation assignment.
    """
    labels: dict[Any, int] = {}
    partition: list[int] = []
    presentation: list[Any] = []
    for value in values:
        if value not in labels:
            labels[value] = len(labels)
            presentation.append(value)
        partition.append(labels[value])
    return tuple(partition), tuple(presentation)


@dataclass(frozen=True)
class FiberFactors:
    controlled_base: tuple[tuple[int, int], ...]
    finite_configuration: tuple[Any, ...]
    presentation_assignment: tuple[Any, ...]
    ordered_budget: int
    one_shot_availability: tuple[tuple[str, bool], ...]
    ordered_feasibility_configuration: tuple[bool, ...] = ()
    operation_domain_assignment: tuple[
        tuple[str, tuple[tuple[int, int], ...]], ...
    ] = ()

    def as_mapping(self) -> Mapping[str, Hashable]:
        return {
            "controlled_base": self.controlled_base,
            "finite_configuration": self.finite_configuration,
            "presentation_assignment": self.presentation_assignment,
            "operation_domain_assignment": self.operation_domain_assignment,
            "ordered_feasibility_configuration": (
                self.ordered_feasibility_configuration
            ),
            "ordered_budget": self.ordered_budget,
            "one_shot_availability": self.one_shot_availability,
        }


@dataclass(frozen=True)
class OperationRecurrenceAcquisitionObligation:
    """Adapter-attested obligation to seek a distinct operation context.

    The known edge is evidence and an exclusion, never the search target.  The
    adapter-local trigger can nominate a different presentation of the same
    conjectured boundary; live execution alone determines its consequence.
    This object carries no carrier-promotion or task-discharge authority.
    """

    obligation_sha256: str
    operation_identity_sha256: str
    trigger_lowering_sha256: str
    witnesses: tuple[tuple[object, int, int, str, object], ...]
    evidence_refs: tuple[str, ...]
    trigger: Callable[[object, object], bool] = field(
        compare=False,
        repr=False,
    )

    @property
    def known_source_states(self) -> tuple[object, ...]:
        # States are opaque at this boundary and need not be hashable.  Preserve
        # witness order while deduplicating by the state's own equality relation.
        unique: list[object] = []
        for state, *_rest in self.witnesses:
            if not any(state == prior for prior in unique):
                unique.append(state)
        return tuple(unique)

    @property
    def goal_source_states(self) -> tuple[object, ...]:
        """Known sources are exclusions and cannot activate goal-source routing."""
        return ()

    def accepts_edge(
        self,
        source: object,
        intervention: object,
        time_value: object,
        successor: object,
    ) -> bool:
        """Whether an edge is a new observation of this operation."""
        # Within one deterministic lifecycle, replaying the same source and
        # intervention at another clock coordinate is the same transition
        # context.  Treating the changed ``t`` property as recurrence makes the
        # planner replay an observation that evidence admission then deduplicates.
        if any(
            source == known_source and intervention == known_intervention
            for known_source, known_intervention, *_rest in self.witnesses
        ):
            return False
        return bool(self.trigger(source, successor))

    def for_source_epoch(
        self, source_epoch: object
    ) -> "OperationRecurrenceAcquisitionObligation | None":
        selected = tuple(row for row in self.witnesses if row[4] == source_epoch)
        if not selected:
            return None
        if len(selected) == len(self.witnesses):
            return self
        scoped_sha = stable_sha256({
            "parent_obligation_sha256": self.obligation_sha256,
            "source_epoch": source_epoch,
            "witnesses": [
                {
                    "source": source,
                    "intervention": intervention,
                    "time": time_value,
                    "evidence_ref": evidence_ref,
                }
                for source, intervention, time_value, evidence_ref, _epoch
                in selected
            ],
        })
        return OperationRecurrenceAcquisitionObligation(
            obligation_sha256=scoped_sha,
            operation_identity_sha256=self.operation_identity_sha256,
            trigger_lowering_sha256=self.trigger_lowering_sha256,
            witnesses=selected,
            evidence_refs=self.evidence_refs,
            trigger=self.trigger,
        )


def operation_recurrence_acquisition_obligation(
    project_dir: str | Path,
    *,
    source_epoch: object | None = None,
    materialize: bool = False,
) -> OperationRecurrenceAcquisitionObligation | None:
    """Lower the current recurrence receipt to an active experiment obligation.

    ``materialize`` belongs to orchestration, not planning: a live conductor
    may execute the registered deterministic workbench chain before reading
    the obligation, while diagnostic callers remain read-only by default.
    """

    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_receipt_family,
    )
    from ztare.worldmodel.evidence_quotients import resolve_episode_ref
    from ztare.worldmodel.episode_log import EpisodeLog

    project = Path(project_dir).resolve()
    family = active_workbench_task_receipt_family(
        project,
        adapter_id="worldmodel",
        materialize=materialize,
    )
    receipt = family.get("mine_worldmodel_lowerable_selectors")
    if not isinstance(receipt, Mapping):
        return None
    summary: Any = receipt.get("output_summary")
    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except json.JSONDecodeError:
            return None
    if (
        not isinstance(summary, Mapping)
        or summary.get("schema") != "ztare-worldmodel-operation-domain-selector-v1"
    ):
        return None
    obligation = summary.get("acquisition_obligation")
    if not isinstance(obligation, Mapping) or obligation.get("schema") != (
        "ztare-worldmodel-edge-acquisition-obligation-v1"
    ):
        return None
    obligation_identity = obligation.get("obligation_identity")
    if not isinstance(obligation_identity, Mapping):
        return None
    obligation_sha = str(obligation.get("obligation_sha256") or "")
    if stable_sha256(obligation_identity) != obligation_sha:
        raise ValueError("operation acquisition obligation identity changed")
    operation_sha = str(summary.get("operation_identity_sha256") or "")
    if operation_sha != str(
        obligation_identity.get("operation_identity_sha256") or ""
    ):
        raise ValueError("operation acquisition obligation changed operation identity")
    conjectures = summary.get("conjecture_predicates")
    trigger_rule = next(
        (
            dict(row)
            for row in (conjectures if isinstance(conjectures, list) else [])
            if isinstance(row, Mapping)
            and row.get("op") in {"region_event", "bind_region_value"}
        ),
        None,
    )
    if trigger_rule is None:
        return None
    trigger_sha = str(summary.get("operation_lowering_sha256") or "")
    if not trigger_sha or stable_sha256(trigger_rule) != trigger_sha:
        raise ValueError("operation acquisition trigger identity changed")
    from ztare.worldmodel.spec_catalog import (
        region_event_triggered,
        validate_patch_delta_spec,
    )

    lowering_error = validate_patch_delta_spec(
        {"actions": {}, "always": [trigger_rule]}
    )
    if lowering_error:
        raise ValueError(f"operation acquisition trigger is not lowerable: {lowering_error}")

    if trigger_rule["op"] == "region_event":
        def trigger(source: object, successor: object) -> bool:
            try:
                return bool(region_event_triggered(source, successor, trigger_rule))
            except Exception:
                return False
    else:
        def trigger(source: object, successor: object) -> bool:
            try:
                y0, x0, y1, x1 = (
                    int(value) for value in trigger_rule["target_rect"]
                )
                dy, dx = (
                    int(value) for value in trigger_rule["source_offset"]
                )
                expected = int(trigger_rule["expected_current"])
                source_value = source[y0 + dy][x0 + dx]
                return source_value != expected and any(
                    successor[row][col] == expected
                    for row in range(y0, y1 + 1)
                    for col in range(x0, x1 + 1)
                )
            except (IndexError, KeyError, TypeError, ValueError):
                return False

    observation_ref = str(obligation.get("source_observation_ref") or "")
    episode_ref, separator, row_text = observation_ref.partition("#transition:")
    if not separator or not row_text.isdigit():
        raise ValueError("operation acquisition obligation has no transition witness")
    row_index = int(row_text)
    episode_path = resolve_episode_ref(project, episode_ref)
    transition = EpisodeLog.read_jsonl_indices(episode_path, {row_index})[row_index]
    identity = transition.identity
    if (
        identity is None
        or not identity.is_authoritative
        or identity.is_boundary
        or identity.source_epoch != identity.target_epoch
    ):
        raise ValueError("operation acquisition witness is not law-owned")
    if source_epoch is not None and identity.source_epoch != source_epoch:
        return None
    hashes = receipt.get("input_hashes")
    hashes = hashes if isinstance(hashes, Mapping) else {}
    kernel_ref = str(hashes.get("kernel_receipt_ref") or "")
    evidence_refs = tuple(
        dict.fromkeys(ref for ref in (kernel_ref, observation_ref) if ref)
    )
    return OperationRecurrenceAcquisitionObligation(
        obligation_sha256=obligation_sha,
        operation_identity_sha256=operation_sha,
        trigger_lowering_sha256=trigger_sha,
        witnesses=((
            transition.s,
            int(transition.a),
            int(transition.t),
            observation_ref,
            identity.source_epoch,
        ),),
        evidence_refs=evidence_refs,
        trigger=trigger,
    )


class CompiledFiberProjection:
    """Pointwise factorizer compiled from one accepted carrier namespace."""

    factor_names = (
        "controlled_base",
        "finite_configuration",
        "presentation_assignment",
        "operation_domain_assignment",
        "ordered_feasibility_configuration",
        "ordered_budget",
        "one_shot_availability",
    )
    terminal_factor_names = ("controlled_base", "finite_configuration")
    feasibility_factor_names = ("ordered_budget",)
    availability_factor_names = ("one_shot_availability",)

    def __init__(
        self,
        *,
        sprite: tuple[tuple[Any, ...], ...],
        display_cells: tuple[tuple[int, int], ...],
        configurations: tuple[tuple[Any, ...], ...],
        configuration_next: Mapping[tuple[Any, ...], tuple[Any, ...]],
        budget_groups: tuple[tuple[tuple[int, int], ...], ...],
        budget_live_value: Any,
        rules: tuple[Mapping[str, Any], ...],
        domain_predicate,
        evidence_refs: tuple[str, ...],
    ) -> None:
        self.sprite = sprite
        self.display_cells = display_cells
        self.configurations = configurations
        self.configuration_next = dict(configuration_next)
        self.budget_groups = budget_groups
        self.budget_live_value = budget_live_value
        self.rules = rules
        self.domain_predicate = domain_predicate
        self.evidence_refs = evidence_refs
        self._validate()
        self._configuration_partition_next: dict[tuple[int, ...], tuple[int, ...]] = {}
        for source, target in self.configuration_next.items():
            source_partition, _ = _partition_presentation(source)
            target_partition, _ = _partition_presentation(target)
            prior = self._configuration_partition_next.get(source_partition)
            if prior is not None and prior != target_partition:
                raise ValueError(
                    "presentation renaming exposes two configuration successors"
                )
            self._configuration_partition_next[source_partition] = target_partition
        identity_payload = {
            "schema": "ztare-compiled-fiber-projection-v1",
            "sprite": sprite,
            "display_cells": display_cells,
            "configurations": configurations,
            "configuration_next": configuration_next,
            "budget_groups": budget_groups,
            "budget_live_value": budget_live_value,
            "rules": rules,
            "factor_names": self.factor_names,
            "terminal_factor_names": self.terminal_factor_names,
            "feasibility_factor_names": self.feasibility_factor_names,
            "availability_factor_names": self.availability_factor_names,
            "evidence_refs": evidence_refs,
        }
        self.projection_sha256 = stable_sha256(identity_payload)
        self._factor_cached = lru_cache(maxsize=1_024)(self._factor_uncached)

    def _validate(self) -> None:
        if not self.sprite or not self.sprite[0]:
            raise ValueError("compiled fiber projection requires a non-empty base rendering")
        width = len(self.sprite[0])
        if any(len(row) != width for row in self.sprite):
            raise ValueError("compiled base rendering must be rectangular")
        if len(set(self.configurations)) != len(self.configurations):
            raise ValueError("finite configurations must be distinct")
        if self.configurations:
            expected = set(self.configurations)
            if not self.configuration_next:
                raise ValueError("configuration action needs at least one witnessed edge")
            if not set(self.configuration_next).issubset(expected):
                raise ValueError("configuration action has a source outside its carrier")
            if not set(self.configuration_next.values()).issubset(expected):
                raise ValueError("configuration action has an image outside its carrier")
        if not self.budget_groups:
            raise ValueError("compiled fiber projection requires an ordered feasibility coordinate")
        for rule in self.rules:
            if not str(rule.get("id") or "").strip():
                raise ValueError("compiled effect rule requires identity")

    def in_domain(self, state: Any) -> bool:
        # A predicate failure is an apparatus fault, not evidence that the
        # state lies outside the represented domain.  The planner owns the
        # resulting obstruction boundary and must not spend a fallback search
        # budget after an instrument failed.
        return bool(self.domain_predicate(state))

    def _block(self, state: Any, row: int, col: int):
        height, width = len(self.sprite), len(self.sprite[0])
        if row < 0 or col < 0 or row + height > len(state):
            return None
        if any(col + width > len(state[index]) for index in range(row, row + height)):
            return None
        return tuple(
            tuple(state[row + offset][col:col + width])
            for offset in range(height)
        )

    def _factor_uncached(self, state: Any) -> FiberFactors:
        height, width = len(self.sprite), len(self.sprite[0])
        bases = tuple(
            (row, col)
            for row in range(len(state) - height + 1)
            for col in range(len(state[row]) - width + 1)
            if self._block(state, row, col) == self.sprite
        )
        rendered = tuple(state[row][col] for row, col in self.display_cells)
        configuration, presentation = _partition_presentation(rendered)
        operation_domains = []
        for rule in self.rules:
            if rule.get("type") != "operation_domain":
                continue
            if isinstance(rule.get("trigger_pattern"), Mapping):
                from ztare.worldmodel.spec_catalog import _trigger_pattern_rects

                rects = _trigger_pattern_rects(state, rule["trigger_pattern"])
            else:
                rects = (tuple(int(value) for value in rule["rect"]),)
            relative_origins = tuple(sorted(
                (row - base_row, col - base_col)
                for base_row, base_col in bases
                for row, col, _row_end, _col_end in rects
            ))
            operation_domains.append((str(rule["id"]), relative_origins))
        budget_configuration = tuple(
            all(state[row][col] == self.budget_live_value for row, col in group)
            for group in self.budget_groups
        )
        budget = sum(budget_configuration)
        availability = []
        for rule in self.rules:
            when_region = rule.get("when_region")
            if isinstance(when_region, (list, tuple)) and len(when_region) == 5:
                y0, x0, y1, x1 = (int(value) for value in when_region[:4])
                expected = tuple(when_region[4])
                observed = tuple(
                    state[row][col]
                    for row in range(y0, y1 + 1)
                    for col in range(x0, x1 + 1)
                    if 0 <= row < len(state) and 0 <= col < len(state[row])
                )
                availability.append((str(rule["id"]), observed == expected))
                continue
            if not bool(rule.get("one_time")):
                continue
            row, col, size = tuple(rule["bbox"])
            footprint = set(rule.get("footprint") or ())
            rendered = tuple(
                state[row + dy][col + dx]
                for dy in range(int(size)) for dx in range(int(size))
            )
            availability.append((str(rule["id"]), any(value in footprint for value in rendered)))
        return FiberFactors(
            controlled_base=bases,
            finite_configuration=configuration,
            presentation_assignment=presentation,
            operation_domain_assignment=tuple(operation_domains),
            ordered_budget=int(budget),
            one_shot_availability=tuple(availability),
            ordered_feasibility_configuration=budget_configuration,
        )

    def factor(self, state: Any) -> FiberFactors:
        frozen = state if isinstance(state, tuple) else _tuple_rows(state)
        return self._factor_cached(frozen)

    def clear_runtime_caches(self) -> None:
        """Release search-local state presentations between lifecycle legs."""
        self._factor_cached.cache_clear()

    def explain_state_difference(self, left: Any, right: Any) -> dict[str, Any]:
        """Bounded presentation witness for a failed consumer quotient."""
        changed = [
            {
                "coordinate": [row, col],
                "left": left[row][col],
                "right": right[row][col],
            }
            for row in range(min(len(left), len(right)))
            for col in range(min(len(left[row]), len(right[row])))
            if left[row][col] != right[row][col]
        ]
        left_factors = self.factor(left).as_mapping()
        right_factors = self.factor(right).as_mapping()
        return {
            "schema": "ztare-consumer-quotient-difference-v1",
            "changed_cell_count": len(changed),
            "changed_cells": changed[:64],
            "changed_factor_names": [
                name
                for name in self.factor_names
                if left_factors[name] != right_factors[name]
            ],
        }

    def problem_for(self, goal_edge: Any, start: Any):
        """Compile a target-specific problem from adapter-attested witnesses."""
        if (
            getattr(goal_edge, "target_kind", "")
            == "hypothesis_edge_version_space"
            and callable(
                getattr(goal_edge, "relation_projection_key", None)
            )
            and tuple(getattr(goal_edge, "operations", ()) or ())
            and self.in_domain(start)
        ):
            return CompiledFiberRelationalGoalProblem(
                projection=self,
                target=goal_edge,
            )
        witnesses = tuple(getattr(goal_edge, "witnesses", ()) or ())
        if not witnesses or not self.in_domain(start):
            return None
        eligible = [
            witness for witness in witnesses
            if len(witness) >= 4 and self.in_domain(witness[0])
        ]
        if not eligible:
            return None
        start_factor = self.factor(start)

        def rough_distance(witness) -> int:
            target = self.factor(witness[0])
            return _base_distance(
                start_factor.controlled_base,
                target.controlled_base,
                max(1, len(self.sprite)),
            )

        source, intervention, _time, evidence_ref, _source_epoch = min(
            eligible, key=rough_distance
        )
        return CompiledFiberSearchProblem(
            projection=self,
            target=self.factor(source),
            terminal_intervention=intervention,
            target_evidence_ref=str(evidence_ref),
            additional_evidence_refs=tuple(
                str(ref)
                for ref in (getattr(goal_edge, "evidence_refs", ()) or ())
                if str(ref)
            ),
        )

    def exact_relational_problem_for(self, goal_edge: Any, start: Any):
        """Withdraw a refuted quotient while preserving a relational target.

        Exact observation equality is a conservative consumer fallback for a
        carrier whose compiled factor equality failed the runtime commutation
        test.  It does not repair or promote that projection.
        """
        if (
            getattr(goal_edge, "target_kind", "")
            != "hypothesis_edge_version_space"
            or not callable(
                getattr(goal_edge, "relation_projection_key", None)
            )
            or not tuple(getattr(goal_edge, "operations", ()) or ())
            or not self.in_domain(start)
        ):
            return None
        return CompiledFiberExactRelationalGoalProblem(
            projection=self,
            target=goal_edge,
        )

    def operation_discrimination_problem(
        self,
        obligation: OperationRecurrenceAcquisitionObligation,
        start: Any,
        predict: Callable[[Any, Any, Any], Any],
    ) -> "CompiledFiberOperationDiscriminationProblem | None":
        """Compile a search for a new presentation of a conjectured trigger.

        The witnessed edge supplies orientation and an explicit exclusion.  A
        search result must fire the adapter-local trigger at a different
        source/intervention context; replaying the banked edge cannot satisfy
        the obligation.
        """

        base = self.problem_for(obligation, start)
        if base is None:
            return None
        return CompiledFiberOperationDiscriminationProblem(
            projection=self,
            target=base.target,
            terminal_intervention=base.terminal_intervention,
            target_evidence_ref=base.target_evidence_ref,
            additional_evidence_refs=obligation.evidence_refs,
            obligation=obligation,
            predict=predict,
        )

    @staticmethod
    def acquisition_key(factors: FiberFactors) -> tuple[Hashable, ...]:
        """Identity whose novelty can change the operation affordance set.

        Controlled position and exact domain offsets are transition coordinates,
        not new skills: counting their translation orbit made every ordinary
        move look like acquisition.  A new finite operation configuration or a
        changed one-shot availability can alter the executable affordance set.
        New domain selectors are acquired through the typed operation-
        discrimination obligation, where the trigger identity is explicit.
        """
        return (
            factors.finite_configuration,
            factors.one_shot_availability,
        )

    def acquisition_problem(
        self,
        *,
        start: Any,
        evidence_states: tuple[Any, ...],
        evidence_ref: str,
    ) -> "CompiledFiberAcquisitionProblem | None":
        if not self.in_domain(start):
            return None
        observed = {
            self.acquisition_key(self.factor(state))
            for state in (*evidence_states, start)
            if self.in_domain(state)
        }
        if not observed:
            return None
        return CompiledFiberAcquisitionProblem(
            projection=self,
            observed_keys=frozenset(observed),
            evidence_ref=evidence_ref,
        )

    def mechanism_acquisition_problem(
        self,
        *,
        start: Any,
        evidence_transitions: tuple[Any, ...],
        predict: Callable[[Any, Any, Any], Any],
        evidence_ref: str,
        boundary_predicate: Callable[[Any, Any, Any], bool] | None = None,
        boundary_edges: tuple[tuple[Any, ...], ...] = (),
        history_trajectories: tuple[Any, ...] = (),
        exhaustive_history_candidates: bool = False,
    ) -> "CompiledFiberMechanismAcquisitionProblem | None":
        """Seek a new context for an exceptional witnessed factor effect.

        This is the successor to exhausted state/configuration novelty.  The
        target is an operation effect transported through the factor relation,
        never a copied source coordinate.
        """
        if not self.in_domain(start) or not evidence_transitions:
            return None
        from ztare.worldmodel.mechanism_effects import (
            build_fiber_action_system,
            select_fiber_history_action_system,
        )

        history_lift = (
            select_fiber_history_action_system(
                evidence_transitions,
                projection=self,
                evidence_ref=evidence_ref,
                explicit_boundary_edges=boundary_edges,
                history_trajectories=history_trajectories,
                exhaustive_candidates=exhaustive_history_candidates,
            )
            if boundary_edges or history_trajectories
            else None
        )
        action_system = (
            history_lift.action_system
            if history_lift is not None
            else build_fiber_action_system(
                evidence_transitions,
                projection=self,
                evidence_ref=evidence_ref,
                boundary_predicate=boundary_predicate,
                explicit_boundary_edges=boundary_edges,
            )
        )
        if not action_system.passed_section:
            raise ValueError("witnessed partial-action section did not commute")
        ranked = tuple(
            row
            for row in action_system.ranked_effects(include_boundaries=False)
            if row.effect != (("identity",),)
        )
        if not ranked:
            return None
        return CompiledFiberMechanismAcquisitionProblem(
            projection=self,
            action_system=action_system,
            predict=predict,
            ranked_effects=ranked[:16],
            evidence_ref=evidence_ref,
            history_lift=history_lift,
        )

    def partial_operation_problem(
        self,
        *,
        start: Any,
        predict: Callable[[Any, Any, Any], Any],
    ) -> "CompiledFiberPartialOperationProblem | None":
        """Expose an admitted partial operation's undefined fibers to control.

        The compiler owns which abstract sources have witnessed images.  The
        live environment owns the missing consequence.  Search may therefore
        steer to an intervention for which the carrier returns ``None`` but may
        neither invent that image nor interpret it as task discharge.
        """
        if not self.in_domain(start):
            return None
        represented = {
            _partition_presentation(configuration)[0]
            for configuration in self.configurations
        }
        unresolved = represented - set(self._configuration_partition_next)
        if not unresolved:
            return None
        return CompiledFiberPartialOperationProblem(
            projection=self,
            unresolved_configurations=frozenset(unresolved),
            predict=predict,
        )

    def goal_problem(self, *, start: Any, target: Any):
        """Compose transition factors with a target-observation quotient."""
        if (
            not self.in_domain(start)
            or not callable(getattr(target, "projection_key", None))
            or not str(getattr(target, "identity_sha256", ""))
        ):
            return None
        return CompiledFiberGoalProblem(
            projection=self,
            target=target,
        )

    def goal_discrimination_problem(
        self,
        *,
        start: Any,
        target: Any,
        evidence_states: tuple[Any, ...],
    ):
        """Seek a target-relevant observation absent from current evidence."""
        problem = self.goal_problem(start=start, target=target)
        if problem is None:
            return None
        observed = frozenset(
            target.projection_key(state)
            for state in (*evidence_states, start)
            if self.in_domain(state)
        )
        return CompiledFiberGoalProblem(
            projection=self,
            target=target,
            observed_target_keys=observed,
        )

    def goal_experiment_problem(
        self,
        *,
        start: Any,
        target: Any,
        predict: Callable[[Any, Any, Any], Any],
        evidence_states: tuple[Any, ...] = (),
        time_translation_certificate: Any = None,
    ):
        if (
            not self.in_domain(start)
            or not callable(getattr(target, "experiment_edge_ids", None))
            or not tuple(getattr(target, "active_experiment_domain_ids", ()))
        ):
            return None
        return CompiledFiberGoalExperimentProblem(
            projection=self,
            target=target,
            predict=predict,
            observed_target_keys=frozenset(
                target.projection_key(state)
                for state in (*evidence_states, start)
                if self.in_domain(state)
            ),
            observed_acquisition_keys=frozenset(
                self.acquisition_key(self.factor(state))
                for state in (*evidence_states, start)
                if self.in_domain(state)
            ),
            time_translation_certificate=time_translation_certificate,
        )

    def receipt_payload(self) -> dict[str, Any]:
        return {
            "schema": "ztare-factored-planning-projection-v1",
            "projection_sha256": self.projection_sha256,
            "factor_names": list(self.factor_names),
            "terminal_factor_names": list(self.terminal_factor_names),
            "feasibility_factor_names": list(self.feasibility_factor_names),
            "availability_factor_names": list(self.availability_factor_names),
            "evidence_refs": list(self.evidence_refs),
            "authority": (
                "accepted carrier constants define the factorization; task adjudicator "
                "retains terminal authority"
            ),
        }


def _patch_refined_projection(
    projection: CompiledFiberProjection,
    patch_spec: Any,
) -> CompiledFiberProjection | None:
    """Transport a declarative finite-state delta into its search projection.

    A composed transition carrier and its control projection must describe the
    same operation graph.  Whole-content display machines refine the finite
    graph.  Translation-equivariant event patterns refine the operation-domain
    relation.  Other rules retain the pointwise factorizer as a proposal whose
    mergers are checked by the common search consumer.
    """
    if not isinstance(patch_spec, Mapping):
        return projection
    rules: list[Mapping[str, Any]] = []
    for bucket in dict(patch_spec.get("actions") or {}).values():
        if isinstance(bucket, (list, tuple)):
            rules.extend(rule for rule in bucket if isinstance(rule, Mapping))
    always = patch_spec.get("always")
    if isinstance(always, (list, tuple)):
        rules.extend(rule for rule in always if isinstance(rule, Mapping))

    display_set = set(projection.display_cells)
    refinements = []
    for rule in rules:
        if (
            rule.get("op") != "region_event"
            or rule.get("content_states") is None
            or rule.get("when_region") is not None
        ):
            continue
        region = rule.get("region")
        if not isinstance(region, (list, tuple)) or len(region) != 4:
            continue
        y0, x0, y1, x1 = (int(value) for value in region)
        region_cells = {
            (row, col)
            for row in range(y0, y1 + 1)
            for col in range(x0, x1 + 1)
        }
        if region_cells != display_set:
            continue
        configurations = tuple(
            tuple(state) for state in rule.get("content_states") or ()
        )
        transition = rule.get("state_transition", "cycle")
        pairs = (
            tuple((index, (index + 1) % len(configurations))
                  for index in range(len(configurations)))
            if transition == "cycle"
            else tuple((int(source), int(target)) for source, target in transition)
        )
        graph = {
            configurations[source]: configurations[target]
            for source, target in pairs
        }
        refinements.append((rule, configurations, graph))
    domain_markers = []
    for rule in rules:
        if rule.get("op") != "region_event":
            continue
        marker = {
            "id": "operation_domain_" + stable_sha256(rule)[:16],
            "type": "operation_domain",
        }
        if isinstance(rule.get("trigger_pattern"), Mapping):
            marker["trigger_pattern"] = dict(rule["trigger_pattern"])
        elif isinstance(rule.get("rect"), (list, tuple)):
            marker["rect"] = tuple(int(value) for value in rule["rect"])
        else:
            continue
        domain_markers.append(marker)
    # A declarative patch does not erase the pointwise factorizer.  Recognized
    # display-state refinements update its finite graph below; other operations
    # retain the inherited projection as a runtime-checked proposal.  The
    # factored search consumer checks commutation/forward simulation at merges.
    if not refinements and not domain_markers:
        return projection
    configurations = projection.configurations
    graph = projection.configuration_next
    markers = list(domain_markers)
    signatures = {stable_sha256(rule) for rule in rules}
    if refinements:
        refinement_signatures = {
            stable_sha256({"configurations": states, "graph": edges})
            for _rule, states, edges in refinements
        }
        if len(refinement_signatures) != 1:
            raise ValueError("patch delta declares conflicting display transition graphs")
        rule, configurations, graph = refinements[0]
        rect = tuple(int(value) for value in rule["rect"])
        markers.append({
            "id": "partial_operation_" + stable_sha256(rule)[:16],
            "bbox": (rect[0], rect[1], max(rect[2] - rect[0] + 1,
                                            rect[3] - rect[1] + 1)),
            "type": "finite_state_transition",
            "one_time": False,
            "footprint": tuple(int(value) for value in rule.get("mover_colors") or ()),
            "delta": 0,
            "reset_value": 0,
            "witness_rows": (),
            "underlay": None,
        })
    evidence_ref = "compiled_carrier:patch_delta_spec:" + stable_sha256(
        sorted(signatures)
    )
    return CompiledFiberProjection(
        sprite=projection.sprite,
        display_cells=projection.display_cells,
        configurations=configurations,
        configuration_next=graph,
        budget_groups=projection.budget_groups,
        budget_live_value=projection.budget_live_value,
        rules=tuple((*projection.rules, *markers)),
        domain_predicate=projection.domain_predicate,
        evidence_refs=tuple(dict.fromkeys((*projection.evidence_refs, evidence_ref))),
    )


def _base_distance(
    bases: tuple[tuple[int, int], ...],
    targets: tuple[tuple[int, int], ...] | tuple[tuple[int, int]],
    scale: int,
) -> int:
    if not bases or not targets:
        return 0 if bases == targets else 64
    return min(
        (abs(row - target_row) + abs(col - target_col)) // max(1, scale)
        for row, col in bases for target_row, target_col in targets
    )


class CompiledFiberSearchProblem:
    """Target-specific consumer projection; common search sees opaque keys."""

    factor_names = CompiledFiberProjection.factor_names
    terminal_factor_names = CompiledFiberProjection.terminal_factor_names
    feasibility_factor_names = CompiledFiberProjection.feasibility_factor_names
    availability_factor_names = CompiledFiberProjection.availability_factor_names

    def __init__(
        self,
        *,
        projection: CompiledFiberProjection,
        target: FiberFactors,
        terminal_intervention: Any,
        target_evidence_ref: str,
        additional_evidence_refs: tuple[str, ...] = (),
    ) -> None:
        self.projection = projection
        self.projection_sha256 = projection.projection_sha256
        self.target = target
        self.terminal_intervention = terminal_intervention
        self.target_evidence_ref = str(target_evidence_ref)
        self.evidence_refs = tuple(dict.fromkeys((
            *projection.evidence_refs,
            target_evidence_ref,
            *additional_evidence_refs,
        )))
        self.problem_id = stable_sha256({
            "projection_sha256": self.projection_sha256,
            "target_terminal_key": self._terminal_key(target),
            "terminal_intervention": terminal_intervention,
            "target_evidence_ref": target_evidence_ref,
            "additional_evidence_refs": additional_evidence_refs,
        })
        self._configuration_landmarks = tuple(
            tuple(rule["bbox"][:2])
            for rule in projection.rules
            if rule.get("type") == "rotation_increment"
        )
        self._renewal_landmarks = {
            str(rule["id"]): tuple(rule["bbox"][:2])
            for rule in projection.rules
            if rule.get("type") == "timer_reset" and rule.get("one_time")
        }

    @staticmethod
    def _terminal_key(factors: FiberFactors) -> tuple[Hashable, Hashable]:
        return factors.controlled_base, factors.finite_configuration

    def dominance_key(self, state: Any) -> Hashable:
        factors = self.projection.factor(state)
        return (
            factors.controlled_base,
            factors.finite_configuration,
            factors.presentation_assignment,
            factors.operation_domain_assignment,
            factors.ordered_feasibility_configuration,
            factors.one_shot_availability,
        )

    def dominance_vector(self, state: Any) -> tuple[int, ...]:
        return (self.projection.factor(state).ordered_budget,)

    def admissible(self, state: Any) -> bool:
        # Zero resource may be a recoverable mechanism state: an admitted
        # successor can renew it.  Feasibility belongs to transition structure,
        # while the terminal edge keeps its stricter positive-budget contract.
        return self.projection.in_domain(state)

    def goal_edge(self, state: Any, intervention: Any, _time: Any) -> bool:
        factors = self.projection.factor(state)
        return (
            intervention == self.terminal_intervention
            and factors.ordered_budget > 0
            and self._terminal_key(factors) == self._terminal_key(self.target)
        )

    def _configuration_distance(self, current: tuple[Any, ...]) -> int:
        if current == self.target.finite_configuration:
            return 0
        seen = set()
        steps = 0
        while (
            current not in seen
            and current in self.projection._configuration_partition_next
        ):
            seen.add(current)
            current = self.projection._configuration_partition_next[current]
            steps += 1
            if current == self.target.finite_configuration:
                return steps
        return 1

    def estimate(self, state: Any) -> int:
        factors = self.projection.factor(state)
        scale = max(1, len(self.projection.sprite))
        configuration_steps = self._configuration_distance(
            factors.finite_configuration
        )
        if configuration_steps:
            milestone = _base_distance(
                factors.controlled_base,
                self._configuration_landmarks,
                scale,
            ) + configuration_steps
        else:
            milestone = _base_distance(
                factors.controlled_base,
                self.target.controlled_base,
                scale,
            )
        availability = dict(factors.one_shot_availability)
        renewals = tuple(
            position
            for identity, position in self._renewal_landmarks.items()
            if availability.get(identity)
        )
        if renewals and factors.ordered_budget <= milestone + 1:
            return _base_distance(factors.controlled_base, renewals, scale)
        return milestone


class CompiledFiberRelationalGoalProblem:
    """Search for an active task relation without importing a target state.

    The carrier projection supplies coordinates sufficient to predict state
    evolution.  The task hypothesis supplies a second, consumer-indexed
    coordinate: the truth vector of every nominated ``(state, operation)``
    relation.  Including that vector in dominance equality prevents a search
    from merging two carrier-equivalent presentations when only one admits a
    candidate completion edge.
    """

    factor_names = (*CompiledFiberProjection.factor_names, "task_relation")
    terminal_factor_names = ("task_relation",)
    feasibility_factor_names = CompiledFiberProjection.feasibility_factor_names
    availability_factor_names = CompiledFiberProjection.availability_factor_names

    def __init__(
        self,
        *,
        projection: CompiledFiberProjection,
        target: Any,
    ) -> None:
        operations = tuple(getattr(target, "operations", ()) or ())
        relation_projection_key = getattr(target, "relation_projection_key", None)
        if not operations or not callable(relation_projection_key):
            raise ValueError(
                "relational fiber goal requires operations and a projection key"
            )
        self.projection = projection
        self.projection_sha256 = projection.projection_sha256
        self.target = target
        self.operations = operations
        self.evidence_refs = tuple(dict.fromkeys((
            *projection.evidence_refs,
            *(str(ref) for ref in (getattr(target, "evidence_refs", ()) or ())),
        )))
        self.problem_id = stable_sha256({
            "schema": "ztare-compiled-fiber-relational-goal-problem-v1",
            "projection_sha256": self.projection_sha256,
            "target_identity_sha256": str(
                getattr(target, "identity_sha256", "")
            ),
            "operations": list(map(repr, operations)),
            "factor_names": self.factor_names,
            "terminal_factor_names": self.terminal_factor_names,
            "feasibility_factor_names": self.feasibility_factor_names,
            "availability_factor_names": self.availability_factor_names,
            "evidence_refs": self.evidence_refs,
        })

    def _dominance_key(self, state: Any, time_value: Any) -> Hashable:
        factors = self.projection.factor(state)
        return (
            factors.controlled_base,
            factors.finite_configuration,
            factors.presentation_assignment,
            factors.operation_domain_assignment,
            factors.ordered_feasibility_configuration,
            factors.one_shot_availability,
            self.target.relation_projection_key(state, time_value),
        )

    def dominance_key(self, state: Any) -> Hashable:
        return self._dominance_key(state, None)

    def dominance_key_at(self, state: Any, time_value: Any) -> Hashable:
        # Until transition and task-relation time translations are jointly
        # certified, retain the clock coordinate.
        return self._dominance_key(state, time_value), ("time", time_value)

    def dominance_vector(self, state: Any) -> tuple[int, ...]:
        return (self.projection.factor(state).ordered_budget,)

    def admissible(self, state: Any) -> bool:
        return self.projection.in_domain(state)

    def goal_edge(
        self,
        state: Any,
        intervention: Any,
        time_value: Any,
    ) -> bool:
        return (
            intervention in self.operations
            and self.projection.factor(state).ordered_budget > 0
            and bool(self.target(state, intervention, time_value))
        )

    @staticmethod
    def state_target(_state: Any) -> bool:
        return False

    @staticmethod
    def estimate(_state: Any) -> int:
        # No target-state metric is licensed by a relation-valued contract.
        return 0

    def explain_state_difference(
        self,
        left: Any,
        right: Any,
    ) -> dict[str, Any]:
        receipt = self.projection.explain_state_difference(left, right)
        try:
            receipt["task_relation_changed"] = (
                self.target.relation_projection_key(left, None)
                != self.target.relation_projection_key(right, None)
            )
        except Exception as exc:  # noqa: BLE001
            receipt["task_relation_diagnostic_error"] = type(exc).__name__
        return receipt


class CompiledFiberExactRelationalGoalProblem(
    CompiledFiberRelationalGoalProblem
):
    """Conservative relational search after factor equality is refuted."""

    exact_transition_identity = True
    factor_names = ("exact_observation", "task_relation")
    terminal_factor_names = ("task_relation",)
    feasibility_factor_names: tuple[str, ...] = ()
    availability_factor_names: tuple[str, ...] = ()

    def __init__(
        self,
        *,
        projection: CompiledFiberProjection,
        target: Any,
    ) -> None:
        super().__init__(projection=projection, target=target)
        self.problem_id = stable_sha256({
            "schema": "ztare-compiled-fiber-exact-relational-goal-problem-v1",
            "refuted_factored_problem_id": self.problem_id,
            "projection_sha256": self.projection_sha256,
            "target_identity_sha256": str(
                getattr(target, "identity_sha256", "")
            ),
            "operations": list(map(repr, self.operations)),
            "factor_names": self.factor_names,
            "terminal_factor_names": self.terminal_factor_names,
            "evidence_refs": self.evidence_refs,
        })

    @staticmethod
    def _exact_observation_key(state: Any) -> Hashable:
        return ("content_sha256", stable_sha256(state))

    def _dominance_key(self, state: Any, time_value: Any) -> Hashable:
        # For a fixed target identity, relation truth is a derived coordinate
        # of exact state, operation, and time. It remains the terminal factor
        # evaluated by ``goal_edge``; repeating it in transition equality would
        # add work but no distinction.
        return self._exact_observation_key(state)

    def dominance_vector(
        self,
        _state: Any,
    ) -> tuple[int | float, ...]:
        return ()

    def dominance_key_at(self, state: Any, time_value: Any) -> Hashable:
        return self._dominance_key(state, time_value), ("time", time_value)


class CompiledFiberOperationDiscriminationProblem(CompiledFiberSearchProblem):
    """Seek a conjectured operation trigger outside its witnessed context."""

    terminal_factor_names: tuple[str, ...] = ()

    def __init__(
        self,
        *,
        projection: CompiledFiberProjection,
        target: FiberFactors,
        terminal_intervention: Any,
        target_evidence_ref: str,
        additional_evidence_refs: tuple[str, ...],
        obligation: OperationRecurrenceAcquisitionObligation,
        predict: Callable[[Any, Any, Any], Any],
    ) -> None:
        super().__init__(
            projection=projection,
            target=target,
            terminal_intervention=terminal_intervention,
            target_evidence_ref=target_evidence_ref,
            additional_evidence_refs=additional_evidence_refs,
        )
        self.obligation = obligation
        self._predict = predict
        self._prediction_cache: dict[Hashable, Any] = {}
        self.problem_id = stable_sha256({
            "base_problem_id": self.problem_id,
            "objective": "distinct_operation_trigger_context",
            "behavioral_identity_factors": ("ordered_budget",),
            "obligation_sha256": obligation.obligation_sha256,
            "operation_identity_sha256": obligation.operation_identity_sha256,
            "trigger_lowering_sha256": obligation.trigger_lowering_sha256,
            "known_contexts": sorted(
                (stable_sha256(source), repr(intervention))
                for source, intervention, _time_value, _ref, _epoch
                in obligation.witnesses
            ),
        })

    feasibility_factor_names: tuple[str, ...] = ()

    def dominance_key(self, state: Any) -> Hashable:
        """Equality for factors that can change the target operation's image."""
        factors = self.projection.factor(state)
        return (
            factors.controlled_base,
            factors.finite_configuration,
            factors.presentation_assignment,
            factors.operation_domain_assignment,
            factors.ordered_feasibility_configuration,
            factors.ordered_budget,
            factors.one_shot_availability,
        )

    def dominance_vector(self, _state: Any) -> tuple[int | float, ...]:
        # The parent consumer may order remaining budget for terminal pursuit.
        # Here it changes operation availability, so no ordered pruning remains.
        return ()

    def dominance_key_at(self, state: Any, time_value: Any) -> Hashable:
        # No time-translation certificate is attached to this carrier.
        return self.dominance_key(state), time_value

    def predict(self, state: Any, intervention: Any, time_value: Any) -> Any:
        key = _prediction_key(state, intervention, time_value)
        if key not in self._prediction_cache:
            self._prediction_cache[key] = self._predict(
                state,
                intervention,
                time_value,
            )
        return self._prediction_cache[key]

    def goal_edge(self, state: Any, intervention: Any, time_value: Any) -> bool:
        successor = self.predict(state, intervention, time_value)
        return successor is not None and self.obligation.accepts_edge(
            state,
            intervention,
            time_value,
            successor,
        )


class CompiledFiberAcquisitionProblem:
    """Current-lifecycle factor novelty with no imported terminal target."""

    factor_names = CompiledFiberProjection.factor_names
    terminal_factor_names: tuple[str, ...] = ()
    feasibility_factor_names = CompiledFiberProjection.feasibility_factor_names
    availability_factor_names = CompiledFiberProjection.availability_factor_names

    def __init__(
        self,
        *,
        projection: CompiledFiberProjection,
        observed_keys: frozenset[Hashable],
        evidence_ref: str,
    ) -> None:
        self.projection = projection
        self.projection_sha256 = projection.projection_sha256
        self.observed_keys = observed_keys
        self.evidence_refs = tuple(
            dict.fromkeys((*projection.evidence_refs, str(evidence_ref)))
        )
        self.problem_id = stable_sha256({
            "projection_sha256": self.projection_sha256,
            "objective": "novel_operation_affordance_identity",
            "observed_key_sha256s": sorted(
                stable_sha256(key) for key in observed_keys
            ),
            "evidence_ref": str(evidence_ref),
        })

    def dominance_key(self, state: Any) -> Hashable:
        factors = self.projection.factor(state)
        return (
            factors.controlled_base,
            factors.finite_configuration,
            factors.presentation_assignment,
            factors.operation_domain_assignment,
            factors.ordered_feasibility_configuration,
            factors.one_shot_availability,
        )

    def dominance_vector(self, state: Any) -> tuple[int, ...]:
        return (self.projection.factor(state).ordered_budget,)

    def admissible(self, state: Any) -> bool:
        factors = self.projection.factor(state)
        return self.projection.in_domain(state) and factors.ordered_budget > 0

    def goal_edge(self, _state: Any, _intervention: Any, _time: Any) -> bool:
        return False

    def state_target(self, state: Any) -> bool:
        factors = self.projection.factor(state)
        return self.projection.acquisition_key(factors) not in self.observed_keys

    def estimate(self, _state: Any) -> int:
        return 0


class CompiledFiberMechanismAcquisitionProblem:
    """Transport an exceptional operation effect to a new witnessed context."""

    factor_names = CompiledFiberProjection.factor_names
    terminal_factor_names: tuple[str, ...] = ()
    feasibility_factor_names = CompiledFiberProjection.feasibility_factor_names
    availability_factor_names = CompiledFiberProjection.availability_factor_names

    def __init__(
        self,
        *,
        projection: CompiledFiberProjection,
        action_system: Any,
        predict: Callable[[Any, Any, Any], Any],
        ranked_effects: tuple[Any, ...],
        evidence_ref: str,
        history_lift: Any = None,
    ) -> None:
        self.projection = projection
        self.projection_sha256 = projection.projection_sha256
        self.action_system = action_system
        self.history_lift = history_lift
        self.history_suffix_length = int(
            getattr(history_lift, "suffix_length", 0) or 0
        )
        self._predict = predict
        self._prediction_cache: dict[Hashable, Any] = {}
        self.target_effect_classes = frozenset(
            row.class_key for row in ranked_effects
        )
        self.observed_effect_classes = frozenset(
            action_system.effect_support
        )
        self.known_sources = {
            key: frozenset(value)
            for key, value in action_system.effect_sources.items()
        }
        self.evidence_refs = tuple(dict.fromkeys((
            *projection.evidence_refs,
            str(evidence_ref),
            *(
                ref
                for row in ranked_effects
                for ref in row.evidence_refs
            ),
        )))
        self.problem_id = stable_sha256({
            "projection_sha256": self.projection_sha256,
            "objective": "exceptional_mechanism_transport",
            "partial_action_system_sha256": action_system.sha256,
            "target_effect_classes": sorted(
                stable_sha256(value)
                for value in self.target_effect_classes
            ),
            "evidence_ref": str(evidence_ref),
            "history_lift": (
                history_lift.to_receipt()
                if history_lift is not None
                else None
            ),
        })

    def observed_start_key(
        self,
        state: Any,
        action_history: Iterable[Hashable] = (),
        operation_effect_history: Iterable[Hashable] = (),
    ) -> Hashable:
        factors = self.projection.factor(state)
        if self.history_lift is not None:
            return self.history_lift.start_key(
                factors,
                observation=state,
                action_history=action_history,
                operation_effect_history=operation_effect_history,
            )
        from ztare.worldmodel.mechanism_effects import fiber_transition_key

        return fiber_transition_key(factors)

    def acquisition_context_key(self, source_key: Hashable) -> Hashable:
        """Context identity for a witnessed control source.

        The partial-action system owns the concrete section. The projection's
        acquisition key owns which factor changes can alter the affordance
        set. Quotient class identifiers and evidence support are absent.
        """
        representative = self.action_system.representative(source_key)
        observation = getattr(
            representative,
            "observation",
            representative,
        )
        key: tuple[Hashable, ...] = (
            self.projection.acquisition_key(
                self.projection.factor(observation)
            ),
        )
        if self.history_lift is not None:
            key = (
                *key,
                self.history_lift.predictive_context_key(observation),
            )
        return key

    def acquisition_support_key(self, source_key: Hashable) -> Hashable:
        """Evidence-admission identity beneath a history-lifted control node."""
        representative = self.action_system.representative(source_key)
        observation = getattr(
            representative,
            "observation",
            representative,
        )
        return stable_sha256(observation)

    def source_lineage_keys(
        self,
        source_key: Hashable,
    ) -> tuple[Hashable, ...]:
        if self.history_lift is None:
            return (source_key,)
        return self.history_lift.source_lineage_keys(source_key)

    def dominance_key(self, state: Any) -> Hashable:
        factors = self.projection.factor(state)
        # Mechanism discovery may depend on any admitted factor.  No factor is
        # ordered away until the effect relation certifies that erasure.
        return tuple(
            factors.as_mapping()[name]
            for name in self.factor_names
        )

    def dominance_key_at(self, state: Any, time_value: Any) -> Hashable:
        # Clock transport has separate certificate authority.
        return self.dominance_key(state), time_value

    def dominance_vector(self, _state: Any) -> tuple[int | float, ...]:
        return ()

    def admissible(self, state: Any) -> bool:
        factors = self.projection.factor(state)
        return self.projection.in_domain(state) and factors.ordered_budget > 0

    def predict(self, state: Any, intervention: Any, time_value: Any) -> Any:
        key = _prediction_key(state, intervention, time_value)
        if key not in self._prediction_cache:
            self._prediction_cache[key] = self._predict(
                state,
                intervention,
                time_value,
            )
        return self._prediction_cache[key]

    def goal_edge(self, state: Any, intervention: Any, time_value: Any) -> bool:
        if self.history_suffix_length:
            # Simulated search does not carry an action-history state.  The
            # witnessed relation owns control for a lifted problem.
            return False
        successor = self.predict(state, intervention, time_value)
        if successor is None or not self.admissible(successor):
            return False
        from ztare.worldmodel.mechanism_effects import (
            fiber_mechanism_effect,
            fiber_transition_key,
        )

        source_factors = self.projection.factor(state)
        target_factors = self.projection.factor(successor)
        effect = fiber_mechanism_effect(source_factors, target_factors)
        if effect == (("identity",),):
            return False
        effect_class = (intervention, effect)
        if effect_class not in self.observed_effect_classes:
            return True
        return (
            effect_class in self.target_effect_classes
            and fiber_transition_key(source_factors)
            not in self.known_sources.get(effect_class, ())
        )

    def estimate(self, _state: Any) -> int:
        return 0


class CompiledFiberGoalProblem:
    """Consumer-indexed quotient for one executable goal version space."""

    factor_names = CompiledFiberProjection.factor_names
    terminal_factor_names = ("target_observation",)
    feasibility_factor_names = CompiledFiberProjection.feasibility_factor_names
    availability_factor_names = CompiledFiberProjection.availability_factor_names

    def __init__(
        self,
        *,
        projection: CompiledFiberProjection,
        target: Any,
        observed_target_keys: frozenset[Hashable] | None = None,
    ) -> None:
        self.projection = projection
        self.projection_sha256 = projection.projection_sha256
        self.target = target
        self.observed_target_keys = observed_target_keys
        self.evidence_refs = projection.evidence_refs
        self.problem_id = stable_sha256({
            "projection_sha256": self.projection_sha256,
            "objective": (
                "goal_observation_acquisition"
                if observed_target_keys is not None
                else "goal_version_space"
            ),
            "target_identity": target.identity_sha256,
            "observed_target_keys": sorted(
                stable_sha256(key) for key in (observed_target_keys or ())
            ),
        })

    def dominance_key(self, state: Any) -> Hashable:
        factors = self.projection.factor(state)
        return (
            factors.controlled_base,
            factors.finite_configuration,
            factors.presentation_assignment,
            factors.operation_domain_assignment,
            factors.ordered_feasibility_configuration,
            factors.ordered_budget,
            factors.one_shot_availability,
            self.target.projection_key(state),
        )

    def dominance_vector(self, _state: Any) -> tuple[int | float, ...]:
        # The commutation checker showed that budget changes successor identity
        # for this consumer, so it belongs in equality rather than dominance.
        return ()

    def dominance_key_at(self, state: Any, time_value: Any) -> Hashable:
        # Time stays in the consumer identity until this carrier has an
        # explicit time-translation equivariance certificate.
        return self.dominance_key(state), time_value

    def admissible(self, state: Any) -> bool:
        factors = self.projection.factor(state)
        return self.projection.in_domain(state) and factors.ordered_budget > 0

    def goal_edge(self, _state: Any, _intervention: Any, _time: Any) -> bool:
        return False

    def state_target(self, state: Any) -> bool:
        if self.observed_target_keys is not None:
            return self.target.projection_key(state) not in self.observed_target_keys
        return bool(self.target(state))

    def estimate(self, _state: Any) -> int:
        return 0


class CompiledFiberGoalExperimentProblem(CompiledFiberGoalProblem):
    """Seek an edge firing an operation already bound to a goal hypothesis."""

    def __init__(
        self,
        *,
        projection,
        target,
        predict,
        observed_target_keys: frozenset[Hashable],
        observed_acquisition_keys: frozenset[Hashable] | None = None,
        time_translation_certificate: Any = None,
    ) -> None:
        super().__init__(projection=projection, target=target)
        self._predict = predict
        self._prediction_cache: dict[Hashable, Any] = {}
        self.observed_target_keys = observed_target_keys
        self.observed_acquisition_keys = observed_acquisition_keys
        self.time_translation_certificate = (
            time_translation_certificate
            if bool(getattr(time_translation_certificate, "passed", False))
            else None
        )
        self.problem_id = stable_sha256({
            "base_problem_id": self.problem_id,
            "objective": "goal_hypothesis_experiment_edge",
            "experiment_domains": target.active_experiment_domain_ids,
            "observed_target_keys": sorted(
                stable_sha256(key) for key in observed_target_keys
            ),
            "observed_acquisition_keys": sorted(
                stable_sha256(key)
                for key in (observed_acquisition_keys or ())
            ),
            "time_translation_certificate_sha256": (
                stable_sha256(self.time_translation_certificate.to_dict())
                if self.time_translation_certificate is not None
                else ""
            ),
        })

    def predict(self, state: Any, intervention: Any, time_value: Any) -> Any:
        key = _prediction_key(state, intervention, time_value)
        if key not in self._prediction_cache:
            self._prediction_cache[key] = self._predict(
                state, intervention, time_value
            )
        return self._prediction_cache[key]

    def goal_edge(self, state: Any, intervention: Any, time_value: Any) -> bool:
        successor = self.predict(state, intervention, time_value)
        return bool(
            successor is not None
            and self.target.experiment_edge_ids(state, successor)
            and self.target.projection_key(successor)
            not in self.observed_target_keys
        )

    def state_target(self, _state: Any) -> bool:
        return (
            bool(self.target(_state))
            or self.target.projection_key(_state)
            not in self.observed_target_keys
        )

    def continuation_admissible(
        self,
        state: Any,
        _path: tuple[Any, ...],
    ) -> bool:
        """Do not replay a bounded frontier with no new affordance identity."""
        if self.observed_acquisition_keys is None:
            return True
        return self.projection.acquisition_key(
            self.projection.factor(state)
        ) not in self.observed_acquisition_keys

    def dominance_key_at(self, state: Any, time_value: Any) -> Hashable:
        if self.time_translation_certificate is not None:
            return self.dominance_key(state)
        return super().dominance_key_at(state, time_value)

    def estimate(self, state: Any) -> int:
        domains = dict(self.projection.factor(state).operation_domain_assignment)
        offsets = [
            offset
            for identity in self.target.active_experiment_domain_ids
            for offset in domains.get(identity, ())
        ]
        scale = max(1, len(self.projection.sprite))
        return min(
            (abs(row) + abs(col)) // scale
            for row, col in offsets
        ) if offsets else 0


class CompiledFiberPartialOperationProblem:
    """Seek one executable edge whose admitted transition image is undefined."""

    factor_names = CompiledFiberProjection.factor_names
    terminal_factor_names: tuple[str, ...] = ()
    feasibility_factor_names: tuple[str, ...] = ()
    availability_factor_names = CompiledFiberProjection.availability_factor_names

    def __init__(
        self,
        *,
        projection: CompiledFiberProjection,
        unresolved_configurations: frozenset[Hashable],
        predict: Callable[[Any, Any, Any], Any],
    ) -> None:
        self.projection = projection
        self.projection_sha256 = projection.projection_sha256
        self.unresolved_configurations = unresolved_configurations
        self.evidence_refs = projection.evidence_refs
        self._predict = predict
        self._prediction_cache: dict[Hashable, Any] = {}
        self._landmarks = tuple(
            tuple(rule["bbox"][:2])
            for rule in getattr(projection, "rules", ())
            if rule.get("type") == "finite_state_transition"
        )
        self.problem_id = stable_sha256({
            "projection_sha256": self.projection_sha256,
            "objective": "undefined_transition_image",
            "unresolved_configurations": sorted(
                stable_sha256(value) for value in unresolved_configurations
            ),
        })

    def dominance_key(self, state: Any) -> Hashable:
        factors = self.projection.factor(state)
        # No coordinate may be erased while searching for an edge on which the
        # current transition program explicitly has no image.
        return tuple(factors.as_mapping()[name] for name in self.factor_names)

    def dominance_vector(self, _state: Any) -> tuple[int | float, ...]:
        return ()

    def admissible(self, state: Any) -> bool:
        factors = self.projection.factor(state)
        return self.projection.in_domain(state) and factors.ordered_budget > 0

    def predict(self, state: Any, intervention: Any, time_value: Any) -> Any:
        key = _prediction_key(state, intervention, time_value)
        if key not in self._prediction_cache:
            self._prediction_cache[key] = self._predict(
                state, intervention, time_value
            )
        return self._prediction_cache[key]

    def goal_edge(self, state: Any, intervention: Any, time_value: Any) -> bool:
        factors = self.projection.factor(state)
        return (
            factors.finite_configuration in self.unresolved_configurations
            and self.predict(state, intervention, time_value) is None
        )

    def estimate(self, state: Any) -> int:
        factors = self.projection.factor(state)
        current = factors.finite_configuration
        steps = 0
        seen = set()
        while (
            current not in self.unresolved_configurations
            and current not in seen
            and current in self.projection._configuration_partition_next
        ):
            seen.add(current)
            current = self.projection._configuration_partition_next[current]
            steps += 1
        if current not in self.unresolved_configurations:
            steps += 1
        return steps + _base_distance(
            factors.controlled_base,
            self._landmarks,
            max(1, len(self.projection.sprite)),
        )


def projection_from_namespace(
    namespace: Mapping[str, Any],
    *,
    project_dir: str | Path | None = None,
) -> CompiledFiberProjection | None:
    """Return a projection only for the accepted rendered-effect ABI."""
    if not _REQUIRED_NAMESPACE_KEYS.issubset(namespace):
        return None
    domain = namespace.get("_world_matches")
    if not callable(domain):
        return None
    project = Path(project_dir).resolve() if project_dir is not None else None
    refs = ["compiled_carrier:effect_compiler_constants"]
    if project is not None:
        for relative in (
            "raw/episodes/episode_001.jsonl",
            "workspace/latest_fiber_effect_table.json",
        ):
            if (project / relative).is_file():
                refs.append(relative)
    return CompiledFiberProjection(
        sprite=_tuple_rows(namespace["SPRITE_RENDERING"]),
        display_cells=tuple(tuple(map(int, cell)) for cell in namespace["DISPLAY_CELLS"]),
        configurations=tuple(tuple(row) for row in namespace["ROTATION_RENDERINGS"]),
        configuration_next={
            tuple(key): tuple(value)
            for key, value in dict(namespace["ROTATION_NEXT"]).items()
        },
        budget_groups=tuple(
            tuple(tuple(map(int, cell)) for cell in group)
            for group in namespace["TIMER_GROUPS"]
        ),
        budget_live_value=namespace["TIMER_TICK_VALUE"],
        rules=tuple(dict(rule) for rule in namespace["OBJECT_RULES"]),
        domain_predicate=domain,
        evidence_refs=tuple(refs),
    )


def attach_compiled_projection(
    program: Any,
    namespace: Mapping[str, Any],
    *,
    project_dir: str | Path | None = None,
) -> Any:
    """Single attachment door shared by gates, caches, and live loading."""
    if not callable(program):
        return program
    declared_projection = projection_from_namespace(
        namespace,
        project_dir=project_dir,
    )
    projection = declared_projection
    if projection is None:
        projection = getattr(program, "_ztare_factored_projection", None)
    if projection is not None:
        patch_specs = []
        if namespace.get("PATCH_DELTA_SPEC") is not None:
            patch_specs.append(namespace["PATCH_DELTA_SPEC"])
        if isinstance(namespace.get("_PATCH_DELTA_SPECS"), (list, tuple)):
            patch_specs.extend(namespace["_PATCH_DELTA_SPECS"])
        # An opaque delta cannot certify a refined quotient, but it also cannot
        # erase the base factorizer.  Keep the inherited projection as a
        # runtime-checked proposal: concrete state-target search uses only its
        # pointwise feasibility coordinate, while quotienting consumers retain
        # the search_factored commutation/forward-simulation guard.
        for patch_spec in patch_specs:
            projection = _patch_refined_projection(projection, patch_spec)
        setattr(program, "_ztare_factored_projection", projection)
    return program


def append_projection_receipt(
    receipts_dir: str | Path,
    *,
    projection: CompiledFiberProjection,
    event: str,
    problem: CompiledFiberSearchProblem | CompiledFiberAcquisitionProblem | None = None,
    search_result: Any | None = None,
) -> Path:
    """Append compile/first-fire evidence without exposing an action route."""
    from ztare.common.schema_routes import assert_schema_route

    route = assert_schema_route(
        "ztare-factored-planning-projection-v1", category="operational_carrier"
    )
    row = {
        **projection.receipt_payload(),
        "route_id": route.route_id,
        "event": str(event),
    }
    if problem is not None:
        row.update({
            "problem_id": problem.problem_id,
            "problem_evidence_refs": list(problem.evidence_refs),
        })
        action_system = getattr(problem, "action_system", None)
        if action_system is not None:
            row["partial_action_system"] = action_system.to_receipt(rank_cap=20)
            row["partial_action_system_sha256"] = action_system.sha256
    if search_result is not None:
        row["search"] = {
            "status": search_result.status,
            "generated": int(search_result.generated),
            "expanded": int(search_result.expanded),
            "deepest_depth": int(search_result.deepest_depth),
            "projection_counterexample": dict(search_result.projection_counterexample),
            "continuation_length": len(search_result.continuation_actions),
        }
    path = Path(receipts_dir) / "factored_planning_projection.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    return path


__all__ = [
    "CompiledFiberProjection",
    "CompiledFiberAcquisitionProblem",
    "CompiledFiberMechanismAcquisitionProblem",
    "CompiledFiberPartialOperationProblem",
    "CompiledFiberOperationDiscriminationProblem",
    "CompiledFiberSearchProblem",
    "FiberFactors",
    "OperationRecurrenceAcquisitionObligation",
    "append_projection_receipt",
    "attach_compiled_projection",
    "operation_recurrence_acquisition_obligation",
    "projection_from_namespace",
]
