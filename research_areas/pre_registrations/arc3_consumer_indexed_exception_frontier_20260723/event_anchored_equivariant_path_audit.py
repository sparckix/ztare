#!/usr/bin/env python3
"""Audit event-anchored control paths modulo one global lattice symmetry."""
from __future__ import annotations

import argparse
from math import gcd
import json
from pathlib import Path
from typing import Any

import success_predecessor_mechanism_audit as predecessor

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.mechanism_effects import fiber_mechanism_effect


TRANSFORMS = (
    ("identity", lambda r, c: (r, c)),
    ("reflect_col", lambda r, c: (r, -c)),
    ("reflect_row", lambda r, c: (-r, c)),
    ("rotate_180", lambda r, c: (-r, -c)),
    ("transpose", lambda r, c: (c, r)),
    ("rotate_90", lambda r, c: (c, -r)),
    ("rotate_270", lambda r, c: (-c, r)),
    ("anti_transpose", lambda r, c: (-c, -r)),
)


def _primitive(vector: tuple[int, int]) -> tuple[int, int]:
    row, col = vector
    divisor = gcd(abs(row), abs(col))
    return (row, col) if divisor == 0 else (row // divisor, col // divisor)


def _effect_parts(effect: Any) -> tuple[tuple[int, int] | None, bool]:
    vector = None
    anchor = False
    for item in effect if isinstance(effect, tuple) else ():
        if not isinstance(item, tuple) or not item:
            continue
        if item[0] == "finite_configuration":
            anchor = True
        if item[0] != "controlled_base" or len(item) < 2:
            continue
        mechanism = item[1]
        if (
            isinstance(mechanism, tuple)
            and mechanism[:1] == ("translate",)
            and len(mechanism) >= 3
        ):
            vector = _primitive((int(mechanism[1]), int(mechanism[2])))
    return vector, anchor


def _collapse_runs(
    rows: tuple[tuple[tuple[int, int], dict[str, Any]], ...],
) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[dict[str, Any], ...], ...]]:
    tokens: list[tuple[int, int]] = []
    lineage: list[list[dict[str, Any]]] = []
    for vector, witness in rows:
        if tokens and tokens[-1] == vector:
            lineage[-1].append(witness)
            continue
        tokens.append(vector)
        lineage.append([witness])
    return tuple(tokens), tuple(tuple(group) for group in lineage)


def _canonical_directions(
    pre: tuple[tuple[int, int], ...],
    post: tuple[tuple[int, int], ...],
) -> tuple[tuple[Any, ...], str]:
    candidates = []
    for name, transform in TRANSFORMS:
        tokens = (
            *(("direction", *transform(*vector)) for vector in pre),
            ("anchor",),
            *(("direction", *transform(*vector)) for vector in post),
        )
        candidates.append((repr(tokens), name, tokens))
    _key, name, tokens = min(candidates)
    return tuple(tokens), name


def _independent_direction_word(
    pre: tuple[tuple[int, int], ...],
    post: tuple[tuple[int, int], ...],
) -> tuple[Any, ...]:
    def orbit(vector: tuple[int, int]) -> tuple[int, int]:
        return min(
            (transform(*vector) for _name, transform in TRANSFORMS),
            key=repr,
        )

    return (
        *(("direction", *orbit(vector)) for vector in pre),
        ("anchor",),
        *(("direction", *orbit(vector)) for vector in post),
    )


def _turn_tokens(vectors: tuple[tuple[int, int], ...]) -> tuple[Any, ...]:
    tokens = []
    for left, right in zip(vectors, vectors[1:]):
        lr, lc = left
        rr, rc = right
        tokens.append((
            "turn",
            lr * lr + lc * lc,
            rr * rr + rc * rc,
            lr * rr + lc * rc,
            abs(lr * rc - lc * rr),
        ))
    return tuple(tokens)


