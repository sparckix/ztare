"""Closed-book walk-forward tournament for typed strategy phenotypes."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
from statistics import mean, median
from typing import Any, Iterable, Mapping
import zipfile

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.strategy import (
    CandidateEvaluation,
    FrontierScope,
    Neighborhood,
    RepresentationAudit,
    compile_enumeration_result,
    compile_jaggedthoughts_frontier,
)

from .historical_strategy_control_design import (
    HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS,
    enumerate_historical_strategy_moderator_programs,
)
from .historical_strategy_event_replay import HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA
from .closed_book import overlap_cluster_ids
from .factor_analysis import (
    FactorDefinition,
    InsufficientFactorHistoryError,
    PricePoint,
    compile_historical_factor_control,
    load_price_points,
)
from .contracts import canonical_timestamp, timestamp_key
from .sources import fetch_sec_filing_document, load_source_manifest


STRATEGY_WALK_FORWARD_SCHEMA = "jaggedthoughts-strategy-walk-forward-tournament-v1"
STRATEGY_SECURITY_WALK_FORWARD_SCHEMA = (
    "jaggedthoughts-strategy-security-walk-forward-tournament-v1"
)
_MIN_TRAINING_BLOCKS = 3
_MIN_TRAINING_EPISODES = 10
_MIN_CELL_EPISODES = 3
_MIN_CELL_ENTITIES = 2
_MIN_SECURITY_CALENDAR_COHORTS = 8
_SECURITY_COMPILER_VERSION = "14"
_SECURITY_IDENTITY_PARSER_VERSION = "4"


def _checked(payload: Mapping[str, Any], field: str, label: str) -> str:
    body = dict(payload)
    declared = str(body.pop(field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{label} content hash mismatch")
    return declared


def _phenotype_value(episode: Mapping[str, Any], field: str) -> str:
    if field == "implementation_mode":
        return str(episode.get(field) or "indeterminate")
    phenotype = episode.get("transaction_phenotype")
    return str((phenotype if isinstance(phenotype, Mapping) else {}).get(field) or "indeterminate")


def _cell_key(episode: Mapping[str, Any], fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_phenotype_value(episode, field) for field in fields)


def _prediction(
    training: Iterable[Mapping[str, Any]], episode: Mapping[str, Any],
    fields: tuple[str, ...],
) -> dict[str, Any]:
    rows = list(training)
    global_effects = [float(row["estimated_effect"]) for row in rows]
    if not global_effects:
        raise ValueError("strategy walk-forward prediction requires training episodes")
    key = _cell_key(episode, fields)
    cell = [row for row in rows if _cell_key(row, fields) == key]
    supported = (
        len(cell) >= _MIN_CELL_EPISODES
        and len({str(row["entity_id"]) for row in cell}) >= _MIN_CELL_ENTITIES
    )
    source = cell if fields and supported else rows
    effect = float(median(float(row["estimated_effect"]) for row in source))
    return {
        "predicted_effect": effect,
        "prediction_basis": "typed_phenotype_cell" if source is cell else "global_median_backoff",
        "cell_key": list(key),
        "cell_episode_count": len(cell),
        "cell_entity_count": len({str(row["entity_id"]) for row in cell}),
    }


def _program_summary(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    values = list(rows)
    losses = [float(row["absolute_error"]) for row in values]
    return {
        "prediction_count": len(values),
        "mean_absolute_error": mean(losses) if losses else None,
        "direction_accuracy": (
            mean(float(bool(row["direction_correct"])) for row in values)
            if values else None
        ),
        "typed_cell_rate": (
            mean(row["prediction_basis"] == "typed_phenotype_cell" for row in values)
            if values else None
        ),
    }


def _neighborhood(programs: Iterable[Any], fields_by_program: Mapping[str, tuple[str, ...]]) -> Neighborhood:
    rows = list(programs)
    edges = []
    for left in rows:
        left_fields = set(fields_by_program[left.program_id])
        for right in rows:
            right_fields = set(fields_by_program[right.program_id])
            if left_fields < right_fields and len(right_fields) == len(left_fields) + 1:
                edges.append((left.program_id, right.program_id))
    return Neighborhood("one-strategy-phenotype-edit", tuple(edges))


def _selection(
    *, grammar: Any, enumeration: Any, programs: list[Any],
    fields_by_program: Mapping[str, tuple[str, ...]], history: list[dict[str, Any]],
    evidence_epoch: str,
    target_type: str = "historical_strategy_projection",
    evaluation_model_id: str = "expanding_window_median_effect_v1",
    representation_audit_id: str = "historical-strategy-walk-forward-representation",
    representation_residuals: tuple[str, ...] = (
        "transaction_classifier_was_designed_after_part_of_the_sample",
        "business_outcomes_are_not_security_returns",
        "causal_controls_are_not_part_of_this_forecast_tournament",
    ),
) -> tuple[str, dict[str, Any] | None]:
    baseline = next(
        program.program_id for program in programs
        if not fields_by_program[program.program_id]
    )
    if not history:
        return baseline, None
    by_program: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in history:
        by_program[str(row["program_id"])].append(row)
    evaluations = []
    summaries = {}
    for program in programs:
        program_id = program.program_id
        summary = _program_summary(by_program.get(program_id, ()))
        summaries[program_id] = summary
        mae = float(summary["mean_absolute_error"])
        fields = fields_by_program[program_id]
        evaluations.append(CandidateEvaluation(
            program_id=program_id,
            objective_values=(
                1.0 / (1.0 + mae),
                float(summary["direction_accuracy"]),
                float(summary["typed_cell_rate"]),
                1.0 - len(fields) / len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
            ),
            behavior_signature=(program_id,),
            evidence_refs=tuple(sorted({str(row["episode_sha256"]) for row in by_program[program_id]})),
        ))
    neighborhood = _neighborhood(programs, fields_by_program)
    scope = FrontierScope(
        grammar_id=grammar.grammar_id,
        grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        target_type=target_type,
        max_depth=len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
        max_programs=2 ** len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
        evaluation_model_id=evaluation_model_id,
        landscape_mode="fixed",
        evidence_epoch=evidence_epoch,
        objective_names=(
            "inverse_absolute_error", "direction_accuracy",
            "typed_cell_rate", "parsimony",
        ),
        neighborhood_id=neighborhood.neighborhood_id,
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope, enumeration=enumeration, evaluations=evaluations,
        neighborhood=neighborhood,
        representation_audit=RepresentationAudit(
            representation_audit_id,
            status="residual",
            residuals=representation_residuals,
        ),
    )
    frontier = set(certificate.frontier_program_ids)
    selected = min(
        (program_id for program_id in frontier),
        key=lambda program_id: (
            float(summaries[program_id]["mean_absolute_error"]),
            -float(summaries[program_id]["direction_accuracy"]),
            -float(summaries[program_id]["typed_cell_rate"]),
            len(fields_by_program[program_id]),
            program_id,
        ),
    )
    receipt_body = {
        "evidence_epoch": evidence_epoch,
        "history_prediction_count": len(history),
        "frontier_program_ids": sorted(frontier),
        "selected_program_id": selected,
        "selected_moderator_fields": list(fields_by_program[selected]),
        "certificate": certificate.to_dict(),
    }
    return selected, {**receipt_body, "selection_sha256": stable_sha256(receipt_body)}


def compile_strategy_walk_forward(replay: Mapping[str, Any]) -> dict[str, Any]:
    """Choose each strategy predictor before opening its next outcome block."""
    if replay.get("schema") != HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA:
        raise ValueError("strategy walk-forward requires a historical strategy replay")
    replay_sha = _checked(replay, "replay_sha256", "historical strategy replay")
    episodes = [dict(row) for row in replay.get("episodes") or ()]
    for episode in episodes:
        _checked(episode, "episode_sha256", "historical strategy episode")
        if abs(
            float(episode["outcome"]["value"])
            - float(episode["baseline"]["value"])
            - float(episode["estimated_effect"])
        ) > 1e-12:
            raise ValueError("historical strategy episode effect differs from its observations")
    blocks = sorted({str(row["inference_block_id"]) for row in episodes})
    grammar, programs, fields_by_program = enumerate_historical_strategy_moderator_programs()
    enumeration = compile_enumeration_result(
        grammar, programs=programs,
        max_depth=len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
        max_programs=2 ** len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
    )
    history: list[dict[str, Any]] = []
    folds, chosen_predictions = [], []
    for block_index, block in enumerate(blocks):
        training = [row for row in episodes if str(row["inference_block_id"]) < block]
        test = [row for row in episodes if str(row["inference_block_id"]) == block]
        if block_index < _MIN_TRAINING_BLOCKS or len(training) < _MIN_TRAINING_EPISODES:
            continue
        selected, selection = _selection(
            grammar=grammar, enumeration=enumeration, programs=programs,
            fields_by_program=fields_by_program, history=history,
            evidence_epoch=blocks[block_index - 1],
        )
        fold_predictions = []
        for program in programs:
            fields = fields_by_program[program.program_id]
            for episode in test:
                forecast = _prediction(training, episode, fields)
                actual = float(episode["estimated_effect"])
                row = {
                    "program_id": program.program_id,
                    "moderator_fields": list(fields),
                    "test_block": block,
                    "episode_sha256": episode["episode_sha256"],
                    "entity_id": episode["entity_id"],
                    "training_episode_count": len(training),
                    **forecast,
                    "actual_effect": actual,
                    "absolute_error": abs(float(forecast["predicted_effect"]) - actual),
                    "direction_correct": (
                        float(forecast["predicted_effect"]) >= 0
                    ) == (actual >= 0),
                }
                fold_predictions.append(row)
                history.append(row)
                if program.program_id == selected:
                    chosen_predictions.append(row)
        fold_body = {
            "test_block": block,
            "training_blocks": blocks[:block_index],
            "training_episode_count": len(training),
            "test_episode_count": len(test),
            "selected_program_id": selected,
            "selected_moderator_fields": list(fields_by_program[selected]),
            "selection_receipt": selection,
            "predictions": fold_predictions,
        }
        folds.append({**fold_body, "fold_sha256": stable_sha256(fold_body)})
    by_program: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in history:
        by_program[str(row["program_id"])].append(row)
    baseline_id = next(
        program.program_id for program in programs if not fields_by_program[program.program_id]
    )
    incumbent = _program_summary(by_program.get(baseline_id, ()))
    chosen = _program_summary(chosen_predictions)
    incumbent_mae = incumbent["mean_absolute_error"]
    chosen_mae = chosen["mean_absolute_error"]
    improvement = (
        (float(incumbent_mae) - float(chosen_mae)) / float(incumbent_mae)
        if incumbent_mae not in (None, 0) and chosen_mae is not None else None
    )
    policy_summary = {
        "incumbent_program_id": baseline_id,
        "incumbent": incumbent,
        "walk_forward_selected_policy": chosen,
        "relative_mae_improvement": improvement,
        "selected_program_sequence": [row["selected_program_id"] for row in folds],
    }
    body = {
        "schema": STRATEGY_WALK_FORWARD_SCHEMA,
        "replay_sha256": replay_sha,
        "evidence_as_of": replay.get("evidence_as_of"),
        "grammar": grammar.to_dict(),
        "enumeration": enumeration.to_dict(),
        "minimum_training_blocks": _MIN_TRAINING_BLOCKS,
        "minimum_training_episodes": _MIN_TRAINING_EPISODES,
        "fold_count": len(folds),
        "scored_episode_count": len(chosen_predictions),
        "folds": folds,
        "program_summaries": [
            {
                "program_id": program.program_id,
                "moderator_fields": list(fields_by_program[program.program_id]),
                **_program_summary(by_program.get(program.program_id, ())),
            }
            for program in programs
        ],
        "policy_summary": policy_summary,
        "status": (
            "typed_policy_outperformed_incumbent_retrospectively"
            if improvement is not None and improvement > 0 else
            "typed_policy_did_not_outperform_incumbent"
            if folds else "insufficient_chronological_blocks"
        ),
        "next_activation": (
            "Freeze this chooser for the next newly settled SEC strategy-event block."
            if folds else "Acquire enough chronologically distinct strategy outcomes."
        ),
        "evidence_use": "retrospective_strategy_forecast_challenge_only",
        "causal_claim": False,
        "security_alpha_claim": False,
        "promotion_eligible": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "tournament_sha256": stable_sha256(body)}


def compile_workspace_strategy_walk_forward(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    source = root / "institutional_learning" / "historical_strategy_event_replay" / "latest.json"
    replay = json.loads(source.read_text(encoding="utf-8"))
    result = compile_strategy_walk_forward(replay)
    destination = source.with_name("walk-forward.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return result


def _dated_prices(points: Iterable[PricePoint], entity_id: str) -> dict[str, PricePoint]:
    rows: dict[str, PricePoint] = {}
    for row in points:
        if row.entity_id != entity_id:
            continue
        current = rows.get(row.date_key)
        if current is None or (row.observed_at, row.observation_id) < (
            current.observed_at, current.observation_id,
        ):
            rows[row.date_key] = row
    return rows


class _SecCoverTableParser(HTMLParser):
    """Collect SEC cover-table cells without depending on filing markup style."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() == "table":
            self._table = []
        elif tag.lower() == "tr" and self._table is not None:
            self._row = []
        elif tag.lower() in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"td", "th"} and self._cell is not None:
            assert self._row is not None
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag.lower() == "tr" and self._row is not None:
            assert self._table is not None
            self._table.append(self._row)
            self._row = None
        elif tag.lower() == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def _cover_table_symbols(html: str) -> set[str]:
    parser = _SecCoverTableParser()
    parser.feed(html)
    symbols: set[str] = set()
    for table in parser.tables:
        symbol_column: int | None = None
        header_width = 0
        for row in table:
            normalized = [re.sub(r"[^a-z]", "", cell.lower()) for cell in row]
            if "tradingsymbols" in normalized or "tradingsymbol" in normalized:
                symbol_column = next(
                    index for index, value in enumerate(normalized)
                    if value in {"tradingsymbol", "tradingsymbols"}
                )
                header_width = len(row)
                continue
            if symbol_column is None or len(row) != header_width:
                continue
            candidate = row[symbol_column].strip(" .,“”‘’'\"").upper()
            if re.fullmatch(r"[A-Z][A-Z0-9.^/-]{0,19}", candidate) and candidate not in {"N/A", "NONE"}:
                symbols.add(candidate)
    return symbols


