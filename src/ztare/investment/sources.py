"""Public-data adapters with point-in-time provenance for investment research.

The adapters cache the exact response bytes before parsing.  Every normalized
observation carries both an economic observation time and an information
availability time.  Providers that do not expose historical availability are
marked ``retrieval_only``; their old rows become usable only from the retrieval
time onward and therefore cannot leak into historical simulations.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import fcntl
from functools import lru_cache
import hashlib
from html import unescape
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

import yaml
import requests

from ztare.common.equivariance import stable_sha256

from .contracts import MetricObservation, canonical_timestamp, require_text
from .evidence_vault import capture_public_source_run
from .metrics import derive_standard_metrics, metric_universe_surface
from .observation_index import build_observation_index
from .signals import SignalDefinition, derive_signals_partial
from .source_epoch import (
    CACHED_RECEIPT_PROJECTION,
    compile_source_epoch,
    derivation_identity,
)


PUBLIC_SOURCE_MANIFEST_SCHEMA = "jaggedthoughts-public-source-manifest-v1"
SOURCE_RECEIPT_SCHEMA = "jaggedthoughts-public-source-receipt-v1"
SOURCE_RUN_SCHEMA = "jaggedthoughts-public-source-run-v1"
FUND_HOLDINGS_SNAPSHOT_SCHEMA = "jaggedthoughts-fund-holdings-snapshot-v1"
OBSERVATION_COLUMNS = (
    "observation_id", "entity_id", "metric_id", "value", "unit",
    "observed_at", "available_at", "source_ref",
)
MAX_SOURCE_BYTES = 64 * 1024 * 1024
DEFAULT_SEC_USER_AGENT = (
    "JaggedThoughts Capital Workbench/1.0 admin@sparckix.com"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _timestamp(value: Any, label: str, *, end_of_day: bool = False) -> str:
    text = require_text(value, label)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        text += "T23:59:59Z" if end_of_day else "T00:00:00Z"
    return canonical_timestamp(text, label)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_write(path, (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))


def _source_receipt_heads(path: Path) -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        str(row.get("source_id") or ""): dict(row)
        for row in payload.get("receipts") or ()
        if isinstance(row, Mapping) and row.get("source_id")
    } if isinstance(payload, Mapping) else {}


def _safe_source_id(value: Any) -> str:
    source_id = require_text(value, "source.id")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", source_id):
        raise ValueError("source.id must use letters, numbers, dot, colon, underscore, or dash")
    return source_id


def _redacted_url(url: str) -> str:
    parsed = urlparse(url)
    redacted = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        redacted.append((key, "<redacted>" if key.lower() in {"apikey", "api_key", "token", "key"} else value))
    return urlunparse(parsed._replace(query=urlencode(redacted)))


def _fetch(
    url: str,
    *,
    user_agent: str,
    timeout: float = 30.0,
    extra_headers: Mapping[str, str] | None = None,
) -> tuple[bytes, Mapping[str, str]]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("public HTTP sources must use an absolute https URL")
    request_headers = {
        "User-Agent": require_text(user_agent, "source user agent"),
        "Accept": "application/json,text/csv,text/plain,*/*;q=0.2",
        "Accept-Encoding": "identity",
    }
    request_headers.update(dict(extra_headers or {}))
    request = Request(url, headers=request_headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - https checked above.
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_SOURCE_BYTES:
                raise ValueError(f"source response exceeds {MAX_SOURCE_BYTES} bytes")
            content = response.read(MAX_SOURCE_BYTES + 1)
            if len(content) > MAX_SOURCE_BYTES:
                raise ValueError(f"source response exceeds {MAX_SOURCE_BYTES} bytes")
            headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
            return content, headers
    except HTTPError as error:
        detail = error.read(2048).decode("utf-8", errors="replace")
        raise ValueError(f"source HTTP {error.code}: {detail[:300]}") from error
    except URLError as error:
        raise ValueError(f"source request failed: {error.reason}") from error


def _fetch_curl(
    url: str,
    *,
    user_agent: str,
    timeout: float = 30.0,
    extra_headers: Mapping[str, str] | None = None,
) -> tuple[bytes, Mapping[str, str]]:
    """Fetch a public source through curl when a provider stalls Python HTTP clients."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("public HTTP sources must use an absolute https URL")
    command = [
        "curl", "--fail", "--silent", "--show-error", "--http1.1",
        "--max-time", str(timeout), "--max-filesize", str(MAX_SOURCE_BYTES),
    ]
    require_text(user_agent, "source user agent")
    for key, value in (extra_headers or {}).items():
        command.extend(("--header", f"{key}: {value}"))
    command.append(url)
    try:
        completed = subprocess.run(command, capture_output=True, check=False, timeout=timeout + 5)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"source request failed: {error}") from error
    if completed.returncode:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"source request failed: {detail[:300] or f'curl exit {completed.returncode}'}")
    content = completed.stdout
    if len(content) > MAX_SOURCE_BYTES:
        raise ValueError(f"source response exceeds {MAX_SOURCE_BYTES} bytes")
    return content, {}


def _fetch_sec(url: str, *, user_agent: str, timeout: float = 30.0) -> tuple[bytes, Mapping[str, str]]:
    """Fetch an SEC JSON surface with its current HTTP-client compatibility needs."""
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": require_text(user_agent, "SEC user agent"),
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=(10, timeout),
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise ValueError(f"SEC source request failed: {error}") from error
    content = response.content
    if len(content) > MAX_SOURCE_BYTES:
        raise ValueError(f"SEC source response exceeds {MAX_SOURCE_BYTES} bytes")
    return content, {str(key).lower(): str(value) for key, value in response.headers.items()}


@dataclass(frozen=True, slots=True)
class SourceReceipt:
    source_id: str
    adapter: str
    canonical_url: str
    retrieved_at: str
    content_sha256: str
    raw_path: str
    media_type: str
    availability_mode: str
    observation_count: int
    provider_note: str
    receipt_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in (
            "source_id", "adapter", "canonical_url", "retrieved_at", "content_sha256",
            "raw_path", "media_type", "availability_mode", "provider_note",
        ):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"source receipt {attr}"))
        object.__setattr__(self, "retrieved_at", canonical_timestamp(self.retrieved_at, "source retrieved_at"))
        if len(self.content_sha256) != 64:
            raise ValueError("source content_sha256 must be a SHA-256 digest")
        if self.observation_count < 0:
            raise ValueError("source observation_count cannot be negative")
        object.__setattr__(self, "receipt_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SOURCE_RECEIPT_SCHEMA,
            "source_id": self.source_id,
            "adapter": self.adapter,
            "canonical_url": self.canonical_url,
            "retrieved_at": self.retrieved_at,
            "content_sha256": self.content_sha256,
            "raw_path": self.raw_path,
            "media_type": self.media_type,
            "availability_mode": self.availability_mode,
            "observation_count": self.observation_count,
            "provider_note": self.provider_note,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "receipt_sha256": self.receipt_sha256}


def _cache_raw(
    workspace: Path, source_id: str, adapter: str, content: bytes, suffix: str
) -> tuple[str, str]:
    digest = hashlib.sha256(content).hexdigest()
    safe_adapter = re.sub(r"[^a-z0-9_-]+", "-", adapter.lower()).strip("-")
    relative = Path("sources") / "raw" / source_id / f"{safe_adapter}-{digest[:20]}{suffix}"
    destination = workspace / relative
    if not destination.exists():
        _atomic_write(destination, content)
    return relative.as_posix(), digest


def _sec_period_matches(row: Mapping[str, Any], period: str) -> bool:
    form = str(row.get("form") or "")
    if period == "instant":
        return not row.get("start")
    if period == "annual":
        return form in {"10-K", "10-K/A", "20-F", "20-F/A"} and str(row.get("fp") or "") == "FY"
    if period == "quarter":
        if form not in {"10-Q", "10-Q/A", "6-K", "6-K/A"} or not row.get("start"):
            return False
        try:
            duration = (date.fromisoformat(str(row["end"])) - date.fromisoformat(str(row["start"]))).days
        except (KeyError, ValueError):
            return False
        return 70 <= duration <= 120
    if period == "any":
        return True
    raise ValueError(f"unsupported SEC selection period: {period}")


_SEC_METRIC_CONCEPT_ALIASES = {
    "debt_current": (
        "LongTermDebtAndCapitalLeaseObligationsCurrent",
        "LongTermDebtCurrent",
        "ShortTermBorrowings",
        "FinanceLeaseLiabilityCurrent",
    ),
    "debt_noncurrent": (
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebtNoncurrent",
        "LongTermDebt",
        "FinanceLeaseLiabilityNoncurrent",
    ),
}


def parse_sec_companyfacts(
    content: bytes, source: Mapping[str, Any]
) -> tuple[MetricObservation, ...]:
    payload = json.loads(content.decode("utf-8"))
    facts = payload.get("facts")
    if not isinstance(facts, Mapping):
        raise ValueError("SEC companyfacts response has no facts object")
    entity_id = require_text(source.get("entity_id"), "SEC source entity_id")
    selections = source.get("selections")
    if not isinstance(selections, list) or not selections:
        raise ValueError("SEC source selections must be a nonempty list")
    observations: list[MetricObservation] = []
    seen: set[tuple[str, str, str, str, float]] = set()
    for selection in selections:
        if not isinstance(selection, Mapping):
            raise ValueError("SEC selection must be a mapping")
        metric_id = require_text(selection.get("metric_id"), "SEC selection metric_id")
        taxonomy = require_text(selection.get("taxonomy", "us-gaap"), "SEC selection taxonomy")
        concept = require_text(selection.get("concept"), "SEC selection concept")
        fallback_concepts = selection.get("fallback_concepts") or []
        if not isinstance(fallback_concepts, list):
            raise ValueError("SEC selection fallback_concepts must be a list")
        configured_concepts = [
            concept,
            *(require_text(value, "SEC fallback concept") for value in fallback_concepts),
        ]
        concepts = tuple(dict.fromkeys(
            (*_SEC_METRIC_CONCEPT_ALIASES.get(metric_id, ()), *configured_concepts)
        ))
        source_unit = require_text(selection.get("source_unit"), "SEC selection source_unit")
        output_unit = require_text(selection.get("unit", source_unit), "SEC selection unit")
        period = require_text(selection.get("period", "any"), "SEC selection period")
        scale = float(selection.get("scale", 1.0))
        allowed_forms = set(str(row) for row in selection.get("forms", []))
        selected_facts: dict[tuple[str, str, str], tuple[int, str, Mapping[str, Any]]] = {}
        for priority, candidate_concept in enumerate(concepts):
            concept_payload = facts.get(taxonomy, {}).get(candidate_concept, {})
            units = concept_payload.get("units", {}) if isinstance(concept_payload, Mapping) else {}
            candidate_rows = units.get(source_unit, []) if isinstance(units, Mapping) else []
            if not isinstance(candidate_rows, list):
                continue
            for fact in candidate_rows:
                if not isinstance(fact, Mapping) or not _sec_period_matches(fact, period):
                    continue
                if allowed_forms and str(fact.get("form") or "") not in allowed_forms:
                    continue
                key = (
                    str(fact.get("accn") or ""), str(fact.get("end") or ""),
                    str(fact.get("frame") or ""),
                )
                if key[0] and key[1] and (
                    key not in selected_facts or priority < selected_facts[key][0]
                ):
                    selected_facts[key] = (priority, candidate_concept, fact)
        for _priority, selected_concept, fact in selected_facts.values():
            filed = str(fact.get("filed") or "")
            observed = str(fact.get("end") or "")
            accession = str(fact.get("accn") or "")
            if not filed or not observed or not accession:
                continue
            try:
                value = float(fact["val"]) * scale
            except (KeyError, TypeError, ValueError):
                continue
            dedupe = (metric_id, accession, observed, str(fact.get("frame") or ""), value)
            if dedupe in seen:
                continue
            seen.add(dedupe)
            observed_at = _timestamp(observed, "SEC fact end", end_of_day=True)
            available_at = _timestamp(filed, "SEC fact filed", end_of_day=True)
            if available_at < observed_at:
                continue
            identity = stable_sha256({
                "source": source["id"], "metric": metric_id, "concept": selected_concept, "accession": accession,
                "observed": observed, "frame": fact.get("frame"), "value": value,
            })[:20]
            observations.append(MetricObservation(
                observation_id=f"{source['id']}:{metric_id}:{identity}",
                entity_id=entity_id,
                metric_id=metric_id,
                value=value,
                unit=output_unit,
                observed_at=observed_at,
                available_at=available_at,
                source_ref=str(source["id"]),
            ))
    return tuple(observations)


def _sec_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    cik = re.sub(r"\D", "", require_text(source.get("cik"), "SEC source cik"))
    if not cik or len(cik) > 10:
        raise ValueError("SEC CIK must contain at most 10 digits")
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"
    user_agent_env = str(source.get("user_agent_env") or "ZTARE_SEC_USER_AGENT")
    user_agent = str(
        os.environ.get(user_agent_env)
        or source.get("user_agent")
        or DEFAULT_SEC_USER_AGENT
    ).strip()
    content, headers = _fetch_sec(
        url, user_agent=user_agent, timeout=float(source.get("timeout_seconds", 30)),
    )
    relative, digest = _cache_raw(workspace, str(source["id"]), "sec-companyfacts", content, ".json")
    observations = parse_sec_companyfacts(content, source)
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="sec_companyfacts", canonical_url=url,
        retrieved_at=retrieved_at, content_sha256=digest, raw_path=relative,
        media_type=headers.get("content-type", "application/json").split(";")[0],
        availability_mode="provider_filed_date", observation_count=len(observations),
        provider_note="SEC EDGAR XBRL facts; availability is conservatively set to filing-date end of day.",
    )
    return receipt, observations


