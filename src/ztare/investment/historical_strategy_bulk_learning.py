"""Rank and hydrate SEC strategy events for staggered-cohort learning."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.common.subscription_agent_runtime import (
    CODEX_SANDBOX_SEALED_COMPLETION,
    run_subscription_agent_with_recovery,
)

from .historical_strategy_bulk_corpus import HISTORICAL_STRATEGY_BULK_CORPUS_SCHEMA
from .historical_strategy_event_replay import (
    canonicalize_strategy_event_phenotype,
    classify_sec_item_201,
    extract_sec_item_201_context,
)
from .sources import fetch_sec_filing_document


HISTORICAL_STRATEGY_BULK_LEARNING_SCHEMA = (
    "jaggedthoughts-historical-strategy-bulk-learning-v1"
)
_ROOT = Path("institutional_learning/historical_strategy_bulk_learning")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _checked_json(path: Path, digest_field: str) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    body = dict(row)
    declared = str(body.pop(digest_field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{path.name} content hash mismatch")
    return row


def _events(root: Path, corpus: Mapping[str, Any]) -> list[dict[str, Any]]:
    path = (root / str(corpus["event_lake_path"])).resolve()
    path.relative_to(root)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _classification_paths(root: Path) -> dict[str, Path]:
    deterministic_paths = [
        *(root / "institutional_learning" / "historical_strategy_event_replay" / "filings").glob("*.json"),
        *(root / _ROOT / "classifications").glob("*.json"),
    ]
    deterministic = {}
    for path in deterministic_paths:
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            accession = str(row.get("accession_number") or "")
            if accession:
                deterministic[accession] = (row, path)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    classified = {
        accession: path for accession, (row, path) in deterministic.items()
        if row.get("classification") != "ambiguous"
    }
    for path in (root / _ROOT / "semantic_resolutions").glob("*.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            accession = str(row.get("accession_number") or "")
            prior = deterministic.get(accession)
            if prior and _semantic_matches_classification(row, prior[0]):
                classified[accession] = path
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return classified


def _semantic_matches_classification(
    semantic: Mapping[str, Any], deterministic: Mapping[str, Any],
) -> bool:
    return bool(
        semantic.get("filing_document_sha256")
        == deterministic.get("filing_document_sha256")
        and semantic.get("deterministic_classification_receipt_sha256")
        == deterministic.get("classification_receipt_sha256")
    )


def _is_current_trial_selection(
    row: Mapping[str, Any], current_trial_sha256: str,
) -> bool:
    selection = row.get("acquisition_selection_receipt") or {}
    basis = selection.get("selection_basis") or {}
    return bool(
        current_trial_sha256
        and selection.get("selection_mode") == "sealed_law_trial_holdout"
        and basis.get("trial_sha256") == current_trial_sha256
    )


def _semantic_resolution_priority(
    row: Mapping[str, Any], current_trial_sha256: str = "",
) -> tuple[int, int, str]:
    selection = row.get("acquisition_selection_receipt") or {}
    mode = str(selection.get("selection_mode") or "")
    current_trial = _is_current_trial_selection(row, current_trial_sha256)
    lane = 0 if current_trial else 1 if mode in {
        "treatment_identity_closure", "causal_panel_frontier",
        "phenotype_refinement_frontier",
    } else 2
    return lane, int(selection.get("selection_rank") or 10**9), str(
        row.get("accession_number") or ""
    )


def _cohort_rows(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_cik: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_cik[str(event["cik"])].append(event)
    first_events = [
        min(rows, key=lambda row: (row["available_at"], row["accession_number"]))
        for rows in by_cik.values()
    ]
    first_year = {str(row["cik"]): int(row["occurred_at"][:4]) for row in first_events}
    by_industry_year = Counter(
        (str(row.get("sic") or "")[:2], first_year[str(row["cik"])])
        for row in first_events
    )
    cells, candidates = [], []
    for (sic2, year), treated_count in sorted(by_industry_year.items()):
        future = sum(
            other_sic == sic2 and other_year > year
            for (other_sic, other_year), count in by_industry_year.items()
            for _ in range(count)
        )
        cell = {
            "sic2": sic2 or "unknown", "adoption_year": year,
            "treated_entity_count": treated_count,
            "future_adopter_entity_count": future,
            "structurally_supported": treated_count >= 4 and future >= 4,
        }
        cells.append(cell)
    cell_index = {(row["sic2"], row["adoption_year"]): row for row in cells}
    for event in first_events:
        year = int(event["occurred_at"][:4])
        cell = cell_index[(str(event.get("sic") or "")[:2] or "unknown", year)]
        if year <= 2024 and cell["structurally_supported"]:
            candidates.append({**event, "design_cell": cell})
    return cells, candidates


def _select_diverse(candidates: list[dict[str, Any]], known: set[str], limit: int) -> list[dict[str, Any]]:
    remaining = [row for row in candidates if str(row["accession_number"]) not in known]
    selected: list[dict[str, Any]] = []
    industry, time_bucket, survival = Counter(), Counter(), Counter()
    while remaining and len(selected) < limit:
        def score(row: Mapping[str, Any]) -> tuple[float, str]:
            cell = row["design_cell"]
            support = min(1.0, min(cell["treated_entity_count"], cell["future_adopter_entity_count"]) / 12)
            sic2 = str(cell["sic2"])
            bucket = f"{int(cell['adoption_year']) // 3 * 3}-{int(cell['adoption_year']) // 3 * 3 + 2}"
            status = "current" if row["current_common_equity_member"] else "historical_only"
            value = (
                0.50 * support
                + 0.22 / (1 + industry[sic2])
                + 0.16 / (1 + time_bucket[bucket])
                + 0.12 / (1 + survival[status])
            )
            return value, str(row["event_sha256"])
        winner = max(remaining, key=score)
        remaining.remove(winner)
        cell = winner["design_cell"]
        bucket = f"{int(cell['adoption_year']) // 3 * 3}-{int(cell['adoption_year']) // 3 * 3 + 2}"
        status = "current" if winner["current_common_equity_member"] else "historical_only"
        industry[str(cell["sic2"])] += 1
        time_bucket[bucket] += 1
        survival[status] += 1
        selected.append({
            **winner,
            "selection_rank": len(selected) + 1,
            "selection_basis": {
                "family_adoption_support": winner["design_cell"],
                "industry_novelty_before_selection": 1 / industry[str(cell["sic2"])],
                "time_bucket_novelty_before_selection": 1 / time_bucket[bucket],
                "survival_status_novelty_before_selection": 1 / survival[status],
                "information_yield_status": "structural_acquisition_priority_not_hypothesis_discrimination",
            },
        })
    return selected


def _select_history_closure(
    events: list[dict[str, Any]], acquired: set[str], limit: int,
) -> list[dict[str, Any]]:
    """Choose unseen filings that complete already-started issuer histories."""
    by_cik: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if int(event["occurred_at"][:4]) <= 2024:
            by_cik[str(event["cik"])].append(event)
    partial = {
        cik: sorted(rows, key=lambda row: (row["available_at"], row["accession_number"]))
        for cik, rows in by_cik.items()
        if any(str(row["accession_number"]) in acquired for row in rows)
        and any(str(row["accession_number"]) not in acquired for row in rows)
    }
    selected: list[dict[str, Any]] = []
    while partial and len(selected) < limit:
        before = len(selected)
        for cik in sorted(
            partial,
            key=lambda value: (
                -sum(str(row["accession_number"]) in acquired for row in partial[value]),
                len(partial[value]), value,
            ),
        ):
            unseen = [
                row for row in partial[cik]
                if str(row["accession_number"]) not in acquired
                and str(row["accession_number"]) not in {
                    str(item["accession_number"]) for item in selected
                }
            ]
            if not unseen:
                partial.pop(cik)
                continue
            event = unseen[0]
            selected.append({
                **event,
                "selection_rank": len(selected) + 1,
                "selection_mode": "issuer_history_closure",
                "selection_basis": {
                    "issuer_event_count": len(partial[cik]),
                    "issuer_previously_acquired_event_count": sum(
                        str(row["accession_number"]) in acquired for row in partial[cik]
                    ),
                    "purpose": "establish_first_observed_granular_phenotype_adoption",
                },
            })
            if len(selected) >= limit:
                break
        if len(selected) == before:
            break
    return selected


def _select_panel_frontier(
    events: list[dict[str, Any]], acquired: set[str],
    panel: Mapping[str, Any], coverage: Mapping[str, list[str]], limit: int,
) -> list[dict[str, Any]]:
    """Target untyped filings that can resolve the nearest causal-panel cells."""
    candidates = [
        row for row in events
        if int(row["occurred_at"][:4]) <= 2024
        and str(row["accession_number"]) not in acquired
    ]
    cells = sorted(
        [
            row for row in panel.get("adoption_cells", [])
            if not row.get("group_time_ready")
            and int(row.get("history_ready_treated_count") or 0) > 0
            and int(row.get("history_ready_future_adopter_count") or 0) > 0
        ],
        key=lambda row: (
            max(0, 4 - min(
                int(row["history_ready_treated_count"]),
                int((row.get("joint_design") or {}).get("pre_treated_count") or 0),
                int((row.get("joint_design") or {}).get("post_treated_count") or 0),
            ))
            + max(0, 4 - min(
                int(row["history_ready_future_adopter_count"]),
                int((row.get("joint_design") or {}).get("pre_control_count") or 0),
                int((row.get("joint_design") or {}).get("post_control_count") or 0),
            )),
            -int(row.get("treated_entity_count") or 0),
            str(row["sic2"]), int(row["adoption_year"]),
            str(row["implementation_mode"]),
        ),
    )
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    while len(selected) < limit:
        before = len(selected)
        for cell in cells:
            year = int(cell["adoption_year"])
            design = dict(cell.get("joint_design") or {})
            treated_gap = max(0, 4 - min(
                int(cell["history_ready_treated_count"]),
                int(design.get("pre_treated_count") or 0),
                int(design.get("post_treated_count") or 0),
            ))
            future_gap = max(0, 4 - min(
                int(cell["history_ready_future_adopter_count"]),
                int(design.get("pre_control_count") or 0),
                int(design.get("post_control_count") or 0),
            ))
            choices = []
            for event in candidates:
                accession = str(event["accession_number"])
                event_year = int(event["occurred_at"][:4])
                periods = coverage.get(str(event["cik"]), [])
                period_years = {int(value[:4]) for value in periods}
                pre_count = sum(int(value[:4]) < event_year for value in periods)
                post_count = sum(int(value[:4]) > event_year for value in periods)
                if accession in used or (str(event.get("sic") or "")[:2] or "unknown") != cell["sic2"]:
                    continue
                if pre_count < 3 or post_count < 1:
                    continue
                required_periods = {
                    *[int(value) for value in design.get("pre_periods") or ()],
                    *([int(design["post_period"])] if design.get("post_period") else []),
                }
                if required_periods and not required_periods <= period_years:
                    continue
                relation = (
                    "treated" if treated_gap and event_year == year
                    else "future_adopter" if future_gap and event_year > max(
                        year, int(design.get("post_period") or year)
                    )
                    else None
                )
                if relation:
                    choices.append((
                        0 if relation == "treated" else 1,
                        abs(event_year - year), event["available_at"], accession,
                        relation, event,
                    ))
            if not choices:
                continue
            *_order, relation, event = min(choices, key=lambda row: row[:4])
            accession = str(event["accession_number"])
            used.add(accession)
            selected.append({
                **event,
                "selection_rank": len(selected) + 1,
                "selection_mode": "causal_panel_frontier",
                "selection_basis": {
                    "target_cell": {
                        "sic2": cell["sic2"],
                        "implementation_mode": cell["implementation_mode"],
                        "adoption_year": year,
                    },
                    "candidate_relation": relation,
                    "history_ready_treated_gap": treated_gap,
                    "history_ready_future_adopter_gap": future_gap,
                    "joint_design_target": dict(cell.get("joint_design") or {}),
                    "candidate_pre_period_count": sum(
                        int(value[:4]) < int(event["occurred_at"][:4])
                        for value in coverage.get(str(event["cik"]), [])
                    ),
                    "candidate_post_period_count": sum(
                        int(value[:4]) > int(event["occurred_at"][:4])
                        for value in coverage.get(str(event["cik"]), [])
                    ),
                    "boundary": "Item 2.01 metadata cannot establish phenotype; the filing may reject this candidate-cell match.",
                },
            })
            if len(selected) >= limit:
                break
        if len(selected) == before:
            break
    return selected


def _select_identity_closure(
    events: list[dict[str, Any]], acquired: set[str],
    panel: Mapping[str, Any], limit: int,
) -> list[dict[str, Any]]:
    """Select exact predecessor filings blocking a typed first-adoption identity."""
    by_accession = {str(row["accession_number"]): row for row in events}
    selected = []
    for blocker in panel.get("identity_closure_blockers", []):
        accession = str(blocker["missing_accession_number"])
        event = by_accession.get(accession)
        if not event or accession in acquired or any(
            str(row["accession_number"]) == accession for row in selected
        ):
            continue
        selected.append({
            **event,
            "selection_rank": len(selected) + 1,
            "selection_mode": "treatment_identity_closure",
            "selection_basis": {
                "blocked_accession_number": blocker["blocked_accession_number"],
                "target_cell": {
                    "sic2": blocker["sic2"],
                    "implementation_mode": blocker["implementation_mode"],
                    "adoption_year": blocker["adoption_year"],
                },
                "history_ready_treated_gap": blocker["history_ready_treated_gap"],
                "history_ready_future_adopter_gap": blocker[
                    "history_ready_future_adopter_gap"
                ],
                "purpose": "resolve_first_observed_phenotype_adoption_identity",
            },
        })
        if len(selected) >= limit:
            break
    return selected


def _select_phenotype_frontier(
    events: list[dict[str, Any]], acquired: set[str],
    law_search: Mapping[str, Any], coverage: Mapping[str, list[str]], limit: int,
) -> list[dict[str, Any]]:
    """Target untyped documents that can fill an outcome-blind child-law cell."""
    selected, used = [], set()
    for cell in law_search.get("acquisition_frontier") or ():
        parent = cell["parent"]
        year = int(parent["adoption_year"])
        design = cell.get("joint_design") or {}
        required_periods = {
            *map(int, design.get("pre_periods") or ()),
            *([int(design["post_period"])] if design.get("post_period") else []),
        }
        occupied = set(cell["treated_entity_ids"]) | set(cell["future_adopter_entity_ids"])
        choices = []
        for event in events:
            accession = str(event["accession_number"])
            cik = str(event["cik"])
            event_year = int(event["occurred_at"][:4])
            period_years = {int(value[:4]) for value in coverage.get(cik, ())}
            if (
                accession in acquired or accession in used or cik in occupied
                or (str(event.get("sic") or "")[:2] or "unknown") != parent["sic2"]
                or sum(value < event_year for value in period_years) < 3
                or sum(value > event_year for value in period_years) < 1
                or (required_periods and not required_periods <= period_years)
            ):
                continue
            relation = (
                "treated" if (
                    cell["treated_support_gap"] or cell["joint_treated_support_gap"]
                ) and event_year == year
                else "future_adopter" if (
                    cell["future_adopter_support_gap"]
                    or cell["joint_future_adopter_support_gap"]
                )
                and event_year > max(year, int(design.get("post_period") or year))
                else None
            )
            if relation:
                choices.append((
                    0 if relation == "treated" else 1,
                    abs(event_year - year), event["available_at"], accession,
                    relation, event,
                ))
        if not choices:
            continue
        *_order, relation, event = min(choices, key=lambda row: row[:4])
        used.add(str(event["accession_number"]))
        selected.append({
            **event,
            "selection_rank": len(selected) + 1,
            "selection_mode": "phenotype_refinement_frontier",
            "selection_basis": {
                "law_search_sha256": law_search.get("law_search_sha256"),
                "target_cell_sha256": cell["cell_sha256"],
                "target_parent": parent,
                "target_moderators": cell["moderators"],
                "candidate_relation": relation,
                "treated_support_gap": cell["treated_support_gap"],
                "future_adopter_support_gap": cell["future_adopter_support_gap"],
                "joint_treated_support_gap": cell["joint_treated_support_gap"],
                "joint_future_adopter_support_gap": cell[
                    "joint_future_adopter_support_gap"
                ],
                "joint_design_target": design,
                "boundary": (
                    "The untyped filing is only a source-acquisition candidate; "
                    "its document must establish the target phenotype."
                ),
            },
        })
        if len(selected) >= limit:
            break
    return selected


def _select_law_trial_holdout(
    events: list[dict[str, Any]], acquired: set[str], trial: Mapping[str, Any],
    coverage: Mapping[str, list[str]], limit: int,
    excluded_ciks: set[str] | None = None,
    support_by_candidate: Mapping[str, Mapping[str, Any]] | None = None,
    reachable_candidate_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Target outcome-blind additions to one immutable child-law trial."""
    selected, used, used_ciks = [], set(), set()
    excluded_ciks = excluded_ciks or set()
    support_by_candidate = support_by_candidate or {}
    candidates = sorted(trial.get("candidates") or (), key=lambda row: (
        sum(max(0, 4 - int(support_by_candidate.get(
            str(row["candidate_identity_sha256"]), {},
        ).get(field) or 0)) for field in (
            "treated_entity_count", "future_adopter_entity_count",
        )),
        str(row["candidate_identity_sha256"]),
    ))
    for candidate in candidates:
        candidate_sha = str(candidate["candidate_identity_sha256"])
        if reachable_candidate_ids is not None and candidate_sha not in reachable_candidate_ids:
            continue
        identity = candidate["candidate_identity"]
        parent = identity["parent"]
        year = int(parent["adoption_year"])
        support = support_by_candidate.get(candidate_sha, {})
        occupied = {
            *candidate["training_treated_entity_ids"],
            *candidate["training_future_adopter_entity_ids"],
            *excluded_ciks,
        }
        for relation in ("treated", "future_adopter"):
            support_field = f"{relation}_entity_count"
            if int(support.get(support_field) or 0) >= 4:
                continue
            reserved = set(map(str, candidate.get(
                f"reserved_{relation}_entity_ids", (),
            )))
            choices = []
            for event in events:
                accession, cik = str(event["accession_number"]), str(event["cik"])
                event_year = int(event["occurred_at"][:4])
                periods = {int(value[:4]) for value in coverage.get(cik, ())}
                if (
                    accession in acquired or accession in used or cik in occupied or cik in used_ciks
                    or (reserved and cik not in reserved)
                    or (str(event.get("sic") or "")[:2] or "unknown") != parent["sic2"]
                    or sum(value < event_year for value in periods) < 3
                    or sum(value > event_year for value in periods) < 1
                    or (relation == "treated" and event_year != year)
                    or (relation == "future_adopter" and event_year <= year)
                ):
                    continue
                choices.append((abs(event_year - year), event["available_at"], accession, event))
            if not choices:
                continue
            *_order, event = min(choices, key=lambda row: row[:3])
            used.add(str(event["accession_number"]))
            used_ciks.add(str(event["cik"]))
            selected.append({
                **event,
                "selection_rank": len(selected) + 1,
                "selection_mode": "sealed_law_trial_holdout",
                "selection_basis": {
                    "trial_id": trial["trial_id"],
                    "trial_sha256": trial["trial_sha256"],
                    "candidate_identity_sha256": candidate["candidate_identity_sha256"],
                    "target_parent": parent,
                    "target_moderators": identity["moderators"],
                    "candidate_relation": relation,
                    "boundary": (
                        "Selection uses only filing metadata and accounting coverage. "
                        "The document may reject the frozen phenotype match."
                    ),
                },
            })
            if len(selected) >= limit:
                return selected
    return selected