def extract_filing_trading_symbols(content: bytes) -> list[str]:
    """Read symbols stated by the issuer in one filed document."""
    html = content.decode("utf-8", errors="replace")
    values = re.findall(
        r"<ix:nonNumeric\b[^>]*\bname=[\"']dei:TradingSymbol[\"'][^>]*>"
        r"(.*?)</ix:nonNumeric>",
        html, flags=re.IGNORECASE | re.DOTALL,
    )
    symbols = _cover_table_symbols(html)
    for value in values:
        text = unescape(re.sub(r"<[^>]+>", " ", value)).strip()
        text = text.strip(" “”‘’'\"").upper()
        if re.fullmatch(r"[A-Z0-9.^/-]{1,20}", text):
            symbols.add(text)
    filing_text = " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split())
    for pattern in (
        r"(?:our|the registrant(?:'s|’s)?|(?:the\s+)?company(?:'s|’s)?[\"”']?\)?)\s+"
        r"(?:shares? of )?(?:class [a-z] )?common stock.{0,160}?under\s+the\s+"
        r"(?:new\s+)?(?:ticker\s+)?symbol\s+[\"“']?([A-Z][A-Z0-9.^/-]{0,19})",
        r"(?:our|the registrant(?:'s|’s)?|(?:the\s+)?company(?:'s|’s)?[\"”']?\)?)\s+"
        r"(?:shares? of )?(?:class [a-z] )?common stock.{0,160}?"
        r"(?:NASDAQ|NYSE)\s*:\s*([A-Z][A-Z0-9.^/-]{0,19})",
        r"(?:our|the registrant(?:'s|’s)?|(?:the\s+)?company(?:'s|’s)?[\"”']?\)?)\s+"
        r"(?:shares? of )?(?:class [a-z] )?common stock.{0,300}?"
        r"effective\s+[^.]{0,100}?the\s+symbol\s+changed\s+to\s+"
        r"[\"“']?([A-Z][A-Z0-9.^/-]{0,19})",
    ):
        for value in re.findall(pattern, filing_text, flags=re.IGNORECASE):
            symbols.add(value.upper().rstrip("."))
    return sorted(symbols)