def _sec_submissions_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str,
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Cache the SEC filing index as an event sensor, without deriving metrics."""
    cik = re.sub(r"\D", "", require_text(source.get("cik"), "SEC submissions cik"))
    if not cik or len(cik) > 10:
        raise ValueError("SEC CIK must contain at most 10 digits")
    url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
    user_agent_env = str(source.get("user_agent_env") or "ZTARE_SEC_USER_AGENT")
    user_agent = str(
        os.environ.get(user_agent_env) or source.get("user_agent") or DEFAULT_SEC_USER_AGENT
    ).strip()
    content, headers = _fetch_sec(
        url, user_agent=user_agent, timeout=float(source.get("timeout_seconds", 30)),
    )
    relative, digest = _cache_raw(
        workspace, str(source["id"]), "sec-submissions", content, ".json",
    )
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="sec_submissions", canonical_url=url,
        retrieved_at=retrieved_at, content_sha256=digest, raw_path=relative,
        media_type=headers.get("content-type", "application/json").split(";")[0],
        availability_mode="retrieval_only", observation_count=0,
        provider_note=(
            "SEC EDGAR submissions index used only as a content-addressed filing-event sensor."
        ),
    )
    return receipt, ()


def fetch_sec_filing_document(
    workspace: str | Path, *, source_id: str, cik: str,
    accession_number: str, primary_document: str, accepted_at: str,
    retrieved_at: str | None = None, user_agent: str | None = None,
) -> dict[str, Any]:
    """Cache one immutable SEC filing document with provider-time lineage."""
    root = Path(workspace).expanduser().resolve()
    source = _safe_source_id(source_id)
    cik_digits = re.sub(r"\D", "", require_text(cik, "SEC filing cik"))
    accession = require_text(accession_number, "SEC filing accession")
    document = require_text(primary_document, "SEC filing primary document")
    if not cik_digits or len(cik_digits) > 10:
        raise ValueError("SEC filing cik must contain at most 10 digits")
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
        raise ValueError("SEC filing accession has an unsupported shape")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", document) or ".." in document:
        raise ValueError("SEC filing primary document must be one safe filename")
    available_at = canonical_timestamp(accepted_at, "SEC filing accepted_at")
    fetched_at = canonical_timestamp(retrieved_at or _utc_now(), "SEC filing retrieved_at")
    accession_path = accession.replace("-", "")
    url = (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik_digits)}/"
        f"{accession_path}/{document}"
    )
    content, headers = _fetch_sec(
        url, user_agent=str(user_agent or DEFAULT_SEC_USER_AGENT),
    )
    relative, digest = _cache_raw(root, source, "sec-filing", content, ".html")
    receipt = SourceReceipt(
        source_id=source, adapter="sec_filing_document", canonical_url=url,
        retrieved_at=fetched_at, content_sha256=digest, raw_path=relative,
        media_type=headers.get("content-type", "text/html").split(";")[0],
        availability_mode="provider_acceptance_time", observation_count=0,
        provider_note="Immutable SEC accession document; availability is EDGAR acceptance time.",
    ).to_dict()
    body = {
        "schema": "jaggedthoughts-sec-filing-document-v1",
        "accession_number": accession, "primary_document": document,
        "accepted_at": available_at, "receipt": receipt,
    }
    return {**body, "filing_document_sha256": stable_sha256(body)}


def capture_sec_filing_url(
    workspace: str | Path, *, source_id: str, url: str,
    retrieved_at: str | None = None, user_agent: str | None = None,
) -> dict[str, Any]:
    """Resolve an EDGAR document URL to provider chronology and cached bytes."""
    match = re.fullmatch(
        r"https://www\.sec\.gov/Archives/edgar/data/(\d+)/(\d{18})/([A-Za-z0-9_.-]+)",
        require_text(url, "SEC filing URL"),
    )
    if not match:
        raise ValueError("source is not a canonical SEC filing document URL")
    cik, accession_path, document = match.groups()
    accession = f"{accession_path[:10]}-{accession_path[10:12]}-{accession_path[12:]}"
    fetched_at = canonical_timestamp(retrieved_at or _utc_now(), "SEC capture retrieved_at")
    agent = str(user_agent or DEFAULT_SEC_USER_AGENT)
    submissions_url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
    content, headers = _fetch_sec(submissions_url, user_agent=agent)
    metadata_path, metadata_digest = _cache_raw(
        Path(workspace).expanduser().resolve(), _safe_source_id(source_id),
        "sec-submissions-metadata", content, ".json",
    )
    recent = ((json.loads(content).get("filings") or {}).get("recent") or {})
    accessions = list(recent.get("accessionNumber") or ())
    try:
        index = accessions.index(accession)
    except ValueError as error:
        raise ValueError("SEC filing URL is absent from the issuer submissions chronology") from error
    primary_documents = list(recent.get("primaryDocument") or ())
    accepted_times = list(recent.get("acceptanceDateTime") or ())
    if index >= len(primary_documents) or primary_documents[index] != document:
        raise ValueError("SEC filing URL document differs from provider chronology")
    if index >= len(accepted_times) or not accepted_times[index]:
        raise ValueError("SEC filing chronology lacks an acceptance time")
    accepted_at = canonical_timestamp(
        accepted_times[index], "SEC filing provider acceptance time",
    )
    filing = fetch_sec_filing_document(
        workspace, source_id=source_id, cik=cik, accession_number=accession,
        primary_document=document, accepted_at=accepted_at,
        retrieved_at=fetched_at, user_agent=agent,
    )
    metadata_receipt = SourceReceipt(
        source_id=_safe_source_id(source_id), adapter="sec_submissions_metadata",
        canonical_url=submissions_url, retrieved_at=fetched_at,
        content_sha256=metadata_digest, raw_path=metadata_path,
        media_type=headers.get("content-type", "application/json").split(";")[0],
        availability_mode="provider_acceptance_index", observation_count=0,
        provider_note="SEC submissions chronology used to verify filing acceptance time.",
    ).to_dict()
    body = {
        "schema": "jaggedthoughts-sec-filing-url-capture-v1",
        "source_url": url, "accession_number": accession,
        "accepted_at": accepted_at, "filing_document": filing,
        "content_sha256": filing["receipt"]["content_sha256"],
        "metadata_receipt": metadata_receipt,
        "publication_time_authority": "sec_provider_acceptance_time",
    }
    return {**body, "capture_sha256": stable_sha256(body)}


def _fred_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str, as_of: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    api_env = str(source.get("api_key_env") or "FRED_API_KEY")
    api_key = str(os.environ.get(api_env) or "").strip()
    if not api_key:
        raise ValueError(f"FRED source requires the free API key environment variable {api_env}")
    series_id = require_text(source.get("series_id"), "FRED series_id")
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "output_type": "4",
        "realtime_start": str(source.get("realtime_start") or "1776-07-04"),
        "realtime_end": canonical_timestamp(as_of, "source as_of")[:10],
        "observation_end": canonical_timestamp(as_of, "source as_of")[:10],
        "limit": "100000",
        "sort_order": "asc",
    }
    url = "https://api.stlouisfed.org/fred/series/observations?" + urlencode(params)
    content, headers = _fetch(url, user_agent=str(source.get("user_agent") or "JaggedThoughts-Capital/1.0"))
    relative, digest = _cache_raw(workspace, str(source["id"]), "fred-series", content, ".json")
    payload = json.loads(content.decode("utf-8"))
    rows = payload.get("observations")
    if not isinstance(rows, list):
        raise ValueError(str(payload.get("error_message") or "FRED response has no observations"))
    entity_id = require_text(source.get("entity_id", "US-MACRO"), "FRED entity_id")
    metric_id = require_text(source.get("metric_id", series_id.lower()), "FRED metric_id")
    unit = require_text(source.get("unit"), "FRED unit")
    scale = float(source.get("scale", 1.0))
    observations: list[MetricObservation] = []
    for row in rows:
        if not isinstance(row, Mapping) or str(row.get("value") or ".") == ".":
            continue
        observed = str(row.get("date") or "")
        available = str(row.get("realtime_start") or "")
        if not observed or not available:
            continue
        identity = stable_sha256({"source": source["id"], "series": series_id, "row": dict(row)})[:20]
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:{metric_id}:{identity}", entity_id=entity_id,
            metric_id=metric_id, value=float(row["value"]) * scale, unit=unit,
            observed_at=_timestamp(observed, "FRED observation date", end_of_day=True),
            available_at=_timestamp(available, "FRED realtime_start", end_of_day=True),
            source_ref=str(source["id"]),
        ))
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="fred_series", canonical_url=_redacted_url(url),
        retrieved_at=retrieved_at, content_sha256=digest, raw_path=relative,
        media_type=headers.get("content-type", "application/json").split(";")[0],
        availability_mode="provider_vintage", observation_count=len(observations),
        provider_note="FRED/ALFRED observations retain provider realtime_start vintage dates.",
    )
    return receipt, tuple(observations)


def _alpha_vantage_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    api_env = str(source.get("api_key_env") or "ALPHAVANTAGE_API_KEY")
    api_key = str(os.environ.get(api_env) or source.get("demo_api_key") or "").strip()
    if not api_key:
        raise ValueError(f"Alpha Vantage source requires the free API key environment variable {api_env}")
    symbol = require_text(source.get("symbol"), "Alpha Vantage symbol")
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": str(source.get("outputsize") or "compact"),
        "datatype": "csv",
        "apikey": api_key,
    }
    url = "https://www.alphavantage.co/query?" + urlencode(params)
    content, headers = _fetch(url, user_agent=str(source.get("user_agent") or "JaggedThoughts-Capital/1.0"))
    text = content.decode("utf-8", errors="replace")
    if text.lstrip().startswith("{"):
        payload = json.loads(text)
        raise ValueError(str(payload.get("Information") or payload.get("Note") or payload.get("Error Message") or "price response was not CSV"))
    relative, digest = _cache_raw(workspace, str(source["id"]), "alpha-vantage-daily", content, ".csv")
    entity_id = require_text(source.get("entity_id"), "Alpha Vantage entity_id")
    metric_id = require_text(source.get("metric_id", "price"), "Alpha Vantage metric_id")
    unit = require_text(source.get("unit", "USD"), "Alpha Vantage unit")
    value_column = str(source.get("value_column") or "close")
    observations: list[MetricObservation] = []
    for row in csv.DictReader(io.StringIO(text)):
        if not row.get("timestamp") or not row.get(value_column):
            continue
        identity = stable_sha256({
            "source": source["id"], "symbol": symbol, "row": row,
        })[:20]
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:{metric_id}:{identity}", entity_id=entity_id,
            metric_id=metric_id, value=float(row[value_column]), unit=unit,
            observed_at=_timestamp(row["timestamp"], "price date", end_of_day=True),
            available_at=retrieved_at, source_ref=str(source["id"]),
        ))
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="alpha_vantage_daily", canonical_url=_redacted_url(url),
        retrieved_at=retrieved_at, content_sha256=digest, raw_path=relative,
        media_type=headers.get("content-type", "text/csv").split(";")[0],
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note="Daily raw close data; historical information availability is bounded by this retrieval time.",
    )
    return receipt, tuple(observations)


def _numeric(value: Any, label: str) -> float:
    """Parse a provider number while rejecting booleans and non-finite values."""
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        numeric = float(
            str(value).strip().replace(",", "").removeprefix("$").removesuffix("%")
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not math.isfinite(numeric):
        raise ValueError(f"{label} must be finite")
    return numeric


def _materialize_fund_holdings(
    workspace: Path,
    *,
    source: Mapping[str, Any],
    entity_id: str,
    observed_at: str,
    retrieved_at: str,
    source_url: str,
    source_digest: str,
    raw_path: str,
    holdings: Sequence[Mapping[str, Any]],
    reported_count: int | None = None,
    provider_row_count: int | None = None,
    holdings_scope: str = "complete_provider_holdings",
) -> tuple[MetricObservation, ...]:
    """Validate one issuer holdings epoch and write its common snapshot contract."""
    raw_row_count = provider_row_count if provider_row_count is not None else len(holdings)
    if reported_count is not None and reported_count != len(holdings):
        raise ValueError(
            f"fund holdings coverage mismatch: parsed {len(holdings)} of {reported_count}"
        )
    by_identifier: dict[str, dict[str, Any]] = {}
    for raw in holdings:
        identifier = require_text(raw.get("identifier"), "fund holding identifier").upper()
        weight = _numeric(raw.get("weight"), f"fund holding {identifier} weight")
        if weight == 0:
            continue
        if weight < 0 or weight > 1.05:
            raise ValueError(f"fund holding {identifier} weight must be in (0, 1.05]")
        row: dict[str, Any] = {
            "identifier": identifier,
            "security_name": require_text(
                raw.get("security_name"), f"fund holding {identifier} security_name"
            ),
            "weight": weight,
        }
        for key in ("cusip", "classification", "asset_class", "country"):
            value = str(raw.get(key) or "").strip()
            if value:
                row[key] = value
        for key in ("shares", "market_value"):
            if raw.get(key) not in (None, ""):
                row[key] = _numeric(raw[key], f"fund holding {identifier} {key}")
        current = by_identifier.get(identifier)
        if current is None:
            by_identifier[identifier] = row
            continue
        for key in ("security_name", "cusip", "classification", "asset_class", "country"):
            if current.get(key) and row.get(key) and current[key] != row[key]:
                raise ValueError(f"fund holding {identifier} has incompatible duplicate {key}")
            if row.get(key) and not current.get(key):
                current[key] = row[key]
        current["weight"] = float(current["weight"]) + weight
        for key in ("shares", "market_value"):
            if key in row:
                current[key] = float(current.get(key, 0.0)) + float(row[key])
    normalized = [row for row in by_identifier.values() if float(row["weight"]) > 0]
    normalized.sort(key=lambda row: (-float(row["weight"]), row["identifier"]))
    if not normalized:
        raise ValueError("fund holdings snapshot cannot be empty")
    weights = [float(row["weight"]) for row in normalized]
    disclosed_weight = sum(weights)
    if disclosed_weight > 1.05:
        raise ValueError(f"fund disclosed holdings weight exceeds 105%: {disclosed_weight:.6f}")
    sector_weights: dict[str, float] = {}
    classified_weight = 0.0
    for row in normalized:
        classification = str(row.get("classification") or "").strip()
        if classification:
            classified_weight += float(row["weight"])
            sector_weights[classification] = (
                sector_weights.get(classification, 0.0) + float(row["weight"])
            )
    metrics: list[tuple[str, float, str]] = [
        ("portfolio_holdings_count", float(reported_count or len(normalized)), "count"),
        ("portfolio_top10_concentration", sum(weights[:10]), "decimal"),
        ("portfolio_max_holding_weight", weights[0], "decimal"),
        ("portfolio_holdings_hhi", sum(value * value for value in weights), "score"),
    ]
    if sector_weights and classified_weight >= disclosed_weight * 0.95:
        metrics.extend((
            ("portfolio_sector_hhi", sum(value * value for value in sector_weights.values()), "score"),
            ("portfolio_top_sector_weight", max(sector_weights.values()), "decimal"),
        ))
    source_id = str(source["id"])
    observations = tuple(MetricObservation(
        observation_id=(
            f"{source_id}:{metric_id}:"
            f"{stable_sha256({'source': source_id, 'metric_id': metric_id, 'observed_at': observed_at, 'value': value})[:20]}"
        ),
        entity_id=entity_id, metric_id=metric_id, value=value, unit=unit,
        observed_at=observed_at, available_at=retrieved_at, source_ref=source_id,
    ) for metric_id, value, unit in metrics)
    snapshot_body = {
        "schema": FUND_HOLDINGS_SNAPSHOT_SCHEMA,
        "entity_id": entity_id, "as_of": observed_at, "available_at": retrieved_at,
        "source_id": source_id, "source_url": source_url,
        "source_content_sha256": source_digest, "raw_path": raw_path,
        "reported_count": reported_count, "provider_row_count": raw_row_count,
        "holdings_scope": require_text(holdings_scope, "fund holdings_scope"),
        "parsed_count": len(normalized),
        "disclosed_weight": disclosed_weight,
        "classified_weight": classified_weight,
        "sector_weights": dict(sorted(sector_weights.items())),
        "holdings": normalized,
    }
    _atomic_json(
        workspace / "data" / "fund_holdings" / f"{entity_id.lower()}.json",
        {**snapshot_body, "snapshot_sha256": stable_sha256(snapshot_body)},
    )
    return observations


def _alpha_vantage_etf_profile_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Normalize ETF_PROFILE aggregates without treating holdings as a vintage archive."""
    api_env = str(source.get("api_key_env") or "ALPHAVANTAGE_API_KEY")
    api_key = str(os.environ.get(api_env) or source.get("demo_api_key") or "").strip()
    if not api_key:
        raise ValueError(f"Alpha Vantage source requires the free API key environment variable {api_env}")
    symbol = require_text(source.get("symbol"), "Alpha Vantage ETF symbol")
    entity_id = require_text(source.get("entity_id", symbol), "Alpha Vantage ETF entity_id")
    url = "https://www.alphavantage.co/query?" + urlencode({
        "function": "ETF_PROFILE", "symbol": symbol, "apikey": api_key,
    })
    content, headers = _fetch(
        url, user_agent=str(source.get("user_agent") or "JaggedThoughts-Capital/1.0")
    )
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Alpha Vantage ETF profile response is not an object")
    provider_error = payload.get("Information") or payload.get("Note") or payload.get("Error Message")
    if provider_error:
        raise ValueError(str(provider_error))
    relative, digest = _cache_raw(
        workspace, str(source["id"]), "alpha-vantage-etf-profile", content, ".json"
    )
    holdings = [row for row in payload.get("holdings", []) if isinstance(row, Mapping)]
    sectors = [row for row in payload.get("sectors", []) if isinstance(row, Mapping)]
    holding_weights = [
        _numeric(row.get("weight"), "ETF holding weight")
        for row in holdings if row.get("weight") not in (None, "")
    ]
    sector_weights = [
        _numeric(row.get("weight"), "ETF sector weight")
        for row in sectors if row.get("weight") not in (None, "")
    ]
    raw_metrics: list[tuple[str, Any, str, float]] = [
        ("fund_net_assets", payload.get("net_assets"), "USD", 1.0),
        ("expense_ratio", payload.get("net_expense_ratio"), "decimal", 1.0),
        ("portfolio_turnover", payload.get("portfolio_turnover"), "decimal", 1.0),
        ("portfolio_trailing_yield", payload.get("dividend_yield"), "decimal", 1.0),
        ("portfolio_holdings_count", len(holdings), "count", 1.0),
        ("portfolio_top10_concentration", sum(sorted(holding_weights, reverse=True)[:10]), "decimal", 1.0),
        ("portfolio_max_holding_weight", max(holding_weights, default=0.0), "decimal", 1.0),
        ("portfolio_sector_hhi", sum(value * value for value in sector_weights), "score", 1.0),
    ]
    observations: list[MetricObservation] = []
    for metric_id, raw_value, unit, scale in raw_metrics:
        if raw_value in (None, ""):
            continue
        value = _numeric(raw_value, f"ETF profile {metric_id}") * scale
        identity = stable_sha256({
            "source": source["id"], "symbol": symbol, "metric_id": metric_id,
            "value": value, "retrieved_at": retrieved_at,
        })[:20]
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:{metric_id}:{identity}", entity_id=entity_id,
            metric_id=metric_id, value=value, unit=unit, observed_at=retrieved_at,
            available_at=retrieved_at, source_ref=str(source["id"]),
        ))
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="alpha_vantage_etf_profile",
        canonical_url=_redacted_url(url), retrieved_at=retrieved_at,
        content_sha256=digest, raw_path=relative,
        media_type=headers.get("content-type", "application/json").split(";")[0],
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note=(
            "Alpha Vantage ETF_PROFILE aggregates and current holdings; historical use begins "
            "at this retrieval receipt because the response exposes no availability vintages."
        ),
    )
    return receipt, tuple(observations)


