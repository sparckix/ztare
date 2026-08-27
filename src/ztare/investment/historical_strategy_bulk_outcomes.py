"""Revision-aware SEC accounting observations for the strategy-event population."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
import zipfile

from ztare.common.equivariance import stable_sha256

from .historical_strategy_bulk_corpus import HISTORICAL_STRATEGY_BULK_CORPUS_SCHEMA
from .historical_strategy_event_replay import canonicalize_strategy_event_phenotype
from .sources import parse_sec_companyfacts


HISTORICAL_STRATEGY_BULK_OUTCOMES_SCHEMA = (
    "jaggedthoughts-historical-strategy-bulk-outcomes-v2"
)
HISTORICAL_STRATEGY_PANEL_READINESS_SCHEMA = (
    "jaggedthoughts-historical-strategy-panel-readiness-v10"
)
_ROOT = Path("institutional_learning/historical_strategy_bulk_outcomes")
_OWNER_EARNINGS_INPUTS = {
    "revenue_fy", "operating_cash_flow_fy", "capital_expenditure_fy",
}
_OBSERVATION_PARSER_REVISION = "sec-companyfacts-chronology-v2"
_SELECTIONS = [
    {"metric_id": "revenue_fy", "taxonomy": "us-gaap", "concept": "RevenueFromContractWithCustomerExcludingAssessedTax", "fallback_concepts": ["Revenues", "SalesRevenueNet"], "source_unit": "USD", "unit": "USD/year", "period": "annual"},
    {"metric_id": "operating_cash_flow_fy", "taxonomy": "us-gaap", "concept": "NetCashProvidedByUsedInOperatingActivities", "source_unit": "USD", "unit": "USD/year", "period": "annual"},
    {"metric_id": "capital_expenditure_fy", "taxonomy": "us-gaap", "concept": "PaymentsToAcquirePropertyPlantAndEquipment", "fallback_concepts": ["PaymentsForAdditionsToPropertyPlantAndEquipment"], "source_unit": "USD", "unit": "USD/year", "period": "annual"},
    {"metric_id": "net_income_fy", "taxonomy": "us-gaap", "concept": "NetIncomeLoss", "source_unit": "USD", "unit": "USD/year", "period": "annual"},
]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _checked(path: Path, digest_field: str) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    body = dict(row)
    declared = str(body.pop(digest_field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{path.name} content hash mismatch")
    return row


def _companyfacts_members(
    bundle: zipfile.ZipFile,
) -> tuple[dict[str, str], dict[str, tuple[int, int]]]:
    members, signatures = {}, {}
    for info in bundle.infolist():
        name = Path(info.filename).name
        if not name.startswith("CIK") or not name.endswith(".json"):
            continue
        cik = name.removeprefix("CIK").removesuffix(".json")
        members[cik] = info.filename
        signatures[cik] = (info.CRC, info.file_size)
    return members, signatures


def compile_bulk_strategy_outcome_observations(workspace: str | Path) -> dict[str, Any]:
    """Extract the four annual owner-earnings inputs for every event issuer."""
    root = Path(workspace).expanduser().resolve()
    corpus = _checked(
        root / "institutional_learning" / "historical_strategy_bulk_corpus" / "latest.json",
        "corpus_sha256",
    )
    if corpus.get("schema") != HISTORICAL_STRATEGY_BULK_CORPUS_SCHEMA:
        raise ValueError("bulk strategy outcome compiler requires the current corpus schema")
    companyfacts = _checked(
        root / "sources" / "bulk" / "sec_companyfacts" / "latest.json",
        "receipt_sha256",
    )
    archive = (root / str(companyfacts["raw_path"])).resolve()
    archive.relative_to(root)
    if _file_sha256(archive) != companyfacts["content_sha256"]:
        raise ValueError("SEC bulk Company Facts archive hash mismatch")
    event_path = (root / str(corpus["event_lake_path"])).resolve()
    event_path.relative_to(root)
    ciks = sorted({
        str(json.loads(line)["cik"])
        for line in event_path.read_text(encoding="utf-8").splitlines() if line
    })
    transform_sha = stable_sha256({
        "companyfacts_receipt_sha256": companyfacts["receipt_sha256"],
        "companyfacts_content_sha256": companyfacts["content_sha256"],
        "bulk_corpus_sha256": corpus["corpus_sha256"],
        "observation_parser_revision": _OBSERVATION_PARSER_REVISION,
    })
    latest_path = root / _ROOT / "latest.json"
    prior = None
    prior_lake = None
    if latest_path.exists():
        prior = json.loads(latest_path.read_text(encoding="utf-8"))
        lake = (root / str(prior.get("observation_lake_path") or "")).resolve()
        try:
            lake.relative_to(root)
            reusable = (
                prior.get("schema") in {
                    HISTORICAL_STRATEGY_BULK_OUTCOMES_SCHEMA,
                    "jaggedthoughts-historical-strategy-bulk-outcomes-v1",
                }
                and prior.get("bulk_corpus_sha256") == corpus["corpus_sha256"]
                and prior.get("companyfacts_receipt_sha256") == companyfacts["receipt_sha256"]
                and prior.get("observation_parser_revision")
                == _OBSERVATION_PARSER_REVISION
                and lake.is_file()
                and _file_sha256(lake) == prior.get("observation_lake_sha256")
            )
            if reusable:
                body = {
                    **{key: value for key, value in prior.items() if key != "outcomes_sha256"},
                    "schema": HISTORICAL_STRATEGY_BULK_OUTCOMES_SCHEMA,
                    "uncovered_no_selected_facts_count": (
                        len(ciks) - int(prior["covered_entity_count"])
                        - int(prior["missing_entity_count"])
                    ),
                    "compilation_mode": str(
                        prior.get("compilation_mode") or "full_archive_rebuild"
                    ),
                    "reparsed_entity_count": int(
                        prior.get("reparsed_entity_count")
                        if prior.get("reparsed_entity_count") is not None
                        else prior.get("event_entity_count") or len(ciks)
                    ),
                    "companyfacts_content_sha256": companyfacts["content_sha256"],
                    "transform_sha256": transform_sha,
                    "observation_parser_revision": _OBSERVATION_PARSER_REVISION,
                }
                if prior.get("schema") == HISTORICAL_STRATEGY_BULK_OUTCOMES_SCHEMA and all(
                    prior.get(field) is not None
                    for field in ("uncovered_no_selected_facts_count", "compilation_mode",
                                  "reparsed_entity_count", "companyfacts_content_sha256",
                                  "transform_sha256", "observation_parser_revision")
                ):
                    return prior
                migrated = {**body, "outcomes_sha256": stable_sha256(body)}
                _atomic_json(latest_path, migrated)
                return migrated
            if (
                prior.get("schema") == HISTORICAL_STRATEGY_BULK_OUTCOMES_SCHEMA
                and prior.get("observation_parser_revision")
                == _OBSERVATION_PARSER_REVISION
                and lake.is_file()
                and _file_sha256(lake) == prior.get("observation_lake_sha256")
            ):
                prior_lake = lake
        except (OSError, ValueError):
            pass

    destination = (
        root / _ROOT
        / f"observations-{companyfacts['content_sha256'][:12]}-{transform_sha[:12]}.jsonl"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    metric_counts: Counter[str] = Counter()
    covered_ciks: set[str] = set()
    missing = []
    observation_count = 0
    compilation_mode = "full_archive_rebuild"
    reparsed_ciks: set[str] = set(ciks)
    with zipfile.ZipFile(archive) as bundle, temporary.open("w", encoding="utf-8") as output:
        members, signatures = _companyfacts_members(bundle)
        previous_archive = None
        if prior_lake is not None:
            prefix = str(
                (prior or {}).get("companyfacts_content_sha256")
                or prior_lake.stem.removeprefix("observations-").split("-", 1)[0]
            )[:20]
            previous_archive = next(iter(sorted(
                (root / "sources/bulk/sec_companyfacts").glob(
                    f"companyfacts-{prefix}*.zip"
                )
            )), None)
        if previous_archive is not None:
            with zipfile.ZipFile(previous_archive) as previous:
                _, previous_signatures = _companyfacts_members(previous)
            reparsed_ciks = {
                cik for cik in ciks
                if signatures.get(cik) != previous_signatures.get(cik)
            }
            eligible = set(ciks)
            prior_present_ciks: set[str] = set()
            with prior_lake.open(encoding="utf-8") as prior_rows:
                for line in prior_rows:
                    row = json.loads(line)
                    cik = str(row["cik"])
                    if cik not in eligible:
                        continue
                    prior_present_ciks.add(cik)
                    if cik in reparsed_ciks:
                        continue
                    body = {
                        key: value for key, value in row.items()
                        if key != "observation_row_sha256"
                    }
                    body["companyfacts_receipt_sha256"] = companyfacts["receipt_sha256"]
                    output.write(json.dumps(
                        {**body, "observation_row_sha256": stable_sha256(body)},
                        sort_keys=True, ensure_ascii=False,
                    ) + "\n")
                    metric_counts[str(row["metric_id"])] += 1
                    observation_count += 1
                    covered_ciks.add(cik)
            reparsed_ciks.update(eligible - prior_present_ciks)
            compilation_mode = "incremental_changed_issuer_replay"
        for cik in ciks:
            if cik not in reparsed_ciks:
                continue
            member = members.get(cik)
            if member is None:
                missing.append(cik)
                continue
            source_id = f"sec_bulk_companyfacts_{cik}"
            observations = parse_sec_companyfacts(
                bundle.read(member),
                {"id": source_id, "entity_id": f"CIK{cik}", "selections": _SELECTIONS},
            )
            if observations:
                covered_ciks.add(cik)
            for row in sorted(observations, key=lambda value: (
                value.observed_at, value.available_at, value.metric_id, value.observation_id,
            )):
                body = {
                    "schema": "jaggedthoughts-bulk-sec-annual-observation-v1",
                    "cik": cik, **row.to_dict(),
                    "companyfacts_receipt_sha256": companyfacts["receipt_sha256"],
                }
                output.write(json.dumps(
                    {**body, "observation_row_sha256": stable_sha256(body)},
                    sort_keys=True, ensure_ascii=False,
                ) + "\n")
                metric_counts[row.metric_id] += 1
                observation_count += 1
    if destination.exists():
        if _file_sha256(destination) != _file_sha256(temporary):
            temporary.unlink()
            raise ValueError("SEC outcome-lake transform identity collision")
        temporary.unlink()
    else:
        temporary.replace(destination)
    body = {
        "schema": HISTORICAL_STRATEGY_BULK_OUTCOMES_SCHEMA,
        "generated_at": companyfacts["retrieved_at"],
        "bulk_corpus_sha256": corpus["corpus_sha256"],
        "companyfacts_receipt_sha256": companyfacts["receipt_sha256"],
        "companyfacts_content_sha256": companyfacts["content_sha256"],
        "transform_sha256": transform_sha,
        "observation_parser_revision": _OBSERVATION_PARSER_REVISION,
        "event_entity_count": len(ciks), "covered_entity_count": len(covered_ciks),
        "missing_entity_count": len(missing), "missing_ciks": missing,
        "uncovered_no_selected_facts_count": len(ciks) - len(covered_ciks) - len(missing),
        "compilation_mode": compilation_mode,
        "reparsed_entity_count": len(reparsed_ciks),
        "observation_count": observation_count,
        "metric_observation_counts": dict(sorted(metric_counts.items())),
        "metric_contract": {
            "owner_earnings": "operating_cash_flow_fy - capital_expenditure_fy",
            "owner_earnings_margin": "owner_earnings / revenue_fy",
            "revision_policy": "retain every accession-bound annual fact and filed-date availability",
        },
        "observation_lake_path": destination.relative_to(root).as_posix(),
        "observation_lake_sha256": _file_sha256(destination),
        "panel_status": "revision_aware_observation_lake_compiled",
        "next_activation": "Align the typed event cohort to pre/post annual observations and future-adopter controls.",
        "causal_estimate_ran": False, "promotion_eligible": False,
        "paper_policy_authority": False, "capital_authority": False,
    }
    result = {**body, "outcomes_sha256": stable_sha256(body)}
    _atomic_json(latest_path, result)
    return result


def compile_bulk_strategy_outcome_coverage(workspace: str | Path) -> dict[str, Any]:
    """Index issuers with complete annual owner-earnings input periods."""
    root = Path(workspace).expanduser().resolve()
    outcomes = _checked(root / _ROOT / "latest.json", "outcomes_sha256")
    latest_path = root / _ROOT / "coverage.json"
    if latest_path.exists():
        prior = _checked(latest_path, "coverage_sha256")
        if prior.get("observation_lake_sha256") == outcomes["observation_lake_sha256"]:
            return prior
    metrics: dict[tuple[str, str], set[str]] = defaultdict(set)
    lake_path = root / str(outcomes["observation_lake_path"])
    with lake_path.open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            if row["metric_id"] in _OWNER_EARNINGS_INPUTS:
                metrics[(str(row["cik"]), str(row["observed_at"]))].add(row["metric_id"])
    by_cik: dict[str, list[str]] = defaultdict(list)
    for (cik, observed_at), present in metrics.items():
        if present == _OWNER_EARNINGS_INPUTS:
            by_cik[cik].append(observed_at)
    entities = [
        {"cik": cik, "complete_periods": sorted(periods)}
        for cik, periods in sorted(by_cik.items())
    ]
    body = {
        "schema": "jaggedthoughts-historical-strategy-outcome-coverage-v1",
        "generated_at": outcomes["generated_at"],
        "bulk_outcomes_sha256": outcomes["outcomes_sha256"],
        "observation_lake_sha256": outcomes["observation_lake_sha256"],
        "metric_ids": sorted(_OWNER_EARNINGS_INPUTS),
        "covered_entity_count": len(entities), "entities": entities,
        "boundary": "Coverage establishes measurement availability, not treatment identity, comparability, or an effect.",
        "capital_authority": False,
    }
    result = {**body, "coverage_sha256": stable_sha256(body)}
    _atomic_json(latest_path, result)
    return result


def _typed_classifications(root: Path) -> tuple[dict[str, dict[str, Any]], str]:
    deterministic = {}
    for path in [
        *(root / "institutional_learning" / "historical_strategy_event_replay" / "filings").glob("*.json"),
        *(root / "institutional_learning" / "historical_strategy_bulk_learning" / "classifications").glob("*.json"),
    ]:
        row = json.loads(path.read_text(encoding="utf-8"))
        body = dict(row)
        declared = str(body.pop("classification_receipt_sha256", ""))
        if stable_sha256(body) != declared:
            raise ValueError("strategy classification receipt hash mismatch")
        deterministic[str(row["accession_number"])] = row
    semantic = {}
    for path in (
        root / "institutional_learning" / "historical_strategy_bulk_learning"
        / "semantic_resolutions"
    ).glob("*.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        body = dict(row)
        declared = str(body.pop("semantic_resolution_sha256", ""))
        if stable_sha256(body) != declared:
            raise ValueError("strategy semantic resolution hash mismatch")
        accession = str(row["accession_number"])
        prior = deterministic.get(accession)
        if (
            not prior
            or row.get("filing_document_sha256") != prior.get("filing_document_sha256")
            or row.get("deterministic_classification_receipt_sha256")
            != prior.get("classification_receipt_sha256")
        ):
            continue
        semantic[accession] = row
    typed = {
        accession: {
            **row,
            **canonicalize_strategy_event_phenotype(semantic.get(accession, row)),
            "classification_admitted_at": (
                semantic[accession].get("resolved_at") if accession in semantic
                else row.get("admitted_at")
            ),
            "classification_evidence_sha256": (
                semantic[accession]["semantic_resolution_sha256"]
                if accession in semantic else row["classification_receipt_sha256"]
            ),
        }
        for accession, row in deterministic.items()
        if row.get("classification") != "ambiguous" or accession in semantic
    }
    digest = stable_sha256(sorted(
        (accession, row["classification_evidence_sha256"])
        for accession, row in typed.items()
    ))
    return typed, digest


def strategy_history_periods(row: Mapping[str, Any]) -> set[int]:
    """Return comparable fiscal years, excluding the event's partial fiscal year."""
    event_year = int(row["event_year"])
    return {
        int(fact["observed_at"][:4]) for fact in row["annual_history"]
        if int(fact["observed_at"][:4]) != event_year
    }