@lru_cache(maxsize=256)
def _periodic_filings(
    root: Path, cik: str,
) -> tuple[tuple[dict[str, str], ...], str]:
    """Read issuer filing chronology from the content-bound SEC archive."""
    receipt = json.loads((
        root / "sources/bulk/sec_submissions/latest.json"
    ).read_text(encoding="utf-8"))
    archive = (root / str(receipt["raw_path"])).resolve()
    archive.relative_to(root)
    main_name = f"CIK{cik}.json"
    with zipfile.ZipFile(archive) as bundle:
        main = json.loads(bundle.read(main_name))
        filing_sets = [((main.get("filings") or {}).get("recent") or {})]
        for row in (main.get("filings") or {}).get("files") or ():
            name = str(row.get("name") or "")
            if name:
                filing_sets.append(json.loads(bundle.read(name)))
    filings = []
    for columns in filing_sets:
        forms = list(columns.get("form") or ())
        for index, form in enumerate(forms):
            accepted = str((columns.get("acceptanceDateTime") or [""] * len(forms))[index])
            accession = str((columns.get("accessionNumber") or [""] * len(forms))[index])
            document = str((columns.get("primaryDocument") or [""] * len(forms))[index])
            if (
                form not in {"10-K", "10-Q", "20-F", "40-F"}
                or not accepted or not accession or not document
            ):
                continue
            filings.append({
                "accepted_at": canonical_timestamp(
                    accepted, "SEC periodic filing accepted_at",
                ),
                "accession_number": accession, "primary_document": document,
            })
    filings.sort(key=lambda row: row["accepted_at"], reverse=True)
    return tuple(filings), str(receipt["receipt_sha256"])


def _periodic_filings_before(
    root: Path, *, cik: str, before: str,
) -> tuple[list[dict[str, str]], str]:
    filings, receipt_sha = _periodic_filings(root, cik)
    cutoff = timestamp_key(before)
    return [
        row for row in filings if timestamp_key(row["accepted_at"]) <= cutoff
    ], receipt_sha


def _pre_event_symbol_evidence(
    root: Path, *, episode: Mapping[str, Any], cik: str,
) -> dict[str, Any]:
    """Find the latest pre-event issuer filing that states a trading symbol."""
    filings, index_sha = _periodic_filings_before(
        root, cik=cik, before=str(episode["available_at"]),
    )
    attempted = []
    for row in filings[:6]:
        filing = fetch_sec_filing_document(
            root,
            source_id=f"sec_{str(episode['entity_id']).lower()}_historical_identity",
            cik=cik, accession_number=row["accession_number"],
            primary_document=row["primary_document"], accepted_at=row["accepted_at"],
        )
        receipt = dict(filing["receipt"])
        symbols = extract_filing_trading_symbols(
            (root / str(receipt["raw_path"])).read_bytes(),
        )
        attempted.append({"filing": filing, "trading_symbols": symbols})
        if symbols:
            break
    body = {
        "schema": "jaggedthoughts-pre-event-security-identity-evidence-v1",
        "identity_parser_version": _SECURITY_IDENTITY_PARSER_VERSION,
        "episode_sha256": episode["episode_sha256"],
        "entity_id": episode["entity_id"],
        "event_available_at": episode["available_at"], "filing_cik": cik,
        "sec_submission_index_receipt_sha256": index_sha,
        "attempted_periodic_filings": attempted,
    }
    return {**body, "evidence_sha256": stable_sha256(body)}