def _ishares_characteristics_payload(content: bytes) -> Mapping[str, Any]:
    decoded = content.decode("utf-8", errors="replace")
    for tag in re.findall(r"<walrus-render-on-client\b[^>]*>", decoded):
        if "PortfolioCharacteristicsV3" not in tag:
            continue
        match = re.search(r'componentprops="([^"]*)"', tag)
        if not match:
            continue
        payload = json.loads(unescape(match.group(1)))
        if isinstance(payload, Mapping):
            return payload
    raise ValueError("iShares page did not expose PortfolioCharacteristicsV3 data")


def _ishares_key_facts_payload(content: bytes) -> Mapping[str, Any]:
    """Return issuer key facts without leaking provider field names downstream."""
    decoded = content.decode("utf-8", errors="replace")
    for tag in re.findall(r"<walrus-render-on-client\b[^>]*>", decoded):
        if 'componentkey="KeyFundFactsV3"' not in tag:
            continue
        match = re.search(r'componentprops="([^"]*)"', tag)
        if match:
            payload = json.loads(unescape(match.group(1)))
            if isinstance(payload, Mapping):
                return payload
    raise ValueError("iShares page did not expose KeyFundFactsV3 data")


def _ishares_holdings_rows(content: bytes) -> tuple[str, list[dict[str, Any]]]:
    """Parse iShares' issuer CSV preamble and equity rows."""
    rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig", errors="replace"))))
    header_index = next((
        index for index, row in enumerate(rows)
        if len(row) >= 2 and row[0].strip() == "Ticker" and row[1].strip() == "Name"
    ), None)
    if header_index is None:
        raise ValueError("iShares holdings CSV omitted its header")
    as_of_text = next((
        row[1].strip() for row in rows[:header_index]
        if len(row) >= 2 and row[0].strip().lower() == "fund holdings as of"
    ), "")
    if not as_of_text:
        raise ValueError("iShares holdings CSV omitted its as-of date")
    observed_at = _timestamp(
        datetime.strptime(as_of_text, "%b %d, %Y").date().isoformat(),
        "iShares holdings as-of date", end_of_day=True,
    )
    header = [value.strip() for value in rows[header_index]]
    holdings: list[dict[str, Any]] = []
    for values in rows[header_index + 1:]:
        if not values or not any(value.strip() for value in values):
            continue
        row = dict(zip(header, values))
        if str(row.get("Asset Class") or "").strip().lower() != "equity":
            continue
        ticker = str(row.get("Ticker") or "").strip()
        security_name = str(row.get("Name") or "").strip()
        exchange = str(row.get("Exchange") or "").strip()
        weight = str(row.get("Weight (%)") or "").strip()
        if not ticker or not weight:
            continue
        identifier = (
            ticker if ticker != "-" else f"NAME:{require_text(security_name, 'iShares holding name')}"
        )
        holdings.append({
            "identifier": f"{identifier}@{exchange}" if exchange else identifier,
            "security_name": security_name,
            "classification": row.get("Sector"),
            "asset_class": row.get("Asset Class"),
            "country": row.get("Location"),
            "shares": row.get("Quantity"),
            "market_value": row.get("Market Value"),
            "weight": _numeric(weight, f"iShares holding {ticker} weight") * 0.01,
        })
    return observed_at, holdings