def strategy_history_ready_at(row: Mapping[str, Any], year: int) -> bool:
    periods = strategy_history_periods(row)
    return (
        bool(row["phenotype_history_closed"])
        and row.get("coadoption_status") == "isolated_strategy_event"
        and sum(value < year for value in periods) >= 3
        and sum(value > year for value in periods) >= 1
    )


def _coadoption_audit(episodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Exclude strategy bundles that annual outcomes cannot disentangle."""
    by_entity_year: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        by_entity_year[(str(episode["cik"]), int(episode["occurred_at"][:4]))].append(episode)
    audit = {}
    for peers in by_entity_year.values():
        for episode in peers:
            concurrent = sorted({
                str(peer["event_sha256"])
                for peer in peers if peer["event_sha256"] != episode["event_sha256"]
            })
            status = (
                "excluded_bundle_event"
                if episode.get("strategy_event_eligibility") == "operating_strategy_bundle_event"
                else "excluded_concurrent_event" if concurrent
                else "isolated_strategy_event"
            )
            audit[str(episode["event_sha256"])] = {
                "coadoption_status": status,
                "concurrent_event_sha256s": concurrent,
                "coadoption_window": "same_event_year",
            }
    return audit


def compile_strategy_group_time_support(
    treated: list[dict[str, Any]], future: list[dict[str, Any]], year: int,
    bounded_controls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Find common support from future adopters and source-bounded non-adopters."""
    bounded = list(bounded_controls or ())

    def periods(row: Mapping[str, Any]) -> set[int]:
        values = strategy_history_periods(row)
        if row.get("control_through_year") is not None:
            values = {value for value in values if value <= int(row["control_through_year"])}
        return values

    candidates = sorted({
        value for row in [*treated, *future, *bounded] for value in periods(row)
    })
    designs = []
    for prior in (value for value in candidates if value < year):
        for base in (value for value in candidates if prior < value < year):
            treated_pre = [
                row for row in treated
                if {prior, base} <= periods(row)
            ]
            future_pre = [
                row for row in future
                if {prior, base} <= periods(row)
            ]
            bounded_pre = [
                row for row in bounded
                if {prior, base} <= periods(row)
            ]
            for post in (value for value in candidates if value > year):
                treated_post = [
                    row for row in treated_pre if post in periods(row)
                ]
                future_post = [
                    row for row in future_pre
                    if int(row["event_year"]) > post
                    and post in periods(row)
                ]
                bounded_post = [
                    row for row in bounded_pre if post in periods(row)
                ]
                designs.append({
                    "pre_periods": [prior, base], "post_period": post,
                    "pre_treated_count": len(treated_pre),
                    "pre_control_count": len(future_pre) + len(bounded_pre),
                    "post_treated_count": len(treated_post),
                    "post_control_count": len(future_post) + len(bounded_post),
                    "post_future_adopter_entity_ids": sorted(
                        str(row["cik"]) for row in future_post
                    ),
                    "post_bounded_control_ids": sorted(
                        str(row["control_id"]) for row in bounded_post
                    ),
                })
    if not designs:
        return {
            "pre_periods": [], "post_period": None,
            "pre_treated_count": 0, "pre_control_count": 0,
            "post_treated_count": 0, "post_control_count": 0,
            "post_future_adopter_entity_ids": [],
            "post_bounded_control_ids": [],
            "joint_support_ready": False,
        }
    best = max(designs, key=lambda row: (
        min(
            row["pre_treated_count"], row["pre_control_count"],
            row["post_treated_count"], row["post_control_count"],
        ),
        sum(min(4, row[key]) for key in (
            "pre_treated_count", "pre_control_count",
            "post_treated_count", "post_control_count",
        )),
        row["post_period"], row["pre_periods"][-1],
    ))
    return {
        **best,
        "joint_support_ready": all(best[key] >= 4 for key in (
            "pre_treated_count", "pre_control_count",
            "post_treated_count", "post_control_count",
        )),
    }


def compile_bulk_strategy_panel_readiness(workspace: str | Path) -> dict[str, Any]:
    """Bind typed events to annual histories without running an effect estimate."""
    root = Path(workspace).expanduser().resolve()
    corpus = _checked(
        root / "institutional_learning" / "historical_strategy_bulk_corpus" / "latest.json",
        "corpus_sha256",
    )
    outcomes = _checked(root / _ROOT / "latest.json", "outcomes_sha256")
    typed, classification_sha = _typed_classifications(root)
    latest_path = root / _ROOT / "panel-readiness.json"
    if latest_path.exists():
        prior = json.loads(latest_path.read_text(encoding="utf-8"))
        if (
            prior.get("schema") == HISTORICAL_STRATEGY_PANEL_READINESS_SCHEMA
            and prior.get("bulk_corpus_sha256") == corpus["corpus_sha256"]
            and prior.get("bulk_outcomes_sha256") == outcomes["outcomes_sha256"]
            and prior.get("classification_set_sha256") == classification_sha
        ):
            return prior
    event_path = root / str(corpus["event_lake_path"])
    population_events = [
        json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    events = {
        str(row["accession_number"]): row
        for row in population_events
        if str(row["accession_number"]) in typed
    }
    eligible_classes = {
        "acquisition_completion", "disposition_completion", "partnership_completion",
        "separation_completion", "portfolio_reconfiguration_completion",
    }
    episodes = [{**event, **typed[accession]} for accession, event in events.items()
                if typed[accession]["classification"] in eligible_classes]
    coadoption_audit = _coadoption_audit(episodes)
    ciks = {str(row["cik"]) for row in episodes}
    earliest: dict[tuple[str, str, str], dict[str, Any]] = {}
    lake_path = root / str(outcomes["observation_lake_path"])
    with lake_path.open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            cik = str(row["cik"])
            if cik not in ciks or row["metric_id"] not in _OWNER_EARNINGS_INPUTS:
                continue
            key = (cik, str(row["observed_at"]), str(row["metric_id"]))
            current = earliest.get(key)
            if current is None or (row["available_at"], row["observation_id"]) < (
                current["available_at"], current["observation_id"],
            ):
                earliest[key] = row
    annual: dict[str, list[dict[str, Any]]] = defaultdict(list)
    periods = sorted({(cik, observed) for cik, observed, _metric in earliest})
    for cik, observed in periods:
        facts = {
            metric: earliest.get((cik, observed, metric))
            for metric in ("revenue_fy", "operating_cash_flow_fy", "capital_expenditure_fy")
        }
        if not all(facts.values()) or not float(facts["revenue_fy"]["value"]):
            continue
        owner = float(facts["operating_cash_flow_fy"]["value"]) - float(
            facts["capital_expenditure_fy"]["value"]
        )
        margin = owner / float(facts["revenue_fy"]["value"])
        annual[cik].append({
            "observed_at": observed,
            "available_at": max(row["available_at"] for row in facts.values()),
            "owner_earnings_margin": margin,
            "owner_earnings_balance": margin / (1.0 + abs(margin)),
            "observation_ids": sorted(row["observation_id"] for row in facts.values()),
            "observation_row_sha256s": sorted(row["observation_row_sha256"] for row in facts.values()),
        })
    histories = []
    population_by_cik: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in population_events:
        population_by_cik[str(event["cik"])].append(event)
    for episode in sorted(episodes, key=lambda row: (row["available_at"], row["cik"])):
        rows = annual.get(str(episode["cik"]), [])
        event_year = int(episode["occurred_at"][:4])
        pre = [row for row in rows if int(row["observed_at"][:4]) < event_year]
        post = [row for row in rows if int(row["observed_at"][:4]) > event_year]
        history_closed = all(
            str(event["accession_number"]) in typed
            for event in population_by_cik[str(episode["cik"])]
            if event["occurred_at"] <= episode["occurred_at"]
        )
        isolation = coadoption_audit[str(episode["event_sha256"])]
        histories.append({
            "event_sha256": episode["event_sha256"],
            "accession_number": episode["accession_number"], "cik": episode["cik"],
            "occurred_at": episode["occurred_at"],
            "treatment_available_at": episode["available_at"],
            "classification_evidence_sha256": episode["classification_evidence_sha256"],
            "classification_admitted_at": episode.get("classification_admitted_at"),
            "acquisition_selection_receipt": episode.get("acquisition_selection_receipt"),
            "sic2": str(episode.get("sic") or "")[:2] or "unknown",
            "implementation_mode": episode["implementation_mode"],
            "transaction_form": episode["transaction_form"],
            "operating_object_scope": episode["operating_object_scope"],
            "issuer_role": episode["issuer_role"],
            "event_year": event_year,
            "pre_period_count": len(pre), "post_period_count": len(post),
            "history_ready": len(pre) >= 3 and len(post) >= 1,
            "phenotype_history_closed": history_closed,
            **isolation,
            "first_adoption_ready": (
                history_closed and isolation["coadoption_status"] == "isolated_strategy_event"
                and len(pre) >= 3 and len(post) >= 1
            ),
            "annual_history": rows,
        })

    control_bases = []
    for cik in sorted(ciks):
        entity_events = sorted(
            population_by_cik[cik],
            key=lambda row: (row["occurred_at"], row["accession_number"]),
        )
        entity_annual = annual.get(cik, [])
        if not entity_events or not entity_annual:
            continue
        first_untyped_year = next((
            int(event["occurred_at"][:4]) for event in entity_events
            if str(event["accession_number"]) not in typed
        ), None)
        control_through_year = max(
            int(row["observed_at"][:4]) for row in entity_annual
        )
        if first_untyped_year is not None:
            control_through_year = min(control_through_year, first_untyped_year - 1)
        classified_events = [{
            "accession_number": event["accession_number"],
            "event_sha256": event["event_sha256"],
            "occurred_at": event["occurred_at"],
            "sic2": str(event.get("sic") or "")[:2] or "unknown",
            "classification": typed[str(event["accession_number"])]["classification"],
            "implementation_mode": typed[str(event["accession_number"])]["implementation_mode"],
            "classification_evidence_sha256": typed[str(event["accession_number"])][
                "classification_evidence_sha256"
            ],
        } for event in entity_events
            if str(event["accession_number"]) in typed
            and int(event["occurred_at"][:4]) <= control_through_year]
        if classified_events:
            control_bases.append({
                "cik": cik, "control_through_year": control_through_year,
                "bulk_corpus_sha256": corpus["corpus_sha256"],
                "classification_set_sha256": classification_sha,
                "annual_history": entity_annual, "classified_events": classified_events,
                "observed_implementation_modes": sorted({
                    typed[str(event["accession_number"])]["implementation_mode"]
                    for event in entity_events
                    if str(event["accession_number"]) in typed
                    and typed[str(event["accession_number"])]["classification"]
                    in eligible_classes
                }),
            })

    first = {}
    for row in histories:
        key = (row["cik"], row["implementation_mode"])
        if key not in first or row["event_year"] < first[key]["event_year"]:
            first[key] = row
    cells = []
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in first.values():
        groups[(row["sic2"], row["implementation_mode"], row["event_year"])].append(row)
    bounded_control_status = {}
    for (sic2, mode, year), treated in sorted(groups.items()):
        future = [row for row in first.values()
                  if row["sic2"] == sic2 and row["implementation_mode"] == mode
                  and row["event_year"] > year]
        ready_treated = [row for row in treated if strategy_history_ready_at(row, year)]
        ready_future = [row for row in future if strategy_history_ready_at(row, year)]
        ready_bounded = []
        for base in control_bases:
            if mode in base["observed_implementation_modes"]:
                continue
            prior_events = [
                event for event in base["classified_events"]
                if int(event["occurred_at"][:4]) <= year
            ]
            periods = {
                int(row["observed_at"][:4]) for row in base["annual_history"]
                if int(row["observed_at"][:4]) <= int(base["control_through_year"])
            }
            if (
                not prior_events or prior_events[-1]["sic2"] != sic2
                or sum(value < year for value in periods) < 3
                or sum(value > year for value in periods) < 1
            ):
                continue
            control_body = {
                **base, "implementation_mode": mode,
                "control_id": stable_sha256({
                    "cik": base["cik"], "implementation_mode": mode,
                    "control_through_year": base["control_through_year"],
                    "bulk_corpus_sha256": base["bulk_corpus_sha256"],
                    "classification_set_sha256": base["classification_set_sha256"],
                    "classification_evidence_sha256s": sorted(
                        event["classification_evidence_sha256"]
                        for event in base["classified_events"]
                    ),
                }),
                "event_year": 10_000,
            }
            ready_bounded.append(control_body)
        design = compile_strategy_group_time_support(
            ready_treated, ready_future, year, ready_bounded,
        )
        selected_control_ids = set(design["post_bounded_control_ids"])
        selected_bounded_controls = [
            row for row in ready_bounded if row["control_id"] in selected_control_ids
        ]
        bounded_control_status.update({
            row["control_id"]: row for row in selected_bounded_controls
        })
        structural_ready = (
            len({row["cik"] for row in ready_treated}) >= 4
            and len({row["cik"] for row in [*ready_future, *ready_bounded]}) >= 4
        )
        cells.append({
            "sic2": sic2, "implementation_mode": mode, "adoption_year": year,
            "treated_entity_count": len({row["cik"] for row in treated}),
            "history_ready_treated_count": len(ready_treated),
            "future_adopter_entity_count": len({row["cik"] for row in future}),
            "history_ready_future_adopter_count": len({row["cik"] for row in ready_future}),
            "history_ready_bounded_control_count": len({
                row["cik"] for row in ready_bounded
            }),
            "joint_bounded_control_count": len(selected_bounded_controls),
            "structural_support_ready": structural_ready,
            "joint_design": design,
            "group_time_ready": structural_ready and design["joint_support_ready"],
        })

    selected_bounded_ids = {
        control_id for cell in cells
        for control_id in cell["joint_design"]["post_bounded_control_ids"]
    }
    if set(bounded_control_status) != selected_bounded_ids:
        raise ValueError("bounded strategy control identities were not materialized")
    cell_index = {
        (row["sic2"], row["implementation_mode"], row["adoption_year"]): row
        for row in cells
    }
    identity_blockers = []
    for row in first.values():
        if not row["history_ready"] or row["phenotype_history_closed"]:
            continue
        cell = cell_index[(row["sic2"], row["implementation_mode"], row["event_year"])]
        for event in population_by_cik[str(row["cik"])]:
            accession = str(event["accession_number"])
            if event["occurred_at"] <= row["occurred_at"] and accession not in typed:
                identity_blockers.append({
                    "blocked_accession_number": row["accession_number"],
                    "blocked_cik": row["cik"],
                    "sic2": row["sic2"],
                    "implementation_mode": row["implementation_mode"],
                    "adoption_year": row["event_year"],
                    "missing_accession_number": accession,
                    "missing_event_sha256": event["event_sha256"],
                    "history_ready_treated_gap": max(
                        0, 4 - int(cell["history_ready_treated_count"])
                    ),
                    "history_ready_future_adopter_gap": max(
                        0, 4 - int(cell["history_ready_future_adopter_count"])
                    ),
                })
    body = {
        "schema": HISTORICAL_STRATEGY_PANEL_READINESS_SCHEMA,
        "generated_at": outcomes["generated_at"],
        "bulk_corpus_sha256": corpus["corpus_sha256"],
        "bulk_outcomes_sha256": outcomes["outcomes_sha256"],
        "classification_set_sha256": classification_sha,
        "typed_event_count": len(typed), "eligible_typed_event_count": len(episodes),
        "history_ready_event_count": sum(row["history_ready"] for row in histories),
        "first_adoption_ready_event_count": sum(
            row["first_adoption_ready"] for row in histories
        ),
        "coadoption_excluded_event_count": sum(
            row["coadoption_status"] != "isolated_strategy_event" for row in histories
        ),
        "adoption_cell_count": len(cells),
        "structural_support_ready_cell_count": sum(
            row["structural_support_ready"] for row in cells
        ),
        "group_time_ready_cell_count": sum(row["group_time_ready"] for row in cells),
        "identity_closure_blocker_count": len(identity_blockers),
        "history_status": histories, "adoption_cells": cells,
        "bounded_control_status": [
            bounded_control_status[key] for key in sorted(bounded_control_status)
        ],
        "identity_closure_blockers": sorted(
            identity_blockers,
            key=lambda row: (
                row["history_ready_treated_gap"] + row["history_ready_future_adopter_gap"],
                row["sic2"], row["adoption_year"], row["missing_accession_number"],
            ),
        ),
        "estimation_status": (
            "ready_for_causal_row_compilation" if any(row["group_time_ready"] for row in cells)
            else "blocked_insufficient_typed_control_support"
        ),
        "next_activation": (
            "Compile source-bound causal rows for the ready cells."
            if any(row["group_time_ready"] for row in cells) else
            "Acquire outcome-feasible filings that close a common pre/post calendar for structurally supported cells."
            if any(row["structural_support_ready"] for row in cells) else
            "Type more ranked filings inside broad cells with future-adopter or bounded non-adopter support."
        ),
        "causal_estimate_ran": False, "promotion_eligible": False,
        "paper_policy_authority": False, "capital_authority": False,
    }
    result = {**body, "readiness_sha256": stable_sha256(body)}
    _atomic_json(latest_path, result)
    return result


__all__ = [
    "HISTORICAL_STRATEGY_BULK_OUTCOMES_SCHEMA",
    "HISTORICAL_STRATEGY_PANEL_READINESS_SCHEMA",
    "compile_bulk_strategy_outcome_observations", "compile_bulk_strategy_outcome_coverage",
    "compile_bulk_strategy_panel_readiness", "compile_strategy_group_time_support",
    "strategy_history_periods", "strategy_history_ready_at",
]