def _law_trial_support_frontier(
    events: list[dict[str, Any]], acquired: set[str], trial: Mapping[str, Any],
    coverage: Mapping[str, list[str]], support_by_candidate: Mapping[str, Mapping[str, Any]],
    excluded_ciks: set[str],
) -> list[dict[str, Any]]:
    """Bound whether untouched filing metadata can still satisfy each trial arm."""
    rows = []
    for candidate in trial.get("candidates") or ():
        candidate_sha = str(candidate["candidate_identity_sha256"])
        identity = candidate["candidate_identity"]
        parent = identity["parent"]
        year = int(parent["adoption_year"])
        support = support_by_candidate.get(candidate_sha, {})
        reserved = {
            role: set(map(str, candidate.get(f"reserved_{role}_entity_ids", ())))
            for role in ("treated", "future_adopter")
        }
        training = {
            *map(str, candidate["training_treated_entity_ids"]),
            *map(str, candidate["training_future_adopter_entity_ids"]),
        }
        remaining = {"treated": set(), "future_adopter": set()}
        for event in events:
            accession, cik = str(event["accession_number"]), str(event["cik"])
            event_year = int(event["occurred_at"][:4])
            periods = {int(value[:4]) for value in coverage.get(cik, ())}
            if (
                accession in acquired or cik in training or cik in excluded_ciks
                or (str(event.get("sic") or "")[:2] or "unknown") != parent["sic2"]
                or sum(value < event_year for value in periods) < 3
                or sum(value > event_year for value in periods) < 1
            ):
                continue
            if event_year == year and (not reserved["treated"] or cik in reserved["treated"]):
                remaining["treated"].add(cik)
            elif event_year > year and (
                not reserved["future_adopter"] or cik in reserved["future_adopter"]
            ):
                remaining["future_adopter"].add(cik)
        current = {
            "treated": int(support.get("treated_entity_count") or 0),
            "future_adopter": int(support.get("future_adopter_entity_count") or 0),
        }
        maximum = {
            role: current[role] + len(remaining[role])
            for role in ("treated", "future_adopter")
        }
        body = {
            "candidate_identity_sha256": candidate_sha,
            "current_support": current,
            "remaining_metadata_entity_count": {
                role: len(remaining[role]) for role in remaining
            },
            "support_upper_bound": maximum,
            "status": (
                "metadata_support_reachable"
                if min(maximum.values()) >= 4
                else "metadata_support_exhausted"
            ),
            "boundary": (
                "An upper bound only: filing text may reject a metadata candidate's "
                "frozen phenotype. A bound below four proves this trial arm cannot settle."
            ),
        }
        rows.append({**body, "support_frontier_sha256": stable_sha256(body)})
    return rows


