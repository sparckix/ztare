"""Signed packets and freeze boundary for frontier theory campaigns."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from ztare.common.leaf_workbench_contract import LeafWorkbenchContract
from ztare.leanmill.contracts.axiom_pack_transport import (
    sign_transport_contract,
    verify_transport_contract,
)
from ztare.leanmill.finite_model import finite_interpretation_count
from ztare.leanmill.theory_context import TheoryLandscapeContext


FRONTIER_CAMPAIGN_SCHEMA = "leanmill.frontier_theory_campaign.v3"
LEGACY_FRONTIER_CAMPAIGN_SCHEMA = "leanmill.frontier_theory_campaign.v2"
CAMPAIGN_MODES = frozenset(
    {"anonymous_signature_census", "evidence_induced", "domain_conditioned", "proof_gap_conditioned"}
)
_EXACT_CONTEXT_CLAIM_SCOPE = "exact_bounded_closure"
_SAMPLED_CONTEXT_CLAIM_SCOPE = "sampled_panel_behavior"
_PANEL_SEMANTIC_USES = ("behavioral_routing", "prediction_profiles")
_SAMPLED_NAVIGATOR_SCHEMA = "leanmill-axiompack-sampled-leaf-workbench-v1"
_SAMPLED_NAVIGATOR_CAPABILITY_IDS = (
    "inspect_formula_profiles",
    "show_separation_models",
    "show_indistinguishable_objects",
    "propose_frontier_formula",
    "select_theory_presentation",
    "propose_theory_language_expansion",
)
_CONTEXT_MANIFEST_KEYS = frozenset(
    {
        "context_hash",
        "context_exact",
        "claim_scope",
        "census_domain",
        "permitted_semantic_uses",
        "exact_closure_authority",
        "formula_count",
        "canonical_model_count",
        "object_count",
        "model_census_receipt_digest",
        "completeness_receipt_digest",
        "formula_ids_digest",
        "model_ids_digest",
        "object_ids_digest",
        "interpretation_labels_visible",
    }
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode()).hexdigest()


def _validate_context_authority_manifest(manifest: Mapping[str, Any]) -> None:
    """Keep sampled evidence useful without laundering it into closure authority."""

    if set(manifest) != _CONTEXT_MANIFEST_KEYS:
        raise ValueError("visible context manifest fields do not match the frozen schema")
    exact = manifest.get("context_exact")
    if type(exact) is not bool:
        raise ValueError("visible context exactness must be boolean")
    object_count = manifest.get("object_count")
    formula_count = manifest.get("formula_count")
    if (
        type(object_count) is not int
        or object_count < 1
        or type(formula_count) is not int
        or formula_count < 1
    ):
        raise ValueError("visible context counts must be positive integers")
    if manifest.get("interpretation_labels_visible") is not False:
        raise ValueError("interpretation labels cannot be visible before freeze")
    for field in ("formula_ids_digest", "object_ids_digest"):
        if not str(manifest.get(field) or "").startswith("sha256:"):
            raise ValueError(f"visible context {field} must be a digest")

    expected_scope = (
        _EXACT_CONTEXT_CLAIM_SCOPE if exact else _SAMPLED_CONTEXT_CLAIM_SCOPE
    )
    expected_uses = _PANEL_SEMANTIC_USES + (
        (_EXACT_CONTEXT_CLAIM_SCOPE,) if exact else ()
    )
    raw_uses = manifest.get("permitted_semantic_uses")
    if not isinstance(raw_uses, (list, tuple)) or tuple(raw_uses) != expected_uses:
        raise ValueError("visible context semantic uses exceed its claim scope")
    if manifest.get("claim_scope") != expected_scope:
        raise ValueError("visible context claim scope disagrees with exactness")
    census_domain = manifest.get("census_domain")
    if census_domain not in {
        "all_interpretations_in_declared_strata",
        "deterministic_image_of_frozen_source",
        "sampled_objects",
    }:
        raise ValueError("visible context census domain is unknown")
    if exact == (census_domain == "sampled_objects"):
        raise ValueError("visible context census domain disagrees with exactness")
    if manifest.get("exact_closure_authority") is not exact:
        raise ValueError("visible context closure authority disagrees with exactness")

    completeness = str(manifest.get("completeness_receipt_digest") or "")
    model_census = str(manifest.get("model_census_receipt_digest") or "")
    model_ids = str(manifest.get("model_ids_digest") or "")
    canonical_count = manifest.get("canonical_model_count")
    object_ids = str(manifest.get("object_ids_digest") or "")
    if exact:
        if not completeness or model_census != completeness:
            raise ValueError("exact context requires one bound completeness receipt")
        if canonical_count != object_count or model_ids != object_ids:
            raise ValueError("exact context model census differs from its object universe")
    elif any((completeness, model_census, model_ids)) or canonical_count is not None:
        raise ValueError("sampled context cannot emit model-census or closure authority")


def _navigator_contract_for_context(
    contract: LeafWorkbenchContract, *, exact: bool
) -> LeafWorkbenchContract:
    if exact:
        return contract
    registry = contract.registry()
    missing = set(_SAMPLED_NAVIGATOR_CAPABILITY_IDS) - set(registry)
    if missing:
        raise ValueError("sampled navigator contract lacks panel-safe capabilities")
    return LeafWorkbenchContract(
        capabilities=tuple(
            registry[capability_id]
            for capability_id in _SAMPLED_NAVIGATOR_CAPABILITY_IDS
        ),
        schema=_SAMPLED_NAVIGATOR_SCHEMA,
    )


def _validate_navigator_context_authority(
    manifest: Mapping[str, Any], navigator: Mapping[str, Any]
) -> None:
    if manifest.get("context_exact") is True:
        return
    if navigator.get("schema") != _SAMPLED_NAVIGATOR_SCHEMA:
        raise ValueError("sampled context must use the panel-safe navigator contract")
    capability_ids = navigator.get("capability_ids")
    if (
        not isinstance(capability_ids, list)
        or tuple(capability_ids) != _SAMPLED_NAVIGATOR_CAPABILITY_IDS
    ):
        raise ValueError("sampled navigator advertises exact-context capabilities")


@dataclass(frozen=True)
class FrontierCampaignPacket:
    campaign_id: str
    blueprint_id: str
    mode: str
    eigenquestion: str
    signature: Mapping[str, Any]
    base_axioms: tuple[Mapping[str, Any], ...]
    formula_grammar: Mapping[str, Any]
    model_strata: tuple[Mapping[str, Any], ...]
    pack_arity: int
    visible_context_manifest: Mapping[str, Any]
    sealed_context_manifest_digest: str
    collapse_controls: tuple[Mapping[str, Any], ...]
    navigator_contract: Mapping[str, Any]
    query_budget: Mapping[str, Any]
    stop_rule: Mapping[str, Any]
    codec_versions: Mapping[str, str]
    authority_refs: tuple[str, ...]
    frozen: bool = True
    schema: str = FRONTIER_CAMPAIGN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != FRONTIER_CAMPAIGN_SCHEMA or self.mode not in CAMPAIGN_MODES:
            raise ValueError("unsupported frontier campaign schema or mode")
        if not self.frozen:
            raise ValueError("scientific campaign packets must be frozen")
        if not self.campaign_id or not self.eigenquestion:
            raise ValueError("campaign identity and eigenquestion must be non-empty")
        if not self.blueprint_id.startswith("blueprint:"):
            raise ValueError("campaign must bind the full reviewed blueprint identity")
        if type(self.pack_arity) is not int or self.pack_arity < 1:
            raise ValueError("pack_arity must be positive")
        presentation_size = self.navigator_contract.get("presentation_size")
        if presentation_size is not None:
            if not isinstance(presentation_size, Mapping):
                raise ValueError("campaign presentation_size must be an object")
            minimum = presentation_size.get("minimum", 1)
            maximum = presentation_size.get("maximum", self.pack_arity)
            if (
                type(minimum) is not int
                or type(maximum) is not int
                or not 1 <= minimum <= maximum <= self.pack_arity
            ):
                raise ValueError("campaign presentation_size violates pack_arity")
        if not self.sealed_context_manifest_digest.startswith("sha256:"):
            raise ValueError("sealed context must be represented only by its digest")
        if "sealed" in self.visible_context_manifest:
            raise ValueError("sealed context content cannot appear in the visible manifest")
        _validate_context_authority_manifest(self.visible_context_manifest)
        _validate_navigator_context_authority(
            self.visible_context_manifest, self.navigator_contract
        )
        if not self.authority_refs:
            raise ValueError("campaign packet requires authority refs")

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "campaign_id": self.campaign_id,
            "blueprint_id": self.blueprint_id,
            "mode": self.mode,
            "eigenquestion": self.eigenquestion,
            "signature": dict(self.signature),
            "base_axioms": [dict(row) for row in self.base_axioms],
            "formula_grammar": dict(self.formula_grammar),
            "model_strata": [dict(row) for row in self.model_strata],
            "pack_arity": self.pack_arity,
            "visible_context_manifest": dict(self.visible_context_manifest),
            "sealed_context_manifest_digest": self.sealed_context_manifest_digest,
            "collapse_controls": [dict(row) for row in self.collapse_controls],
            "navigator_contract": dict(self.navigator_contract),
            "query_budget": dict(self.query_budget),
            "stop_rule": dict(self.stop_rule),
            "codec_versions": dict(self.codec_versions),
            "authority_refs": list(self.authority_refs),
            "frozen": self.frozen,
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_json())


@dataclass(frozen=True)
class SignedFrontierCampaign:
    packet: FrontierCampaignPacket
    signature: str
    signer_ref: str

    def to_json(self) -> dict[str, Any]:
        return {
            "packet": self.packet.to_json(),
            "packet_digest": self.packet.digest,
            "signature": self.signature,
            "signer_ref": self.signer_ref,
        }


def sign_frontier_campaign(packet: FrontierCampaignPacket, *, private_key_pem: str, signer_ref: str) -> SignedFrontierCampaign:
    if not signer_ref:
        raise ValueError("signer_ref must be non-empty")
    return SignedFrontierCampaign(
        packet=packet,
        signature=sign_transport_contract(packet.to_json(), private_key_pem),
        signer_ref=signer_ref,
    )


def verify_frontier_campaign(signed: SignedFrontierCampaign, *, public_key_pem: str, expected_signer_ref: str) -> bool:
    return signed.signer_ref == expected_signer_ref and verify_transport_contract(
        signed.packet.to_json(), signed.signature, public_key_pem
    )


def verify_campaign_artifact_signature(
    campaign: Mapping[str, Any],
    *,
    public_key_pem: str,
    expected_signer_ref: str = "",
) -> bool:
    packet = campaign.get("packet")
    signer = str(campaign.get("signer_ref") or "")
    return bool(
        isinstance(packet, Mapping)
        and signer
        and (not expected_signer_ref or signer == expected_signer_ref)
        and verify_transport_contract(
            dict(packet), str(campaign.get("signature") or ""), public_key_pem
        )
    )


def validate_campaign_artifact_binding(
    campaign: Mapping[str, Any],
    *,
    blueprint_id: str,
    context_hash: str,
    expected_packet_digest: str = "",
) -> Mapping[str, Any]:
    """Replay the immutable packet-to-blueprint/context binding."""

    packet = campaign.get("packet")
    if not isinstance(packet, Mapping):
        raise ValueError("campaign artifact has no packet")
    schema = str(packet.get("schema") or "")
    if schema not in {FRONTIER_CAMPAIGN_SCHEMA, LEGACY_FRONTIER_CAMPAIGN_SCHEMA}:
        raise ValueError("campaign artifact uses an unknown packet schema")
    calculated = _digest(packet)
    if campaign.get("packet_digest") != calculated:
        raise ValueError("campaign packet digest mismatch")
    if expected_packet_digest and expected_packet_digest != calculated:
        raise ValueError("campaign packet differs from the frozen run")
    manifest = packet.get("visible_context_manifest")
    if not isinstance(manifest, Mapping) or manifest.get("context_hash") != context_hash:
        raise ValueError("campaign packet differs from the frozen context")
    if schema == FRONTIER_CAMPAIGN_SCHEMA:
        _validate_context_authority_manifest(manifest)
        navigator = packet.get("navigator_contract")
        if not isinstance(navigator, Mapping):
            raise ValueError("campaign packet has no navigator contract")
        _validate_navigator_context_authority(manifest, navigator)
    if schema == FRONTIER_CAMPAIGN_SCHEMA and packet.get("blueprint_id") != blueprint_id:
        raise ValueError("campaign packet differs from the reviewed blueprint")
    if not str(campaign.get("signature") or "") or not str(
        campaign.get("signer_ref") or ""
    ):
        raise ValueError("campaign artifact is missing signing provenance")
    return packet


def packet_for_context(
    *,
    campaign_id: str,
    blueprint_id: str,
    eigenquestion: str,
    context: TheoryLandscapeContext,
    formula_grammar: Mapping[str, Any],
    pack_arity: int,
    navigator_contract: LeafWorkbenchContract,
    sealed_context_manifest_digest: str,
    query_budget: Mapping[str, Any],
    stop_rule: Mapping[str, Any],
    collapse_controls: tuple[Mapping[str, Any], ...] = (),
    authority_refs: tuple[str, ...] = ("deterministic-host",),
    mode: str = "anonymous_signature_census",
    model_strata: tuple[Mapping[str, Any], ...] | None = None,
    codec_versions: Mapping[str, str] | None = None,
    presentation_size: Mapping[str, int] | None = None,
) -> FrontierCampaignPacket:
    context_exact = context.complete
    if type(context_exact) is not bool:
        raise ValueError("context exactness must be boolean")
    completeness_receipt = str(context.completeness_receipt_digest or "")
    if model_strata is None:
        universe = getattr(context, "universe", None)
        receipt = getattr(universe, "receipt", None)
        if receipt is not None and hasattr(receipt, "declared_strata"):
            rows = []
            for declared in receipt.declared_strata:
                stratum = dict(declared)
                if "sort_sizes" in stratum:
                    sort_sizes = dict(stratum["sort_sizes"])
                elif "carrier_size" in stratum and len(context.signature.sorts) == 1:
                    sort_sizes = {
                        context.signature.sorts[0].name: int(stratum["carrier_size"])
                    }
                else:
                    raise ValueError(
                        "finite model receipt exposes an unsupported stratum"
                    )
                stratum_id = (
                    "carrier_size:" + str(stratum["carrier_size"])
                    if "carrier_size" in stratum
                    else "sort_sizes:"
                    + ",".join(
                        f"{key}={value}"
                        for key, value in sorted(sort_sizes.items())
                    )
                )
                rows.append(
                    {
                        **stratum,
                        "labeled_interpretation_count": finite_interpretation_count(
                            context.signature, sort_sizes
                        ),
                        "canonical_accepted_model_count": sum(
                            row.stratum_id == stratum_id for row in universe.models
                        ),
                    }
                )
            model_strata = tuple(rows)
        else:
            counts: dict[str, int] = {}
            object_records = tuple(getattr(context, "object_records", ()))
            for row in object_records:
                counts[row.stratum_id] = counts.get(row.stratum_id, 0) + 1
            model_strata = tuple(
                {"stratum_id": key, "object_count": value}
                for key, value in sorted(counts.items())
            ) or ({"object_count": len(context.object_ids)},)
    active_navigator_contract = _navigator_contract_for_context(
        navigator_contract, exact=context_exact
    )
    receipt = getattr(getattr(context, "universe", None), "receipt", None)
    functor_image = bool(getattr(receipt, "functor_image_receipt", {}))
    return FrontierCampaignPacket(
        campaign_id=campaign_id,
        blueprint_id=blueprint_id,
        mode=mode,
        eigenquestion=eigenquestion,
        signature=context.signature.to_json(),
        base_axioms=tuple(row.to_json() for row in context.base_axioms),
        formula_grammar=dict(formula_grammar),
        model_strata=model_strata,
        pack_arity=pack_arity,
        visible_context_manifest={
            "context_hash": context.context_hash,
            "context_exact": context_exact,
            "claim_scope": (
                _EXACT_CONTEXT_CLAIM_SCOPE
                if context_exact
                else _SAMPLED_CONTEXT_CLAIM_SCOPE
            ),
            "census_domain": (
                "deterministic_image_of_frozen_source"
                if context_exact and functor_image
                else "all_interpretations_in_declared_strata"
                if context_exact
                else "sampled_objects"
            ),
            "permitted_semantic_uses": list(
                _PANEL_SEMANTIC_USES
                + ((_EXACT_CONTEXT_CLAIM_SCOPE,) if context_exact else ())
            ),
            "exact_closure_authority": context_exact,
            "formula_count": len(context.formula_ids),
            "canonical_model_count": (
                len(context.object_ids) if context_exact else None
            ),
            "object_count": len(context.object_ids),
            "model_census_receipt_digest": (
                completeness_receipt if context_exact else ""
            ),
            "completeness_receipt_digest": (
                completeness_receipt if context_exact else ""
            ),
            "formula_ids_digest": _digest(list(context.formula_ids)),
            "model_ids_digest": (
                _digest(list(context.object_ids)) if context_exact else ""
            ),
            "object_ids_digest": _digest(list(context.object_ids)),
            "interpretation_labels_visible": False,
        },
        sealed_context_manifest_digest=sealed_context_manifest_digest,
        collapse_controls=collapse_controls,
        navigator_contract={
            "schema": active_navigator_contract.schema,
            "fingerprint": active_navigator_contract.fingerprint(),
            "capability_ids": list(active_navigator_contract.registry()),
            **(
                {"presentation_size": dict(presentation_size)}
                if presentation_size is not None
                else {}
            ),
        },
        query_budget=dict(query_budget),
        stop_rule=dict(stop_rule),
        codec_versions=dict(codec_versions or {"model": "finite-table-v1", "context": context.schema}),
        authority_refs=authority_refs,
    )


def packet_for_exact_context(**kwargs: Any) -> FrontierCampaignPacket:
    """Compatibility door for controls whose identity is an exact census."""

    context = kwargs.get("context")
    if context is None or not context.complete:
        raise ValueError("exact campaign packet requires a complete context")
    return packet_for_context(**kwargs)


__all__ = [
    "CAMPAIGN_MODES", "FRONTIER_CAMPAIGN_SCHEMA", "FrontierCampaignPacket",
    "SignedFrontierCampaign", "packet_for_context", "packet_for_exact_context",
    "sign_frontier_campaign",
    "validate_campaign_artifact_binding", "verify_campaign_artifact_signature",
    "verify_frontier_campaign",
]
