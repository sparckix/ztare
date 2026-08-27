"""Historical strategy-event diagnostics from exact SEC filing evidence."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
from html import unescape
import json
from pathlib import Path
import re
from statistics import mean, median
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.evaluation import compile_evaluation_integrity_receipt

from .company_quality import compile_company_quality_histories
from .contracts import canonical_timestamp, timestamp_key
from .sources import fetch_sec_filing_document
from .source_epoch import current_source_epoch


HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA = (
    "jaggedthoughts-historical-strategy-event-replay-v1"
)
HISTORICAL_STRATEGY_EVENT_CLASSIFICATION_SCHEMA = (
    "jaggedthoughts-historical-strategy-event-classification-v2"
)
_ROOT = Path("institutional_learning/historical_strategy_event_replay")
_HORIZON_DAYS = 365
_MINIMUM_EFFECT = 0.01
_CLASSIFIER_VERSION = "typed-transaction-phenotype-v2.4"
_ELIGIBLE_CLASSIFICATIONS = {
    "acquisition_completion", "disposition_completion",
    "partnership_completion", "separation_completion",
    "portfolio_reconfiguration_completion",
}


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


def _event_key(*, cik: str, accession_number: str) -> str:
    return stable_sha256({
        "cik": str(int(cik)),
        "accession_number": accession_number,
        "item": "2.01",
    })


def _event_rows(root: Path, source_run: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = yaml.safe_load((root / "sources.yaml").read_text(encoding="utf-8"))
    sources = {
        str(row["id"]): row for row in manifest.get("sources") or ()
        if isinstance(row, Mapping) and row.get("adapter") == "sec_submissions"
    }
    receipts = {
        str(row["source_id"]): row for row in source_run.get("source_receipts") or ()
        if isinstance(row, Mapping) and row.get("adapter") == "sec_submissions"
    }
    events, blocks = [], []
    for source_id, source in sorted(sources.items()):
        receipt = receipts.get(source_id)
        if not receipt:
            candidates = []
            for path in (root / "sources/raw" / source_id).glob("*.json"):
                try:
                    content = path.read_bytes()
                    payload = json.loads(content)
                    accepted = ((payload.get("filings") or {}).get("recent") or {}).get(
                        "acceptanceDateTime",
                    ) or ()
                    candidates.append((max(accepted, default=""), hashlib.sha256(content).hexdigest(), path))
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    continue
            if not candidates:
                blocks.append({"source_id": source_id, "reason": "source_receipt_unavailable"})
                continue
            _, digest, path = max(candidates)
            receipt_body = {
                "source_id": source_id, "adapter": "sec_submissions",
                "content_sha256": digest, "raw_path": path.relative_to(root).as_posix(),
                "lineage_status": "content_bound_cache_without_current_receipt_head",
            }
            receipt = {**receipt_body, "receipt_sha256": stable_sha256(receipt_body)}
            blocks.append({
                "source_id": source_id,
                "reason": "source_receipt_head_unavailable_cached_index_used",
                "content_sha256": digest,
            })
        path = (root / str(receipt.get("raw_path") or "")).resolve()
        try:
            path.relative_to(root)
            content = path.read_bytes()
        except (OSError, ValueError):
            blocks.append({"source_id": source_id, "reason": "source_document_unavailable"})
            continue
        if hashlib.sha256(content).hexdigest() != receipt.get("content_sha256"):
            blocks.append({"source_id": source_id, "reason": "source_document_hash_mismatch"})
            continue
        payload = json.loads(content)
        recent = (payload.get("filings") or {}).get("recent") or {}
        forms = recent.get("form") or ()
        for index, form in enumerate(forms):
            items = str((recent.get("items") or [""] * len(forms))[index])
            if form != "8-K" or "2.01" not in items.split(","):
                continue
            occurred_at = canonical_timestamp(
                f"{recent['reportDate'][index]}T00:00:00Z", "SEC event report date",
            )
            available_at = canonical_timestamp(
                recent["acceptanceDateTime"][index], "SEC event acceptance time",
            )
            body = {
                "entity_id": str(source["entity_id"]).upper(),
                "source_id": source_id, "cik": str(source["cik"]),
                "accession_number": str(recent["accessionNumber"][index]),
                "primary_document": str(recent["primaryDocument"][index]),
                "occurred_at": occurred_at, "available_at": available_at,
                "form": "8-K", "item": "2.01",
                "source_index_sha256": receipt["content_sha256"],
                "source_index_receipt_sha256": receipt["receipt_sha256"],
            }
            events.append({
                **body,
                "event_key_sha256": _event_key(
                    cik=str(source["cik"]),
                    accession_number=str(recent["accessionNumber"][index]),
                ),
                "event_sha256": stable_sha256(body),
            })
    return sorted(events, key=lambda row: (row["available_at"], row["entity_id"])), blocks


def _source_context(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_run = json.loads((root / "data/latest_source_run.json").read_text(encoding="utf-8"))
    source_epoch = current_source_epoch(root)
    if not source_epoch:
        raise ValueError("historical strategy replay requires a current source epoch")
    heads_path = (root / str(source_epoch["receipt_heads"]["path"])).resolve()
    heads_path.relative_to(root)
    heads = json.loads(heads_path.read_text(encoding="utf-8"))
    receipt_book = {"source_receipts": heads.get("receipts") or ()}
    return source_run, source_epoch, receipt_book


def _plain_filing_text(content: bytes) -> str:
    text = content.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def extract_sec_item_201_context(content: bytes, *, max_characters: int = 14_000) -> str:
    """Return bounded filed text around the operative Item 2.01 occurrence."""
    if max_characters < 1:
        raise ValueError("SEC Item 2.01 context bound must be positive")
    text = _plain_filing_text(content)
    markers = list(re.finditer(
        r"item\s*2\.01|completion of acquisition or disposition of assets",
        text, flags=re.IGNORECASE,
    ))
    if not markers:
        return text[:max_characters]
    marker = markers[-1].start()
    before = min(4_000, max_characters // 3)
    return text[max(0, marker - before):marker + max_characters - before]


def canonicalize_strategy_event_phenotype(row: Mapping[str, Any]) -> dict[str, str]:
    """Lower a source-bound semantic label into the finite strategy grammar."""
    classification = str(row.get("classification") or "ambiguous")
    text = " ".join(str(row.get(key) or "") for key in (
        "transaction_form", "operating_object_scope", "issuer_role", "reasoning",
    )).lower()
    if classification == "excluded_identity_transition":
        transaction_form = "business_combination_listing"
    elif "sale-leaseback" in text or "sale leaseback" in text:
        transaction_form = "sale_leaseback"
    elif "spin" in text:
        transaction_form = "spin_off"
    elif "split" in text:
        transaction_form = "split_off"
    elif "joint" in text:
        transaction_form = "joint_venture"
    elif "royalty" in text or "revenue participation" in text:
        transaction_form = "revenue_or_royalty_right"
    elif "tender" in text:
        transaction_form = "tender_offer"
    elif "merger" in text or "business combination" in text:
        transaction_form = "merger"
    elif "asset" in text or "fdic" in text:
        transaction_form = "asset_purchase" if classification == "acquisition_completion" else "asset_sale"
    elif "stock" in text or "shares" in text or "equity interest" in text:
        transaction_form = "stock_purchase" if classification == "acquisition_completion" else "equity_interest_sale"
    elif classification == "disposition_completion":
        transaction_form = "business_sale"
    elif classification == "acquisition_completion":
        transaction_form = "business_purchase"
    else:
        transaction_form = "indeterminate"

    if "whole company" in text or classification in {
        "excluded_identity_transition", "separation_completion",
    } or transaction_form in {"merger", "tender_offer"}:
        scope = "whole_company"
    elif "product" in text:
        scope = "product_line"
    elif "subsidiary" in text or "business" in text or "partnership interest" in text:
        scope = "business_unit"
    elif "real estate" in text or "property" in text or "equipment" in text:
        scope = "physical_assets"
    elif "royalty" in text or "intellectual property" in text or "license" in text:
        scope = "intellectual_property_or_rights"
    elif "equity" in text or "shares" in text or "stock" in text:
        scope = "equity_interest"
    elif "asset" in text:
        scope = "assets"
    else:
        scope = "indeterminate"

    mode_role_eligibility = {
        "acquisition_completion": ("acquisition", "acquirer", "operating_strategy_event"),
        "disposition_completion": ("divestiture", "seller", "operating_strategy_event"),
        "partnership_completion": ("partnership", "partner", "operating_strategy_event"),
        "separation_completion": ("divestiture", "separating_parent", "operating_strategy_event"),
        "portfolio_reconfiguration_completion": ("resource_reallocation", "acquirer_and_seller", "operating_strategy_bundle_event"),
        "excluded_identity_transition": ("other", "identity_successor", "excluded_issuer_identity_transition"),
        "excluded_non_operating": ("other", "financial_rights_seller", "excluded_financial_rights_transfer"),
        "excluded_noncompleted": ("other", "indeterminate", "excluded_not_completed"),
        "excluded_non_event_document": ("other", "indeterminate", "excluded_non_event_document"),
        "ambiguous": ("other", "indeterminate", "requires_more_filed_context"),
    }
    mode, role, eligibility = mode_role_eligibility.get(
        classification, ("other", "indeterminate", "requires_more_filed_context"),
    )
    return {
        "classification": classification,
        "implementation_mode": mode,
        "transaction_form": transaction_form,
        "operating_object_scope": scope,
        "issuer_role": role,
        "completion_state": "completed" if classification in _ELIGIBLE_CLASSIFICATIONS else (
            "not_completed" if classification == "excluded_noncompleted" else "indeterminate"
        ),
        "strategy_event_eligibility": eligibility,
    }


def _match_rule(text: str, rules: Iterable[tuple[str, str]]) -> tuple[str, str]:
    for label, pattern in rules:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return label, pattern
    return "indeterminate", ""


def _evidence_span(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE) if pattern else None
    if not match:
        return ""
    start = max(0, match.start() - 120)
    end = min(len(text), match.end() + 220)
    return text[start:end].strip()


def classify_sec_item_201(content: bytes) -> dict[str, Any]:
    """Compile an entity-relative transaction phenotype from one filed document."""
    text = _plain_filing_text(content)
    markers = list(re.finditer(
        r"item\s*2\.01|completion of acquisition or disposition of assets",
        text, flags=re.IGNORECASE,
    ))
    if not markers:
        body = {
            "classifier_version": _CLASSIFIER_VERSION,
            "classification": "excluded_noncompleted",
            "implementation_mode": "other", "transaction_form": "non_event_document",
            "operating_object_scope": "indeterminate", "issuer_role": "indeterminate",
            "completion_state": "not_completed",
            "strategy_event_eligibility": "excluded_non_event_document",
            "matched_rules": ["missing_item_2_01_filing_text"],
            "evidence_spans": [], "llm_used": False,
        }
        return {**body, "classification_sha256": stable_sha256(body)}

    marker = markers[-1]
    direct = text[marker.start():marker.start() + 10_000]
    context = text[max(0, marker.start() - 14_000):marker.start() + 10_000]
    transaction_form, form_rule = _match_rule(context, (
        ("sale_leaseback", r"sale[- ]leaseback transaction"),
        ("spin_off", r"spin[- ]off|completed .*? separation .*? distribution"),
        ("split_off", r"split[- ]off exchange offer"),
        ("joint_venture", r"joint (?:ownership|venture)|jointly own|contribut(?:e|ed|ion).*?newco"),
        ("revenue_or_royalty_right", r"revenue participation right|royalty purchase agreement|royalty interest"),
        ("tender_offer", r"tender offer|accepted for payment all .*?shares"),
        ("merger", r"merger (?:agreement|with|was|has been)|completed (?:its|the) merger"),
        ("stock_purchase", r"purchase of all .*?(?:shares|capital stock|equity interests)"),
        ("asset_purchase", r"asset purchase|purchase of (?:certain |substantially all )?assets"),
        ("business_sale", r"sale of (?:the|its|our) .*?(?:business|division|operations)"),
        ("asset_sale", r"sale (?:and transfer )?of .*?assets|sell .*?(?:properties|assets|real estate)"),
    ))
    object_scope, scope_rule = _match_rule(context, (
        ("whole_company", r"all (?:of )?(?:the )?(?:outstanding |issued and outstanding )?(?:shares|capital stock)"),
        ("product_line", r"product line"),
        ("business_unit", r"business unit|business division|(?:the|its|our) [a-z0-9& ,'-]{1,80} business\b"),
        ("physical_assets", r"real estate|campus|fabrication buildings|capital equipment|inventory"),
        ("intellectual_property_or_rights", r"revenue participation right|royalty|intellectual property|license"),
        ("mixed_assets", r"assets and liabilities|properties and other assets"),
        ("assets", r"\bassets\b"),
        ("equity_interest", r"equity interests|common stock|capital stock"),
    ))
    if transaction_form in {"merger", "tender_offer", "stock_purchase"}:
        object_scope = "whole_company"

    explicit = direct if len(direct) > 400 else context
    financial = bool(re.search(
        r"revenue participation right|royalty purchase agreement|royalty interest",
        context, flags=re.IGNORECASE,
    ))
    noncompleted = bool(re.search(
        r"will not consummate|outside date for completion|closing .*? will occur",
        context, flags=re.IGNORECASE,
    )) and not bool(re.search(
        r"(?:completed|consummated|closed on|closing .*? occurred|accepted for payment)",
        context, flags=re.IGNORECASE,
    ))
    separated_entity = bool(re.search(
        r"(?:flex|former parent).*?(?:spin[- ]off|distribution).*?(?:nextracker|company)",
        context, flags=re.IGNORECASE,
    ))
    separation_rule = r"completed [^.]{0,240} separation|completed [^.]{0,240} spin[- ]off|closed the spin[- ]off|split[- ]off exchange offer"
    partnership_rule = r"joint (?:ownership|venture)|jointly own|contribut(?:e|ed|ion)[^.]{0,240}newco"
    disposition_rule = (
        r"closed on the sale|completed [^.]{0,240} sale(?: and transfer)?|sale [^.]{0,240} (?:was|has been) completed|"
        r"commercial divestiture|announc(?:e|ed|ing) the sale of|"
        r"closing of [^.]{0,240} sale[- ]leaseback transaction occurred"
    )
    acquisition_rule = (
        r"completed (?:the|its|a) (?:previously announced )?acquisition|completed the purchase|"
        r"completed [^.]{0,240} merger|merger [^.]{0,240} (?:completed|consummated)|accepted for payment all [^.]{0,240}shares|"
        r"accepted for payment [^.]{0,240}shares|closing [^.]{0,240} occurred [^.]{0,240} agreed to purchase|"
        r"agreed to purchase [^.]{0,240} closing [^.]{0,240} occurred|closed on the asset purchase|"
        r"purchased [^.]{0,240} for an initial purchase price|announc(?:e|ed|ing) the purchase of assets"
    )
    mixed_reconfiguration = bool(
        re.search(r"completed [^.]{0,240} acquisition", context, flags=re.IGNORECASE)
        and re.search(r"completed [^.]{0,240} divestiture", context, flags=re.IGNORECASE)
    )
    acquired_after_framework = bool(
        re.search(r"agreed to purchase", context, flags=re.IGNORECASE)
        and re.search(
            r"closing contemplated [^.]{0,480} occurred", context,
            flags=re.IGNORECASE,
        )
    )

    if financial:
        classification, mode, role, eligibility, completion_rule = (
            "excluded_non_operating", "other", "financial_rights_seller",
            "excluded_financial_rights_transfer", form_rule,
        )
    elif noncompleted:
        classification, mode, role, eligibility, completion_rule = (
            "excluded_noncompleted", "other", "indeterminate",
            "excluded_not_completed", r"will not consummate|outside date for completion|closing .*? will occur",
        )
    elif mixed_reconfiguration:
        classification, mode, role, eligibility, completion_rule = (
            "portfolio_reconfiguration_completion", "resource_reallocation",
            "acquirer_and_seller", "operating_strategy_bundle_event",
            r"completed [^.]{0,240} acquisition|completed [^.]{0,240} divestiture",
        )
        transaction_form = "mixed_acquisition_divestiture"
        object_scope = "mixed_assets"
    elif re.search(partnership_rule, context, flags=re.IGNORECASE):
        classification, mode, role, eligibility, completion_rule = (
            "partnership_completion", "partnership", "partner",
            "operating_strategy_event", partnership_rule,
        )
    elif re.search(separation_rule, context, flags=re.IGNORECASE):
        classification, mode, role, eligibility, completion_rule = (
            "separation_completion", "other" if separated_entity else "divestiture",
            "separated_entity" if separated_entity else "separating_parent",
            "operating_strategy_event", separation_rule,
        )
        object_scope = "whole_company" if separated_entity else "business_unit"
    elif re.search(disposition_rule, explicit, flags=re.IGNORECASE) or (
        transaction_form == "sale_leaseback"
        and re.search(disposition_rule, context, flags=re.IGNORECASE)
    ):
        classification, mode, role, eligibility, completion_rule = (
            "disposition_completion", "divestiture", "seller",
            "operating_strategy_event", disposition_rule,
        )
    elif acquired_after_framework or re.search(
        acquisition_rule, context, flags=re.IGNORECASE,
    ):
        classification, mode, role, eligibility, completion_rule = (
            "acquisition_completion", "acquisition", "acquirer",
            "operating_strategy_event", acquisition_rule,
        )
    else:
        classification, mode, role, eligibility, completion_rule = (
            "ambiguous", "other", "indeterminate", "requires_semantic_resolution", "",
        )

    evidence_spans = []
    for evidence_role, pattern in (
        ("completion_and_direction", completion_rule),
        ("transaction_form", form_rule), ("operating_object_scope", scope_rule),
    ):
        span = _evidence_span(context, pattern)
        if span and span not in {row["text"] for row in evidence_spans}:
            evidence_spans.append({
                "evidence_role": evidence_role, "text": span,
                "text_sha256": hashlib.sha256(span.encode("utf-8")).hexdigest(),
            })
    body = {
        "classifier_version": _CLASSIFIER_VERSION,
        "classification": classification, "implementation_mode": mode,
        "transaction_form": transaction_form,
        "operating_object_scope": object_scope, "issuer_role": role,
        "completion_state": (
            "completed" if classification in _ELIGIBLE_CLASSIFICATIONS
            or classification == "excluded_non_operating" else
            "not_completed" if classification == "excluded_noncompleted" else "indeterminate"
        ),
        "strategy_event_eligibility": eligibility,
        "matched_rules": sorted({rule for rule in (
            form_rule, scope_rule, completion_rule,
        ) if rule}),
        "evidence_spans": evidence_spans, "llm_used": False,
    }
    return {**body, "classification_sha256": stable_sha256(body)}


def _quality_point(report: Mapping[str, Any]) -> dict[str, Any] | None:
    history = report.get("history") or ()
    if not history or history[-1].get("owner_earnings_margin") is None:
        return None
    head = history[-1]
    return {
        "observed_at": head["observed_at"], "available_at": report["available_at"],
        "value": float(head["owner_earnings_margin"]), "unit": "decimal",
        "observation_ids": list(head.get("observation_ids") or ()),
        "source_refs": list(head.get("source_refs") or ()),
        "quality_report_sha256": report["quality_report_sha256"],
    }


def _ready_events(
    events: Iterable[Mapping[str, Any]], histories: Mapping[str, Iterable[Mapping[str, Any]]],
    *, as_of: str, horizon_days: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    epoch = timestamp_key(as_of)
    ready, pending, blocked = [], [], []
    for event in events:
        due = timestamp_key(str(event["occurred_at"])) + timedelta(days=horizon_days)
        due_at = due.isoformat(timespec="seconds").replace("+00:00", "Z")
        if due > epoch:
            pending.append({**dict(event), "due_at": due_at})
            continue
        reports = tuple(histories.get(str(event["entity_id"]), ()))
        baseline = [
            row for row in reports
            if timestamp_key(str(row["available_at"])) <= timestamp_key(str(event["available_at"]))
            and timestamp_key(str(row["history"][-1]["observed_at"]))
            < timestamp_key(str(event["occurred_at"]))
        ]
        outcomes = [
            row for row in reports
            if timestamp_key(str(row["history"][-1]["observed_at"])) >= due
            and timestamp_key(str(row["available_at"])) <= epoch
        ]
        if not baseline:
            blocked.append({**dict(event), "due_at": due_at, "reason": "baseline_unavailable"})
            continue
        if not outcomes:
            blocked.append({**dict(event), "due_at": due_at, "reason": "outcome_unavailable"})
            continue
        before = _quality_point(max(
            baseline, key=lambda row: timestamp_key(str(row["history"][-1]["observed_at"])),
        ))
        after = _quality_point(min(
            outcomes, key=lambda row: timestamp_key(str(row["history"][-1]["observed_at"])),
        ))
        if before is None or after is None:
            blocked.append({**dict(event), "due_at": due_at, "reason": "metric_unavailable"})
            continue
        ready.append({**dict(event), "due_at": due_at, "baseline": before, "outcome": after})
    return ready, pending, blocked


def _classification_path(root: Path, accession: str) -> Path:
    return root / _ROOT / "filings" / f"{accession.replace('-', '')}.json"


def _semantic_resolution_matches(
    semantic: Mapping[str, Any], classification: Mapping[str, Any],
) -> bool:
    """Bind adjudication to immutable evidence, not a refresh-scoped event hash."""
    return bool(
        semantic.get("filing_document_sha256")
        == classification.get("filing_document_sha256")
        and semantic.get("deterministic_classification_receipt_sha256")
        == classification.get("classification_receipt_sha256")
    )


def _load_classification(root: Path, event: Mapping[str, Any]) -> dict[str, Any] | None:
    path = _classification_path(root, str(event["accession_number"]))
    if not path.exists():
        return None
    row = json.loads(path.read_text(encoding="utf-8"))
    body = dict(row)
    declared = str(body.pop("classification_receipt_sha256", ""))
    accession = str(event["accession_number"])
    stable_event_binding = (
        str(row.get("accession_number") or "") == accession
        and (
            not row.get("event_key_sha256")
            or row.get("event_key_sha256") == event.get("event_key_sha256")
        )
    )
    if stable_sha256(body) != declared or not stable_event_binding:
        raise ValueError("historical strategy event classification binding is invalid")
    if row.get("schema") == HISTORICAL_STRATEGY_EVENT_CLASSIFICATION_SCHEMA:
        keys = [
            "classification", "implementation_mode", "transaction_form",
            "operating_object_scope", "issuer_role", "completion_state",
            "strategy_event_eligibility", "matched_rules", "evidence_spans", "llm_used",
        ]
        if row.get("classifier_version"):
            keys.insert(0, "classifier_version")
        classification_body = {key: row.get(key) for key in keys}
    else:
        classification_body = {
            "classification": row.get("classification"),
            "matched_rules": row.get("matched_rules") or [],
            "llm_used": row.get("llm_used"),
        }
    if stable_sha256(classification_body) != row.get("classification_sha256"):
        raise ValueError("historical strategy event classification hash is invalid")
    source_receipt = dict(row.get("filing_source_receipt") or {})
    receipt_sha = str(source_receipt.pop("receipt_sha256", ""))
    raw_path = (root / str(source_receipt.get("raw_path") or "")).resolve()
    raw_path.relative_to(root)
    if (
        stable_sha256(source_receipt) != receipt_sha
        or hashlib.sha256(raw_path.read_bytes()).hexdigest()
        != source_receipt.get("content_sha256")
    ):
        raise ValueError("historical strategy filing source receipt is invalid")
    if row.get("classification") == "ambiguous":
        semantic_path = (
            root / "institutional_learning" / "historical_strategy_bulk_learning"
            / "semantic_resolutions" / path.name
        )
        if semantic_path.exists():
            semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
            semantic_body = dict(semantic)
            semantic_sha = str(semantic_body.pop("semantic_resolution_sha256", ""))
            if stable_sha256(semantic_body) != semantic_sha:
                raise ValueError("historical strategy semantic resolution binding is invalid")
            if _semantic_resolution_matches(semantic, row):
                phenotype = canonicalize_strategy_event_phenotype(semantic)
                spans = [{
                    "evidence_role": value["evidence_role"], "text": value["quote"],
                    "text_sha256": hashlib.sha256(value["quote"].encode("utf-8")).hexdigest(),
                } for value in semantic.get("evidence") or ()]
                return {
                    **row, **phenotype,
                    "classifier_version": "source-quote-semantic-resolution-v1",
                    "classification_sha256": semantic_sha,
                    "classification_receipt_sha256": semantic_sha,
                    "matched_rules": [], "evidence_spans": spans, "llm_used": True,
                    "semantic_resolution_sha256": semantic_sha,
                }
    return row


def _episode(
    event: Mapping[str, Any], classification: Mapping[str, Any], *, minimum_effect: float,
) -> dict[str, Any]:
    delta = float(event["outcome"]["value"]) - float(event["baseline"]["value"])
    status = (
        "supports" if delta >= minimum_effect else
        "contradicts" if delta <= -minimum_effect else "inconclusive"
    )
    body = {
        "schema": "jaggedthoughts-historical-strategy-event-episode-v1",
        "episode_id": f"sec-item-2.01:{event['accession_number']}",
        "inference_block_id": f"fiscal-year:{str(event['outcome']['observed_at'])[:4]}",
        "entity_id": event["entity_id"], "event_sha256": event["event_sha256"],
        "implementation_mode": classification.get("implementation_mode") or (
            "acquisition" if classification["classification"] == "acquisition_completion"
            else "divestiture"
        ),
        "transaction_phenotype": {
            "classification": classification["classification"],
            "transaction_form": classification.get("transaction_form") or "indeterminate",
            "operating_object_scope": (
                classification.get("operating_object_scope") or "indeterminate"
            ),
            "issuer_role": classification.get("issuer_role") or (
                "acquirer" if classification["classification"] == "acquisition_completion"
                else "seller"
            ),
            "completion_state": classification.get("completion_state") or "completed",
            "strategy_event_eligibility": (
                classification.get("strategy_event_eligibility")
                or "legacy_direction_only"
            ),
        },
        "occurred_at": event["occurred_at"], "available_at": event["available_at"],
        "due_at": event["due_at"], "accession_number": event["accession_number"],
        "filing_document_sha256": classification["filing_document_sha256"],
        "filing_source_receipt": classification["filing_source_receipt"],
        "classification_sha256": classification["classification_sha256"],
        "outcome_contract": {
            "metric_id": "owner_earnings_margin", "unit": "decimal",
            "direction": "increase", "minimum_effect": minimum_effect,
            "horizon_days": _HORIZON_DAYS, "comparator": "pre_event_baseline",
        },
        "baseline": event["baseline"], "outcome": event["outcome"],
        "estimated_effect": delta, "status": status,
        "causal_status": "descriptive_uncontrolled_historical_replay",
        "policy_selected_after_sample": True, "promotion_eligible": False,
        "capital_authority": False,
    }
    return {**body, "episode_sha256": stable_sha256(body)}


def _summaries(episodes: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = tuple(episodes)
    summaries = []
    for mode in sorted({str(row["implementation_mode"]) for row in rows}):
        cohort = [row for row in rows if row["implementation_mode"] == mode]
        effects = [float(row["estimated_effect"]) for row in cohort]
        counts = Counter(str(row["status"]) for row in cohort)
        summaries.append({
            "implementation_mode": mode, "episode_count": len(cohort),
            "entity_count": len({str(row["entity_id"]) for row in cohort}),
            "mean_effect": mean(effects) if effects else None,
            "median_effect": median(effects) if effects else None,
            "status_counts": dict(sorted(counts.items())),
            "interpretation": "uniform historical base-rate diagnostic only",
        })
    return summaries


def _classification_receipt(
    event: Mapping[str, Any], filing: Mapping[str, Any], classification: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "schema": HISTORICAL_STRATEGY_EVENT_CLASSIFICATION_SCHEMA,
        "event_key_sha256": event["event_key_sha256"],
        "event_sha256": event["event_sha256"],
        "accession_number": event["accession_number"],
        "filing_document_sha256": filing["filing_document_sha256"],
        "filing_source_receipt": filing["receipt"],
        **{
            key: classification[key]
            for key in (
                "classifier_version", "classification", "classification_sha256", "implementation_mode",
                "transaction_form", "operating_object_scope", "issuer_role",
                "completion_state", "strategy_event_eligibility", "matched_rules",
                "evidence_spans", "llm_used",
            )
        },
    }
    return {**body, "classification_receipt_sha256": stable_sha256(body)}


def compile_workspace_historical_strategy_event_replay(
    workspace: str | Path, *, as_of: str | None = None,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    source_run, source_epoch, receipt_book = _source_context(root)
    epoch = canonical_timestamp(as_of or source_run["as_of"], "strategy replay as_of")
    events, source_blocks = _event_rows(root, receipt_book)
    histories = compile_company_quality_histories(
        entity_ids={str(row["entity_id"]) for row in events},
        observations_path=root / "data/observations.csv", as_of=epoch, min_years=2,
    )
    ready, pending, evidence_blocks = _ready_events(
        events, histories, as_of=epoch, horizon_days=_HORIZON_DAYS,
    )
    matured = [row for row in events if timestamp_key(str(row["occurred_at"])) + timedelta(
        days=_HORIZON_DAYS,
    ) <= timestamp_key(epoch)]
    search_body = {
        "schema": "jaggedthoughts-historical-strategy-event-search-v1",
        "source_run_sha256": source_run["run_sha256"], "as_of": epoch,
        "source_epoch_sha256": source_epoch["source_epoch_sha256"],
        "event_selector": {"form": "8-K", "item": "2.01"},
        "outcome_policy": {
            "metric_id": "owner_earnings_margin", "unit": "decimal",
            "horizon_days": _HORIZON_DAYS, "minimum_effect": _MINIMUM_EFFECT,
            "baseline_rule": "latest filing-time fiscal head available before event",
            "outcome_rule": "earliest filing-time fiscal head at or after frozen horizon",
        },
        "matured_event_sha256s": sorted(str(row["event_sha256"]) for row in matured),
    }
    search = {**search_body, "search_sha256": stable_sha256(search_body)}
    episodes, document_blocks, classifications = [], [], []
    excluded_classifications = []
    for event in ready:
        classification = _load_classification(root, event)
        if not classification:
            document_blocks.append({
                "event_sha256": event["event_sha256"], "entity_id": event["entity_id"],
                "accession_number": event["accession_number"],
                "reason": "filing_document_unavailable",
            })
        else:
            classifications.append(classification)
        if classification and classification["classification"] == "ambiguous":
            document_blocks.append({
                "event_sha256": event["event_sha256"], "entity_id": event["entity_id"],
                "accession_number": event["accession_number"],
                "reason": "document_classification_ambiguous",
            })
        elif classification and classification["classification"] in _ELIGIBLE_CLASSIFICATIONS:
            episodes.append(_episode(event, classification, minimum_effect=_MINIMUM_EFFECT))
        elif classification:
            excluded_classifications.append(classification)
            document_blocks.append({
                "event_sha256": event["event_sha256"], "entity_id": event["entity_id"],
                "accession_number": event["accession_number"],
                "reason": "document_classification_excluded",
                "classification": classification["classification"],
                "strategy_event_eligibility": classification.get(
                    "strategy_event_eligibility"
                ),
            })
    policy_not_before = max(
        [epoch, *(
            str((row.get("filing_source_receipt") or {}).get("retrieved_at") or epoch)
            for row in classifications
        )],
        key=timestamp_key,
    )
    source_rows = []
    for row in episodes:
        source_rows.extend((
            {
                "source_id": str(row["filing_source_receipt"]["source_id"]),
                "available_at": row["available_at"], "as_of": row["available_at"],
                "source_sha256": row["filing_source_receipt"]["content_sha256"],
                "availability_basis": "SEC acceptance time",
            },
            {
                "source_id": f"baseline:{row['baseline']['quality_report_sha256']}",
                "available_at": row["baseline"]["available_at"], "as_of": row["available_at"],
                "source_sha256": row["baseline"]["quality_report_sha256"],
                "availability_basis": "SEC company-facts filed date",
            },
            {
                "source_id": f"outcome:{row['outcome']['quality_report_sha256']}",
                "available_at": row["outcome"]["available_at"], "as_of": epoch,
                "source_sha256": row["outcome"]["quality_report_sha256"],
                "availability_basis": "SEC company-facts filed date",
            },
        ))
    integrity = compile_evaluation_integrity_receipt(
        temporal_design="historical_replay", generation_processes=("deterministic",),
        source_availability_rows=source_rows,
    )
    integrity = {
        **integrity, "outcome_domain": "business_accounting",
        "alpha_evidence_eligible": False, "sufficient_for_alpha_claim": False,
        "paper_policy_authority": False, "capital_authority": False,
    }
    integrity["evaluation_integrity_sha256"] = stable_sha256({
        key: value for key, value in integrity.items()
        if key != "evaluation_integrity_sha256"
    })
    body = {
        "schema": HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA,
        "generated_at": policy_not_before, "evidence_as_of": epoch,
        "search": search, "event_count": len(events),
        "matured_event_count": len(matured), "outcome_ready_event_count": len(ready),
        "pending_horizon_count": len(pending),
        "evidence_block_count": len(evidence_blocks),
        "document_block_count": len(document_blocks), "episode_count": len(episodes),
        "typed_classification_count": len(classifications),
        "ambiguous_classification_count": sum(
            row.get("classification") == "ambiguous" for row in classifications
        ),
        "excluded_classification_count": len(excluded_classifications),
        "entity_count": len({str(row["entity_id"]) for row in episodes}),
        "episodes": sorted(episodes, key=lambda row: (row["inference_block_id"], row["entity_id"])),
        "cohort_summaries": _summaries(episodes),
        "blocks": [*source_blocks, *evidence_blocks, *document_blocks],
        "evaluation_integrity": integrity,
        "status": "historical_strategy_diagnostic_available" if episodes else "awaiting_filing_documents",
        "next_activation": (
            "Acquire the next exact SEC Item 2.01 filing documents."
            if any(row["reason"] == "filing_document_unavailable" for row in document_blocks) else
            f"Resolve {sum(row['reason'] == 'document_classification_ambiguous' for row in document_blocks)} "
            "ambiguous transaction contexts and freeze a moderator/control design before testing narrower laws."
            if any(row["reason"] == "document_classification_ambiguous" for row in document_blocks) else
            "Freeze a moderator/control design before testing narrower laws on later events."
        ),
        "causal_credit": False, "promotion_eligible": False,
        "paper_policy_authority": False, "capital_authority": False,
        "boundaries": [
            "The event and accounting rows are point-in-time, but the uniform policy was selected after this historical sample.",
            "Item 2.01 establishes a material transaction; typed filing-language rules resolve transaction form, object scope, issuer role, and completion state, not strategic quality.",
            "Before/after owner-earnings changes have no causal interpretation without compatible not-yet-treated controls and pretrend evidence.",
            "Subscription-model historical answers are excluded because source timestamps cannot remove parameter memory.",
        ],
    }
    return {**body, "replay_sha256": stable_sha256(body)}


def acquire_workspace_historical_strategy_events(
    workspace: str | Path, *, limit: int = 4, as_of: str | None = None,
) -> dict[str, Any]:
    if limit < 0:
        raise ValueError("historical strategy event acquisition limit cannot be negative")
    root = Path(workspace).expanduser().resolve()
    replay = compile_workspace_historical_strategy_event_replay(root, as_of=as_of)
    blocked_accessions = {
        str(row["accession_number"]): row for row in replay["blocks"]
        if row.get("reason") == "filing_document_unavailable"
    }
    _, _, receipt_book = _source_context(root)
    events, _ = _event_rows(root, receipt_book)
    event_by_accession = {str(row["accession_number"]): row for row in events}
    selected = sorted(
        (event_by_accession[key] for key in blocked_accessions if key in event_by_accession),
        key=lambda row: (row["available_at"], row["entity_id"]), reverse=True,
    )[:limit]
    acquired, reclassified, errors = [], [], []
    for event in selected:
        try:
            filing = fetch_sec_filing_document(
                root, source_id=f"sec_{str(event['entity_id']).lower()}_strategy_event",
                cik=str(event["cik"]), accession_number=str(event["accession_number"]),
                primary_document=str(event["primary_document"]),
                accepted_at=str(event["available_at"]),
            )
            raw_path = root / str(filing["receipt"]["raw_path"])
            classification = classify_sec_item_201(raw_path.read_bytes())
            receipt = _classification_receipt(event, filing, classification)
            _atomic_json(_classification_path(root, str(event["accession_number"])), receipt)
            acquired.append(receipt)
        except (OSError, TypeError, ValueError) as error:
            errors.append({
                "event_sha256": event["event_sha256"],
                "accession_number": event["accession_number"],
                "error": f"{type(error).__name__}: {error}"[:1_000],
            })

    # Existing v1 or ambiguous receipts can be upgraded from the same immutable
    # filing bytes without another source call.
    for event in events:
        path = _classification_path(root, str(event["accession_number"]))
        prior = _load_classification(root, event)
        if not prior or (
            prior.get("schema") == HISTORICAL_STRATEGY_EVENT_CLASSIFICATION_SCHEMA
            and prior.get("classifier_version") == _CLASSIFIER_VERSION
            and prior.get("classification") != "ambiguous"
        ):
            continue
        source_receipt = dict(prior["filing_source_receipt"])
        raw_path = (root / str(source_receipt["raw_path"])).resolve()
        raw_path.relative_to(root)
        classification = classify_sec_item_201(raw_path.read_bytes())
        filing = {
            "filing_document_sha256": prior["filing_document_sha256"],
            "receipt": prior["filing_source_receipt"],
        }
        receipt = _classification_receipt(event, filing, classification)
        if receipt["classification_receipt_sha256"] != prior.get(
            "classification_receipt_sha256"
        ):
            _atomic_json(path, receipt)
            reclassified.append(receipt)
    replay = compile_workspace_historical_strategy_event_replay(root, as_of=as_of)
    body = {
        "schema": "jaggedthoughts-historical-strategy-event-acquisition-v1",
        "executed_at": _utc_now(), "search_sha256": replay["search"]["search_sha256"],
        "selected_count": len(selected), "acquired_count": len(acquired),
        "reclassified_count": len(reclassified),
        "error_count": len(errors), "acquired": acquired, "errors": errors,
        "replay_sha256": replay["replay_sha256"], "capital_authority": False,
    }
    acquisition = {**body, "acquisition_sha256": stable_sha256(body)}
    _atomic_json(root / _ROOT / "latest.json", replay)
    _atomic_json(root / _ROOT / "acquisition-latest.json", acquisition)
    return {"replay": replay, "acquisition": acquisition}


__all__ = [
    "HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA",
    "acquire_workspace_historical_strategy_events",
    "classify_sec_item_201",
    "canonicalize_strategy_event_phenotype",
    "compile_workspace_historical_strategy_event_replay",
    "extract_sec_item_201_context",
]