def compile_bulk_strategy_learning_queue(
    workspace: str | Path, *, queue_limit: int = 128,
) -> dict[str, Any]:
    """Compile a diverse, outcome-mature document queue without survivor conditioning."""
    if queue_limit < 1:
        raise ValueError("bulk strategy queue limit must be positive")
    root = Path(workspace).expanduser().resolve()
    corpus = _checked_json(
        root / "institutional_learning" / "historical_strategy_bulk_corpus" / "latest.json",
        "corpus_sha256",
    )
    if corpus.get("schema") != HISTORICAL_STRATEGY_BULK_CORPUS_SCHEMA:
        raise ValueError("bulk strategy corpus schema is incompatible")
    events = _events(root, corpus)
    cells, candidates = _cohort_rows(events)
    known = _classification_paths(root)
    deterministic_by_accession = {}
    deterministic_paths = [
        *(root / "institutional_learning" / "historical_strategy_event_replay" / "filings").glob("*.json"),
        *(root / _ROOT / "classifications").glob("*.json"),
    ]
    for path in deterministic_paths:
        try:
            row = _checked_json(path, "classification_receipt_sha256")
            deterministic_by_accession[str(row.get("accession_number") or path.stem)] = row
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    deterministic_rows = list(deterministic_by_accession.values())
    current_semantic_accessions = set()
    for path in (root / _ROOT / "semantic_resolutions").glob("*.json"):
        try:
            semantic = json.loads(path.read_text(encoding="utf-8"))
            accession = str(semantic.get("accession_number") or "")
            if accession in deterministic_by_accession and _semantic_matches_classification(
                semantic, deterministic_by_accession[accession],
            ):
                current_semantic_accessions.add(accession)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    acquired = set(deterministic_by_accession) | set(known)
    panel_path = root / "institutional_learning" / "historical_strategy_bulk_outcomes" / "panel-readiness.json"
    panel = json.loads(panel_path.read_text(encoding="utf-8")) if panel_path.is_file() else {}
    coverage_path = root / "institutional_learning" / "historical_strategy_bulk_outcomes" / "coverage.json"
    coverage_artifact = (
        json.loads(coverage_path.read_text(encoding="utf-8"))
        if coverage_path.is_file() else {}
    )
    coverage = {
        str(row["cik"]): list(row["complete_periods"])
        for row in coverage_artifact.get("entities", [])
    }
    law_search_path = (
        root / "institutional_learning" / "historical_strategy_bulk_outcomes"
        / "law-search.json"
    )
    law_search = _checked_json(law_search_path, "law_search_sha256") \
        if law_search_path.is_file() else {}
    if law_search.get("panel_readiness_sha256") != panel.get("readiness_sha256"):
        law_search = {}
    trial_path = root / "institutional_learning" / "historical_strategy_bulk_outcomes" / "law-trials" / "current.json"
    trial = _checked_json(trial_path, "trial_sha256") if trial_path.is_file() else {}
    excluded_trial_ciks = {
        str(cik)
        for candidate in trial.get("candidates") or ()
        for cik in (
            *candidate.get("training_treated_entity_ids", ()),
            *candidate.get("training_future_adopter_entity_ids", ()),
        )
    }
    latest_trial_epoch: dict[str, Any] = {}
    if trial:
        epoch_root = trial_path.parent / str(trial["trial_id"]) / "epochs"
        for epoch_path in epoch_root.glob("*.json"):
            epoch = _checked_json(epoch_path, "epoch_sha256")
            if epoch.get("trial_sha256") != trial.get("trial_sha256"):
                continue
            if str(epoch.get("evaluated_at") or "") > str(
                latest_trial_epoch.get("evaluated_at") or ""
            ):
                latest_trial_epoch = epoch
            for row in epoch.get("results") or ():
                support = row.get("support") or {}
                excluded_trial_ciks.update(map(str, (
                    *support.get("treated_entity_ids", ()),
                    *support.get("future_adopter_entity_ids", ()),
                )))
    trial_support = {
        str(row["candidate_identity_sha256"]): dict(row.get("support") or {})
        for row in latest_trial_epoch.get("results") or ()
    }
    trial_support_frontier = _law_trial_support_frontier(
        events, acquired, trial, coverage, trial_support, excluded_trial_ciks,
    ) if trial else []
    reachable_trial_candidates = {
        str(row["candidate_identity_sha256"])
        for row in trial_support_frontier
        if row["status"] == "metadata_support_reachable"
    }
    reserved_trial_ciks = {
        str(cik) for candidate in trial.get("candidates") or ()
        for key in ("reserved_treated_entity_ids", "reserved_future_adopter_entity_ids")
        for cik in candidate.get(key) or ()
    }
    reserved_trial_accessions = {
        str(event["accession_number"]) for event in events
        if str(event["cik"]) in reserved_trial_ciks
    }
    non_trial_acquired = acquired | reserved_trial_accessions
    identity_limit = min(queue_limit, max(1, round(queue_limit * 0.25)))
    identity = _select_identity_closure(
        events, non_trial_acquired, panel, identity_limit,
    )
    selected_accessions = {str(row["accession_number"]) for row in identity}
    frontier_limit = min(
        queue_limit - len(identity), max(1, round(queue_limit * 0.20)),
    )
    frontier = _select_panel_frontier(
        events, non_trial_acquired | selected_accessions, panel, coverage,
        frontier_limit,
    )
    selected_accessions.update(str(row["accession_number"]) for row in frontier)
    trial_limit = min(
        queue_limit - len(identity) - len(frontier),
        max(1, round(queue_limit * 0.25)) if trial else 0,
    )
    trial_holdout = _select_law_trial_holdout(
        events, acquired | selected_accessions, trial, coverage, trial_limit,
        excluded_trial_ciks, trial_support, reachable_trial_candidates,
    )
    selected_accessions.update(str(row["accession_number"]) for row in trial_holdout)
    phenotype_limit = min(
        queue_limit - len(identity) - len(frontier) - len(trial_holdout),
        max(1, round(queue_limit * 0.10)),
    )
    phenotype = _select_phenotype_frontier(
        events, non_trial_acquired | selected_accessions, law_search, coverage,
        phenotype_limit,
    )
    selected_accessions.update(str(row["accession_number"]) for row in phenotype)
    closure_limit = min(
        queue_limit - len(identity) - len(frontier) - len(trial_holdout) - len(phenotype),
        max(1, round(queue_limit * 0.10)),
    )
    closure = _select_history_closure(
        events, non_trial_acquired | selected_accessions, closure_limit,
    )
    selected_accessions.update(str(row["accession_number"]) for row in closure)
    exploration = _select_diverse(
        candidates, non_trial_acquired | selected_accessions,
        queue_limit - len(identity) - len(frontier) - len(trial_holdout) - len(phenotype) - len(closure),
    )
    lanes = {
        "identity": iter(identity), "frontier": iter(frontier), "trial": iter(trial_holdout),
        "closure": iter(closure),
        "phenotype": iter(phenotype), "exploration": iter(exploration),
    }
    queue = []
    pattern = (
        "identity", "frontier", "trial", "phenotype", "closure",
        "identity", "trial", "frontier", "exploration",
    )
    while len(queue) < queue_limit:
        before = len(queue)
        for lane in pattern:
            try:
                queue.append(next(lanes[lane]))
            except StopIteration:
                continue
            if len(queue) >= queue_limit:
                break
        if len(queue) == before:
            break
    for rank, row in enumerate(queue, start=1):
        row["selection_rank"] = rank
        row.setdefault("selection_mode", "cross_sectional_exploration")
    reservation_leaks = [
        row for row in queue
        if str(row.get("cik") or "") in reserved_trial_ciks
        and row.get("selection_mode") != "sealed_law_trial_holdout"
    ]
    if reservation_leaks:
        raise ValueError("a non-trial acquisition lane consumed a reserved trial issuer")
    trial_status = "no_active_trial"
    if trial:
        if any(
            row.get("status") == "sealed_holdout_scored"
            for row in latest_trial_epoch.get("results") or ()
        ):
            trial_status = "sealed_holdout_scored"
        elif trial_support_frontier and all(
            row["status"] == "metadata_support_exhausted"
            for row in trial_support_frontier
        ):
            trial_status = "support_exhausted"
        else:
            trial_status = "collecting_sealed_holdout_support"
    unresolved_ambiguous = [
        row for row in deterministic_rows
        if row.get("classification") == "ambiguous"
        and str(row.get("accession_number") or "") not in current_semantic_accessions
    ]
    body = {
        "schema": HISTORICAL_STRATEGY_BULK_LEARNING_SCHEMA,
        "generated_at": corpus["generated_at"],
        "bulk_corpus_sha256": corpus["corpus_sha256"],
        "event_population_count": len(events),
        "first_family_adoption_count": len({row["cik"] for row in events}),
        "design_cell_count": len(cells),
        "supported_design_cell_count": sum(row["structurally_supported"] for row in cells),
        "outcome_mature_supported_candidate_count": len(candidates),
        "classified_event_count": len(set(known) & {str(row["accession_number"]) for row in events}),
        "deterministic_classification_count": len(deterministic_rows),
        "semantic_resolution_count": len(current_semantic_accessions),
        "ambiguous_semantic_queue_count": len(unresolved_ambiguous),
        "sealed_law_trial_ambiguous_queue_count": sum(
            _is_current_trial_selection(
                row, str(trial.get("trial_sha256") or ""),
            )
            for row in unresolved_ambiguous
        ),
        "queue_count": len(queue), "queue": queue,
        "treatment_identity_closure_queue_count": len(identity),
        "causal_panel_frontier_queue_count": len(frontier),
        "sealed_law_trial_holdout_queue_count": len(trial_holdout),
        "sealed_law_trial_id": trial.get("trial_id"),
        "sealed_law_trial_sha256": trial.get("trial_sha256"),
        "sealed_law_trial_status": trial_status,
        "sealed_law_trial_reserved_issuer_count": len(reserved_trial_ciks),
        "sealed_law_trial_reservation_embargoed_accession_count": len(
            reserved_trial_accessions
        ),
        "sealed_law_trial_support_frontier": trial_support_frontier,
        "sealed_law_trial_reachable_candidate_count": len(
            reachable_trial_candidates
        ),
        "sealed_law_trial_exhausted_candidate_count": sum(
            row["status"] == "metadata_support_exhausted"
            for row in trial_support_frontier
        ),
        "phenotype_refinement_frontier_queue_count": len(phenotype),
        "history_closure_queue_count": len(closure),
        "cross_sectional_exploration_queue_count": len(exploration),
        "outcome_coverage_sha256": coverage_artifact.get("coverage_sha256"),
        "law_search_sha256": law_search.get("law_search_sha256"),
        "selection_contract": {
            "treatment_identity": "first_observed_granular_phenotype_adoption_after_issuer_history_closure",
            "control_identity": "same_sic2_future_family_adopter_prefilter",
            "minimum_treated_entities": 4, "minimum_future_adopters": 4,
            "maximum_adoption_year": 2024,
            "ranking": "25% treatment-identity closure; 20% causal-panel frontier; 25% sealed child-law holdout; 10% phenotype refinement; 10% issuer-history closure; remaining capacity for exploration",
            "boundary": "Generic Item 2.01 order cannot establish granular first adoption; document classification and issuer-history closure are required. This prefilter cannot estimate an effect.",
        },
        "next_activation": (
            "Compile a fresh outcome-blind trial design or widen the typed law universe; "
            "the current sealed cohort cannot reach minimum support."
            if trial_status == "support_exhausted"
            else "Hydrate and type the queued filing documents, then select outcome joins within supported phenotype cohorts."
        ),
        "causal_estimate_ran": False, "promotion_eligible": False,
        "paper_policy_authority": False, "capital_authority": False,
    }
    result = {**body, "learning_queue_sha256": stable_sha256(body)}
    _atomic_json(root / _ROOT / "latest.json", result)
    return result


