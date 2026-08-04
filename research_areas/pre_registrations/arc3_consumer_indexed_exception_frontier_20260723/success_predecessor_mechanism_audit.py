#!/usr/bin/env python3
"""Hold out a rewarded option section under mechanism-event transport."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.mechanism_effects import fiber_mechanism_effect


@dataclass(frozen=True)
class EventWitness:
    event: tuple[Any, ...]
    operation: Any
    bank_row: int
    time: int
    evidence_ref: str


def _sign(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return (number > 0) - (number < 0)


def _continuous(left: Any, right: Any) -> bool:
    return bool(
        left.s_next == right.s
        and getattr(left, "t", None) is not None
        and getattr(right, "t", None) is not None
        and int(right.t) == int(left.t) + 1
    )


def _boundary_section(
    rows: tuple[Any, ...],
    boundary_index: int,
) -> tuple[tuple[int, Any], ...]:
    start = boundary_index
    while start > 0:
        prior = rows[start - 1]
        current = rows[start]
        prior_identity = getattr(prior, "identity", None)
        if (
            prior_identity is not None
            and prior_identity.is_authoritative
            and prior_identity.is_boundary
        ):
            break
        if not _continuous(prior, current):
            break
        start -= 1
    return tuple((index, rows[index]) for index in range(start, boundary_index + 1))


def _availability_directions(changes: Iterable[Any]) -> tuple[str, ...]:
    directions = []
    for change in changes:
        if not isinstance(change, tuple) or len(change) < 3:
            directions.append("changed")
        elif change[1] is False and change[2] is True:
            directions.append("enabled")
        elif change[1] is True and change[2] is False:
            directions.append("consumed")
        else:
            directions.append("changed")
    return tuple(sorted(directions))


def _mechanism_event(effect: Any) -> tuple[Any, ...]:
    """Remove presentation and routine controllability costs."""
    retained: list[tuple[Any, ...]] = []
    for item in effect if isinstance(effect, tuple) else ():
        if not isinstance(item, tuple) or not item:
            continue
        factor = item[0]
        if factor == "controlled_base":
            mechanism = item[1] if len(item) > 1 else ()
            if (
                isinstance(mechanism, tuple)
                and mechanism[:1] == ("support_change",)
            ):
                before = mechanism[1] if len(mechanism) > 1 else 0
                after = mechanism[2] if len(mechanism) > 2 else 0
                retained.append((factor, "support_change", _sign(after - before)))
        elif factor == "finite_configuration":
            retained.append((factor, "changed"))
        elif factor == "operation_domain_assignment":
            retained.append((factor, "changed"))
        elif factor == "one_shot_availability":
            changes = (
                item[1]
                if len(item) > 1 and isinstance(item[1], tuple)
                else ()
            )
            retained.append((factor, _availability_directions(changes)))
        elif factor in {
            "ordered_feasibility_configuration",
            "ordered_budget",
        }:
            delta = item[1] if len(item) > 1 else 0
            if _sign(delta) > 0:
                retained.append((factor, "renewal"))
    return tuple(sorted(retained, key=repr))


def _event_witnesses(
    section: tuple[tuple[int, Any], ...],
    *,
    projection: Any,
    bank_ref: str,
) -> tuple[EventWitness, ...]:
    witnesses = []
    for bank_row, transition in section[:-1]:
        effect = fiber_mechanism_effect(
            projection.factor(transition.s),
            projection.factor(transition.s_next),
        )
        event = _mechanism_event(effect)
        if not event:
            continue
        witnesses.append(EventWitness(
            event=event,
            operation=transition.a,
            bank_row=bank_row,
            time=int(transition.t),
            evidence_ref=f"{bank_ref}#{bank_row}",
        ))
    return tuple(witnesses)


def _restricted_growth(values: Iterable[Any]) -> tuple[int, ...]:
    seen: dict[str, int] = {}
    result = []
    for value in values:
        key = repr(value)
        if key not in seen:
            seen[key] = len(seen)
        result.append(seen[key])
    return tuple(result)


def _collapse(
    tokens: tuple[Any, ...],
    witnesses: tuple[EventWitness, ...],
) -> tuple[tuple[Any, ...], tuple[tuple[EventWitness, ...], ...]]:
    collapsed: list[Any] = []
    lineage: list[list[EventWitness]] = []
    for token, witness in zip(tokens, witnesses, strict=True):
        if collapsed and collapsed[-1] == token:
            lineage[-1].append(witness)
            continue
        collapsed.append(token)
        lineage.append([witness])
    return tuple(collapsed), tuple(tuple(group) for group in lineage)


def _languages(
    witnesses: tuple[EventWitness, ...],
) -> dict[str, tuple[tuple[Any, ...], tuple[tuple[EventWitness, ...], ...]]]:
    events = tuple(witness.event for witness in witnesses)
    event_tokens, event_lineage = _collapse(events, witnesses)
    operation_partition = _restricted_growth(
        witness.operation for witness in witnesses
    )
    bound_tokens = tuple(
        (witness.event, operation_partition[index])
        for index, witness in enumerate(witnesses)
    )
    bound_tokens, bound_lineage = _collapse(bound_tokens, witnesses)
    return {
        "event_family": (event_tokens, event_lineage),
        "event_operation_partition": (bound_tokens, bound_lineage),
    }


def _lcs_alignment(
    left: tuple[Any, ...],
    right: tuple[Any, ...],
) -> tuple[tuple[int, int], ...]:
    table = [
        [0 for _ in range(len(right) + 1)]
        for _ in range(len(left) + 1)
    ]
    for i in range(len(left) - 1, -1, -1):
        for j in range(len(right) - 1, -1, -1):
            if left[i] == right[j]:
                table[i][j] = 1 + table[i + 1][j + 1]
            else:
                table[i][j] = max(table[i + 1][j], table[i][j + 1])
    alignment = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] == right[j]:
            alignment.append((i, j))
            i += 1
            j += 1
        elif table[i + 1][j] >= table[i][j + 1]:
            i += 1
        else:
            j += 1
    return tuple(alignment)


def _f1(common: int, left: int, right: int) -> float:
    return 0.0 if left + right == 0 else (2.0 * common) / (left + right)


def _lineage_payload(group: tuple[EventWitness, ...]) -> list[dict[str, Any]]:
    return [
        {
            "bank_row": witness.bank_row,
            "time": witness.time,
            "operation": repr(witness.operation),
            "event": witness.event,
            "event_sha256": stable_sha256(witness.event),
            "evidence_ref": witness.evidence_ref,
        }
        for witness in group
    ]


def _action_baseline(
    template: tuple[tuple[int, Any], ...],
    candidate: tuple[tuple[int, Any], ...],
) -> float:
    left = _restricted_growth(row.a for _index, row in template[:-1])
    right = _restricted_growth(row.a for _index, row in candidate[:-1])
    common = len(_lcs_alignment(left, right))
    return _f1(common, len(left), len(right))


def _length_baseline(
    template: tuple[tuple[int, Any], ...],
    candidate: tuple[tuple[int, Any], ...],
) -> float:
    left = len(template) - 1
    right = len(candidate) - 1
    return 1.0 if left == right == 0 else 1.0 - abs(left - right) / max(left, right)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    carrier, _kind, _sha = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")

    bank_path = project / "raw/episodes/episode_001.jsonl"
    bank = tuple(EpisodeLog.read_jsonl(bank_path))
    bank_ref = "raw/episodes/episode_001.jsonl"
    boundaries = []
    for index, transition in enumerate(bank):
        identity = getattr(transition, "identity", None)
        if (
            identity is None
            or not identity.is_authoritative
            or not identity.is_boundary
            or identity.source_epoch not in {0, 1}
        ):
            continue
        section = _boundary_section(bank, index)
        witnesses = _event_witnesses(
            section,
            projection=projection,
            bank_ref=bank_ref,
        )
        boundaries.append({
            "boundary_index": index,
            "source_epoch": int(identity.source_epoch),
            "target_epoch": int(identity.target_epoch),
            "boundary_kind": str(identity.boundary_kind),
            "positive": str(identity.boundary_kind) == "level_completed",
            "section": section,
            "event_witnesses": witnesses,
            "languages": _languages(witnesses),
        })

    templates = [
        row for row in boundaries
        if row["source_epoch"] == 0 and row["positive"]
    ]
    candidates = [row for row in boundaries if row["source_epoch"] == 1]
    if len(templates) != 1:
        raise SystemExit(
            f"expected one epoch-0 positive template, found {len(templates)}"
        )
    if not candidates:
        raise SystemExit("no epoch-1 terminal holdouts")
    template = templates[0]

    language_results = []
    for language in ("event_family", "event_operation_partition"):
        template_tokens, template_lineage = template["languages"][language]
        scored = []
        for candidate in candidates:
            candidate_tokens, candidate_lineage = candidate["languages"][language]
            alignment = _lcs_alignment(template_tokens, candidate_tokens)
            common = len(alignment)
            score = _f1(common, len(template_tokens), len(candidate_tokens))
            reverse_alignment = _lcs_alignment(
                tuple(reversed(template_tokens)),
                candidate_tokens,
            )
            reverse_score = _f1(
                len(reverse_alignment),
                len(template_tokens),
                len(candidate_tokens),
            )
            scored.append({
                "boundary_index": candidate["boundary_index"],
                "boundary_kind": candidate["boundary_kind"],
                "positive": candidate["positive"],
                "section_length": len(candidate["section"]),
                "event_count": len(candidate_tokens),
                "score": score,
                "aligned_template_count": common,
                "full_template_embedding": common == len(template_tokens),
                "reverse_score": reverse_score,
                "action_baseline_score": _action_baseline(
                    template["section"],
                    candidate["section"],
                ),
                "length_baseline_score": _length_baseline(
                    template["section"],
                    candidate["section"],
                ),
                "alignment": [
                    {
                        "template_position": left_index,
                        "candidate_position": right_index,
                        "template_lineage": _lineage_payload(
                            template_lineage[left_index]
                        ),
                        "candidate_lineage": _lineage_payload(
                            candidate_lineage[right_index]
                        ),
                    }
                    for left_index, right_index in alignment
                ],
            })
        scored.sort(key=lambda row: (-row["score"], row["boundary_index"]))
        positives = [row for row in scored if row["positive"]]
        if len(positives) != 1:
            raise SystemExit(
                f"expected one epoch-1 positive holdout, found {len(positives)}"
            )
        positive = positives[0]
        negative_scores = [
            row["score"] for row in scored if not row["positive"]
        ]
        next_score = max(negative_scores, default=-1.0)
        reverse_identical = template_tokens == tuple(reversed(template_tokens))
        passed = bool(
            len(template_tokens) >= 2
            and positive["full_template_embedding"]
            and positive["score"] > next_score
            and not reverse_identical
            and positive["score"] > positive["reverse_score"]
            and scored[0]["positive"]
        )
        language_results.append({
            "language": language,
            "template_event_count": len(template_tokens),
            "template_sha256": stable_sha256(template_tokens),
            "template_reverse_identical": reverse_identical,
            "positive_margin": positive["score"] - next_score,
            "passed": passed,
            "ranked_holdouts": scored,
        })

    passed = [row for row in language_results if row["passed"]]
    payload = {
        "schema": "ztare-success-predecessor-mechanism-audit-v1",
        "template": {
            "boundary_index": template["boundary_index"],
            "source_epoch": template["source_epoch"],
            "target_epoch": template["target_epoch"],
            "section_length": len(template["section"]),
            "raw_event_count": len(template["event_witnesses"]),
            "boundary_kind": template["boundary_kind"],
        },
        "holdout_count": len(candidates),
        "holdout_positive_count": sum(
            1 for row in candidates if row["positive"]
        ),
        "language_results": language_results,
        "passing_languages": [row["language"] for row in passed],
        "status": (
            "success_predecessor_mechanism_transport_confirmed"
            if passed
            else "success_predecessor_mechanism_transport_refuted"
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "template": payload["template"],
        "holdout_count": payload["holdout_count"],
        "passing_languages": payload["passing_languages"],
        "languages": [
            {
                "language": row["language"],
                "template_event_count": row["template_event_count"],
                "positive_margin": row["positive_margin"],
                "passed": row["passed"],
                "ranking": [
                    {
                        "boundary_index": item["boundary_index"],
                        "boundary_kind": item["boundary_kind"],
                        "event_count": item["event_count"],
                        "score": item["score"],
                        "reverse_score": item["reverse_score"],
                    }
                    for item in row["ranked_holdouts"]
                ],
            }
            for row in language_results
        ],
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