def _merge_lineage(
    left: tuple[dict[str, Any], ...],
    right: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    merged = []
    seen = set()
    for witness in (*left, *right):
        identity = str(witness["evidence_ref"])
        if identity in seen:
            continue
        seen.add(identity)
        merged.append(witness)
    return tuple(merged)


def _word_payload(
    section: tuple[tuple[int, Any], ...],
    *,
    projection: Any,
    bank_ref: str,
) -> dict[str, Any]:
    motion_before = []
    motion_after = []
    anchor_witness = None
    anchor_seen = False
    for bank_row, transition in section[:-1]:
        effect = fiber_mechanism_effect(
            projection.factor(transition.s),
            projection.factor(transition.s_next),
        )
        vector, is_anchor = _effect_parts(effect)
        witness = {
            "bank_row": bank_row,
            "time": int(transition.t),
            "operation": repr(transition.a),
            "evidence_ref": f"{bank_ref}#{bank_row}",
        }
        if vector is not None:
            (motion_after if anchor_seen else motion_before).append(
                (vector, witness)
            )
        if is_anchor and anchor_witness is None:
            anchor_seen = True
            anchor_witness = {
                **witness,
                "event": "finite_configuration:changed",
            }

    pre_vectors, pre_lineage = _collapse_runs(tuple(motion_before))
    post_vectors, post_lineage = _collapse_runs(tuple(motion_after))
    direction_tokens, transform = _canonical_directions(
        pre_vectors,
        post_vectors,
    )
    anchor_lineage = (
        (anchor_witness,)
        if anchor_witness is not None
        else ()
    )
    direction_lineage = (
        *pre_lineage,
        anchor_lineage,
        *post_lineage,
    )
    turn_tokens = (
        *_turn_tokens(pre_vectors),
        ("anchor",),
        *_turn_tokens(post_vectors),
    )
    turn_lineage: tuple[tuple[dict[str, Any], ...], ...] = (
        *tuple(
            _merge_lineage(
                pre_lineage[index],
                pre_lineage[index + 1],
            )
            for index in range(max(0, len(pre_lineage) - 1))
        ),
        anchor_lineage,
        *tuple(
            _merge_lineage(
                post_lineage[index],
                post_lineage[index + 1],
            )
            for index in range(max(0, len(post_lineage) - 1))
        ),
    )
    return {
        "anchor_present": anchor_witness is not None,
        "anchor_witness": anchor_witness,
        "pre_run_count": len(pre_vectors),
        "post_run_count": len(post_vectors),
        "direction": {
            "tokens": direction_tokens if anchor_witness is not None else (),
            "lineage": direction_lineage if anchor_witness is not None else (),
            "global_transform": transform,
            "independent_step_tokens": (
                _independent_direction_word(pre_vectors, post_vectors)
                if anchor_witness is not None
                else ()
            ),
        },
        "turn": {
            "tokens": turn_tokens if anchor_witness is not None else (),
            "lineage": turn_lineage if anchor_witness is not None else (),
            "global_transform": "orthogonal_invariants",
            "independent_step_tokens": (),
        },
    }


def _score(
    template: dict[str, Any],
    candidate: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    template_tokens = template[language]["tokens"]
    candidate_tokens = candidate[language]["tokens"]
    alignment = predecessor._lcs_alignment(template_tokens, candidate_tokens)
    score = predecessor._f1(
        len(alignment),
        len(template_tokens),
        len(candidate_tokens),
    )
    reversed_tokens = tuple(reversed(template_tokens))
    reverse_alignment = predecessor._lcs_alignment(
        reversed_tokens,
        candidate_tokens,
    )
    reverse_score = predecessor._f1(
        len(reverse_alignment),
        len(reversed_tokens),
        len(candidate_tokens),
    )
    unanchored_template = tuple(
        token for token in template_tokens if token != ("anchor",)
    )
    unanchored_candidate = tuple(
        token for token in candidate_tokens if token != ("anchor",)
    )
    unanchored_alignment = predecessor._lcs_alignment(
        unanchored_template,
        unanchored_candidate,
    )
    unanchored_score = predecessor._f1(
        len(unanchored_alignment),
        len(unanchored_template),
        len(unanchored_candidate),
    )
    independent_score = None
    if language == "direction":
        independent_template = template[language]["independent_step_tokens"]
        independent_candidate = candidate[language]["independent_step_tokens"]
        independent_alignment = predecessor._lcs_alignment(
            independent_template,
            independent_candidate,
        )
        independent_score = predecessor._f1(
            len(independent_alignment),
            len(independent_template),
            len(independent_candidate),
        )
    return {
        "score": score,
        "aligned_template_count": len(alignment),
        "full_template_embedding": len(alignment) == len(template_tokens),
        "reverse_score": reverse_score,
        "anchor_removed_score": unanchored_score,
        "independent_step_score": independent_score,
        "alignment": [
            {
                "template_position": left,
                "candidate_position": right,
                "template_token": template_tokens[left],
                "candidate_token": candidate_tokens[right],
                "template_lineage": template[language]["lineage"][left],
                "candidate_lineage": candidate[language]["lineage"][right],
            }
            for left, right in alignment
        ],
    }


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
        section = predecessor._boundary_section(bank, index)
        words = _word_payload(
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
            "section_length": len(section),
            "words": words,
        })

    templates = [
        row for row in boundaries
        if row["source_epoch"] == 0 and row["positive"]
    ]
    holdouts = [row for row in boundaries if row["source_epoch"] == 1]
    if len(templates) != 1:
        raise SystemExit(
            f"expected one epoch-0 completion, found {len(templates)}"
        )
    template = templates[0]

    results = []
    for language in ("direction", "turn"):
        template_tokens = template["words"][language]["tokens"]
        ranked = []
        for holdout in holdouts:
            row = _score(
                template["words"],
                holdout["words"],
                language,
            )
            ranked.append({
                "boundary_index": holdout["boundary_index"],
                "boundary_kind": holdout["boundary_kind"],
                "positive": holdout["positive"],
                "section_length": holdout["section_length"],
                "anchor_present": holdout["words"]["anchor_present"],
                "pre_run_count": holdout["words"]["pre_run_count"],
                "post_run_count": holdout["words"]["post_run_count"],
                "global_transform": (
                    holdout["words"][language]["global_transform"]
                ),
                **row,
            })
        ranked.sort(key=lambda row: (-row["score"], row["boundary_index"]))
        positives = [row for row in ranked if row["positive"]]
        if len(positives) != 1:
            raise SystemExit(
                f"expected one epoch-1 completion, found {len(positives)}"
            )
        positive = positives[0]
        negative_max = max(
            (row["score"] for row in ranked if not row["positive"]),
            default=-1.0,
        )
        motion_token_count = sum(
            token != ("anchor",) for token in template_tokens
        )
        passed = bool(
            template["words"]["anchor_present"]
            and template["words"]["pre_run_count"] >= 1
            and template["words"]["post_run_count"] >= 1
            and motion_token_count >= 3
            and positive["anchor_present"]
            and positive["full_template_embedding"]
            and positive["score"] > negative_max
            and ranked[0]["positive"]
            and positive["score"] > positive["reverse_score"]
            and positive["score"] > positive["anchor_removed_score"]
        )
        results.append({
            "language": (
                "anchored_direction_runs"
                if language == "direction"
                else "anchored_relative_turns"
            ),
            "template_token_count": len(template_tokens),
            "template_motion_token_count": motion_token_count,
            "template_sha256": stable_sha256(template_tokens),
            "template_global_transform": (
                template["words"][language]["global_transform"]
            ),
            "positive_margin": positive["score"] - negative_max,
            "passed": passed,
            "ranked_holdouts": ranked,
        })

    passing = [row for row in results if row["passed"]]
    payload = {
        "schema": "ztare-event-anchored-equivariant-path-audit-v1",
        "template": {
            "boundary_index": template["boundary_index"],
            "section_length": template["section_length"],
            "anchor_present": template["words"]["anchor_present"],
            "anchor_witness": template["words"]["anchor_witness"],
            "pre_run_count": template["words"]["pre_run_count"],
            "post_run_count": template["words"]["post_run_count"],
        },
        "holdout_count": len(holdouts),
        "language_results": results,
        "passing_languages": [row["language"] for row in passing],
        "status": (
            "event_anchored_equivariant_path_confirmed"
            if passing
            else "event_anchored_equivariant_path_refuted"
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
        "passing_languages": payload["passing_languages"],
        "languages": [
            {
                "language": row["language"],
                "template_token_count": row["template_token_count"],
                "template_motion_token_count": row[
                    "template_motion_token_count"
                ],
                "positive_margin": row["positive_margin"],
                "passed": row["passed"],
                "positive": next(
                    item for item in row["ranked_holdouts"]
                    if item["positive"]
                ),
            }
            for row in results
        ],
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