def acquire_bulk_strategy_documents(
    workspace: str | Path, *, limit: int = 8,
) -> dict[str, Any]:
    """Fetch and deterministically type the next bounded queue tranche."""
    if limit < 0:
        raise ValueError("bulk strategy acquisition limit cannot be negative")
    root = Path(workspace).expanduser().resolve()
    plan = compile_bulk_strategy_learning_queue(root)
    acquired, errors = [], []
    for event in plan["queue"][:limit]:
        try:
            filing = fetch_sec_filing_document(
                root,
                source_id=f"sec_bulk_strategy_{event['cik']}_{str(event['accession_number'])[-6:]}",
                cik=str(event["cik"]), accession_number=str(event["accession_number"]),
                primary_document=str(event["primary_document"]),
                accepted_at=str(event["available_at"]),
            )
            classification = classify_sec_item_201(
                (root / str(filing["receipt"]["raw_path"])).read_bytes()
            )
            selection_body = {
                "learning_queue_sha256": plan["learning_queue_sha256"],
                "event_sha256": event["event_sha256"],
                "accession_number": event["accession_number"],
                "selection_rank": event["selection_rank"],
                "selection_mode": event.get("selection_mode", "diverse_exploration"),
                "selection_basis": event.get("selection_basis") or {},
            }
            selection_receipt = {
                **selection_body,
                "selection_receipt_sha256": stable_sha256(selection_body),
            }
            body = {
                "schema": "jaggedthoughts-historical-strategy-bulk-classification-v1",
                "admitted_at": _utc_now(),
                "event_sha256": event["event_sha256"],
                "accession_number": event["accession_number"],
                "cik": event["cik"], "sic": event["sic"],
                "filing_document_sha256": filing["filing_document_sha256"],
                "filing_source_receipt": filing["receipt"],
                "acquisition_selection_receipt": selection_receipt,
                **classification,
            }
            receipt = {**body, "classification_receipt_sha256": stable_sha256(body)}
            path = root / _ROOT / "classifications" / f"{str(event['accession_number']).replace('-', '')}.json"
            _atomic_json(path, receipt)
            acquired.append(receipt)
        except (OSError, TypeError, ValueError) as error:
            errors.append({
                "event_sha256": event["event_sha256"],
                "accession_number": event["accession_number"],
                "error": f"{type(error).__name__}: {error}"[:1_000],
            })
    successor = compile_bulk_strategy_learning_queue(root)
    body = {
        "schema": "jaggedthoughts-historical-strategy-bulk-acquisition-v1",
        "executed_at": _utc_now(), "prior_queue_sha256": plan["learning_queue_sha256"],
        "selected_count": min(limit, len(plan["queue"])),
        "acquired_count": len(acquired), "error_count": len(errors),
        "acquired": acquired, "errors": errors,
        "successor_queue_sha256": successor["learning_queue_sha256"],
        "capital_authority": False,
    }
    result = {**body, "acquisition_sha256": stable_sha256(body)}
    _atomic_json(root / _ROOT / "acquisition-latest.json", result)
    return {"queue": successor, "acquisition": result}