def _ishares_fundamentals_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Read issuer-published aggregate portfolio characteristics from an iShares page."""
    symbol = str(source.get("symbol") or source.get("entity_id") or "").strip().upper()
    url = str(source.get("url") or "").strip()
    catalog_digest = ""
    if not url:
        symbol = require_text(symbol, "iShares source symbol")
        catalog_url = str(
            source.get("catalog_url")
            or "https://www.ishares.com/us/products/etf-investments"
        )
        catalog, _catalog_headers = _fetch(
            catalog_url,
            user_agent=str(source.get("user_agent") or "Mozilla/5.0 JaggedThoughts-Capital/1.0"),
            timeout=float(source.get("timeout_seconds", 30)),
        )
        catalog_digest = hashlib.sha256(catalog).hexdigest()
        decoded_catalog = catalog.decode("utf-8", errors="replace")
        matches = {
            urljoin(catalog_url, unescape(match.group(1)))
            for match in re.finditer(
                rf'<a\s+href="([^"]+)"[^>]*>\s*{re.escape(symbol)}\s*</a>',
                decoded_catalog,
                flags=re.IGNORECASE,
            )
        }
        if len(matches) != 1:
            raise ValueError(
                f"iShares product catalog resolved {len(matches)} product pages for {symbol}"
            )
        url = matches.pop()
    url = require_text(url, "iShares source url")
    entity_id = require_text(source.get("entity_id"), "iShares entity_id")
    content, _page_headers = _fetch(
        url,
        user_agent=str(source.get("user_agent") or "Mozilla/5.0 JaggedThoughts-Capital/1.0"),
        timeout=float(source.get("timeout_seconds", 30)),
    )
    page_relative, page_digest = _cache_raw(
        workspace, str(source["id"]), "ishares-product", content, ".html"
    )
    payload = _ishares_characteristics_payload(content)
    points = (
        payload.get("containersByNameMap", {})
        .get("default", {})
        .get("dataPointsByNameMap", {})
    )
    if not isinstance(points, Mapping):
        raise ValueError("iShares characteristics payload has no data-point map")
    mapping = {
        "priceEarnings": ("portfolio_price_to_earnings", "multiple", 1.0),
        "priceBook": ("portfolio_price_to_book", "multiple", 1.0),
        "beta3Yr": ("portfolio_equity_beta", "multiple", 1.0),
        "standardDeviation3Yr": ("portfolio_standard_deviation_3y", "decimal", 0.01),
        "twelveMonTrlYld": ("portfolio_trailing_yield", "decimal", 0.01),
    }
    observations: list[MetricObservation] = []
    for provider_id, (metric_id, unit, scale) in mapping.items():
        row = points.get(provider_id)
        if not isinstance(row, Mapping) or row.get("value") in (None, ""):
            continue
        value = _numeric(row.get("value"), f"iShares {provider_id}") * scale
        date_text = str(row.get("asOfDate") or "")
        observed_at = retrieved_at
        if re.fullmatch(r"\d{8}", date_text):
            observed_at = _timestamp(
                f"{date_text[:4]}-{date_text[4:6]}-{date_text[6:]}",
                f"iShares {provider_id} as-of date", end_of_day=True,
            )
        identity = stable_sha256({
            "source": source["id"], "provider_id": provider_id,
            "observed_at": observed_at, "value": value,
        })[:20]
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:{metric_id}:{identity}", entity_id=entity_id,
            metric_id=metric_id, value=value, unit=unit, observed_at=observed_at,
            available_at=retrieved_at, source_ref=str(source["id"]),
        ))
    key_facts = _ishares_key_facts_payload(content).get("dataPoints") or {}
    if not isinstance(key_facts, Mapping):
        raise ValueError("iShares key facts have no data-point map")
    for provider_id, metric_id, unit, scale in (
        ("totalNetAssetsFundLevel", "fund_net_assets", "USD", 1.0),
        ("thirtyDayMedianBidAskSpread", "median_bid_ask_spread", "decimal", 0.01),
        ("thirtyDayAverageVolume", "average_daily_volume_30d", "shares/day", 1.0),
    ):
        row = key_facts.get(provider_id)
        if not isinstance(row, Mapping) or row.get("formattedValue") in (None, ""):
            continue
        value = _numeric(row["formattedValue"], f"iShares {provider_id}") * scale
        raw_date = row.get("formattedAsOfDate")
        observed_at = (
            _timestamp(
                datetime.strptime(str(raw_date), "%b %d, %Y").date().isoformat(),
                f"iShares {provider_id} as-of date", end_of_day=True,
            ) if raw_date else retrieved_at
        )
        identity = stable_sha256({
            "source": source["id"], "provider_id": provider_id,
            "observed_at": observed_at, "value": value,
        })[:20]
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:{metric_id}:{identity}", entity_id=entity_id,
            metric_id=metric_id, value=value, unit=unit, observed_at=observed_at,
            available_at=retrieved_at, source_ref=str(source["id"]),
        ))
    decoded = content.decode("utf-8", errors="replace")
    if symbol and not re.search(rf"\b{re.escape(symbol)}\b", decoded, flags=re.IGNORECASE):
        raise ValueError(f"iShares product page did not confirm ticker {symbol}")
    expense = re.search(
        r'"name"\s*:\s*"Expense Ratio:"\s*,\s*"value"\s*:\s*"([0-9.,]+)"',
        decoded,
    )
    if expense:
        value = _numeric(expense.group(1), "iShares expense ratio") * 0.01
        identity = stable_sha256({
            "source": source["id"], "metric_id": "expense_ratio",
            "retrieved_at": retrieved_at, "value": value,
        })[:20]
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:expense_ratio:{identity}", entity_id=entity_id,
            metric_id="expense_ratio", value=value, unit="decimal", observed_at=retrieved_at,
            available_at=retrieved_at, source_ref=str(source["id"]),
        ))
    holdings_urls = {
        urljoin(url, unescape(match.group(1)))
        for match in re.finditer(
            r'href="([^"]+/latest-holdings\.csv(?:\?[^"]*)?)"',
            decoded, flags=re.IGNORECASE,
        )
    }
    if len(holdings_urls) != 1:
        raise ValueError(
            f"iShares product page resolved {len(holdings_urls)} full-holdings downloads"
        )
    holdings_url = holdings_urls.pop()
    holdings_content, _holdings_headers = _fetch(
        holdings_url,
        user_agent=str(source.get("user_agent") or "Mozilla/5.0 JaggedThoughts-Capital/1.0"),
        timeout=float(source.get("timeout_seconds", 30)),
        extra_headers={"Accept": "text/csv"},
    )
    holdings_relative, holdings_digest = _cache_raw(
        workspace, str(source["id"]), "ishares-holdings", holdings_content, ".csv"
    )
    holdings_at, holdings = _ishares_holdings_rows(holdings_content)
    count_row = points.get("numHoldings")
    reported_count = int(_numeric(count_row.get("value"), "iShares holdings count")) if (
        isinstance(count_row, Mapping) and count_row.get("value") not in (None, "")
    ) else None
    provider_row_count = len(holdings)
    holdings_scope = "complete_provider_equity_holdings"
    if reported_count and len(holdings) > reported_count:
        direct = sorted(holdings, key=lambda row: float(row["weight"]), reverse=True)[:reported_count]
        direct_weight = sum(float(row["weight"]) for row in direct)
        total_weight = sum(float(row["weight"]) for row in holdings)
        if 0.95 <= direct_weight <= 1.05 and total_weight >= direct_weight + 0.5:
            holdings = direct
            holdings_scope = "issuer_reported_direct_holdings_filtered_from_lookthrough"
    observations.extend(_materialize_fund_holdings(
        workspace, source=source, entity_id=entity_id, observed_at=holdings_at,
        retrieved_at=retrieved_at, source_url=holdings_url,
        source_digest=holdings_digest, raw_path=holdings_relative,
        holdings=holdings, reported_count=reported_count,
        provider_row_count=provider_row_count, holdings_scope=holdings_scope,
    ))
    if not observations:
        raise ValueError("iShares page contained no supported portfolio characteristics")
    envelope = json.dumps({
        "product_url": url, "product_raw_path": page_relative,
        "product_sha256": page_digest, "holdings_url": holdings_url,
        "holdings_raw_path": holdings_relative, "holdings_sha256": holdings_digest,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")
    relative, digest = _cache_raw(
        workspace, str(source["id"]), "ishares-fundamentals", envelope, ".json"
    )
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="ishares_fundamentals", canonical_url=url,
        retrieved_at=retrieved_at, content_sha256=digest, raw_path=relative,
        media_type="application/json",
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note=(
            "Issuer-published aggregate portfolio characteristics plus complete equity holdings; "
            "economic as-of dates are retained and historical admissibility begins at retrieval."
            + (
                f" The product URL was resolved from issuer catalog SHA-256 {catalog_digest}."
                if catalog_digest else ""
            )
        ),
    )
    return receipt, tuple(observations)


def _vanguard_profile_payload(content: bytes) -> Mapping[str, Any]:
    decoded = content.decode("utf-8", errors="replace")
    match = re.search(
        r'<script\s+id="fundProfileData"\s+type="application/json">(.*?)</script>',
        decoded,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not match:
        raise ValueError("Vanguard profile page did not expose fundProfileData")
    payload = json.loads(unescape(match.group(1)))
    if not isinstance(payload, Mapping) or not isinstance(payload.get("fundProfile"), Mapping):
        raise ValueError("Vanguard fundProfileData is not an object")
    return payload


def _vanguard_number(value: Any, label: str) -> float:
    text = str(value).strip()
    text = re.sub(r"[xX]$", "", text)
    return _numeric(text, label)


def _vanguard_fundamentals_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Read Vanguard's public profile identity and characteristic API as one source."""
    symbol = require_text(
        source.get("symbol") or source.get("entity_id"), "Vanguard source symbol"
    ).upper()
    entity_id = require_text(source.get("entity_id", symbol), "Vanguard entity_id")
    profile_url = str(
        source.get("url")
        or f"https://investor.vanguard.com/investment-products/etfs/profile/{symbol.lower()}"
    )
    user_agent = str(source.get("user_agent") or "Mozilla/5.0 JaggedThoughts-Capital/1.0")
    timeout = float(source.get("timeout_seconds", 30))
    profile_content, profile_headers = _fetch(
        profile_url, user_agent=user_agent, timeout=timeout,
    )
    profile_payload = _vanguard_profile_payload(profile_content)
    profile = profile_payload["fundProfile"]
    if str(profile.get("ticker") or "").upper() != symbol:
        raise ValueError(f"Vanguard profile identity does not match {symbol}")
    api_url = str(
        source.get("characteristic_url")
        or (
            f"https://investor.vanguard.com/vmf/api/{symbol}/characteristic"
            "?isInternal=true&isBfpCharacteristicsToggle=true"
        )
    )
    characteristic_content, characteristic_headers = _fetch(
        api_url,
        user_agent=user_agent,
        timeout=timeout,
        extra_headers={"Accept": "application/json"},
    )
    characteristic_payload = json.loads(characteristic_content.decode("utf-8"))
    if not isinstance(characteristic_payload, Mapping):
        raise ValueError("Vanguard characteristic response is not an object")
    equity = characteristic_payload.get("equityCharacteristic")
    if not isinstance(equity, Mapping) or not isinstance(equity.get("fund"), Mapping):
        raise ValueError("Vanguard characteristic response has no equity fund object")
    fund = equity["fund"]
    observations: list[MetricObservation] = []

    def add(
        metric_id: str, raw_value: Any, unit: str, scale: float,
        raw_date: Any, provider_id: str,
    ) -> None:
        if raw_value in (None, ""):
            return
        value = _vanguard_number(raw_value, f"Vanguard {provider_id}") * scale
        observed_at = retrieved_at
        if raw_date not in (None, ""):
            observed_at = _timestamp(raw_date, f"Vanguard {provider_id} date", end_of_day=True)
        identity = stable_sha256({
            "source": source["id"], "provider_id": provider_id,
            "observed_at": observed_at, "value": value,
        })[:20]
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:{metric_id}:{identity}",
            entity_id=entity_id, metric_id=metric_id, value=value, unit=unit,
            observed_at=observed_at, available_at=retrieved_at,
            source_ref=str(source["id"]),
        ))

    mappings = (
        ("portfolio_price_to_earnings", "priceEarningsRatio", "multiple", 1.0),
        ("portfolio_price_to_book", "priceBookRatio", "multiple", 1.0),
        ("portfolio_return_on_equity", "returnOnEquity", "decimal", 0.01),
        ("portfolio_earnings_growth", "earningsGrowthRate", "decimal", 0.01),
        ("portfolio_holdings_count", "numberOfStocks", "count", 1.0),
        ("portfolio_turnover", "turnoverRate", "decimal", 0.01),
    )
    for metric_id, provider_id, unit, scale in mappings:
        add(
            metric_id, fund.get(provider_id), unit, scale,
            fund.get(f"{provider_id}Date") or equity.get("asOfDate"), provider_id,
        )
    add(
        "expense_ratio", profile.get("expenseRatio"), "decimal", 0.01,
        profile.get("expenseRatioAsOfDate"), "expenseRatio",
    )
    if not any(row.metric_id == "portfolio_price_to_earnings" for row in observations):
        raise ValueError("Vanguard source contained no portfolio P/E")
    if not any(row.metric_id == "portfolio_price_to_book" for row in observations):
        raise ValueError("Vanguard source contained no portfolio P/B")
    envelope = json.dumps({
        "profile_url": profile_url,
        "characteristic_url": api_url,
        "profile_sha256": hashlib.sha256(profile_content).hexdigest(),
        "characteristic_sha256": hashlib.sha256(characteristic_content).hexdigest(),
        "fund_profile": profile_payload,
        "characteristic": characteristic_payload,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    relative, digest = _cache_raw(
        workspace, str(source["id"]), "vanguard-fundamentals", envelope, ".json"
    )
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="vanguard_fundamentals",
        canonical_url=profile_url, retrieved_at=retrieved_at,
        content_sha256=digest, raw_path=relative,
        media_type=(
            characteristic_headers.get("content-type")
            or profile_headers.get("content-type")
            or "application/json"
        ).split(";")[0],
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note=(
            "Issuer profile identity plus issuer characteristic API; economic as-of dates are "
            "retained and historical admissibility begins at this retrieval."
        ),
    )
    return receipt, tuple(observations)


def _nested_objects(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _nested_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nested_objects(child)


def _harbor_fundamentals_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Read Harbor's public Gatsby page-data snapshot for one ETF identity."""
    symbol = require_text(
        source.get("symbol") or source.get("entity_id"), "Harbor source symbol"
    ).upper()
    entity_id = require_text(source.get("entity_id", symbol), "Harbor entity_id")
    product_url = str(
        source.get("url") or f"https://www.harborcapital.com/etf/{symbol.lower()}/"
    )
    data_url = str(
        source.get("data_url")
        or f"https://www.harborcapital.com/page-data/etf/{symbol.lower()}/page-data.json"
    )
    content, headers = _fetch(
        data_url,
        user_agent=str(source.get("user_agent") or "Mozilla/5.0 JaggedThoughts-Capital/1.0"),
        timeout=float(source.get("timeout_seconds", 30)),
        extra_headers={"Accept": "application/json"},
    )
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Harbor page-data response is not an object")
    page_context = payload.get("result")
    data = page_context.get("data") if isinstance(page_context, Mapping) else None
    product = data.get("contentstackProductV2") if isinstance(data, Mapping) else None
    if not isinstance(product, Mapping):
        raise ValueError("Harbor page-data has no product identity")
    context = payload.get("result", {}).get("pageContext", {})
    context_ticker = str(context.get("ticker") or "").upper() if isinstance(context, Mapping) else ""
    fund_classes = [row for row in product.get("fund_classes", []) if isinstance(row, Mapping)]
    matching_classes = [row for row in fund_classes if str(row.get("ticker") or "").upper() == symbol]
    if context_ticker != symbol or len(matching_classes) != 1:
        raise ValueError(f"Harbor page-data did not uniquely confirm ticker {symbol}")
    characteristics: list[Mapping[str, Any]] = []
    full_holdings: list[Mapping[str, Any]] = []
    for row in _nested_objects(product):
        if isinstance(row.get("portfolioCharacteristics"), list):
            characteristics.extend(
                item for item in row["portfolioCharacteristics"] if isinstance(item, Mapping)
            )
        if isinstance(row.get("fullHoldings"), list):
            full_holdings.extend(
                item for item in row["fullHoldings"] if isinstance(item, Mapping)
            )
    by_name: dict[str, Mapping[str, Any]] = {}
    for row in characteristics:
        name = str(row.get("name") or "")
        if name and name not in by_name:
            by_name[name] = row
    observations: list[MetricObservation] = []

    def add(metric_id: str, raw_value: Any, unit: str, scale: float, raw_date: Any, provider_id: str) -> None:
        if raw_value in (None, ""):
            return
        value = _numeric(raw_value, f"Harbor {provider_id}") * scale
        observed_at = (
            _timestamp(raw_date, f"Harbor {provider_id} date", end_of_day=True)
            if raw_date not in (None, "") else retrieved_at
        )
        identity = stable_sha256({
            "source": source["id"], "provider_id": provider_id,
            "observed_at": observed_at, "value": value,
        })[:20]
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:{metric_id}:{identity}",
            entity_id=entity_id, metric_id=metric_id, value=value, unit=unit,
            observed_at=observed_at, available_at=retrieved_at,
            source_ref=str(source["id"]),
        ))

    mappings = (
        ("portfolio_price_to_earnings", "Adjusted Trailing P/E Ratio", "multiple", 1.0),
        ("portfolio_price_to_book", "Price/Book Ratio", "multiple", 1.0),
        ("portfolio_return_on_equity", "Return on Equity (%)", "decimal", 0.01),
        ("portfolio_earnings_growth", "% EPS Growth - Past 3 Yr", "decimal", 0.01),
    )
    for metric_id, provider_id, unit, scale in mappings:
        row = by_name.get(provider_id)
        if row is None:
            continue
        calendar = row.get("calendar") if isinstance(row.get("calendar"), Mapping) else {}
        add(metric_id, row.get("fundValue"), unit, scale, calendar.get("date"), provider_id)
    expense = matching_classes[0].get("expense_ratio")
    expense = expense if isinstance(expense, Mapping) else {}
    add(
        "expense_ratio", expense.get("net") or expense.get("gross"),
        "decimal", 0.01, None, "expense_ratio",
    )
    holding_date = next((
        (row.get("calendar") or {}).get("date")
        for row in full_holdings
        if isinstance(row.get("calendar"), Mapping) and (row.get("calendar") or {}).get("date")
    ), None)
    required = {"portfolio_price_to_earnings", "portfolio_price_to_book", "expense_ratio"}
    if not required.issubset({row.metric_id for row in observations}):
        raise ValueError("Harbor page-data omitted a required valuation characteristic")
    relative, digest = _cache_raw(
        workspace, str(source["id"]), "harbor-fundamentals", content, ".json"
    )
    count_row = by_name.get("Number of Holdings")
    reported_count = int(_numeric(count_row.get("fundValue"), "Harbor holdings count")) if (
        isinstance(count_row, Mapping) and count_row.get("fundValue") not in (None, "")
    ) else None
    normalized_holdings = [{
        "identifier": row.get("ticker"), "security_name": row.get("securityName"),
        "cusip": row.get("cusip"), "classification": row.get("sectorName"),
        "asset_class": row.get("assetGroup"), "country": row.get("countryName"),
        "shares": row.get("shares"), "market_value": row.get("marketValue"),
        "weight": row.get("weight"),
    } for row in full_holdings if str(row.get("assetGroup") or "").upper() == "EQUITY"]
    observations.extend(_materialize_fund_holdings(
        workspace, source=source, entity_id=entity_id,
        observed_at=_timestamp(holding_date, "Harbor holdings date"),
        retrieved_at=retrieved_at, source_url=data_url, source_digest=digest,
        raw_path=relative, holdings=normalized_holdings, reported_count=reported_count,
    ))
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="harbor_fundamentals",
        canonical_url=product_url, retrieved_at=retrieved_at,
        content_sha256=digest, raw_path=relative,
        media_type=headers.get("content-type", "application/json").split(";")[0],
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note=(
            "Issuer-published Gatsby page-data snapshot with product identity, portfolio "
            "characteristics, fees, and holdings; historical use starts at retrieval."
        ),
    )
    return receipt, tuple(observations)


def _provider_date(value: Any) -> Any:
    text = str(value or "").strip()
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", text):
        return datetime.strptime(text, "%m/%d/%Y").date().isoformat()
    return value


