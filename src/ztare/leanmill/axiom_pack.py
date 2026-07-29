"""Quarantined axiom-pack discovery contract.

This is a research-lane carrier, not a theorem-closing mechanism. An
`AxiomPack` can explain a proposed axiom system and its stress receipts, but it
is never proof credit and never mutates a Lean campaign theory by itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import argparse
import time
import json
import re
from pathlib import Path
from typing import Any

from ztare.leanmill.axiom_pack_semantic_screen import (
    DEFAULT_FIXED_SIZE_SMT_TIMEOUT_MS,
    normalize_fixed_size_smt_policy,
)


REPO = Path(__file__).resolve().parents[3]
DEFAULT_AXIOM_PACK_STORE = REPO / "analytics" / "public" / "queries" / "axiom_pack_candidates.jsonl"
AXIOM_PACK_SCHEMA = "leanmill.axiom_pack.v1"
AXIOM_PACK_BLUEPRINT_SCHEMA = "leanmill.axiom_pack_blueprint.v1"
AXIOM_PACK_STRESS_SCHEMA = "leanmill.axiom_pack_stress.v1"
AXIOM_PACK_BLUEPRINT_LINT_SCHEMA = "leanmill.axiom_pack_blueprint_lint.v1"
AXIOM_PACK_CANDIDATE_GENERATION_SCHEMA = "leanmill.axiom_pack_candidate_generation.v1"
AXIOM_PACK_DOWNSTREAM_YIELD_SCHEMA = "leanmill.axiom_pack_downstream_yield_replay.v1"
AXIOM_PACK_STORE_EVENT_SCHEMA = "leanmill.axiom_pack_store_event.v1"
AXIOM_PACK_THEOREM_CONSUMPTION_SCHEMA = "leanmill.axiom_pack_theorem_consumption_gate.v1"
AXIOM_PACK_MOVE_CARD_SCHEMA = "leanmill.agent_move_card.structural_isomorphism.v1"
AXIOM_PACK_USEFULNESS_SCORE_SCHEMA = "leanmill.axiom_pack_usefulness_score.v1"
AXIOM_PACK_DISCOVERY_EVAL_SCHEMA = "leanmill.axiom_pack_discovery_eval.v1"
AXIOM_PACK_AGENT_BLUEPRINT_SCHEMA = "leanmill.axiom_pack_agent_blueprint_trial.v1"
GROUP_THEORY_STRESS_SCHEMA = "leanmill.group_theory_axiom_pack_stress.v1"
AXIOM_PACK_COMPUTE_ROUTE_SCHEMA = "leanmill.axiom_pack_compute_route.v1"
AXIOM_PACK_ISOMORPHISM_FOLLOWUP_SCHEMA = "leanmill.axiom_pack_isomorphism_followups.v1"
AXIOM_PACK_BLUEPRINT_SCREEN_SCHEMA = "leanmill.axiom_pack_blueprint_screen.v1"

CHEAP_STRESS_DIMENSIONS: tuple[str, ...] = (
    "nontriviality",
    "consistency_smoke",
    "model_or_example",
    "strength_comparison",
    "separation_or_interpretation",
)

DEFAULT_CHEAP_FILTER_POLICY: dict[str, Any] = {
    "max_finite_carrier_size": 5,
    "filter_budget_k": 4,
    "require_countermodel_strata": True,
    "prune_before_downstream_yield": True,
    "semantic_min_carrier_size": 2,
    "semantic_max_carrier_size": 2,
    "semantic_max_interpretations": 100_000,
    "fixed_size_smt_timeout_ms": DEFAULT_FIXED_SIZE_SMT_TIMEOUT_MS,
}

DEFAULT_DOWNSTREAM_YIELD_POLICY: dict[str, Any] = {
    "mode": "shadow_replay",
    "max_replayed_residuals": 3,
    "proof_credit_eligible": False,
    "theorem_campaign_admissible": False,
}

FORBIDDEN_BLUEPRINT_SHORTCUT_MARKERS: tuple[str, ...] = (
    "assume target theorem",
    "axiom target theorem",
    "postulate target theorem",
    "skip stress",
    "proof credit",
    "theorem campaign may consume",
)

GENERIC_TEMPLATE_TOKENS: set[str] = {
    "axiom",
    "assoc",
    "identity",
    "inverse",
    "law",
    "property",
    "structure",
    "closure",
    "theorem",
    "lemma",
    "generic",
}

EXPENSIVE_STRESS_DIMENSIONS: tuple[str, ...] = (
    "downstream_yield",
)

REQUIRED_STRESS_DIMENSIONS: tuple[str, ...] = CHEAP_STRESS_DIMENSIONS + EXPENSIVE_STRESS_DIMENSIONS

GROUP_THEORY_STRESS_FAMILIES: tuple[str, ...] = (
    "magma",
    "semigroup",
    "inverse_semigroup",
    "left_identity",
    "right_identity",
    "monoid",
    "left_inverse",
    "right_inverse",
    "group",
    "commutative_group",
    "cancellative_semigroup",
    "quasigroup",
    "loop",
    "moufang_loop",
    "modular_lattice",
    "distributive_lattice",
)

UNDEREXPLORED_ALGEBRAIC_DOMAINS: tuple[dict[str, str], ...] = (
    {
        "domain": "inverse_semigroups",
        "why": "partial symmetries and rollback-like local inverses; cheaper novelty surface than textbook groups",
        "stress_axis": "x * inv x * x = x without global inverse collapse",
    },
    {
        "domain": "quasigroups_and_loops",
        "why": "non-associative composition forces invariants that do not depend on left-fold associativity",
        "stress_axis": "division/loop laws versus associativity and Moufang variants",
    },
    {
        "domain": "lattice_order_structures",
        "why": "single distributivity/modularity/duality axioms can change priority-queue and order-isomorphism behavior",
        "stress_axis": "minimal order axioms for uncrossed or monotone structures",
    },
)

CHEAP_FILTER_OBSERVABILITY_FIELDS: tuple[str, ...] = (
    "countermodel_size",
    "countermodel_size_bound",
    "countermodel_stratum",
    "uses_partial_or_undefined_value",
    "filter_budget_k",
    "cheap_filter_wallclock_s",
)

ISOMORPHISM_FOLLOWUP_EXPERIMENTS: tuple[dict[str, Any], ...] = (
    {
        "name": "boundary_countermodel_forced_replay",
        "mother_structure": "dual_semantics_screening_funnel",
        "claim": "boundary-size countermodel kills may be enriched for axioms true in the target semantics",
        "instrumentation": ("countermodel_size", "countermodel_size_bound", "countermodel_stratum"),
        "cheap_stage_only": False,
        "expensive_stage": "forced downstream-yield replay on a sampled killed stratum",
    },
    {
        "name": "filter_budget_yield_sweep",
        "mother_structure": "dual_semantics_screening_funnel",
        "claim": "larger small-model bounds can reduce validated yield per compute after a domain-specific optimum",
        "instrumentation": ("filter_budget_k", "survivor_count", "validated_yield", "compute_s"),
        "cheap_stage_only": False,
        "expensive_stage": "frozen-candidate yield replay across k settings",
    },
    {
        "name": "membrane_breach_goodhart_ab",
        "mother_structure": "goodhart_firewall",
        "claim": "conditioning the proposer on its own survivors can raise cheap pass rate while lowering target yield",
        "instrumentation": ("cheap_pass_rate", "yield_per_survivor", "schema_diversity"),
        "cheap_stage_only": False,
        "expensive_stage": "A/B replay with proposer-survivor feedback enabled only in the breach arm",
    },
)


@dataclass(frozen=True)
class AxiomPack:
    name: str
    domain: str
    extends_theory: str
    candidate_axioms: list[dict[str, Any]]
    intended_unlocks: list[str]
    provenance: list[str]
    downstream_residuals: list[str]
    theory_signature: dict[str, Any] = field(default_factory=dict)
    base_axioms: list[dict[str, Any]] = field(default_factory=list)
    base_theory_resolved: bool = False
    stress_receipts: list[dict[str, Any]] = field(default_factory=list)
    promotion_status: str = "quarantined"
    schema: str = AXIOM_PACK_SCHEMA

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> "AxiomPack":
        return cls(
            name=str(obj.get("name") or ""),
            domain=str(obj.get("domain") or ""),
            extends_theory=str(obj.get("extends_theory") or ""),
            candidate_axioms=[x for x in obj.get("candidate_axioms") or [] if isinstance(x, dict)],
            intended_unlocks=[str(x) for x in obj.get("intended_unlocks") or [] if str(x).strip()],
            provenance=[str(x) for x in obj.get("provenance") or [] if str(x).strip()],
            downstream_residuals=[str(x) for x in obj.get("downstream_residuals") or [] if str(x).strip()],
            theory_signature=(
                dict(obj.get("theory_signature"))
                if isinstance(obj.get("theory_signature"), dict)
                else {}
            ),
            base_axioms=[x for x in obj.get("base_axioms") or [] if isinstance(x, dict)],
            base_theory_resolved=obj.get("base_theory_resolved") is True,
            stress_receipts=[x for x in obj.get("stress_receipts") or [] if isinstance(x, dict)],
            promotion_status=str(obj.get("promotion_status") or "quarantined"),
            schema=str(obj.get("schema") or AXIOM_PACK_SCHEMA),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "name": self.name,
            "domain": self.domain,
            "extends_theory": self.extends_theory,
            "candidate_axioms": self.candidate_axioms,
            "intended_unlocks": self.intended_unlocks,
            "provenance": self.provenance,
            "downstream_residuals": self.downstream_residuals,
            "theory_signature": self.theory_signature,
            "base_axioms": self.base_axioms,
            "base_theory_resolved": self.base_theory_resolved,
            "stress_receipts": self.stress_receipts,
            "promotion_status": self.promotion_status,
            "proof_credit_eligible": False,
            "theorem_campaign_admissible": False,
        }


@dataclass(frozen=True)
class AxiomPackBlueprint:
    name: str
    domain: str
    nl_statement: str
    semantic_intent: str
    target_structure_family: str
    current_theory: str
    residuals: list[str]
    forbidden_shortcuts: list[str]
    candidate_axiom_templates: list[dict[str, Any]]
    theory_signature: dict[str, Any] = field(default_factory=dict)
    base_axioms: list[dict[str, Any]] = field(default_factory=list)
    base_theory_resolved: bool = False
    cheap_filter_policy: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_CHEAP_FILTER_POLICY))
    downstream_yield_policy: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_DOWNSTREAM_YIELD_POLICY))
    provenance: list[str] = field(default_factory=list)
    schema: str = AXIOM_PACK_BLUEPRINT_SCHEMA

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> "AxiomPackBlueprint":
        return cls(
            name=str(obj.get("name") or ""),
            domain=str(obj.get("domain") or ""),
            nl_statement=str(obj.get("nl_statement") or ""),
            semantic_intent=str(obj.get("semantic_intent") or ""),
            target_structure_family=str(obj.get("target_structure_family") or ""),
            current_theory=str(obj.get("current_theory") or ""),
            residuals=[str(x) for x in obj.get("residuals") or [] if str(x).strip()],
            forbidden_shortcuts=[str(x) for x in obj.get("forbidden_shortcuts") or [] if str(x).strip()],
            candidate_axiom_templates=[x for x in obj.get("candidate_axiom_templates") or [] if isinstance(x, dict)],
            theory_signature=(
                dict(obj.get("theory_signature"))
                if isinstance(obj.get("theory_signature"), dict)
                else {}
            ),
            base_axioms=[x for x in obj.get("base_axioms") or [] if isinstance(x, dict)],
            base_theory_resolved=obj.get("base_theory_resolved") is True,
            cheap_filter_policy=(
                dict(obj.get("cheap_filter_policy"))
                if isinstance(obj.get("cheap_filter_policy"), dict)
                else dict(DEFAULT_CHEAP_FILTER_POLICY)
            ),
            downstream_yield_policy=(
                dict(obj.get("downstream_yield_policy"))
                if isinstance(obj.get("downstream_yield_policy"), dict)
                else dict(DEFAULT_DOWNSTREAM_YIELD_POLICY)
            ),
            provenance=[str(x) for x in obj.get("provenance") or [] if str(x).strip()],
            schema=str(obj.get("schema") or AXIOM_PACK_BLUEPRINT_SCHEMA),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "name": self.name,
            "domain": self.domain,
            "nl_statement": self.nl_statement,
            "semantic_intent": self.semantic_intent,
            "target_structure_family": self.target_structure_family,
            "current_theory": self.current_theory,
            "residuals": self.residuals,
            "forbidden_shortcuts": self.forbidden_shortcuts,
            "candidate_axiom_templates": self.candidate_axiom_templates,
            "theory_signature": self.theory_signature,
            "base_axioms": self.base_axioms,
            "base_theory_resolved": self.base_theory_resolved,
            "cheap_filter_policy": self.cheap_filter_policy,
            "downstream_yield_policy": self.downstream_yield_policy,
            "provenance": self.provenance,
        }


def _normalized_cheap_filter_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise ValueError("cheap_filter_policy must be an object")
    merged = {**DEFAULT_CHEAP_FILTER_POLICY, **policy}
    for key in (
        "semantic_min_carrier_size",
        "semantic_max_carrier_size",
        "semantic_max_interpretations",
    ):
        value = merged.get(key)
        if type(value) is not int or value < 1:
            raise ValueError(f"{key} must be a positive integer")
    if merged["semantic_min_carrier_size"] > merged["semantic_max_carrier_size"]:
        raise ValueError(
            "semantic_min_carrier_size must not exceed semantic_max_carrier_size"
        )
    for key in ("require_countermodel_strata", "prune_before_downstream_yield"):
        if type(merged.get(key)) is not bool:
            raise ValueError(f"{key} must be boolean")
    normalize_fixed_size_smt_policy(merged)
    return merged


def lint_axiom_pack_blueprint(blueprint: AxiomPackBlueprint | dict[str, Any]) -> dict[str, Any]:
    if isinstance(blueprint, dict):
        blueprint = AxiomPackBlueprint.from_json(blueprint)
    missing: list[str] = []
    for key, value in (
        ("name", blueprint.name),
        ("domain", blueprint.domain),
        ("nl_statement", blueprint.nl_statement),
        ("semantic_intent", blueprint.semantic_intent),
        ("target_structure_family", blueprint.target_structure_family),
        ("current_theory", blueprint.current_theory),
        ("residuals", blueprint.residuals),
        ("forbidden_shortcuts", blueprint.forbidden_shortcuts),
        ("candidate_axiom_templates", blueprint.candidate_axiom_templates),
        ("theory_signature", blueprint.theory_signature),
        ("cheap_filter_policy", blueprint.cheap_filter_policy),
        ("downstream_yield_policy", blueprint.downstream_yield_policy),
    ):
        if not value:
            missing.append(key)
    violations: list[str] = []
    if blueprint.schema != AXIOM_PACK_BLUEPRINT_SCHEMA:
        violations.append("wrong_schema")
    haystack = "\n".join([
        blueprint.nl_statement,
        blueprint.semantic_intent,
        "\n".join(blueprint.forbidden_shortcuts),
        json.dumps(blueprint.candidate_axiom_templates, sort_keys=True),
    ]).lower()
    for marker in FORBIDDEN_BLUEPRINT_SHORTCUT_MARKERS:
        if marker in haystack and marker not in "\n".join(blueprint.forbidden_shortcuts).lower():
            violations.append(f"shortcut_marker:{marker}")
    if blueprint.downstream_yield_policy.get("proof_credit_eligible") is not False:
        violations.append("downstream_yield_must_not_grant_proof_credit")
    if blueprint.downstream_yield_policy.get("theorem_campaign_admissible") is not False:
        violations.append("downstream_yield_must_not_be_theorem_admissible")
    if not blueprint.cheap_filter_policy.get("prune_before_downstream_yield"):
        violations.append("cheap_filter_must_precede_yield")
    try:
        _normalized_cheap_filter_policy(blueprint.cheap_filter_policy)
    except (TypeError, ValueError) as exc:
        violations.append(f"cheap_filter_policy:{exc}")
    if blueprint.base_theory_resolved is not True:
        violations.append("base_theory_must_be_resolved_to_typed_axioms_or_explicit_empty_base")
    template_names = [str(t.get("name") or "") for t in blueprint.candidate_axiom_templates]
    if len(set(template_names)) != len([n for n in template_names if n]):
        violations.append("duplicate_or_empty_template_name")
    formal_axiom_hashes: list[str] = []
    base_axiom_hashes: list[str] = []
    theory_signature_hash = ""
    try:
        from ztare.leanmill.theory_ir import (
            AxiomFormula,
            TheorySignature,
            validate_axioms,
        )

        signature = TheorySignature.from_json(blueprint.theory_signature)
        base_axioms = []
        for base_axiom in blueprint.base_axioms:
            if not isinstance(base_axiom.get("formula"), dict):
                raise ValueError(f"base axiom {base_axiom.get('name')!r} has no typed formula")
            base_axioms.append(
                AxiomFormula.from_json(
                    {"name": base_axiom.get("name"), "formula": base_axiom.get("formula")}
                )
            )
        formal_axioms = []
        for template in blueprint.candidate_axiom_templates:
            if not isinstance(template.get("formula"), dict):
                raise ValueError(f"candidate {template.get('name')!r} has no typed formula")
            formal_axioms.append(
                AxiomFormula.from_json(
                    {"name": template.get("name"), "formula": template.get("formula")}
                )
            )
        validate_axioms(signature, [*base_axioms, *formal_axioms])
        theory_signature_hash = signature.content_hash
        base_axiom_hashes = [axiom.content_hash for axiom in base_axioms]
        formal_axiom_hashes = [axiom.content_hash for axiom in formal_axioms]
    except (TypeError, ValueError) as exc:
        violations.append(f"typed_formula_ir:{exc}")
    ok = not missing and not violations
    return {
        "schema": AXIOM_PACK_BLUEPRINT_LINT_SCHEMA,
        "ok": ok,
        "blueprint_name": blueprint.name,
        "missing_fields": missing,
        "violations": violations,
        "required_receipts": list(REQUIRED_STRESS_DIMENSIONS),
        "cheap_filter_policy": blueprint.cheap_filter_policy,
        "downstream_yield_policy": blueprint.downstream_yield_policy,
        "theory_signature_hash": theory_signature_hash,
        "formal_axiom_hashes": formal_axiom_hashes,
        "base_axiom_hashes": base_axiom_hashes,
    }


def group_theory_stress_plan() -> dict[str, Any]:
    return {
        "schema": GROUP_THEORY_STRESS_SCHEMA,
        "domain": "algebraic_axiom_packs",
        "families": list(GROUP_THEORY_STRESS_FAMILIES),
        "underexplored_domains": list(UNDEREXPLORED_ALGEBRAIC_DOMAINS),
        "required_receipts": list(REQUIRED_STRESS_DIMENSIONS),
        "cheap_filter_receipts": list(CHEAP_STRESS_DIMENSIONS),
        "expensive_receipts": list(EXPENSIVE_STRESS_DIMENSIONS),
        "yield_test_rule": "run downstream proof-DAG yield only after cheap filters pass",
        "cheap_filter_prune_target": 0.95,
        "cheap_filter_observability_fields": list(CHEAP_FILTER_OBSERVABILITY_FIELDS),
        "purpose": "cheap small-model and implication/separation stress for candidate algebraic axiom packs",
    }


def research_isomorphism_followups() -> dict[str, Any]:
    return {
        "schema": AXIOM_PACK_ISOMORPHISM_FOLLOWUP_SCHEMA,
        "source": "research_isomorphism --mode conjecture over AxiomPack lane vs CEGIS/spec-mining",
        "followups": list(ISOMORPHISM_FOLLOWUP_EXPERIMENTS),
        "design_implications": [
            "record countermodel strata instead of a bare killed/survived bit",
            "treat downstream-yield replay as a sampled expensive audit, not the universal first filter",
            "keep proposer learning from survivor packs behind an explicit Goodhart A/B membrane",
        ],
    }


def compute_route_for_pack(pack: AxiomPack, receipt_dims: set[str]) -> dict[str, Any]:
    missing_cheap = [d for d in CHEAP_STRESS_DIMENSIONS if d not in receipt_dims]
    missing_expensive = [d for d in EXPENSIVE_STRESS_DIMENSIONS if d not in receipt_dims]
    cheap_filter_ok = not missing_cheap
    return {
        "schema": AXIOM_PACK_COMPUTE_ROUTE_SCHEMA,
        "cheap_filter_ok": cheap_filter_ok,
        "yield_test_admissible": cheap_filter_ok,
        "yield_test_completed": not missing_expensive,
        "missing_cheap_receipts": missing_cheap,
        "missing_expensive_receipts": missing_expensive,
        "cheap_filter_prune_target": 0.95,
        "cheap_filter_observability_fields": list(CHEAP_FILTER_OBSERVABILITY_FIELDS),
        "route": (
            "run_downstream_yield"
            if cheap_filter_ok and not missing_expensive
            else "cheap_filter_first"
            if not cheap_filter_ok
            else "eligible_for_downstream_yield"
        ),
        "note": "downstream-yield replay is the expensive stage and must not run for candidates killed by cheap receipts",
        "pack_name": pack.name,
        "isomorphism_followups": research_isomorphism_followups(),
    }


def theorem_campaign_consumption_gate(
    pack: AxiomPack | dict[str, Any],
    ratification_receipt: dict[str, Any] | None = None,
    *,
    trusted_public_key_pem: str | None = None,
    trusted_base_resolver_public_key_pem: str | None = None,
    trusted_task_manifest_public_key_pem: str | None = None,
    trusted_shadow_checker_public_key_pem: str | None = None,
    trusted_lowering_checker_public_key_pem: str | None = None,
    trusted_semantic_fidelity_public_key_pem: str | None = None,
) -> dict[str, Any]:
    if isinstance(pack, dict):
        pack = AxiomPack.from_json(pack)
    receipt = ratification_receipt if isinstance(ratification_receipt, dict) else {}
    try:
        from ztare.leanmill.axiom_authority import verify_ratification_receipt

        verification = verify_ratification_receipt(
            pack=pack,
            receipt=receipt,
            trusted_public_key_pem=trusted_public_key_pem,
            trusted_base_resolver_public_key_pem=trusted_base_resolver_public_key_pem,
            trusted_task_manifest_public_key_pem=trusted_task_manifest_public_key_pem,
            trusted_shadow_checker_public_key_pem=trusted_shadow_checker_public_key_pem,
            trusted_lowering_checker_public_key_pem=trusted_lowering_checker_public_key_pem,
            trusted_semantic_fidelity_public_key_pem=trusted_semantic_fidelity_public_key_pem,
        )
    except Exception as exc:  # noqa: BLE001 - consumption fails closed
        verification = {"allowed": False, "failures": [f"verification_error:{exc}"]}
    allowed = pack.promotion_status == "promoted" and verification.get("allowed") is True
    return {
        "schema": AXIOM_PACK_THEOREM_CONSUMPTION_SCHEMA,
        "pack_name": pack.name,
        "promotion_status": pack.promotion_status,
        "allowed": allowed,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": allowed,
        "reason": (
            "signed_content_bound_ratification_verified"
            if allowed
            else "unpromoted_or_unverified_ratification"
        ),
        "ratification_verification": verification,
    }


def promote_axiom_pack(
    pack: AxiomPack | dict[str, Any],
    ratification_receipt: dict[str, Any],
    *,
    trusted_public_key_pem: str,
    trusted_base_resolver_public_key_pem: str,
    trusted_task_manifest_public_key_pem: str,
    trusted_shadow_checker_public_key_pem: str,
    trusted_lowering_checker_public_key_pem: str,
    trusted_semantic_fidelity_public_key_pem: str | None = None,
) -> AxiomPack:
    """Return the promoted read model only after signed receipt verification."""

    if isinstance(pack, dict):
        pack = AxiomPack.from_json(pack)
    if pack.promotion_status != "quarantined":
        raise ValueError("only a quarantined pack can enter promotion")
    candidate = replace(pack, promotion_status="promoted")
    gate = theorem_campaign_consumption_gate(
        candidate,
        ratification_receipt,
        trusted_public_key_pem=trusted_public_key_pem,
        trusted_base_resolver_public_key_pem=trusted_base_resolver_public_key_pem,
        trusted_task_manifest_public_key_pem=trusted_task_manifest_public_key_pem,
        trusted_shadow_checker_public_key_pem=trusted_shadow_checker_public_key_pem,
        trusted_lowering_checker_public_key_pem=trusted_lowering_checker_public_key_pem,
        trusted_semantic_fidelity_public_key_pem=trusted_semantic_fidelity_public_key_pem,
    )
    if gate.get("allowed") is not True:
        failures = gate.get("ratification_verification", {}).get("failures") or []
        raise ValueError(f"ratification verification failed: {failures}")
    return candidate


def _pack_formal_theory(
    pack: AxiomPack,
) -> tuple[Any, list[Any], list[Any]]:
    from ztare.leanmill.theory_ir import AxiomFormula, TheorySignature, validate_axioms

    if pack.base_theory_resolved is not True:
        raise ValueError("base theory has not been resolved to typed axioms or an explicit empty base")
    signature = TheorySignature.from_json(pack.theory_signature)

    def parse(rows: list[dict[str, Any]], kind: str) -> list[Any]:
        out = []
        for row in rows:
            if not isinstance(row.get("formula"), dict):
                raise ValueError(f"{kind} {row.get('name')!r} has no typed formula")
            out.append(
                AxiomFormula.from_json(
                    {"name": row.get("name"), "formula": row.get("formula")}
                )
            )
        return out

    base_axioms = parse(pack.base_axioms, "base axiom")
    candidate_axioms = parse(pack.candidate_axioms, "candidate axiom")
    if not candidate_axioms:
        raise ValueError("pack has no typed candidate axioms")
    validate_axioms(signature, [*base_axioms, *candidate_axioms])
    return signature, base_axioms, candidate_axioms


def _semantic_dimension_receipt(
    *,
    pack: AxiomPack,
    dimension: str,
    passed: bool,
    suite: dict[str, Any],
    evidence: Any,
    fixed_size_smt_screen: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from ztare.leanmill.axiom_authority import pack_digest
    from ztare.leanmill.theory_ir import content_hash

    core = {
        "schema": "leanmill.axiom_pack_semantic_dimension.v1",
        "dimension": dimension,
        "status": "pass" if passed else "fail",
        "pack_digest": pack_digest(pack),
        "theory_digest": suite.get("theory_digest"),
        "semantic_suite_digest": suite.get("certificate_digest"),
        "evidence": evidence,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    if fixed_size_smt_screen is not None:
        core["fixed_size_smt_screen_digest"] = fixed_size_smt_screen.get(
            "receipt_sha256"
        )
    return {**core, "receipt_sha256": content_hash(core)}


def run_semantic_cheap_filters(
    pack: AxiomPack,
    *,
    min_carrier_size: int = 2,
    max_carrier_size: int = 2,
    max_interpretations: int = 100_000,
    fixed_size_smt_policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run enumerative semantics plus the optional fixed-size SMT extension."""

    from ztare.leanmill.finite_model import (
        CERTIFIED_WITH_WITNESSES,
        INDEPENDENCE_WITNESS,
        SAT,
        FiniteSearchBounds,
        certify_theory,
    )
    from ztare.leanmill.axiom_authority import pack_digest
    from ztare.leanmill.theory_ir import content_hash

    signature, base_axioms, candidate_axioms = _pack_formal_theory(pack)
    bounds = FiniteSearchBounds(
        min_carrier_size=min_carrier_size,
        max_carrier_size=max_carrier_size,
        max_interpretations=max_interpretations,
    )
    suite = certify_theory(
        signature,
        candidate_axioms,
        bounds,
        base_axioms=base_axioms,
    ).to_json()
    fixed_size_smt_screen = None
    if fixed_size_smt_policy is not None:
        from ztare.leanmill.axiom_pack_semantic_screen import (
            run_fixed_size_smt_screen,
        )

        fixed_size_smt_screen = run_fixed_size_smt_screen(
            pack=pack,
            signature=signature,
            base_axioms=base_axioms,
            candidate_axioms=candidate_axioms,
            policy=fixed_size_smt_policy,
        )
    joint = suite.get("joint_satisfiability") or {}
    witness = joint.get("witness") if isinstance(joint, dict) else None
    model = witness.get("model") if isinstance(witness, dict) else {}
    sort_sizes = model.get("sort_sizes") if isinstance(model, dict) else {}
    nontrivial = bool(sort_sizes) and any(
        isinstance(size, int) and size > 1 for size in sort_sizes.values()
    )
    independence = [
        row for row in suite.get("independence") or [] if isinstance(row, dict)
    ]
    witnessed_independence = [
        row for row in independence if row.get("status") == INDEPENDENCE_WITNESS
    ]
    separation_edges = [
        {
            "background": row.get("details", {}).get("background_axioms") or [],
            "does_not_imply": row.get("details", {}).get("target_axiom"),
            "witness_model_sha256": row.get("witness", {}).get("model_sha256"),
        }
        for row in witnessed_independence
    ]
    fixed_summary = (
        fixed_size_smt_screen.get("summary")
        if isinstance(fixed_size_smt_screen, dict)
        else {}
    ) or {}
    fixed_countermodel_edges = [
        row
        for row in fixed_summary.get("countermodel_edges") or []
        if isinstance(row, dict)
    ]
    fixed_implication_edges = [
        row
        for row in fixed_summary.get("fixed_size_implication_edges") or []
        if isinstance(row, dict)
    ]
    certified = suite.get("status") == CERTIFIED_WITH_WITNESSES
    receipts = [
        _semantic_dimension_receipt(
            pack=pack,
            dimension="nontriviality",
            passed=joint.get("status") == SAT and nontrivial,
            suite=suite,
            evidence={"joint_status": joint.get("status"), "sort_sizes": sort_sizes},
            fixed_size_smt_screen=fixed_size_smt_screen,
        ),
        _semantic_dimension_receipt(
            pack=pack,
            dimension="consistency_smoke",
            passed=joint.get("status") == SAT and bool(witness),
            suite=suite,
            evidence={"joint_receipt_sha256": joint.get("receipt_sha256")},
            fixed_size_smt_screen=fixed_size_smt_screen,
        ),
        _semantic_dimension_receipt(
            pack=pack,
            dimension="model_or_example",
            passed=joint.get("status") == SAT and bool(witness),
            suite=suite,
            evidence=witness or {},
            fixed_size_smt_screen=fixed_size_smt_screen,
        ),
        _semantic_dimension_receipt(
            pack=pack,
            dimension="strength_comparison",
            passed=bool(separation_edges or fixed_countermodel_edges),
            suite=suite,
            evidence={
                "enumerative_edges": separation_edges,
                "fixed_size_countermodel_edges": fixed_countermodel_edges,
                "fixed_size_implication_edges": fixed_implication_edges,
            },
            fixed_size_smt_screen=fixed_size_smt_screen,
        ),
        _semantic_dimension_receipt(
            pack=pack,
            dimension="separation_or_interpretation",
            passed=(
                certified and len(witnessed_independence) == len(candidate_axioms)
            )
            or bool(
                fixed_size_smt_screen
                and fixed_size_smt_screen.get("status") == "pass"
            ),
            suite=suite,
            evidence={
                "witnessed": len(witnessed_independence),
                "candidate_count": len(candidate_axioms),
                "receipt_sha256s": [row.get("receipt_sha256") for row in independence],
                "fixed_size_smt_screen_digest": (
                    fixed_size_smt_screen.get("receipt_sha256")
                    if fixed_size_smt_screen
                    else ""
                ),
                "fixed_size_candidate_outcomes": fixed_summary.get(
                    "candidate_outcomes"
                )
                or [],
            },
            fixed_size_smt_screen=fixed_size_smt_screen,
        ),
    ]
    suite_core = {
        "schema": "leanmill.axiom_pack_semantic_certification.v1",
        "dimension": "semantic_certification",
        "status": "pass" if certified else "fail",
        "pack_digest": pack_digest(pack),
        "suite": suite,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    if fixed_size_smt_screen is not None:
        suite_core["fixed_size_smt_screen"] = fixed_size_smt_screen
    receipts.append({**suite_core, "receipt_sha256": content_hash(suite_core)})
    return receipts


def _validate_stress_receipt(
    pack: AxiomPack,
    receipt: dict[str, Any],
    *,
    trusted_task_manifest_public_key_pem: str | None,
    trusted_shadow_checker_public_key_pem: str | None,
    semantic_suite_digest: str = "",
    fixed_size_smt_screen_digest: str = "",
) -> tuple[bool, str]:
    from ztare.leanmill.axiom_authority import pack_digest
    from ztare.leanmill.theory_ir import content_hash

    dimension = str(receipt.get("dimension") or "")
    if receipt.get("status") != "pass":
        return False, "status_not_pass"
    if receipt.get("pack_digest") != pack_digest(pack):
        return False, "pack_digest_mismatch"
    if dimension in CHEAP_STRESS_DIMENSIONS:
        if receipt.get("schema") != "leanmill.axiom_pack_semantic_dimension.v1":
            return False, "nonsemantic_cheap_receipt"
        unsigned = dict(receipt)
        expected = unsigned.pop("receipt_sha256", None)
        if expected != content_hash(unsigned):
            return False, "receipt_hash_mismatch"
        if not receipt.get("semantic_suite_digest") or not receipt.get("theory_digest"):
            return False, "semantic_binding_missing"
        if receipt.get("semantic_suite_digest") != semantic_suite_digest:
            return False, "semantic_suite_digest_mismatch"
        declared_screen_digest = str(
            receipt.get("fixed_size_smt_screen_digest") or ""
        )
        if declared_screen_digest != fixed_size_smt_screen_digest:
            return False, "fixed_size_smt_screen_digest_mismatch"
        return True, "validated_semantic_receipt"
    if dimension == "downstream_yield":
        from ztare.leanmill.axiom_yield import (
            SHADOW_YIELD_SCHEMA,
            verify_shadow_yield_receipt,
        )

        if receipt.get("schema") != SHADOW_YIELD_SCHEMA:
            return False, "nonshadow_yield_receipt"
        if not verify_shadow_yield_receipt(
            receipt,
            trusted_checker_public_key_pem=trusted_shadow_checker_public_key_pem,
            trusted_manifest_public_key_pem=trusted_task_manifest_public_key_pem,
        ):
            return False, "shadow_checker_verification_failed"
        return True, "validated_shadow_yield_receipt"
    return False, "unsupported_dimension"


def _verified_semantic_suite(
    pack: AxiomPack,
    receipts: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str]:
    from ztare.leanmill.axiom_authority import pack_digest
    from ztare.leanmill.finite_model import (
        SAT,
        FiniteModel,
        evaluate_axiom,
        verify_certified_theory_suite,
        verify_receipt_hash,
        verify_theory_suite_hash,
    )
    from ztare.leanmill.theory_ir import content_hash, relative_theory_content_hash

    rows = [row for row in receipts if row.get("dimension") == "semantic_certification"]
    if len(rows) != 1:
        return None, "semantic_certification_receipt_count"
    row = rows[0]
    unsigned = dict(row)
    expected_hash = unsigned.pop("receipt_sha256", None)
    if expected_hash != content_hash(unsigned):
        return None, "semantic_certification_receipt_hash"
    if row.get("pack_digest") != pack_digest(pack):
        return None, "semantic_certification_pack_digest"
    suite = row.get("suite")
    if not isinstance(suite, dict):
        return None, "semantic_suite_missing"
    try:
        signature, base_axioms, candidate_axioms = _pack_formal_theory(pack)
        if row.get("status") == "pass":
            verified, errors = verify_certified_theory_suite(
                signature,
                candidate_axioms,
                suite,
                base_axioms=base_axioms,
            )
            if not verified:
                return None, f"semantic_suite_replay_failed:{','.join(errors)}"
            return suite, "validated_semantic_suite"

        inputs = suite.get("input_hashes") or {}
        expected_theory = relative_theory_content_hash(
            signature, candidate_axioms, base_axioms=base_axioms
        )
        if (
            not verify_theory_suite_hash(suite)
            or suite.get("theory_digest") != expected_theory
            or inputs.get("signature_sha256") != signature.content_hash
            or inputs.get("base_axiom_sha256s")
            != sorted(axiom.content_hash for axiom in base_axioms)
            or inputs.get("axiom_sha256s")
            != sorted(axiom.content_hash for axiom in candidate_axioms)
        ):
            return None, "partial_semantic_suite_binding"
        joint = suite.get("joint_satisfiability") or {}
        witness = joint.get("witness") or {}
        model = FiniteModel.from_json(witness.get("model") or {})
        if (
            joint.get("status") != SAT
            or not verify_receipt_hash(joint)
            or witness.get("model_sha256") != model.content_hash(signature)
            or not all(
                evaluate_axiom(signature, axiom, model)
                for axiom in [*base_axioms, *candidate_axioms]
            )
        ):
            return None, "partial_semantic_joint_witness"
        return suite, "validated_joint_witness_only"
    except (TypeError, ValueError) as exc:
        return None, f"semantic_suite_replay_error:{exc}"


def _verified_fixed_size_smt_screen(
    pack: AxiomPack,
    receipts: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str]:
    rows = [row for row in receipts if row.get("dimension") == "semantic_certification"]
    if len(rows) != 1:
        return None, "semantic_certification_receipt_count"
    screen = rows[0].get("fixed_size_smt_screen")
    if screen is None:
        return None, "not_present"
    if not isinstance(screen, dict):
        return None, "fixed_size_smt_screen_not_object"
    try:
        from ztare.leanmill.axiom_pack_semantic_screen import (
            verify_fixed_size_smt_screen,
        )

        signature, base_axioms, candidate_axioms = _pack_formal_theory(pack)
        valid, failures = verify_fixed_size_smt_screen(
            pack=pack,
            signature=signature,
            base_axioms=base_axioms,
            candidate_axioms=candidate_axioms,
            receipt=screen,
        )
    except (TypeError, ValueError) as exc:
        return None, f"fixed_size_smt_screen_replay_error:{exc}"
    if not valid:
        return None, "fixed_size_smt_screen_replay_failed:" + ",".join(failures)
    return screen, "validated_fixed_size_smt_screen"


def stress_axiom_pack(
    pack: AxiomPack | dict[str, Any],
    *,
    trusted_task_manifest_public_key_pem: str | None = None,
    trusted_shadow_checker_public_key_pem: str | None = None,
) -> dict[str, Any]:
    if isinstance(pack, dict):
        pack = AxiomPack.from_json(pack)
    from ztare.leanmill.axiom_authority import pack_digest as _pack_digest
    by_dimension: dict[str, list[dict[str, Any]]] = {}
    for receipt in pack.stress_receipts:
        if isinstance(receipt, dict):
            by_dimension.setdefault(str(receipt.get("dimension") or ""), []).append(receipt)
    semantic_suite, semantic_reason = _verified_semantic_suite(pack, pack.stress_receipts)
    semantic_suite_digest = str((semantic_suite or {}).get("certificate_digest") or "")
    fixed_size_smt_screen, fixed_size_smt_reason = _verified_fixed_size_smt_screen(
        pack, pack.stress_receipts
    )
    fixed_size_smt_screen_digest = str(
        (fixed_size_smt_screen or {}).get("receipt_sha256") or ""
    )
    fixed_size_smt_declared = any(
        row.get("dimension") == "semantic_certification"
        and row.get("fixed_size_smt_screen") is not None
        for row in pack.stress_receipts
        if isinstance(row, dict)
    )
    validated_receipts: list[dict[str, Any]] = []
    valid_dimensions: set[str] = set()
    invalid_receipts: list[dict[str, Any]] = []
    for dimension in REQUIRED_STRESS_DIMENSIONS:
        rows = by_dimension.get(dimension, [])
        if len(rows) != 1:
            if len(rows) > 1:
                invalid_receipts.append({
                    "dimension": dimension,
                    "reason": "duplicate_dimension_receipts",
                    "count": len(rows),
                })
            continue
        valid, reason = _validate_stress_receipt(
            pack,
            rows[0],
            trusted_task_manifest_public_key_pem=trusted_task_manifest_public_key_pem,
            trusted_shadow_checker_public_key_pem=trusted_shadow_checker_public_key_pem,
            semantic_suite_digest=semantic_suite_digest,
            fixed_size_smt_screen_digest=fixed_size_smt_screen_digest,
        )
        if dimension in CHEAP_STRESS_DIMENSIONS:
            if semantic_suite is None:
                valid, reason = False, semantic_reason
            elif fixed_size_smt_declared and fixed_size_smt_screen is None:
                valid, reason = False, fixed_size_smt_reason
        validation = {
            "dimension": dimension,
            "status": "pass" if valid else "fail",
            "reason": reason,
            "receipt_sha256": rows[0].get("receipt_sha256") or rows[0].get("receipt_digest"),
        }
        validated_receipts.append(validation)
        if valid:
            valid_dimensions.add(dimension)
        else:
            invalid_receipts.append(validation)
    compute_route = compute_route_for_pack(pack, valid_dimensions)
    missing = []
    if pack.schema != AXIOM_PACK_SCHEMA:
        missing.append("schema")
    if pack.promotion_status != "quarantined":
        missing.append("promotion_status_quarantined")
    for key, value in (
        ("name", pack.name),
        ("domain", pack.domain),
        ("extends_theory", pack.extends_theory),
        ("candidate_axioms", pack.candidate_axioms),
        ("intended_unlocks", pack.intended_unlocks),
        ("provenance", pack.provenance),
        ("downstream_residuals", pack.downstream_residuals),
        ("theory_signature", pack.theory_signature),
    ):
        if not value:
            missing.append(key)
    if pack.base_theory_resolved is not True:
        missing.append("base_theory_resolved")
    missing_receipts = [d for d in REQUIRED_STRESS_DIMENSIONS if d not in valid_dimensions]
    ok = not missing and not missing_receipts and not invalid_receipts
    return {
        "schema": AXIOM_PACK_STRESS_SCHEMA,
        "ok": ok,
        "pack_name": pack.name,
        "pack_digest": _pack_digest(pack),
        "domain": pack.domain,
        "promotion_status": pack.promotion_status,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
        "missing_fields": missing,
        "missing_stress_receipts": missing_receipts,
        "stress_receipt_dimensions": sorted(valid_dimensions),
        "validated_receipts": validated_receipts,
        "invalid_stress_receipts": invalid_receipts,
        "semantic_certification": {
            "status": (
                "pass"
                if semantic_reason == "validated_semantic_suite"
                else "partial"
                if semantic_suite is not None
                else "fail"
            ),
            "reason": semantic_reason,
            "certificate_digest": semantic_suite_digest,
        },
        "fixed_size_smt_screen": {
            "validation_status": (
                "pass"
                if fixed_size_smt_reason == "validated_fixed_size_smt_screen"
                else "not_present"
                if fixed_size_smt_reason == "not_present"
                else "fail"
            ),
            "reason": fixed_size_smt_reason,
            "screen_status": (fixed_size_smt_screen or {}).get("status"),
            "receipt_sha256": fixed_size_smt_screen_digest,
            "verdict_counts": (
                (fixed_size_smt_screen or {}).get("summary") or {}
            ).get("verdict_counts")
            or {},
        },
        "compute_route": compute_route,
        "theorem_consumption_gate": theorem_campaign_consumption_gate(pack),
        "group_theory_plan": group_theory_stress_plan() if pack.domain.lower().replace("-", "_") == "group_theory" else None,
    }


def _priority_typed_surface() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    from ztare.leanmill.theory_ir import (
        AxiomFormula,
        Binder,
        Formula,
        OperationSymbol,
        RelationSymbol,
        SortDecl,
        Term,
        TheorySignature,
    )

    signature = TheorySignature(
        name="PriorityLattice",
        sorts=(SortDecl("Element"),),
        operations=(
            OperationSymbol("meet", ("Element", "Element"), "Element"),
            OperationSymbol("join", ("Element", "Element"), "Element"),
        ),
        relations=(
            RelationSymbol("le", ("Element", "Element")),
            RelationSymbol("priority", ("Element", "Element")),
        ),
    )
    x, y, z = Term.var("x"), Term.var("y"), Term.var("z")
    bind1 = (Binder("x", "Element"),)
    bind2 = (Binder("x", "Element"), Binder("y", "Element"))
    bind3 = (*bind2, Binder("z", "Element"))
    meet = lambda a, b: Term.app("meet", a, b)
    join = lambda a, b: Term.app("join", a, b)
    rel = lambda name, a, b: Formula.rel(name, a, b)

    def axiom(name: str, body: Any) -> AxiomFormula:
        return AxiomFormula(name, body)

    base = [
        axiom("meet_comm", Formula.forall(bind2, Formula.eq(meet(x, y), meet(y, x)))),
        axiom("join_comm", Formula.forall(bind2, Formula.eq(join(x, y), join(y, x)))),
        axiom(
            "meet_assoc",
            Formula.forall(bind3, Formula.eq(meet(meet(x, y), z), meet(x, meet(y, z)))),
        ),
        axiom(
            "join_assoc",
            Formula.forall(bind3, Formula.eq(join(join(x, y), z), join(x, join(y, z)))),
        ),
        axiom("meet_idem", Formula.forall(bind1, Formula.eq(meet(x, x), x))),
        axiom("join_idem", Formula.forall(bind1, Formula.eq(join(x, x), x))),
        axiom("meet_absorption", Formula.forall(bind2, Formula.eq(meet(x, join(x, y)), x))),
        axiom("join_absorption", Formula.forall(bind2, Formula.eq(join(x, meet(x, y)), x))),
        axiom(
            "le_by_meet",
            Formula.forall(bind2, Formula.iff(rel("le", x, y), Formula.eq(meet(x, y), x))),
        ),
        axiom("priority_refl", Formula.forall(bind1, rel("priority", x, x))),
        axiom(
            "priority_trans",
            Formula.forall(
                bind3,
                Formula.implies(
                    Formula.conjunction(rel("priority", x, y), rel("priority", y, z)),
                    rel("priority", x, z),
                ),
            ),
        ),
    ]
    candidates = [
        (
            axiom(
                "total_priority_order",
                Formula.forall(
                    bind2,
                    Formula.disjunction(rel("priority", x, y), rel("priority", y, x)),
                ),
            ),
            "priority is total on the finite carrier",
            "order",
        ),
        (
            axiom(
                "distributive_priority_lattice",
                Formula.forall(
                    bind3,
                    Formula.eq(meet(x, join(y, z)), join(meet(x, y), meet(x, z))),
                ),
            ),
            "meet distributes over join",
            "lattice",
        ),
        (
            axiom(
                "modular_priority_lattice",
                Formula.forall(
                    bind3,
                    Formula.implies(
                        rel("le", x, z),
                        Formula.eq(join(x, meet(y, z)), meet(join(x, y), z)),
                    ),
                ),
            ),
            "the lattice satisfies the modular law",
            "lattice",
        ),
        (
            axiom(
                "uncrossed_monotone_join",
                Formula.forall(
                    bind3,
                    Formula.implies(
                        rel("priority", x, y),
                        rel("priority", join(x, z), join(y, z)),
                    ),
                ),
            ),
            "joining the same element preserves priority comparisons",
            "priority_join",
        ),
    ]
    return (
        signature.to_json(),
        [{"name": item.name, "formula": item.formula.to_json()} for item in base],
        [
            {
                "name": item.name,
                "formula": item.formula.to_json(),
                "statement": statement,
                "family": family,
            }
            for item, statement, family in candidates
        ],
    )


def priority_uncrossed_order_blueprint() -> AxiomPackBlueprint:
    theory_signature, base_axioms, candidates = _priority_typed_surface()
    return AxiomPackBlueprint(
        name="priority_uncrossed_order_axiom_pack",
        domain="finite_lattice_order_priority_structures",
        nl_statement=(
            "Find minimal order/lattice axioms under which a priority relation stays uncrossed "
            "through monotone joins, without assuming the target theorem as an axiom."
        ),
        semantic_intent=(
            "Discover reusable structural compressions for finite priority queues, order duality, "
            "and uncrossed matching/order-book arguments."
        ),
        target_structure_family="finite lattices with priority preorder and join operation",
        current_theory="bounded finite posets/lattices with explicit priority relation",
        residuals=[
            "priority comparisons re-derived under order duality",
            "uncrossedness proof search depends on local monotone-join facts",
            "distributive vs modular hypotheses are not separated early",
        ],
        forbidden_shortcuts=[
            "Do not add the target uncrossed theorem as an axiom.",
            "Do not let a surviving candidate grant proof credit.",
            "Do not run downstream yield before finite-model stress receipts.",
        ],
        candidate_axiom_templates=candidates,
        theory_signature=theory_signature,
        base_axioms=base_axioms,
        base_theory_resolved=True,
        provenance=["leanmill_axiom_pack_v1_pilot"],
    )


def structural_isomorphism_move_card_for_axiom_pack(blueprint: AxiomPackBlueprint) -> dict[str, Any]:
    return {
        "schema": AXIOM_PACK_MOVE_CARD_SCHEMA,
        "action": "run_structural_isomorphism_conjecture",
        "tool": "python -m ztare.leanmill.agent_tools isomorphism",
        "canonical_engine": "ztare.research_director.research_isomorphism",
        "mode": "conjecture",
        "allowed_outputs": ["candidate_axiom_template", "structural_correspondence", "kill_condition"],
        "disallowed_outputs": ["proof_credit", "substrate_mutation", "theorem_campaign_consumption"],
        "blueprint_name": blueprint.name,
        "default_args": {
            "left_seam": blueprint.nl_statement,
            "right_seam": "small finite-model and countermodel stress for candidate axioms",
            "model": "codex",
            "n": 3,
            "debug": True,
            "json": True,
        },
        "promotion_rule": "output is provenance only until AxiomPack lint, cheap filters, and separate ratification pass",
    }


def generate_candidate_axiom_pack(
    blueprint: AxiomPackBlueprint | dict[str, Any],
    *,
    isomorphism_receipt: dict[str, Any] | None = None,
    trusted_semantic_fidelity_public_key_pem: str | None = None,
) -> tuple[AxiomPack, dict[str, Any]]:
    if isinstance(blueprint, dict):
        blueprint = AxiomPackBlueprint.from_json(blueprint)
    lint = lint_axiom_pack_blueprint(blueprint)
    if not lint.get("ok"):
        return (
            AxiomPack(
                name=blueprint.name,
                domain=blueprint.domain,
                extends_theory=blueprint.current_theory,
                candidate_axioms=[],
                intended_unlocks=blueprint.residuals,
                provenance=blueprint.provenance,
                downstream_residuals=blueprint.residuals,
                theory_signature=blueprint.theory_signature,
                base_axioms=blueprint.base_axioms,
                base_theory_resolved=blueprint.base_theory_resolved,
            ),
            {
                "schema": AXIOM_PACK_CANDIDATE_GENERATION_SCHEMA,
                "ok": False,
                "blueprint_lint": lint,
                "reason": "blueprint_lint_failed",
            },
        )
    construction = verify_typed_blueprint_construction(
        blueprint,
        isomorphism_receipt,
        trusted_semantic_fidelity_public_key_pem=trusted_semantic_fidelity_public_key_pem,
    )
    if construction.get("ok") is not True:
        return (
            AxiomPack(
                name=blueprint.name,
                domain=blueprint.domain,
                extends_theory=blueprint.current_theory,
                candidate_axioms=[],
                intended_unlocks=blueprint.residuals,
                provenance=blueprint.provenance,
                downstream_residuals=blueprint.residuals,
                theory_signature=blueprint.theory_signature,
                base_axioms=blueprint.base_axioms,
                base_theory_resolved=blueprint.base_theory_resolved,
            ),
            {
                "schema": AXIOM_PACK_CANDIDATE_GENERATION_SCHEMA,
                "ok": False,
                "blueprint_lint": lint,
                "reason": "typed_blueprint_construction_unverified",
                "typed_blueprint_construction": construction,
            },
        )
    provenance = list(blueprint.provenance)
    if isomorphism_receipt:
        provenance.append("structural_isomorphism_move_card")
    pack = AxiomPack(
        name=blueprint.name.replace("_blueprint", ""),
        domain=blueprint.domain,
        extends_theory=blueprint.current_theory,
        candidate_axioms=[
            {
                **dict(template),
                "axiom_hash": lint["formal_axiom_hashes"][index],
                "status": "candidate",
                "proof_credit_eligible": False,
                "theorem_campaign_admissible": False,
            }
            for index, template in enumerate(blueprint.candidate_axiom_templates)
        ],
        intended_unlocks=blueprint.residuals,
        provenance=provenance,
        downstream_residuals=blueprint.residuals,
        theory_signature=blueprint.theory_signature,
        base_axioms=[
            {**dict(row), "axiom_hash": lint["base_axiom_hashes"][index]}
            for index, row in enumerate(blueprint.base_axioms)
        ],
        base_theory_resolved=blueprint.base_theory_resolved,
    )
    return pack, {
        "schema": AXIOM_PACK_CANDIDATE_GENERATION_SCHEMA,
        "ok": True,
        "blueprint_lint": lint,
        "pack_name": pack.name,
        "candidate_count": len(pack.candidate_axioms),
        "isomorphism_receipt_attached": bool(isomorphism_receipt),
        "typed_blueprint_construction": construction,
        "move_card": structural_isomorphism_move_card_for_axiom_pack(blueprint),
    }


def _norm_slug(text: str) -> str:
    parts = [p for p in re.split(r"[^a-z0-9]+", text.lower()) if p]
    return "_".join(parts)


def _candidate_text(candidate: dict[str, Any]) -> str:
    return " ".join(
        str(candidate.get(k) or "")
        for k in ("name", "statement", "family", "rationale", "kill_condition")
    )


def capped_downstream_yield_replay(
    pack: AxiomPack,
    *,
    max_items: int = 3,
    dry_run: bool = True,
) -> dict[str, Any]:
    sampled = pack.downstream_residuals[:max(0, max_items)]
    candidate_terms = {
        tok
        for ax in pack.candidate_axioms
        for tok in str(ax.get("name") or "").replace("-", "_").split("_")
        if len(tok) > 3
    }
    residual_hits = []
    for residual in sampled:
        words = {w.strip(".,;:()[]").lower() for w in residual.split()}
        overlap = sorted(candidate_terms & words)
        residual_hits.append({"residual": residual, "candidate_term_overlap": overlap})
    return {
        "dimension": "downstream_yield",
        "schema": AXIOM_PACK_DOWNSTREAM_YIELD_SCHEMA,
        "status": "insufficient_proxy",
        "ok": False,
        "dry_run": dry_run,
        "cap": max_items,
        "sampled_residuals": sampled,
        "residual_hits": residual_hits,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
        "can_feed_solver": False,
        "note": "lexical diagnostic only; use axiom_yield.evaluate_shadow_ab for a stress receipt",
    }


def _inverse_typed_surface() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    from ztare.leanmill.theory_ir import (
        AxiomFormula,
        Binder,
        Formula,
        OperationSymbol,
        RelationSymbol,
        SortDecl,
        Term,
        TheorySignature,
    )

    signature = TheorySignature(
        name="PartialSymmetry",
        sorts=(SortDecl("Element"),),
        operations=(
            OperationSymbol("mul", ("Element", "Element"), "Element"),
            OperationSymbol("inv", ("Element",), "Element"),
            OperationSymbol("unit", (), "Element"),
        ),
        relations=(RelationSymbol("le", ("Element", "Element")),),
    )
    x, y, z = Term.var("x"), Term.var("y"), Term.var("z")
    bind1 = (Binder("x", "Element"),)
    bind2 = (Binder("x", "Element"), Binder("y", "Element"))
    bind3 = (*bind2, Binder("z", "Element"))
    mul = lambda a, b: Term.app("mul", a, b)
    inv = lambda a: Term.app("inv", a)
    unit = Term.app("unit")
    le = lambda a, b: Formula.rel("le", a, b)

    def axiom(name: str, body: Any) -> AxiomFormula:
        return AxiomFormula(name, body)

    base = [
        axiom(
            "mul_assoc",
            Formula.forall(bind3, Formula.eq(mul(mul(x, y), z), mul(x, mul(y, z)))),
        ),
        axiom("le_refl", Formula.forall(bind1, le(x, x))),
        axiom(
            "le_trans",
            Formula.forall(
                bind3,
                Formula.implies(Formula.conjunction(le(x, y), le(y, z)), le(x, z)),
            ),
        ),
    ]
    idempotent_x = Formula.eq(mul(x, x), x)
    idempotent_y = Formula.eq(mul(y, y), y)
    candidates = [
        (
            axiom(
                "partial_inverse_law",
                Formula.forall(bind1, Formula.eq(mul(mul(x, inv(x)), x), x)),
            ),
            "for every x, x * inv x * x = x",
            "inverse_semigroup",
        ),
        (
            axiom(
                "global_group_inverse",
                Formula.forall(
                    bind1,
                    Formula.conjunction(
                        Formula.eq(mul(x, inv(x)), unit),
                        Formula.eq(mul(inv(x), x), unit),
                    ),
                ),
            ),
            "a shared unit is both inverse products for every element",
            "group_collapse",
        ),
        (
            axiom(
                "idempotent_commute",
                Formula.forall(
                    bind2,
                    Formula.implies(
                        Formula.conjunction(idempotent_x, idempotent_y),
                        Formula.eq(mul(x, y), mul(y, x)),
                    ),
                ),
            ),
            "idempotent elements commute under multiplication",
            "idempotent_semilattice",
        ),
        (
            axiom(
                "domain_idempotent_monotone",
                Formula.forall(
                    bind2,
                    Formula.implies(le(x, y), le(mul(x, inv(x)), mul(y, inv(y)))),
                ),
            ),
            "domain idempotents are monotone under the declared preorder",
            "partial_domain",
        ),
    ]
    return (
        signature.to_json(),
        [{"name": item.name, "formula": item.formula.to_json()} for item in base],
        [
            {
                "name": item.name,
                "formula": item.formula.to_json(),
                "statement": statement,
                "family": family,
            }
            for item, statement, family in candidates
        ],
    )


def inverse_semigroup_axiom_blueprint() -> AxiomPackBlueprint:
    theory_signature, base_axioms, candidates = _inverse_typed_surface()
    return AxiomPackBlueprint(
        name="inverse_semigroup_partial_symmetry_axiom_pack",
        domain="inverse_semigroup_partial_symmetry_structures",
        nl_statement=(
            "Find compact axioms for partial symmetries where local inverse behavior is useful "
            "without collapsing the structure to a group."
        ),
        semantic_intent=(
            "Stress AxiomPack outside order/lattice examples by separating partial transformations, "
            "idempotents, and global inverse assumptions."
        ),
        target_structure_family="finite partial symmetry structures with multiplication and inverse operation",
        current_theory="finite magmas with named inverse operation and idempotent predicates",
        residuals=[
            "global inverse assumptions overfit partial-transition domains",
            "idempotent commutation is repeatedly rediscovered in partial-symmetry arguments",
            "domain idempotent behavior is confused with group identity behavior",
        ],
        forbidden_shortcuts=[
            "Do not assert that every partial symmetry has a shared global identity.",
            "Do not treat small-model survival as proof credit.",
            "Do not run downstream yield before inverse/partial countermodel stress.",
        ],
        candidate_axiom_templates=candidates,
        theory_signature=theory_signature,
        base_axioms=base_axioms,
        base_theory_resolved=True,
        cheap_filter_policy={**DEFAULT_CHEAP_FILTER_POLICY, "max_finite_carrier_size": 7, "filter_budget_k": 4},
        provenance=["leanmill_axiom_pack_v2_second_domain"],
    )


def stress_pack_for_domain(pack: AxiomPack, blueprint: AxiomPackBlueprint | None = None) -> AxiomPack:
    try:
        policy = _normalized_cheap_filter_policy(
            blueprint.cheap_filter_policy
            if blueprint
            else DEFAULT_CHEAP_FILTER_POLICY
        )
        cheap = run_semantic_cheap_filters(
            pack,
            min_carrier_size=policy["semantic_min_carrier_size"],
            max_carrier_size=policy["semantic_max_carrier_size"],
            max_interpretations=policy["semantic_max_interpretations"],
            fixed_size_smt_policy=policy,
        )
    except (TypeError, ValueError) as exc:
        cheap = [
            {
                "schema": "leanmill.axiom_pack_semantic_dimension.v1",
                "dimension": dimension,
                "status": "fail",
                "reason": f"typed_semantic_stress_unavailable:{exc}",
                "proof_credit_eligible": False,
                "theorem_campaign_admissible": False,
            }
            for dimension in CHEAP_STRESS_DIMENSIONS
        ]
    existing_yield = [
        row
        for row in pack.stress_receipts
        if isinstance(row, dict) and row.get("dimension") == "downstream_yield"
    ]
    yield_receipts = existing_yield if len(existing_yield) == 1 else [
        capped_downstream_yield_replay(
            pack,
            max_items=int(
                (blueprint.downstream_yield_policy if blueprint else DEFAULT_DOWNSTREAM_YIELD_POLICY).get(
                    "max_replayed_residuals"
                )
                or 3
            ),
        )
    ]
    return replace(pack, stress_receipts=[*cheap, *yield_receipts])


def screen_axiom_pack_blueprint(
    blueprint: AxiomPackBlueprint | dict[str, Any],
) -> dict[str, Any]:
    """Run the generic typed, bounded screen without claiming downstream lift."""

    if isinstance(blueprint, dict):
        blueprint = AxiomPackBlueprint.from_json(blueprint)
    pack, generation = generate_candidate_axiom_pack(blueprint)
    stressed = stress_pack_for_domain(pack, blueprint)
    stress = stress_axiom_pack(stressed)
    cheap_ok = stress.get("compute_route", {}).get("cheap_filter_ok") is True
    screen_ok = generation.get("ok") is True and cheap_ok
    return {
        "schema": AXIOM_PACK_BLUEPRINT_SCREEN_SCHEMA,
        "status": "screened_quarantined" if screen_ok else "screen_rejected",
        "screen_ok": screen_ok,
        "promotion_ready": False,
        "blueprint": blueprint.to_json(),
        "generation": generation,
        "pack": stressed.to_json(),
        "stress": stress,
        "next_required": [
            "signed_frozen_task_manifest",
            "matched_shadow_proof_outcomes",
            "exact_candidate_dependency_ablation",
            "conditional_lean_lowering",
            "separate_signed_ratification",
        ],
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }


def _criterion(name: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "evidence": evidence}


def _receipt_by_dimension(pack: AxiomPack, dimension: str) -> dict[str, Any]:
    for receipt in pack.stress_receipts:
        if isinstance(receipt, dict) and receipt.get("dimension") == dimension:
            return receipt
    return {}


def _non_generic_candidate_evidence(pack: AxiomPack) -> dict[str, Any]:
    stop = {"a", "an", "and", "as", "by", "for", "in", "is", "of", "on", "or", "the", "to", "under", "with"}
    rows = []
    for candidate in pack.candidate_axioms:
        text = _candidate_text(candidate)
        tokens = {t for t in _norm_slug(text).split("_") if t and t not in stop}
        domain_tokens = sorted(tokens - GENERIC_TEMPLATE_TOKENS)
        rows.append({
            "name": str(candidate.get("name") or ""),
            "domain_token_count": len(domain_tokens),
            "domain_tokens": domain_tokens[:8],
        })
    return {
        "candidate_count": len(rows),
        "non_generic_count": sum(1 for row in rows if int(row["domain_token_count"]) >= 2),
        "rows": rows,
    }


def score_axiom_pack_usefulness(
    pack: AxiomPack | dict[str, Any],
    stress_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(pack, dict):
        pack = AxiomPack.from_json(pack)
    stress = stress_report if isinstance(stress_report, dict) else stress_axiom_pack(pack)
    nontriviality = _receipt_by_dimension(pack, "nontriviality")
    separation = _receipt_by_dimension(pack, "separation_or_interpretation")
    strength = _receipt_by_dimension(pack, "strength_comparison")
    downstream = _receipt_by_dimension(pack, "downstream_yield")
    measured_hits = [
        row
        for row in downstream.get("paired_results") or []
        if isinstance(row, dict) and row.get("attributable_improvement") is True
    ]
    countermodels = [
        row for row in separation.get("countermodel_strata") or []
        if isinstance(row, dict) and row.get("countermodel")
    ]
    if not countermodels:
        countermodels = [
            row
            for row in (separation.get("evidence") or {}).get("receipt_sha256s") or []
            if row
        ]
    strength_edges = strength.get("edges") or (strength.get("evidence") or {}).get("edges") or []
    novelty = _non_generic_candidate_evidence(pack)
    pack_json = pack.to_json()
    no_credit_leakage = (
        pack_json.get("proof_credit_eligible") is False
        and pack_json.get("theorem_campaign_admissible") is False
        and stress.get("proof_credit_eligible") is False
        and stress.get("theorem_campaign_admissible") is False
        and theorem_campaign_consumption_gate(pack).get("allowed") is False
        and all(
            not bool(r.get("proof_credit_eligible")) and not bool(r.get("theorem_campaign_admissible"))
            for r in pack.stress_receipts
            if isinstance(r, dict)
        )
        and downstream.get("can_feed_solver") is False
    )
    criteria = [
        _criterion("nontriviality", nontriviality.get("status") == "pass", nontriviality.get("models") or []),
        _criterion("countermodel_separation", bool(countermodels), countermodels[:5]),
        _criterion("strength_relation_learned", bool(strength_edges), strength_edges),
        _criterion("heldout_downstream_gain", bool(measured_hits), measured_hits),
        _criterion("novelty_vs_generic_templates", novelty["non_generic_count"] > 0, novelty),
        _criterion("no_proof_credit_leakage", no_credit_leakage, {
            "pack_proof_credit_eligible": pack_json.get("proof_credit_eligible"),
            "theorem_campaign_gate_allowed": theorem_campaign_consumption_gate(pack).get("allowed"),
            "downstream_can_feed_solver": downstream.get("can_feed_solver"),
        }),
    ]
    passed = sum(1 for c in criteria if c["pass"])
    return {
        "schema": AXIOM_PACK_USEFULNESS_SCORE_SCHEMA,
        "pack_name": pack.name,
        "domain": pack.domain,
        "ok": passed == len(criteria),
        "score": round(passed / max(1, len(criteria)), 3),
        "passed": passed,
        "total": len(criteria),
        "criteria": criteria,
    }


def cached_priority_agent_isomorphism_receipt() -> dict[str, Any]:
    return {
        "schema": "leanmill.agent_tool.structural_isomorphism_receipt.v1",
        "status": "ok",
        "mode": "conjecture",
        "model": "cached-agent-fixture",
        "canonical_engine": "ztare.research_director.research_isomorphism",
        "trial_source": "cached_agent_authored_fixture",
        "proof_credit_eligible": False,
        "can_mutate_substrate": False,
        "result": {
            "candidate_count": 4,
            "candidate_axiom_templates": [
                {
                    "name": "separation_lattice_uncrossed_join",
                    "statement": "a separation-lattice join law preserves uncrossed priority comparisons",
                    "family": "priority_join",
                    "kill_condition": "diamond or pentagon countermodel breaks the proxy law",
                },
                {
                    "name": "priority_totality_boundary",
                    "statement": "priority totality may be needed only on boundary-comparable elements",
                    "family": "order",
                    "kill_condition": "branching distributive models separate totality from uncrossedness",
                },
                {
                    "name": "distributive_vs_modular_separator",
                    "statement": "distributivity should be separated from modularity before proof replay",
                    "family": "lattice",
                    "kill_condition": "M3 survives modularity and refutes distributivity",
                },
                {
                    "name": "uncrossed_monotone_join_candidate",
                    "statement": "joining with a higher-priority element is monotone for uncrossed comparisons",
                    "family": "priority_join",
                    "kill_condition": "N5 refutes the monotone join law",
                },
            ],
            "note": "Cached receipt exercises the agent-authored surface and provides no mathematical evidence.",
        },
    }


def cached_inverse_agent_isomorphism_receipt() -> dict[str, Any]:
    return {
        "schema": "leanmill.agent_tool.structural_isomorphism_receipt.v1",
        "status": "ok",
        "mode": "conjecture",
        "model": "cached-agent-fixture",
        "canonical_engine": "ztare.research_director.research_isomorphism",
        "trial_source": "cached_agent_authored_fixture",
        "proof_credit_eligible": False,
        "can_mutate_substrate": False,
        "result": {
            "candidate_count": 4,
            "candidate_axiom_templates": [
                {
                    "name": "partial_inverse_transport_law",
                    "statement": "local inverse behavior should satisfy x * inv x * x = x",
                    "family": "inverse_semigroup",
                    "kill_condition": "bad inverse magma refutes the law",
                },
                {
                    "name": "avoid_global_group_inverse_collapse",
                    "statement": "global group inverse should be treated as a stronger collapse axiom",
                    "family": "group_collapse",
                    "kill_condition": "partial bijection model refutes shared global identity",
                },
                {
                    "name": "idempotent_commutation_surface",
                    "statement": "commuting idempotents form the semilattice-like surface to stress",
                    "family": "idempotent_semilattice",
                    "kill_condition": "noncommuting idempotent band refutes it",
                },
                {
                    "name": "domain_idempotent_monotone_surface",
                    "statement": "domain idempotents should be monotone under partial composition",
                    "family": "partial_domain",
                    "kill_condition": "noncommuting idempotent band refutes the monotone surface",
                },
            ],
            "note": "Cached second-domain receipt checks that the loop is not priority-only.",
        },
    }


def _templates_from_isomorphism_result(result: dict[str, Any], domain: str) -> list[dict[str, Any]]:
    """Render legacy prose conjectures for diagnostics only.

    These rows deliberately lack ``formula`` and therefore fail blueprint
    lint.  The admitted path is ``_typed_templates_from_isomorphism_result``;
    keeping the prose visible is useful for debugging without treating a
    language-model paraphrase as a mathematical law.
    """
    templates = result.get("candidate_axiom_templates")
    if isinstance(templates, list) and templates:
        return [dict(t) for t in templates if isinstance(t, dict)]
    out = []
    for idx, candidate in enumerate(result.get("candidates") or result.get("conjectures") or []):
        if not isinstance(candidate, dict):
            continue
        mother = str(candidate.get("mother_structure") or f"isomorphism_candidate_{idx + 1}")
        cards = candidate.get("prediction_cards") or []
        statement = mother
        if cards and isinstance(cards[0], dict):
            statement = str(cards[0].get("prediction") or cards[0].get("test") or mother)
        out.append({
            "name": f"{_norm_slug(mother)[:48] or 'isomorphism_candidate'}_{idx + 1}",
            "statement": statement,
            "family": "isomorphism_conjecture",
            "kill_condition": "must survive domain cheap filters before replay",
        })
    if out:
        return out
    return []


def _typed_templates_from_isomorphism_result(
    result: dict[str, Any],
    base: AxiomPackBlueprint,
    *,
    trusted_semantic_fidelity_public_key_pem: str | None,
    expected_semantic_fidelity_verifier_ref: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Admit typed agent proposals under a caller-configured checker key.

    The receipt never supplies its own trust root.  Each row also carries the
    structural conjecture bytes so the proposal digest is checked against the
    source that crossed this adapter.
    """

    rows = result.get("typed_axiom_proposals")
    if not isinstance(rows, list):
        rows = []
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_proposals: set[str] = set()
    seen_axiom_names: set[str] = set()
    try:
        from ztare.leanmill.theory_ir import TheorySignature

        base_signature_sha256 = TheorySignature.from_json(base.theory_signature).content_hash
    except (TypeError, ValueError) as exc:
        base_signature_sha256 = ""
        rejected.append({"index": -1, "failures": [f"base_theory_signature:{exc}"]})

    for index, row in enumerate(rows):
        failures: list[str] = []
        if not isinstance(row, dict):
            rejected.append({"index": index, "failures": ["row_must_be_object"]})
            continue
        proposal = row.get("typed_axiom_proposal")
        verdict = row.get("semantic_fidelity_verdict")
        source = row.get("source_conjecture")
        if not isinstance(source, dict):
            failures.append("source_conjecture_missing")
        if not trusted_semantic_fidelity_public_key_pem:
            failures.append("trusted_semantic_fidelity_public_key_missing")
        try:
            from ztare.leanmill.typed_axiom_proposal import (
                TypedAxiomProposal,
                admit_axiom_template,
            )

            parsed = TypedAxiomProposal.from_json(proposal)
            if parsed.theory_signature_sha256 != base_signature_sha256:
                failures.append("proposal_theory_signature_mismatch")
            if parsed.content_hash in seen_proposals:
                failures.append("duplicate_typed_proposal")
            if parsed.axiom.name in seen_axiom_names:
                failures.append("duplicate_typed_axiom_name")
            if not failures:
                template = admit_axiom_template(
                    parsed,
                    verdict,
                    trusted_public_key_pem=str(trusted_semantic_fidelity_public_key_pem),
                    source_conjecture=source,
                    expected_verifier_ref=expected_semantic_fidelity_verifier_ref,
                )
                accepted.append(template)
                seen_proposals.add(parsed.content_hash)
                seen_axiom_names.add(parsed.axiom.name)
        except (TypeError, ValueError) as exc:
            failures.append(f"typed_axiom_admission:{exc}")
        if failures:
            rejected.append({"index": index, "failures": failures})

    return accepted, {
        "schema": "leanmill.typed_axiom_proposal_admission.v1",
        "submitted": len(rows),
        "accepted": len(accepted),
        "rejected": rejected,
        "base_theory_signature_sha256": base_signature_sha256,
        "trust_root_from_receipt": False,
    }


def verify_typed_blueprint_construction(
    blueprint: AxiomPackBlueprint | dict[str, Any],
    receipt: dict[str, Any] | None,
    *,
    trusted_semantic_fidelity_public_key_pem: str | None,
) -> dict[str, Any]:
    """Replay signed agent proposals before a blueprint can generate a pack."""

    if isinstance(blueprint, dict):
        blueprint = AxiomPackBlueprint.from_json(blueprint)
    typed = any(
        isinstance(row.get("typed_proposal_sha256"), str)
        and bool(row.get("typed_proposal_sha256"))
        for row in blueprint.candidate_axiom_templates
    )
    agent_origin = bool(
        {str(value) for value in blueprint.provenance}
        & {"agent_authored_blueprint_trial", "structural_isomorphism_move_card"}
    )
    if not typed and not agent_origin:
        return {
            "schema": "leanmill.typed_axiom_blueprint_construction.v1",
            "ok": True,
            "required": False,
            "failures": [],
        }
    failures: list[str] = []
    receipt = receipt if isinstance(receipt, dict) else {}
    result = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
    if receipt.get("status") != "ok":
        failures.append("source_receipt_status_not_ok")
    if not isinstance(result.get("typed_axiom_proposals"), list):
        failures.append("typed_axiom_proposals_missing")
    templates, admission = _typed_templates_from_isomorphism_result(
        result,
        blueprint,
        trusted_semantic_fidelity_public_key_pem=trusted_semantic_fidelity_public_key_pem,
        expected_semantic_fidelity_verifier_ref=None,
    )
    if admission.get("rejected"):
        failures.append("typed_candidate_admission_rejected")
    if templates != blueprint.candidate_axiom_templates:
        failures.append("typed_candidate_templates_do_not_replay")
    return {
        "schema": "leanmill.typed_axiom_blueprint_construction.v1",
        "ok": not failures,
        "required": True,
        "failures": failures,
        "admission": admission,
    }


def blueprint_from_agent_isomorphism_receipt(
    base: AxiomPackBlueprint,
    receipt: dict[str, Any],
    *,
    trusted_semantic_fidelity_public_key_pem: str | None = None,
    expected_semantic_fidelity_verifier_ref: str | None = None,
) -> dict[str, Any]:
    result = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
    has_typed_candidates = isinstance(result.get("typed_axiom_proposals"), list)
    has_explicit_candidates = bool(
        has_typed_candidates
        or result.get("candidate_axiom_templates")
        or result.get("candidates")
        or result.get("conjectures")
    )
    admission: dict[str, Any]
    if has_typed_candidates:
        if receipt.get("status") == "ok":
            templates, admission = _typed_templates_from_isomorphism_result(
                result,
                base,
                trusted_semantic_fidelity_public_key_pem=trusted_semantic_fidelity_public_key_pem,
                expected_semantic_fidelity_verifier_ref=expected_semantic_fidelity_verifier_ref,
            )
        else:
            templates = []
            admission = {
                "schema": "leanmill.typed_axiom_proposal_admission.v1",
                "submitted": len(result.get("typed_axiom_proposals") or []),
                "accepted": 0,
                "rejected": [{"index": -1, "failures": ["source_receipt_status_not_ok"]}],
                "trust_root_from_receipt": False,
            }
    else:
        templates = (
            _templates_from_isomorphism_result(result, base.domain)
            if receipt.get("status") == "ok" or has_explicit_candidates
            else []
        )
        admission = {
            "schema": "leanmill.typed_axiom_proposal_admission.v1",
            "submitted": 0,
            "accepted": 0,
            "rejected": [
                {
                    "index": index,
                    "failures": ["untyped_natural_language_conjecture"],
                }
                for index, _template in enumerate(templates)
            ],
            "trust_root_from_receipt": False,
        }
    if has_typed_candidates:
        unique_templates = [dict(template) for template in templates]
    else:
        seen: set[str] = set()
        unique_templates = []
        for idx, template in enumerate(templates, start=1):
            item = dict(template)
            item["name"] = _norm_slug(str(item.get("name") or f"candidate_{idx}")) or f"candidate_{idx}"
            while item["name"] in seen:
                item["name"] = f"{item['name']}_{idx}"
            seen.add(item["name"])
            unique_templates.append(item)
    blueprint = AxiomPackBlueprint(
        name=f"{base.name}_agent_trial",
        domain=base.domain,
        nl_statement=base.nl_statement,
        semantic_intent=base.semantic_intent,
        target_structure_family=base.target_structure_family,
        current_theory=base.current_theory,
        residuals=base.residuals,
        forbidden_shortcuts=base.forbidden_shortcuts,
        candidate_axiom_templates=unique_templates,
        theory_signature=base.theory_signature,
        base_axioms=base.base_axioms,
        base_theory_resolved=base.base_theory_resolved,
        cheap_filter_policy=base.cheap_filter_policy,
        downstream_yield_policy=base.downstream_yield_policy,
        provenance=[
            *base.provenance,
            "agent_authored_blueprint_trial",
            str(receipt.get("trial_source") or "structural_isomorphism_receipt"),
        ],
    )
    lint = lint_axiom_pack_blueprint(blueprint)
    construction_ready = bool(
        lint.get("ok")
        and (
            not has_typed_candidates
            or (
                admission.get("submitted", 0) > 0
                and admission.get("accepted") == admission.get("submitted")
                and not admission.get("rejected")
            )
        )
    )
    return {
        "schema": AXIOM_PACK_AGENT_BLUEPRINT_SCHEMA,
        "ok": construction_ready,
        "construction_ready": construction_ready,
        "trial_source": receipt.get("trial_source") or "unknown",
        "receipt_status": receipt.get("status"),
        "receipt_model": receipt.get("model"),
        "receipt_candidate_count": result.get("candidate_count") or len(unique_templates),
        "typed_candidate_admission": admission,
        "typed_candidate_evidence": (
            list(result.get("typed_axiom_proposals") or []) if has_typed_candidates else []
        ),
        "blueprint": blueprint.to_json(),
        "lint": lint,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }


def run_live_axiom_pack_isomorphism(
    blueprint: AxiomPackBlueprint,
    *,
    model: str = "codex",
    n: int = 8,
    typed_producer_runtime: Any | None = None,
) -> dict[str, Any]:
    if typed_producer_runtime is None:
        return {
            "schema": "leanmill.agent_tool.structural_isomorphism_receipt.v1",
            "status": "language_capability_gap",
            "mode": "conjecture",
            "model": model,
            "canonical_engine": "ztare.leanmill.axiom_pack_orchestration",
            "trial_source": "live_typed_axiom_pack_producer",
            "proof_credit_eligible": False,
            "theorem_campaign_admissible": False,
            "can_mutate_substrate": False,
            "provider_calls": 0,
            "result": {
                "candidate_count": 0,
                "typed_axiom_proposals": [],
                "producer_outcome": "language_capability_gap",
                "outcome_detail": "live typed producer runtime was not supplied",
                "missing_capabilities": [
                    "live_typed_producer_runtime.escalation",
                    "live_typed_producer_runtime.task_manifest",
                    "live_typed_producer_runtime.proposer_call",
                    "live_typed_producer_runtime.semantic_checker_fn",
                ],
                "requested_candidate_cap": n,
            },
        }
    from ztare.leanmill.axiom_pack_live_producer import (
        run_live_typed_axiom_pack_producer,
    )

    orchestration = run_live_typed_axiom_pack_producer(
        base_blueprint=blueprint,
        runtime=typed_producer_runtime,
    )
    receipt = orchestration.get("receipt")
    if not isinstance(receipt, dict):
        raise ValueError("live typed producer returned no source receipt")
    return {
        **receipt,
        "model": model,
        "requested_candidate_cap": n,
    }


def _base_blueprint_for_domain(domain: str) -> AxiomPackBlueprint:
    d = domain.lower().replace("-", "_")
    if d in {"inverse", "inverse_semigroup", "inverse_semigroups", "partial_symmetry"}:
        return inverse_semigroup_axiom_blueprint()
    return priority_uncrossed_order_blueprint()


def _cached_receipt_for_domain(domain: str) -> dict[str, Any]:
    d = domain.lower()
    if "inverse" in d or "partial" in d:
        return cached_inverse_agent_isomorphism_receipt()
    return cached_priority_agent_isomorphism_receipt()


def _read_receipt(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _single_domain_discovery_eval(
    domain: str,
    *,
    receipt: dict[str, Any] | None = None,
    live_isomorphism: bool = False,
    model: str = "codex",
    n: int = 8,
    trusted_semantic_fidelity_public_key_pem: str | None = None,
    expected_semantic_fidelity_verifier_ref: str | None = None,
    live_typed_producer_runtime: Any | None = None,
) -> dict[str, Any]:
    base = _base_blueprint_for_domain(domain)
    if live_typed_producer_runtime is not None:
        if trusted_semantic_fidelity_public_key_pem is None:
            trusted_semantic_fidelity_public_key_pem = str(
                live_typed_producer_runtime.trusted_semantic_fidelity_public_key_pem
            )
        if expected_semantic_fidelity_verifier_ref is None:
            expected_semantic_fidelity_verifier_ref = str(
                live_typed_producer_runtime.expected_semantic_fidelity_verifier_ref
            )
    if receipt is None:
        receipt = (
            run_live_axiom_pack_isomorphism(
                base,
                model=model,
                n=n,
                typed_producer_runtime=live_typed_producer_runtime,
            )
            if live_isomorphism
            else _cached_receipt_for_domain(base.domain)
        )
    from ztare.leanmill.axiom_pack_candidate_birth import (
        materialize_typed_axiom_pack_candidate,
    )

    candidate_birth = materialize_typed_axiom_pack_candidate(
        base_blueprint=base,
        source_receipt=receipt,
        trusted_semantic_fidelity_public_key_pem=(
            trusted_semantic_fidelity_public_key_pem
        ),
        expected_semantic_fidelity_verifier_ref=(
            expected_semantic_fidelity_verifier_ref
        ),
    )
    if candidate_birth.get("status") == "candidate_born":
        agent_blueprint_row = dict(candidate_birth["agent_blueprint_trial"])
        agent_blueprint = AxiomPackBlueprint.from_json(agent_blueprint_row["blueprint"])
        pack = AxiomPack.from_json(candidate_birth["pack"])
        generation = dict(candidate_birth["generation"])
    else:
        # Preserve rejected prose as a diagnostic trial without persisting it
        # as a candidate pack.
        agent_blueprint_row = blueprint_from_agent_isomorphism_receipt(
            base,
            receipt,
            trusted_semantic_fidelity_public_key_pem=(
                trusted_semantic_fidelity_public_key_pem
            ),
            expected_semantic_fidelity_verifier_ref=(
                expected_semantic_fidelity_verifier_ref
            ),
        )
        agent_blueprint = AxiomPackBlueprint.from_json(agent_blueprint_row["blueprint"])
        pack, generation = generate_candidate_axiom_pack(
            agent_blueprint,
            isomorphism_receipt=receipt,
            trusted_semantic_fidelity_public_key_pem=(
                trusted_semantic_fidelity_public_key_pem
            ),
        )
    stressed = stress_pack_for_domain(pack, agent_blueprint)
    stress = stress_axiom_pack(stressed)
    usefulness = score_axiom_pack_usefulness(stressed, stress)
    return {
        "domain": base.domain,
        "base_blueprint": base.to_json(),
        "isomorphism_receipt": receipt,
        "agent_blueprint_trial": agent_blueprint_row,
        "agent_blueprint_lint": agent_blueprint_row["lint"],
        "candidate_birth": candidate_birth,
        "generation": generation,
        "pack": stressed.to_json(),
        "stress": stress,
        "usefulness_score": usefulness,
        "ok": bool(
            candidate_birth.get("status") == "candidate_born"
            and agent_blueprint_row.get("ok")
            and generation.get("ok")
            and stress.get("ok")
            and usefulness.get("ok")
        ),
    }


def run_axiom_pack_discovery_eval(
    *,
    domain: str = "priority",
    receipt_path: str | Path | None = None,
    live_isomorphism: bool = False,
    model: str = "codex",
    n: int = 8,
    include_second_domain: bool = True,
    trusted_semantic_fidelity_public_key_pem: str | None = None,
    expected_semantic_fidelity_verifier_ref: str | None = None,
    live_typed_producer_runtime: Any | None = None,
) -> dict[str, Any]:
    receipt = _read_receipt(receipt_path)
    primary = _single_domain_discovery_eval(
        domain,
        receipt=receipt,
        live_isomorphism=live_isomorphism,
        model=model,
        n=n,
        trusted_semantic_fidelity_public_key_pem=trusted_semantic_fidelity_public_key_pem,
        expected_semantic_fidelity_verifier_ref=expected_semantic_fidelity_verifier_ref,
        live_typed_producer_runtime=live_typed_producer_runtime,
    )
    primary_trial_source = str(primary.get("isomorphism_receipt", {}).get("trial_source") or "")
    hand_tooled_risk = primary["domain"] == priority_uncrossed_order_blueprint().domain and primary_trial_source.startswith("cached_")
    second = None
    if include_second_domain and hand_tooled_risk:
        second = _single_domain_discovery_eval(
            "inverse_semigroup",
            receipt=None,
            live_isomorphism=False,
            model=model,
            n=n,
            trusted_semantic_fidelity_public_key_pem=trusted_semantic_fidelity_public_key_pem,
            expected_semantic_fidelity_verifier_ref=expected_semantic_fidelity_verifier_ref,
        )
    next_domain = (
        "quasigroups_and_loops"
        if second or "inverse" in primary["domain"].lower() or "partial_symmetry" in primary["domain"].lower()
        else "inverse_semigroups"
    )
    criteria = {
        "agent_blueprint_lint": primary["agent_blueprint_lint"].get("ok") is True,
        "stress_ok": primary["stress"].get("ok") is True,
        "usefulness_ok": primary["usefulness_score"].get("ok") is True,
        "proof_credit_quarantined": primary["usefulness_score"]["criteria"][-1]["pass"] is True,
        "second_domain_probe_ok": None if second is None else second.get("ok") is True,
    }
    ok = all(v is True for v in criteria.values() if v is not None)
    return {
        "schema": AXIOM_PACK_DISCOVERY_EVAL_SCHEMA,
        "ok": ok,
        "mode": "live" if live_isomorphism else "cached",
        "model": model,
        "n": n,
        "primary": primary,
        "hand_tooled_risk": hand_tooled_risk,
        "second_domain_eval": second,
        "next_domain_to_stress": next_domain,
        "pass_fail_criteria": criteria,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
        "interpretation": (
            "cached harness validation only; spend a live leaf budget for discovery claims"
            if not live_isomorphism
            else "live agent proposals still require separate finite-model and promotion receipts"
        ),
    }


def render_axiom_pack_discovery_eval(report: dict[str, Any]) -> str:
    primary = report.get("primary") or {}
    score = primary.get("usefulness_score") or {}
    lines = [
        "# AxiomPack Discovery Eval",
        "",
        f"- schema: {report.get('schema')}",
        f"- ok: {report.get('ok')}",
        f"- mode: {report.get('mode')}",
        f"- primary_domain: {primary.get('domain')}",
        f"- primary_score: {score.get('score')} ({score.get('passed')}/{score.get('total')})",
        f"- hand_tooled_risk: {report.get('hand_tooled_risk')}",
        f"- next_domain_to_stress: {report.get('next_domain_to_stress')}",
        "",
        "## Criteria",
    ]
    for name, passed in (report.get("pass_fail_criteria") or {}).items():
        lines.append(f"- {name}: {passed}")
    lines.append("")
    lines.append("## Usefulness")
    for criterion in score.get("criteria") or []:
        lines.append(f"- {criterion.get('name')}: {criterion.get('pass')}")
    second = report.get("second_domain_eval")
    if isinstance(second, dict):
        second_score = second.get("usefulness_score") or {}
        lines.extend([
            "",
            "## Second Domain",
            f"- domain: {second.get('domain')}",
            f"- ok: {second.get('ok')}",
            f"- score: {second_score.get('score')} ({second_score.get('passed')}/{second_score.get('total')})",
        ])
    lines.extend([
        "",
        f"Interpretation: {report.get('interpretation')}",
    ])
    return "\n".join(lines) + "\n"


def append_axiom_pack_event(
    store_path: str | Path,
    *,
    pack: AxiomPack,
    stress: dict[str, Any],
    blueprint: AxiomPackBlueprint | None = None,
    generation: dict[str, Any] | None = None,
    candidate_birth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        _pack_formal_theory(pack)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"candidate store requires an executable typed pack: {exc}"
        ) from exc
    agent_origin = bool(
        {"agent_authored_blueprint_trial", "structural_isomorphism_move_card"}
        & set(pack.provenance)
    )
    if agent_origin and candidate_birth is None:
        raise ValueError("agent-authored pack requires a candidate-birth receipt")
    if candidate_birth is not None:
        from ztare.leanmill.axiom_authority import pack_digest
        from ztare.leanmill.axiom_pack_candidate_birth import (
            verify_axiom_pack_candidate_birth,
        )

        birth_ok, birth_failures = verify_axiom_pack_candidate_birth(candidate_birth)
        if not birth_ok:
            raise ValueError(f"candidate-birth receipt rejected: {birth_failures}")
        if candidate_birth.get("pack_digest") != pack_digest(pack):
            raise ValueError("candidate-birth receipt names a different pack")
    event = {
        "schema": AXIOM_PACK_STORE_EVENT_SCHEMA,
        "ts": time.time(),
        "pack": pack.to_json(),
        "stress": stress,
        "blueprint": blueprint.to_json() if blueprint else None,
        "generation": generation or {},
        "candidate_birth": candidate_birth,
        "promotion_status": pack.promotion_status,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    p = Path(store_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
    event["store_path"] = str(p)
    return event


def _demo_group_theory_pack() -> AxiomPack:
    blueprint = inverse_semigroup_axiom_blueprint()
    pack, _generation = generate_candidate_axiom_pack(blueprint)
    return stress_pack_for_domain(pack, blueprint)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate a quarantined LeanMill AxiomPack")
    ap.add_argument(
        "path",
        nargs="?",
        help="JSON file containing a typed AxiomPack or AxiomPack blueprint",
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--lint-blueprint", metavar="PATH")
    ap.add_argument("--pilot-priority", action="store_true")
    ap.add_argument("--discovery-eval-priority", action="store_true")
    ap.add_argument("--discovery-eval-inverse-semigroup", action="store_true")
    ap.add_argument("--receipt", default="", help="optional cached structural-isomorphism receipt JSON")
    ap.add_argument(
        "--semantic-fidelity-public-key",
        default="",
        help="configured checker public-key PEM path for typed agent proposals",
    )
    ap.add_argument("--semantic-fidelity-verifier-ref", default="")
    ap.add_argument(
        "--live-isomorphism",
        action="store_true",
        help=(
            "run the non-calibration typed AxiomPack authoring transition from "
            "a frozen escalation, task manifest, and separated subscription roles"
        ),
    )
    ap.add_argument("--live-escalation", default="")
    ap.add_argument("--live-task-manifest", default="")
    ap.add_argument("--task-manifest-public-key", default="")
    ap.add_argument("--semantic-fidelity-private-key", default="")
    ap.add_argument("--live-artifact-dir", default="")
    ap.add_argument(
        "--subscription-runtime", choices=("codex", "claude"), default="codex"
    )
    ap.add_argument("--subscription-model", default="gpt-5.5")
    ap.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high", "ultra"),
        default="medium",
    )
    ap.add_argument("--live-timeout-seconds", type=int, default=900)
    ap.add_argument("--model", default="codex")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--markdown-report", default="")
    ap.add_argument("--no-second-domain", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--store", default="")
    args = ap.parse_args(argv)
    if args.self_test:
        print(json.dumps(stress_axiom_pack(_demo_group_theory_pack()), indent=2, sort_keys=True))
        return 0
    if args.lint_blueprint:
        obj = json.loads(Path(args.lint_blueprint).read_text(encoding="utf-8"))
        report = lint_axiom_pack_blueprint(obj)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if args.pilot_priority:
        blueprint = priority_uncrossed_order_blueprint()
        pack, generation = generate_candidate_axiom_pack(blueprint)
        pack = stress_pack_for_domain(pack, blueprint)
        report = stress_axiom_pack(pack)
        payload = {
            "schema": "leanmill.axiom_pack_pilot.v1",
            "blueprint": blueprint.to_json(),
            "generation": generation,
            "pack": pack.to_json(),
            "stress": report,
        }
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.store:
            append_axiom_pack_event(args.store, pack=pack, stress=report, blueprint=blueprint, generation=generation)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if args.discovery_eval_priority or args.discovery_eval_inverse_semigroup:
        domain = "inverse_semigroup" if args.discovery_eval_inverse_semigroup else "priority"
        semantic_fidelity_public_key = (
            Path(args.semantic_fidelity_public_key).read_text(encoding="utf-8")
            if args.semantic_fidelity_public_key
            else None
        )
        live_typed_producer_runtime = None
        if args.live_isomorphism:
            if args.receipt:
                ap.error("--live-isomorphism cannot be combined with --receipt")
            required_live_artifacts = {
                "--live-escalation": args.live_escalation,
                "--live-task-manifest": args.live_task_manifest,
                "--task-manifest-public-key": args.task_manifest_public_key,
                "--semantic-fidelity-private-key": (
                    args.semantic_fidelity_private_key
                ),
                "--semantic-fidelity-public-key": (
                    args.semantic_fidelity_public_key
                ),
                "--semantic-fidelity-verifier-ref": (
                    args.semantic_fidelity_verifier_ref
                ),
                "--live-artifact-dir": args.live_artifact_dir,
            }
            missing_live_artifacts = [
                flag for flag, value in required_live_artifacts.items() if not value
            ]
            if missing_live_artifacts:
                ap.error(
                    "--live-isomorphism requires "
                    + ", ".join(missing_live_artifacts)
                )
            from ztare.leanmill.axiom_pack_live_producer import (
                build_live_typed_axiom_pack_runtime,
            )
            from ztare.leanmill.frontier_agent_runtime import (
                FrontierAgentConfig,
                SubscriptionJSONRole,
            )

            config = FrontierAgentConfig(
                runtime=args.subscription_runtime,
                model=args.subscription_model,
                reasoning_effort=args.reasoning_effort,
                timeout_seconds=int(args.live_timeout_seconds),
            )
            artifact_root = Path(args.live_artifact_dir)
            domain_slug = _norm_slug(domain)
            proposer_role = SubscriptionJSONRole(
                role="axiom_pack_typed_proposer",
                agent_id=f"axiompack-typed-proposer-{domain_slug}",
                repo=REPO,
                artifact_dir=artifact_root / "typed_axiom_proposer",
                config=config,
            )
            semantic_checker_role = SubscriptionJSONRole(
                role="axiom_pack_semantic_checker",
                agent_id=f"axiompack-semantic-checker-{domain_slug}",
                repo=REPO,
                artifact_dir=artifact_root / "semantic_checker",
                config=config,
            )
            live_typed_producer_runtime = build_live_typed_axiom_pack_runtime(
                escalation=json.loads(
                    Path(args.live_escalation).read_text(encoding="utf-8")
                ),
                task_manifest=json.loads(
                    Path(args.live_task_manifest).read_text(encoding="utf-8")
                ),
                trusted_manifest_public_key_pem=Path(
                    args.task_manifest_public_key
                ).read_text(encoding="utf-8"),
                semantic_checker_private_key_pem=Path(
                    args.semantic_fidelity_private_key
                ).read_text(encoding="utf-8"),
                trusted_semantic_fidelity_public_key_pem=str(
                    semantic_fidelity_public_key
                ),
                expected_semantic_fidelity_verifier_ref=(
                    args.semantic_fidelity_verifier_ref
                ),
                proposer_call=proposer_role,
                semantic_checker_call=semantic_checker_role,
            )
        report = run_axiom_pack_discovery_eval(
            domain=domain,
            receipt_path=args.receipt or None,
            live_isomorphism=bool(args.live_isomorphism),
            model=args.model,
            n=int(args.n),
            include_second_domain=not args.no_second_domain,
            trusted_semantic_fidelity_public_key_pem=semantic_fidelity_public_key,
            expected_semantic_fidelity_verifier_ref=(
                args.semantic_fidelity_verifier_ref or None
            ),
            live_typed_producer_runtime=live_typed_producer_runtime,
        )
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.markdown_report:
            md = Path(args.markdown_report)
            md.parent.mkdir(parents=True, exist_ok=True)
            md.write_text(render_axiom_pack_discovery_eval(report), encoding="utf-8")
        if args.store:
            primary = report.get("primary") or {}
            if (
                primary.get("pack")
                and primary.get("stress")
                and primary.get("candidate_birth", {}).get("status")
                == "candidate_born"
            ):
                append_axiom_pack_event(
                    args.store,
                    pack=AxiomPack.from_json(primary["pack"]),
                    stress=primary["stress"],
                    blueprint=AxiomPackBlueprint.from_json(primary["agent_blueprint_trial"]["blueprint"]),
                    generation=primary.get("generation"),
                    candidate_birth=primary.get("candidate_birth"),
                )
            second = report.get("second_domain_eval")
            if (
                isinstance(second, dict)
                and second.get("pack")
                and second.get("stress")
                and second.get("candidate_birth", {}).get("status")
                == "candidate_born"
            ):
                append_axiom_pack_event(
                    args.store,
                    pack=AxiomPack.from_json(second["pack"]),
                    stress=second["stress"],
                    blueprint=AxiomPackBlueprint.from_json(second["agent_blueprint_trial"]["blueprint"]),
                    generation=second.get("generation"),
                    candidate_birth=second.get("candidate_birth"),
                )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if not args.path:
        ap.error("provide a JSON path or --self-test")
    obj = json.loads(Path(args.path).read_text(encoding="utf-8"))
    if obj.get("schema") == AXIOM_PACK_BLUEPRINT_SCHEMA:
        payload = screen_axiom_pack_blueprint(obj)
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.store:
            append_axiom_pack_event(
                args.store,
                pack=AxiomPack.from_json(payload["pack"]),
                stress=payload["stress"],
                blueprint=AxiomPackBlueprint.from_json(payload["blueprint"]),
                generation=payload["generation"],
            )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("screen_ok") else 1
    report = stress_axiom_pack(obj)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
