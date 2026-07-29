"""Typed deterministic semantics for binary linear-code construction tasks.

This adapter layer owns binary-code vocabulary and exact finite checks.  It
does not choose generator matrices or search strategies.  Candidate authors
submit a data-only generator matrix; the host can then replay rank, minimum
distance, a low-weight failure witness, and elementary construction steps.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Sequence

from ztare.leanmill.protocol_validation import (
    require_exact_fields as _exact_fields,
)
from ztare.leanmill.theory_ir import TheorySignature, content_hash


ADAPTER_ID = "binary_linear_code.v1"
GENERATOR_MATRIX_SCHEMA = "leanmill.binary_linear_generator_matrix.v1"
VERIFICATION_RECEIPT_SCHEMA = "leanmill.binary_linear_code_verification.v1"
PREDICATE_SCHEMA = "leanmill.binary_linear_code_predicate.v1"
NORMALIZER_CAPABILITY = "binary_generator_row_basis_normalizer"
VERIFIER_CAPABILITY = "binary_linear_code_exact_verifier"
EVIDENCE_PANEL_SCHEMA = "leanmill.binary_linear_code_evidence_panel.v1"
BINARY_FORMAL_CERTIFICATE_CAPABILITY = (
    "binary_linear_code_kernel_reduction_certificate"
)
BINARY_FORMAL_CHUNK_SIZE = 8192
BINARY_FORMAL_AGGREGATE_GROUP_SIZE = 16
# This is the largest exhaustive range exercised end-to-end by a kernel compile.
# Larger artifacts stay host-verifiable but require a different proof certificate.
BINARY_FORMAL_MAX_NONZERO_MESSAGES = (1 << 14) - 1


def binary_generator_matrix_schema(*, length: int, dimension: int) -> dict[str, Any]:
    """Public JSON Schema for one frozen ``[n,k]`` generator artifact."""

    if (
        type(length) is not int
        or type(dimension) is not int
        or length < 1
        or not 1 <= dimension <= length
    ):
        raise ValueError("binary generator schema requires 1 <= dimension <= length")
    width = max(1, (length + 3) // 4)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema",
            "field_order",
            "length",
            "dimension",
            "coordinate_convention",
            "rows_hex",
        ],
        "properties": {
            "schema": {"type": "string", "const": GENERATOR_MATRIX_SCHEMA},
            "field_order": {"type": "integer", "const": 2},
            "length": {"type": "integer", "const": length},
            "dimension": {"type": "integer", "const": dimension},
            "coordinate_convention": {
                "type": "string",
                "const": "bit_i_is_coordinate_i",
            },
            "rows_hex": {
                "type": "array",
                "minItems": dimension,
                "maxItems": dimension,
                "items": {
                    "type": "string",
                    "pattern": rf"^0x[0-9a-f]{{{width}}}$",
                },
            },
        },
    }


def binary_code_predicate(
    *,
    length: int,
    dimension: int,
    minimum_distance: int,
    target_snapshot_sha256: str,
) -> dict[str, Any]:
    """Freeze one externally sourced constructive target."""

    if (
        type(length) is not int
        or type(dimension) is not int
        or type(minimum_distance) is not int
        or length < 1
        or not 1 <= dimension <= length
        or not 1 <= minimum_distance <= length
    ):
        raise ValueError("binary-code predicate parameters are invalid")
    digest = str(target_snapshot_sha256).removeprefix("sha256:")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("binary-code predicate requires a target snapshot SHA-256")
    return {
        "schema": PREDICATE_SCHEMA,
        "field_order": 2,
        "length": length,
        "dimension": dimension,
        "required_rank": dimension,
        "required_minimum_distance": minimum_distance,
        "target_snapshot_sha256": f"sha256:{digest}",
    }


def binary_witness_construction_interface(
    *,
    length: int,
    dimension: int,
    minimum_distance: int,
    target_snapshot_sha256: str,
    max_nonzero_messages: int,
    target_config_sha256: str,
) -> dict[str, Any]:
    """Build the reviewed interface exposed by a target-bound adapter config."""

    predicate = binary_code_predicate(
        length=length,
        dimension=dimension,
        minimum_distance=minimum_distance,
        target_snapshot_sha256=target_snapshot_sha256,
    )
    required = (1 << dimension) - 1
    if type(max_nonzero_messages) is not int or max_nonzero_messages < required:
        raise ValueError("binary witness verifier budget cannot certify the target")
    from ztare.leanmill.witness_construction_boundary import (
        build_witness_construction_interface,
    )

    return build_witness_construction_interface(
        predicate_ir=predicate,
        witness_schema=binary_generator_matrix_schema(
            length=length,
            dimension=dimension,
        ),
        normalizer={
            "capability_id": NORMALIZER_CAPABILITY,
            "contract": {
                "kind": "canonical_row_basis",
                "preserve_coordinate_order": True,
            },
        },
        verifier={
            "capability_id": VERIFIER_CAPABILITY,
            "contract": {
                "kind": "exhaustive_nonzero_message_replay",
                "max_nonzero_messages": max_nonzero_messages,
            },
        },
        discharge_policy="construction_artifact_ratification_required",
        target_config_sha256=target_config_sha256,
    )


@dataclass(frozen=True)
class BinaryGeneratorMatrix:
    """A row generator over ``F_2`` using bit ``i`` for coordinate ``i``."""

    length: int
    dimension: int
    rows: tuple[int, ...]
    schema: str = GENERATOR_MATRIX_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != GENERATOR_MATRIX_SCHEMA:
            raise ValueError("unsupported binary generator-matrix schema")
        if type(self.length) is not int or self.length < 1:
            raise ValueError("binary generator length must be positive")
        if (
            type(self.dimension) is not int
            or self.dimension < 1
            or self.dimension > self.length
        ):
            raise ValueError("binary generator dimension must lie in [1, length]")
        if len(self.rows) != self.dimension:
            raise ValueError("binary generator row count must equal dimension")
        limit = 1 << self.length
        if any(type(row) is not int or row < 0 or row >= limit for row in self.rows):
            raise ValueError("binary generator row lies outside its declared length")

    @property
    def row_hex_width(self) -> int:
        return max(1, (self.length + 3) // 4)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "field_order": 2,
            "length": self.length,
            "dimension": self.dimension,
            "coordinate_convention": "bit_i_is_coordinate_i",
            "rows_hex": [f"0x{row:0{self.row_hex_width}x}" for row in self.rows],
        }

    @property
    def artifact_sha256(self) -> str:
        return content_hash(self.to_json())

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "BinaryGeneratorMatrix":
        required = {
            "schema",
            "field_order",
            "length",
            "dimension",
            "coordinate_convention",
            "rows_hex",
        }
        _exact_fields(value, required, context="binary generator matrix")
        if value.get("field_order") != 2:
            raise ValueError("binary generator matrix requires field order two")
        if value.get("coordinate_convention") != "bit_i_is_coordinate_i":
            raise ValueError("unsupported binary generator coordinate convention")
        rows = value.get("rows_hex")
        if not isinstance(rows, list) or any(not isinstance(row, str) for row in rows):
            raise TypeError("binary generator rows_hex must be a list of strings")
        try:
            decoded = tuple(int(row, 16) for row in rows)
        except ValueError as exc:
            raise ValueError("binary generator rows_hex contains invalid hex") from exc
        matrix = cls(
            length=value.get("length"),
            dimension=value.get("dimension"),
            rows=decoded,
            schema=str(value.get("schema") or ""),
        )
        if matrix.to_json() != dict(value):
            raise ValueError("binary generator matrix is not in canonical wire form")
        return matrix


def gf2_rank_with_dependency(rows: Sequence[int]) -> tuple[int, int | None]:
    """Return row rank and one nonzero dependency mask when rank is deficient."""

    basis: dict[int, tuple[int, int]] = {}
    rank = 0
    first_dependency = None
    for index, source in enumerate(rows):
        row = int(source)
        combination = 1 << index
        while row:
            pivot = row.bit_length() - 1
            existing = basis.get(pivot)
            if existing is None:
                basis[pivot] = (row, combination)
                rank += 1
                break
            row ^= existing[0]
            combination ^= existing[1]
        if row == 0 and first_dependency is None:
            first_dependency = combination
    return rank, first_dependency


def canonical_row_basis(matrix: BinaryGeneratorMatrix) -> BinaryGeneratorMatrix:
    """Canonicalize row operations while preserving coordinate order."""

    rows = list(matrix.rows)
    pivot_row = 0
    for coordinate in range(matrix.length):
        source = next(
            (
                index
                for index in range(pivot_row, len(rows))
                if (rows[index] >> coordinate) & 1
            ),
            None,
        )
        if source is None:
            continue
        rows[pivot_row], rows[source] = rows[source], rows[pivot_row]
        for index in range(len(rows)):
            if index != pivot_row and ((rows[index] >> coordinate) & 1):
                rows[index] ^= rows[pivot_row]
        pivot_row += 1
        if pivot_row == len(rows):
            break
    return BinaryGeneratorMatrix(
        length=matrix.length,
        dimension=matrix.dimension,
        rows=tuple(rows),
    )


@dataclass(frozen=True)
class MinimumDistanceResult:
    status: str
    minimum_distance: int | None
    message_mask: int | None
    codeword: int | None
    examined_nonzero_messages: int
    required_nonzero_messages: int

    def to_json(self, *, length: int, dimension: int) -> dict[str, Any]:
        word_width = max(1, (length + 3) // 4)
        message_width = max(1, (dimension + 3) // 4)
        return {
            "status": self.status,
            "minimum_distance": self.minimum_distance,
            "message_hex": (
                f"0x{self.message_mask:0{message_width}x}"
                if self.message_mask is not None
                else None
            ),
            "codeword_hex": (
                f"0x{self.codeword:0{word_width}x}"
                if self.codeword is not None
                else None
            ),
            "examined_nonzero_messages": self.examined_nonzero_messages,
            "required_nonzero_messages": self.required_nonzero_messages,
        }


def exact_minimum_distance(
    matrix: BinaryGeneratorMatrix,
    *,
    max_nonzero_messages: int = 2_000_000,
) -> MinimumDistanceResult:
    """Enumerate the row span once in Gray-code order.

    The result is exact only after all ``2^k - 1`` nonzero messages have been
    visited.  A resource refusal is typed and carries no lower-bound credit.
    """

    if type(max_nonzero_messages) is not int or max_nonzero_messages < 1:
        raise ValueError("max_nonzero_messages must be positive")
    required = (1 << matrix.dimension) - 1
    if required > max_nonzero_messages:
        return MinimumDistanceResult(
            status="unavailable_message_budget",
            minimum_distance=None,
            message_mask=None,
            codeword=None,
            examined_nonzero_messages=0,
            required_nonzero_messages=required,
        )
    best_weight = matrix.length + 1
    best_message = None
    best_word = None
    previous_gray = 0
    word = 0
    for step in range(1, required + 1):
        gray = step ^ (step >> 1)
        changed = gray ^ previous_gray
        row_index = changed.bit_length() - 1
        word ^= matrix.rows[row_index]
        weight = word.bit_count()
        if word and weight < best_weight:
            best_weight = weight
            best_message = gray
            best_word = word
        previous_gray = gray
    return MinimumDistanceResult(
        status="exact",
        minimum_distance=(best_weight if best_word is not None else None),
        message_mask=best_message,
        codeword=best_word,
        examined_nonzero_messages=required,
        required_nonzero_messages=required,
    )


def verify_binary_linear_code(
    candidate: BinaryGeneratorMatrix | Mapping[str, Any],
    *,
    required_rank: int,
    required_minimum_distance: int,
    max_nonzero_messages: int = 2_000_000,
) -> dict[str, Any]:
    """Replay one explicit witness against one frozen ``[n,k,d]`` predicate."""

    matrix = (
        candidate
        if isinstance(candidate, BinaryGeneratorMatrix)
        else BinaryGeneratorMatrix.from_json(candidate)
    )
    if required_rank != matrix.dimension:
        raise ValueError("required rank must equal the candidate dimension")
    if (
        type(required_minimum_distance) is not int
        or required_minimum_distance < 1
        or required_minimum_distance > matrix.length
    ):
        raise ValueError("required minimum distance lies outside the candidate length")
    rank, dependency = gf2_rank_with_dependency(matrix.rows)
    normalized = canonical_row_basis(matrix)
    if rank != required_rank:
        distance = MinimumDistanceResult(
            status="not_run_rank_deficient",
            minimum_distance=None,
            message_mask=None,
            codeword=None,
            examined_nonzero_messages=0,
            required_nonzero_messages=(1 << matrix.dimension) - 1,
        )
        status = "rank_deficient"
    else:
        distance = exact_minimum_distance(
            matrix,
            max_nonzero_messages=max_nonzero_messages,
        )
        if distance.status != "exact":
            status = distance.status
        elif (
            distance.minimum_distance is None
            or distance.minimum_distance < required_minimum_distance
        ):
            status = "low_weight_counterexample"
        else:
            status = "satisfied"
    core = {
        "schema": VERIFICATION_RECEIPT_SCHEMA,
        "adapter_id": ADAPTER_ID,
        "artifact_sha256": matrix.artifact_sha256,
        "normalized_row_basis_sha256": normalized.artifact_sha256,
        "predicate": {
            "field_order": 2,
            "length": matrix.length,
            "dimension": matrix.dimension,
            "required_rank": required_rank,
            "required_minimum_distance": required_minimum_distance,
        },
        "status": status,
        "observed_rank": rank,
        "dependency_message_hex": (
            f"0x{dependency:0{max(1, (matrix.dimension + 3) // 4)}x}"
            if dependency is not None
            else None
        ),
        "distance_replay": distance.to_json(
            length=matrix.length,
            dimension=matrix.dimension,
        ),
        "claim_scope": (
            "one_explicit_generator_satisfies_the_frozen_predicate"
            if status == "satisfied"
            else "candidate_replay_only_no_existence_or_nonexistence_claim"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _bind_predicate(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "field_order",
        "length",
        "dimension",
        "required_rank",
        "required_minimum_distance",
        "target_snapshot_sha256",
    }
    _exact_fields(value, required, context="binary-code predicate")
    expected = binary_code_predicate(
        length=value.get("length"),
        dimension=value.get("dimension"),
        minimum_distance=value.get("required_minimum_distance"),
        target_snapshot_sha256=str(value.get("target_snapshot_sha256") or ""),
    )
    if expected != dict(value) or value.get("required_rank") != value.get("dimension"):
        raise ValueError("binary-code predicate changed identity")
    return expected


def normalize_binary_generator_candidate(
    *,
    descriptor: Mapping[str, Any],
    artifact: Mapping[str, Any],
    predicate_ir: Mapping[str, Any],
    witness_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """Registered normalizer callback for the generic construction boundary."""

    expected_descriptor = {
        "adapter_id": ADAPTER_ID,
        "capability_id": NORMALIZER_CAPABILITY,
        "contract": {
            "kind": "canonical_row_basis",
            "preserve_coordinate_order": True,
        },
    }
    if dict(descriptor) != expected_descriptor:
        raise ValueError("binary generator normalizer descriptor changed identity")
    predicate = _bind_predicate(predicate_ir)
    expected_schema = binary_generator_matrix_schema(
        length=int(predicate["length"]),
        dimension=int(predicate["dimension"]),
    )
    if dict(witness_schema) != expected_schema:
        raise ValueError("binary generator witness schema changed identity")
    matrix = BinaryGeneratorMatrix.from_json(artifact)
    if (
        matrix.length != predicate["length"]
        or matrix.dimension != predicate["dimension"]
    ):
        raise ValueError("binary generator crossed its frozen predicate dimensions")
    return canonical_row_basis(matrix).to_json()


def verify_binary_generator_candidate(
    *,
    descriptor: Mapping[str, Any],
    normalized_artifact: Mapping[str, Any],
    predicate_ir: Mapping[str, Any],
    witness_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """Registered exact verifier callback for the generic construction boundary."""

    predicate = _bind_predicate(predicate_ir)
    contract = descriptor.get("contract") if isinstance(descriptor, Mapping) else None
    if (
        not isinstance(contract, Mapping)
        or set(descriptor) != {"adapter_id", "capability_id", "contract"}
        or descriptor.get("adapter_id") != ADAPTER_ID
        or descriptor.get("capability_id") != VERIFIER_CAPABILITY
        or set(contract) != {"kind", "max_nonzero_messages"}
        or contract.get("kind") != "exhaustive_nonzero_message_replay"
        or type(contract.get("max_nonzero_messages")) is not int
    ):
        raise ValueError("binary-code verifier descriptor changed identity")
    expected_schema = binary_generator_matrix_schema(
        length=int(predicate["length"]),
        dimension=int(predicate["dimension"]),
    )
    if dict(witness_schema) != expected_schema:
        raise ValueError("binary-code verifier witness schema changed identity")
    matrix = BinaryGeneratorMatrix.from_json(normalized_artifact)
    receipt = verify_binary_linear_code(
        matrix,
        required_rank=int(predicate["required_rank"]),
        required_minimum_distance=int(
            predicate["required_minimum_distance"]
        ),
        max_nonzero_messages=int(contract["max_nonzero_messages"]),
    )
    if receipt["status"] == "satisfied":
        outcome = "accepted"
    elif receipt["status"] == "unavailable_message_budget":
        outcome = "unavailable"
    else:
        outcome = "rejected"
    return {
        "outcome": outcome,
        "observed": receipt,
        "evidence_refs": ["binary-code-verification:" + receipt["receipt_sha256"]],
    }


def _construction_target(adapter_config: Mapping[str, Any]) -> dict[str, Any]:
    raw = adapter_config.get("construction_target")
    required = {
        "schema",
        "field_order",
        "length",
        "dimension",
        "minimum_distance",
        "max_nonzero_messages",
        "target_snapshot_sha256",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError("binary adapter requires one exact construction_target")
    if (
        raw.get("schema") != "leanmill.binary_linear_code_target_config.v1"
        or raw.get("field_order") != 2
    ):
        raise ValueError("binary construction target schema is unsupported")
    predicate = binary_code_predicate(
        length=raw.get("length"),
        dimension=raw.get("dimension"),
        minimum_distance=raw.get("minimum_distance"),
        target_snapshot_sha256=str(raw.get("target_snapshot_sha256") or ""),
    )
    required_messages = (1 << int(predicate["dimension"])) - 1
    maximum = raw.get("max_nonzero_messages")
    if type(maximum) is not int or maximum < required_messages:
        raise ValueError("binary construction target verifier budget is incomplete")
    return {
        "length": int(predicate["length"]),
        "dimension": int(predicate["dimension"]),
        "minimum_distance": int(predicate["required_minimum_distance"]),
        "max_nonzero_messages": maximum,
        "target_snapshot_sha256": str(predicate["target_snapshot_sha256"]),
    }


def _construction_interface(adapter_config: Mapping[str, Any]) -> dict[str, Any]:
    target = _construction_target(adapter_config)
    return binary_witness_construction_interface(
        **target,
        target_config_sha256=content_hash(dict(adapter_config)),
    )


def _evidence_panel(adapter_config: Mapping[str, Any]) -> dict[str, Any]:
    """Bind one exact declared panel without claiming a census of all codes."""

    raw = adapter_config.get("evidence_panel")
    required = {
        "schema",
        "field_order",
        "completeness_scope",
        "completeness_ref",
        "objects",
        "hypotheses",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError("binary adapter requires one exact evidence_panel")
    if (
        raw.get("schema") != EVIDENCE_PANEL_SCHEMA
        or raw.get("field_order") != 1
        or raw.get("completeness_scope") != "declared_control_panel_only"
    ):
        raise ValueError("binary evidence panel identity is unsupported")
    completeness_ref = str(raw.get("completeness_ref") or "").strip()
    if not completeness_ref:
        raise ValueError("binary evidence panel requires a completeness_ref")
    return {
        "completeness_ref": completeness_ref,
        "objects": list(raw.get("objects") or ()),
        "hypotheses": list(raw.get("hypotheses") or ()),
    }


def preflight_blueprint(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    formula_grammar: Mapping[str, Any],
    strata: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Preflight the declared evidence panel and the separate target verifier."""

    if set(adapter_config) != {"construction_target", "evidence_panel"}:
        raise ValueError("binary campaign adapter configuration fields changed identity")
    _construction_target(adapter_config)
    from ztare.leanmill.adapters.generic_finite_evidence import (
        preflight_blueprint as preflight_evidence_panel,
    )

    result = preflight_evidence_panel(
        signature,
        adapter_config=_evidence_panel(adapter_config),
        formula_grammar=formula_grammar,
        strata=strata,
    )
    return {
        **result,
        "adapter_id": ADAPTER_ID,
        "completeness_scope": "declared_control_panel_only",
        "claim_boundary": (
            "exact incidence over the declared control panel; no completeness "
            "claim over binary linear codes or construction families"
        ),
        "target_config_sha256": content_hash(dict(adapter_config)),
    }