def _avantis_fundamentals_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Read the issuer-hydrated Avantis fund object embedded in public HTML."""
    symbol = require_text(
        source.get("symbol") or source.get("entity_id"), "Avantis source symbol"
    ).upper()
    entity_id = require_text(source.get("entity_id", symbol), "Avantis entity_id")
    url = require_text(source.get("url"), "Avantis source url")
    content, headers = _fetch(
        url,
        user_agent=str(source.get("user_agent") or "Mozilla/5.0 JaggedThoughts-Capital/1.0"),
        timeout=float(source.get("timeout_seconds", 30)),
    )
    decoded = content.decode("utf-8", errors="replace")

    def assigned(field: str) -> str | None:
        match = re.search(rf"\ba\.{re.escape(field)}=\"([^\"]*)\"", decoded)
        return unescape(match.group(1)) if match else None

    if str(assigned("ticker") or "").upper() != symbol:
        raise ValueError(f"Avantis page did not confirm ticker {symbol}")
    characteristic = re.search(
        r"\ba\.characteristics=\{(.*?)\};a\.distributions=",
        decoded,
        flags=re.DOTALL,
    )
    if not characteristic:
        raise ValueError("Avantis page did not expose the hydrated characteristics object")
    body = characteristic.group(1)

    def field(name: str) -> str | None:
        match = re.search(rf"(?:^|,){re.escape(name)}:\"([^\"]*)\"", body)
        return unescape(match.group(1)) if match else None

    observations: list[MetricObservation] = []

    def add(metric_id: str, raw_value: Any, unit: str, scale: float, raw_date: Any, provider_id: str) -> None:
        if raw_value in (None, ""):
            return
        value = _numeric(raw_value, f"Avantis {provider_id}") * scale
        observed_at = (
            _timestamp(_provider_date(raw_date), f"Avantis {provider_id} date", end_of_day=True)
            if raw_date not in (None, "") else retrieved_at
        )
        identity = stable_sha256({
            "source": source["id"], "provider_id": provider_id,
            "observed_at": observed_at, "value": value,
        })[:20]
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:{metric_id}:{identity}", entity_id=entity_id,
            metric_id=metric_id, value=value, unit=unit, observed_at=observed_at,
            available_at=retrieved_at, source_ref=str(source["id"]),
        ))

    characteristic_date = field("characteristicsAsOfDate")
    for metric_id, provider_id, unit, scale in (
        ("portfolio_price_to_earnings", "priceEarningsRatio", "multiple", 1.0),
        ("portfolio_price_to_book", "priceBookRatio", "multiple", 1.0),
        ("portfolio_holdings_count", "numberOfHoldings", "count", 1.0),
        ("portfolio_turnover", "portfolioTurnover", "decimal", 0.01),
    ):
        add(metric_id, field(provider_id), unit, scale, characteristic_date, provider_id)
    add(
        "expense_ratio", assigned("netExpenseRatio") or assigned("grossExpenseRatio"),
        "decimal", 0.01, assigned("expenseRatioAsOfDate"), "expenseRatio",
    )
    top_holdings = re.search(r"topHoldings:\[(.*?)\],", decoded, flags=re.DOTALL)
    weights = (
        [_numeric(value, "Avantis holding weight") * 0.01 for value in re.findall(r'weight:\"([0-9.,]+)%\"', top_holdings.group(1))]
        if top_holdings else []
    )
    if weights:
        add("portfolio_top10_concentration", sum(weights[:10]), "decimal", 1.0, assigned("portfolioAsOfDate"), "top10_concentration")
        add("portfolio_max_holding_weight", max(weights), "decimal", 1.0, assigned("portfolioAsOfDate"), "max_holding_weight")
    required = {"portfolio_price_to_earnings", "portfolio_price_to_book", "expense_ratio"}
    if not required.issubset({row.metric_id for row in observations}):
        raise ValueError("Avantis page omitted a required valuation characteristic")
    relative, digest = _cache_raw(
        workspace, str(source["id"]), "avantis-fundamentals", content, ".html"
    )
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="avantis_fundamentals", canonical_url=url,
        retrieved_at=retrieved_at, content_sha256=digest, raw_path=relative,
        media_type=headers.get("content-type", "text/html").split(";")[0],
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note=(
            "Issuer-hydrated public fund object with characteristics and fees; economic dates "
            "are retained and historical use starts at retrieval."
        ),
    )
    return receipt, tuple(observations)


def _first_trust_fundamentals_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Read First Trust's public fund summary table by labeled cells."""
    symbol = require_text(
        source.get("symbol") or source.get("entity_id"), "First Trust source symbol"
    ).upper()
    entity_id = require_text(source.get("entity_id", symbol), "First Trust entity_id")
    url = str(
        source.get("url")
        or f"https://www.ftportfolios.com/retail/etf/ETFsummary.aspx?Ticker={symbol}"
    )
    content, headers = _fetch(
        url,
        user_agent=str(source.get("user_agent") or "Mozilla/5.0 JaggedThoughts-Capital/1.0"),
        timeout=float(source.get("timeout_seconds", 30)),
    )
    decoded = content.decode("utf-8", errors="replace")
    title = re.search(r"<title[^>]*>(.*?)</title>", decoded, flags=re.DOTALL | re.IGNORECASE)
    if not title or not re.search(rf"\b{re.escape(symbol)}\b", unescape(title.group(1)), re.IGNORECASE):
        raise ValueError(f"First Trust page did not confirm ticker {symbol}")

    def cell(label: str) -> str | None:
        match = re.search(
            rf">\s*{re.escape(label)}(?:\*)?(?:<[^>]+>.*?</[^>]+>)?\s*</td>\s*<td[^>]*>\s*([^<]+?)\s*</td>",
            decoded,
            flags=re.IGNORECASE,
        )
        return unescape(match.group(1)).strip() if match else None

    characteristic_date_match = re.search(
        r"Fund Characteristics\s*\(as of\s*([^)]+)\)", decoded, flags=re.IGNORECASE,
    )
    characteristic_date = characteristic_date_match.group(1).strip() if characteristic_date_match else None
    expense_date_match = re.search(
        r"divExpenseRatioDate[^>]*>\s*\*?\s*As of\s+([^<]+)", decoded, flags=re.IGNORECASE,
    )
    expense_date = expense_date_match.group(1).strip() if expense_date_match else None
    observations: list[MetricObservation] = []

    def add(metric_id: str, raw_value: Any, unit: str, scale: float, raw_date: Any, provider_id: str) -> None:
        if raw_value in (None, ""):
            return
        value = _numeric(raw_value, f"First Trust {provider_id}") * scale
        observed_at = (
            _timestamp(_provider_date(raw_date), f"First Trust {provider_id} date", end_of_day=True)
            if raw_date not in (None, "") else retrieved_at
        )
        identity = stable_sha256({
            "source": source["id"], "provider_id": provider_id,
            "observed_at": observed_at, "value": value,
        })[:20]
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:{metric_id}:{identity}", entity_id=entity_id,
            metric_id=metric_id, value=value, unit=unit, observed_at=observed_at,
            available_at=retrieved_at, source_ref=str(source["id"]),
        ))

    add("portfolio_price_to_earnings", cell("Price/Earnings"), "multiple", 1.0, characteristic_date, "Price/Earnings")
    add("portfolio_price_to_book", cell("Price/Book"), "multiple", 1.0, characteristic_date, "Price/Book")
    add("portfolio_holdings_count", cell("Number of Holdings (excluding cash)"), "count", 1.0, None, "holdings_count")
    add("expense_ratio", cell("Total Expense Ratio"), "decimal", 0.01, expense_date, "Total Expense Ratio")
    add("fund_net_assets", cell("Total Net Assets"), "USD", 1.0, None, "Total Net Assets")
    add("median_bid_ask_spread", cell("30-Day Median Bid/Ask Spread"), "decimal", 0.01, None, "Median Bid/Ask Spread")
    add("average_daily_volume_30d", cell("Average 30-Day Daily Volume"), "shares/day", 1.0, None, "Average 30-Day Daily Volume")
    required = {"portfolio_price_to_earnings", "portfolio_price_to_book", "expense_ratio"}
    if not required.issubset({row.metric_id for row in observations}):
        raise ValueError("First Trust page omitted a required valuation characteristic")
    relative, digest = _cache_raw(
        workspace, str(source["id"]), "first-trust-fundamentals", content, ".html"
    )
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="first_trust_fundamentals",
        canonical_url=url, retrieved_at=retrieved_at, content_sha256=digest,
        raw_path=relative,
        media_type=headers.get("content-type", "text/html").split(";")[0],
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note=(
            "Issuer-published labeled summary tables with portfolio characteristics and fees; "
            "economic dates are retained and historical use starts at retrieval."
        ),
    )
    return receipt, tuple(observations)


def _first_trust_holdings_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Normalize First Trust's complete public holdings table and concentration."""
    symbol = require_text(
        source.get("symbol") or source.get("entity_id"), "First Trust holdings symbol"
    ).upper()
    entity_id = require_text(source.get("entity_id", symbol), "First Trust holdings entity_id")
    url = str(
        source.get("url")
        or f"https://www.ftportfolios.com/Retail/Etf/EtfHoldings.aspx?Ticker={symbol}"
    )
    content, headers = _fetch(
        url,
        user_agent=str(source.get("user_agent") or "Mozilla/5.0 JaggedThoughts-Capital/1.0"),
        timeout=float(source.get("timeout_seconds", 30)),
    )
    decoded = content.decode("utf-8", errors="replace")
    heading = re.search(r'class="CEFPageTitle"[^>]*>(.*?)</span>', decoded, flags=re.DOTALL | re.IGNORECASE)
    if not heading or not re.search(rf"\b{re.escape(symbol)}\b", unescape(heading.group(1)), re.IGNORECASE):
        raise ValueError(f"First Trust holdings page did not confirm ticker {symbol}")
    date_match = re.search(r"Holdings of the Fund as of\s*([^<]+)", decoded, flags=re.IGNORECASE)
    if not date_match:
        raise ValueError("First Trust holdings page omitted its holdings date")
    observed_at = _timestamp(
        _provider_date(unescape(date_match.group(1)).strip()),
        "First Trust holdings date", end_of_day=True,
    )

    def text(value: str) -> str:
        return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())

    holdings: list[dict[str, Any]] = []
    for table_row in re.findall(r"<tr(?:\s[^>]*)?>(.*?)</tr>", decoded, flags=re.DOTALL | re.IGNORECASE):
        cells = [text(value) for value in re.findall(
            r"<td(?:\s[^>]*)?>(.*?)</td>", table_row, flags=re.DOTALL | re.IGNORECASE,
        )]
        if len(cells) != 7 or not re.fullmatch(r"[0-9.,]+%", cells[-1]):
            continue
        if cells[1].startswith("$"):
            continue
        holdings.append({
            "security_name": cells[0], "identifier": cells[1], "cusip": cells[2],
            "classification": cells[3],
            "shares": _numeric(cells[4], "First Trust holding shares"),
            "market_value": _numeric(cells[5].removeprefix("$"), "First Trust holding market value"),
            "weight": _numeric(cells[6], "First Trust holding weight") * 0.01,
        })
    count_match = re.search(r"Total Number of Holdings \(excluding cash\):\s*([0-9,]+)", decoded)
    reported_count = int(_numeric(count_match.group(1), "First Trust holdings count")) if count_match else 0
    if not holdings or reported_count != len(holdings):
        raise ValueError(
            f"First Trust holdings coverage mismatch: parsed {len(holdings)} of {reported_count}"
        )
    relative, digest = _cache_raw(
        workspace, str(source["id"]), "first-trust-holdings", content, ".html"
    )
    observations = _materialize_fund_holdings(
        workspace, source=source, entity_id=entity_id, observed_at=observed_at,
        retrieved_at=retrieved_at, source_url=url, source_digest=digest,
        raw_path=relative, holdings=holdings, reported_count=reported_count,
    )
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="first_trust_holdings",
        canonical_url=url, retrieved_at=retrieved_at, content_sha256=digest,
        raw_path=relative, media_type=headers.get("content-type", "text/html").split(";")[0],
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note=(
            "Issuer-published complete holdings table with identifiers, classifications, weights, "
            "and an economic as-of date; historical use starts at retrieval."
        ),
    )
    return receipt, observations


