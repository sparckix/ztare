"""Market-wide SEC transaction-event corpus from the nightly submissions archive."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping
import zipfile

import requests

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp
from .sources import DEFAULT_SEC_USER_AGENT


SEC_BULK_SUBMISSIONS_URL = (
    "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
)
SEC_BULK_COMPANYFACTS_URL = (
    "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
)
HISTORICAL_STRATEGY_BULK_CORPUS_SCHEMA = (
    "jaggedthoughts-historical-strategy-bulk-event-corpus-v2"
)
_ROOT = Path("institutional_learning/historical_strategy_bulk_corpus")


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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _acquire_sec_bulk_archive(
    workspace: str | Path, *, source_url: str, archive_id: str,
    receipt_schema: str, force: bool, timeout_seconds: float,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    destination_root = root / "sources" / "bulk" / archive_id
    latest_path = destination_root / "latest.json"
    headers = {"User-Agent": DEFAULT_SEC_USER_AGENT, "Accept": "application/zip"}
    response = requests.head(
        source_url, headers=headers, timeout=(10, 30),
    )
    response.raise_for_status()
    remote = {
        "etag": str(response.headers.get("etag") or ""),
        "last_modified": str(response.headers.get("last-modified") or ""),
        "content_length": int(response.headers.get("content-length") or 0),
    }
    if not force and latest_path.exists():
        prior = json.loads(latest_path.read_text(encoding="utf-8"))
        archive = (root / str(prior.get("raw_path") or "")).resolve()
        try:
            archive.relative_to(root)
            content_ok = (
                archive.is_file()
                and archive.stat().st_size == int(prior.get("content_length") or -1)
                and _file_sha256(archive) == prior.get("content_sha256")
            )
        except (OSError, ValueError):
            content_ok = False
        if content_ok and all(prior.get(key) == value for key, value in remote.items()):
            return prior

    destination_root.mkdir(parents=True, exist_ok=True)
    temporary = destination_root / f".{archive_id}.zip.tmp"
    digest = hashlib.sha256()
    size = 0
    with requests.get(
        source_url, headers=headers, stream=True,
        timeout=(10, timeout_seconds),
    ) as download:
        download.raise_for_status()
        with temporary.open("wb") as output:
            for chunk in download.iter_content(chunk_size=4 * 1024 * 1024):
                if not chunk:
                    continue
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    if remote["content_length"] and size != remote["content_length"]:
        temporary.unlink(missing_ok=True)
        raise ValueError("SEC bulk submissions download length mismatch")
    stem = archive_id.removeprefix("sec_")
    destination = destination_root / f"{stem}-{digest.hexdigest()[:20]}.zip"
    temporary.replace(destination)
    body = {
        "schema": receipt_schema,
        "source_url": source_url,
        "retrieved_at": _utc_now(), "raw_path": destination.relative_to(root).as_posix(),
        "content_sha256": digest.hexdigest(), "content_length": size, **remote,
        "availability_mode": "provider_filing_timestamps",
    }
    receipt = {**body, "receipt_sha256": stable_sha256(body)}
    _atomic_json(latest_path, receipt)
    return receipt


def acquire_sec_bulk_submissions(
    workspace: str | Path, *, force: bool = False, timeout_seconds: float = 300.0,
) -> dict[str, Any]:
    """Download or reuse the SEC nightly submissions archive."""
    return _acquire_sec_bulk_archive(
        workspace, source_url=SEC_BULK_SUBMISSIONS_URL,
        archive_id="sec_submissions",
        receipt_schema="jaggedthoughts-sec-bulk-submissions-receipt-v1",
        force=force, timeout_seconds=timeout_seconds,
    )


def acquire_sec_bulk_companyfacts(
    workspace: str | Path, *, force: bool = False, timeout_seconds: float = 300.0,
) -> dict[str, Any]:
    """Download or reuse the SEC nightly Company Facts archive."""
    return _acquire_sec_bulk_archive(
        workspace, source_url=SEC_BULK_COMPANYFACTS_URL,
        archive_id="sec_companyfacts",
        receipt_schema="jaggedthoughts-sec-bulk-companyfacts-receipt-v1",
        force=force, timeout_seconds=timeout_seconds,
    )


def _logical_archive_delta(
    older: Path, successor: Path, destination_root: Path,
) -> dict[str, Any]:
    """Preserve the changed members needed to reconstruct one older snapshot."""

    older_sha, successor_sha = _file_sha256(older), _file_sha256(successor)
    destination = destination_root / (
        f"{older_sha[:16]}-to-{successor_sha[:16]}.zip"
    )
    if destination.exists():
        with zipfile.ZipFile(destination) as delta:
            manifest = json.loads(delta.read("__jaggedthoughts__/manifest.json"))
            if (
                manifest.get("older_archive_sha256") != older_sha
                or manifest.get("successor_archive_sha256") != successor_sha
            ):
                raise ValueError("SEC logical archive delta identity mismatch")
            for row in manifest["changed_or_removed_members"]:
                if hashlib.sha256(delta.read(row["member"])).hexdigest() != row[
                    "content_sha256"
                ]:
                    raise ValueError("SEC logical archive delta verification failed")
        return {
            "older_archive": older.name, "successor_archive": successor.name,
            "delta_path": destination.as_posix(), "delta_sha256": _file_sha256(destination),
            "status": "existing_delta",
        }
    temporary = destination.with_name(f".{destination.name}.tmp")
    destination_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(older) as old_bundle, zipfile.ZipFile(successor) as new_bundle:
        old_index = {
            info.filename: info for info in old_bundle.infolist() if not info.is_dir()
        }
        new_index = {
            info.filename: info for info in new_bundle.infolist() if not info.is_dir()
        }
        changed_names = [
            name for name, info in old_index.items()
            if name not in new_index or (
                info.CRC, info.file_size
            ) != (new_index[name].CRC, new_index[name].file_size)
        ]
        successor_only = sorted(set(new_index) - set(old_index))
        changed = []
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
        ) as delta:
            for name in sorted(changed_names):
                content = old_bundle.read(old_index[name])
                delta.writestr(name, content)
                changed.append({
                    "member": name, "content_sha256": hashlib.sha256(content).hexdigest(),
                    "size": len(content), "crc32": old_index[name].CRC,
                })
            manifest = {
                "schema": "jaggedthoughts-sec-logical-archive-delta-v1",
                "older_archive_sha256": older_sha,
                "successor_archive_sha256": successor_sha,
                "older_member_count": len(old_index),
                "successor_member_count": len(new_index),
                "unchanged_member_count": len(old_index) - len(changed),
                "changed_or_removed_members": changed,
                "successor_only_members": successor_only,
                "reconstruction_semantics": (
                    "apply changed members and remove successor-only members from the "
                    "successor logical member set; original zip container bytes are not reproduced"
                ),
            }
            delta.writestr(
                "__jaggedthoughts__/manifest.json",
                json.dumps(manifest, sort_keys=True, ensure_ascii=False),
            )
    if temporary.stat().st_size >= older.stat().st_size:
        temporary.unlink()
        return {
            "older_archive": older.name, "successor_archive": successor.name,
            "status": "retained_raw_delta_not_smaller",
        }
    temporary.replace(destination)
    with zipfile.ZipFile(destination) as delta:
        stored = json.loads(delta.read("__jaggedthoughts__/manifest.json"))
        for row in stored["changed_or_removed_members"]:
            if hashlib.sha256(delta.read(row["member"])).hexdigest() != row[
                "content_sha256"
            ]:
                raise ValueError("SEC logical archive delta verification failed")
    return {
        "older_archive": older.name, "successor_archive": successor.name,
        "older_archive_sha256": older_sha,
        "delta_path": destination.as_posix(), "delta_sha256": _file_sha256(destination),
        "delta_byte_count": destination.stat().st_size,
        "status": "logical_delta_verified",
    }


def enforce_sec_bulk_archive_retention(
    workspace: str | Path, *, keep_raw: int = 2,
) -> dict[str, Any]:
    """Keep two raw SEC snapshots and compact older snapshots into logical deltas."""

    if isinstance(keep_raw, bool) or keep_raw < 2:
        raise ValueError("SEC archive retention requires current plus predecessor")
    root = Path(workspace).expanduser().resolve()
    corpus = json.loads((root / _ROOT / "latest.json").read_text(encoding="utf-8"))
    outcomes = json.loads((
        root / "institutional_learning/historical_strategy_bulk_outcomes/latest.json"
    ).read_text(encoding="utf-8"))
    submissions = json.loads((
        root / "sources/bulk/sec_submissions/latest.json"
    ).read_text(encoding="utf-8"))
    companyfacts = json.loads((
        root / "sources/bulk/sec_companyfacts/latest.json"
    ).read_text(encoding="utf-8"))
    latest_path = root / "sources/bulk/retention/latest.json"
    prior_retention = (
        json.loads(latest_path.read_text(encoding="utf-8"))
        if latest_path.is_file() else None
    )
    if prior_retention:
        prior_body = dict(prior_retention)
        prior_sha = str(prior_body.pop("retention_sha256", ""))
        if stable_sha256(prior_body) != prior_sha:
            raise ValueError("SEC retention receipt hash mismatch")

    def archive_epoch() -> list[dict[str, Any]]:
        rows = []
        for archive_id in ("sec_submissions", "sec_companyfacts"):
            directory = root / "sources/bulk" / archive_id
            for path in sorted((
                *directory.glob("*.zip"),
                *(directory / "logical_deltas").glob("*.zip"),
            )):
                stat = path.stat()
                rows.append({
                    "path": path.relative_to(root).as_posix(),
                    "byte_count": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                })
        return rows

    retention_basis = {
        "bulk_corpus_sha256": corpus.get("corpus_sha256"),
        "outcomes_sha256": outcomes.get("outcomes_sha256"),
        "submissions_receipt_sha256": submissions.get("receipt_sha256"),
        "companyfacts_receipt_sha256": companyfacts.get("receipt_sha256"),
        "submissions_raw_path": submissions.get("raw_path"),
        "companyfacts_raw_path": companyfacts.get("raw_path"),
    }
    current_archive_epoch = archive_epoch()
    if (
        prior_retention
        and prior_retention.get("keep_raw_per_archive") == keep_raw
        and prior_retention.get("retention_basis") == retention_basis
        and prior_retention.get("archive_epoch") == current_archive_epoch
    ):
        return prior_retention
    if prior_retention and not prior_retention.get("retention_basis"):
        epoch_by_path = {row["path"]: row for row in current_archive_epoch}
        prior_delta_sizes = {
            str(row.get("delta_path") or ""): int(row.get("delta_byte_count") or -1)
            for row in prior_retention.get("delta_inventory") or ()
        }
        current_delta_paths = {
            path for path in epoch_by_path if "/logical_deltas/" in path
        }
        raw_counts = {
            archive_id: sum(
                row["path"].startswith(f"sources/bulk/{archive_id}/")
                and "/logical_deltas/" not in row["path"]
                for row in current_archive_epoch
            )
            for archive_id in ("sec_submissions", "sec_companyfacts")
        }
        legacy_receipt_epoch_ns = latest_path.stat().st_mtime_ns
        legacy_epoch_unchanged = bool(
            current_delta_paths == set(prior_delta_sizes)
            and all(
                epoch_by_path[path]["byte_count"] == prior_delta_sizes[path]
                for path in current_delta_paths
            )
            and all(count == keep_raw for count in raw_counts.values())
            and all(row["mtime_ns"] <= legacy_receipt_epoch_ns for row in current_archive_epoch)
            and all(
                (root / str(receipt.get("raw_path") or "")).is_file()
                for receipt in (submissions, companyfacts)
            )
        )
        if legacy_epoch_unchanged:
            body = {
                "schema": "jaggedthoughts-sec-bulk-archive-retention-v1",
                "applied_at": _utc_now(), "keep_raw_per_archive": keep_raw,
                "actions": [],
                "delta_inventory": list(prior_retention.get("delta_inventory") or ()),
                "retention_basis": retention_basis,
                "archive_epoch": current_archive_epoch,
                "previous_retention_sha256": prior_retention.get("retention_sha256"),
                "migration_basis": "verified_legacy_receipt_with_unchanged_file_epoch",
                "recovery_boundary": (
                    "current and predecessor retain exact zip bytes; older snapshots retain "
                    "verified changed-member deltas for logical reconstruction"
                ),
                "capital_authority": False,
            }
            receipt = {**body, "retention_sha256": stable_sha256(body)}
            immutable_path = (
                root / "sources/bulk/retention/receipts"
                / f"{receipt['retention_sha256']}.json"
            )
            _atomic_json(immutable_path, receipt)
            _atomic_json(latest_path, receipt)
            return receipt
    corpus_body = dict(corpus)
    corpus_sha = str(corpus_body.pop("corpus_sha256", ""))
    outcomes_body = dict(outcomes)
    outcomes_sha = str(outcomes_body.pop("outcomes_sha256", ""))
    event_lake = (root / str(corpus.get("event_lake_path") or "")).resolve()
    outcome_lake = (root / str(outcomes.get("observation_lake_path") or "")).resolve()
    event_lake.relative_to(root)
    outcome_lake.relative_to(root)
    if (
        stable_sha256(corpus_body) != corpus_sha
        or stable_sha256(outcomes_body) != outcomes_sha
        or _file_sha256(event_lake) != corpus.get("event_lake_sha256")
        or _file_sha256(outcome_lake) != outcomes.get("observation_lake_sha256")
        or corpus.get("bulk_source_receipt_sha256") != submissions.get("receipt_sha256")
        or outcomes.get("companyfacts_receipt_sha256") != companyfacts.get("receipt_sha256")
        or outcomes.get("bulk_corpus_sha256") != corpus.get("corpus_sha256")
    ):
        raise ValueError("SEC archive retention requires settled current dependents")
    actions = []
    current_receipts = {
        "sec_submissions": submissions, "sec_companyfacts": companyfacts,
    }
    for archive_id, current_receipt in current_receipts.items():
        directory = root / "sources/bulk" / archive_id
        archives = sorted(
            directory.glob("*.zip"), key=lambda path: (path.stat().st_mtime_ns, path.name),
        )
        current_archive = (root / str(current_receipt["raw_path"])).resolve()
        current_archive.relative_to(directory)
        if not archives or archives[-1].resolve() != current_archive:
            raise ValueError("SEC archive retention requires current receipt to be newest")
        delta_root = directory / "logical_deltas"
        for index, older in enumerate(archives[:-keep_raw]):
            action = _logical_archive_delta(older, archives[index + 1], delta_root)
            action["archive_id"] = archive_id
            if action["status"] == "logical_delta_verified":
                action["removed_raw_path"] = older.relative_to(root).as_posix()
                action["removed_raw_byte_count"] = older.stat().st_size
                older.unlink()
            if action.get("delta_path"):
                action["delta_path"] = Path(action["delta_path"]).relative_to(root).as_posix()
            actions.append(action)
    delta_inventory = []
    for archive_id in current_receipts:
        directory = root / "sources/bulk" / archive_id
        stem = archive_id.removeprefix("sec_")
        for delta_path in sorted((directory / "logical_deltas").glob("*.zip")):
            with zipfile.ZipFile(delta_path) as delta:
                manifest = json.loads(delta.read("__jaggedthoughts__/manifest.json"))
                for row in manifest["changed_or_removed_members"]:
                    if hashlib.sha256(delta.read(row["member"])).hexdigest() != row[
                        "content_sha256"
                    ]:
                        raise ValueError("SEC logical archive delta verification failed")
            older_sha = str(manifest["older_archive_sha256"])
            raw_name = f"{stem}-{older_sha[:20]}.zip"
            delta_inventory.append({
                "archive_id": archive_id,
                "removed_raw_path": (directory / raw_name).relative_to(root).as_posix(),
                "raw_snapshot_present": (directory / raw_name).exists(),
                "older_archive_sha256": older_sha,
                "successor_archive_sha256": manifest["successor_archive_sha256"],
                "delta_path": delta_path.relative_to(root).as_posix(),
                "delta_sha256": _file_sha256(delta_path),
                "delta_byte_count": delta_path.stat().st_size,
            })
    if (
        not actions and prior_retention
        and prior_retention.get("delta_inventory") == delta_inventory
        and prior_retention.get("retention_basis") == retention_basis
    ):
        return prior_retention
    body = {
        "schema": "jaggedthoughts-sec-bulk-archive-retention-v1",
        "applied_at": _utc_now(), "keep_raw_per_archive": keep_raw,
        "actions": actions,
        "delta_inventory": delta_inventory,
        "retention_basis": retention_basis,
        "archive_epoch": archive_epoch(),
        "previous_retention_sha256": (
            prior_retention.get("retention_sha256") if prior_retention else None
        ),
        "recovery_boundary": (
            "current and predecessor retain exact zip bytes; older snapshots retain "
            "verified changed-member deltas for logical reconstruction"
        ),
        "capital_authority": False,
    }
    receipt = {**body, "retention_sha256": stable_sha256(body)}
    immutable_path = (
        root / "sources/bulk/retention/receipts"
        / f"{receipt['retention_sha256']}.json"
    )
    if immutable_path.exists():
        if json.loads(immutable_path.read_text(encoding="utf-8")) != receipt:
            raise ValueError("SEC retention receipt identity collision")
    else:
        _atomic_json(immutable_path, receipt)
    _atomic_json(latest_path, receipt)
    return receipt


def _registry_by_symbol(root: Path) -> dict[str, str]:
    candidates = list((root / "sources" / "registry").glob("sec-company-tickers-*.json"))
    if not candidates:
        raise FileNotFoundError("SEC ticker registry cache is unavailable")
    latest = max(candidates, key=lambda path: path.stat().st_mtime_ns)
    payload = json.loads(latest.read_text(encoding="utf-8"))
    return {
        str(row.get("ticker") or "").upper(): f"{int(row['cik_str']):010d}"
        for row in payload.values() if isinstance(row, Mapping) and row.get("ticker")
    }


def _current_common_equity_ciks(
    root: Path,
) -> tuple[dict[str, set[str]], str, str]:
    catalog = json.loads((root / "universe" / "catalog-latest.json").read_text(encoding="utf-8"))
    body = dict(catalog)
    catalog_sha = str(body.pop("catalog_sha256", ""))
    if stable_sha256(body) != catalog_sha:
        raise ValueError("public market catalog content hash mismatch")
    registry = _registry_by_symbol(root)
    by_cik: dict[str, set[str]] = {}
    for row in catalog.get("securities") or ():
        symbol = str(row.get("symbol") or "").upper()
        if (
            row.get("entity_kind") != "public_equity"
            or row.get("security_kind") != "common_equity"
            or row.get("country") != "United States"
            or symbol not in registry
        ):
            continue
        by_cik.setdefault(registry[symbol], set()).add(symbol)
    population_sha = stable_sha256({
        cik: sorted(symbols) for cik, symbols in sorted(by_cik.items())
    })
    return by_cik, catalog_sha, population_sha


def _filing_rows(columns: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    forms = list(columns.get("form") or ())
    for index, form in enumerate(forms):
        items = str((columns.get("items") or [""] * len(forms))[index])
        if form != "8-K" or "2.01" not in {value.strip() for value in items.split(",")}:
            continue
        accepted = str((columns.get("acceptanceDateTime") or [""] * len(forms))[index])
        filed = str((columns.get("filingDate") or [""] * len(forms))[index])
        report = str((columns.get("reportDate") or [""] * len(forms))[index])
        if not filed:
            continue
        yield {
            "accession_number": str(columns["accessionNumber"][index]),
            "primary_document": str(columns["primaryDocument"][index]),
            "form": "8-K", "item": "2.01", "filing_date": filed,
            "occurred_at": canonical_timestamp(
                f"{report or filed}T00:00:00Z", "bulk SEC event date",
            ),
            "available_at": canonical_timestamp(
                accepted or f"{filed}T23:59:59Z", "bulk SEC event availability",
            ),
        }


def _zip_members(bundle: zipfile.ZipFile) -> tuple[dict[str, str], dict[str, tuple[tuple[str, int, int], ...]]]:
    members = {Path(info.filename).name: info.filename for info in bundle.infolist()}
    signatures: dict[str, list[tuple[str, int, int]]] = {}
    for info in bundle.infolist():
        name = Path(info.filename).name
        if not name.startswith("CIK") or not name.endswith(".json"):
            continue
        cik = name.removeprefix("CIK").split("-submissions-", 1)[0].removesuffix(".json")
        signatures.setdefault(cik, []).append((name, info.CRC, info.file_size))
    return members, {
        cik: tuple(sorted(rows)) for cik, rows in signatures.items()
    }


def _issuer_events(
    bundle: zipfile.ZipFile, members: Mapping[str, str], *, cik: str,
    symbols: set[str], receipt: Mapping[str, Any], start_year: int, through_year: int,
) -> Iterable[dict[str, Any]]:
    main_name = f"CIK{cik}.json"
    member = members.get(main_name)
    if member is None:
        return
    payload = json.loads(bundle.read(member))
    filing_sets = [((payload.get("filings") or {}).get("recent") or {})]
    for old in (payload.get("filings") or {}).get("files") or ():
        old_member = members.get(Path(str(old.get("name") or "")).name)
        if old_member:
            filing_sets.append(json.loads(bundle.read(old_member)))
    for columns in filing_sets:
        for filing in _filing_rows(columns):
            year = int(filing["filing_date"][:4])
            if not start_year <= year <= through_year:
                continue
            body = {
                "schema": "jaggedthoughts-bulk-sec-item-2.01-event-v1",
                "cik": cik,
                "current_common_equity_symbols": sorted(symbols),
                "sec_tickers": sorted(str(value) for value in payload.get("tickers") or ()),
                "sec_exchanges": sorted(str(value) for value in payload.get("exchanges") or ()),
                "current_common_equity_member": bool(symbols),
                "company_name": str(payload.get("name") or ""),
                "sic": str(payload.get("sic") or ""),
                "sic_description": str(payload.get("sicDescription") or ""),
                **filing,
                "bulk_source_receipt_sha256": receipt["receipt_sha256"],
            }
            yield {**body, "event_sha256": stable_sha256(body)}


def compile_historical_strategy_bulk_event_corpus(
    workspace: str | Path, *, start_year: int = 2010, end_year: int | None = None,
) -> dict[str, Any]:
    """Filter the nightly archive into one current-common-equity Item 2.01 lake."""
    root = Path(workspace).expanduser().resolve()
    receipt = json.loads((
        root / "sources" / "bulk" / "sec_submissions" / "latest.json"
    ).read_text(encoding="utf-8"))
    archive = (root / str(receipt["raw_path"])).resolve()
    archive.relative_to(root)
    current_equities_by_cik, catalog_sha, population_sha = _current_common_equity_ciks(root)
    through_year = end_year or int(str(receipt["retrieved_at"])[:4])
    transform_sha = stable_sha256({
        "bulk_source_receipt_sha256": receipt["receipt_sha256"],
        "bulk_source_content_sha256": receipt["content_sha256"],
        "market_catalog_sha256": catalog_sha,
        "current_common_equity_population_sha256": population_sha,
        "start_year": start_year,
        "end_year": through_year,
    })
    destination = (
        root / _ROOT
        / f"events-{receipt['content_sha256'][:12]}-{transform_sha[:12]}.jsonl"
    )
    latest_path = root / _ROOT / "latest.json"
    prior_corpus = None
    if latest_path.exists():
        prior_corpus = json.loads(latest_path.read_text(encoding="utf-8"))
        lake = (root / str(prior_corpus.get("event_lake_path") or "")).resolve()
        try:
            lake.relative_to(root)
            reusable = (
                prior_corpus.get("schema") == HISTORICAL_STRATEGY_BULK_CORPUS_SCHEMA
                and prior_corpus.get("bulk_source_receipt_sha256") == receipt.get("receipt_sha256")
                and prior_corpus.get("market_catalog_sha256") == catalog_sha
                and prior_corpus.get("current_common_equity_population_sha256")
                == population_sha
                and prior_corpus.get("start_year") == start_year
                and prior_corpus.get("end_year") == through_year
                and lake.is_file()
                and _file_sha256(lake) == prior_corpus.get("event_lake_sha256")
            )
        except (OSError, ValueError):
            reusable = False
        if reusable:
            if all(
                prior_corpus.get(field) is not None
                for field in (
                    "compilation_mode", "reparsed_issuer_count",
                    "bulk_source_content_sha256", "transform_sha256",
                )
            ) and lake == destination.resolve():
                return prior_corpus
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if _file_sha256(destination) != prior_corpus["event_lake_sha256"]:
                    raise ValueError("SEC event-lake transform identity collision")
            else:
                destination.write_bytes(lake.read_bytes())
            body = {
                **{
                    key: value for key, value in prior_corpus.items()
                    if key != "corpus_sha256"
                },
                "compilation_mode": "full_archive_rebuild",
                "reparsed_issuer_count": int(
                    prior_corpus.get("archive_main_issuer_count") or 0
                ),
                "bulk_source_content_sha256": receipt["content_sha256"],
                "transform_sha256": transform_sha,
                "event_lake_path": destination.relative_to(root).as_posix(),
                "event_lake_sha256": _file_sha256(destination),
            }
            migrated = {**body, "corpus_sha256": stable_sha256(body)}
            _atomic_json(latest_path, migrated)
            return migrated
    if _file_sha256(archive) != receipt["content_sha256"]:
        raise ValueError("SEC bulk submissions archive hash mismatch")
    events_by_accession: dict[tuple[str, str], dict[str, Any]] = {}
    missing_ciks = []
    compilation_mode = "full_archive_rebuild"
    changed_ciks: set[str] = set()
    with zipfile.ZipFile(archive) as bundle:
        members, signatures = _zip_members(bundle)
        available_ciks = {
            name.removeprefix("CIK").removesuffix(".json")
            for name in members if name.startswith("CIK") and "-submissions-" not in name
        }
        missing_ciks = sorted(set(current_equities_by_cik) - available_ciks)
        prior_lake = None
        previous_archive = None
        if prior_corpus is not None and (
            prior_corpus.get("schema") == HISTORICAL_STRATEGY_BULK_CORPUS_SCHEMA
            and prior_corpus.get("current_common_equity_population_sha256")
            == population_sha
            and prior_corpus.get("start_year") == start_year
            and prior_corpus.get("end_year") == through_year
        ):
            candidate = (root / str(prior_corpus.get("event_lake_path") or "")).resolve()
            try:
                candidate.relative_to(root)
                if candidate.is_file() and _file_sha256(candidate) == prior_corpus.get(
                    "event_lake_sha256"
                ):
                    prior_lake = candidate
                    prefix = str(
                        prior_corpus.get("bulk_source_content_sha256")
                        or candidate.stem.removeprefix("events-").split("-", 1)[0]
                    )[:20]
                    previous_archive = next(iter(sorted(
                        (root / "sources/bulk/sec_submissions").glob(
                            f"submissions-{prefix}*.zip"
                        )
                    )), None)
            except (OSError, ValueError):
                prior_lake = None
        if prior_lake is not None and previous_archive is not None:
            with zipfile.ZipFile(previous_archive) as previous:
                _, previous_signatures = _zip_members(previous)
            changed_ciks = {
                cik for cik in set(signatures) | set(previous_signatures)
                if signatures.get(cik) != previous_signatures.get(cik)
            }
            for line in prior_lake.read_text(encoding="utf-8").splitlines():
                prior_event = json.loads(line)
                cik = str(prior_event["cik"])
                if cik in changed_ciks:
                    continue
                body = {key: value for key, value in prior_event.items() if key != "event_sha256"}
                body["bulk_source_receipt_sha256"] = receipt["receipt_sha256"]
                event = {**body, "event_sha256": stable_sha256(body)}
                events_by_accession[(cik, str(event["accession_number"]))] = event
            compilation_mode = "incremental_changed_issuer_replay"
        else:
            changed_ciks = set(signatures)
        for cik in sorted(changed_ciks & available_ciks):
            for event in _issuer_events(
                bundle, members, cik=cik,
                symbols=current_equities_by_cik.get(cik, set()), receipt=receipt,
                start_year=start_year, through_year=through_year,
            ):
                identity = (cik, str(event["accession_number"]))
                prior_event = events_by_accession.setdefault(identity, event)
                if prior_event != event:
                    raise ValueError(f"conflicting duplicate SEC filing {identity}")
    events = list(events_by_accession.values())
    events.sort(key=lambda row: (row["available_at"], row["cik"], row["accession_number"]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in events),
        encoding="utf-8",
    )
    if destination.exists():
        if _file_sha256(destination) != _file_sha256(temporary):
            temporary.unlink()
            raise ValueError("SEC event-lake transform identity collision")
        temporary.unlink()
    else:
        temporary.replace(destination)
    years = Counter(row["filing_date"][:4] for row in events)
    body = {
        "schema": HISTORICAL_STRATEGY_BULK_CORPUS_SCHEMA,
        "generated_at": receipt["retrieved_at"],
        "bulk_source_receipt_sha256": receipt["receipt_sha256"],
        "bulk_source_content_sha256": receipt["content_sha256"],
        "transform_sha256": transform_sha,
        "market_catalog_sha256": catalog_sha,
        "current_common_equity_population_sha256": population_sha,
        "start_year": start_year, "end_year": through_year,
        "issuer_population_scope": "all_sec_filers_with_item_2.01_events",
        "archive_main_issuer_count": len(available_ciks),
        "compilation_mode": compilation_mode,
        "reparsed_issuer_count": len(changed_ciks & available_ciks),
        "current_common_equity_eligible_cik_count": len(current_equities_by_cik),
        "current_common_equity_missing_cik_count": len(missing_ciks),
        "current_common_equity_missing_ciks": missing_ciks,
        "event_count": len(events),
        "event_entity_count": len({row["cik"] for row in events}),
        "current_common_equity_event_count": sum(
            bool(row["current_common_equity_member"]) for row in events
        ),
        "current_common_equity_event_entity_count": len({
            row["cik"] for row in events if row["current_common_equity_member"]
        }),
        "events_by_year": dict(sorted(years.items())),
        "event_lake_path": destination.relative_to(root).as_posix(),
        "event_lake_sha256": _file_sha256(destination),
        "classification_status": "primary_documents_not_yet_hydrated",
        "outcome_join_status": "bulk_financial_panel_not_yet_compiled",
        "next_activation": "Rank event documents by moderator-cell information yield, then join as-filed bulk financial outcomes without conditioning the learning population on current survival.",
        "causal_estimate_ran": False, "promotion_eligible": False,
        "paper_policy_authority": False, "capital_authority": False,
    }
    corpus = {**body, "corpus_sha256": stable_sha256(body)}
    _atomic_json(latest_path, corpus)
    return corpus


__all__ = [
    "HISTORICAL_STRATEGY_BULK_CORPUS_SCHEMA", "SEC_BULK_SUBMISSIONS_URL",
    "SEC_BULK_COMPANYFACTS_URL", "acquire_sec_bulk_companyfacts",
    "acquire_sec_bulk_submissions", "compile_historical_strategy_bulk_event_corpus",
    "enforce_sec_bulk_archive_retention",
]