def build_evidence_context(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    strata: Sequence[Mapping[str, Any]],
) -> Any:
    """Expose the control panel through the binary adapter's campaign identity."""

    if set(adapter_config) != {"construction_target", "evidence_panel"}:
        raise ValueError("binary campaign adapter configuration fields changed identity")
    _construction_target(adapter_config)
    from ztare.leanmill.adapters.generic_finite_evidence import (
        build_evidence_context as build_declared_panel,
    )
    from ztare.leanmill.evidence_theory_context import EvidenceTheoryContext

    context = build_declared_panel(
        signature,
        adapter_config=_evidence_panel(adapter_config),
        strata=strata,
    )
    return EvidenceTheoryContext(
        signature=context.signature,
        adapter_id=ADAPTER_ID,
        incidence=context.incidence,
        formula_profiles=context.formula_profiles,
        object_records=context.object_records,
        completeness_receipt_digest=context.completeness_receipt_digest,
        base_axioms=context.base_axioms,
    )


def theory_task_capabilities(
    *, adapter_config: Mapping[str, Any]
) -> tuple[dict[str, Any], ...]:
    """Return the target-bound task interface shown to the navigator."""

    return (
        {
            "capability_id": "governed_witness_construction",
            "purpose": (
                "normalize and exactly verify one explicit binary generator "
                "matrix against the frozen code parameters"
            ),
            "use_when": (
                "the campaign has authored a concrete generator matrix; exact "
                "verification remains open pending construction-artifact ratification"
            ),
            "interface": _construction_interface(adapter_config),
        },
    )