def _parse_yahoo_chart_observations(
    content: bytes, source: Mapping[str, Any], retrieved_at: str,
) -> tuple[MetricObservation, ...]:
    """Normalize close identities from one already time-bound Yahoo response."""
    symbol = require_text(source.get("symbol"), "Yahoo chart symbol")
    payload = json.loads(content.decode("utf-8"))
    chart = payload.get("chart") if isinstance(payload, Mapping) else None
    if not isinstance(chart, Mapping) or chart.get("error"):
        raise ValueError(str((chart or {}).get("error") or "Yahoo chart response is invalid"))
    results = chart.get("result")
    if not isinstance(results, list) or not results or not isinstance(results[0], Mapping):
        raise ValueError("Yahoo chart response has no result")
    result = results[0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quotes = indicators.get("quote") if isinstance(indicators, Mapping) else []
    adjusted = indicators.get("adjclose") if isinstance(indicators, Mapping) else []
    quote = quotes[0] if isinstance(quotes, list) and quotes and isinstance(quotes[0], Mapping) else {}
    adjusted_row = adjusted[0] if isinstance(adjusted, list) and adjusted and isinstance(adjusted[0], Mapping) else {}
    price_kind = str(source.get("price_kind") or "close")
    values = adjusted_row.get("adjclose") if price_kind == "adjusted_close" else quote.get("close")
    if not isinstance(timestamps, list) or not isinstance(values, list):
        raise ValueError(f"Yahoo chart response has no {price_kind} series")
    entity_id = require_text(source.get("entity_id"), "Yahoo chart entity_id")
    metric_id = require_text(source.get("metric_id", "price"), "Yahoo chart metric_id")
    meta = result.get("meta") if isinstance(result.get("meta"), Mapping) else {}
    response_symbol = str(meta.get("symbol") or "").strip()
    if response_symbol and response_symbol.upper() != symbol.upper():
        raise ValueError(
            f"Yahoo chart response symbol {response_symbol} does not match {symbol}"
        )
    expected_interval = str(source.get("interval") or "").strip()
    response_interval = str(meta.get("dataGranularity") or "").strip()
    if expected_interval and response_interval and response_interval != expected_interval:
        raise ValueError(
            "Yahoo chart response granularity "
            f"{response_interval} does not match requested {expected_interval}"
        )
    unit = require_text(source.get("unit") or meta.get("currency") or "USD", "Yahoo chart unit")
    observations: list[MetricObservation] = []
    series = [(metric_id, price_kind, values)]
    adjusted_values = adjusted_row.get("adjclose")
    if (
        price_kind != "adjusted_close"
        and source.get("emit_adjusted_price", True) is not False
        and isinstance(adjusted_values, list)
    ):
        series.append(("adjusted_price", "adjusted_close", adjusted_values))
    for series_metric, series_kind, series_values in series:
        for epoch, value in zip(timestamps, series_values):
            if value is None:
                continue
            try:
                observed_at = datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                numeric = float(value)
            except (TypeError, ValueError, OSError):
                continue
            if not math.isfinite(numeric) or numeric <= 0:
                continue
            identity = _yahoo_price_observation_id(
                source=source, metric_id=series_metric, epoch=epoch,
                value=numeric, kind=series_kind,
            )
            observations.append(MetricObservation(
                observation_id=identity, entity_id=entity_id,
                metric_id=series_metric, value=numeric, unit=unit, observed_at=observed_at,
                available_at=retrieved_at, source_ref=str(source["id"]),
            ))
    events = result.get("events") if isinstance(result.get("events"), Mapping) else {}
    splits = events.get("splits") if isinstance(events, Mapping) else {}
    if isinstance(splits, Mapping):
        for event in splits.values():
            if not isinstance(event, Mapping):
                continue
            try:
                epoch = float(event["date"])
                numerator = float(event["numerator"])
                denominator = float(event["denominator"])
                if numerator <= 0 or denominator <= 0:
                    continue
                ratio = numerator / denominator
                observed_at = datetime.fromtimestamp(
                    epoch, tz=timezone.utc,
                ).isoformat(timespec="seconds").replace("+00:00", "Z")
            except (KeyError, TypeError, ValueError, OSError):
                continue
            identity = stable_sha256({
                "source": source["id"], "symbol": symbol, "timestamp": epoch,
                "numerator": numerator, "denominator": denominator,
            })[:20]
            observations.append(MetricObservation(
                observation_id=f"{source['id']}:stock_split_ratio:{identity}",
                entity_id=entity_id, metric_id="stock_split_ratio", value=ratio,
                unit="new_shares/old_share", observed_at=observed_at,
                available_at=retrieved_at, source_ref=str(source["id"]),
            ))
    return tuple(observations)


def _yahoo_price_observation_id(
    *, source: Mapping[str, Any], metric_id: str, epoch: int | float,
    value: float, kind: str,
) -> str:
    """Return the retrieval-invariant identity used by Yahoo price rows."""
    timestamp = float(epoch)
    normalized_epoch: int | float = int(timestamp) if timestamp.is_integer() else timestamp
    digest = stable_sha256({
        "source": source["id"],
        "symbol": require_text(source.get("symbol"), "Yahoo chart symbol"),
        "timestamp": normalized_epoch, "value": float(value), "kind": kind,
    })[:20]
    return f"{source['id']}:{metric_id}:{digest}"


def _yahoo_chart_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Consume Yahoo Finance's public chart response as retrieval-time data.

    The endpoint does not publish historical information-vintage metadata, so
    every row is conservatively unavailable before this retrieval receipt.
    This adapter is a replaceable convenience source, not a backtest archive.
    """
    symbol = require_text(source.get("symbol"), "Yahoo chart symbol")
    interval = str(source.get("interval") or "1d")
    range_value = str(source.get("range") or "5y")
    query: dict[str, Any] = {
        "interval": interval,
        "events": "div,splits",
    }
    if interval == "1d" and range_value == "max":
        query.update({
            "period1": 0,
            "period2": int(datetime.fromisoformat(
                retrieved_at.replace("Z", "+00:00")
            ).timestamp()),
        })
    else:
        query["range"] = range_value
    params = urlencode(query)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{params}"
    content, headers = _fetch(url, user_agent=str(source.get("user_agent") or "Mozilla/5.0 JaggedThoughts-Capital/1.0"))
    relative, digest = _cache_raw(workspace, str(source["id"]), "yahoo-chart", content, ".json")
    observations = _parse_yahoo_chart_observations(content, source, retrieved_at)
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="yahoo_chart_daily", canonical_url=url,
        retrieved_at=retrieved_at, content_sha256=digest, raw_path=relative,
        media_type=headers.get("content-type", "application/json").split(";")[0],
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note=(
            "Public Yahoo Finance chart response with no historical information-vintage metadata; "
            f"the response symbol and {interval} granularity matched the request; close and "
            "adjusted-close identities remain separate; rows are admissible only from this "
            "retrieval receipt and the adapter is replaceable."
        ),
    )
    return receipt, tuple(observations)


def _csv_timestamp(
    row: Mapping[str, str], config: Mapping[str, Any], retrieved_at: str, *, observed: bool
) -> str:
    column_key = "observed_at_column" if observed else "available_at_column"
    column = str(config.get(column_key) or "")
    if column:
        return _timestamp(row.get(column), f"CSV {column}", end_of_day=True)
    if observed:
        raise ValueError("CSV mapping requires observed_at_column")
    lag_days = config.get("availability_lag_days")
    if lag_days is None:
        return retrieved_at
    observed_at = _csv_timestamp(row, config, retrieved_at, observed=True)
    parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00")) + timedelta(days=float(lag_days))
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_mapped_csv(
    content: bytes, source: Mapping[str, Any], retrieved_at: str
) -> tuple[MetricObservation, ...]:
    text = content.decode(str(source.get("encoding") or "utf-8-sig"))
    mappings = source.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("CSV source mappings must be a nonempty list")
    delimiter = str(source.get("delimiter") or ",")
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
    observations: list[MetricObservation] = []
    for config in mappings:
        if not isinstance(config, Mapping):
            raise ValueError("CSV source mapping must be an object")
        value_column = require_text(config.get("value_column"), "CSV value_column")
        entity_id = require_text(config.get("entity_id"), "CSV entity_id")
        metric_id = require_text(config.get("metric_id"), "CSV metric_id")
        unit = require_text(config.get("unit"), "CSV unit")
        scale = float(config.get("scale", 1.0))
        filters = config.get("filter") or {}
        if not isinstance(filters, Mapping):
            raise ValueError("CSV filter must be a mapping")
        for row in rows:
            if any(str(row.get(str(key), "")) != str(value) for key, value in filters.items()):
                continue
            raw_value = str(row.get(value_column) or "").strip().replace(",", "")
            if not raw_value or raw_value in {".", "NA", "N/A", "null"}:
                continue
            observed_at = _csv_timestamp(row, config, retrieved_at, observed=True)
            available_at = _csv_timestamp(row, config, retrieved_at, observed=False)
            identity = stable_sha256({
                "source": source["id"], "mapping": dict(config), "row": row,
                "retrieved_at": (
                    retrieved_at
                    if source.get("bind_retrieval_epoch")
                    and not config.get("available_at_column")
                    and config.get("availability_lag_days") is None
                    else None
                ),
            })[:20]
            observations.append(MetricObservation(
                observation_id=f"{source['id']}:{metric_id}:{identity}", entity_id=entity_id,
                metric_id=metric_id, value=float(raw_value) * scale, unit=unit,
                observed_at=observed_at, available_at=available_at, source_ref=str(source["id"]),
            ))
    if source.get("latest_only"):
        latest: dict[tuple[str, str], MetricObservation] = {}
        for row in observations:
            key = (row.entity_id, row.metric_id)
            current = latest.get(key)
            if current is None or (row.observed_at, row.observation_id) > (
                current.observed_at, current.observation_id
            ):
                latest[key] = row
        observations = list(latest.values())
    return tuple(observations)


def _http_csv_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    url = require_text(source.get("url"), "CSV source url")
    transport = str(source.get("transport") or "urllib")
    if transport not in {"urllib", "curl"}:
        raise ValueError("CSV source transport must be urllib or curl")
    fetch = _fetch_curl if transport == "curl" else _fetch
    content, headers = fetch(
        url,
        user_agent=str(source.get("user_agent") or "JaggedThoughts-Capital/1.0"),
        timeout=float(source.get("timeout_seconds", 30)),
    )
    relative, digest = _cache_raw(workspace, str(source["id"]), "http-csv", content, ".csv")
    observations = _parse_mapped_csv(content, source, retrieved_at)
    mappings = source.get("mappings") or []
    mode = "declared_column" if all(isinstance(row, Mapping) and row.get("available_at_column") for row in mappings) else (
        "declared_lag" if all(isinstance(row, Mapping) and row.get("availability_lag_days") is not None for row in mappings)
        else "retrieval_only"
    )
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="http_csv", canonical_url=_redacted_url(url),
        retrieved_at=retrieved_at, content_sha256=digest, raw_path=relative,
        media_type=headers.get("content-type", "text/csv").split(";")[0],
        availability_mode=mode, observation_count=len(observations),
        provider_note=str(source.get("provider_note") or "Public HTTPS CSV normalized by declared column mappings."),
    )
    return receipt, observations


def _http_regex_metrics_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Extract a few current public metrics from source-authored HTML."""

    mappings = source.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("HTML regex source mappings must be a nonempty list")
    observations: list[MetricObservation] = []
    cached: list[bytes] = []
    media_types: list[str] = []
    for mapping in mappings:
        if not isinstance(mapping, Mapping):
            raise ValueError("HTML regex source mapping must be an object")
        url = require_text(mapping.get("url"), "HTML regex source url")
        content, headers = _fetch(
            url,
            user_agent=str(source.get("user_agent") or "JaggedThoughts Capital public research"),
            timeout=float(source.get("timeout_seconds", 30)),
        )
        cached.extend((f"\nURL: {url}\n".encode(), content))
        media_types.append(str(headers.get("content-type") or "text/html").split(";", 1)[0])
        plain = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", content.decode("utf-8", errors="replace"))))
        match = re.search(require_text(mapping.get("pattern"), "HTML metric regex"), plain, re.I)
        if not match:
            raise ValueError(f"public HTML metric pattern did not match {url}")
        value = float(match.group(1).replace(",", ""))
        transform = str(mapping.get("transform") or "scale")
        if transform == "reciprocal":
            value = 1.0 / value
        elif transform == "scale":
            value *= float(mapping.get("scale", 1.0))
        else:
            raise ValueError(f"unsupported HTML metric transform: {transform}")
        metric_id = require_text(mapping.get("metric_id"), "HTML metric id")
        entity_id = require_text(mapping.get("entity_id"), "HTML metric entity")
        observed_at = canonical_timestamp(
            mapping.get("observed_at") or retrieved_at, "HTML metric observed_at"
        )
        observations.append(MetricObservation(
            observation_id=f"{source['id']}:{metric_id}:{stable_sha256({'value': value, 'observed_at': observed_at, 'retrieved_at': retrieved_at})[:20]}",
            entity_id=entity_id, metric_id=metric_id, value=value,
            unit=require_text(mapping.get("unit"), "HTML metric unit"),
            observed_at=observed_at, available_at=retrieved_at, source_ref=str(source["id"]),
        ))
    combined = b"".join(cached)
    relative, digest = _cache_raw(workspace, str(source["id"]), "http-regex-metrics", combined, ".html")
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="http_regex_metrics",
        canonical_url=str(source.get("canonical_url") or mappings[0]["url"]),
        retrieved_at=retrieved_at, content_sha256=digest, raw_path=relative,
        media_type=media_types[0] if len(set(media_types)) == 1 else "multipart/mixed",
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note=str(source.get("provider_note") or "Public HTML values frozen at retrieval."),
    )
    return receipt, tuple(observations)


def _damodaran_current_erp_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    """Read the current US implied ERP and Treasury rate from the public NYU page.

    The page is a useful valuation input, not a point-in-time archive.  Both
    rows therefore inherit the retrieval timestamp as their availability time;
    the displayed update date is retained as the economic observation time.
    """
    url = str(source.get("url") or "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm")
    content, headers = _fetch(
        url,
        user_agent=str(source.get("user_agent") or "JaggedThoughts Capital public research"),
        timeout=float(source.get("timeout_seconds", 30)),
    )
    decoded = content.decode("utf-8", errors="replace")
    plain = unescape(re.sub(r"<[^>]+>", "", decoded))
    plain = re.sub(r"\s+", " ", plain)
    match = re.search(
        r"Implied ERP on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*=\s*"
        r"([0-9]+(?:\s*\.\s*[0-9]+)?)%.*?"
        r"US treasury rate of\s*([0-9]+(?:\s*\.\s*[0-9]+)?)%",
        plain,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError("NYU current ERP page did not contain the expected dated ERP and Treasury fields")
    observed_date = datetime.strptime(match.group(1), "%B %d, %Y").date().isoformat()
    erp = float(re.sub(r"\s+", "", match.group(2))) / 100.0
    treasury = float(re.sub(r"\s+", "", match.group(3))) / 100.0
    entity_id = str(source.get("entity_id") or "US-MARKET")
    metrics = [
        (str(source.get("erp_metric_id") or "implied_equity_risk_premium"), erp),
        (str(source.get("risk_free_metric_id") or "risk_free_rate"), treasury),
    ]
    variants = {
        "implied_erp_ttm_cash_yield": r"([0-9]+(?:\s*\.\s*[0-9]+)?)%\s*\(Trailing 12 month cash yield\)",
        "implied_erp_10y_average_cash_flow_yield": r"([0-9]+(?:\s*\.\s*[0-9]+)?)%\s*\(Average CF yield last 10 years\)",
        "implied_erp_net_cash_yield": r"([0-9]+(?:\s*\.\s*[0-9]+)?)%\s*\(Net cash yield\)",
        "implied_erp_normalized_earnings_payout": r"([0-9]+(?:\s*\.\s*[0-9]+)?)%\s*\(Normalized Earnings & Payout\)",
    }
    for metric_id, pattern in variants.items():
        variant = re.search(pattern, plain, re.I)
        if variant:
            metrics.append((metric_id, float(re.sub(r"\s+", "", variant.group(1))) / 100.0))
    observations = tuple(MetricObservation(
        observation_id=f"{source['id']}:{metric_id}:{stable_sha256({'observed': observed_date, 'value': value, 'retrieved_at': retrieved_at})[:20]}",
        entity_id=entity_id,
        metric_id=metric_id,
        value=value,
        unit="decimal",
        observed_at=_timestamp(observed_date, "NYU ERP observation date", end_of_day=True),
        available_at=retrieved_at,
        source_ref=str(source["id"]),
    ) for metric_id, value in metrics)
    relative, digest = _cache_raw(workspace, str(source["id"]), "damodaran-current-erp", content, ".html")
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="damodaran_current_erp",
        canonical_url=_redacted_url(url), retrieved_at=retrieved_at,
        content_sha256=digest, raw_path=relative,
        media_type=str(headers.get("content-type") or "text/html").split(";", 1)[0],
        availability_mode="retrieval_only", observation_count=len(observations),
        provider_note=("NYU public current-value page; the first trailing-twelve-month adjusted-payout ERP "
                       "and the displayed US Treasury rate are parsed. Historical use starts at retrieval."),
    )
    return receipt, observations


def _local_csv_adapter(
    workspace: Path, source: Mapping[str, Any], retrieved_at: str
) -> tuple[SourceReceipt, tuple[MetricObservation, ...]]:
    relative_source = Path(require_text(source.get("path"), "local CSV path"))
    source_path = (workspace / relative_source).resolve()
    try:
        source_path.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("local CSV source escapes the investment workspace") from error
    content = source_path.read_bytes()
    relative, digest = _cache_raw(workspace, str(source["id"]), "local-csv", content, ".csv")
    observations = _parse_mapped_csv(content, source, retrieved_at)
    mappings = source.get("mappings") or []
    mode = "declared_column" if all(isinstance(row, Mapping) and row.get("available_at_column") for row in mappings) else "retrieval_only"
    receipt = SourceReceipt(
        source_id=str(source["id"]), adapter="local_csv", canonical_url=f"workspace:{relative_source.as_posix()}",
        retrieved_at=retrieved_at, content_sha256=digest, raw_path=relative,
        media_type="text/csv", availability_mode=mode, observation_count=len(observations),
        provider_note=str(source.get("provider_note") or "Operator-supplied CSV; public origin remains declared in the manifest."),
    )
    return receipt, observations


def _write_observations(path: Path, observations: Iterable[MetricObservation]) -> None:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=OBSERVATION_COLUMNS)
    writer.writeheader()
    for row in sorted(observations, key=lambda value: (value.entity_id, value.metric_id, value.available_at, value.observation_id)):
        writer.writerow(row.to_dict())
    _atomic_write(path, output.getvalue().encode("utf-8"))


def _read_observations(path: Path) -> Iterable[MetricObservation]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            yield MetricObservation(
                observation_id=str(raw["observation_id"]), entity_id=str(raw["entity_id"]),
                metric_id=str(raw["metric_id"]), value=float(raw["value"]), unit=str(raw["unit"]),
                observed_at=str(raw["observed_at"]), available_at=str(raw["available_at"]),
                source_ref=str(raw["source_ref"]),
            )


