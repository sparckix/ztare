"""Strict transport boundary for model-authored AxiomPack drafts.

The wire format is intentionally smaller than the theory IR.  Constrained
decoders reliably enforce a shallow JSON object; LeanMill, not the model,
parses the nested axiom IR and resolves the source artifact.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from ztare.leanmill.theory_ir import AxiomFormula, Binder, Formula, Term
from ztare.leanmill import prompts


AXIOM_PACK_TRANSPORT_SCHEMA = "leanmill.band_word_axiom_transport.v1"
_WORD = re.compile(r"^[a-z]{1,12}$")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _sha256_ref(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def sign_transport_contract(contract: Mapping[str, Any], private_key_pem: str) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("transport signer must be an Ed25519 private key")
    return "ed25519:" + key.sign(_canonical_json(dict(contract)).encode("utf-8")).hex()


def verify_transport_contract(contract: Mapping[str, Any], signature: str, public_key_pem: str) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if not signature.startswith("ed25519:"):
        return False
    key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    if not isinstance(key, Ed25519PublicKey):
        return False
    try:
        key.verify(bytes.fromhex(signature.split(":", 1)[1]), _canonical_json(dict(contract)).encode("utf-8"))
    except (InvalidSignature, ValueError):
        return False
    return True


def band_word_output_schema() -> dict[str, Any]:
    """Codex-compatible strict schema for finite-band word-equation drafts."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["typed_axiom_proposals"],
        "properties": {
            "typed_axiom_proposals": {
                "type": "array",
                "minItems": 1,
                "maxItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["source_ref", "axiom_name", "lhs_word", "rhs_word", "nl_intent", "kill_condition"],
                    "properties": {
                        "source_ref": {"type": "string", "minLength": 1},
                        "axiom_name": {"type": "string", "minLength": 1},
                        "lhs_word": {"type": "string", "minLength": 1},
                        "rhs_word": {"type": "string", "minLength": 1},
                        "nl_intent": {"type": "string", "minLength": 1},
                        "kill_condition": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    }


@dataclass(frozen=True)
class AxiomPackTransportContract:
    """Frozen mapping from shallow model output to canonical AxiomPack inputs."""

    proposer_view_digest: str
    source_catalog: Mapping[str, Mapping[str, Any]]
    schema: str = AXIOM_PACK_TRANSPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != AXIOM_PACK_TRANSPORT_SCHEMA:
            raise ValueError(f"unsupported transport schema: {self.schema!r}")
        if not self.proposer_view_digest.startswith("sha256:"):
            raise ValueError("proposer_view_digest must be a sha256 reference")
        if not self.source_catalog:
            raise ValueError("source_catalog must not be empty")
        for ref, source in self.source_catalog.items():
            if not isinstance(ref, str) or not ref:
                raise ValueError("source catalog references must be non-empty strings")
            if not isinstance(source, Mapping):
                raise ValueError(f"source catalog item {ref!r} must be an object")

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "proposer_view_digest": self.proposer_view_digest,
            "source_catalog": {
                ref: json.loads(_canonical_json(dict(source)))
                for ref, source in sorted(self.source_catalog.items())
            },
            "output_schema": band_word_output_schema(),
            "output_schema_digest": _sha256_ref(band_word_output_schema()),
        }

    @property
    def digest(self) -> str:
        return _sha256_ref(self.to_json())

    def render_prompt(self, proposer_view: Mapping[str, Any]) -> str:
        if _sha256_ref(dict(proposer_view)) != self.proposer_view_digest:
            raise ValueError("proposer view does not match frozen transport contract")
        return prompts.AXIOM_PACK_BAND_WORD_PROPOSER_PROMPT.format(
            proposer_view=_canonical_json(dict(proposer_view))
        )

    def decode(self, raw: Any) -> dict[str, Any]:
        """Parse the model envelope without guessing repairs or source identity."""

        if not isinstance(raw, str):
            raise ValueError("transport output must be text")
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"transport_json:{exc.msg}") from exc
        if not isinstance(envelope, Mapping) or set(envelope) != {"typed_axiom_proposals"}:
            raise ValueError("transport envelope fields")
        rows = envelope["typed_axiom_proposals"]
        if not isinstance(rows, list) or len(rows) != 1:
            raise ValueError("exactly_one_typed_axiom_proposal_required")
        parsed: list[dict[str, Any]] = []
        required = {"source_ref", "axiom_name", "lhs_word", "rhs_word", "nl_intent", "kill_condition"}
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping) or set(row) != required:
                raise ValueError(f"row.{index}.fields")
            source_ref = row["source_ref"]
            if not isinstance(source_ref, str) or source_ref not in self.source_catalog:
                raise ValueError(f"row.{index}.unknown_source_ref")
            axiom = _axiom_from_words(
                name=str(row["axiom_name"]), left=str(row["lhs_word"]), right=str(row["rhs_word"])
            )
            parsed.append({
                "source_conjecture": json.loads(_canonical_json(dict(self.source_catalog[source_ref]))),
                "typed_axiom_proposal": {
                    "axiom": axiom.to_json(),
                    "nl_intent": str(row["nl_intent"]),
                    "kill_condition": str(row["kill_condition"]),
                },
            })
        return {"typed_axiom_proposals": parsed}


def _axiom_from_words(*, name: str, left: str, right: str) -> AxiomFormula:
    if not _WORD.fullmatch(left) or not _WORD.fullmatch(right):
        raise ValueError("word equations must use lowercase variable words")
    def word(value: str) -> Term:
        current = Term.var(value[0])
        for letter in value[1:]:
            current = Term.app("mul", current, Term.var(letter))
        return current
    binders = tuple(Binder(letter, "B") for letter in dict.fromkeys(left + right))
    return AxiomFormula(name, Formula.forall(binders, Formula.eq(word(left), word(right))))


__all__ = [
    "AXIOM_PACK_TRANSPORT_SCHEMA",
    "AxiomPackTransportContract",
    "band_word_output_schema",
    "sign_transport_contract",
    "verify_transport_contract",
]