def _workspace_pre_event_symbol_evidence(
    root: Path, replay: Mapping[str, Any], ciks: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    path = (
        root / "institutional_learning/historical_strategy_event_replay"
        / "security-identity-evidence.json"
    )
    prior = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    cached = {}
    changed = False
    for row in prior.get("episodes") or ():
        body = dict(row)
        declared = str(body.pop("evidence_sha256", ""))
        if declared != stable_sha256(body):
            continue
        current = dict(row)
        if row.get("identity_parser_version") != _SECURITY_IDENTITY_PARSER_VERSION:
            attempts = []
            for attempted in row.get("attempted_periodic_filings") or ():
                filing = dict(attempted.get("filing") or {})
                receipt = dict(filing.get("receipt") or {})
                content = (root / str(receipt.get("raw_path") or "")).read_bytes()
                if hashlib.sha256(content).hexdigest() != receipt.get("content_sha256"):
                    raise ValueError("cached SEC identity document hash mismatch")
                symbols = extract_filing_trading_symbols(content)
                attempts.append({"filing": filing, "trading_symbols": symbols})
                if symbols:
                    break
            body["identity_parser_version"] = _SECURITY_IDENTITY_PARSER_VERSION
            body["attempted_periodic_filings"] = attempts
            current = {**body, "evidence_sha256": stable_sha256(body)}
            changed = True
        cached[str(row.get("episode_sha256"))] = current
    for episode in replay.get("episodes") or ():
        episode_sha = str(episode["episode_sha256"])
        entity_id = str(episode["entity_id"])
        if episode_sha in cached or entity_id not in ciks:
            continue
        try:
            cached[episode_sha] = _pre_event_symbol_evidence(
                root, episode=episode, cik=ciks[entity_id],
            )
            changed = True
        except (KeyError, OSError, ValueError, zipfile.BadZipFile):
            continue
    if changed:
        body = {
            "schema": "jaggedthoughts-pre-event-security-identity-evidence-book-v1",
            "identity_parser_version": _SECURITY_IDENTITY_PARSER_VERSION,
            "episodes": [cached[key] for key in sorted(cached)],
        }
        payload = {**body, "evidence_book_sha256": stable_sha256(body)}
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        temporary.replace(path)
    return cached


def _workspace_security_identity_receipts(
    root: Path, replay: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    manifest = load_source_manifest(root / "sources.yaml")
    sources = [dict(row) for row in manifest.get("sources") or ()]
    ciks = {
        str(source["entity_id"]): str(source.get("cik") or "").zfill(10)
        for source in sources
        if source.get("entity_id")
        and source.get("adapter") in {"sec_companyfacts", "sec_submissions"}
    }
    needs_pre_event = []
    for episode in replay.get("episodes") or ():
        filing = dict(episode.get("filing_source_receipt") or {})
        path = (root / str(filing.get("raw_path") or "")).resolve()
        try:
            path.relative_to(root)
            content = path.read_bytes()
        except (OSError, ValueError):
            continue
        if (
            hashlib.sha256(content).hexdigest() == filing.get("content_sha256")
            and not extract_filing_trading_symbols(content)
        ):
            needs_pre_event.append(episode)
    pre_event_evidence = _workspace_pre_event_symbol_evidence(
        root, {"episodes": needs_pre_event}, ciks,
    )
    receipts: dict[str, dict[str, Any]] = {}
    for episode in replay.get("episodes") or ():
        episode_sha = str(episode["episode_sha256"])
        entity_id = str(episode["entity_id"])
        filing = dict(episode.get("filing_source_receipt") or {})
        path = (root / str(filing.get("raw_path") or "")).resolve()
        try:
            path.relative_to(root)
            content = path.read_bytes()
        except (OSError, ValueError):
            content = b""
        content_sha = hashlib.sha256(content).hexdigest() if content else ""
        url = str(filing.get("canonical_url") or "")
        cik_match = re.search(r"/Archives/edgar/data/(\d+)/", url, flags=re.IGNORECASE)
        filing_cik = cik_match.group(1).zfill(10) if cik_match else ""
        sec_ciks = sorted({
            str(source.get("cik") or "").zfill(10)
            for source in sources
            if source.get("entity_id") == entity_id
            and source.get("adapter") in {"sec_companyfacts", "sec_submissions"}
        })
        market_symbols = sorted({
            str(source.get("symbol") or "").upper()
            for source in sources
            if source.get("entity_id") == entity_id
            and source.get("adapter") == "yahoo_chart_daily"
        })
        filing_symbols = extract_filing_trading_symbols(content) if content else []
        pre_event = dict(pre_event_evidence.get(episode_sha) or {})
        pre_event_filing = None
        if (
            not filing_symbols and content_sha == str(filing.get("content_sha256") or "")
            and filing_cik and filing_cik in sec_ciks
        ):
            attempts = list(pre_event.get("attempted_periodic_filings") or ())
            candidate = dict(attempts[-1]) if attempts else {}
            candidate_filing = dict(candidate.get("filing") or {})
            candidate_receipt = dict(candidate_filing.get("receipt") or {})
            candidate_path = (root / str(candidate_receipt.get("raw_path") or "")).resolve()
            try:
                candidate_path.relative_to(root)
                candidate_content = candidate_path.read_bytes()
            except (OSError, ValueError):
                candidate_content = b""
            candidate_body = dict(candidate_filing)
            candidate_declared = str(candidate_body.pop("filing_document_sha256", ""))
            extracted = (
                extract_filing_trading_symbols(candidate_content)
                if candidate_content else []
            )
            if (
                candidate_declared == stable_sha256(candidate_body)
                and hashlib.sha256(candidate_content).hexdigest()
                == candidate_receipt.get("content_sha256")
                and extracted == candidate.get("trading_symbols")
                and timestamp_key(str(candidate_filing.get("accepted_at")))
                <= timestamp_key(str(episode["available_at"]))
                and pre_event.get("filing_cik") == filing_cik
                and pre_event.get("entity_id") == entity_id
            ):
                filing_symbols = extracted
                pre_event_filing = candidate_filing
        reasons = []
        if content_sha != str(filing.get("content_sha256") or ""):
            reasons.append("filing_document_hash_mismatch")
        if not filing_cik or filing_cik not in sec_ciks:
            reasons.append("filing_cik_not_bound_to_configured_sec_entity")
        if not filing_symbols:
            reasons.append("filing_trading_symbol_unavailable")
        if len(market_symbols) != 1 or not set(filing_symbols).intersection(market_symbols):
            reasons.append("filing_symbol_not_bound_to_configured_market_series")
        status = (
            "exact_pre_event_filing_symbol_match"
            if not reasons and pre_event_filing else
            "exact_filing_symbol_match" if not reasons else "excluded"
        )
        body = {
            "schema": "jaggedthoughts-historical-security-identity-receipt-v1",
            "episode_sha256": episode_sha,
            "entity_id": entity_id,
            "filing_cik": filing_cik,
            "configured_sec_ciks": sec_ciks,
            "filing_trading_symbols": filing_symbols,
            "configured_market_symbols": market_symbols,
            "filing_content_sha256": content_sha,
            "pre_event_symbol_filing": pre_event_filing,
            "status": status,
            "reasons": reasons,
        }
        receipts[episode_sha] = {
            **body, "identity_receipt_sha256": stable_sha256(body),
        }
    return receipts


def _identity_surface_sha256(
    receipts: Mapping[str, Mapping[str, Any]] | None,
) -> str:
    return stable_sha256({
        "identity_receipts": {
            key: dict(receipts[key]) for key in sorted(receipts or {})
        },
    })


def _security_outcomes(
    replay: Mapping[str, Any], points: Iterable[PricePoint], *,
    benchmark_id: str, horizon_days: int, entry_lag_sessions: int,
    round_trip_cost_bps: float,
    identity_receipts: Mapping[str, Mapping[str, Any]] | None = None,
    factor_definitions: Iterable[FactorDefinition] = (),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    point_rows = tuple(points)
    factors = tuple(factor_definitions)
    point_evidence_as_of = max(
        (point.available_at for point in point_rows), default="1970-01-01T00:00:00Z",
    )
    by_entity = {
        entity_id: _dated_prices(point_rows, entity_id)
        for entity_id in {
            benchmark_id,
            *(str(row["entity_id"]) for row in replay.get("episodes") or ()),
        }
    }
    outcomes, gaps = [], []
    for episode in replay.get("episodes") or ():
        entity_id = str(episode["entity_id"])
        identity = (
            identity_receipts.get(str(episode["episode_sha256"]))
            if identity_receipts is not None else None
        )
        if identity_receipts is not None and (
            not isinstance(identity, Mapping)
            or identity.get("status") not in {
                "exact_filing_symbol_match", "exact_pre_event_filing_symbol_match",
            }
        ):
            gaps.append({
                "episode_sha256": episode["episode_sha256"],
                "entity_id": entity_id,
                "reason": "historical_security_identity_unresolved",
                "identity_receipt": dict(identity or {}),
            })
            continue
        event_time = timestamp_key(str(episode["available_at"]))
        common = sorted(set(by_entity.get(entity_id, ())) & set(by_entity.get(benchmark_id, ())))
        eligible_entry_dates = [
            day for day in common
            if timestamp_key(by_entity[entity_id][day].observed_at) > event_time
            and timestamp_key(by_entity[benchmark_id][day].observed_at) > event_time
        ]
        if len(eligible_entry_dates) <= entry_lag_sessions:
            gaps.append({
                "episode_sha256": episode["episode_sha256"],
                "entity_id": entity_id, "reason": "entry_price_unavailable",
            })
            continue
        entry_day = eligible_entry_dates[entry_lag_sessions]
        entry = by_entity[entity_id][entry_day]
        benchmark_entry = by_entity[benchmark_id][entry_day]
        target = (
            datetime.fromisoformat(entry.observed_at.replace("Z", "+00:00"))
            + timedelta(days=horizon_days)
        )
        exit_dates = [
            day for day in common
            if datetime.fromisoformat(
                by_entity[entity_id][day].observed_at.replace("Z", "+00:00")
            ) >= target
        ]
        if not exit_dates:
            gaps.append({
                "episode_sha256": episode["episode_sha256"],
                "entity_id": entity_id, "reason": "exit_price_unavailable",
            })
            continue
        exit_day = exit_dates[0]
        exit_point = by_entity[entity_id][exit_day]
        benchmark_exit = by_entity[benchmark_id][exit_day]
        asset_return = exit_point.value / entry.value - 1.0
        benchmark_return = benchmark_exit.value / benchmark_entry.value - 1.0
        cost = round_trip_cost_bps / 10_000.0
        active_return = asset_return - benchmark_return - cost
        active_log_return = (
            math.log(exit_point.value / entry.value)
            - math.log(benchmark_exit.value / benchmark_entry.value)
            - cost
        )
        factor_control = None
        if factors:
            try:
                factor_control = compile_historical_factor_control(
                    analysis_id=f"strategy-event:{episode['episode_sha256']}",
                    candidate_entity_id=entity_id,
                    factors=factors, price_points=point_rows,
                    evidence_as_of=point_evidence_as_of,
                    calibration_end=str(episode["available_at"]),
                    settlement_start=entry.observed_at,
                    settlement_end=exit_point.observed_at,
                    round_trip_cost_bps=round_trip_cost_bps,
                )
            except (InsufficientFactorHistoryError, ValueError) as error:
                gaps.append({
                    "episode_sha256": episode["episode_sha256"],
                    "entity_id": entity_id,
                    "reason": "historical_factor_control_unavailable",
                    "detail": str(error),
                })
                continue
        target_return = (
            float(factor_control["realized"]["factor_controlled_log_return_after_cost"])
            if factor_control else active_log_return
        )
        body = {
            "schema": "jaggedthoughts-historical-strategy-security-outcome-v1",
            "episode_sha256": episode["episode_sha256"],
            "entity_id": entity_id,
            "inference_block_id": f"event-year:{str(episode['available_at'])[:4]}",
            "event_available_at": episode["available_at"],
            "implementation_mode": episode["implementation_mode"],
            "transaction_phenotype": episode["transaction_phenotype"],
            "business_outcome_effect": episode["estimated_effect"],
            "entry": {
                "observed_at": entry.observed_at,
                "entity_observation_id": entry.observation_id,
                "benchmark_observation_id": benchmark_entry.observation_id,
            },
            "exit": {
                "observed_at": exit_point.observed_at,
                "entity_observation_id": exit_point.observation_id,
                "benchmark_observation_id": benchmark_exit.observation_id,
            },
            "asset_return": asset_return,
            "benchmark_return": benchmark_return,
            "active_simple_return_after_cost": active_return,
            "benchmark_active_log_return_after_cost": active_log_return,
            "estimated_effect": target_return,
            "target_metric_id": (
                "factor_controlled_log_return_after_cost"
                if factor_control else "benchmark_active_log_return_after_cost"
            ),
            "factor_control": factor_control,
            "source_refs": sorted({
                entry.source_ref, exit_point.source_ref,
                benchmark_entry.source_ref, benchmark_exit.source_ref,
            }),
            "security_identity_receipt": dict(identity or {
                "status": "caller_supplied_entity_series",
            }),
        }
        outcomes.append({**body, "security_outcome_sha256": stable_sha256(body)})
    admitted = []
    by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in outcomes:
        by_entity[str(row["entity_id"])].append(row)
    for entity_id, rows in by_entity.items():
        ordered = sorted(rows, key=lambda row: row["entry"]["observed_at"])
        clusters: list[list[dict[str, Any]]] = []
        for row in ordered:
            if (
                not clusters
                or timestamp_key(str(row["entry"]["observed_at"]))
                > max(timestamp_key(str(item["exit"]["observed_at"])) for item in clusters[-1])
            ):
                clusters.append([row])
            else:
                clusters[-1].append(row)
        for cluster in clusters:
            if len(cluster) == 1:
                admitted.extend(cluster)
                continue
            gaps.append({
                "entity_id": entity_id,
                "reason": "overlapping_strategy_events_require_bundle_representation",
                "episode_sha256s": [row["episode_sha256"] for row in cluster],
                "entry_start": min(row["entry"]["observed_at"] for row in cluster),
                "exit_end": max(row["exit"]["observed_at"] for row in cluster),
            })
    return admitted, gaps


def _security_summary(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    values = list(rows)
    summary = _program_summary(values)
    invested = [row for row in values if float(row["predicted_effect"]) > 0]
    return {
        **summary,
        "paper_exposure_rate": len(invested) / len(values) if values else None,
        "mean_active_return_after_cost": (
            mean(float(row["actual_simple_active_return"]) for row in invested)
            if invested else 0.0
        ),
        "mean_book_active_return_after_cost": (
            mean(
                float(row["actual_simple_active_return"])
                if float(row["predicted_effect"]) > 0 else 0.0
                for row in values
            ) if values else None
        ),
    }


def _security_independence_receipt(
    outcomes: Iterable[Mapping[str, Any]], scored_episode_sha256s: set[str],
) -> dict[str, Any]:
    """Retain connected overlap components as a dependence diagnostic."""
    scored = [
        row for row in outcomes
        if str(row["episode_sha256"]) in scored_episode_sha256s
    ]
    cluster_ids = overlap_cluster_ids([{
        "run_id": row["security_outcome_sha256"],
        "return_window_binding": {"entry_observed_at": row["entry"]["observed_at"]},
        "return_window_settlement": {"exit_observed_at": row["exit"]["observed_at"]},
    } for row in scored])
    windows = [{
        "episode_sha256": row["episode_sha256"],
        "security_outcome_sha256": row["security_outcome_sha256"],
        "entry_observed_at": row["entry"]["observed_at"],
        "exit_observed_at": row["exit"]["observed_at"],
        "inference_block_id": cluster_ids[row["security_outcome_sha256"]],
    } for row in sorted(scored, key=lambda item: (
        item["entry"]["observed_at"], item["security_outcome_sha256"],
    ))]
    body = {
        "schema": "jaggedthoughts-strategy-security-independence-receipt-v1",
        "block_identity": "connected_components_of_overlapping_tradable_return_windows",
        "scored_window_count": len(windows),
        "independent_block_count": len(set(cluster_ids.values())),
        "count_is_inference_sample_size": False,
        "interpretation": (
            "Transitive overlap components diagnose shared market time but do not estimate "
            "effective sample size."
        ),
        "windows": windows,
    }
    return {**body, "independence_receipt_sha256": stable_sha256(body)}


def _security_dependence_adjusted_inference(
    folds: Iterable[Mapping[str, Any]], *, baseline_program_id: str,
    horizon_days: int,
) -> dict[str, Any]:
    """Estimate paired policy deltas with calendar-cohort Newey-West errors."""
    paired = []
    for fold in folds:
        predictions = list(fold.get("predictions") or ())
        by_key = {
            (str(row["program_id"]), str(row["episode_sha256"])): row
            for row in predictions
        }
        selected_id = str(fold["selected_program_id"])
        for row in predictions:
            if str(row["program_id"]) != selected_id:
                continue
            baseline = by_key[(baseline_program_id, str(row["episode_sha256"]))]
            actual_return = float(row["actual_simple_active_return"])
            body = {
                "test_block": str(fold["test_block"]),
                "episode_sha256": str(row["episode_sha256"]),
                "forecast_absolute_error_advantage": (
                    float(baseline["absolute_error"]) - float(row["absolute_error"])
                ),
                "paper_return_increment_after_cost": (
                    actual_return * (float(row["predicted_effect"]) > 0)
                    - actual_return * (float(baseline["predicted_effect"]) > 0)
                ),
            }
            paired.append({**body, "paired_delta_sha256": stable_sha256(body)})

    cohort_ids = sorted({str(row["test_block"]) for row in paired})
    cohort_years = {cohort: int(cohort.rsplit(":", 1)[-1]) for cohort in cohort_ids}
    max_lag = min(
        max(1, math.ceil(horizon_days / 365)),
        max(0, len(cohort_ids) - 1),
    )

    def estimate(field: str) -> dict[str, Any]:
        values = [float(row[field]) for row in paired]
        if not values:
            return {"mean": None, "standard_error": None, "confidence_interval_95": None}
        center = mean(values)
        observed_scores = {
            cohort_years[cohort]: sum(
                float(row[field]) - center
                for row in paired if str(row["test_block"]) == cohort
            )
            for cohort in cohort_ids
        }
        years = range(min(observed_scores), max(observed_scores) + 1)
        scores = {year: observed_scores.get(year, 0.0) for year in years}
        covariance = sum(score * score for score in scores.values())
        for lag in range(1, max_lag + 1):
            weight = 1.0 - lag / (max_lag + 1.0)
            covariance += 2.0 * weight * sum(
                scores[year] * scores.get(year - lag, 0.0) for year in scores
            )
        finite_sample = len(cohort_ids) / max(1, len(cohort_ids) - 1)
        standard_error = math.sqrt(max(0.0, covariance) * finite_sample) / len(values)
        return {
            "mean": center,
            "standard_error": standard_error,
            "confidence_interval_95": [
                center - 1.96 * standard_error,
                center + 1.96 * standard_error,
            ],
        }

    body = {
        "schema": "jaggedthoughts-strategy-security-dependence-adjusted-inference-v1",
        "design": "purged_expanding_window_with_calendar_cohort_newey_west",
        "training_purge_rule": "training_return_exit_strictly_precedes_test_issue_cutoff",
        "post_test_embargo": "not_applicable_to_past_only_expanding_training",
        "cohort_identity": "event_year_of_source_available_strategy_event",
        "calendar_cohort_count": len(cohort_ids),
        "minimum_calendar_cohorts": _MIN_SECURITY_CALENDAR_COHORTS,
        "newey_west_lag_calendar_cohorts": max_lag,
        "method_references": [
            "https://doi.org/10.3386/t0055",
            "https://doi.org/10.1086/260910",
        ],
        "scored_pair_count": len(paired),
        "forecast_absolute_error_advantage": estimate(
            "forecast_absolute_error_advantage"
        ),
        "paper_return_increment_after_cost": estimate(
            "paper_return_increment_after_cost"
        ),
        "paired_deltas": paired,
        "interpretation_eligible": len(cohort_ids) >= _MIN_SECURITY_CALENDAR_COHORTS,
        "boundary": (
            "HAC adjusts overlapping-horizon serial dependence; it does not remove common shocks, "
            "post-selection design risk, survivorship, or current-retrieval-vintage limitations."
        ),
    }
    return {**body, "inference_receipt_sha256": stable_sha256(body)}


def compile_strategy_security_walk_forward(
    replay: Mapping[str, Any], points: Iterable[PricePoint], *,
    price_source_run_sha256: str, evidence_as_of: str,
    benchmark_id: str = "SPY", horizon_days: int = 365,
    entry_lag_sessions: int = 2, round_trip_cost_bps: float = 20.0,
    identity_receipts: Mapping[str, Mapping[str, Any]] | None = None,
    factor_definitions: Iterable[FactorDefinition] = (),
) -> dict[str, Any]:
    """Test whether typed strategy moves predict later benchmark-relative returns."""
    if replay.get("schema") != HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA:
        raise ValueError("strategy-security walk-forward requires a historical strategy replay")
    replay_sha = _checked(replay, "replay_sha256", "historical strategy replay")
    if horizon_days < 30 or not 1 <= entry_lag_sessions <= 20 or round_trip_cost_bps < 0:
        raise ValueError("invalid strategy-security execution contract")
    epoch = canonical_timestamp(evidence_as_of, "strategy-security evidence_as_of")
    factors = tuple(factor_definitions)
    outcomes, gaps = _security_outcomes(
        replay, points, benchmark_id=benchmark_id, horizon_days=horizon_days,
        entry_lag_sessions=entry_lag_sessions,
        round_trip_cost_bps=round_trip_cost_bps,
        identity_receipts=identity_receipts,
        factor_definitions=factors,
    )
    blocks = sorted({str(row["inference_block_id"]) for row in outcomes})
    grammar, programs, fields_by_program = enumerate_historical_strategy_moderator_programs()
    enumeration = compile_enumeration_result(
        grammar, programs=programs,
        max_depth=len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
        max_programs=2 ** len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
    )
    history: list[dict[str, Any]] = []
    folds, chosen_predictions = [], []
    for block in blocks:
        test = [row for row in outcomes if row["inference_block_id"] == block]
        issue_cutoff = min(timestamp_key(str(row["event_available_at"])) for row in test)
        training = [
            row for row in outcomes
            if timestamp_key(str(row["exit"]["observed_at"])) < issue_cutoff
        ]
        training_blocks = sorted({str(row["inference_block_id"]) for row in training})
        if len(training_blocks) < _MIN_TRAINING_BLOCKS or len(training) < _MIN_TRAINING_EPISODES:
            continue
        selected, selection = _selection(
            grammar=grammar, enumeration=enumeration, programs=programs,
            fields_by_program=fields_by_program, history=history,
            evidence_epoch=max(training_blocks),
            target_type="historical_strategy_projection",
            evaluation_model_id=(
                "expanding_window_median_factor_controlled_return_v1"
                if factors else "expanding_window_median_active_return_v1"
            ),
            representation_audit_id="historical-strategy-security-walk-forward-representation",
            representation_residuals=(
                "transaction_classifier_was_designed_after_part_of_the_sample",
                "current_retrieval_prices_are_not_historical_information_vintages",
                "filing_symbol_matches_do_not_supply_archived_price_vintages",
                "declared_traded_factor_proxies_do_not_remove_all_event_confounding",
                "overlapping_move_bundles_are_excluded_until_the_grammar_represents_them",
            ),
        )
        predictions = []
        for program in programs:
            fields = fields_by_program[program.program_id]
            for outcome in test:
                forecast = _prediction(training, outcome, fields)
                actual = float(outcome["estimated_effect"])
                row = {
                    "program_id": program.program_id,
                    "moderator_fields": list(fields),
                    "test_block": block,
                    "episode_sha256": outcome["episode_sha256"],
                    "security_outcome_sha256": outcome["security_outcome_sha256"],
                    "entity_id": outcome["entity_id"],
                    "training_episode_count": len(training),
                    **forecast,
                    "actual_effect": actual,
                    "actual_simple_active_return": outcome[
                        "active_simple_return_after_cost"
                    ],
                    "absolute_error": abs(float(forecast["predicted_effect"]) - actual),
                    "direction_correct": (float(forecast["predicted_effect"]) >= 0) == (actual >= 0),
                }
                predictions.append(row)
                history.append(row)
                if program.program_id == selected:
                    chosen_predictions.append(row)
        fold_body = {
            "test_block": block,
            "issue_cutoff": issue_cutoff.isoformat().replace("+00:00", "Z"),
            "training_latest_exit_at": max(
                str(row["exit"]["observed_at"]) for row in training
            ),
            "training_purge_rule_satisfied": all(
                timestamp_key(str(row["exit"]["observed_at"])) < issue_cutoff
                for row in training
            ),
            "training_blocks": training_blocks,
            "training_episode_count": len(training),
            "test_episode_count": len(test),
            "selected_program_id": selected,
            "selected_moderator_fields": list(fields_by_program[selected]),
            "selection_receipt": selection,
            "predictions": predictions,
        }
        folds.append({**fold_body, "fold_sha256": stable_sha256(fold_body)})
    by_program: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in history:
        by_program[str(row["program_id"])].append(row)
    baseline_id = next(
        program.program_id for program in programs if not fields_by_program[program.program_id]
    )
    incumbent = _security_summary(by_program.get(baseline_id, ()))
    chosen = _security_summary(chosen_predictions)
    incumbent_mae, chosen_mae = incumbent["mean_absolute_error"], chosen["mean_absolute_error"]
    relative_mae_improvement = (
        (float(incumbent_mae) - float(chosen_mae)) / float(incumbent_mae)
        if incumbent_mae not in (None, 0) and chosen_mae is not None else None
    )
    economic_increment = (
        float(chosen["mean_book_active_return_after_cost"])
        - float(incumbent["mean_book_active_return_after_cost"])
        if chosen["mean_book_active_return_after_cost"] is not None
        and incumbent["mean_book_active_return_after_cost"] is not None else None
    )
    point_estimate_supports_challenger = bool(
        relative_mae_improvement is not None and relative_mae_improvement > 0
        and economic_increment is not None and economic_increment > 0
    )
    independence = _security_independence_receipt(
        outcomes, {str(row["episode_sha256"]) for row in chosen_predictions},
    )
    independent_block_count = int(independence["independent_block_count"])
    dependence_adjusted = _security_dependence_adjusted_inference(
        folds, baseline_program_id=baseline_id, horizon_days=horizon_days,
    )
    inference_block_count = int(dependence_adjusted["calendar_cohort_count"])
    inference_sufficient = bool(dependence_adjusted["interpretation_eligible"])
    forecast_interval = (
        dependence_adjusted["forecast_absolute_error_advantage"]
        ["confidence_interval_95"]
    )
    return_interval = (
        dependence_adjusted["paper_return_increment_after_cost"]
        ["confidence_interval_95"]
    )
    dependence_adjusted_supports_challenger = bool(
        inference_sufficient
        and forecast_interval and float(forecast_interval[0]) > 0
        and return_interval and float(return_interval[0]) > 0
    )
    body = {
        "schema": STRATEGY_SECURITY_WALK_FORWARD_SCHEMA,
        "compiler_version": _SECURITY_COMPILER_VERSION,
        "replay_sha256": replay_sha,
        "price_source_run_sha256": price_source_run_sha256,
        "identity_surface_sha256": _identity_surface_sha256(identity_receipts),
        "evidence_as_of": epoch,
        "benchmark_id": benchmark_id,
        "execution_contract": {
            "price_metric_id": "adjusted_price",
            "entry_lag_sessions": entry_lag_sessions,
            "horizon_days": horizon_days,
            "round_trip_cost_bps": round_trip_cost_bps,
            "return_target": (
                "pre_event_factor_controlled_log_return_after_cost"
                if factors else "benchmark_active_log_return_after_cost"
            ),
            "factor_definitions": [factor.to_dict() for factor in factors],
            "factor_basis_sha256": stable_sha256([
                factor.to_dict() for factor in factors
            ]),
        },
        "security_identity_contract": {
            "required_statuses": (
                ["exact_filing_symbol_match", "exact_pre_event_filing_symbol_match"]
                if identity_receipts is not None else ["caller_supplied_entity_series"]
            ),
            "filing_cik_match_required": identity_receipts is not None,
            "filing_trading_symbol_match_required": identity_receipts is not None,
        },
        "enumeration": enumeration.to_dict(),
        "eligible_security_outcome_count": len(outcomes),
        "coverage_gap_count": len(gaps),
        "excluded_episode_count": sum(
            len(row.get("episode_sha256s") or [row.get("episode_sha256")])
            for row in gaps
        ),
        "coverage_gaps": gaps,
        "security_outcomes": outcomes,
        "fold_count": len(folds),
        "independent_block_count": independent_block_count,
        "minimum_independent_blocks": _MIN_SECURITY_CALENDAR_COHORTS,
        "statistical_independence": independence,
        "dependence_adjusted_inference": dependence_adjusted,
        "inference_block_count": inference_block_count,
        "minimum_inference_blocks": _MIN_SECURITY_CALENDAR_COHORTS,
        "inference_sufficient": inference_sufficient,
        "scored_episode_count": len(chosen_predictions),
        "folds": folds,
        "program_summaries": [{
            "program_id": program.program_id,
            "moderator_fields": list(fields_by_program[program.program_id]),
            **_security_summary(by_program.get(program.program_id, ())),
        } for program in programs],
        "policy_summary": {
            "incumbent_program_id": baseline_id,
            "incumbent": incumbent,
            "walk_forward_selected_policy": chosen,
            "relative_mae_improvement": relative_mae_improvement,
            "mean_book_active_return_increment_after_cost": economic_increment,
            "point_estimate_supports_challenger": point_estimate_supports_challenger,
            "dependence_adjusted_supports_challenger": (
                dependence_adjusted_supports_challenger
            ),
            "selected_program_sequence": [row["selected_program_id"] for row in folds],
        },
        "status": (
            "insufficient_calendar_cohorts"
            if not inference_sufficient else
            "typed_policy_outperformed_forecast_and_economic_controls_retrospectively"
            if dependence_adjusted_supports_challenger
            else "typed_policy_did_not_clear_both_controls"
        ),
        "next_activation": (
            "Retain as a challenger in prospective strategy-alpha blocks; no historical promotion."
            if inference_sufficient and point_estimate_supports_challenger else
            "Acquire more prospective calendar cohorts and recompute dependence-adjusted uncertainty."
        ),
        "evidence_boundary": (
            "SEC event times precede every simulated entry, filing CIK and filing-era trading "
            "symbols bind each admitted issuer series, and training outcomes precede each test "
            "block; price histories remain current retrievals rather than archived issue-time vintages."
        ),
        "security_alpha_claim": False,
        "promotion_eligible": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "tournament_sha256": stable_sha256(body)}


def compile_workspace_strategy_security_walk_forward(
    workspace: str | Path,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    replay = json.loads((
        root / "institutional_learning" / "historical_strategy_event_replay" / "latest.json"
    ).read_text(encoding="utf-8"))
    identity_receipts = _workspace_security_identity_receipts(root, replay)
    identity_surface_sha = _identity_surface_sha256(identity_receipts)
    factor_profile = yaml.safe_load((
        root / "watchlists" / "public_equity_etf_opportunities.yaml"
    ).read_text(encoding="utf-8"))
    factors = tuple(
        FactorDefinition.from_dict(row)
        for row in (factor_profile.get("factors") or ())
    )
    factor_basis_sha = stable_sha256([factor.to_dict() for factor in factors])
    source_run = json.loads((root / "data" / "latest_source_run.json").read_text(encoding="utf-8"))
    source_run_sha = str(source_run["run_sha256"])
    destination = (
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "security-walk-forward.json"
    )
    if destination.is_file():
        cached = json.loads(destination.read_text(encoding="utf-8"))
        if (
            cached.get("replay_sha256") == replay.get("replay_sha256")
            and cached.get("price_source_run_sha256") == source_run_sha
            and cached.get("compiler_version") == _SECURITY_COMPILER_VERSION
            and cached.get("identity_surface_sha256") == identity_surface_sha
            and (cached.get("execution_contract") or {}).get("factor_basis_sha256")
            == factor_basis_sha
        ):
            return cached
    entities = {
        str(row["entity_id"]) for row in replay.get("episodes") or ()
    } | {"SPY"} | {
        entity_id for factor in factors
        for entity_id in (factor.long_entity_id, factor.short_entity_id)
        if entity_id
    }
    points = load_price_points(
        root / "data" / "observations.csv", as_of=str(source_run["as_of"]),
        metric_id="adjusted_price", entity_ids=entities,
    )
    result = compile_strategy_security_walk_forward(
        replay, points, price_source_run_sha256=source_run_sha,
        evidence_as_of=str(source_run["as_of"]),
        identity_receipts=identity_receipts,
        factor_definitions=factors,
    )
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return result


__all__ = [
    "STRATEGY_SECURITY_WALK_FORWARD_SCHEMA",
    "STRATEGY_WALK_FORWARD_SCHEMA",
    "compile_strategy_security_walk_forward",
    "compile_strategy_walk_forward",
    "compile_workspace_strategy_security_walk_forward",
    "compile_workspace_strategy_walk_forward",
    "extract_filing_trading_symbols",
]