def compile_theory_task(
    *,
    request: Mapping[str, Any],
    context: Any,
    adapter_config: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Lower only the target-bound binary witness-construction task."""

    from ztare.leanmill.witness_construction_boundary import (
        compile_governed_witness_construction_task,
    )

    return compile_governed_witness_construction_task(
        request=request,
        context=context,
        adapter_id=ADAPTER_ID,
        construction_interface=_construction_interface(adapter_config),
    )


def adjudicate_theory_task(
    *, contract: Any, boundary_result: Mapping[str, Any]
) -> Any:
    """Project the registered witness result through common task discharge."""

    from ztare.leanmill.witness_construction_boundary import (
        GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
        adjudicate_governed_witness_construction_task,
    )

    if contract.adjudicator_id != GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR:
        raise KeyError(
            f"unsupported binary-code task adjudicator: {contract.adjudicator_id}"
        )
    return adjudicate_governed_witness_construction_task(
        contract=contract,
        boundary_result=boundary_result,
    )


_BINARY_CERTIFICATE_PREFIX = """import Mathlib

namespace AxiomPack.BinaryLinearCodeCertificate

structure Generator where
  schema : String
  fieldOrder : Nat
  length : Nat
  dimension : Nat
  coordinateConvention : String
  rows : List Nat
  artifactSha256 : String
deriving DecidableEq

structure Predicate where
  schema : String
  fieldOrder : Nat
  length : Nat
  dimension : Nat
  requiredRank : Nat
  requiredMinimumDistance : Nat
  targetSnapshotSha256 : String
  predicateSha256 : String
  constructionInterfaceSha256 : String
  targetConfigSha256 : String
deriving DecidableEq

structure Binding where
  formalInputSha256 : String
  artifactSha256 : String
  predicateSha256 : String
  witnessSchemaSha256 : String
  constructionInterfaceSha256 : String
  targetConfigSha256 : String
  rowCount : Nat
  requiredNonzeroMessages : Nat
  chunkSize : Nat
  blockCount : Nat
deriving DecidableEq

def nibbleWeight (n : Nat) : Nat :=
  match n % 16 with
  | 0 => 0 | 1 => 1 | 2 => 1 | 3 => 2
  | 4 => 1 | 5 => 2 | 6 => 2 | 7 => 3
  | 8 => 1 | 9 => 2 | 10 => 2 | 11 => 3
  | 12 => 2 | 13 => 3 | 14 => 3 | _ => 4

def popcountNibbles : Nat -> Nat -> Nat
  | 0, _ => 0
  | count + 1, word => nibbleWeight word + popcountNibbles count (word / 16)

def popcount (length word : Nat) : Nat :=
  popcountNibbles ((length + 3) / 4) word

def encode (rows : List Nat) (message : Nat) : Nat :=
  (List.range rows.length).foldl
    (fun word i => if message.testBit i then Nat.xor word (rows.getD i 0) else word)
    0

def gray (message : Nat) : Nat := Nat.xor message (message / 2)

def grayLoop (length : Nat) (rows : List Nat) (distance : Nat) : Nat -> Nat -> Nat -> Bool
  | _, 0, _ => true
  | step, count + 1, previousWord =>
      let delta := Nat.xor (gray step) (gray (step - 1))
      let word := Nat.xor previousWord (rows.getD delta.log2 0)
      decide (word ≠ 0 ∧ distance ≤ popcount length word) &&
        grayLoop length rows distance (step + 1) count word

def intervalPasses (length : Nat) (rows : List Nat) (distance start count : Nat) : Bool :=
  grayLoop length rows distance start count (encode rows (gray (start - 1)))

def coverageFrom (next stop : Nat) : List (Nat × Nat) -> Bool
  | [] => decide (next = stop)
  | (start, count) :: rest =>
      decide (start = next ∧ 0 < count ∧ next + count ≤ stop) &&
        coverageFrom (next + count) stop rest

def blocksPass
    (artifact : Generator) (predicate : Predicate)
    (blocks : List (Nat × Nat)) : Bool :=
  blocks.all fun block => intervalPasses artifact.length artifact.rows
    predicate.requiredMinimumDistance block.1 block.2

def metadataPasses
    (artifact : Generator) (predicate : Predicate) (binding : Binding)
    (blocks : List (Nat × Nat)) : Bool :=
  decide (artifact.schema = "leanmill.binary_linear_generator_matrix.v1") &&
  decide (predicate.schema = "leanmill.binary_linear_code_predicate.v1") &&
  decide (artifact.fieldOrder = 2) &&
  decide (predicate.fieldOrder = 2) &&
  decide (artifact.coordinateConvention = "bit_i_is_coordinate_i") &&
  decide (artifact.length = predicate.length) &&
  decide (artifact.dimension = predicate.dimension) &&
  decide (predicate.requiredRank = artifact.dimension) &&
  decide (0 < predicate.requiredMinimumDistance) &&
  decide (predicate.requiredMinimumDistance ≤ artifact.length) &&
  decide (artifact.rows.length = artifact.dimension) &&
  decide (binding.rowCount = artifact.rows.length) &&
  decide (binding.requiredNonzeroMessages = 2 ^ artifact.dimension - 1) &&
  decide (binding.chunkSize = __BINARY_FORMAL_CHUNK_SIZE__) &&
  decide (binding.blockCount = blocks.length) &&
  decide (artifact.artifactSha256 = binding.artifactSha256) &&
  decide (predicate.predicateSha256 = binding.predicateSha256) &&
  decide (predicate.constructionInterfaceSha256 = binding.constructionInterfaceSha256) &&
  decide (predicate.targetConfigSha256 = binding.targetConfigSha256) &&
  decide (binding.formalInputSha256 ≠ "") &&
  decide (binding.witnessSchemaSha256 ≠ "") &&
  decide (binding.artifactSha256 ≠ "") &&
  decide (predicate.targetSnapshotSha256 ≠ "") &&
  (artifact.rows.all fun row => decide (row < 2 ^ artifact.length)) &&
  (blocks.all fun block => decide (0 < block.2 ∧ block.2 ≤ binding.chunkSize)) &&
  coverageFrom 1 (2 ^ artifact.dimension) blocks

def Satisfies
    (artifact : Generator) (predicate : Predicate) (binding : Binding)
    (blocks : List (Nat × Nat)) : Prop :=
  metadataPasses artifact predicate binding blocks = true ∧
  blocksPass artifact predicate blocks = true
"""


def _lean_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def _binary_formal_surface(frozen: Mapping[str, Any]) -> dict[str, str]:
    from ztare.leanmill.construction_artifact_ratification import (
        ConstructionArtifactRatificationCapabilityUnavailable,
    )

    if frozen["adapter_id"] != ADAPTER_ID:
        raise ValueError("binary formal interface crossed adapter identity")
    predicate = _bind_predicate(frozen["predicate_ir"])
    expected_schema = binary_generator_matrix_schema(
        length=int(predicate["length"]),
        dimension=int(predicate["dimension"]),
    )
    if dict(frozen["witness_schema"]) != expected_schema:
        raise ValueError("binary formal interface crossed witness schema")
    matrix = BinaryGeneratorMatrix.from_json(frozen["normalized_artifact"])
    if (
        matrix.length != predicate["length"]
        or matrix.dimension != predicate["dimension"]
    ):
        raise ValueError("binary formal interface crossed artifact dimensions")
    if canonical_row_basis(matrix) != matrix:
        raise ValueError("binary formal interface requires the canonical row basis")
    rank, _dependency = gf2_rank_with_dependency(matrix.rows)
    if rank != matrix.dimension:
        raise ValueError("binary formal interface requires independent normalized rows")

    required_messages = (1 << matrix.dimension) - 1
    if required_messages > BINARY_FORMAL_MAX_NONZERO_MESSAGES:
        raise ConstructionArtifactRatificationCapabilityUnavailable(
            "binary_kernel_certificate_message_bound_exceeded"
        )
    blocks = tuple(
        (start, min(BINARY_FORMAL_CHUNK_SIZE, required_messages - start + 1))
        for start in range(1, required_messages + 1, BINARY_FORMAL_CHUNK_SIZE)
    )
    tag = str(frozen["input_sha256"])[:16]
    artifact_name = "artifact_" + tag
    predicate_name = "predicate_" + tag
    binding_name = "binding_" + tag
    blocks_name = "blocks_" + tag
    metadata_name = "metadata_" + tag
    aggregate_name = "aggregate_" + tag

    rows_term = "[" + ", ".join(str(row) for row in matrix.rows) + "]"
    block_groups = tuple(
        blocks[index : index + BINARY_FORMAL_AGGREGATE_GROUP_SIZE]
        for index in range(0, len(blocks), BINARY_FORMAL_AGGREGATE_GROUP_SIZE)
    )
    group_names = tuple(
        f"block_group_{tag}_{index}" for index in range(len(block_groups))
    )
    generator = "AxiomPack.BinaryLinearCodeCertificate.Generator.mk"
    formal_predicate = "AxiomPack.BinaryLinearCodeCertificate.Predicate.mk"
    binding = "AxiomPack.BinaryLinearCodeCertificate.Binding.mk"
    satisfies = "AxiomPack.BinaryLinearCodeCertificate.Satisfies"
    artifact_term = (
        f"({generator} {_lean_string(matrix.schema)} 2 {matrix.length} "
        f"{matrix.dimension} {_lean_string('bit_i_is_coordinate_i')} {rows_term} "
        f"{_lean_string(str(frozen['normalized_artifact_sha256']))})"
    )
    predicate_term = (
        f"({formal_predicate} {_lean_string(str(predicate['schema']))} 2 "
        f"{predicate['length']} {predicate['dimension']} "
        f"{predicate['required_rank']} {predicate['required_minimum_distance']} "
        f"{_lean_string(str(predicate['target_snapshot_sha256']))} "
        f"{_lean_string(str(frozen['predicate_sha256']))} "
        f"{_lean_string(str(frozen['interface_sha256']))} "
        f"{_lean_string(str(frozen['target_config_sha256']))})"
    )
    binding_term = (
        f"({binding} {_lean_string(str(frozen['input_sha256']))} "
        f"{_lean_string(str(frozen['normalized_artifact_sha256']))} "
        f"{_lean_string(str(frozen['predicate_sha256']))} "
        f"{_lean_string(str(frozen['witness_schema_sha256']))} "
        f"{_lean_string(str(frozen['interface_sha256']))} "
        f"{_lean_string(str(frozen['target_config_sha256']))} "
        f"{len(matrix.rows)} {required_messages} {BINARY_FORMAL_CHUNK_SIZE} "
        f"{len(blocks)})"
    )

    exact = [
        f"def {artifact_name} : Generator := {artifact_term}",
        f"def {predicate_name} : Predicate := {predicate_term}",
        f"def {binding_name} : Binding := {binding_term}",
    ]
    for group_name, group in zip(group_names, block_groups, strict=True):
        group_term = "[" + ", ".join(
            f"({start}, {count})" for start, count in group
        ) + "]"
        exact.append(
            f"def {group_name} : List (Nat × Nat) := {group_term}"
        )
    exact.extend([
        f"def {blocks_name} : List (Nat × Nat) := "
        + " ++ ".join(group_names),
        "",
        "set_option maxHeartbeats 0",
        "set_option maxRecDepth 100000",
        "",
        f"theorem {metadata_name} : metadataPasses {artifact_name} {predicate_name} "
        f"{binding_name} {blocks_name} = true := by decide",
    ])
    block_names: list[str] = []
    for index, (start, count) in enumerate(blocks):
        block_name = f"block_{tag}_{index}"
        block_names.append(block_name)
        exact.append(
            f"theorem {block_name} : intervalPasses {artifact_name}.length "
            f"{artifact_name}.rows {predicate_name}.requiredMinimumDistance "
            f"{start} {count} = true := by decide"
        )
    group_pass_names: list[str] = []
    for index, (group_name, group) in enumerate(
        zip(group_names, block_groups, strict=True)
    ):
        group_pass_name = f"group_pass_{tag}_{index}"
        group_pass_names.append(group_pass_name)
        first = index * BINARY_FORMAL_AGGREGATE_GROUP_SIZE
        group_block_names = block_names[first : first + len(group)]
        exact.extend((
            "",
            f"theorem {group_pass_name} : ({group_name}.all fun block => "
            f"intervalPasses {artifact_name}.length {artifact_name}.rows "
            f"{predicate_name}.requiredMinimumDistance block.1 block.2) = true := by",
            f"  simp [{group_name}, {', '.join(group_block_names)}]",
        ))
    exact.extend((
        "",
        f"theorem {aggregate_name} : blocksPass {artifact_name} {predicate_name} "
        f"{blocks_name} = true := by",
        f"  simp [{blocks_name}, blocksPass, {', '.join(group_pass_names)}]",
    ))
    target_signature = (
        f": {satisfies} {artifact_term} {predicate_term} {binding_term} {blocks_name}"
    )
    proof_text = (
        "by\n"
        f"  change Satisfies {artifact_name} {predicate_name} {binding_name} {blocks_name}\n"
        f"  exact ⟨{metadata_name}, {aggregate_name}⟩"
    )
    return {
        "source": "\n".join(exact) + "\n",
        "target_signature": target_signature,
        "proof_text": proof_text,
        "written": "certificate_" + tag,
        "generator": generator,
        "satisfies": satisfies,
    }


def binary_construction_artifact_formal_interface(
    *, formal_input: Mapping[str, Any]
) -> dict[str, Any]:
    """Compile one reviewed binary generator into a chunked Lean proposition."""

    from ztare.leanmill.construction_artifact_ratification import (
        build_construction_artifact_formal_interface,
        validate_construction_artifact_formal_input,
    )

    frozen = validate_construction_artifact_formal_input(formal_input)
    surface = _binary_formal_surface(frozen)
    namespace = "AxiomPack.BinaryLinearCodeCertificate"
    return build_construction_artifact_formal_interface(
        frozen,
        adapter_id=ADAPTER_ID,
        certificate_capability_id=BINARY_FORMAL_CERTIFICATE_CAPABILITY,
        target_selector=namespace + "." + surface["written"],
        target_written_name=surface["written"],
        target_signature=surface["target_signature"],
        source_prefix=(
            _BINARY_CERTIFICATE_PREFIX.replace(
                "__BINARY_FORMAL_CHUNK_SIZE__", str(BINARY_FORMAL_CHUNK_SIZE)
            )
            + "\n"
            + surface["source"]
        ),
        source_suffix="end AxiomPack.BinaryLinearCodeCertificate\n",
        claim_predicate=surface["satisfies"],
        artifact_constructor=surface["generator"],
    )


def binary_construction_artifact_formal_certificate(
    *, ratification_contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the aggregate proof over the content-bound ``by decide`` chunks."""

    from ztare.leanmill.construction_artifact_ratification import (
        build_construction_artifact_proof_receipt,
        validate_construction_artifact_ratification_contract_record,
    )

    contract = validate_construction_artifact_ratification_contract_record(
        ratification_contract
    )
    frozen = contract["formal_input"]
    surface = _binary_formal_surface(frozen)
    if (
        contract["formal_interface"]["certificate_capability_id"]
        != BINARY_FORMAL_CERTIFICATE_CAPABILITY
    ):
        raise ValueError("binary proof producer crossed formal capability identity")
    expected_interface = binary_construction_artifact_formal_interface(
        formal_input=frozen
    )
    if contract["formal_interface"] != expected_interface:
        raise ValueError("binary proof producer crossed its exact formal interface")
    return build_construction_artifact_proof_receipt(
        contract,
        proof_text=surface["proof_text"],
    )


CAPABILITIES = {
    NORMALIZER_CAPABILITY: normalize_binary_generator_candidate,
    VERIFIER_CAPABILITY: verify_binary_generator_candidate,
    "construction_artifact_formal_interface": (
        binary_construction_artifact_formal_interface
    ),
    BINARY_FORMAL_CERTIFICATE_CAPABILITY: (
        binary_construction_artifact_formal_certificate
    ),
    "theory_task_compiler": compile_theory_task,
    "task_discharge_adjudicator": adjudicate_theory_task,
}

# The construction protocol resolves exact arithmetic through the same static,
# reviewed adapter registry as every other executable capability.  The shared
# implementation owns Q semantics; this adapter merely grants it for this
# reviewed interface.  Campaign output cannot mutate this mapping.
from ztare.leanmill.adapters.construction_backends import (  # noqa: E402
    explicit_finite_json as _explicit_finite_construction,
)

CAPABILITIES.update({
    _explicit_finite_construction.CAPABILITY_ID:
        _explicit_finite_construction.capability,
})

CAPABILITY_CONTRACTS = {
    _explicit_finite_construction.CAPABILITY_ID: {
        "role": "construction_backend",
        "contract": dict(_explicit_finite_construction.CONTRACT),
        "contract_sha256": content_hash(_explicit_finite_construction.CONTRACT),
    },
}


def _rotate_block(mask: int, shift: int, block_size: int) -> int:
    limit = (1 << block_size) - 1
    amount = shift % block_size
    if amount == 0:
        return mask & limit
    return ((mask << amount) | (mask >> (block_size - amount))) & limit


def quasicyclic_generator_matrix(
    polynomial_masks: Sequence[Sequence[int]],
    *,
    block_size: int,
) -> BinaryGeneratorMatrix:
    """Expand a matrix over ``F_2[x]/(x^m-1)`` into binary circulant blocks."""

    if type(block_size) is not int or block_size < 1:
        raise ValueError("quasicyclic block size must be positive")
    block_rows = tuple(tuple(row) for row in polynomial_masks)
    if not block_rows or not block_rows[0]:
        raise ValueError("quasicyclic polynomial matrix cannot be empty")
    width = len(block_rows[0])
    limit = 1 << block_size
    if any(len(row) != width for row in block_rows):
        raise ValueError("quasicyclic polynomial rows must have equal width")
    if any(type(mask) is not int or mask < 0 or mask >= limit for row in block_rows for mask in row):
        raise ValueError("quasicyclic polynomial mask exceeds its block size")
    rows: list[int] = []
    for polynomial_row in block_rows:
        for shift in range(block_size):
            binary_row = 0
            for block_index, mask in enumerate(polynomial_row):
                binary_row |= _rotate_block(mask, shift, block_size) << (
                    block_index * block_size
                )
            rows.append(binary_row)
    return BinaryGeneratorMatrix(
        length=width * block_size,
        dimension=len(block_rows) * block_size,
        rows=tuple(rows),
    )


def extend_with_parity(matrix: BinaryGeneratorMatrix) -> BinaryGeneratorMatrix:
    """Append the overall parity coordinate to every generator row."""

    parity_bit = 1 << matrix.length
    return BinaryGeneratorMatrix(
        length=matrix.length + 1,
        dimension=matrix.dimension,
        rows=tuple(
            row | (parity_bit if row.bit_count() % 2 else 0)
            for row in matrix.rows
        ),
    )


__all__ = [
    "ADAPTER_ID",
    "BINARY_FORMAL_CHUNK_SIZE",
    "BINARY_FORMAL_CERTIFICATE_CAPABILITY",
    "BINARY_FORMAL_AGGREGATE_GROUP_SIZE",
    "BINARY_FORMAL_MAX_NONZERO_MESSAGES",
    "CAPABILITIES",
    "EVIDENCE_PANEL_SCHEMA",
    "GENERATOR_MATRIX_SCHEMA",
    "NORMALIZER_CAPABILITY",
    "PREDICATE_SCHEMA",
    "VERIFICATION_RECEIPT_SCHEMA",
    "VERIFIER_CAPABILITY",
    "BinaryGeneratorMatrix",
    "MinimumDistanceResult",
    "binary_code_predicate",
    "binary_construction_artifact_formal_certificate",
    "binary_construction_artifact_formal_interface",
    "binary_generator_matrix_schema",
    "binary_witness_construction_interface",
    "build_evidence_context",
    "canonical_row_basis",
    "compile_theory_task",
    "exact_minimum_distance",
    "extend_with_parity",
    "gf2_rank_with_dependency",
    "normalize_binary_generator_candidate",
    "preflight_blueprint",
    "quasicyclic_generator_matrix",
    "theory_task_capabilities",
    "verify_binary_linear_code",
    "verify_binary_generator_candidate",
]