def _semantic_prompt(rows: list[dict[str, Any]]) -> str:
    compact = [{
        "accession_number": row["accession_number"],
        "registrant_cik": row["cik"],
        "sic": row["sic"],
        "filed_context": row["filed_context"],
    } for row in rows]
    return """You are a bounded SEC transaction-classification leaf. Use only the filed text supplied below.
Classify each Item 2.01 event from the REGISTRANT'S perspective. Copy 1-3 exact verbatim evidence quotes.
Eligible operating events require an explicitly completed acquisition, disposition, separation, partnership, or mixed reallocation by the registrant.
Exclude a de-SPAC, reverse merger, shell recapitalization, or transaction whose main effect is changing/listing the registrant identity as excluded_identity_transition.
Exclude agreements that are not shown as completed, financial-right transfers, and non-event documents. If direction, completion, or registrant role cannot be established from the text, return ambiguous / requires_more_filed_context.
Do not infer strategic quality, performance, or causality. Return exactly the requested JSON schema.

EVENTS:
""" + json.dumps(compact, ensure_ascii=False, sort_keys=True)


def resolve_bulk_strategy_ambiguities(
    workspace: str | Path, *, limit: int = 4, timeout_seconds: int = 300,
    accession_numbers: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Resolve a bounded ambiguous tranche with a sealed Codex subscription leaf."""
    if limit < 0:
        raise ValueError("semantic resolution limit cannot be negative")
    root = Path(workspace).expanduser().resolve()
    resolution_root = root / _ROOT / "semantic_resolutions"
    trial_path = (
        root / "institutional_learning" / "historical_strategy_bulk_outcomes"
        / "law-trials" / "current.json"
    )
    trial = _checked_json(trial_path, "trial_sha256") if trial_path.is_file() else {}
    event_lake = json.loads((
        root / "institutional_learning" / "historical_strategy_bulk_corpus" / "latest.json"
    ).read_text(encoding="utf-8"))["event_lake_path"]
    bulk_events = {
        str(row["accession_number"]): row
        for line in (root / event_lake).read_text(encoding="utf-8").splitlines() if line
        for row in (json.loads(line),)
    }
    rows, seen = [], set()
    requested = {str(value) for value in accession_numbers or ()}
    candidate_by_accession = {}
    for path in [
        *(root / "institutional_learning" / "historical_strategy_event_replay" / "filings").glob("*.json"),
        *(root / _ROOT / "classifications").glob("*.json"),
    ]:
        row = _checked_json(path, "classification_receipt_sha256")
        accession = str(row.get("accession_number") or "")
        if accession:
            candidate_by_accession[accession] = (path, row)
    candidate_rows = [
        (
            _semantic_resolution_priority(row, str(trial.get("trial_sha256") or "")),
            path, row,
        )
        for path, row in candidate_by_accession.values()
    ]
    for _priority, path, row in sorted(candidate_rows, key=lambda item: item[0]):
        destination = resolution_root / path.name
        accession = str(row.get("accession_number") or "")
        current_resolution = None
        if destination.is_file():
            try:
                candidate = json.loads(destination.read_text(encoding="utf-8"))
                if _semantic_matches_classification(candidate, row):
                    current_resolution = candidate
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                pass
        if (
            not accession or accession in seen
            or (requested and accession not in requested)
            or row.get("classification") != "ambiguous" or current_resolution is not None
        ):
            continue
        seen.add(accession)
        raw_path = (root / str((row.get("filing_source_receipt") or {}).get("raw_path") or "")).resolve()
        raw_path.relative_to(root)
        content = raw_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != (row.get("filing_source_receipt") or {}).get("content_sha256"):
            raise ValueError("semantic resolution filing bytes do not match their source receipt")
        event = bulk_events.get(str(row["accession_number"]), {})
        rows.append({
            **row,
            "cik": str(row.get("cik") or event.get("cik") or "unknown"),
            "sic": str(row.get("sic") or event.get("sic") or "unknown"),
            "filed_context": extract_sec_item_201_context(content),
        })
        if len(rows) >= limit:
            break
    if not rows:
        queue = compile_bulk_strategy_learning_queue(root)
        return {"status": "no_ambiguous_documents_due", "resolved_count": 0, "queue": queue}

    run_root = root / _ROOT / "agent_runs" / stable_sha256([
        row["classification_receipt_sha256"] for row in rows
    ])[:20]
    run_root.mkdir(parents=True, exist_ok=True)
    output_path = run_root / "last-message.json"
    schema_path = Path(__file__).resolve().parents[3] / "schemas" / "investment" / "strategy_event_semantic_resolution.schema.json"
    dispatch_path = run_root / "dispatch.json"
    dispatch = (
        json.loads(dispatch_path.read_text(encoding="utf-8"))
        if dispatch_path.is_file() else {}
    )
    if not (output_path.is_file() and dispatch.get("status") == "completed"):
        run = run_subscription_agent_with_recovery(
            runtime="codex", prompt=_semantic_prompt(rows),
            agent_id=f"jaggedthoughts-strategy-semantic::{run_root.name}",
            repo=Path(__file__).resolve().parents[3], session_state=None,
            timeout_seconds=timeout_seconds, default_codex_model="account-default",
            codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION,
            output_schema=schema_path, output_last_message_path=output_path,
            dispatch_receipt_path=dispatch_path,
            stdout_path=str(run_root / "stdout.log"), stderr_path=str(run_root / "stderr.log"),
        )
        if run.result.returncode != 0 or not output_path.exists():
            raise RuntimeError(
                f"Codex subscription semantic leaf failed with return code {run.result.returncode}"
            )
    output = json.loads(output_path.read_text(encoding="utf-8"))
    proposals = {str(row["accession_number"]): row for row in output.get("resolutions") or ()}
    expected = {str(row["accession_number"]): row for row in rows}
    if set(proposals) != set(expected):
        raise ValueError("semantic leaf output changed the requested accession set")
    eligible = {
        "acquisition_completion", "disposition_completion", "partnership_completion",
        "separation_completion", "portfolio_reconfiguration_completion",
    }
    resolved = []
    for accession, proposal in sorted(proposals.items()):
        source = expected[accession]
        context = source["filed_context"]
        quotes = [str(row.get("quote") or "") for row in proposal.get("evidence") or ()]
        if not quotes or any(quote not in context for quote in quotes):
            raise ValueError(f"semantic leaf evidence is not verbatim filed text for {accession}")
        if proposal["classification"] in eligible and (
            proposal["completion_state"] != "completed"
            or proposal["strategy_event_eligibility"] not in {
                "operating_strategy_event", "operating_strategy_bundle_event",
            }
        ):
            raise ValueError(f"semantic leaf returned inconsistent eligible status for {accession}")
        body = {
            "schema": "jaggedthoughts-strategy-event-semantic-resolution-v1",
            "resolved_at": _utc_now(),
            "event_sha256": source["event_sha256"], "accession_number": accession,
            "filing_document_sha256": source["filing_document_sha256"],
            "deterministic_classification_receipt_sha256": source["classification_receipt_sha256"],
            "transport": "codex_subscription_cli", "model": "account_default",
            "source_span_verification": "all_evidence_quotes_exact_substrings",
            "adjudication_status": "source_span_verified_agent_label",
            **canonicalize_strategy_event_phenotype(proposal),
            "evidence": proposal["evidence"], "reasoning": proposal["reasoning"],
            "agent_proposal": proposal,
            "capital_authority": False,
        }
        receipt = {**body, "semantic_resolution_sha256": stable_sha256(body)}
        _atomic_json(resolution_root / f"{accession.replace('-', '')}.json", receipt)
        resolved.append(receipt)
    queue = compile_bulk_strategy_learning_queue(root)
    body = {
        "schema": "jaggedthoughts-strategy-event-semantic-resolution-run-v1",
        "executed_at": _utc_now(), "transport": "codex_subscription_cli",
        "input_accessions": sorted(expected), "resolved_count": len(resolved),
        "resolution_sha256s": [row["semantic_resolution_sha256"] for row in resolved],
        "successor_queue_sha256": queue["learning_queue_sha256"],
        "capital_authority": False,
    }
    result = {**body, "run_sha256": stable_sha256(body)}
    _atomic_json(run_root / "result.json", result)
    return {**result, "resolutions": resolved, "queue": queue}


__all__ = [
    "HISTORICAL_STRATEGY_BULK_LEARNING_SCHEMA",
    "acquire_bulk_strategy_documents", "compile_bulk_strategy_learning_queue",
    "resolve_bulk_strategy_ambiguities",
]
