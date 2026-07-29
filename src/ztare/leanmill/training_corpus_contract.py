"""Authority check for LeanMill training-corpus consumers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


STRICT_TRAINING_AUTHORITY = "strict_forward"
TRAINING_CORPUS_VALIDATION_SCHEMA = "leanmill.training_corpus_validation.v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _validate_training_row(name: str, row: dict, line_number: int) -> None:
    where = f"{name}:{line_number}"
    if row.get("authority") != STRICT_TRAINING_AUTHORITY:
        raise ValueError(f"non-strict training row in {where}")
    if name == "prover_corpus.jsonl":
        for field in (
            "target",
            "statement",
            "proof",
            "recompilable_probe",
            "job_id",
            "run_tag",
            "goal_sha256",
            "proof_sha256",
            "recompilable_probe_sha256",
        ):
            if not str(row.get(field) or "").strip():
                raise ValueError(f"strict prover row lacks {field} in {where}")
        if _sha256_text(str(row["proof"])) != row["proof_sha256"]:
            raise ValueError(f"strict prover proof hash mismatch in {where}")
        if _sha256_text(str(row["recompilable_probe"])) != row[
            "recompilable_probe_sha256"
        ]:
            raise ValueError(f"strict prover probe hash mismatch in {where}")
        try:
            from ztare.leanmill.lean_source import extract_signature

            signature = extract_signature(
                str(row["recompilable_probe"]), str(row["target"])
            ).strip()
        except Exception as exc:  # noqa: BLE001 - consumer validation is fail-closed
            raise ValueError(
                f"strict prover target identity cannot be replayed in {where}"
            ) from exc
        if not signature or signature != str(row["statement"]).strip():
            raise ValueError(f"strict prover target statement mismatch in {where}")
        if _sha256_text(signature) != row["goal_sha256"]:
            raise ValueError(f"strict prover goal hash mismatch in {where}")
    elif name == "faithfulness_discriminator_corpus.jsonl":
        from ztare.leanmill.solver.no_good_store import (
            validate_integrity_artifact_binding,
            validate_integrity_rejection_provenance,
        )

        binding = row.get("artifact_binding")
        if reason := validate_integrity_artifact_binding(binding):
            raise ValueError(f"invalid altered-artifact binding in {where}: {reason}")
        if reason := validate_integrity_rejection_provenance(
            row.get("integrity_provenance"),
            binding=binding,
            source=str(row.get("source") or ""),
            witness=str(row.get("witness") or ""),
        ):
            raise ValueError(
                f"invalid altered-artifact provenance in {where}: {reason}"
            )
        if str(row.get("statement") or "").strip() != str(
            binding["altered_probe"]
        ).strip():
            raise ValueError(f"discriminator labels the wrong artifact in {where}")
        expected = {
            "target_statement": binding["altered_target_signature"],
            "target_name": binding["altered_target_identity"],
            "posed_probe_sha256": binding["posed_probe_sha256"],
            "altered_probe_sha256": binding["altered_probe_sha256"],
            "artifact_binding_receipt_sha256": binding["receipt_sha256"],
        }
        for field, value in expected.items():
            if row.get(field) != value:
                raise ValueError(f"discriminator {field} mismatch in {where}")
        if row.get("label") != "unfaithful":
            raise ValueError(f"invalid discriminator label in {where}")
    elif name == "autoformalization_corpus.jsonl":
        for field in (
            "nl",
            "lean_statement",
            "source",
            "statement_id",
            "verdict_provenance",
        ):
            if not row.get(field):
                raise ValueError(f"strict autoformalization row lacks {field} in {where}")
        if row.get("evidence_tier") not in {"reviewed", "certified"}:
            raise ValueError(f"invalid autoformalization evidence tier in {where}")
    elif name == "falsification_corpus.jsonl":
        for field in ("statement", "refutation", "source", "statement_id"):
            if not row.get(field):
                raise ValueError(f"strict falsification row lacks {field} in {where}")


def validate_training_corpus_directory(
    corpus_dir: str | Path,
    *,
    required_files: Iterable[str],
    allow_legacy_diagnostic: bool = False,
) -> dict:
    """Validate the manifest, file bytes, and row authority before consumption."""
    directory = Path(corpus_dir)
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        if allow_legacy_diagnostic:
            return {"authority": "legacy_diagnostic", "manifest": "missing"}
        raise ValueError("training corpus has no authority manifest")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("training corpus authority manifest is unreadable") from exc
    authority = str(manifest.get("authority") or "")
    if authority != STRICT_TRAINING_AUTHORITY:
        if allow_legacy_diagnostic:
            return {**manifest, "authority": "legacy_diagnostic"}
        raise ValueError(
            "training corpus is legacy or unlabelled; pass the explicit diagnostic override"
        )
    expected_hashes = manifest.get("corpus_sha256s")
    if not isinstance(expected_hashes, dict):
        raise ValueError("strict training corpus lacks content hashes")
    row_counts: dict[str, int] = {}
    for name in required_files:
        path = directory / str(name)
        if not path.is_file() or expected_hashes.get(str(name)) != _sha256(path):
            raise ValueError(f"strict training corpus bytes changed identity: {name}")
        row_count = 0
        for line_number, raw in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid training row in {name}:{line_number}"
                ) from exc
            _validate_training_row(str(name), row, line_number)
            row_count += 1
        row_counts[str(name)] = row_count
    receipt = {
        "schema": TRAINING_CORPUS_VALIDATION_SCHEMA,
        "authority": STRICT_TRAINING_AUTHORITY,
        "corpus_directory": str(directory),
        "manifest_sha256": _sha256(manifest_path),
        "validated_file_sha256s": {
            str(name): _sha256(directory / str(name)) for name in required_files
        },
        "validated_row_counts": row_counts,
        "manifest": manifest,
    }
    receipt["receipt_sha256"] = hashlib.sha256(json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")).hexdigest()
    return receipt


__all__ = [
    "STRICT_TRAINING_AUTHORITY",
    "TRAINING_CORPUS_VALIDATION_SCHEMA",
    "validate_training_corpus_directory",
]