def _merge_observations(*groups: Iterable[MetricObservation]) -> tuple[MetricObservation, ...]:
    merged: dict[str, MetricObservation] = {}
    for group in groups:
        for row in group:
            current = merged.get(row.observation_id)
            if current is None:
                merged[row.observation_id] = row
                continue
            if (
                current.entity_id,
                current.metric_id,
                current.value,
                current.unit,
                current.observed_at,
                current.source_ref,
            ) != (
                row.entity_id,
                row.metric_id,
                row.value,
                row.unit,
                row.observed_at,
                row.source_ref,
            ):
                raise ValueError(f"observation identity changed content: {row.observation_id}")
            # Retrieval-only adapters repeatedly expose unchanged history. Keep
            # the earliest witnessed availability; a changed value has a new ID.
            if row.available_at < current.available_at:
                merged[row.observation_id] = row
    return tuple(merged[key] for key in sorted(merged))


def compact_legacy_yahoo_price_identities(
    observations: Iterable[MetricObservation], manifest: Mapping[str, Any],
) -> tuple[tuple[MetricObservation, ...], dict[str, Any]]:
    """Collapse retrieval-bound legacy Yahoo IDs onto the stable price identity."""
    yahoo_sources = {
        str(row.get("id")): dict(row)
        for row in manifest.get("sources", ())
        if isinstance(row, Mapping) and row.get("adapter") == "yahoo_chart_daily"
    }
    compacted: dict[str, MetricObservation] = {}
    before_digest = hashlib.sha256()
    before_count = 0
    target_metrics = {"price", "adjusted_price"}

    def content(row: MetricObservation) -> tuple[Any, ...]:
        return (
            row.source_ref, row.entity_id, row.metric_id, float(row.value),
            row.unit, row.observed_at,
        )

    def digest_row(digest: Any, row: MetricObservation) -> None:
        digest.update(json.dumps(
            row.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8"))
        digest.update(b"\n")

    for row in observations:
        source = yahoo_sources.get(row.source_ref)
        target = source is not None and row.metric_id in target_metrics
        if target:
            before_count += 1
            digest_row(before_digest, row)
            epoch = datetime.fromisoformat(row.observed_at.replace("Z", "+00:00")).timestamp()
            kind = (
                "adjusted_close" if row.metric_id == "adjusted_price"
                else str(source.get("price_kind") or "close")
            )
            observation_id = _yahoo_price_observation_id(
                source=source, metric_id=row.metric_id, epoch=epoch,
                value=row.value, kind=kind,
            )
            row = MetricObservation(
                observation_id=observation_id, entity_id=row.entity_id,
                metric_id=row.metric_id, value=row.value, unit=row.unit,
                observed_at=row.observed_at, available_at=row.available_at,
                source_ref=row.source_ref,
            )
        current = compacted.get(row.observation_id)
        if current is not None and content(current) != content(row):
            raise ValueError(
                f"Yahoo canonical observation identity changed content: {row.observation_id}"
            )
        if current is None or row.available_at < current.available_at:
            compacted[row.observation_id] = row

    rows = tuple(compacted[key] for key in sorted(compacted))
    after_digest = hashlib.sha256()
    after_count = 0
    for row in rows:
        if row.source_ref in yahoo_sources and row.metric_id in target_metrics:
            after_count += 1
            digest_row(after_digest, row)
    body = {
        "schema": "jaggedthoughts-yahoo-legacy-identity-compaction-v1",
        "adapter": "yahoo_chart_daily",
        "metric_ids": sorted(target_metrics),
        "source_ids": sorted(yahoo_sources),
        "before_count": before_count,
        "after_count": after_count,
        "collapsed_count": before_count - after_count,
        "before_sha256": before_digest.hexdigest(),
        "after_sha256": after_digest.hexdigest(),
        "status": "compacted" if before_count != after_count else "up_to_date",
        "capital_authority": False,
    }
    return rows, {**body, "receipt_sha256": stable_sha256(body)}


def compact_yahoo_granularity_drift(
    observations: Iterable[MetricObservation], manifest: Mapping[str, Any], *,
    workspace: str | Path, source_ids: Iterable[str],
) -> tuple[tuple[MetricObservation, ...], dict[str, Any]]:
    """Drop price rows emitted by cached Yahoo responses at an undeclared grain."""

    root = Path(workspace).expanduser().resolve()
    selected = set(source_ids)
    sources = {
        str(row.get("id") or ""): dict(row)
        for row in manifest.get("sources", ())
        if isinstance(row, Mapping)
        and row.get("adapter") == "yahoo_chart_daily"
        and str(row.get("id") or "") in selected
    }
    invalid_ids: set[str] = set()
    invalid_payloads: list[dict[str, Any]] = []
    for source_id in sorted(sources):
        source = sources[source_id]
        expected = str(source.get("interval") or "1d")
        raw_dir = root / "sources" / "raw" / source_id
        for path in sorted(raw_dir.glob("yahoo-chart-*.json")):
            try:
                content = path.read_bytes()
                payload = json.loads(content.decode("utf-8"))
                result = payload["chart"]["result"][0]
                actual = str((result.get("meta") or {}).get("dataGranularity") or "")
            except (OSError, KeyError, IndexError, TypeError, json.JSONDecodeError):
                continue
            if not actual or actual == expected:
                continue
            parse_source = {**source, "interval": actual}
            parsed = _parse_yahoo_chart_observations(
                content, parse_source, "1970-01-01T00:00:00Z",
            )
            invalid_ids.update(
                row.observation_id for row in parsed
                if row.metric_id in {"price", "adjusted_price"}
            )
            invalid_payloads.append({
                "source_id": source_id,
                "content_sha256": hashlib.sha256(content).hexdigest(),
                "declared_interval": expected,
                "response_interval": actual,
            })
    values = tuple(observations)
    rows = tuple(
        row for row in values
        if row.observation_id not in invalid_ids
    )
    removed_count = len(values) - len(rows)
    body = {
        "schema": "jaggedthoughts-yahoo-granularity-compaction-v1",
        "source_ids": sorted(sources),
        "invalid_payloads": invalid_payloads,
        "removed_observation_count": removed_count,
        "status": "compacted" if removed_count else "up_to_date",
        "capital_authority": False,
    }
    return rows, {**body, "receipt_sha256": stable_sha256(body)}


def compile_latest_observation_projection(
    observations: Iterable[MetricObservation], *, as_of: str,
) -> dict[str, Any]:
    """Compile the disposable current-value index while source rows are in memory."""
    epoch = canonical_timestamp(as_of, "latest-observation projection as_of")
    latest: dict[tuple[str, str], MetricObservation] = {}
    count = 0
    for row in observations:
        count += 1
        if row.available_at > epoch:
            continue
        key = (row.entity_id, row.metric_id)
        current = latest.get(key)
        if current is None or (row.available_at, row.observed_at, row.observation_id) > (
            current.available_at, current.observed_at, current.observation_id
        ):
            latest[key] = row
    return {
        "schema": "jaggedthoughts-latest-observation-projection-v1",
        "as_of": epoch, "observation_count": count, "latest_count": len(latest),
        "observations": [latest[key].to_dict() for key in sorted(latest)],
    }


def project_cached_yahoo_adjusted_prices(
    manifest_path: str | Path, *, workspace: str | Path,
) -> dict[str, Any]:
    """Add adjusted-price rows derivable from current content-addressed cache heads."""

    root = Path(workspace).expanduser().resolve()
    manifest = load_source_manifest(manifest_path)
    sources = {
        str(row.get("id") or ""): dict(row)
        for row in manifest.get("sources") or ()
        if isinstance(row, Mapping) and row.get("adapter") == "yahoo_chart_daily"
    }
    data_dir = root / "data"
    observations_path = data_dir / "observations.csv"
    heads_path = data_dir / "source_receipt_heads.json"
    lock_dir = root / "state"
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / "source_refresh.lock").open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        heads = _source_receipt_heads(heads_path)
        existing_ids: set[str] = set()
        existing_count = 0
        if observations_path.is_file():
            with observations_path.open("r", encoding="utf-8", newline="") as source_file:
                for row in csv.DictReader(source_file):
                    existing_count += 1
                    existing_ids.add(str(row.get("observation_id") or ""))
        additions: dict[str, MetricObservation] = {}
        projected_sources: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        for source_id in sorted(sources):
            source = sources[source_id]
            receipt = heads.get(source_id)
            if receipt is None:
                skipped.append({"source_id": source_id, "reason": "receipt_head_unavailable"})
                continue
            receipt_body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
            if (
                receipt.get("adapter") != "yahoo_chart_daily"
                or receipt.get("receipt_sha256") != stable_sha256(receipt_body)
            ):
                skipped.append({"source_id": source_id, "reason": "receipt_head_invalid"})
                continue
            raw_path = (root / str(receipt.get("raw_path") or "")).resolve()
            try:
                raw_path.relative_to(root)
                content = raw_path.read_bytes()
            except (OSError, ValueError):
                skipped.append({"source_id": source_id, "reason": "cached_bytes_unavailable"})
                continue
            if hashlib.sha256(content).hexdigest() != receipt.get("content_sha256"):
                skipped.append({"source_id": source_id, "reason": "cached_bytes_hash_mismatch"})
                continue
            try:
                rows = _parse_yahoo_chart_observations(
                    content, source, str(receipt["retrieved_at"]),
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                skipped.append({
                    "source_id": source_id,
                    "reason": f"projection_failed:{type(error).__name__}:{str(error)[:200]}",
                })
                continue
            projected = [
                row for row in rows
                if row.metric_id in {"adjusted_price", "stock_split_ratio"}
            ]
            for row in projected:
                if row.observation_id not in existing_ids:
                    additions[row.observation_id] = row
            projected_sources.append({
                "source_id": source_id,
                "source_receipt_sha256": receipt["receipt_sha256"],
                "adjusted_observation_count": sum(
                    row.metric_id == "adjusted_price" for row in projected
                ),
                "stock_split_observation_count": sum(
                    row.metric_id == "stock_split_ratio" for row in projected
                ),
            })
        new_rows = [additions[key] for key in sorted(additions)]
        observation_index = None
        if new_rows:
            try:
                index_as_of = json.loads(
                    (data_dir / "latest_observations.json").read_text(encoding="utf-8")
                ).get("as_of") or _utc_now()
            except (OSError, json.JSONDecodeError, AttributeError):
                index_as_of = _utc_now()
            temporary = observations_path.with_name(f".{observations_path.name}.cached-yahoo.tmp")
            if observations_path.is_file():
                shutil.copyfile(observations_path, temporary)
            else:
                _atomic_write(temporary, b"")
            try:
                with temporary.open("a", encoding="utf-8", newline="") as output:
                    writer = csv.DictWriter(output, fieldnames=OBSERVATION_COLUMNS)
                    if existing_count == 0:
                        writer.writeheader()
                    for row in new_rows:
                        writer.writerow(row.to_dict())
                observation_index = build_observation_index(temporary, as_of=index_as_of)
                temporary.replace(observations_path)
            finally:
                if temporary.exists():
                    temporary.unlink()

        latest_path = data_dir / "latest_observations.json"
        try:
            latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            latest_payload = {}
        as_of = canonical_timestamp(
            latest_payload.get("as_of") or _utc_now(),
            "cached Yahoo projection as_of",
        )
        latest: dict[tuple[str, str], dict[str, Any]] = {
            (str(row.get("entity_id") or ""), str(row.get("metric_id") or "")): dict(row)
            for row in latest_payload.get("observations") or ()
            if isinstance(row, Mapping)
        }
        for row in new_rows:
            if row.available_at > as_of:
                continue
            key = (row.entity_id, row.metric_id)
            current = latest.get(key)
            if current is None or (row.available_at, row.observed_at, row.observation_id) > (
                str(current.get("available_at") or ""),
                str(current.get("observed_at") or ""),
                str(current.get("observation_id") or ""),
            ):
                latest[key] = row.to_dict()
        _atomic_json(latest_path, {
            "schema": "jaggedthoughts-latest-observation-projection-v1",
            "as_of": as_of,
            "observation_count": existing_count + len(new_rows),
            "latest_count": len(latest),
            "observations": [latest[key] for key in sorted(latest)],
        })
        body = {
            "schema": "jaggedthoughts-cached-yahoo-adjusted-projection-v1",
            "projected_at": _utc_now(),
            "as_of": as_of,
            "provider_call_count": 0,
            "cached_source_count": len(projected_sources),
            "added_observation_count": len(new_rows),
            "status": "projected" if new_rows else "up_to_date",
            "projected_sources": projected_sources,
            "skipped_sources": skipped,
            "observation_index": observation_index,
            "capital_authority": False,
        }
        result = {**body, "projection_sha256": stable_sha256(body)}
        _atomic_json(data_dir / "cached_yahoo_adjusted_projection.json", result)
        source_run_path = data_dir / "latest_source_run.json"
        if source_run_path.is_file():
            epoch = compile_source_epoch(
                root,
                source_run_path=source_run_path,
                projection_path=latest_path,
                observations_path=observations_path,
                receipt_heads_path=heads_path,
                source_manifest_path=Path(manifest_path).expanduser().resolve(),
                derivation=derivation_identity(
                    manifest.get("signals") or (),
                    derive_metrics=False,
                    metric_universe_sha256=metric_universe_surface()[
                        "metric_universe_sha256"
                    ],
                    pipeline_id=CACHED_RECEIPT_PROJECTION,
                ),
            )
            _atomic_json(data_dir / "latest_source_epoch.json", epoch)
        return result


def _compact_latest_only(
    observations: Iterable[MetricObservation], source_ids: set[str],
) -> tuple[MetricObservation, ...]:
    """Keep one latest row per metric and retrieval epoch for current-state sources."""

    compacted: dict[tuple[str, ...], MetricObservation] = {}
    for row in observations:
        key = (
            ("latest", row.source_ref, row.available_at, row.entity_id, row.metric_id)
            if row.source_ref in source_ids else ("identity", row.observation_id)
        )
        current = compacted.get(key)
        if current is None or (row.observed_at, row.observation_id) > (
            current.observed_at, current.observation_id
        ):
            compacted[key] = row
    return tuple(compacted.values())


@lru_cache(maxsize=8)
def _load_source_manifest_cached(
    source_path: str, modified_ns: int, size: int,
) -> Mapping[str, Any]:
    del modified_ns, size
    source = Path(source_path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != PUBLIC_SOURCE_MANIFEST_SCHEMA:
        raise ValueError(f"source manifest schema must be {PUBLIC_SOURCE_MANIFEST_SCHEMA}")
    return payload


def load_source_manifest(path: str | Path) -> Mapping[str, Any]:
    source = Path(path).expanduser().resolve()
    stat = source.stat()
    return _load_source_manifest_cached(
        str(source), stat.st_mtime_ns, stat.st_size,
    )


def source_requirements(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return environment prerequisites without revealing secret values."""
    rows: list[dict[str, Any]] = []
    for source in manifest.get("sources", []):
        if not isinstance(source, Mapping):
            continue
        adapter = str(source.get("adapter") or "")
        env_name = ""
        purpose = ""
        if adapter in {"sec_companyfacts", "sec_submissions"}:
            env_name = str(source.get("user_agent_env") or "ZTARE_SEC_USER_AGENT")
            purpose = "optional override for the built-in SEC application identity"
        elif adapter == "fred_series":
            env_name = str(source.get("api_key_env") or "FRED_API_KEY")
            purpose = "free FRED API key"
        elif adapter in {"alpha_vantage_daily", "alpha_vantage_etf_profile"} and not source.get("demo_api_key"):
            env_name = str(source.get("api_key_env") or "ALPHAVANTAGE_API_KEY")
            purpose = "free Alpha Vantage API key"
        if env_name:
            rows.append({
                "source_id": str(source.get("id") or ""), "environment_variable": env_name,
                "configured": bool(os.environ.get(env_name)) or adapter in {"sec_companyfacts", "sec_submissions"},
                "uses_builtin_default": adapter in {"sec_companyfacts", "sec_submissions"} and not bool(os.environ.get(env_name)),
                "enabled": source.get("enabled", True) is not False,
                "purpose": purpose,
            })
    return rows


def _consume_public_sources_unlocked(
    manifest_path: str | Path,
    *,
    workspace: str | Path,
    strict: bool = False,
    retrieved_at: str | None = None,
    source_ids: Iterable[str] | None = None,
    derive_metrics: bool = True,
    receipt_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Fetch, cache, normalize, derive signals, and materialize one source run."""
    workspace_path = Path(workspace).expanduser().resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    receipt_root = (
        Path(receipt_dir).expanduser().resolve()
        if receipt_dir is not None else workspace_path / "data"
    )
    try:
        receipt_root.relative_to(workspace_path)
    except ValueError as error:
        raise ValueError("source receipt directory must stay inside the investment workspace") from error
    manifest = load_source_manifest(manifest_path)
    retrieval = canonical_timestamp(retrieved_at or _utc_now(), "source retrieved_at")
    declared_as_of = manifest.get("as_of")
    as_of = canonical_timestamp(
        retrieval if str(declared_as_of or "").strip().lower() in {"", "now"} else declared_as_of,
        "source manifest as_of",
    )
    receipts: list[SourceReceipt] = []
    observations: list[MetricObservation] = []
    statuses: list[dict[str, Any]] = []
    seen: set[str] = set()
    selected_ids = (
        {require_text(value, "selected source id") for value in source_ids}
        if source_ids is not None else None
    )
    adapters = {
        "sec_companyfacts": lambda row: _sec_adapter(workspace_path, row, retrieval),
        "sec_submissions": lambda row: _sec_submissions_adapter(workspace_path, row, retrieval),
        "fred_series": lambda row: _fred_adapter(workspace_path, row, retrieval, as_of),
        "alpha_vantage_daily": lambda row: _alpha_vantage_adapter(workspace_path, row, retrieval),
        "alpha_vantage_etf_profile": lambda row: _alpha_vantage_etf_profile_adapter(workspace_path, row, retrieval),
        "yahoo_chart_daily": lambda row: _yahoo_chart_adapter(workspace_path, row, retrieval),
        "ishares_fundamentals": lambda row: _ishares_fundamentals_adapter(workspace_path, row, retrieval),
        "vanguard_fundamentals": lambda row: _vanguard_fundamentals_adapter(workspace_path, row, retrieval),
        "harbor_fundamentals": lambda row: _harbor_fundamentals_adapter(workspace_path, row, retrieval),
        "avantis_fundamentals": lambda row: _avantis_fundamentals_adapter(workspace_path, row, retrieval),
        "first_trust_fundamentals": lambda row: _first_trust_fundamentals_adapter(workspace_path, row, retrieval),
        "first_trust_holdings": lambda row: _first_trust_holdings_adapter(workspace_path, row, retrieval),
        "damodaran_current_erp": lambda row: _damodaran_current_erp_adapter(workspace_path, row, retrieval),
        "http_regex_metrics": lambda row: _http_regex_metrics_adapter(workspace_path, row, retrieval),
        "http_csv": lambda row: _http_csv_adapter(workspace_path, row, retrieval),
        "local_csv": lambda row: _local_csv_adapter(workspace_path, row, retrieval),
    }
    for raw_source in manifest.get("sources", []):
        if not isinstance(raw_source, Mapping):
            raise ValueError("source manifest sources must contain mappings")
        source = dict(raw_source)
        source_id = _safe_source_id(source.get("id"))
        if source_id in seen:
            raise ValueError(f"duplicate source id: {source_id}")
        seen.add(source_id)
        source["id"] = source_id
        adapter = require_text(source.get("adapter"), f"source {source_id} adapter")
        if source.get("enabled", True) is False:
            statuses.append({"source_id": source_id, "adapter": adapter, "status": "disabled"})
            continue
        if selected_ids is not None and source_id not in selected_ids:
            statuses.append({"source_id": source_id, "adapter": adapter, "status": "not_scheduled"})
            continue
        if adapter not in adapters:
            raise ValueError(f"unsupported public-source adapter: {adapter}")
        try:
            receipt, rows = adapters[adapter](source)
            receipts.append(receipt)
            observations.extend(rows)
            statuses.append({
                "source_id": source_id, "adapter": adapter, "status": "consumed",
                "observation_count": len(rows), "receipt_sha256": receipt.receipt_sha256,
            })
        except (OSError, ValueError, json.JSONDecodeError, csv.Error) as error:
            required = bool(source.get("required", True))
            statuses.append({
                "source_id": source_id, "adapter": adapter, "status": "failed",
                "required": required, "error": str(error),
            })
            if strict or required:
                # Continue through all sources so the operator receives one complete failure report.
                continue
    if selected_ids is not None:
        unknown = sorted(selected_ids - seen)
        if unknown:
            raise ValueError("selected source ids are absent from the manifest: " + ", ".join(unknown))
    raw_signals = manifest.get("signals") or []
    if not isinstance(raw_signals, list):
        raise ValueError("source manifest signals must be a list")
    data_dir = workspace_path / "data"
    observations_path = data_dir / "observations.csv"
    existing_observations, yahoo_identity_compaction = compact_legacy_yahoo_price_identities(
        _read_observations(observations_path), manifest,
    )
    observations = _merge_observations(existing_observations, observations)
    observations, yahoo_granularity_compaction = compact_yahoo_granularity_drift(
        observations, manifest, workspace=workspace_path,
        source_ids={
            receipt.source_id for receipt in receipts
            if receipt.adapter == "yahoo_chart_daily"
        },
    )
    latest_only_sources = {
        str(row.get("id") or "") for row in manifest.get("sources", ())
        if isinstance(row, Mapping) and row.get("latest_only")
    }
    if latest_only_sources:
        observations = list(_compact_latest_only(observations, latest_only_sources))
    definitions: tuple[SignalDefinition, ...] = ()
    signal_receipts = ()
    signal_status: dict[str, Any] = {
        "status": "not_configured" if derive_metrics else "not_scheduled",
        "receipt_count": 0,
    }
    if raw_signals and derive_metrics:
        definitions = tuple(
            SignalDefinition.from_dict(row) for row in raw_signals if isinstance(row, Mapping)
        )
        required_signals = {
            str(row.get("id") or row.get("signal_id") or "")
            for row in raw_signals if isinstance(row, Mapping) and row.get("required", True)
        }
        try:
            observations_with_signals, signal_receipts, signal_blocks = derive_signals_partial(
                observations, definitions, as_of=as_of,
            )
            observations = list(observations_with_signals)
            required_blocks = [
                row for row in signal_blocks if row["signal_id"] in required_signals
            ]
            signal_status = {
                "status": "derived" if not signal_blocks else "derived_partial",
                "receipt_count": len(signal_receipts),
                "blocked_count": len(signal_blocks),
                "blocks": list(signal_blocks),
                "required_signal_ids": sorted(required_signals),
                "required_blocks": required_blocks,
            }
            if strict or required_blocks:
                statuses.append({
                    "source_id": "signal_graph", "adapter": "typed_signal_grammar",
                    "status": "failed", "required": bool(required_blocks),
                    "error": f"{len(signal_blocks)} signal outputs blocked",
                })
        except (KeyError, ValueError) as error:
            signal_status = {
                "status": "blocked", "receipt_count": 0, "error": str(error),
                "required_signal_ids": sorted(required_signals),
            }
            if strict or required_signals:
                statuses.append({
                    "source_id": "signal_graph", "adapter": "typed_signal_grammar",
                    "status": "failed", "required": bool(required_signals), "error": str(error),
                })
    if derive_metrics:
        observations_with_standard, standard_receipts, standard_blocks = derive_standard_metrics(
            observations,
            as_of=as_of,
            configured_outputs={(row.entity_id, row.metric_id) for row in definitions},
        )
        observations = list(observations_with_standard)
        signal_receipts = tuple(signal_receipts) + tuple(standard_receipts)
        standard_metric_status = {
            "status": "derived" if not standard_blocks else "derived_partial",
            "receipt_count": len(standard_receipts),
            "blocked_count": len(standard_blocks),
            "blocks": list(standard_blocks),
        }
    else:
        standard_metric_status = {"status": "not_scheduled", "receipt_count": 0}
    receipts_path = receipt_root / "source_receipts.json"
    receipt_heads_path = receipt_root / "source_receipt_heads.json"
    signals_path = receipt_root / "signal_receipts.json"
    latest_observations_path = receipt_root / "latest_observations.json"
    temporary_observations = observations_path.with_name(
        f".{observations_path.name}.source-refresh.tmp"
    )
    try:
        _write_observations(temporary_observations, observations)
        observation_index = build_observation_index(
            temporary_observations, observations, as_of=as_of,
        )
        temporary_observations.replace(observations_path)
    finally:
        if temporary_observations.exists():
            temporary_observations.unlink()
    _atomic_json(
        latest_observations_path,
        compile_latest_observation_projection(observations, as_of=as_of),
    )
    receipt_rows = [row.to_dict() for row in receipts]
    _atomic_json(receipts_path, {
        "schema": "jaggedthoughts-public-source-receipt-set-v1",
        "as_of": as_of, "retrieved_at": retrieval,
        "receipts": receipt_rows,
    })
    heads = _source_receipt_heads(receipt_heads_path)
    for row in receipt_rows:
        current = heads.get(str(row["source_id"]))
        if current is None or str(row["retrieved_at"]) >= str(current.get("retrieved_at") or ""):
            heads[str(row["source_id"])] = row
    _atomic_json(receipt_heads_path, {
        "schema": "jaggedthoughts-public-source-receipt-heads-v1",
        "as_of": as_of,
        "receipts": [heads[key] for key in sorted(heads)],
    })
    if derive_metrics:
        _atomic_json(signals_path, {
            "schema": "jaggedthoughts-signal-receipt-set-v1",
            "as_of": as_of,
            "receipts": [row.to_dict() for row in signal_receipts],
        })
    required_failures = [row for row in statuses if row.get("status") == "failed" and row.get("required")]
    body: dict[str, Any] = {
        "schema": SOURCE_RUN_SCHEMA,
        "ok": not required_failures,
        "as_of": as_of,
        "retrieved_at": retrieval,
        "manifest_path": str(Path(manifest_path).expanduser().resolve()),
        "workspace_path": str(workspace_path),
        "source_selection": {
            "mode": "complete_manifest" if selected_ids is None else "scheduled_subset",
            "selected_source_ids": sorted(selected_ids or ()),
            "configured_source_count": len(seen),
            "attempted_source_count": len(receipts) + sum(row.get("status") == "failed" for row in statuses),
            "derive_metrics": bool(derive_metrics),
        },
        "source_statuses": statuses,
        "source_receipts": [row.to_dict() for row in receipts],
        "signal_receipts": [row.to_dict() for row in signal_receipts],
        "signal_status": signal_status,
        "standard_metric_status": standard_metric_status,
        "yahoo_identity_compaction": yahoo_identity_compaction,
        "yahoo_granularity_compaction": yahoo_granularity_compaction,
        "observation_count": len(observations),
        "observation_index": observation_index,
        "required_failure_count": len(required_failures),
        "paths": {
            "observations": str(observations_path),
            "source_receipts": str(receipts_path),
            "signal_receipts": str(signals_path),
            "latest_observations": str(latest_observations_path),
            "observation_index": observation_index["path"],
        },
        "historical_use_boundary": (
            "Rows from retrieval_only sources are admissible no earlier than retrieved_at. "
            "Historical experiments require provider vintages or archived retrieval receipts."
        ),
        "evidence_vault": {
            "activation": "automatic_after_source_ingestion",
            "authority": "point_in_time_evidence_only",
            "paper_policy_authority": False,
            "capital_authority": False,
        },
    }
    result = {**body, "run_sha256": stable_sha256(body)}
    capture_public_source_run(workspace_path, result)
    latest_source_run_path = receipt_root / "latest_source_run.json"
    _atomic_json(latest_source_run_path, result)
    if not required_failures:
        epoch = compile_source_epoch(
            workspace_path,
            source_run_path=latest_source_run_path,
            projection_path=latest_observations_path,
            observations_path=observations_path,
            receipt_heads_path=receipt_heads_path,
            source_manifest_path=Path(manifest_path).expanduser().resolve(),
            derivation=derivation_identity(
                raw_signals,
                derive_metrics=derive_metrics,
                metric_universe_sha256=metric_universe_surface()["metric_universe_sha256"],
            ),
        )
        # Keep the lane-local receipt, then advance the one canonical current pointer.
        _atomic_json(receipt_root / "latest_source_epoch.json", epoch)
        if receipt_root != data_dir:
            # Existing compilers still consume this canonical run path directly.
            _atomic_json(data_dir / "latest_source_run.json", result)
            _atomic_json(data_dir / "latest_source_epoch.json", epoch)
    if strict and required_failures:
        raise ValueError(f"{len(required_failures)} required public source(s) failed")
    return result


def consume_public_sources(
    manifest_path: str | Path,
    *,
    workspace: str | Path,
    strict: bool = False,
    retrieved_at: str | None = None,
    source_ids: Iterable[str] | None = None,
    derive_metrics: bool = True,
    receipt_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Serialize source epochs so an older concurrent run cannot replace a newer head."""
    root = Path(workspace).expanduser().resolve()
    lock_dir = root / "state"
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / "source_refresh.lock").open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return _consume_public_sources_unlocked(
            manifest_path, workspace=root, strict=strict,
            retrieved_at=retrieved_at, source_ids=source_ids,
            derive_metrics=derive_metrics, receipt_dir=receipt_dir,
        )


__all__ = [
    "FUND_HOLDINGS_SNAPSHOT_SCHEMA",
    "OBSERVATION_COLUMNS",
    "PUBLIC_SOURCE_MANIFEST_SCHEMA",
    "compile_latest_observation_projection",
    "DEFAULT_SEC_USER_AGENT",
    "SOURCE_RECEIPT_SCHEMA",
    "SOURCE_RUN_SCHEMA",
    "SourceReceipt",
    "compact_yahoo_granularity_drift",
    "consume_public_sources",
    "capture_sec_filing_url",
    "fetch_sec_filing_document",
    "load_source_manifest",
    "project_cached_yahoo_adjusted_prices",
    "source_requirements",
]
