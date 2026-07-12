#!/usr/bin/env python3
"""RD-side PDE estimate workbench.

This is a thin RD caller over existing ZTARE primitives. It does not call an
LLM and does not edit Lean. It is not a second workbench; ZTARE remains the
general-purpose thesis-hardening workbench. This script exists to compose
already-shipped pieces for one proof-director move.

Use it when a typed endpoint needs analytical work and Codex wants one compact
packet before choosing a patch route:

  * workmap field/type context from `typed_endpoint_pack.py`,
  * local gap typing + Mathlib shelf from `gap_typed_prompter.py`,
  * auxiliary-object families from `auxiliary_object_catalog.py`,
  * GP-219 PDE estimate-craft op suggestions from `src/ztare`,
  * optional pi-group forcing anti-laundering checks,
  * optional single-spend carrier audit for multi-channel PDE carriers,
  * optional dimensional/endpoint checks for candidate inequalities,
  * optional toy-case variant emission through `curriculum_generator.py`.

Clean split:
  - ZTARE core/autoresearch: general theory-building primitives, falsifiers,
    framer/Lagrangian derivation, deterministic gates, and bounded briefing
    artifacts.
  - RD/Codex turn: choose a concrete proof target, inspect Lean, run local
    scouts/curriculum packs, and edit theorem files when warranted.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Kernel-location bootstrap (2026-05-25 hoist from
# projects/ns_millennium_hunt/scripts/). The workbench is general-purpose —
# callable by any PDE substrate — and now lives alongside the other RD kernel
# primitives. The residual band-aid below adds the two helper directories to
# sys.path because the helpers in scripts/public/{lean,utilities}/ are not
# yet proper Python packages (no __init__.py). Tracked separately: convert
# scripts/public/*/ into namespace packages so this bootstrap can disappear.
REPO = Path(__file__).resolve().parents[3]
for _hd in (
    REPO,
    REPO / "src",  # canonical kernel root: enables `from ztare.X import ...`
    REPO / "scripts" / "public" / "lean",
    REPO / "scripts" / "public" / "utilities",
):
    _hs = str(_hd)
    if _hs not in sys.path:
        sys.path.insert(0, _hs)

from ztare.research_director.source_currency_discriminator import (  # noqa: E402
    classify_source_currency,
)

DEFAULT_OUT_DIR = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "pde_workbench"
)
DEFAULT_RESIDUAL_NORMAL_FORM_PROFILE = (
    REPO / "projects" / "ns_millennium_hunt" / "config"
    / "residual_normal_forms.json"
)
LEAN_ROOT = REPO / "ztare_proofs" / "ZtareProofs"

from ztare.substrates.ns_millennium_hunt.pde_profiles import (  # noqa: E402
    FRESH_ANNULAR_ANTI_LAUNDERING_PROFILE,
    FRESH_ANNULAR_INNOVATION_PROFILE,
    FRESH_ANNULAR_NON_DISGUISE_PROFILE,
    NS_HOSTILE_PACKET_SUITES,
    NS_SCALED_TRANSFER_NUMERIC_PROFILE,
    NS_THEOREM_APPLICABILITY_DB,
    OWNER_GEOMETRY_CORE_PROFILE,
    PDE_SINGLE_SPEND_PROFILE,
    SECTION_FIXED_UNSIGNED_VARIATION_PROFILE,
    TRANSFORM_HINTS,
)

def safe_slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_")[:120]


def _json_or_file(raw: str | Path | None) -> Any:
    """Parse a JSON literal or a path containing JSON."""
    if raw is None:
        return None
    text = str(raw)
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(stripped)
    return json.loads(Path(text).read_text(encoding="utf-8"))


def _find_live_lean_decl(target: str) -> dict[str, Any] | None:
    """Best-effort source-truth fallback when the workmap is stale.

    This intentionally stays shallow: it finds the declaration line and, for
    structures/classes, extracts displayed field names and type snippets.  It is
    a context aid, not a parser or theorem prover.
    """
    decl_modifiers = r"(?:(?:noncomputable|private|protected|unsafe|partial)\s+)*"
    decl_re = re.compile(
        rf"^\s*{decl_modifiers}(structure|class|theorem|def|lemma|abbrev)\s+"
        rf"{re.escape(target)}\b"
    )
    next_decl_re = re.compile(
        rf"^\s*{decl_modifiers}"
        r"(structure|class|theorem|def|lemma|abbrev|opaque|axiom|inductive)\s+"
    )
    field_re = re.compile(r"^\s{2,}([A-Za-z_][A-Za-z0-9_']*)\s*:\s*(.*)$")

    def preceding_doc_comment(lines: list[str], decl_idx: int) -> str:
        j = decl_idx - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        if j < 0 or not lines[j].strip().endswith("-/"):
            return ""
        parts: list[str] = []
        while j >= 0:
            parts.append(lines[j])
            if "/--" in lines[j]:
                return "\n".join(reversed(parts))
            j -= 1
        return ""

    for path in LEAN_ROOT.glob("*.lean"):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(lines):
            match = decl_re.match(line)
            if not match:
                continue
            kind = match.group(1)
            block: list[str] = []
            for later in lines[i + 1:]:
                if next_decl_re.match(later) and not later.startswith("  "):
                    break
                block.append(later)
            fields: list[dict[str, str]] = []
            current: dict[str, str] | None = None
            for raw in block:
                field_match = field_re.match(raw)
                if field_match:
                    if current:
                        fields.append(current)
                    current = {
                        "name": field_match.group(1),
                        "type": field_match.group(2).strip(),
                    }
                    continue
                if current and raw.startswith("    "):
                    current["type"] = (current["type"] + " " + raw.strip()).strip()
            if current:
                fields.append(current)
            header_text = " ".join([line] + block[:4])
            parent_fields: list[dict[str, str]] = []
            parent_match = re.search(
                r"\bextends\s+([A-Za-z_][A-Za-z0-9_'.]*)", header_text
            )
            if parent_match:
                parent_name = parent_match.group(1).split(".")[-1]
                if parent_name and parent_name != target:
                    parent_ctx = _find_live_lean_decl(parent_name)
                    if parent_ctx:
                        for parent_field in parent_ctx.get("fields", []):
                            if isinstance(parent_field, dict):
                                copied = dict(parent_field)
                                copied.setdefault("inherited_from", parent_name)
                                parent_fields.append(copied)
            combined_fields = fields + parent_fields
            return {
                "found": True,
                "source": "live_lean_fallback",
                "target": target,
                "kind": kind,
                "doc": preceding_doc_comment(lines, i),
                "file": str(path.relative_to(REPO)),
                "line": i + 1,
                "n_fields": len(combined_fields),
                "fields": combined_fields[:160],
            }
    return None


def load_target_context(target: str, field: str | None) -> dict[str, Any]:
    from typed_endpoint_pack import (
        find_theorems_using_field,
        find_type_constructors,
        find_type_producers,
        load_decl_index,
        load_workmap_target,
        resolve_field,
    )

    live = _find_live_lean_decl(target)
    target_obj = load_workmap_target(target)
    if not target_obj:
        if live:
            return {
                "found": True,
                "target": target,
                "field": field,
                "target_file": live.get("file"),
                "source": live.get("source"),
                "kind": live.get("kind"),
                "doc": live.get("doc") or "",
                "line": live.get("line"),
                "n_fields": live.get("n_fields"),
                "fields": live.get("fields") or [],
                "field_info": None,
                "constructors": [],
                "type_producers": [],
                "nearby_theorems": [],
            }
        return {
            "found": False,
            "target": target,
            "field": field,
            "reason": "target not found in workmap",
        }
    field_info = resolve_field(target_obj, field) if field else None
    decl_index = load_decl_index()
    constructors: list[dict[str, Any]] = []
    type_producers: list[dict[str, Any]] = []
    nearby: list[dict[str, Any]] = []
    if field_info:
        constructors = find_type_constructors(field_info["type_head"], decl_index)
        type_producers = find_type_producers(field_info["type_head"], top_n=10)
        nearby = find_theorems_using_field(
            field_info["field_name"], field_info["type_head"], top_n=10)
    return {
        "found": True,
        "target": target,
        "field": field,
        "target_file": (live or {}).get("file") or target_obj.get("file"),
        "source": "workmap+live_lean" if live else "workmap",
        "kind": (live or {}).get("kind"),
        "doc": (live or {}).get("doc") or target_obj.get("doc") or "",
        "line": (live or {}).get("line"),
        "endpoint_exposure": target_obj.get("endpoint_exposure"),
        "n_downstream_users": target_obj.get("n_downstream_users"),
        "priority": target_obj.get("closure_priority_score")
            or target_obj.get("leverage_score")
            or target_obj.get("priority"),
        "n_fields": (live or {}).get("n_fields") or target_obj.get("n_fields"),
        "fields": ((live or {}).get("fields") or target_obj.get("fields") or [])[:160],
        "field_info": field_info,
        "constructors": constructors[:5],
        "type_producers": type_producers[:10],
        "nearby_theorems": nearby[:10],
    }


def classify_gap_local(target: str, field: str | None) -> dict[str, Any]:
    if not field:
        return {
            "gap_type": "UNKNOWN",
            "confidence": "low",
            "rationale": "No field supplied.",
            "classifier": "pde_estimate_workbench",
        }
    from gap_typed_prompter import classify_gap
    return classify_gap(target, field, dry_run=True)


def _compact_query_fragment(value: Any, *, budget: int = 900) -> str:
    """Small deterministic stringifier for semantic-query side information."""
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=True)
    except TypeError:
        raw = str(value)
    return raw[:budget]


def _apn_query_text(
    target_name: str,
    field: str | None,
    *,
    context: dict[str, Any] | None = None,
    gap: dict[str, Any] | None = None,
    basin_context: dict[str, Any] | None = None,
    pde_ops: list[dict[str, Any]] | None = None,
    candidate_inequalities: list[str] | None = None,
    target_currency: str | None = None,
) -> str:
    """Build a semantic APN query from the actual PDE packet, not names alone."""
    terms: list[str] = [target_name, field or "", target_currency or ""]
    if gap:
        terms.append(str(gap.get("gap_type") or ""))
        terms.append(str(gap.get("rationale") or ""))
    if context:
        terms.append(str(context.get("doc") or ""))
        for item in context.get("fields", [])[:20]:
            if isinstance(item, dict):
                terms.append(str(item.get("name") or ""))
                terms.append(str(item.get("type") or ""))
        for item in context.get("constructors", [])[:8]:
            if isinstance(item, dict):
                terms.append(str(item.get("type_head") or ""))
    if basin_context:
        preferred = (
            "tag_fingerprint",
            "typed_failure_log",
            "manifest_aliases",
            "nearby_refutations",
            "open_obligation_proximity",
        )
        used = False
        for key in preferred:
            if key in basin_context:
                terms.append(_compact_query_fragment({key: basin_context.get(key)}))
                used = True
        if not used:
            terms.append(_compact_query_fragment(basin_context))
    for op in pde_ops or []:
        terms.append(str(op.get("name") or op.get("op_id") or ""))
        terms.append(str(op.get("rationale") or ""))
        terms.append(str(op.get("gate_mechanization") or ""))
    terms.extend(str(x) for x in candidate_inequalities or [])
    query = " ".join(t for t in terms if t).strip()
    return query[:1800]


def _load_apn_semantic_for_target(
    target_name: str,
    field: str | None,
    *,
    context: dict[str, Any] | None = None,
    gap: dict[str, Any] | None = None,
    basin_context: dict[str, Any] | None = None,
    pde_ops: list[dict[str, Any]] | None = None,
    candidate_inequalities: list[str] | None = None,
    target_currency: str | None = None,
    threshold: float = 0.55,
    top_k: int = 5,
) -> dict | None:
    """Workbench consumer of the APN cross-corpus bridge.

    Builds a free-text query from the PDE packet and returns both nearest APN
    declarations and explicit ``ns_apn_bridge`` edges. Graceful degradation —
    never raises into the workbench.
    """
    try:
        from ztare.research_director.apn_semantic import apn_semantic_neighbours
    except Exception:
        return {"available": False, "skip_reason": "apn_semantic module not importable"}
    query = _apn_query_text(
        target_name, field, context=context, gap=gap, basin_context=basin_context,
        pde_ops=pde_ops, candidate_inequalities=candidate_inequalities,
        target_currency=target_currency,
    )
    if not query:
        return {"available": False, "skip_reason": "empty target/field"}
    try:
        hits, corpus_size, filtered_size, skip_reason = apn_semantic_neighbours(
            query, threshold=threshold, top_k=top_k,
        )
    except Exception as e:
        return {"available": False, "skip_reason": f"apn lookup failed: {e!r}"}
    hit_rows = [
        {
            "id": h.id, "name": h.name, "kind": h.kind, "domain": h.domain,
            "file": h.file, "variant_tag": h.variant_tag,
            "cosine": h.cosine, "snippet": h.snippet,
        }
        for h in hits
    ]
    bridge_edges = [
        {
            "@type": "ns_apn_bridge",
            "src": target_name,
            "src_field": field,
            "dst_apn": h["id"],
            "cosine": h["cosine"],
            "apn_name": h["name"],
            "apn_kind": h["kind"],
            "apn_domain": h["domain"],
            "apn_file": h["file"],
            "apn_variant_tag": h["variant_tag"],
        }
        for h in hit_rows
    ]
    return {
        "available": True,
        "query": query,
        "threshold": threshold,
        "top_k": top_k,
        "corpus_size": corpus_size,
        "filtered_size": filtered_size,
        "skip_reason": skip_reason,
        "hits": hit_rows,
        "bridge_edges": bridge_edges,
    }


def _load_basin_context_for_target(target_name: str) -> dict | None:
    """Workbench consumer of the enriched-basin signals (2026-05-26 turbocharge).

    Defers to enrich_basin_with_proof_history.summarize_basin_context_for_target
    when present. Returns None if the enriched basin or the helper is unavailable
    (graceful degradation — never raises into the workbench's deterministic flow).
    """
    try:
        import importlib.util
        helper_path = REPO / "projects" / "ns_millennium_hunt" / "scripts" / "enrich_basin_with_proof_history.py"
        if not helper_path.exists():
            return None
        spec = importlib.util.spec_from_file_location("_basin_history_helper", helper_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "summarize_basin_context_for_target"):
            return mod.summarize_basin_context_for_target(target_name)
    except Exception:
        return None
    return None


def fetch_lemmas(gap_type: str, top: int) -> list[dict[str, Any]]:
    from gap_typed_prompter import fetch_gap_specific_lemmas
    lemmas = fetch_gap_specific_lemmas(gap_type, top_n=top)
    return [
        {
            "name": lemma.get("name"),
            "file": lemma.get("file"),
            "shapes": lemma.get("shapes", []),
            "preview": (lemma.get("preview") or "")[:240],
        }
        for lemma in lemmas
    ]


AUXILIARY_FAMILY_FALLBACKS: list[dict[str, Any]] = [
    {
        "family": "exponential_majorant",
        "mathematical_form": "B(x) = C1 exp(C2 phi(x)) for a convex phi",
        "gap_types": ["PROPAGATION", "COERCIVITY", "AUXILIARY"],
        "source_mathematician": ["maximum principle", "barrier method"],
        "typical_use_pattern": "turn local growth into a propagated envelope",
        "ns_track_b_relevance": "pressure or cutoff growth envelopes that must be paid outside the target spend",
    },
    {
        "family": "cutoff_partition",
        "mathematical_form": "psi in C_c^infty, 0 <= psi <= 1, psi = 1 on K",
        "gap_types": ["LOCALIZATION", "COMMUTATOR", "AUXILIARY", "PROPAGATION"],
        "source_mathematician": ["Caccioppoli", "local energy method"],
        "typical_use_pattern": "separate interior payment from boundary leakage",
        "ns_track_b_relevance": "annular owner fibers, cutoff pressure leakage, and C7 prefix invoices",
    },
    {
        "family": "energy_with_correction",
        "mathematical_form": "E_tilde(t) = E(t) + delta F(t)",
        "gap_types": ["PROPAGATION", "COERCIVITY", "COMMUTATOR"],
        "source_mathematician": ["modified energy", "normal form"],
        "typical_use_pattern": "absorb sign-indefinite terms into a coercive corrected quantity",
        "ns_track_b_relevance": "tests whether signed pressure cancellation can be converted to a positive receipt",
    },
    {
        "family": "monotone_quantity",
        "mathematical_form": "M(t) monotone after choosing the right test object",
        "gap_types": ["PROPAGATION", "LIMIT_PASSAGE", "AUXILIARY"],
        "source_mathematician": ["monotonicity formula"],
        "typical_use_pattern": "replace pointwise control by a one-directional ledger",
        "ns_track_b_relevance": "candidate carrier-local variation budgets that must survive prefix refinement",
    },
    {
        "family": "blowup_profile_renormalization",
        "mathematical_form": "U_hat(s,y) = lambda(t)^alpha U(t, x(t) + lambda(t)y)",
        "gap_types": ["PROPAGATION", "COMPACTNESS", "AUXILIARY"],
        "source_mathematician": ["blowup analysis", "renormalization"],
        "typical_use_pattern": "move a scale-critical failure into a fixed-window profile",
        "ns_track_b_relevance": "tests whether a hostile packet is excluded by profile rigidity rather than hidden CF/BV input",
    },
]


def _fallback_auxiliary_families(gap_type: str, keyword: str | None) -> list[dict[str, Any]]:
    gap = gap_type.upper()
    key = (keyword or "").lower()
    rows = []
    for item in AUXILIARY_FAMILY_FALLBACKS:
        gap_match = gap in {str(x).upper() for x in item.get("gap_types", [])} or gap == "AUXILIARY"
        haystack = " ".join(str(v) for v in item.values()).lower()
        keyword_match = not key or key in haystack
        if gap_match and keyword_match:
            rows.append(item)
    if not rows and gap != "AUXILIARY":
        rows = _fallback_auxiliary_families("AUXILIARY", keyword)
    return rows


def fetch_auxiliary_families(gap_type: str, keyword: str | None, top: int) -> list[dict[str, Any]]:
    try:
        from auxiliary_object_catalog import query_catalog
        families = query_catalog(gap_type=gap_type, keyword=keyword)
        if not families and gap_type != "AUXILIARY":
            families = query_catalog(gap_type="AUXILIARY", keyword=keyword)
    except ModuleNotFoundError:
        families = _fallback_auxiliary_families(gap_type, keyword)
    return [
        {
            "family": item.get("family"),
            "mathematical_form": item.get("mathematical_form"),
            "gap_types": item.get("gap_types", []),
            "source_mathematician": item.get("source_mathematician", []),
            "typical_use_pattern": item.get("typical_use_pattern", ""),
            "ns_track_b_relevance": item.get("ns_track_b_relevance", ""),
        }
        for item in families[:top]
    ]


def suggest_pde_craft_ops(
    gap_type: str,
    target: str,
    field: str | None,
    inequalities: list[str],
    context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Recommend ZTARE PDE estimate-craft primitives for the current surface."""
    from ztare.research_director.pde_estimate_craft_ops import get

    context_terms: list[str] = []
    if context:
        doc = str(context.get("doc", ""))
        if doc:
            context_terms.append(doc)
        for item in context.get("fields", []):
            name = str(item.get("name", ""))
            ftype = str(item.get("type", ""))
            context_terms.append(f"{name} {ftype}")

    raw_haystack = " ".join([
        target,
        field or "",
        *inequalities,
        *context_terms,
    ]).lower()
    haystack = f"{raw_haystack} {raw_haystack.replace('-', '_')}"
    op_ids: list[tuple[str, str]] = []

    if gap_type in {"AUXILIARY", "UNKNOWN", "COERCIVITY"} or any(
        token in haystack
        for token in ("carrier", "localiz", "freshregion", "fresh_region",
                      "eventtent", "event_tent", "gauge", "collar")
    ):
        op_ids.append((
            "pec_a",
            "construct the missing carrier/test object explicitly before proving estimates",
        ))
    if gap_type in {"COERCIVITY", "UNKNOWN"} or any(
        token in haystack
        for token in ("rebill", "endpoint", "sharp", "failure", "counter")
    ):
        op_ids.append((
            "pec_e",
            "build the hostile witness or sharpness model before accepting the route",
        ))
    if gap_type in {"LIMIT_PASSAGE", "PROPAGATION"} or any(
        token in haystack
        for token in ("prefix", "finite", "limit", "inherit", "propagation")
    ):
        op_ids.append((
            "pec_d",
            "name the finite-to-limit or persistence lemma instead of assuming inheritance",
        ))
    if any(
        token in haystack
        for token in (
            "nonadaptive", "non-adaptive", "predeclared", "preselected",
            "fixed before", "fixedbefore", "before payoff", "beforepayoff",
            "before radius", "no post hoc", "noposthoc", "posthoc",
            "source selection", "sourceselection", "selected before",
            "chosen before", "auditindex", "audit index",
        )
    ):
        op_ids.append((
            "pec_i",
            "prove the source/event/window/schedule selection is fixed before payoff",
        ))
    if gap_type == "PACKING" or any(
        token in haystack
        for token in (
            "same-carrier", "same_carrier", "fresh capacity", "fresh_capacity",
            "fresh annular", "fresh_annular", "no reuse", "no_reuse",
            "noreuse", "nonreuse", "rebilling", "rebill", "injection",
            "injective", "packing", "bounded overlap", "bounded_overlap",
            "disjoint", "capacity packet", "monotone reserve",
            "reserve drop", "same capacity", "same_capacity",
        )
    ):
        op_ids.append((
            "pec_j",
            "prove same-carrier fresh packing/no-reuse injection before accepting the route",
        ))
    if any(
        token in haystack
        for token in (
            "phase-space", "phase_space", "phase space", "microlocal",
            "littlewood-paley", "littlewood_paley", "lp tile", "lp_tile",
            "bony tile", "bony_tile", "packet", "tile", "tube",
            "owner map", "ownermap", "owner atom", "owner_atom",
            "ownership", "preimage", "owner preimage", "owner_preimage",
            "event-to-packet", "event_to_packet", "event-to-atom",
            "event_to_atom", "owned event", "owned_event",
            "owned event prefix", "owned_event_prefix",
            "event prefix budget", "event_prefix_budget",
            "event pay", "event_pay", "event stream", "event_stream",
            "selected prefix map", "selected_prefix_map",
            "same selected prefix map", "same_selected_prefix_map",
            "bounded multiplicity", "bounded_multiplicity",
            "material tube", "material_tube", "transported tube",
            "global selected-tree", "global_selected_tree",
            "output-scale", "output_scale", "output packet",
            "output_packet", "full packet", "full_packet",
            "product tile", "product_tile", "bilinear packet",
            "bilinear_packet", "factor reuse", "factor_reuse",
            "factor owner", "factor_owner", "catalyst",
            "low-high", "low_high", "pressure sheath",
            "pressure_sheath",
        )
    ):
        op_ids.append((
            "pec_k",
            "prove pre-payoff phase-space/material ownership plus a numerical owner-preimage or prefix budget",
        ))
    if any(
        token in haystack
        for token in ("regime", "class", "same-tree", "same_tree",
                      "subcritical", "endpoint", "type-i", "type_i",
                      "type i", "typei", "amplitude envelope",
                      "amplitude_envelope")
    ):
        op_ids.append((
            "pec_b",
            "scope the regime precisely so later estimates cannot use deferred cases",
        ))
    if any(
        token in haystack
        for token in (
            "weak l", "weak-l", "weak_l", "weakl", "tail",
            "distribution", "reverse holder", "reverse-holder",
            "anti-concentration", "anticoncentration", "level-set",
            "level set", "positive part", "signed average",
            "conditional average", "integrability",
            "critical source square", "critical_source_square",
            "source-square", "source square", "source_square",
            "source carleson", "source-carleson", "source_carleson",
            "annular renewal budget", "annular_renewal_budget",
            "duhamel source square", "duhamel_source_square",
            "paraproduct source", "paraproduct_source",
        )
    ):
        op_ids.append((
            "pec_h",
            "upgrade average/integral control to a local distribution tail or reverse Holder estimate",
        ))
    if any(
        token in haystack
        for token in (
            "skew", "skew-symmetry", "skew_symmetry",
            "energy cancellation", "energy_cancellation",
            "signed cancellation", "signed_cancellation",
            "null-form", "null_form", "null form",
            "symbol vanishing", "symbol_vanishing",
            "bilinear cancellation", "bilinear_cancellation",
            "projection cancellation", "projection_cancellation",
            "leray projection cancellation", "leray_projection_cancellation",
            "commutator cancellation", "commutator_cancellation",
            "signed-to-positive", "signed_to_positive",
            "signed identity", "signed_identity",
            "signed measure", "signed_measure",
            "trace-free", "trace_free", "tracefree",
            "positive variation", "positive_variation",
            "total variation", "total_variation",
            "positive source square", "positive_source_square",
            "dual price", "dual_price", "dual product", "dual_product",
            "self-tax", "self_tax", "selftax", "production_sq",
            "production^2", "production squared", "frame self tax",
            "frame_self_tax",
            "high-high", "high_high",
        )
    ):
        op_ids.append((
            "pec_l",
            "audit that the claimed signed/symbol cancellation pays the positive target quantity",
        ))
    if any(
        token in haystack
        for token in ("coordinate", "representation", "gauge", "section",
                      "duhamel", "pressure")
    ):
        op_ids.append((
            "cand_g",
            "try a same-system representation change if the current carrier hides structure",
        ))

    if any(
        token in haystack
        for token in (
            "log-corrected", "log_corrected", "log log", "log-log",
            "kozono", "taniuchi", "log bkm", "log-bkm",
            "non-pure-power", "non_pure_power", "pure power",
            "parabolic slaving", "parabolic_slaving", "tick647",
        )
    ):
        op_ids.append((
            "pec_b",
            "classify the asymptotic regime before using or bypassing the parabolic-slaving wall",
        ))
        op_ids.append((
            "pec_e",
            "test whether the log correction is a genuine non-pure-power receipt or a BKM-log relabel",
        ))
    if any(
        token in haystack
        for token in (
            "topological", "topology", "vortex link", "vortex-line",
            "vortex line", "helicity", "reconnection", "linking",
            "moffatt", "ricca", "vortex topology",
        )
    ):
        op_ids.append((
            "pec_i",
            "fix the topology/extractor before payoff so a topological label cannot be selected after seeing the route",
        ))
        op_ids.append((
            "pec_k",
            "prove finite owner-preimage multiplicity for topology/reconnection events before treating them as controllable",
        ))
        op_ids.append((
            "pec_e",
            "run the helicity-dark/topology-dark hostile packet before accepting the candidate",
        ))

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for op_id, rationale in op_ids:
        if op_id in seen:
            continue
        seen.add(op_id)
        op = get(op_id)
        if op is None:
            continue
        out.append({
            "op_id": op.op_id,
            "name": op.name,
            "tier": op.tier,
            "rationale": rationale,
            "gate_mechanization": op.gate_mechanization,
            "boundary_collapse_risk": op.boundary_collapse_risk,
        })
    return out


def build_pde_execution_contract(
    pde_ops: list[dict[str, Any]],
    *,
    min_work_units: int = 3,
    hostile_suite: str = "ns_default",
    target_currency: str | None = None,
) -> dict[str, Any]:
    """Build the execution-mode contract for an RD PDE estimate attempt."""
    from ztare.research_director.hostile_packet_suite import (
        build_hostile_packet_suite,
    )
    from ztare.pde.currency import (
        pde_currency_ledger_template,
    )
    from ztare.pde.ops import (
        pde_execution_template_for_ops,
    )

    op_ids = [str(op.get("op_id")) for op in pde_ops if op.get("op_id")]
    hostile_packets = NS_HOSTILE_PACKET_SUITES.get(hostile_suite)
    if hostile_packets is None:
        hostile_packets = []
    return {
        "mode": "pde-execution",
        "minimum_work_units": min_work_units,
        "gp219_execution_templates": pde_execution_template_for_ops(op_ids),
        "hostile_packet_suite": build_hostile_packet_suite(
            hostile_suite,
            hostile_packets,
        ),
        "theorem_applicability_db": {
            "profile": "ns_millennium_hunt",
            "theorems": NS_THEOREM_APPLICABILITY_DB,
            "matcher": "src/ztare/research_director/theorem_applicability_db.py",
        },
        "currency_ledger_template": pde_currency_ledger_template(target_currency),
        "no_early_stop_rule": {
            "terminal_gap_verdicts": [
                "MISSING_HYPOTHESIS",
                "OPEN",
                "NO_CLOSE",
                "THEOREM_OR_DOMAIN_GAP",
                "NEW_PDE_WORK_NEEDED",
            ],
            "required_before_terminal_gap": {
                "estimate_derivation_min": 2,
                "falsifier_packet_min": 1,
                "requires_one_of": ["smaller_theorem", "literature_match"],
            },
            "constructive_turn_rule": {
                "trigger": (
                    "conditional/source law plus bounded or selectable target "
                    "carrier is visible and no immediate packet kill is declared"
                ),
                "required_before_more_obstruction_only_work": [
                    "positive_constructor_attempt"
                ],
                "work_unit_fields": [
                    "source_law",
                    "target_carrier",
                    "bounded_or_selectable_variable",
                    "constructor_map",
                    "nearest_confuser",
                    "first_failed_line_or_success",
                    "conclusion",
                ],
            },
            "linter": "src/ztare/research_director/pde_work_unit_gate.py",
            "linter_cli": "python -m src.ztare.research_director.pde_work_unit_gate <payload.json>",
            "receipt_strength_linter": "src/ztare/research_director/receipt_strength_audit.py",
            "receipt_strength_rule": (
                "Prop-only proofs of no-overlap, same-owner/source, no-reuse, "
                "or payoff-independence do not discharge the PDE receipt; "
                "supply typed/numeric backing or record the exact missing receipt."
            ),
        },
        "prompt_contract": [
            "Normalize variables.",
            "Write one target inequality.",
            "Attempt the estimate and name the first failed line.",
            "Test at least one hostile packet.",
            "If a conditional source law and bounded/selectable carrier are visible, attempt the positive constructor before adding another obstruction layer.",
            "Run receipt-strength audit when using no-overlap, same-owner/source, no-reuse, or payoff-independence fields.",
            "Either repair the theorem, shrink the residual, or prove an exact theorem match.",
        ],
        "notebook_templates": [
            "normalization.md",
            "estimate_attempt_1.md",
            "estimate_attempt_2.md",
            "positive_constructor_attempt.md",
            "hostile_packet_1.md",
            "first_failed_line.md",
            "corrected_theorem.md",
            "theorem_applicability_match.md",
        ],
    }


def run_moment_ratio_surplus_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-MOMENT-RATIO-SURPLUS checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.moment_ratio_surplus_gate import run_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"moment_ratio_check_{i}")
        result = run_gate(
            first_moment_sq=check.get("first_moment_sq"),
            second_moment_cap=check.get("second_moment_cap"),
            cheap_boundary_lower_bound=check.get("cheap_boundary_lower_bound"),
            threshold_space_measure=check.get("threshold_space_measure"),
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_bounded_ratio_support_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-BOUNDED-RATIO-SUPPORT checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.bounded_ratio_support_gate import run_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"bounded_ratio_support_check_{i}")
        result = run_gate(
            mean_surplus=check.get("mean_surplus"),
            ratio_upper_bound=check.get("ratio_upper_bound"),
            companion_lower_bound=check.get("companion_lower_bound"),
            threshold_space_measure=check.get("threshold_space_measure"),
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_finite_prefix_selection_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINITE-PREFIX-SELECTION checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.finite_prefix_selection_gate import run_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"finite_prefix_selection_check_{i}")
        result = run_gate(
            boundary=check.get("boundary"),
            interface=check.get("interface"),
            prefix_length=check.get("prefix_length"),
            same_source_family=bool(check.get("same_source_family")),
            prefix_fixed_before_payoff=bool(check.get("prefix_fixed_before_payoff")),
            boundary_interface_units_aligned=bool(
                check.get("boundary_interface_units_aligned")
            ),
            no_post_payoff_selection=bool(check.get("no_post_payoff_selection")),
            interface_floor=check.get("interface_floor"),
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_event_family_binding_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-EVENT-FAMILY-BINDING checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.event_family_binding_gate import (
        run_event_family_binding_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"event_family_binding_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_event_family_binding_gate(check, enforce_block=enforce_block)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_analogical_transfer_receipt_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-ANALOGICAL-TRANSFER-RECEIPT checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.analogical_transfer_receipt_gate import (
        run_analogical_transfer_receipt_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"analogical_transfer_receipt_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_analogical_transfer_receipt_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_prefix_count_bridge_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-PREFIX-COUNT-BRIDGE checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.prefix_count_bridge_gate import (
        run_prefix_count_bridge_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"prefix_count_bridge_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_prefix_count_bridge_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_source_prefix_budget_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SOURCE-PREFIX-BUDGET checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.source_prefix_budget_gate import (
        run_source_prefix_budget_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"source_prefix_budget_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_source_prefix_budget_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_final_slot_indexed_source_budget_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINAL-SLOT-INDEXED-SOURCE-BUDGET checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.final_slot_indexed_source_budget_gate import (
        run_final_slot_indexed_source_budget_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"final_slot_indexed_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_final_slot_indexed_source_budget_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_target_indexed_event_assignment_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TARGET-INDEXED-EVENT-ASSIGNMENT-PROVENANCE checks."""
    if not checks:
        return []
    from ztare.gates.target_indexed_event_assignment_gate import (
        run_target_indexed_event_assignment_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"target_indexed_assignment_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_target_indexed_event_assignment_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_incidence_derived_finite_injection_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-INCIDENCE-DERIVED-FINITE-INJECTION checks."""
    if not checks:
        return []
    from ztare.gates.incidence_derived_finite_injection_gate import (
        run_incidence_derived_finite_injection_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"incidence_injection_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_incidence_derived_finite_injection_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_bounded_incident_existence_eventdata_horizon_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-BOUNDED-INCIDENT-EXISTENCE-EVENTDATA-HORIZON checks."""
    if not checks:
        return []
    from ztare.gates.bounded_incident_existence_eventdata_horizon_gate import (
        run_bounded_incident_existence_eventdata_horizon_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"bounded_incident_eventdata_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_bounded_incident_existence_eventdata_horizon_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_target_event_candidate_cover_selection_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TARGET-EVENT-CANDIDATE-COVER-SELECTION checks."""
    if not checks:
        return []
    from ztare.gates.target_event_candidate_cover_selection_gate import (
        run_target_event_candidate_cover_selection_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"target_event_cover_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_target_event_candidate_cover_selection_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_target_cover_eventdata_incidence_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TARGET-COVER-EVENTDATA-INCIDENCE checks."""
    if not checks:
        return []
    from ztare.gates.target_cover_eventdata_incidence_gate import (
        run_target_cover_eventdata_incidence_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"target_cover_eventdata_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_target_cover_eventdata_incidence_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_cover_event_selector_finalslot_assignment_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-COVER-EVENT-SELECTOR-FINALSLOT-ASSIGNMENT checks."""
    if not checks:
        return []
    from ztare.gates.cover_event_selector_finalslot_assignment_gate import (
        run_cover_event_selector_finalslot_assignment_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"cover_selector_assignment_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_cover_event_selector_finalslot_assignment_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_target_slot_bounded_incidence_least_hit_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TARGET-SLOT-BOUNDED-INCIDENCE-LEAST-HIT checks."""
    if not checks:
        return []
    from ztare.gates.target_slot_bounded_incidence_least_hit_gate import (
        run_target_slot_bounded_incidence_least_hit_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"target_slot_least_hit_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_target_slot_bounded_incidence_least_hit_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_bounded_incident_existence_sametree_eventdata_index_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-BOUNDED-INCIDENT-EXISTENCE-SAMETREE-EVENTDATA-INDEX checks."""
    if not checks:
        return []
    from ztare.gates.bounded_incident_existence_sametree_eventdata_index_gate import (
        run_bounded_incident_existence_sametree_eventdata_index_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"same_tree_eventdata_index_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_bounded_incident_existence_sametree_eventdata_index_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_target_eventdata_index_prefix_cover_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TARGET-EVENTDATA-INDEX-PREFIX-COVER checks."""
    if not checks:
        return []
    from ztare.gates.target_eventdata_index_prefix_cover_gate import (
        run_target_eventdata_index_prefix_cover_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"target_eventdata_prefix_cover_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_target_eventdata_index_prefix_cover_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_finite_scale_cofinality_prefix_cover_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINITE-SCALE-COFINALITY-PREFIX-COVER checks."""
    if not checks:
        return []
    from ztare.gates.finite_scale_cofinality_prefix_cover_gate import (
        run_finite_scale_cofinality_prefix_cover_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"finite_scale_cofinality_cover_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_finite_scale_cofinality_prefix_cover_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_event_to_badnode_selected_index_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-EVENT-TO-BADNODE-SELECTED-INDEX checks."""
    if not checks:
        return []
    from ztare.gates.event_to_badnode_selected_index_gate import (
        run_event_to_badnode_selected_index_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"event_to_badnode_index_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_event_to_badnode_selected_index_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_event_prefix_coverage_selected_index_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-EVENT-PREFIX-COVERAGE-SELECTED-INDEX checks."""
    if not checks:
        return []
    from ztare.gates.event_prefix_coverage_selected_index_gate import (
        run_event_prefix_coverage_selected_index_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"event_prefix_coverage_index_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_event_prefix_coverage_selected_index_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_coverage_choice_finite_selector_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-COVERAGE-CHOICE-FINITE-SELECTOR checks."""
    if not checks:
        return []
    from ztare.gates.coverage_choice_finite_selector_gate import (
        run_coverage_choice_finite_selector_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"coverage_choice_selector_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_coverage_choice_finite_selector_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_typed_appearance_coverage_choice_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TYPED-APPEARANCE-COVERAGE-CHOICE checks."""
    if not checks:
        return []
    from ztare.gates.typed_appearance_coverage_choice_gate import (
        run_typed_appearance_coverage_choice_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"typed_appearance_choice_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_typed_appearance_coverage_choice_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_typed_coverage_packet_appearance_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TYPED-COVERAGE-PACKET-APPEARANCE checks."""
    if not checks:
        return []
    from ztare.gates.typed_coverage_packet_appearance_gate import (
        run_typed_coverage_packet_appearance_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"typed_coverage_packet_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_typed_coverage_packet_appearance_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_event_prefix_enumeration_packet_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-EVENT-PREFIX-ENUMERATION-PACKET checks."""
    if not checks:
        return []
    from ztare.gates.event_prefix_enumeration_packet_gate import (
        run_event_prefix_enumeration_packet_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"event_prefix_enumeration_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_event_prefix_enumeration_packet_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_bounded_natural_event_enumeration_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-BOUNDED-NATURAL-EVENT-ENUMERATION checks."""
    if not checks:
        return []
    from ztare.gates.bounded_natural_event_enumeration_gate import (
        run_bounded_natural_event_enumeration_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"bounded_nat_event_enum_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_bounded_natural_event_enumeration_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_unbounded_event_witness_prefix_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-UNBOUNDED-EVENT-WITNESS-PREFIX-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.unbounded_event_witness_prefix_bound_gate import (
        run_unbounded_event_witness_prefix_bound_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"unbounded_event_witness_bound_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_unbounded_event_witness_prefix_bound_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_cofinal_incidence_witness_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-COFINAL-INCIDENCE-WITNESS-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.cofinal_incidence_witness_bound_gate import (
        run_cofinal_incidence_witness_bound_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"cofinal_incidence_witness_bound_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_cofinal_incidence_witness_bound_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_explicit_cofinal_event_witness_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-EXPLICIT-COFINAL-EVENT-WITNESS-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.explicit_cofinal_event_witness_bound_gate import (
        run_explicit_cofinal_event_witness_bound_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label") or
            f"explicit_cofinal_event_witness_bound_check_{i}"
        )
        enforce_block = bool(check.get("enforce_block"))
        result = run_explicit_cofinal_event_witness_bound_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_cofinal_event_selector_final_prefix_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-COFINAL-EVENT-SELECTOR-FINAL-PREFIX-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.cofinal_event_selector_final_prefix_bound_gate import (
        run_cofinal_event_selector_final_prefix_bound_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label") or
            f"cofinal_event_selector_final_prefix_bound_check_{i}"
        )
        enforce_block = bool(check.get("enforce_block"))
        result = run_cofinal_event_selector_final_prefix_bound_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_finite_cofinal_event_selector_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINITE-COFINAL-EVENT-SELECTOR checks."""
    if not checks:
        return []
    from ztare.gates.finite_cofinal_event_selector_gate import (
        run_finite_cofinal_event_selector_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"finite_cofinal_event_selector_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_finite_cofinal_event_selector_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_positive_variation_bridge_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-POSITIVE-VARIATION-BRIDGE checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.positive_variation_bridge_gate import (
        run_positive_variation_bridge_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"positive_variation_bridge_check_{i}")
        result = run_positive_variation_bridge_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_positive_variation_quotient_wash_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-POSITIVE-VARIATION-QUOTIENT-WASH checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.positive_variation_quotient_wash_gate import (
        run_positive_variation_quotient_wash_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"positive_variation_quotient_wash_check_{i}")
        result = run_positive_variation_quotient_wash_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_quotient_minimal_carrier_payment_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-QUOTIENT-MINIMAL-CARRIER-PAYMENT checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.quotient_minimal_carrier_payment_gate import (
        run_quotient_minimal_carrier_payment_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"quotient_minimal_carrier_payment_check_{i}")
        result = run_quotient_minimal_carrier_payment_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_quadratic_quotient_descent_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-QUADRATIC-QUOTIENT-DESCENT checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.quadratic_quotient_descent_gate import (
        run_quadratic_quotient_descent_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"quadratic_quotient_descent_check_{i}")
        result = run_quadratic_quotient_descent_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_nonadaptive_source_selection_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-NONADAPTIVE-SOURCE-SELECTION checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.nonadaptive_source_selection_gate import (
        run_nonadaptive_source_selection_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"nonadaptive_source_selection_check_{i}")
        result = run_nonadaptive_source_selection_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_law_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-LAW checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_law_gate import (
        run_support_index_law_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_law_check_{i}")
        result = run_support_index_law_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_injectivity_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-INJECTIVITY checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_injectivity_gate import (
        run_support_index_injectivity_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_injectivity_check_{i}")
        result = run_support_index_injectivity_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_affine_order_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-AFFINE-ORDER checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_affine_order_gate import (
        run_support_index_affine_order_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_affine_order_check_{i}")
        result = run_support_index_affine_order_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_fixed_step_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-FIXED-STEP checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_fixed_step_gate import (
        run_support_index_fixed_step_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_fixed_step_check_{i}")
        result = run_support_index_fixed_step_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_adjacent_gap_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-ADJACENT-GAP checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_adjacent_gap_gate import (
        run_support_index_adjacent_gap_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_adjacent_gap_check_{i}")
        result = run_support_index_adjacent_gap_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_unit_gap_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-UNIT-GAP checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_unit_gap_gate import (
        run_support_index_unit_gap_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_unit_gap_check_{i}")
        result = run_support_index_unit_gap_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_no_hole_unit_gap_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-NO-HOLE-UNIT-GAP checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_no_hole_unit_gap_gate import (
        run_support_index_no_hole_unit_gap_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_no_hole_unit_gap_check_{i}")
        result = run_support_index_no_hole_unit_gap_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_endpoint_tight_no_hole_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-ENDPOINT-TIGHT-NO-HOLE checks."""
    if not checks:
        return []
    from ztare.gates.support_index_endpoint_tight_no_hole_gate import (
        run_support_index_endpoint_tight_no_hole_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_endpoint_tight_no_hole_check_{i}"
        )
        result = run_support_index_endpoint_tight_no_hole_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_base_anchored_strict_lower_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-BASE-ANCHORED-STRICT-LOWER-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.support_index_base_strict_lower_endpoint_gate import (
        run_support_index_base_strict_lower_endpoint_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_base_anchored_strict_lower_bound_check_{i}"
        )
        result = run_support_index_base_strict_lower_endpoint_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_final_endpoint_capacity_upper_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-FINAL-ENDPOINT-CAPACITY-UPPER-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.support_index_tail_capacity_upper_endpoint_gate import (
        run_support_index_tail_capacity_upper_endpoint_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_final_endpoint_capacity_upper_bound_check_{i}"
        )
        result = run_support_index_tail_capacity_upper_endpoint_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_final_slot_upper_bound_tail_capacity_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-FINAL-SLOT-UPPER-BOUND-TAIL-CAPACITY checks."""
    if not checks:
        return []
    from ztare.gates.support_index_final_slot_upper_bound_tail_capacity_gate import (
        run_support_index_final_slot_upper_bound_tail_capacity_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_final_slot_upper_bound_tail_capacity_check_{i}"
        )
        result = run_support_index_final_slot_upper_bound_tail_capacity_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_tail_capacity_failure_witness_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-TAIL-CAPACITY-FAILURE-WITNESS checks."""
    if not checks:
        return []
    from ztare.gates.support_index_tail_capacity_failure_witness_gate import (
        run_support_index_tail_capacity_failure_witness_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_tail_capacity_failure_witness_check_{i}"
        )
        result = run_support_index_tail_capacity_failure_witness_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_skipped_slot_hostile_witness_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-SKIPPED-SLOT-HOSTILE-WITNESS checks."""
    if not checks:
        return []
    from ztare.gates.support_index_skipped_slot_hostile_witness_gate import (
        run_support_index_skipped_slot_hostile_witness_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_skipped_slot_hostile_witness_check_{i}"
        )
        result = run_support_index_skipped_slot_hostile_witness_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_interval_image_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-INTERVAL-IMAGE checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_interval_image_gate import (
        run_support_index_interval_image_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_interval_image_check_{i}")
        result = run_support_index_interval_image_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_interval_preimage_selector_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-INTERVAL-PREIMAGE-SELECTOR checks."""
    if not checks:
        return []
    from ztare.gates.support_index_interval_preimage_selector_gate import (
        run_support_index_interval_preimage_selector_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_interval_preimage_selector_check_{i}")
        result = run_support_index_interval_preimage_selector_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_least_interval_preimage_selector_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-LEAST-INTERVAL-PREIMAGE-SELECTOR checks."""
    if not checks:
        return []
    from ztare.gates.support_index_least_interval_preimage_selector_gate import (
        run_support_index_least_interval_preimage_selector_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_least_interval_preimage_selector_check_{i}")
        result = run_support_index_least_interval_preimage_selector_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_first_hit_interval_preimage_selector_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-FIRST-HIT-INTERVAL-PREIMAGE-SELECTOR checks."""
    if not checks:
        return []
    from ztare.gates.support_index_first_hit_interval_preimage_selector_gate import (
        run_support_index_first_hit_interval_preimage_selector_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_first_hit_interval_preimage_selector_check_{i}")
        result = run_support_index_first_hit_interval_preimage_selector_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_vacuous_first_hit_adapter_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-VACUOUS-FIRST-HIT-ADAPTER checks."""
    if not checks:
        return []
    from ztare.gates.support_index_vacuous_first_hit_adapter_gate import (
        run_support_index_vacuous_first_hit_adapter_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_vacuous_first_hit_adapter_check_{i}")
        result = run_support_index_vacuous_first_hit_adapter_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_finite_support_extraction_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINITE-SUPPORT-EXTRACTION checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.finite_support_extraction_gate import (
        run_finite_support_extraction_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"finite_support_extraction_check_{i}")
        enforce_block = bool(check.get("enforce_block", True))
        result = run_finite_support_extraction_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_finite_image_support_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINITE-IMAGE-SUPPORT checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.finite_image_support_gate import (
        run_finite_image_support_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"finite_image_support_check_{i}")
        enforce_block = bool(check.get("enforce_block", True))
        result = run_finite_image_support_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_no_rebilling_freshness_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-NO-REBILLING-FRESHNESS checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.no_rebilling_freshness_gate import (
        run_no_rebilling_freshness_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"no_rebilling_freshness_check_{i}")
        result = run_no_rebilling_freshness_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_same_carrier_packing_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SAME-CARRIER-PACKING checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.same_carrier_packing_gate import (
        run_same_carrier_packing_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"same_carrier_packing_check_{i}")
        result = run_same_carrier_packing_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_metric_covering_selection_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-METRIC-COVERING-SELECTION checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.metric_covering_selection_gate import (
        run_metric_covering_selection_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"metric_covering_selection_check_{i}")
        result = run_metric_covering_selection_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_pde_analytic_substance_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-PDE-ANALYTIC-SUBSTANCE checks supplied by the caller."""
    if not checks:
        return []
    from ztare.pde.gate_runner import run_pde_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"pde_analytic_substance_check_{i}")
        gate_run = run_pde_gate("G-PDE-ANALYTIC-SUBSTANCE", check)
        results.append({
            "label": label,
            "input": check,
            "gate_run": gate_run,
            "result": gate_run["result"],
        })
    return results


def run_pde_physical_accounting_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-PDE-PHYSICAL-ACCOUNTING checks supplied by the caller."""
    if not checks:
        return []
    from ztare.pde.gate_runner import run_pde_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"pde_physical_accounting_check_{i}")
        gate_run = run_pde_gate("G-PDE-PHYSICAL-ACCOUNTING", check)
        results.append({
            "label": label,
            "input": check,
            "gate_run": gate_run,
            "result": gate_run["result"],
        })
    return results


def run_pde_equality_provenance_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-PDE-EQUALITY-PROVENANCE checks supplied by the caller."""
    if not checks:
        return []
    from ztare.pde.gate_runner import run_pde_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"pde_equality_provenance_check_{i}")
        gate_run = run_pde_gate("G-PDE-EQUALITY-PROVENANCE", check)
        results.append({
            "label": label,
            "input": check,
            "gate_run": gate_run,
            "result": gate_run["result"],
        })
    return results


def run_pde_operator_admissibility_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-PDE-OPERATOR-ADMISSIBILITY checks supplied by the caller."""
    if not checks:
        return []
    from ztare.pde.gate_runner import run_pde_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"pde_operator_admissibility_check_{i}")
        gate_run = run_pde_gate("G-PDE-OPERATOR-ADMISSIBILITY", check)
        results.append({
            "label": label,
            "input": check,
            "gate_run": gate_run,
            "result": gate_run["result"],
        })
    return results


def run_pde_rigorous_numerics_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-PDE-RIGOROUS-NUMERICS checks supplied by the caller."""
    if not checks:
        return []
    from ztare.pde.gate_runner import run_pde_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"pde_rigorous_numerics_check_{i}")
        gate_run = run_pde_gate("G-PDE-RIGOROUS-NUMERICS", check)
        results.append({
            "label": label,
            "input": check,
            "gate_run": gate_run,
            "result": gate_run["result"],
        })
    return results


def run_pde_hostile_witness_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-PDE-HOSTILE-WITNESS checks supplied by the caller."""
    if not checks:
        return []
    from ztare.pde.gate_runner import run_pde_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"pde_hostile_witness_check_{i}")
        gate_run = run_pde_gate("G-PDE-HOSTILE-WITNESS", check)
        results.append({
            "label": label,
            "input": check,
            "gate_run": gate_run,
            "result": gate_run["result"],
        })
    return results


def run_theorem_applicability_checks(
    checks: list[dict[str, Any]],
    theorem_db: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run deterministic theorem/profile applicability matches."""
    if not checks:
        return []
    from ztare.pde.gate_runner import run_pde_gate

    results = []
    for i, check in enumerate(checks):
        theorem_id = str(check.get("theorem") or check.get("theorem_id") or "")
        label = str(check.get("label") or theorem_id or f"theorem_applicability_check_{i}")
        gate_run = run_pde_gate(
            "G-PDE-THEOREM-APPLICABILITY",
            check,
            theorem_db=theorem_db,
        )
        results.append({
            "label": label,
            "input": check,
            "gate_run": gate_run,
            "result": gate_run["result"],
        })
    return results


def run_pi_group_checks(
    pi_checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-PI-GROUP-FORCING checks supplied by the caller."""
    if not pi_checks:
        return []
    from ztare.gates.pi_group_forcing import (
        format_forcing_report,
        run_pi_group_forcing,
    )

    results = []
    for i, check in enumerate(pi_checks):
        label = str(check.get("label") or f"pi_check_{i}")
        result = run_pi_group_forcing(
            quantity_dim=check.get("quantity_dim") or {},
            subset_dims=check.get("subset_dims") or {},
        )
        results.append({
            "label": label,
            "quantity_dim": check.get("quantity_dim") or {},
            "subset_dims": check.get("subset_dims") or {},
            "result": result,
            "report": format_forcing_report(result),
        })
    return results


def run_ambiguous_pi_pinning_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-AMBIGUOUS-PI-PINNING checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.ambiguous_pi_pinning_gate import (
        format_report,
        run_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"ambiguous_pi_pinning_{i}")
        result = run_gate(
            pi_group_result=check.get("pi_group_result"),
            ambiguous=check.get("ambiguous"),
            receipts=check.get("receipts") or {},
            label=label,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
            "report": format_report(result),
        })
    return results


def run_dimensionless_exponent_source_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run analytic-source checks for dimensionless exponents."""
    if not checks:
        return []
    from ztare.gates.dimensionless_exponent_source_gate import (
        format_report,
        run_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"dimensionless_exponent_{i}")
        result = run_gate(
            expression=str(check.get("expression") or ""),
            dimensionless_variables=check.get("dimensionless_variables") or {},
            receipts=check.get("receipts") or {},
            label=label,
        )
        results.append({
            "label": label,
            "expression": check.get("expression") or "",
            "result": result,
            "report": format_report(result),
        })
    return results


def run_persistence_budget_exponent_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run persistence exponent/thickness anti-laundering checks."""
    if not checks:
        return []
    from ztare.gates.persistence_budget_exponent_gate import (
        format_persistence_budget_exponent_report,
        run_persistence_budget_exponent_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"persistence_budget_{i}")
        result = run_persistence_budget_exponent_gate(
            dimension=float(check.get("dimension", 0)),
            persistence_exponent=float(check.get("persistence_exponent", 0)),
            thickness_or_reach_receipt=bool(
                check.get("thickness_or_reach_receipt")
            ),
            uniform_complexity_receipt=bool(
                check.get("uniform_complexity_receipt")
            ),
            same_carrier_receipt=bool(check.get("same_carrier_receipt")),
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
            "report": format_persistence_budget_exponent_report(result),
        })
    return results

def generate_pde_estimate_skeletons(
    *,
    target: str,
    field: str | None,
    gap_type: str,
    context: dict[str, Any],
    inequalities: list[str],
) -> list[dict[str, Any]]:
    """Generate substrate-neutral analytic estimate skeletons."""
    from ztare.research_director.pde_estimate_skeleton import (
        generate_estimate_skeletons,
    )

    return generate_estimate_skeletons(
        target=target,
        field=field,
        gap_type=gap_type,
        context=context,
        inequalities=inequalities,
    )


def run_limit_passage_audit(
    gap_type: str,
    steps: list[dict[str, Any]],
    *,
    finite_prefix_results: bool = False,
) -> dict[str, Any] | None:
    """Run the existing pec_d limit-passage inheritance gate when applicable."""
    if gap_type != "LIMIT_PASSAGE" and not steps and not finite_prefix_results:
        return None
    from ztare.gates.limit_passage_inheritance_lemma_gate import (
        run_limit_passage_gate,
    )
    return run_limit_passage_gate({
        "finite_prefix_results": finite_prefix_results or gap_type == "LIMIT_PASSAGE",
        "limit_passage_steps": steps,
    })


def run_linear_observable_coercivity_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-LINEAR-OBS-COERCIVITY checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.linear_observable_coercivity_gate import (
        format_report,
        run_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"linear_observable_check_{i}")
        result = run_gate(
            target_dimension=check.get("target_dimension", 0),
            observable_rank=check.get("observable_rank", 0),
            full_reconstruction_receipt=bool(
                check.get("full_reconstruction_receipt", False)
            ),
            coercivity_receipt=bool(check.get("coercivity_receipt", False)),
            kernel_quotient_dimension=check.get("kernel_quotient_dimension"),
            kernel_quotient_receipt=bool(
                check.get("kernel_quotient_receipt", False)
            ),
            kernel_witness_present=bool(check.get("kernel_witness_present", False)),
            dimensionally_compatible=check.get("dimensionally_compatible"),
            labels=check.get("labels") or {},
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
            "report": format_report(result),
        })
    return results


def run_residual_normal_form(
    profile_path: Path | None,
    target: str,
    field: str | None,
    candidates: list[str],
    context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Classify the proposed estimate against a substrate normal-form profile."""
    if profile_path is None:
        return None
    if not profile_path.exists():
        return {
            "classification": "UNAVAILABLE",
            "reason": f"profile not found: {profile_path}",
        }
    from ztare.research_director.residual_normal_form import (
        compile_residual_normal_form,
        load_profile,
    )
    profile = load_profile(profile_path)
    context_terms: list[str] = []
    if context:
        doc = str(context.get("doc", ""))
        if doc:
            context_terms.append(doc)
        for item in context.get("fields", []):
            name = str(item.get("name", ""))
            ftype = str(item.get("type", ""))
            context_terms.append(f"{name}: {ftype}")
    text = "\n".join([target, field or "", *candidates, *context_terms])
    return compile_residual_normal_form(text, profile)


def run_single_spend_audit(fields: list[str]) -> dict[str, Any] | None:
    """Run the RD single-spend carrier audit if fields were supplied."""
    if not fields:
        return None
    from ztare.research_director.single_spend_carrier_audit import (
        run_single_spend_carrier_audit,
    )
    return run_single_spend_carrier_audit(
        fields,
        profile=PDE_SINGLE_SPEND_PROFILE,
    )


def run_receipt_strength_audit_from_fields(fields: list[str]) -> dict[str, Any] | None:
    """Run the general receipt-strength audit over extracted carrier fields."""
    if not fields:
        return None
    from ztare.research_director.receipt_strength_audit import (
        run_receipt_strength_audit,
    )
    return run_receipt_strength_audit(fields)


def run_owner_preimage_prefix_audit(
    pde_ops: list[dict[str, Any]],
    owner_preimage_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the owner-preimage prefix gate when selected or receipts are supplied."""
    if not owner_preimage_receipts and not any(
        op.get("op_id") == "pec_k" for op in pde_ops
    ):
        return None
    from ztare.gates.owner_preimage_prefix_gate import (
        run_owner_preimage_prefix_gate,
    )

    return run_owner_preimage_prefix_gate(
        {"owner_preimage_receipts": owner_preimage_receipts},
        expect_receipt=True,
    )


def run_scaled_transfer_numeric_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    scaled_transfer_numeric_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the scaled-transfer numeric receipt gate for route-tail edges."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(scaled_transfer_numeric_receipts)
        or "C7RouteActiveTailNonnegativeReceipt" in text
        or "C7SelectedEventNodeRadiusNonnegativeReceipt" in text
        or "eventNodeRadius_nonnegative" in text
        or "selectedNodeRadius_nonnegative" in text
    )
    if not selected:
        return None

    from ztare.gates.scaled_transfer_numeric_receipt_gate import (
        run_scaled_transfer_numeric_receipt_gate,
    )

    return run_scaled_transfer_numeric_receipt_gate(
        {"scaled_transfer_numeric_receipts": scaled_transfer_numeric_receipts},
        profile=NS_SCALED_TRANSFER_NUMERIC_PROFILE,
        expect_receipt=True,
    )


def run_owner_geometry_core_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    owner_geometry_core_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the owner-geometry-core gate for reduced TICK668 edges."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(owner_geometry_core_receipts)
        or "C7OwnerPreimageGeometryCoreReceipt" in text
        or "C7OwnerGeometryResidualAfterScaledTransfer" in text
        or "ofOwnerPreimageGeometryCore" in text
    )
    if not selected:
        return None

    from ztare.gates.residual_core_receipt_gate import (
        run_residual_core_receipt_gate,
    )

    return run_residual_core_receipt_gate(
        {"owner_geometry_core_receipts": owner_geometry_core_receipts},
        profile=OWNER_GEOMETRY_CORE_PROFILE,
        expect_receipt=True,
    )


def run_fresh_annular_anti_laundering_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    fresh_annular_anti_laundering_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the anti-laundering gate for the fresh-annular bridge edge."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(fresh_annular_anti_laundering_receipts)
        or "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource" in text
        or "ofOwnerLineageAndAntiLaundering" in text
        or "ofCarrierRadiusPositiveIdentityAndAntiLaundering" in text
    )
    if not selected:
        return None

    from ztare.gates.residual_core_receipt_gate import (
        run_residual_core_receipt_gate,
    )

    return run_residual_core_receipt_gate(
        {
            "fresh_annular_anti_laundering_receipts":
                fresh_annular_anti_laundering_receipts
        },
        profile=FRESH_ANNULAR_ANTI_LAUNDERING_PROFILE,
        expect_receipt=True,
    )

def run_fresh_annular_non_disguise_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    fresh_annular_non_disguise_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the non-disguise morphology gate for the fresh-annular split edge."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(fresh_annular_non_disguise_receipts)
        or "C7FreshAnnularNonDisguiseReceiptFromSeparatedSource" in text
        or "ofNonDisguiseAndSourceNondeclaration" in text
    )
    if not selected:
        return None

    from ztare.gates.residual_core_receipt_gate import (
        run_residual_core_receipt_gate,
    )

    return run_residual_core_receipt_gate(
        {
            "fresh_annular_non_disguise_receipts":
                fresh_annular_non_disguise_receipts
        },
        profile=FRESH_ANNULAR_NON_DISGUISE_PROFILE,
        expect_receipt=True,
    )


def run_fresh_annular_innovation_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    fresh_annular_innovation_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the innovation gate for the fresh-annular anti-laundering route."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(fresh_annular_innovation_receipts)
        or "FreshAnnularInnovationAntiLaunderingReceipt" in text
        or "innovation" in text.lower()
    )
    if not selected:
        return None

    from ztare.gates.residual_core_receipt_gate import (
        run_residual_core_receipt_gate,
    )

    return run_residual_core_receipt_gate(
        {
            "fresh_annular_innovation_receipts":
                fresh_annular_innovation_receipts
        },
        profile=FRESH_ANNULAR_INNOVATION_PROFILE,
        expect_receipt=True,
    )


def run_section_fixed_unsigned_variation_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    section_fixed_unsigned_variation_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the section-fixed unsigned variation gate for the crown route."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(section_fixed_unsigned_variation_receipts)
        or "DuhamelSectionFixedUnsignedCrownMeasureReceipt" in text
        or "SectionFixedUnsignedLocalizedCrownMass" in text
        or "UnsignedLocalizedCrownSourceFromDuhamelSection" in text
        or "unsigned variation" in text.lower()
        or "unsigned-variation" in text.lower()
    )
    if not selected:
        return None

    from ztare.gates.residual_core_receipt_gate import (
        run_residual_core_receipt_gate,
    )

    return run_residual_core_receipt_gate(
        {
            "section_fixed_unsigned_variation_receipts":
                section_fixed_unsigned_variation_receipts
        },
        profile=SECTION_FIXED_UNSIGNED_VARIATION_PROFILE,
        expect_receipt=True,
    )


def single_spend_fields_from_context(context: dict[str, Any]) -> list[str]:
    """Convert source-truth context fields into audit inputs."""
    fields: list[str] = []
    for item in context.get("fields", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        ftype = str(item.get("type") or "").strip()
        if not name:
            continue
        fields.append(f"{name}:{ftype}" if ftype else name)
    return fields


def allowed_endpoints_from_context(context: dict[str, Any]) -> set[str]:
    allowed = {str(context.get("target") or "")}
    field = context.get("field")
    if field:
        allowed.add(str(field))
    for item in context.get("fields", []):
        if isinstance(item, dict):
            allowed.add(str(item.get("name") or ""))
            ftype = str(item.get("type") or "")
            for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", ftype):
                if token and token[0].isupper():
                    allowed.add(token)
    for item in context.get("constructors", []):
        allowed.add(str(item.get("type_head") or ""))
    return {x for x in allowed if x}


def check_inequalities(
    inequalities: list[str],
    context: dict[str, Any],
    dims_path: Path | None,
    extra_allowed: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not inequalities:
        return []
    from ztare.gates.pde_inequality_dimensional_gate import run_gate
    dimensional_features: dict[str, str] = {}
    if dims_path:
        dims_arg = str(dims_path)
        if dims_arg.lstrip().startswith("{"):
            dimensional_features = json.loads(dims_arg)
        else:
            dimensional_features = json.loads(dims_path.read_text(encoding="utf-8"))
    allowed = allowed_endpoints_from_context(context)
    allowed.update(str(name) for name in dimensional_features.keys())
    if extra_allowed:
        allowed.update(extra_allowed)
    results = []
    for ineq in inequalities:
        result = run_gate(
            candidate_inequality=ineq,
            dimensional_features=dimensional_features,
            allowed_endpoints=allowed,
        )
        result["candidate_inequality"] = ineq
        results.append(result)
    return results


def emit_curriculum_variants(
    target: str,
    transforms: list[str],
    out_dir: Path,
) -> list[dict[str, Any]]:
    if not transforms:
        return []
    from curriculum_generator import apply_transformation, load_obligation_source, load_workmap_target
    target_obj = load_workmap_target(target)
    if not target_obj:
        return [{"error": "target not found in workmap", "target": target}]
    source = load_obligation_source(target_obj)
    if not source:
        return [{"error": "could not load obligation source", "target": target}]
    variant_dir = out_dir / "curriculum_variants"
    variant_dir.mkdir(parents=True, exist_ok=True)
    emitted = []
    for transform in transforms:
        result = apply_transformation(source, target, transform)
        if "error" in result:
            emitted.append(result)
            continue
        base = variant_dir / f"{target}_{transform.lower()}"
        json_path = base.with_suffix(".json")
        lean_path = base.with_suffix(".lean")
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "original_target": target,
            "original_file": target_obj.get("file", ""),
            **result,
        }
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        import_line = (
            f"import ZtareProofs.{target_obj.get('file')}\n\n"
            if target_obj.get("file") else ""
        )
        lean_path.write_text(
            f"-- Curriculum variant: {target} -> {result['new_target_name']}\n"
            f"-- Transform: {transform} ({result['transform_description']})\n"
            f"-- HONEST CAVEAT: template-based; may be ill-typed.\n\n"
            f"{import_line}"
            "namespace ZtareProofs.NS\n\n"
            f"{result['transformed_source']}\n\n"
            "end ZtareProofs.NS\n",
            encoding="utf-8",
        )
        emitted.append({
            "transform": transform,
            "new_target_name": result["new_target_name"],
            "json_path": str(json_path.relative_to(REPO)),
            "lean_path": str(lean_path.relative_to(REPO)),
            "caveat": result["honest_caveat"],
        })
    return emitted


def render_markdown(pack: dict[str, Any]) -> str:
    ctx = pack["target_context"]
    lines = [
        "# PDE Estimate Workbench Pack",
        "",
        f"- Target: `{pack['target']}`",
        f"- Field: `{pack.get('field') or ''}`",
        f"- Scope: RD caller over existing ZTARE primitives; not a replacement workbench",
        f"- Gap type: `{pack['gap_classification'].get('gap_type')}` "
        f"({pack['gap_classification'].get('confidence', '?')})",
        "",
        "## Target Context",
        "",
        f"- Found in workmap: `{ctx.get('found')}`",
        f"- File: `{ctx.get('target_file')}`",
        f"- Downstream users: `{ctx.get('n_downstream_users')}`",
        f"- Priority: `{ctx.get('priority')}`",
        "",
        "## Mathlib Shelf",
        "",
    ]
    if pack["mathlib_lemmas"]:
        for lemma in pack["mathlib_lemmas"][:10]:
            lines.append(f"- `{lemma['name']}` ({lemma['file']})")
    else:
        lines.append("- (none found; this is a thin-zone warning)")
    apn = pack.get("apn_semantic_neighbors") or {}
    lines.extend(["", "## APN Semantic Bridges", ""])
    if apn.get("available"):
        lines.append(
            f"- Corpus/filtered: `{apn.get('corpus_size')}` / "
            f"`{apn.get('filtered_size')}`; threshold=`{apn.get('threshold')}`"
        )
        lines.append(f"- Bridge edges: `{len(apn.get('bridge_edges') or [])}`")
        hits = apn.get("hits") or []
        if hits:
            try:
                from ztare.research_director.apn_semantic import (
                    APNSemanticHit,
                    render_text as render_apn_text,
                )
                rendered_hits = [
                    APNSemanticHit(
                        id=str(hit.get("id") or ""),
                        name=str(hit.get("name") or "?"),
                        kind=str(hit.get("kind") or ""),
                        domain=str(hit.get("domain") or ""),
                        file=str(hit.get("file") or ""),
                        variant_tag=hit.get("variant_tag"),
                        cosine=float(hit.get("cosine") or 0.0),
                        snippet=str(hit.get("snippet") or ""),
                    )
                    for hit in hits[:5]
                ]
                lines.extend(
                    render_apn_text(
                        rendered_hits, header="APN semantic neighbours"
                    ).splitlines()
                )
            except Exception:
                for hit in hits[:5]:
                    lines.append(
                        f"- `{hit.get('name')}` ({hit.get('domain')}/{hit.get('file')}, "
                        f"cos={hit.get('cosine')}): {hit.get('snippet')}"
                    )
        elif apn.get("skip_reason"):
            lines.append(f"- Skip: {apn.get('skip_reason')}")
        else:
            lines.append("- (none above threshold)")
    elif apn:
        lines.append(f"- unavailable: {apn.get('skip_reason')}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Auxiliary Families", ""])
    if pack["auxiliary_families"]:
        for item in pack["auxiliary_families"]:
            lines.append(f"- `{item['family']}`: {item['mathematical_form']}")
    else:
        lines.append("- (none selected)")
    lines.extend(["", "## ZTARE Primitive Suggestions", ""])
    if pack.get("pde_craft_ops"):
        for item in pack["pde_craft_ops"]:
            gate = item.get("gate_mechanization") or "no shipped gate"
            lines.append(
                f"- `{item['op_id']}` {item['name']}: "
                f"{item['rationale']} ({gate})"
            )
    else:
        lines.append("- (none selected)")
    if pack.get("estimate_skeletons"):
        lines.extend(["", "## Estimate Skeletons", ""])
        for skeleton in pack["estimate_skeletons"]:
            lines.append(
                f"- `{skeleton.get('id')}` {skeleton.get('route')}: "
                f"{skeleton.get('target_inequality')}"
            )
            receipts = skeleton.get("required_receipts") or []
            if receipts:
                lines.append(f"  - required receipts: `{', '.join(receipts)}`")
            hostile = skeleton.get("hostile_packet") or {}
            if hostile:
                lines.append(
                    f"  - hostile packet: `{hostile.get('name')}` kills "
                    f"{hostile.get('kills')}"
                )
    else:
        lines.extend(["", "## Estimate Skeletons", "", "- (none selected)"])
    if pack.get("pde_execution_contract"):
        contract = pack["pde_execution_contract"]
        lines.extend(["", "## PDE Execution Contract", ""])
        lines.append(f"- Mode: `{contract.get('mode')}`")
        lines.append(
            f"- Minimum work units: `{contract.get('minimum_work_units')}`"
        )
        rule = contract.get("no_early_stop_rule", {})
        required = rule.get("required_before_terminal_gap", {})
        lines.append(
            "- Terminal gap verdicts require "
            f"`{required.get('estimate_derivation_min')}` estimate derivations, "
            f"`{required.get('falsifier_packet_min')}` falsifier packet, and "
            f"one of `{', '.join(required.get('requires_one_of', []))}`."
        )
        constructive = rule.get("constructive_turn_rule", {})
        if constructive:
            lines.append(
                "- Constructive turn: when "
                f"{constructive.get('trigger')}, require "
                f"`{', '.join(constructive.get('required_before_more_obstruction_only_work', []))}`."
            )
        hints = (
            contract.get("gp219_execution_templates", {})
            .get("pde_execution_hints", {})
        )
        if hints:
            lines.append("- Selected GP-219 execution hints:")
            for op_id, hint in hints.items():
                lines.append(
                    f"  - `{op_id}` {hint.get('name')}: "
                    f"{', '.join(hint.get('fields', []))}"
                )
        packets = contract.get("hostile_packet_suite", {}).get("packets", [])
        if packets:
            lines.append("- Hostile packets to test:")
            for packet in packets[:10]:
                lines.append(
                    f"  - `{packet.get('id')}`: {packet.get('packet')}"
                )
        theorem_db = contract.get("theorem_applicability_db", {})
        theorem_ids = sorted((theorem_db.get("theorems") or {}).keys())
        if theorem_ids:
            lines.append(
                "- Theorem applicability profile: "
                f"`{theorem_db.get('profile')}`; "
                f"templates `{', '.join(theorem_ids)}`"
            )
        lines.append("- Currency ledger:")
        for key in (
            contract.get("currency_ledger_template", {})
            .get("exchange_rate_obligations", {})
        ):
            lines.append(f"  - `{key}`")
    lines.extend(["", "## PDE Engine Context", ""])
    engine_context = pack.get("pde_engine_context")
    if isinstance(engine_context, dict):
        lines.append(f"- Schema: `{engine_context.get('schema')}`")
        boundaries = engine_context.get("service_boundaries") or {}
        if isinstance(boundaries, dict):
            for owner, items in boundaries.items():
                if isinstance(items, list):
                    joined = ", ".join(f"`{item}`" for item in items)
                    lines.append(f"- `{owner}` owns: {joined}")
        lines.append(
            "- Kernel surfaces: "
            f"`ops={len(engine_context.get('op_registry') or [])}`, "
            f"`gates={len(engine_context.get('gate_registry') or [])}`, "
            f"`receipts={len(engine_context.get('receipt_registry') or [])}`, "
            f"`estimate_skeletons={len(engine_context.get('estimate_skeletons') or [])}`"
        )
    else:
        lines.append("- (not available)")
    lines.extend(["", "## PDE Receipt Registry", ""])
    receipts = [
        entry for entry in (pack.get("pde_receipt_registry") or [])
        if isinstance(entry, dict)
    ]
    if receipts:
        lines.append(
            "- Receipt schemas exposed for work units and gate payloads "
            f"({len(receipts)} total):"
        )
        for entry in receipts[:20]:
            lines.append(
                f"  - `{entry.get('receipt_id')}` kind=`{entry.get('kind')}`"
            )
    else:
        lines.append("- (registry unavailable)")
    lines.extend(["", "## PDE Gate Registry", ""])
    registry = [
        entry for entry in (pack.get("pde_gate_registry") or [])
        if isinstance(entry, dict)
    ]
    if registry:
        lines.append(
            "- Registry entries exposed for leaf-agent work orders "
            f"({len(registry)} total):"
        )
        for entry in registry[:20]:
            ops = ", ".join(str(op) for op in entry.get("requires_ops", []))
            tags = ", ".join(str(tag) for tag in entry.get("tags", []))
            lines.append(
                f"  - `{entry.get('gate_id')}` via `{entry.get('workbench_flag')}` "
                f"ops=[{ops}] tags=[{tags}]"
            )
    else:
        lines.append("- (registry unavailable)")
    lines.extend(["", "## PDE Formal Feedback", ""])
    formal_feedback = pack.get("pde_formal_feedback")
    if isinstance(formal_feedback, dict):
        lines.append(
            f"- Status: `{formal_feedback.get('formal_surface_status')}`"
        )
        lines.append(
            f"- Next leaf: {formal_feedback.get('recommended_next_leaf')}"
        )
        lines.append(
            f"- Source counts: `{formal_feedback.get('source_counts', {})}`"
        )
        skips = formal_feedback.get("skip_reasons") or []
        if skips:
            lines.append("- Retrieval degradation notes:")
            for item in skips[:8]:
                lines.append(f"  - {item}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## PDE Formal Surface Map", ""])
    formal_surface_map = pack.get("pde_formal_surface_map")
    if isinstance(formal_surface_map, dict):
        from ztare.pde.formal_surface_status import (
            render_pde_formal_surface_map,
        )
        lines.append(render_pde_formal_surface_map(formal_surface_map))
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## PDE Leaf Work Order", ""])
    leaf_work_order = pack.get("pde_leaf_work_order")
    if isinstance(leaf_work_order, dict):
        from ztare.pde.work_order import (
            render_pde_leaf_work_order,
        )
        lines.append(render_pde_leaf_work_order(leaf_work_order))
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## PDE Applicability Cards", ""])
    applicability_cards = pack.get("pde_applicability_cards")
    if isinstance(applicability_cards, list):
        from ztare.pde.applicability_cards import render_applicability_cards
        lines.append(render_applicability_cards(applicability_cards))
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## PDE Knowledge Context", ""])
    knowledge_context = pack.get("pde_knowledge_context")
    if isinstance(knowledge_context, dict):
        lines.append(f"- Schema: `{knowledge_context.get('schema')}`")
        lines.append(
            "- Theorem profile cards: "
            f"`{len(knowledge_context.get('theorem_profile_cards') or [])}`"
        )
        memory = knowledge_context.get("leanmill_memory") or {}
        if isinstance(memory, dict):
            proof_cache = memory.get("proof_cache") or {}
            no_good = memory.get("no_good_store") or {}
            if isinstance(proof_cache, dict):
                lines.append(
                    "- LeanMill proof-cache hit: "
                    f"`{bool(proof_cache.get('hit'))}`"
                )
            if isinstance(no_good, dict):
                lines.append(
                    "- LeanMill no-good matches: "
                    f"`{int(no_good.get('n_matches') or 0)}`"
                )
        leaves = knowledge_context.get("recommended_leaf_sequence") or []
        if leaves:
            lines.append("- Recommended leaves:")
            for leaf in leaves[:8]:
                lines.append(f"  - {leaf}")
        boundary = knowledge_context.get("credit_boundary")
        if boundary:
            lines.append(f"- Credit boundary: `{boundary}`")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Residual Normal Form", ""])
    normal_form = pack.get("residual_normal_form")
    if normal_form:
        lines.append(f"- Classification: `{normal_form.get('classification')}`")
        if normal_form.get("reason"):
            lines.append(f"- Reason: {normal_form['reason']}")
        best = normal_form.get("best_match") or {}
        if best:
            lines.append(
                f"- Best match: `{best.get('canonical_name')}` "
                f"(score `{best.get('score')}`)"
            )
        if normal_form.get("required_next_move"):
            lines.append(
                f"- Required next move: {normal_form['required_next_move']}"
            )
        if normal_form.get("packet_hits"):
            lines.append("- Packet hits:")
            for hit in normal_form["packet_hits"]:
                lines.append(
                    f"  - `{hit['packet_id']}` {hit['name']}: "
                    f"{hit.get('required_escape')}"
                )
        if normal_form.get("currency_mismatches"):
            lines.append("- Currency mismatches:")
            for hit in normal_form["currency_mismatches"]:
                lines.append(
                    f"  - `{hit['rule_id']}` {hit['verdict']}: "
                    f"{hit.get('missing_exchange_rate')}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Limit-Passage Gate", ""])
    if pack.get("limit_passage_gate"):
        gate = pack["limit_passage_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_steps']}/{gate['n_steps_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', '')}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Moment Ratio Surplus", ""])
    if pack.get("moment_ratio_surplus_checks"):
        for item in pack["moment_ratio_surplus_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"ratio=`{res.get('ratio_lower_bound')}` "
                f"margin=`{res.get('overfill_margin')}`; {res.get('reason')}"
            )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Bounded Ratio Support", ""])
    if pack.get("bounded_ratio_support_checks"):
        for item in pack["bounded_ratio_support_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"support=`{res.get('support_lower_bound')}` "
                f"margin=`{res.get('overfill_margin')}`; {res.get('reason')}"
            )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Finite Prefix Selection", ""])
    if pack.get("finite_prefix_selection_checks"):
        for item in pack["finite_prefix_selection_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"boundary_sum=`{res.get('boundary_prefix_sum')}` "
                f"interface_sum=`{res.get('interface_prefix_sum')}` "
                f"witnesses=`{res.get('witness_indices')}` "
                f"floor_witnesses=`{res.get('payment_floor_witness_indices')}`; "
                f"{res.get('reason')}"
            )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Event Family Binding", ""])
    if pack.get("event_family_binding_checks"):
        for item in pack["event_family_binding_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Analogical Transfer Receipt", ""])
    if pack.get("analogical_transfer_receipt_checks"):
        for item in pack["analogical_transfer_receipt_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Prefix Count Bridge", ""])
    if pack.get("prefix_count_bridge_checks"):
        for item in pack["prefix_count_bridge_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            if res.get("numeric_check") is not None:
                lines.append(f"- numeric_check: `{res.get('numeric_check')}`")
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Source Prefix Budget", ""])
    if pack.get("source_prefix_budget_checks"):
        for item in pack["source_prefix_budget_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            if res.get("numeric_check") is not None:
                lines.append(f"- numeric_check: `{res.get('numeric_check')}`")
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Final-Slot Indexed Source Budget", ""])
    if pack.get("final_slot_indexed_source_budget_checks"):
        for item in pack["final_slot_indexed_source_budget_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            if res.get("numeric_check") is not None:
                lines.append(f"- numeric_check: `{res.get('numeric_check')}`")
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Target Indexed Event Assignment", ""])
    if pack.get("target_indexed_event_assignment_checks"):
        for item in pack["target_indexed_event_assignment_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` mode=`{res.get('mode')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            if res.get("numeric_check") is not None:
                lines.append(f"- numeric_check: `{res.get('numeric_check')}`")
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Incidence-Derived Finite Injection", ""])
    if pack.get("incidence_derived_finite_injection_checks"):
        for item in pack["incidence_derived_finite_injection_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Bounded Incident EventData/Horizon", ""])
    if pack.get("bounded_incident_existence_eventdata_horizon_checks"):
        for item in pack["bounded_incident_existence_eventdata_horizon_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Target Event Candidate Cover Selection", ""])
    if pack.get("target_event_candidate_cover_selection_checks"):
        for item in pack["target_event_candidate_cover_selection_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Target Cover EventData/Incidence", ""])
    if pack.get("target_cover_eventdata_incidence_checks"):
        for item in pack["target_cover_eventdata_incidence_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Cover Event Selector Final-Slot Assignment", ""])
    if pack.get("cover_event_selector_finalslot_assignment_checks"):
        for item in pack["cover_event_selector_finalslot_assignment_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Target Slot Bounded-Incidence Least-Hit", ""])
    if pack.get("target_slot_bounded_incidence_least_hit_checks"):
        for item in pack["target_slot_bounded_incidence_least_hit_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Bounded Incident Existence Same-Tree EventData Index", ""])
    if pack.get("bounded_incident_existence_sametree_eventdata_index_checks"):
        for item in pack["bounded_incident_existence_sametree_eventdata_index_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Target EventData Index Prefix Cover", ""])
    if pack.get("target_eventdata_index_prefix_cover_checks"):
        for item in pack["target_eventdata_index_prefix_cover_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Finite Scale/Cofinality Prefix Cover", ""])
    if pack.get("finite_scale_cofinality_prefix_cover_checks"):
        for item in pack["finite_scale_cofinality_prefix_cover_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Event-to-BadNode Selected Index", ""])
    if pack.get("event_to_badnode_selected_index_checks"):
        for item in pack["event_to_badnode_selected_index_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Event-Prefix Coverage Selected Index", ""])
    if pack.get("event_prefix_coverage_selected_index_checks"):
        for item in pack["event_prefix_coverage_selected_index_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Coverage Choice Finite Selector", ""])
    if pack.get("coverage_choice_finite_selector_checks"):
        for item in pack["coverage_choice_finite_selector_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Typed Appearance Coverage Choice", ""])
    if pack.get("typed_appearance_coverage_choice_checks"):
        for item in pack["typed_appearance_coverage_choice_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Typed Coverage Packet Appearance", ""])
    if pack.get("typed_coverage_packet_appearance_checks"):
        for item in pack["typed_coverage_packet_appearance_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Event-Prefix Enumeration Packet", ""])
    if pack.get("event_prefix_enumeration_packet_checks"):
        for item in pack["event_prefix_enumeration_packet_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Bounded Natural Event Enumeration", ""])
    if pack.get("bounded_natural_event_enumeration_checks"):
        for item in pack["bounded_natural_event_enumeration_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Unbounded Event Witness Prefix Bound", ""])
    if pack.get("unbounded_event_witness_prefix_bound_checks"):
        for item in pack["unbounded_event_witness_prefix_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Cofinal Incidence Witness Bound", ""])
    if pack.get("cofinal_incidence_witness_bound_checks"):
        for item in pack["cofinal_incidence_witness_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Explicit Cofinal Event Witness Bound", ""])
    if pack.get("explicit_cofinal_event_witness_bound_checks"):
        for item in pack["explicit_cofinal_event_witness_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Cofinal Event Selector Final Prefix Bound", ""])
    if pack.get("cofinal_event_selector_final_prefix_bound_checks"):
        for item in pack["cofinal_event_selector_final_prefix_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Finite Cofinal Event Selector", ""])
    if pack.get("finite_cofinal_event_selector_checks"):
        for item in pack["finite_cofinal_event_selector_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Positive Variation Bridge", ""])
    if pack.get("positive_variation_bridge_checks"):
        for item in pack["positive_variation_bridge_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Positive Variation Quotient Wash", ""])
    if pack.get("positive_variation_quotient_wash_checks"):
        for item in pack["positive_variation_quotient_wash_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}; "
                f"wash={res.get('wash_confusers')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Quotient Minimal Carrier Payment", ""])
    if pack.get("quotient_minimal_carrier_payment_checks"):
        for item in pack["quotient_minimal_carrier_payment_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}; "
                f"underpay={res.get('underpayment_confusers')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Quadratic Quotient Descent", ""])
    if pack.get("quadratic_quotient_descent_checks"):
        for item in pack["quadratic_quotient_descent_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}; "
                f"confusers={res.get('quadratic_confusers')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Nonadaptive Source Selection", ""])
    if pack.get("nonadaptive_source_selection_checks"):
        for item in pack["nonadaptive_source_selection_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Law", ""])
    if pack.get("support_index_law_checks"):
        for item in pack["support_index_law_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Injectivity", ""])
    if pack.get("support_index_injectivity_checks"):
        for item in pack["support_index_injectivity_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Affine Order", ""])
    if pack.get("support_index_affine_order_checks"):
        for item in pack["support_index_affine_order_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index First-Hit Interval Preimage Selector", ""])
    if pack.get("support_index_first_hit_interval_preimage_selector_checks"):
        for item in pack["support_index_first_hit_interval_preimage_selector_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Vacuous First-Hit Adapter", ""])
    if pack.get("support_index_vacuous_first_hit_adapter_checks"):
        for item in pack["support_index_vacuous_first_hit_adapter_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Least Interval Preimage Selector", ""])
    if pack.get("support_index_least_interval_preimage_selector_checks"):
        for item in pack["support_index_least_interval_preimage_selector_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Interval Preimage Selector", ""])
    if pack.get("support_index_interval_preimage_selector_checks"):
        for item in pack["support_index_interval_preimage_selector_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Interval Image", ""])
    if pack.get("support_index_interval_image_checks"):
        for item in pack["support_index_interval_image_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Base-Anchored Strict Lower Bound", ""])
    if pack.get("support_index_base_anchored_strict_lower_bound_checks"):
        for item in pack["support_index_base_anchored_strict_lower_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Final-Slot Upper Bound Tail Capacity", ""])
    if pack.get("support_index_final_slot_upper_bound_tail_capacity_checks"):
        for item in pack["support_index_final_slot_upper_bound_tail_capacity_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Final-Endpoint Capacity Upper Bound", ""])
    if pack.get("support_index_final_endpoint_capacity_upper_bound_checks"):
        for item in pack["support_index_final_endpoint_capacity_upper_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Tail-Capacity Failure Witness", ""])
    if pack.get("support_index_tail_capacity_failure_witness_checks"):
        for item in pack["support_index_tail_capacity_failure_witness_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            computed = res.get("computed") or {}
            if computed:
                lines.append(
                    f"- computed: tail_capacity_failure="
                    f"`{computed.get('tail_capacity_failure_holds')}` "
                    f"upper_endpoint_failure="
                    f"`{computed.get('upper_endpoint_failure_holds')}`"
                )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('forbidden_shortcuts', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Endpoint-Tight No-Hole", ""])
    if pack.get("support_index_endpoint_tight_no_hole_checks"):
        for item in pack["support_index_endpoint_tight_no_hole_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Skipped-Slot Hostile Witness", ""])
    if pack.get("support_index_skipped_slot_hostile_witness_checks"):
        for item in pack["support_index_skipped_slot_hostile_witness_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('forbidden_shortcuts', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index No-Hole Unit Gap", ""])
    if pack.get("support_index_no_hole_unit_gap_checks"):
        for item in pack["support_index_no_hole_unit_gap_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Unit Gap", ""])
    if pack.get("support_index_unit_gap_checks"):
        for item in pack["support_index_unit_gap_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Adjacent Gap", ""])
    if pack.get("support_index_adjacent_gap_checks"):
        for item in pack["support_index_adjacent_gap_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Fixed Step", ""])
    if pack.get("support_index_fixed_step_checks"):
        for item in pack["support_index_fixed_step_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Finite Support Extraction", ""])
    if pack.get("finite_support_extraction_checks"):
        for item in pack["finite_support_extraction_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Finite Image Support", ""])
    if pack.get("finite_image_support_checks"):
        for item in pack["finite_image_support_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## No-Rebilling Freshness", ""])
    if pack.get("no_rebilling_freshness_checks"):
        for item in pack["no_rebilling_freshness_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Same-Carrier Packing", ""])
    if pack.get("same_carrier_packing_checks"):
        for item in pack["same_carrier_packing_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Metric Covering Selection", ""])
    if pack.get("metric_covering_selection_checks"):
        for item in pack["metric_covering_selection_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## PDE Analytic Substance", ""])
    if pack.get("pde_analytic_substance_checks"):
        for item in pack["pde_analytic_substance_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"classification=`{res.get('classification')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}; "
                f"markers={res.get('analytic_markers')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## PDE Physical Accounting", ""])
    if pack.get("pde_physical_accounting_checks"):
        for item in pack["pde_physical_accounting_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"classification=`{res.get('classification')}` "
                f"missing={res.get('missing_fields')}; "
                f"rejected={res.get('rejected_substitutes')}; "
                f"dimension_mismatch={res.get('dimension_mismatch')}; "
                f"markers={res.get('physical_markers')}"
            )
            candidate_audit = res.get("candidate_dimension_audit")
            if isinstance(candidate_audit, dict):
                lines.append(
                    f"  - candidate_dimension_audit: ran=`{candidate_audit.get('ran')}` "
                    f"passed=`{candidate_audit.get('passed')}`"
                )
            balance_audit = res.get("balance_law_audit")
            if isinstance(balance_audit, dict):
                lines.append(
                    f"  - balance_law_audit: ran=`{balance_audit.get('ran')}` "
                    f"passed=`{balance_audit.get('passed')}` "
                    f"roles={balance_audit.get('role_hits')}"
                )
            pi_audit = res.get("pi_group_audit")
            if isinstance(pi_audit, dict):
                lines.append(
                    f"  - pi_group_audit: ran=`{pi_audit.get('ran')}` "
                    f"passed=`{pi_audit.get('passed')}`"
                )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('rejected_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## PDE Equality Provenance", ""])
    if pack.get("pde_equality_provenance_checks"):
        for item in pack["pde_equality_provenance_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"classification=`{res.get('classification')}` "
                f"provenance_kind=`{res.get('provenance_kind')}` "
                f"missing={res.get('missing_fields')}; "
                f"rejected={res.get('rejected_substitutes')}"
            )
            lines.append(
                "  - constructor_body_assignments_present="
                f"`{res.get('constructor_body_assignments_present')}` "
                f"source_binding_present=`{res.get('source_binding_present')}`"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('rejected_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## PDE Operator Admissibility", ""])
    if pack.get("pde_operator_admissibility_checks"):
        for item in pack["pde_operator_admissibility_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"classification=`{res.get('classification')}` "
                f"missing={res.get('missing_fields')}; "
                f"rejected={res.get('rejected_substitutes')}; "
                f"markers={res.get('operator_markers')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('rejected_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## PDE Hostile Witness", ""])
    if pack.get("pde_hostile_witness_checks"):
        for item in pack["pde_hostile_witness_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"classification=`{res.get('classification')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('rejected_substitutes')}"
            )
            lines.append(f"  - boundary: {res.get('credit_boundary')}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## PDE Rigorous Numerics", ""])
    if pack.get("pde_rigorous_numerics_checks"):
        for item in pack["pde_rigorous_numerics_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"classification=`{res.get('classification')}` "
                f"missing={res.get('missing_fields')}; "
                f"rejected={res.get('rejected_substitutes')}"
            )
            lines.append(f"  - boundary: {res.get('credit_boundary')}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Theorem Applicability", ""])
    if pack.get("theorem_applicability_checks"):
        for item in pack["theorem_applicability_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: verdict=`{res.get('verdict')}` "
                f"missing={res.get('missing_fields', [])}; "
                f"rejected={res.get('rejected_substitutes', [])}"
            )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Pi-Group Forcing", ""])
    if pack.get("pi_group_checks"):
        for item in pack["pi_group_checks"]:
            lines.append(f"- `{item['label']}`: {item['report']}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Ambiguous Pi Pinning", ""])
    if pack.get("ambiguous_pi_pinning_checks"):
        for item in pack["ambiguous_pi_pinning_checks"]:
            result = item.get("result") or {}
            lines.append(f"- `{item['label']}`: {item['report']}")
            for violation in result.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Dimensionless Exponent Source", ""])
    if pack.get("dimensionless_exponent_source_checks"):
        for item in pack["dimensionless_exponent_source_checks"]:
            result = item.get("result") or {}
            lines.append(f"- `{item["label"]}`: {item["report"]}")
            for violation in result.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get("type")}` "
                    f"{violation.get("missing_fields", violation.get("fields", ""))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Linear Observable Coercivity", ""])
    if pack.get("linear_observable_coercivity_checks"):
        for item in pack["linear_observable_coercivity_checks"]:
            lines.append(f"- `{item['label']}`: {item['report']}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Single-Spend Carrier Audit", ""])
    if pack.get("single_spend_audit"):
        audit = pack["single_spend_audit"]
        lines.append(
            f"- `{audit['summary']}`; passed=`{audit['passed']}`; "
            f"missing={audit['missing_channels']}; "
            f"prop_only={audit.get('prop_only_blocking_channels', audit.get('prop_only_payment_channels', []))}"
        )
        for warning in audit.get("warnings", []):
            lines.append(f"- warning: {warning}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Receipt Strength Audit", ""])
    if pack.get("receipt_strength_audit"):
        audit = pack["receipt_strength_audit"]
        lines.append(
            f"- `{audit['summary']}`; passed=`{audit['passed']}`; "
            f"missing={audit['missing_receipts']}; weak={audit['weak_receipts']}"
        )
        for warning in audit.get("warnings", []):
            lines.append(f"- warning: {warning}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Owner-Preimage Prefix Gate", ""])
    if pack.get("owner_preimage_prefix_gate"):
        gate = pack["owner_preimage_prefix_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', '')}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Scaled-Transfer Numeric Receipt Gate", ""])
    if pack.get("scaled_transfer_numeric_receipt_gate"):
        gate = pack["scaled_transfer_numeric_receipt_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Owner-Geometry Core Receipt Gate", ""])
    if pack.get("owner_geometry_core_receipt_gate"):
        gate = pack["owner_geometry_core_receipt_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Fresh-Annular Anti-Laundering Gate", ""])
    if pack.get("fresh_annular_anti_laundering_gate"):
        gate = pack["fresh_annular_anti_laundering_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Fresh-Annular Non-Disguise Gate", ""])
    if pack.get("fresh_annular_non_disguise_gate"):
        gate = pack["fresh_annular_non_disguise_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Fresh-Annular Innovation Gate", ""])
    if pack.get("fresh_annular_innovation_gate"):
        gate = pack["fresh_annular_innovation_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Section-Fixed Unsigned Variation Gate", ""])
    if pack.get("section_fixed_unsigned_variation_gate"):
        gate = pack["section_fixed_unsigned_variation_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Inequality Prefilter", ""])
    if pack["inequality_checks"]:
        for check in pack["inequality_checks"]:
            if check.get("lhs") is not None:
                label = f"{check.get('lhs')} {check.get('op')} {check.get('rhs')}"
            else:
                label = check.get("candidate_inequality") or "<unparsed>"
            detail = check.get("violations", [])
            if check.get("reason"):
                detail = [*detail, {"reason": check.get("reason")}]
            lines.append(
                f"- `{label}`: `passed={check.get('passed')}` {detail}"
            )
    else:
        lines.append("- (no candidate inequalities supplied)")
    lines.extend(["", "## Curriculum", ""])
    if pack["curriculum_variants"]:
        for item in pack["curriculum_variants"]:
            if "error" in item:
                lines.append(f"- ERROR: {item['error']}")
            else:
                lines.append(f"- `{item['transform']}` -> `{item['lean_path']}`")
    else:
        hints = TRANSFORM_HINTS.get(pack["gap_classification"].get("gap_type"), [])
        lines.append(f"- Suggested transforms: {', '.join(hints) if hints else '(none)'}")
    lines.extend([
        "",
        "## Anti-Tautology Notes",
        "",
        "- This pack nominates context only; it does not prove a theorem.",
        "- If a rubric already enables GP-180 / framer / in-loop falsifiers, use those core ZTARE mechanisms rather than duplicating them here.",
        "- Treat `Prop` fields as declarations unless paired with paid proof fields.",
        "- Promote only compiler-checked Lean, concrete falsifiers, or named missing primitives.",
    ])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build an RD caller pack over existing ZTARE PDE/scout primitives")
    ap.add_argument("--target", required=True)
    ap.add_argument("--field")
    ap.add_argument(
        "--mode",
        choices=["audit", "pde-execution"],
        default="audit",
        help=(
            "audit builds the existing context pack; pde-execution also emits "
            "required estimate/falsifier/theorem-match work-unit templates."
        ),
    )
    ap.add_argument(
        "--min-work-units",
        type=int,
        default=3,
        help="Minimum work-unit count requested in pde-execution mode.",
    )
    ap.add_argument(
        "--hostile-packet-suite",
        default="ns_default",
        help="Hostile packet suite to include in pde-execution mode.",
    )
    ap.add_argument(
        "--target-currency",
        help="Target proof currency for the pde-execution currency ledger.",
    )
    ap.add_argument("--candidate-inequality", action="append", default=[])
    ap.add_argument("--dimensional-features-json", type=Path)
    ap.add_argument(
        "--allowed-endpoint",
        action="append",
        default=[],
        help="Identifier allowed in candidate inequalities; repeatable.",
    )
    ap.add_argument(
        "--allowed-json",
        type=Path,
        help="JSON list of identifiers allowed in candidate inequalities.",
    )
    ap.add_argument("--aux-keyword")
    ap.add_argument("--top-lemmas", type=int, default=12)
    ap.add_argument("--top-aux", type=int, default=5)
    ap.add_argument("--emit-curriculum", action="store_true")
    ap.add_argument("--curriculum-transform", action="append", default=[])
    ap.add_argument(
        "--pi-group-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-PI-GROUP-FORCING check. "
            "Shape: {label, quantity_dim, subset_dims}."
        ),
    )
    ap.add_argument(
        "--dimensionless-exponent-source-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-DIMENSIONLESS-EXPONENT-SOURCE. "
            "Shape: {label, expression, dimensionless_variables, receipts}."
        ),
    )
    ap.add_argument(
        "--ambiguous-pi-pinning-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-AMBIGUOUS-PI-PINNING. "
            "Shape: {label, pi_group_result|ambiguous, receipts}."
        ),
    )
    ap.add_argument(
        "--persistence-budget-exponent-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-PERSISTENCE-BUDGET-EXPONENT. "
            "Shape: {label, dimension, persistence_exponent, "
            "thickness_or_reach_receipt, uniform_complexity_receipt, "
            "same_carrier_receipt}."
        ),
    )
    ap.add_argument(
        "--moment-ratio-surplus-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-MOMENT-RATIO-SURPLUS check. "
            "Shape: {label, first_moment_sq, second_moment_cap, "
            "cheap_boundary_lower_bound, threshold_space_measure}."
        ),
    )
    ap.add_argument(
        "--bounded-ratio-support-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-BOUNDED-RATIO-SUPPORT check. "
            "Shape: {label, mean_surplus, ratio_upper_bound, "
            "companion_lower_bound, threshold_space_measure}."
        ),
    )
    ap.add_argument(
        "--finite-prefix-selection-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-FINITE-PREFIX-SELECTION check. "
            "Shape: {label, boundary, interface, prefix_length, "
            "same_source_family, prefix_fixed_before_payoff, "
            "boundary_interface_units_aligned, no_post_payoff_selection, "
            "interface_floor}."
        ),
    )
    ap.add_argument(
        "--event-family-binding-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-EVENT-FAMILY-BINDING check. "
            "Shape: {label, target_event_family, source_event_family, "
            "event_identity, pre_payoff_timing, same_carrier, "
            "same_owner_or_source, index_map, index_map_total_on_prefix, "
            "no_proxy_family, no_post_payoff_selection}."
        ),
    )
    ap.add_argument(
        "--analogical-transfer-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a "
            "G-ANALOGICAL-TRANSFER-RECEIPT check. Shape: {label, "
            "donor_domain, donor_pattern, donor_invariant, target_domain, "
            "target_obligation, mapping, preserved_structure, loss_budget, "
            "target_receipt_or_gate, nearest_confuser, confuser_distinction, "
            "falsifier_or_kill_condition, concrete_next_check}."
        ),
    )
    ap.add_argument(
        "--prefix-count-bridge-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-PREFIX-COUNT-BRIDGE check. "
            "Shape: {label, target_prefix_family, source_prefix_family, "
            "target_count, source_count, source_budget, prefix_index_map, "
            "map_total_on_target_prefix, pointwise_assignment_or_injection, "
            "target_count_le_source_count, source_count_le_budget, "
            "target_count_le_budget_conclusion, fixed_before_payoff, "
            "not_target_defined, no_post_payoff_selection, "
            "no_rebilling_same_source_atom, no_endpoint_restatement, "
            "nearest_confuser, confuser_distinction}."
        ),
    )
    ap.add_argument(
        "--source-prefix-budget-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-SOURCE-PREFIX-BUDGET check. "
            "Shape: {label, source_prefix_family, budget_family, "
            "source_count, budget_count, budget_index, prefix_to_budget_map, "
            "map_total_on_source_prefix, pointwise_budget_assignment, "
            "source_count_le_budget, fixed_before_payoff, "
            "same_owner_or_source, bounded_fanout_or_multiplicity, "
            "no_logarithmic_reuse, no_rebilling_same_source_atom, "
            "not_target_defined, no_post_payoff_selection, "
            "no_endpoint_restatement, nearest_confuser, confuser_distinction}."
        ),
    )
    ap.add_argument(
        "--final-slot-indexed-source-budget-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a "
            "G-FINAL-SLOT-INDEXED-SOURCE-BUDGET check. Shape: {label, "
            "source_prefix_family, source_prefix_definition, event_stream, "
            "final_slot_index, source_count, budget_count, source_slot_map, "
            "identity_on_final_slot_prefix, map_total_on_indexed_prefix, "
            "source_slot_injective, event_data_binding, same_tree_lock_binding, "
            "displayed_fanout_or_no_log_reuse, fixed_before_payoff, "
            "not_target_defined, no_post_payoff_slot_truncation, "
            "no_rebilling_same_source_atom, no_endpoint_capacity_restatement, "
            "remaining_target_assignment_obligation, nearest_confuser, "
            "confuser_distinction}."
        ),
    )
    ap.add_argument(
        "--target-indexed-event-assignment-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TARGET-INDEXED-EVENT-ASSIGNMENT-PROVENANCE. Shape: {label, "
            "mode, target_prefix_family, target_prefix_definition, "
            "target_count, indexed_event_stream, "
            "indexed_event_prefix_definition, event_prefix_index, "
            "event_count, incidence_geometry, same_tree_or_carrier_binding, "
            "fixed_before_payoff, not_target_defined, "
            "no_post_payoff_assignment_pruning, "
            "no_endpoint_capacity_restatement, nearest_confuser, "
            "confuser_distinction, plus mode-specific construction, "
            "reduction, or refutation fields}."
        ),
    )
    ap.add_argument(
        "--incidence-derived-finite-injection-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-INCIDENCE-DERIVED-FINITE-INJECTION. Shape: {label, "
            "incidence_source, domain_predicate, codomain_event_family, "
            "map_extraction_rule, totality_derivation, "
            "uniqueness_or_collision_exclusion, injectivity_derivation, "
            "same_event_family_binding, finite_domain, finite_codomain, "
            "no_post_payoff_choice, not_cardinality_as_injectivity, "
            "not_label_only_incidence, nearest_confuser, "
            "downstream_cardinality_bridge}."
        ),
    )
    ap.add_argument(
        "--bounded-incident-existence-eventdata-horizon-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-BOUNDED-INCIDENT-EXISTENCE-EVENTDATA-HORIZON. Shape: "
            "{label, target_family, target_event_candidate, "
            "candidate_event_selector, eventdata_binding, horizon_bound, "
            "incidence_witness, bounded_existence_derivation, "
            "prefix_domination_binding, same_tree_binding, "
            "fixed_before_payoff, no_post_payoff_choice, "
            "not_target_deficit_selected, not_label_only_eventdata, "
            "not_label_only_incidence, downstream_no_reuse_collision_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--target-event-candidate-cover-selection-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TARGET-EVENT-CANDIDATE-COVER-SELECTION. Shape: {label, "
            "target_family, cover_relation, cover_selector, "
            "selector_totality, horizon_from_cover, incidence_from_cover, "
            "eventdata_binding, prefix_domination_binding, same_tree_binding, "
            "fixed_before_payoff, no_post_payoff_selection, "
            "not_target_deficit_selected, not_label_only_cover, "
            "not_label_only_eventdata, downstream_eventdata_horizon_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--target-cover-eventdata-incidence-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TARGET-COVER-EVENTDATA-INCIDENCE. Shape: {label, "
            "target_family, eventdata_source, target_node_source, "
            "cover_event_selector, cover_relation_definition, "
            "selector_totality, cover_relation_is_selector_graph, "
            "selector_below_final_slot, selector_incident_to_target, "
            "cover_to_horizon_law, cover_to_incidence_law, "
            "same_tree_binding, prefix_domination_binding, "
            "incidence_geometry_binding, fixed_before_payoff, "
            "no_post_payoff_cover_choice, not_target_deficit_selected, "
            "not_label_only_eventdata, not_label_only_incidence, "
            "not_label_only_cover, downstream_cover_selection_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--cover-event-selector-finalslot-assignment-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-COVER-EVENT-SELECTOR-FINALSLOT-ASSIGNMENT. Shape: {label, "
            "target_family, final_slot_assignment, assignment_codomain, "
            "cover_event_selector_definition, selector_is_assignment_value, "
            "selector_below_final_slot, assignment_incidence_law, "
            "selector_incidence_transport, eventdata_binding, "
            "same_tree_binding, prefix_domination_binding, "
            "incidence_geometry_binding, assignment_totality, "
            "assignment_fixed_before_payoff, not_target_deficit_selected, "
            "no_post_payoff_assignment, not_endpoint_capacity_only, "
            "not_label_only_assignment, not_label_only_eventdata, "
            "not_label_only_incidence, downstream_eventdata_incidence_cover_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--target-slot-bounded-incidence-least-hit-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TARGET-SLOT-BOUNDED-INCIDENCE-LEAST-HIT. Shape: {label, "
            "target_family, incidence_relation, bounded_incident_existence_theorem, "
            "least_hit_target_slot_rule, target_slot_codomain, "
            "target_slot_bound_derivation, target_slot_incidence_law, "
            "same_tree_eventdata_binding, prefix_domination_binding, "
            "fanout_no_reuse_binding, assignment_totality, "
            "assignment_fixed_before_payoff, no_post_payoff_least_hit_choice, "
            "no_post_payoff_existence_choice, not_target_deficit_selected, "
            "not_endpoint_capacity_only, not_cardinality_as_injectivity, "
            "not_label_only_assignment, not_label_only_eventdata, "
            "not_label_only_incidence, downstream_finalslot_assignment_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--bounded-incident-existence-sametree-eventdata-index-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-BOUNDED-INCIDENT-EXISTENCE-SAMETREE-EVENTDATA-INDEX. Shape: "
            "{label, target_family, same_tree_eventdata_stream, "
            "target_eventdata_index, target_eventdata_codomain, "
            "eventdata_binding, index_below_final_slot, displayed_incidence_law, "
            "bounded_existence_witness_rule, same_tree_binding, "
            "prefix_domination_binding, fanout_no_reuse_binding, "
            "fixed_before_payoff, no_post_payoff_index_choice, "
            "not_target_deficit_selected, not_endpoint_capacity_only, "
            "not_label_only_eventdata, not_label_only_incidence, "
            "downstream_least_hit_targetslot_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--target-eventdata-index-prefix-cover-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TARGET-EVENTDATA-INDEX-PREFIX-COVER. Shape: {label, "
            "target_family, prefix_cover_relation, selected_eventdata_index, "
            "selected_index_codomain, selected_index_covers_target, "
            "eventdata_binding_rule, cover_to_incidence_law, "
            "same_tree_binding, prefix_domination_binding, "
            "incidence_geometry_binding, cover_relation_total_before_payoff, "
            "selected_index_fixed_before_payoff, not_target_deficit_selected, "
            "not_endpoint_capacity_only, not_label_only_cover, "
            "not_label_only_eventdata, not_label_only_incidence, "
            "downstream_sametree_eventdata_index_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--finite-scale-cofinality-prefix-cover-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-FINITE-SCALE-COFINALITY-PREFIX-COVER. Shape: {label, "
            "target_family, finite_scale_prefix_comparison, "
            "event_prefix_cofinality, selected_eventdata_index, "
            "selected_index_codomain, cover_relation_definition, "
            "cover_relation_is_guarded_graph, selected_index_cover_membership, "
            "selected_index_incidence_law, cover_to_incidence_transport, "
            "same_tree_binding, prefix_domination_primitive_binding, "
            "incidence_geometry_binding, selected_index_fixed_before_payoff, "
            "not_arbitrary_cover_relation, not_endpoint_capacity_only, "
            "not_label_only_prefix_domination, not_post_payoff_selection, "
            "downstream_prefix_cover_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--event-to-badnode-selected-index-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-EVENT-TO-BADNODE-SELECTED-INDEX. Shape: {label, "
            "target_family, finite_event_prefix_index, selected_index_codomain, "
            "event_to_badnode_map, target_node_event_to_badnode_equality, "
            "event_prefix_membership_source, displayed_incidence_refinement, "
            "selected_index_incidence_transport, same_tree_binding, "
            "prefix_domination_primitive_binding, incidence_geometry_binding, "
            "event_node_identification_binding, selected_index_fixed_before_payoff, "
            "not_arbitrary_selected_index, not_endpoint_capacity_only, "
            "not_event_to_badnode_label_only, not_incidence_label_only, "
            "not_post_payoff_selection, downstream_finite_scale_cofinality_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--event-prefix-coverage-selected-index-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-EVENT-PREFIX-COVERAGE-SELECTED-INDEX. Shape: {label, "
            "target_family, coverage_packet, selected_prefix_event_index, "
            "selected_index_codomain, event_prefixes_exhaust_selected_bad_nodes, "
            "every_selected_bad_node_appears_in_some_prefix, "
            "prefix_dominates_finite_selected_bad_tree_beta_sum, "
            "duplicate_events_charge_multiplicity, "
            "no_shell_only_enumeration_shortcut, "
            "no_adaptive_stopping_from_beta_sum, "
            "target_node_event_to_badnode_equality, "
            "displayed_incidence_refinement, selected_index_incidence_transport, "
            "same_tree_binding, event_node_identification_binding, "
            "selected_index_fixed_before_payoff, not_coverage_label_only, "
            "not_arbitrary_selected_index, not_endpoint_capacity_only, "
            "not_post_payoff_selection, "
            "downstream_event_to_badnode_selected_index_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--coverage-choice-finite-selector-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-COVERAGE-CHOICE-FINITE-SELECTOR. Shape: {label, "
            "target_family, coverage_packet, coverage_choice_witness, "
            "selected_index_definition, selected_index_codomain, "
            "target_node_selected_bad_membership, choice_from_appearance_field, "
            "choice_uses_target_membership, event_to_badnode_target_equality, "
            "displayed_incidence_refinement, selected_index_incidence_transport, "
            "same_tree_binding, event_node_identification_binding, "
            "event_prefixes_exhaust_selected_bad_nodes, "
            "every_selected_bad_node_appears_in_some_prefix, "
            "prefix_dominates_finite_selected_bad_tree_beta_sum, "
            "duplicate_events_charge_multiplicity, "
            "no_shell_only_enumeration_shortcut, "
            "no_adaptive_stopping_from_beta_sum, "
            "coverage_choice_fixed_before_payoff, "
            "not_classical_choice_from_bare_appearance, "
            "not_endpoint_capacity_only, not_post_payoff_selection, "
            "downstream_event_prefix_coverage_selected_index_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--typed-appearance-coverage-choice-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TYPED-APPEARANCE-COVERAGE-CHOICE. Shape: {label, "
            "target_family, typed_selected_bad_node_appearance, "
            "target_node_selected_bad_membership, coverage_choice_specialization, "
            "selected_index_codomain, event_to_badnode_target_equality, "
            "coverage_packet, appearance_refines_coverage, "
            "appearance_uses_target_membership, displayed_incidence_refinement, "
            "same_tree_binding, event_node_identification_binding, "
            "event_prefixes_exhaust_selected_bad_nodes, "
            "every_selected_bad_node_appears_in_some_prefix, "
            "prefix_dominates_finite_selected_bad_tree_beta_sum, "
            "duplicate_events_charge_multiplicity, "
            "no_shell_only_enumeration_shortcut, "
            "no_adaptive_stopping_from_beta_sum, "
            "typed_appearance_fixed_before_payoff, "
            "not_classical_choice_from_bare_appearance, "
            "not_endpoint_capacity_only, not_post_payoff_selection, "
            "downstream_coverage_choice_finite_selector_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--typed-coverage-packet-appearance-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TYPED-COVERAGE-PACKET-APPEARANCE. Shape: {label, "
            "target_family, ordinary_coverage_packet, typed_coverage_packet, "
            "typed_selected_bad_node_appearance, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "target_node_selected_bad_membership, "
            "target_membership_specialization, "
            "event_to_badnode_target_equality, displayed_incidence_refinement, "
            "same_tree_binding, typed_appearance_fixed_before_payoff, "
            "not_bare_prop_choice, not_endpoint_capacity_only, "
            "not_post_payoff_selection, "
            "downstream_typed_appearance_coverage_choice_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--event-prefix-enumeration-packet-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-EVENT-PREFIX-ENUMERATION-PACKET. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "selected_bad_node_event_prefix_enumeration, enumeration_codomain, "
            "enumeration_refines_coverage_appearance, "
            "enumeration_bounded_by_final_event_prefix, "
            "enumeration_uses_same_bad_center_event_nodes, "
            "enumeration_uses_event_to_badnode, event_to_badnode_target_equality, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "enumeration_fixed_before_payoff, not_bare_prop_choice, "
            "not_endpoint_capacity_only, not_shell_only_enumeration, "
            "not_post_payoff_selection, downstream_typed_coverage_packet, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--bounded-natural-event-enumeration-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-BOUNDED-NATURAL-EVENT-ENUMERATION. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "selected_bad_node_natural_event_enumeration, "
            "natural_index_codomain, strict_prefix_bound, "
            "event_to_badnode_target_equality, "
            "natural_enumeration_refines_coverage_appearance, "
            "natural_enumeration_uses_same_bad_center_event_nodes, "
            "natural_enumeration_uses_event_to_badnode, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "natural_enumeration_fixed_before_payoff, "
            "not_bare_prop_choice, not_endpoint_capacity_only, "
            "not_shell_only_enumeration, not_post_payoff_selection, "
            "downstream_event_prefix_enumeration_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--unbounded-event-witness-prefix-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-UNBOUNDED-EVENT-WITNESS-PREFIX-BOUND. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "selected_bad_node_natural_event_witness, "
            "event_to_badnode_target_equality, same_witness_prefix_bound, "
            "strict_prefix_bound, witness_refines_cofinal_selected_tree_incidence, "
            "prefix_bound_comes_from_final_event_prefix, "
            "witness_uses_same_bad_center_event_nodes, "
            "witness_uses_event_to_badnode, coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "witness_and_bound_fixed_before_payoff, not_bare_prop_choice, "
            "not_endpoint_capacity_only, not_shell_only_enumeration, "
            "not_post_payoff_selection, "
            "downstream_bounded_natural_event_enumeration_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--cofinal-incidence-witness-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-COFINAL-INCIDENCE-WITNESS-BOUND. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "cofinal_selected_tree_incidence_receipt, selected_bad_node_has_event, "
            "chosen_event_witness, chosen_event_to_badnode_equality, "
            "same_chosen_witness_prefix_bound, strict_prefix_bound, "
            "cofinal_incidence_refines_coverage_appearance, "
            "prefix_bound_comes_from_final_event_prefix, "
            "cofinal_incidence_uses_same_bad_center_event_nodes, "
            "cofinal_witness_uses_event_to_badnode, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "cofinal_witness_and_bound_fixed_before_payoff, "
            "not_bare_prop_choice_beyond_cofinal_receipt, "
            "not_endpoint_capacity_only, not_shell_only_enumeration, "
            "not_post_payoff_selection, "
            "downstream_unbounded_event_witness_prefix_bound_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--explicit-cofinal-event-witness-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-EXPLICIT-COFINAL-EVENT-WITNESS-BOUND. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "cofinal_selected_tree_incidence_receipt, "
            "explicit_cofinal_event_witness, explicit_event_to_badnode_equality, "
            "same_explicit_witness_prefix_bound, strict_prefix_bound, "
            "explicit_witness_refines_cofinal_incidence, "
            "prefix_bound_comes_from_final_event_prefix, "
            "explicit_witness_uses_same_bad_center_event_nodes, "
            "explicit_witness_uses_event_to_badnode, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "explicit_witness_and_bound_fixed_before_payoff, "
            "not_bare_prop_choice_for_explicit_witness, "
            "not_endpoint_capacity_only, not_shell_only_enumeration, "
            "not_post_payoff_selection, "
            "downstream_unbounded_event_witness_prefix_bound_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--cofinal-event-selector-final-prefix-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-COFINAL-EVENT-SELECTOR-FINAL-PREFIX-BOUND. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "cofinal_selected_tree_incidence_receipt, cofinal_event_selector, "
            "selector_event_to_badnode_equality, "
            "same_selector_final_prefix_bound, strict_prefix_bound, "
            "selector_refines_cofinal_incidence, "
            "selector_bound_comes_from_final_event_prefix, "
            "selector_uses_same_bad_center_event_nodes, "
            "selector_uses_event_to_badnode, coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "selector_and_bound_fixed_before_payoff, "
            "not_bare_prop_choice_for_selector, not_endpoint_capacity_only, "
            "not_shell_only_enumeration, not_post_payoff_selection, "
            "downstream_explicit_cofinal_event_witness_bound_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--finite-cofinal-event-selector-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-FINITE-COFINAL-EVENT-SELECTOR. Shape: {label, target_family, "
            "ordinary_coverage_packet, cofinal_selected_tree_incidence_receipt, "
            "finite_cofinal_event_selector, finite_selector_codomain, "
            "finite_selector_event_to_badnode_equality, "
            "strict_prefix_bound_from_fin_codomain, "
            "finite_selector_refines_cofinal_incidence, "
            "finite_selector_codomain_is_final_event_prefix, "
            "finite_selector_uses_same_bad_center_event_nodes, "
            "finite_selector_uses_event_to_badnode, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "finite_selector_fixed_before_payoff, "
            "not_bare_prop_choice_for_finite_selector, "
            "not_endpoint_capacity_only, not_shell_only_enumeration, "
            "not_post_payoff_selection, "
            "downstream_cofinal_event_selector_final_prefix_bound_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--positive-variation-bridge-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-POSITIVE-VARIATION-BRIDGE "
            "check. Shape: {label, signed_source, positive_variation_source, "
            "same_carrier, numeric_domination, event_scope, "
            "fixed_before_payoff, no_post_payoff_positive_part, "
            "no_target_deficit_definition}."
        ),
    )
    ap.add_argument(
        "--positive-variation-quotient-wash-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-POSITIVE-VARIATION-QUOTIENT-WASH "
            "check. Shape: {label, net_or_quotient_source_law, "
            "positive_variation_or_turnover_currency, same_source_or_owner_binding, "
            "pre_payoff_representative_fixed, no_wash_cycle_law, "
            "no_null_cycle_growth, bounded_positive_variation_from_net_budget, "
            "no_post_payoff_grossing}."
        ),
    )
    ap.add_argument(
        "--quotient-minimal-carrier-payment-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-QUOTIENT-MINIMAL-CARRIER-PAYMENT "
            "check. Shape: {label, quotient_source_law, "
            "minimal_carrier_definition, selected_production_functional, "
            "pre_payoff_representative_selector, "
            "selector_independent_of_target_deficit, "
            "production_preserved_by_selector, "
            "kernel_cycles_zero_selected_production, "
            "minimal_carrier_bounds_selected_production}."
        ),
    )
    ap.add_argument(
        "--quadratic-quotient-descent-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-QUADRATIC-QUOTIENT-DESCENT "
            "check. Shape: {label, source_map_or_equivalence, "
            "quadratic_functional, polarized_bilinear_form, "
            "source_kernel_definition, representative_selector, "
            "selector_fixed_before_payoff, kernel_square_zero_or_nonpositive, "
            "kernel_cross_zero_or_nonpositive, quotient_descent_or_bound, "
            "not_defined_by_target_deficit}."
        ),
    )
    ap.add_argument(
        "--nonadaptive-source-selection-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-NONADAPTIVE-SOURCE-SELECTION "
            "check. Shape: {label, source_object, extractor_or_selection_rule, "
            "source_family, owner_or_carrier_binding, index_or_selection_map, "
            "fixed_before_payoff, selection_rule_declared_before_target, "
            "target_not_used_to_define_source, timing_receipt, "
            "no_post_payoff_selection}."
        ),
    )
    ap.add_argument(
        "--support-index-law-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-LAW. Shape: "
            "{label, support_index_map, support_domain, membership_law, "
            "restricted_prefix_law, injectivity_law, totality_law, "
            "pointwise_lower_transfer_law, boundary_payment_transfer_law, "
            "fixed_before_payoff, not_target_defined, no_post_payoff_pruning}."
        ),
    )
    ap.add_argument(
        "--support-index-injectivity-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-INJECTIVITY. "
            "Shape: {label, support_index_map, support_domain, "
            "order_or_separation_law, collision_exclusion_derivation, "
            "equality_reflection_law, injectivity_scope, fixed_before_payoff, "
            "not_target_defined, no_post_payoff_reindexing, "
            "no_cardinality_label_as_injectivity, no_packing_label_as_injectivity}."
        ),
    )
    ap.add_argument(
        "--support-index-affine-order-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-AFFINE-ORDER. "
            "Shape: {label, support_index_map, support_domain, affine_base, "
            "affine_stride, positive_stride, affine_formula_on_domain, "
            "strict_order_derivation, fixed_before_payoff, not_target_defined, "
            "no_post_payoff_reindexing, no_cardinality_label_as_order, "
            "no_packing_label_as_order}."
        ),
    )
    ap.add_argument(
        "--support-index-fixed-step-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-FIXED-STEP. "
            "Shape: {label, support_index_map, support_domain, base_at_zero, "
            "step_stride, positive_stride, successor_step_law, "
            "induction_derivation, fixed_before_payoff, not_target_defined, "
            "no_post_payoff_reindexing, no_cardinality_label_as_step, "
            "no_packing_label_as_step, no_selected_event_as_step}."
        ),
    )
    ap.add_argument(
        "--support-index-adjacent-gap-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-ADJACENT-GAP. "
            "Shape: {label, support_index_map, adjacent_pair_domain, "
            "owner_or_carrier_binding, base_at_zero, adjacent_gap_map, "
            "gap_stride, positive_stride, support_index_succ_eq_add_gap, "
            "adjacent_gap_eq_stride_on_prefix, successor_step_derivation, "
            "same_owner_adjacent_step_receipt, fixed_before_payoff, "
            "not_target_defined, no_post_payoff_pair_selection, "
            "no_strict_order_label_as_gap, no_cardinality_label_as_gap, "
            "no_packing_label_as_gap, no_selected_event_as_gap}."
        ),
    )
    ap.add_argument(
        "--support-index-unit-gap-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-UNIT-GAP. "
            "Shape: {label, support_index_map, adjacent_pair_domain, "
            "owner_or_carrier_binding, base_at_zero, unit_gap_law, "
            "unit_gap_positive, support_index_succ_eq_succ, "
            "adjacent_gap_constructor, stride_one_derivation, "
            "fixed_before_payoff, not_target_defined, "
            "no_post_payoff_pair_selection, "
            "no_strict_order_label_as_unit_gap, "
            "no_cardinality_label_as_unit_gap, "
            "no_packing_label_as_unit_gap, no_selected_event_as_unit_gap}."
        ),
    )
    ap.add_argument(
        "--support-index-no-hole-unit-gap-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-NO-HOLE-UNIT-GAP. "
            "Shape: {label, support_index_map, adjacent_pair_domain, "
            "owner_or_carrier_binding, base_at_zero, strict_successor_order, "
            "no_between_adjacent_support_index, nat_successor_derivation, "
            "unit_gap_constructor, fixed_before_payoff, not_target_defined, "
            "no_post_payoff_pair_selection, no_strict_order_only_as_no_hole, "
            "no_cardinality_label_as_no_hole, no_packing_label_as_no_hole, "
            "no_selected_event_as_no_hole}."
        ),
    )
    ap.add_argument(
        "--support-index-endpoint-tight-no-hole-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-ENDPOINT-TIGHT-NO-HOLE. Shape: "
            "{label, support_index_map, support_length, prefix_domain, "
            "base_index, base_anchor_at_zero, endpoint_lower_bound_on_prefix, "
            "endpoint_upper_bound_on_prefix, "
            "pointwise_eq_base_plus_k_derived_from_bounds, "
            "strict_order_on_prefix_holds_or_derived, "
            "adjacent_endpoint_eq_left, adjacent_endpoint_eq_right, "
            "nat_no_between_successive_endpoints, no_hole_constructor, "
            "level475_skipped_slot_rejected_by_upper_bound, "
            "not_level464_no_hole_assumed, not_unit_gap_assumed, "
            "not_affine_stride_one_assumed_without_bounds}."
        ),
    )
    ap.add_argument(
        "--support-index-base-anchored-strict-lower-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-BASE-ANCHORED-STRICT-LOWER-BOUND. Shape: "
            "{label, support_index_map, support_length, prefix_domain, "
            "base_index, base_anchor_at_zero, strict_order_on_prefix, "
            "same_owner_base_and_support_index, nonempty_zero_domain_guard, "
            "predecessor_prefix_closure, nat_strict_step_implies_successor_le, "
            "lower_bound_induction_base, lower_bound_induction_step, "
            "derived_endpoint_lower_bound_on_prefix, "
            "upper_endpoint_bound_live_debt, "
            "level475_skipped_slot_still_admitted}."
        ),
    )
    ap.add_argument(
        "--support-index-final-endpoint-capacity-upper-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-FINAL-ENDPOINT-CAPACITY-UPPER-BOUND. Shape: "
            "{label, support_index_map, support_length, prefix_domain, "
            "base_index, final_slot, support_length_eq_succ_final_slot, "
            "strict_order_on_prefix, tail_step_count_from_strict_order, "
            "final_endpoint_capacity_bound, nat_tail_capacity_cancellation, "
            "derived_endpoint_upper_bound_on_prefix, "
            "level475_skipped_slot_rejected_by_final_capacity}."
        ),
    )
    ap.add_argument(
        "--support-index-final-slot-upper-bound-tail-capacity-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-FINAL-SLOT-UPPER-BOUND-TAIL-CAPACITY. Shape: "
            "{label, support_index_map, support_length, prefix_domain, "
            "base_index, final_slot, support_length_eq_succ_final_slot, "
            "strict_order_on_prefix, tail_step_count_from_strict_order, "
            "final_slot_upper_bound_tail_capacity, "
            "nat_tail_capacity_cancellation, "
            "derived_endpoint_upper_bound_on_prefix, "
            "level475_skipped_slot_rejected_by_final_capacity}."
        ),
    )
    ap.add_argument(
        "--support-index-tail-capacity-failure-witness-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-TAIL-CAPACITY-FAILURE-WITNESS. Shape: "
            "{label, support_index_map, support_index_values, support_length, "
            "prefix_domain, base_index, final_slot, "
            "support_length_eq_succ_final_slot, capacity_failure_index, "
            "base_anchor_at_zero_holds, strict_order_on_prefix_holds, "
            "lower_endpoint_bound_on_prefix_holds, "
            "final_endpoint_capacity_bound_fails, "
            "tail_capacity_inequality_fails, "
            "derived_upper_endpoint_bound_fails, "
            "level477_lower_bound_still_holds}."
        ),
    )
    ap.add_argument(
        "--support-index-skipped-slot-hostile-witness-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-SKIPPED-SLOT-HOSTILE-WITNESS. Shape: "
            "{label, support_index_map, support_index_values, support_length, "
            "prefix_domain, adjacent_pair_index, adjacent_pair_domain, "
            "strict_order_on_prefix_holds, injectivity_on_prefix_holds, "
            "finite_image_cardinality_eq_support_length_holds, "
            "skipped_slot_witness, skipped_slot_between_adjacent_values, "
            "no_prefix_preimage_for_skipped_slot, "
            "no_between_adjacent_support_index_fails, "
            "unit_successor_law_fails, interval_image_totality_fails, "
            "not_empty_domain_vacuity, fixed_before_payoff, "
            "not_target_defined, nearest_confuser_level474_distinction, "
            "nearest_confuser_level465_distinction}."
        ),
    )
    ap.add_argument(
        "--support-index-interval-image-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-INTERVAL-IMAGE. "
            "Shape: {label, support_index_map, prefix_domain, "
            "owner_or_carrier_binding, base_at_zero, strict_order_on_prefix, "
            "adjacent_interval_totality, strict_order_collision_exclusion, "
            "no_hole_constructor, fixed_before_payoff, not_target_defined, "
            "no_post_payoff_interval_filling, "
            "no_strict_order_only_as_interval_image, "
            "no_cardinality_label_as_interval_image, "
            "no_packing_label_as_interval_image, "
            "no_selected_event_as_interval_image}."
        ),
    )
    ap.add_argument(
        "--support-index-interval-preimage-selector-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-INTERVAL-PREIMAGE-SELECTOR. "
            "Shape: {label, support_index_map, prefix_domain, "
            "owner_or_carrier_binding, base_at_zero, strict_order_on_prefix, "
            "interval_preimage_selector, selector_domain_totality, "
            "selector_prefix_membership, selector_maps_to_requested_nat, "
            "selector_not_skolemized_from_interval_image_totality, "
            "interval_image_constructor, fixed_before_payoff, "
            "not_target_defined, no_post_payoff_selector_filling, "
            "no_exists_label_only_as_selector, no_strict_order_only_as_selector, "
            "no_cardinality_label_as_selector, no_packing_label_as_selector, "
            "no_selected_event_as_selector}."
        ),
    )
    ap.add_argument(
        "--support-index-least-interval-preimage-selector-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-LEAST-INTERVAL-PREIMAGE-SELECTOR. "
            "Shape: {label, support_index_map, prefix_domain, "
            "same_support_index_same_prefix, owner_or_carrier_binding, "
            "base_at_zero, strict_order_on_prefix, least_selector_function, "
            "bounded_search_domain, candidate_predicate_exact, "
            "bounded_search_provenance, search_success_certificate, "
            "search_success_not_from_interval_image_totality, "
            "search_success_not_from_level467_selector, "
            "no_classical_choice_or_nat_find_from_existential, "
            "least_prefix_membership, least_maps_to_requested_nat, "
            "least_minimality_law, interval_preimage_selector_constructor, "
            "fixed_before_payoff, not_target_defined, no_post_payoff_search, "
            "no_least_label_only, no_minimal_label_only, "
            "no_bounded_search_label_only, no_packing_label_as_least_selector, "
            "no_selected_event_as_least_selector}."
        ),
    )
    ap.add_argument(
        "--support-index-first-hit-interval-preimage-selector-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-FIRST-HIT-INTERVAL-PREIMAGE-SELECTOR. "
            "Shape: {label, support_index_map, prefix_domain, "
            "same_support_index_same_prefix, owner_or_carrier_binding, "
            "base_at_zero, strict_order_on_prefix, first_hit_function, "
            "bounded_search_domain, candidate_predicate_exact, "
            "bounded_search_provenance, first_hit_success_certificate, "
            "success_not_from_interval_image_totality, "
            "success_not_from_level467_selector, "
            "success_not_from_level469_least_selector, "
            "no_classical_choice_or_nat_find_from_existential, "
            "first_hit_prefix_membership, first_hit_maps_to_requested_nat, "
            "no_prior_candidate_law, least_selector_constructor, "
            "fixed_before_payoff, not_target_defined, no_post_payoff_search, "
            "no_first_hit_label_only, no_bounded_search_label_only, "
            "no_packing_label_as_first_hit_selector, "
            "no_selected_event_as_first_hit_selector}."
        ),
    )
    ap.add_argument(
        "--support-index-vacuous-first-hit-adapter-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-VACUOUS-FIRST-HIT-ADAPTER. Shape: "
            "{label, support_index_map, prefix_domain, source_no_hole_receipt, "
            "skipped_slot_domain_empty_by_no_hole, no_hole_source_field, "
            "dummy_first_hit_function, first_hit_membership_from_false, "
            "first_hit_image_equality_from_false, no_prior_candidate_from_false, "
            "strict_source_constructor_chain, "
            "not_independent_bounded_search_certificate, "
            "not_new_source_mechanism, next_lever_returns_to_no_hole_geometry, "
            "no_level465_interval_image_import, no_level467_selector_import, "
            "no_level469_least_selector_import, no_classical_choice_or_nat_find, "
            "fixed_before_payoff, not_target_defined, "
            "no_packing_label_as_vacuity, no_selected_event_as_vacuity}."
        ),
    )
    ap.add_argument(
        "--finite-support-extraction-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-FINITE-SUPPORT-EXTRACTION. "
            "Shape: {label, finite_support_object, support_predicate, "
            "membership_equivalence, cardinality_length_alignment, "
            "enumeration_map, enumeration_totality, selected_membership_law, "
            "restricted_prefix_membership, fixed_before_payoff, "
            "not_target_defined, no_measure_only_extraction, no_label_only_packing}."
        ),
    )
    ap.add_argument(
        "--finite-image-support-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-FINITE-IMAGE-SUPPORT. Shape: "
            "{label, domain_finset, image_map, image_support_object, "
            "support_object_is_image, membership_iff_exists_domain, "
            "selected_membership_from_domain, totality_from_image_membership, "
            "injective_on_domain, card_image_eq_domain_card, "
            "domain_card_eq_length, restricted_prefix_on_image, "
            "fixed_before_payoff, not_target_defined, "
            "no_post_payoff_domain_pruning}."
        ),
    )
    ap.add_argument(
        "--no-rebilling-freshness-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-NO-REBILLING-FRESHNESS check. "
            "Shape: {label, selected_units, payment_atoms, assignment_map, "
            "assignment_total_on_prefix, distinctness_or_disjointness, "
            "no_rebilling_same_atom, prefix_budget_bound, fixed_before_payoff, "
            "same_owner_or_source, overlap_or_multiplicity_bound}."
        ),
    )
    ap.add_argument(
        "--same-carrier-packing-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-SAME-CARRIER-PACKING check. "
            "Shape: {label, source_carrier, target_payment_family, "
            "assignment_or_injection_map, assignment_total_on_prefix, "
            "same_carrier_binding, overlap_or_multiplicity_bound, "
            "finite_prefix_budget, pre_payoff_timing, no_nested_reuse, "
            "no_rebilling_same_atom}."
        ),
    )
    ap.add_argument(
        "--metric-covering-selection-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-METRIC-COVERING-SELECTION "
            "check. Shape: {label, ambient_metric_or_quasi_metric, "
            "source_family, scale_or_radius_function, "
            "doubling_or_besicovitch_constant, "
            "bounded_eccentricity_or_engulfing, selection_rule, "
            "selection_totality_or_paid_omission, "
            "pre_payoff_selection_timing, same_carrier_binding, "
            "bounded_overlap_conclusion, nested_children_policy, "
            "discarded_or_nested_error_budget}."
        ),
    )
    ap.add_argument(
        "--pde-analytic-substance-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-PDE-ANALYTIC-SUBSTANCE. "
            "Shape: {label, analytic_object, target_estimate, "
            "quantitative_inequality, norm_or_quantity, scale_or_localization, "
            "derivation_mechanism, constants_or_exponents, "
            "endpoint_or_limit_handling, hostile_packet_or_sharpness}."
        ),
    )
    ap.add_argument(
        "--theorem-applicability-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for deterministic theorem/profile "
            "applicability matching. Shape: {label, theorem, available}; "
            "theorem names a profile from the workbench theorem DB and "
            "available maps required/confuser field names to booleans."
        ),
    )
    ap.add_argument(
        "--pde-physical-accounting-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-PDE-PHYSICAL-ACCOUNTING. "
            "Shape: {physical_system, governing_law_or_balance, "
            "conserved_or_dissipated_quantity, quantity_dimensions, "
            "target_dimensions, scale_normalization, flux_or_boundary_terms, "
            "localization_region, carrier_or_material_volume, "
            "source_sink_or_forcing_terms, sign_or_positivity_structure, "
            "operator_or_projection_losses, cutoff_commutator_or_tail_terms, "
            "initial_boundary_data, hostile_physical_packet}."
        ),
    )
    ap.add_argument(
        "--pde-equality-provenance-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-PDE-EQUALITY-PROVENANCE. "
            "Shape: {equality_target, left_stream, right_stream, "
            "provenance_kind, constructor_or_theorem, generated_fields, "
            "source_binding, constructor_body_assignments, "
            "anti_proxy_or_anti_laundering_fields, hostile_packet_or_confuser, "
            "proof_boundary}."
        ),
    )
    ap.add_argument(
        "--pde-operator-admissibility-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-PDE-OPERATOR-ADMISSIBILITY. "
            "Shape: {operator_family, kernel_or_multiplier_model, "
            "input_output_norms, scale_or_bandlimit, localization_or_cutoff, "
            "carrier_identity, endpoint_handling, commutator_or_tail_payment, "
            "currency_target, hostile_packet_or_counterexample}."
        ),
    )
    ap.add_argument(
        "--pde-rigorous-numerics-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-PDE-RIGOROUS-NUMERICS. "
            "Shape: {certificate_type, pde_problem_statement, "
            "discretization_or_basis, interval_arithmetic_or_bounds, "
            "residual_bound, truncation_tail_bound, a_posteriori_argument, "
            "reproducibility_artifact, validator, theorem_linkage, "
            "hostile_packet_or_failure_mode}."
        ),
    )
    ap.add_argument(
        "--pde-hostile-witness-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-PDE-HOSTILE-WITNESS. "
            "Shape: {witness_family, target_estimate_or_claim, "
            "amplitude_scaling, support_or_localization, "
            "frequency_or_scale_regime, norm_or_quantity_profile, "
            "hypotheses_preserved, conclusion_stressed_or_violated, "
            "failure_mechanism, parameter_limit, claim_boundary_update}."
        ),
    )
    ap.add_argument(
        "--linear-observable-coercivity-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-LINEAR-OBS-COERCIVITY check. "
            "Shape: {label, target_dimension, observable_rank, receipts...}."
        ),
    )
    ap.add_argument(
        "--residual-normal-form-profile",
        type=Path,
        default=DEFAULT_RESIDUAL_NORMAL_FORM_PROFILE,
        help=(
            "JSON residual normal-form profile. Pass an empty string to disable."
        ),
    )
    ap.add_argument(
        "--single-spend-field",
        action="append",
        default=[],
        help=(
            "Field name or name:type pair for the RD single-spend carrier "
            "audit; repeatable."
        ),
    )
    ap.add_argument(
        "--single-spend-from-target",
        action="store_true",
        help=(
            "Also run the single-spend audit over fields extracted from the "
            "target declaration in the workmap or live Lean source."
        ),
    )
    ap.add_argument(
        "--owner-preimage-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a pec_k owner-preimage receipt. "
            "Each receipt should include owner_map, pre_payoff_timing, "
            "full_output_scale_owner, pointwise_payment, finite_atom_budget, "
            "multiplicity_bound, and owner_preimage_prefix_inequality."
        ),
    )
    ap.add_argument(
        "--scaled-transfer-numeric-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a scaled-transfer numeric receipt. "
            "Each receipt should include source_quantity, event_index_map, "
            "pointwise_numeric_statement, prop_to_numeric_bridge, consumed_by, "
            "and downstream_receipt."
        ),
    )
    ap.add_argument(
        "--owner-geometry-core-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a TICK668 owner-geometry-core "
            "receipt. Each receipt should include owner_map_timing, "
            "output_scale_owner, selected_prefix_preimage, "
            "bounded_projection_multiplicity, same_carrier_owner_budget, "
            "anti_laundering, and consumed_by."
        ),
    )
    ap.add_argument(
        "--fresh-annular-anti-laundering-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a fresh-annular anti-laundering "
            "receipt. Each receipt should include not_monotone_tail, "
            "not_scalar_measure, not_uniform_enstrophy_disguise, "
            "source_selection_not_declaration_only, same_separated_source, "
            "and consumed_by."
        ),
    )
    ap.add_argument(
        "--fresh-annular-non-disguise-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a fresh-annular non-disguise "
            "morphology receipt. Each receipt should include "
            "not_monotone_tail, not_scalar_measure, "
            "not_uniform_enstrophy_disguise, same_separated_source, "
            "and consumed_by."
        ),
    )
    ap.add_argument(
        "--fresh-annular-innovation-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a fresh-annular innovation "
            "anti-laundering receipt. Each receipt should include "
            "invoice_filtration, coarse_predictable_part, innovation_part, "
            "innovation_mass_lower_bound, same_source_binding, "
            "nondeclaration_binding, non_disguise_morphology_consequence, "
            "source_nondeclaration_timing_consequence, and consumed_by."
        ),
    )
    ap.add_argument(
        "--section-fixed-unsigned-variation-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a section-fixed unsigned "
            "variation receipt. Each receipt should include "
            "lower_envelope_uses_section, parent_crown_fixed_by_section, "
            "unshadowed_crown_fixed_by_section, "
            "child_shadow_crown_fixed_by_section, "
            "localized_unsigned_variation_measure, "
            "variation_measure_fixed_before_payoff, "
            "positive_variation_before_route_budget, "
            "no_parent_invoice_positive_part_selection, "
            "child_shadow_not_from_parent_deficit, "
            "unshadowed_mass_pays_production, "
            "child_shadow_mass_pays_inherited_reserve, "
            "same_event_stream_binding, and consumed_by."
        ),
    )
    ap.add_argument(
        "--limit-passage-step-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a limit-passage step. Each step "
            "should include name, sequence_described, inheritance_lemma, "
            "and property_inherited."
        ),
    )
    ap.add_argument(
        "--finite-prefix-results",
        action="store_true",
        help="Declare finite-prefix results that require a limit-passage check.",
    )
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument(
        "--semantic-mathlib-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "When the shape-tagged Mathlib shelf returns 0 hits, also query "
            "the gemini-embedding-001 Mathlib atlas for vocabulary-invariant "
            "neighbours. Additive fallback only; never replaces the tag-typed "
            "shelf. Atlas: scripts/public/lean/build_mathlib_atlas_embeddings.py. "
            "Default ON (post-2026-05-25 calibration); pass "
            "--no-semantic-mathlib-fallback to disable."
        ),
    )
    ap.add_argument(
        "--semantic-mathlib-threshold",
        type=float,
        default=0.55,
        help="Cosine threshold for the Mathlib semantic fallback (default 0.55).",
    )
    ap.add_argument(
        "--semantic-mathlib-top-k",
        type=int,
        default=8,
        help="Top-K hits to surface in the semantic fallback (default 8).",
    )
    ap.add_argument(
        "--semantic-mathlib-untagged-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Restrict the semantic fallback to lemmas with empty shape-tag "
            "lists (the 61%% of Mathlib entries the shape-tagged shelf cannot "
            "see). Default ON — cleanest information gain, disjoint from the "
            "tag-typed shelf. Pass --no-semantic-mathlib-untagged-only to "
            "query the full 46K atlas."
        ),
    )
    ap.add_argument(
        "--pde-formal-feedback",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Attach a PDE formal-feedback card built from LeanMill services "
            "(semantic premise shelf, own-ledger recall, domain atlases, and "
            "optional compiler/typed-exit payloads). Advisory only."
        ),
    )
    ap.add_argument(
        "--formal-feedback-statement",
        default="",
        help="Candidate Lean statement or theorem surface for the formal-feedback card.",
    )
    ap.add_argument(
        "--formal-feedback-context",
        default="",
        help="Extra informal/PDE context for LeanMill premise retrieval.",
    )
    ap.add_argument(
        "--formal-feedback-source-file",
        default="",
        help="Optional Lean source file whose imports are scanned for in-scope citation hits.",
    )
    ap.add_argument(
        "--formal-feedback-lean-root",
        default=str(LEAN_ROOT),
        help="Lean root used for in-scope citation lookup in the formal-feedback lane.",
    )
    ap.add_argument(
        "--formal-feedback-compile-result-json",
        default="",
        help="Optional JSON literal or path for a compiler result attached to formal feedback.",
    )
    ap.add_argument(
        "--formal-feedback-typed-exit-json",
        default="",
        help="Optional JSON literal or path for a LeanMill typed-exit payload attached to formal feedback.",
    )
    ap.add_argument(
        "--formal-feedback-threshold",
        type=float,
        default=0.55,
        help="Cosine threshold for LeanMill semantic premise retrieval.",
    )
    ap.add_argument(
        "--formal-feedback-mathlib-top-k",
        type=int,
        default=8,
        help="Mathlib hits to request in the formal-feedback lane.",
    )
    ap.add_argument(
        "--formal-feedback-domain-top-k",
        type=int,
        default=5,
        help="Domain-atlas hits to request in the formal-feedback lane.",
    )
    ap.add_argument(
        "--formal-feedback-own-top-k",
        type=int,
        default=4,
        help="Own-ledger hits to request in the formal-feedback lane.",
    )
    ap.add_argument(
        "--pde-leaf-work-order-op",
        default="",
        help=(
            "Optional GP-219 op id (for example pec_l) used to attach a "
            "registry-backed PDE leaf-agent work order to the pack."
        ),
    )
    ap.add_argument(
        "--pde-leaf-work-order-goal",
        default="",
        help="Optional goal text for the PDE leaf-agent work order.",
    )
    ap.add_argument(
        "--pde-leaf-given-json",
        default="",
        help="Optional JSON literal or path for the work-order `given` payload.",
    )
    ap.add_argument(
        "--pde-leaf-extra-gate",
        action="append",
        default=[],
        help="Additional PDE gate id to require in the work order; repeatable.",
    )
    ap.add_argument(
        "--pde-leaf-only-gate",
        action="append",
        default=[],
        help=(
            "Use only these PDE gate ids in the work order instead of all "
            "gates associated with --pde-leaf-work-order-op; repeatable."
        ),
    )
    ap.add_argument(
        "--pde-applicability-query",
        "--pde-theorem-query",
        dest="pde_applicability_query",
        default="",
        help=(
            "Optional PDE applicability-card retrieval query. Uses the "
            "project/app theorem-profile DB passed into the workbench. "
            "--pde-theorem-query is a compatibility alias."
        ),
    )
    ap.add_argument(
        "--pde-applicability-available-json",
        "--pde-theorem-available-json",
        dest="pde_applicability_available_json",
        default="",
        help="Optional JSON literal or path mapping PDE profile fields to availability.",
    )
    ap.add_argument(
        "--pde-applicability-top-k",
        "--pde-theorem-top-k",
        dest="pde_applicability_top_k",
        type=int,
        default=8,
        help="Number of applicability cards to attach when a query is set.",
    )
    ap.add_argument(
        "--pde-knowledge-context",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Attach the PDE kernel knowledge context: project theorem-profile "
            "cards plus read-only LeanMill proof-cache/no-good summaries. "
            "Semantic premise retrieval is off unless top-k flags are positive "
            "or source/lean-root is explicitly supplied."
        ),
    )
    ap.add_argument(
        "--pde-knowledge-query",
        default="",
        help="Optional retrieval query for the PDE knowledge context.",
    )
    ap.add_argument(
        "--pde-knowledge-statement",
        default="",
        help="Optional Lean/theorem statement used for LeanMill memory lookup.",
    )
    ap.add_argument(
        "--pde-knowledge-context-text",
        default="",
        help="Optional informal/PDE context for the knowledge service.",
    )
    ap.add_argument(
        "--pde-knowledge-source-file",
        default="",
        help="Optional Lean source file for explicit semantic/formal-feedback lookup.",
    )
    ap.add_argument(
        "--pde-knowledge-lean-root",
        default="",
        help=(
            "Optional Lean root for explicit semantic/formal-feedback lookup. "
            "Default empty avoids premise-shelf calls."
        ),
    )
    ap.add_argument(
        "--pde-knowledge-available-json",
        default="",
        help=(
            "Optional JSON literal or path mapping PDE theorem-profile fields "
            "to availability for knowledge-context applicability cards."
        ),
    )
    ap.add_argument(
        "--pde-knowledge-proof-cache-jsonl",
        default="",
        help="Optional LeanMill proof-cache JSONL path to inspect read-only.",
    )
    ap.add_argument(
        "--pde-knowledge-no-good-jsonl",
        default="",
        help="Optional LeanMill no-good/failure-memory JSONL path to inspect read-only.",
    )
    ap.add_argument(
        "--pde-knowledge-top-k-cards",
        type=int,
        default=8,
        help="Number of project theorem-profile cards for the knowledge context.",
    )
    ap.add_argument(
        "--pde-knowledge-mathlib-top-k",
        type=int,
        default=0,
        help="Semantic Mathlib premise hits. Default 0 avoids embedding calls.",
    )
    ap.add_argument(
        "--pde-knowledge-domain-top-k",
        type=int,
        default=0,
        help="Semantic domain-atlas premise hits. Default 0 avoids embedding calls.",
    )
    ap.add_argument(
        "--pde-knowledge-own-top-k",
        type=int,
        default=0,
        help="Semantic own-ledger premise hits. Default 0 avoids embedding calls.",
    )
    ap.add_argument(
        "--pde-formal-surface-json",
        action="append",
        default=[],
        help=(
            "Optional JSON literal/path for PDE formal-surface inventory rows. "
            "Accepts one row, a list of rows, or an object with records and "
            "required_primitives."
        ),
    )
    ap.add_argument(
        "--pde-formal-surface-required",
        action="append",
        default=[],
        help="Required primitive id expected in the formal-surface map; repeatable.",
    )
    ap.add_argument(
        "--pde-formal-surface-profile",
        default="ns_millennium_hunt",
        help="Source profile label for formal-surface rows loaded by this workbench.",
    )
    ap.add_argument(
        "--include-basin-context",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Include NS enriched-basin signals for the typed --target in the "
            "pack JSON: tag fingerprint, refutation edges, atlas-bridge "
            "open-obligation proximity. Default ON. Silently empty if the "
            "enriched basin file isn't built yet."
        ),
    )
    ap.add_argument(
        "--semantic-apn-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Query the AlphaProof Nexus (APN) corpus for cross-repo lemma "
            "matches. APN includes monotone-operator iterate-convergence "
            "machinery (Ryu-Yuan-Yin) directly applicable to NS Leray-Hopf "
            "sequence analysis. Default ON. Filtered to NS-relevant domains "
            "(optimization, additive_combinatorics, graphs)."
        ),
    )
    ap.add_argument(
        "--semantic-apn-threshold",
        type=float, default=0.55,
        help="Cosine threshold for APN bridges (default 0.55).",
    )
    ap.add_argument(
        "--semantic-apn-top-k",
        type=int, default=5,
        help="Top-K APN matches per target (default 5).",
    )
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = safe_slug(f"{args.target}_{args.field or 'target'}")
    out_root = args.out_dir if args.out_dir.is_absolute() else REPO / args.out_dir
    out_dir = out_root / f"{stamp}_{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)

    context = load_target_context(args.target, args.field)
    gap = classify_gap_local(args.target, args.field)
    gap_type = str(gap.get("gap_type") or "UNKNOWN")
    transforms = list(args.curriculum_transform)
    if args.emit_curriculum and not transforms:
        transforms = TRANSFORM_HINTS.get(gap_type, [])[:2]
    extra_allowed = set(str(x) for x in args.allowed_endpoint)
    if args.allowed_json:
        raw_allowed = _json_or_file(args.allowed_json)
        if not isinstance(raw_allowed, list):
            raise SystemExit("--allowed-json must be a JSON list or a path to one")
        extra_allowed.update(str(x) for x in raw_allowed)
    single_spend_fields = list(args.single_spend_field)
    single_spend_source = "manual"
    if args.single_spend_from_target:
        extracted = single_spend_fields_from_context(context)
        single_spend_fields.extend(extracted)
        single_spend_source = (
            "manual+target" if args.single_spend_field else "target"
        )
    owner_preimage_receipts = [
        _json_or_file(raw) for raw in args.owner_preimage_receipt_json
    ]
    for i, receipt in enumerate(owner_preimage_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                f"--owner-preimage-receipt-json entry {i} must be a JSON object"
            )
    scaled_transfer_numeric_receipts = [
        _json_or_file(raw) for raw in args.scaled_transfer_numeric_receipt_json
    ]
    for i, receipt in enumerate(scaled_transfer_numeric_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--scaled-transfer-numeric-receipt-json entry "
                f"{i} must be a JSON object"
            )
    owner_geometry_core_receipts = [
        _json_or_file(raw) for raw in args.owner_geometry_core_receipt_json
    ]
    for i, receipt in enumerate(owner_geometry_core_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--owner-geometry-core-receipt-json entry "
                f"{i} must be a JSON object"
            )
    fresh_annular_anti_laundering_receipts = [
        _json_or_file(raw)
        for raw in args.fresh_annular_anti_laundering_receipt_json
    ]
    for i, receipt in enumerate(fresh_annular_anti_laundering_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--fresh-annular-anti-laundering-receipt-json entry "
                f"{i} must be a JSON object"
            )
    fresh_annular_non_disguise_receipts = [
        _json_or_file(raw)
        for raw in args.fresh_annular_non_disguise_receipt_json
    ]
    for i, receipt in enumerate(fresh_annular_non_disguise_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--fresh-annular-non-disguise-receipt-json entry "
                f"{i} must be a JSON object"
            )
    fresh_annular_innovation_receipts = [
        _json_or_file(raw)
        for raw in args.fresh_annular_innovation_receipt_json
    ]
    for i, receipt in enumerate(fresh_annular_innovation_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--fresh-annular-innovation-receipt-json entry "
                f"{i} must be a JSON object"
            )
    section_fixed_unsigned_variation_receipts = [
        _json_or_file(raw)
        for raw in args.section_fixed_unsigned_variation_receipt_json
    ]
    for i, receipt in enumerate(section_fixed_unsigned_variation_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--section-fixed-unsigned-variation-receipt-json entry "
                f"{i} must be a JSON object"
            )
    limit_passage_steps = [
        _json_or_file(raw) for raw in args.limit_passage_step_json
    ]
    for i, step in enumerate(limit_passage_steps):
        if not isinstance(step, dict):
            raise SystemExit(
                f"--limit-passage-step-json entry {i} must be a JSON object"
            )
    pde_ops = suggest_pde_craft_ops(
        gap_type,
        args.target,
        args.field,
        args.candidate_inequality,
        context=context,
    )
    mathlib_lemmas = fetch_lemmas(gap_type, top=args.top_lemmas)
    mathlib_semantic_fallback: dict[str, Any] | None = None
    if args.semantic_mathlib_fallback and not mathlib_lemmas:
        # Additive fallback: only fires when the shape-tagged shelf returned
        # 0 hits. Preserves the 0-hit information signal in the main slot
        # while surfacing semantic neighbours in a clearly-labelled secondary
        # field.
        try:
            from ztare.research_director.mathlib_semantic import (
                mathlib_semantic_neighbours,
                MathlibSemanticHit,
            )
        except Exception as exc:
            mathlib_semantic_fallback = {
                "enabled": True,
                "fired": False,
                "skip_reason": f"mathlib_semantic import failed: {exc}",
                "hits": [],
            }
        else:
            rationale = (gap.get("rationale") or "") if isinstance(gap, dict) else ""
            query = " ".join(
                p for p in (args.target, args.field, gap_type, rationale) if p
            ).strip()
            hits, corpus_size, filtered_size, skip_reason = mathlib_semantic_neighbours(
                query,
                top_k=args.semantic_mathlib_top_k,
                threshold=args.semantic_mathlib_threshold,
                untagged_only=args.semantic_mathlib_untagged_only,
            )
            mathlib_semantic_fallback = {
                "enabled": True,
                "fired": skip_reason is None,
                "query": query,
                "threshold": args.semantic_mathlib_threshold,
                "top_k": args.semantic_mathlib_top_k,
                "untagged_only": args.semantic_mathlib_untagged_only,
                "corpus_size": corpus_size,
                "filtered_size": filtered_size,
                "skip_reason": skip_reason,
                "hits": [
                    {
                        "name": h.name,
                        "kind": h.kind,
                        "file": h.file,
                        "cosine": h.cosine,
                        "preview": h.preview,
                        "shapes": h.shapes,
                    }
                    for h in hits
                ],
                "note": (
                    "Additive fallback (shape-tagged shelf was empty for "
                    "this gap_type). Treat as candidate lemmas to verify, "
                    "NOT as a typed shelf — the 0-hit on the main shelf "
                    "still carries information."
                ),
            }
    basin_context = (
        _load_basin_context_for_target(args.target)
        if args.include_basin_context else None
    )
    pde_formal_surface_records: list[dict[str, Any]] = []
    pde_formal_surface_required = [
        str(item) for item in args.pde_formal_surface_required
        if str(item).strip()
    ]
    for i, raw_surface in enumerate(args.pde_formal_surface_json):
        surface_payload = _json_or_file(raw_surface)
        if isinstance(surface_payload, list):
            for j, row in enumerate(surface_payload):
                if not isinstance(row, dict):
                    raise SystemExit(
                        "--pde-formal-surface-json list entry "
                        f"{i}.{j} must be a JSON object"
                    )
                pde_formal_surface_records.append(row)
        elif isinstance(surface_payload, dict):
            records = surface_payload.get("records")
            if isinstance(records, list):
                for j, row in enumerate(records):
                    if not isinstance(row, dict):
                        raise SystemExit(
                            "--pde-formal-surface-json records entry "
                            f"{i}.{j} must be a JSON object"
                        )
                    pde_formal_surface_records.append(row)
                required = surface_payload.get("required_primitives")
                if isinstance(required, list):
                    pde_formal_surface_required.extend(
                        str(item) for item in required if str(item).strip()
                    )
            else:
                pde_formal_surface_records.append(surface_payload)
        else:
            raise SystemExit(
                f"--pde-formal-surface-json entry {i} must be an object or list"
            )
    from ztare.pde.engine import (
        PDEEngineContextRequest,
        PDEApplicabilityCardOptions,
        PDEEstimateSkeletonOptions,
        PDEFormalFeedbackOptions,
        PDEFormalSurfaceMapOptions,
        PDEKnowledgeServiceOptions,
        PDELeafWorkOrderOptions,
        build_pde_engine_context,
    )
    source_text = ""
    if args.pde_formal_feedback:
        if args.formal_feedback_source_file:
            source_path = Path(args.formal_feedback_source_file)
            if not source_path.is_absolute():
                source_path = REPO / source_path
            try:
                source_text = source_path.read_text(encoding="utf-8")
            except OSError as exc:
                source_text = f"-- source read failed: {exc}"
    knowledge_source_text = ""
    if args.pde_knowledge_context and args.pde_knowledge_source_file:
        knowledge_source_path = Path(args.pde_knowledge_source_file)
        if not knowledge_source_path.is_absolute():
            knowledge_source_path = REPO / knowledge_source_path
        try:
            knowledge_source_text = knowledge_source_path.read_text(encoding="utf-8")
        except OSError as exc:
            knowledge_source_text = f"-- source read failed: {exc}"
    pde_engine_context = build_pde_engine_context(
        PDEEngineContextRequest(
            target=args.target,
            formal_feedback=PDEFormalFeedbackOptions(
                enabled=bool(args.pde_formal_feedback),
                statement=args.formal_feedback_statement or "",
                context=args.formal_feedback_context or "",
                source=source_text,
                lean_root=args.formal_feedback_lean_root,
                compile_result=(
                    _json_or_file(args.formal_feedback_compile_result_json)
                    if args.formal_feedback_compile_result_json else None
                ),
                typed_exit=(
                    _json_or_file(args.formal_feedback_typed_exit_json)
                    if args.formal_feedback_typed_exit_json else None
                ),
                top_k_mathlib=args.formal_feedback_mathlib_top_k,
                top_k_domain=args.formal_feedback_domain_top_k,
                top_k_own=args.formal_feedback_own_top_k,
                threshold=args.formal_feedback_threshold,
            ),
            leaf_work_order=PDELeafWorkOrderOptions(
                op_id=args.pde_leaf_work_order_op,
                goal=args.pde_leaf_work_order_goal or args.target,
                given=(
                    _json_or_file(args.pde_leaf_given_json)
                    if args.pde_leaf_given_json else {}
                ),
                only_gate_ids=tuple(args.pde_leaf_only_gate),
                extra_gate_ids=tuple(args.pde_leaf_extra_gate),
            ),
            applicability_cards=PDEApplicabilityCardOptions(
                enabled=bool(args.pde_applicability_query),
                query=args.pde_applicability_query,
                available=(
                    _json_or_file(args.pde_applicability_available_json)
                    if args.pde_applicability_available_json else {}
                ),
                source_profile="ns_millennium_hunt",
                top_k=args.pde_applicability_top_k,
            ),
            knowledge_service=PDEKnowledgeServiceOptions(
                enabled=bool(args.pde_knowledge_context),
                query=args.pde_knowledge_query or args.pde_applicability_query or args.target,
                available=(
                    _json_or_file(args.pde_knowledge_available_json)
                    if args.pde_knowledge_available_json
                    else (
                        _json_or_file(args.pde_applicability_available_json)
                        if args.pde_applicability_available_json else {}
                    )
                ),
                source_profile="ns_millennium_hunt",
                statement=args.pde_knowledge_statement,
                context=args.pde_knowledge_context_text,
                source=knowledge_source_text,
                lean_root=args.pde_knowledge_lean_root or None,
                proof_cache_path=args.pde_knowledge_proof_cache_jsonl or None,
                no_good_store_path=args.pde_knowledge_no_good_jsonl or None,
                top_k_cards=args.pde_knowledge_top_k_cards,
                top_k_mathlib=args.pde_knowledge_mathlib_top_k,
                top_k_domain=args.pde_knowledge_domain_top_k,
                top_k_own=args.pde_knowledge_own_top_k,
            ),
            formal_surface_map=PDEFormalSurfaceMapOptions(
                records=tuple(pde_formal_surface_records),
                required_primitives=tuple(pde_formal_surface_required),
                source_profile=args.pde_formal_surface_profile,
            ),
            estimate_skeletons=PDEEstimateSkeletonOptions(
                enabled=True,
                field=args.field,
                gap_type=(
                    gap.get("gap_type") if isinstance(gap, dict) else None
                ) or "",
                context=context if isinstance(context, dict) else {},
                inequalities=tuple(args.candidate_inequality),
            ),
            target_currency=args.target_currency or args.target,
            theorem_db=NS_THEOREM_APPLICABILITY_DB,
        )
    )

    pack = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "target": args.target,
        "field": args.field,
        "tool_scope": (
            "RD caller over existing ZTARE primitives; not a second "
            "autoresearch loop or replacement workbench"
        ),
        "target_context": context,
        "gap_classification": gap,
        "source_currency_discriminator": classify_source_currency(
            args.target,
            args.field,
            args.target_currency,
            context.get("doc") if isinstance(context, dict) else None,
            gap.get("gap_type") if isinstance(gap, dict) else None,
            gap.get("rationale") if isinstance(gap, dict) else None,
        ),
        "mathlib_lemmas": mathlib_lemmas,
        "mathlib_semantic_fallback": mathlib_semantic_fallback,
        "basin_context": basin_context,
        "pde_engine_context": pde_engine_context,
        "pde_op_registry": pde_engine_context["op_registry"],
        "pde_currency_ledger": pde_engine_context["currency_ledger"],
        "pde_receipt_registry": pde_engine_context["receipt_registry"],
        "pde_engine_estimate_skeletons": pde_engine_context["estimate_skeletons"],
        "pde_gate_registry": pde_engine_context["gate_registry"],
        "pde_formal_feedback": pde_engine_context["formal_feedback"],
        "pde_formal_surface_map": pde_engine_context["formal_surface_map"],
        "pde_leaf_work_order": pde_engine_context["leaf_work_order"],
        "pde_applicability_cards": pde_engine_context["applicability_cards"],
        "pde_knowledge_context": pde_engine_context["knowledge_context"],
        "apn_semantic_neighbors": (
            _load_apn_semantic_for_target(
                args.target, args.field,
                context=context,
                gap=gap,
                basin_context=basin_context,
                pde_ops=pde_ops,
                candidate_inequalities=args.candidate_inequality,
                target_currency=args.target_currency,
                threshold=args.semantic_apn_threshold,
                top_k=args.semantic_apn_top_k,
            ) if args.semantic_apn_fallback else None
        ),
        "auxiliary_families": fetch_auxiliary_families(
            gap_type, keyword=args.aux_keyword, top=args.top_aux),
        "pde_craft_ops": pde_ops,
        "pde_execution_contract": (
            build_pde_execution_contract(
                pde_ops,
                min_work_units=args.min_work_units,
                hostile_suite=args.hostile_packet_suite,
                target_currency=args.target_currency,
            )
            if args.mode == "pde-execution"
            else None
        ),
        "estimate_skeletons": generate_pde_estimate_skeletons(
            target=args.target,
            field=args.field,
            gap_type=gap_type,
            context=context,
            inequalities=args.candidate_inequality,
        ),
        "residual_normal_form": run_residual_normal_form(
            None
            if str(args.residual_normal_form_profile) == ""
            else args.residual_normal_form_profile,
            args.target,
            args.field,
            args.candidate_inequality,
            context=context,
        ),
        "limit_passage_gate": run_limit_passage_audit(
            gap_type,
            limit_passage_steps,
            finite_prefix_results=args.finite_prefix_results,
        ),
        "moment_ratio_surplus_checks": run_moment_ratio_surplus_checks([
            _json_or_file(raw) for raw in args.moment_ratio_surplus_json
        ]),
        "bounded_ratio_support_checks": run_bounded_ratio_support_checks([
            _json_or_file(raw) for raw in args.bounded_ratio_support_json
        ]),
        "finite_prefix_selection_checks": run_finite_prefix_selection_checks([
            _json_or_file(raw) for raw in args.finite_prefix_selection_json
        ]),
        "event_family_binding_checks": run_event_family_binding_checks([
            _json_or_file(raw) for raw in args.event_family_binding_json
        ]),
        "analogical_transfer_receipt_checks": run_analogical_transfer_receipt_checks([
            _json_or_file(raw) for raw in args.analogical_transfer_receipt_json
        ]),
        "prefix_count_bridge_checks": run_prefix_count_bridge_checks([
            _json_or_file(raw) for raw in args.prefix_count_bridge_json
        ]),
        "source_prefix_budget_checks": run_source_prefix_budget_checks([
            _json_or_file(raw) for raw in args.source_prefix_budget_json
        ]),
        "final_slot_indexed_source_budget_checks":
            run_final_slot_indexed_source_budget_checks([
                _json_or_file(raw)
                for raw in args.final_slot_indexed_source_budget_json
            ]),
        "target_indexed_event_assignment_checks":
            run_target_indexed_event_assignment_checks([
                _json_or_file(raw)
                for raw in args.target_indexed_event_assignment_json
            ]),
        "incidence_derived_finite_injection_checks":
            run_incidence_derived_finite_injection_checks([
                _json_or_file(raw)
                for raw in args.incidence_derived_finite_injection_json
            ]),
        "bounded_incident_existence_eventdata_horizon_checks":
            run_bounded_incident_existence_eventdata_horizon_checks([
                _json_or_file(raw)
                for raw in args.bounded_incident_existence_eventdata_horizon_json
            ]),
        "target_event_candidate_cover_selection_checks":
            run_target_event_candidate_cover_selection_checks([
                _json_or_file(raw)
                for raw in args.target_event_candidate_cover_selection_json
            ]),
        "target_cover_eventdata_incidence_checks":
            run_target_cover_eventdata_incidence_checks([
                _json_or_file(raw)
                for raw in args.target_cover_eventdata_incidence_json
            ]),
        "cover_event_selector_finalslot_assignment_checks":
            run_cover_event_selector_finalslot_assignment_checks([
                _json_or_file(raw)
                for raw in args.cover_event_selector_finalslot_assignment_json
            ]),
        "target_slot_bounded_incidence_least_hit_checks":
            run_target_slot_bounded_incidence_least_hit_checks([
                _json_or_file(raw)
                for raw in args.target_slot_bounded_incidence_least_hit_json
            ]),
        "bounded_incident_existence_sametree_eventdata_index_checks":
            run_bounded_incident_existence_sametree_eventdata_index_checks([
                _json_or_file(raw)
                for raw in args.bounded_incident_existence_sametree_eventdata_index_json
            ]),
        "target_eventdata_index_prefix_cover_checks":
            run_target_eventdata_index_prefix_cover_checks([
                _json_or_file(raw)
                for raw in args.target_eventdata_index_prefix_cover_json
            ]),
        "finite_scale_cofinality_prefix_cover_checks":
            run_finite_scale_cofinality_prefix_cover_checks([
                _json_or_file(raw)
                for raw in args.finite_scale_cofinality_prefix_cover_json
            ]),
        "event_to_badnode_selected_index_checks":
            run_event_to_badnode_selected_index_checks([
                _json_or_file(raw)
                for raw in args.event_to_badnode_selected_index_json
            ]),
        "event_prefix_coverage_selected_index_checks":
            run_event_prefix_coverage_selected_index_checks([
                _json_or_file(raw)
                for raw in args.event_prefix_coverage_selected_index_json
            ]),
        "coverage_choice_finite_selector_checks":
            run_coverage_choice_finite_selector_checks([
                _json_or_file(raw)
                for raw in args.coverage_choice_finite_selector_json
            ]),
        "typed_appearance_coverage_choice_checks":
            run_typed_appearance_coverage_choice_checks([
                _json_or_file(raw)
                for raw in args.typed_appearance_coverage_choice_json
            ]),
        "typed_coverage_packet_appearance_checks":
            run_typed_coverage_packet_appearance_checks([
                _json_or_file(raw)
                for raw in args.typed_coverage_packet_appearance_json
            ]),
        "event_prefix_enumeration_packet_checks":
            run_event_prefix_enumeration_packet_checks([
                _json_or_file(raw)
                for raw in args.event_prefix_enumeration_packet_json
            ]),
        "bounded_natural_event_enumeration_checks":
            run_bounded_natural_event_enumeration_checks([
                _json_or_file(raw)
                for raw in args.bounded_natural_event_enumeration_json
            ]),
        "unbounded_event_witness_prefix_bound_checks":
            run_unbounded_event_witness_prefix_bound_checks([
                _json_or_file(raw)
                for raw in args.unbounded_event_witness_prefix_bound_json
            ]),
        "cofinal_incidence_witness_bound_checks":
            run_cofinal_incidence_witness_bound_checks([
                _json_or_file(raw)
                for raw in args.cofinal_incidence_witness_bound_json
            ]),
        "explicit_cofinal_event_witness_bound_checks":
            run_explicit_cofinal_event_witness_bound_checks([
                _json_or_file(raw)
                for raw in args.explicit_cofinal_event_witness_bound_json
            ]),
        "cofinal_event_selector_final_prefix_bound_checks":
            run_cofinal_event_selector_final_prefix_bound_checks([
                _json_or_file(raw)
                for raw in args.cofinal_event_selector_final_prefix_bound_json
            ]),
        "finite_cofinal_event_selector_checks":
            run_finite_cofinal_event_selector_checks([
                _json_or_file(raw)
                for raw in args.finite_cofinal_event_selector_json
            ]),
        "positive_variation_bridge_checks": run_positive_variation_bridge_checks([
            _json_or_file(raw) for raw in args.positive_variation_bridge_json
        ]),
        "positive_variation_quotient_wash_checks":
            run_positive_variation_quotient_wash_checks([
                _json_or_file(raw)
                for raw in args.positive_variation_quotient_wash_json
            ]),
        "quotient_minimal_carrier_payment_checks":
            run_quotient_minimal_carrier_payment_checks([
                _json_or_file(raw)
                for raw in args.quotient_minimal_carrier_payment_json
            ]),
        "quadratic_quotient_descent_checks":
            run_quadratic_quotient_descent_checks([
                _json_or_file(raw)
                for raw in args.quadratic_quotient_descent_json
            ]),
        "nonadaptive_source_selection_checks": run_nonadaptive_source_selection_checks([
            _json_or_file(raw) for raw in args.nonadaptive_source_selection_json
        ]),
        "support_index_law_checks": run_support_index_law_checks([
            _json_or_file(raw) for raw in args.support_index_law_json
        ]),
        "support_index_injectivity_checks": run_support_index_injectivity_checks([
            _json_or_file(raw) for raw in args.support_index_injectivity_json
        ]),
        "support_index_affine_order_checks": run_support_index_affine_order_checks([
            _json_or_file(raw) for raw in args.support_index_affine_order_json
        ]),
        "support_index_fixed_step_checks": run_support_index_fixed_step_checks([
            _json_or_file(raw) for raw in args.support_index_fixed_step_json
        ]),
        "support_index_adjacent_gap_checks": run_support_index_adjacent_gap_checks([
            _json_or_file(raw) for raw in args.support_index_adjacent_gap_json
        ]),
        "support_index_unit_gap_checks": run_support_index_unit_gap_checks([
            _json_or_file(raw) for raw in args.support_index_unit_gap_json
        ]),
        "support_index_no_hole_unit_gap_checks": run_support_index_no_hole_unit_gap_checks([
            _json_or_file(raw) for raw in args.support_index_no_hole_unit_gap_json
        ]),
        "support_index_endpoint_tight_no_hole_checks":
            run_support_index_endpoint_tight_no_hole_checks([
                _json_or_file(raw)
                for raw in args.support_index_endpoint_tight_no_hole_json
            ]),
        "support_index_base_anchored_strict_lower_bound_checks":
            run_support_index_base_anchored_strict_lower_bound_checks([
                _json_or_file(raw)
                for raw in args.support_index_base_anchored_strict_lower_bound_json
            ]),
        "support_index_final_endpoint_capacity_upper_bound_checks":
            run_support_index_final_endpoint_capacity_upper_bound_checks([
                _json_or_file(raw)
                for raw in args.support_index_final_endpoint_capacity_upper_bound_json
            ]),
        "support_index_final_slot_upper_bound_tail_capacity_checks":
            run_support_index_final_slot_upper_bound_tail_capacity_checks([
                _json_or_file(raw)
                for raw in args.support_index_final_slot_upper_bound_tail_capacity_json
            ]),
        "support_index_tail_capacity_failure_witness_checks":
            run_support_index_tail_capacity_failure_witness_checks([
                _json_or_file(raw)
                for raw in args.support_index_tail_capacity_failure_witness_json
            ]),
        "support_index_skipped_slot_hostile_witness_checks":
            run_support_index_skipped_slot_hostile_witness_checks([
                _json_or_file(raw)
                for raw in args.support_index_skipped_slot_hostile_witness_json
            ]),
        "support_index_interval_image_checks": run_support_index_interval_image_checks([
            _json_or_file(raw) for raw in args.support_index_interval_image_json
        ]),
        "support_index_interval_preimage_selector_checks": run_support_index_interval_preimage_selector_checks([
            _json_or_file(raw) for raw in args.support_index_interval_preimage_selector_json
        ]),
        "support_index_least_interval_preimage_selector_checks":
            run_support_index_least_interval_preimage_selector_checks([
                _json_or_file(raw)
                for raw in args.support_index_least_interval_preimage_selector_json
            ]),
        "support_index_first_hit_interval_preimage_selector_checks":
            run_support_index_first_hit_interval_preimage_selector_checks([
                _json_or_file(raw)
                for raw in args.support_index_first_hit_interval_preimage_selector_json
            ]),
        "support_index_vacuous_first_hit_adapter_checks":
            run_support_index_vacuous_first_hit_adapter_checks([
                _json_or_file(raw)
                for raw in args.support_index_vacuous_first_hit_adapter_json
            ]),
        "finite_support_extraction_checks": run_finite_support_extraction_checks([
            _json_or_file(raw) for raw in args.finite_support_extraction_json
        ]),
        "finite_image_support_checks": run_finite_image_support_checks([
            _json_or_file(raw) for raw in args.finite_image_support_json
        ]),
        "no_rebilling_freshness_checks": run_no_rebilling_freshness_checks([
            _json_or_file(raw) for raw in args.no_rebilling_freshness_json
        ]),
        "same_carrier_packing_checks": run_same_carrier_packing_checks([
            _json_or_file(raw) for raw in args.same_carrier_packing_json
        ]),
        "metric_covering_selection_checks": run_metric_covering_selection_checks([
            _json_or_file(raw) for raw in args.metric_covering_selection_json
        ]),
        "pde_analytic_substance_checks": run_pde_analytic_substance_checks([
            _json_or_file(raw) for raw in args.pde_analytic_substance_json
        ]),
        "pde_physical_accounting_checks": run_pde_physical_accounting_checks([
            _json_or_file(raw) for raw in args.pde_physical_accounting_json
        ]),
        "pde_equality_provenance_checks": run_pde_equality_provenance_checks([
            _json_or_file(raw) for raw in args.pde_equality_provenance_json
        ]),
        "pde_operator_admissibility_checks": run_pde_operator_admissibility_checks([
            _json_or_file(raw) for raw in args.pde_operator_admissibility_json
        ]),
        "pde_rigorous_numerics_checks": run_pde_rigorous_numerics_checks([
            _json_or_file(raw) for raw in args.pde_rigorous_numerics_json
        ]),
        "pde_hostile_witness_checks": run_pde_hostile_witness_checks([
            _json_or_file(raw) for raw in args.pde_hostile_witness_json
        ]),
        "theorem_applicability_checks": run_theorem_applicability_checks([
            _json_or_file(raw) for raw in args.theorem_applicability_json
        ], NS_THEOREM_APPLICABILITY_DB),
        "pi_group_checks": run_pi_group_checks([
            _json_or_file(raw) for raw in args.pi_group_json
        ]),
        "ambiguous_pi_pinning_checks": run_ambiguous_pi_pinning_checks([
            _json_or_file(raw) for raw in args.ambiguous_pi_pinning_json
        ]),
        "dimensionless_exponent_source_checks":
            run_dimensionless_exponent_source_checks([
                _json_or_file(raw)
                for raw in args.dimensionless_exponent_source_json
            ]),
        "persistence_budget_exponent_checks":
            run_persistence_budget_exponent_checks([
                _json_or_file(raw)
                for raw in args.persistence_budget_exponent_json
            ]),
        "linear_observable_coercivity_checks":
            run_linear_observable_coercivity_checks([
                _json_or_file(raw)
                for raw in args.linear_observable_coercivity_json
            ]),
        "single_spend_audit": run_single_spend_audit(single_spend_fields),
        "single_spend_source": single_spend_source,
        "receipt_strength_audit": run_receipt_strength_audit_from_fields(
            single_spend_fields
        ),
        "owner_preimage_prefix_gate": run_owner_preimage_prefix_audit(
            pde_ops,
            owner_preimage_receipts,
        ),
        "scaled_transfer_numeric_receipt_gate":
            run_scaled_transfer_numeric_audit(
                args.target,
                args.field,
                context,
                scaled_transfer_numeric_receipts,
            ),
        "owner_geometry_core_receipt_gate":
            run_owner_geometry_core_audit(
                args.target,
                args.field,
                context,
                owner_geometry_core_receipts,
            ),
        "fresh_annular_anti_laundering_gate":
            run_fresh_annular_anti_laundering_audit(
                args.target,
                args.field,
                context,
                fresh_annular_anti_laundering_receipts,
            ),
        "fresh_annular_non_disguise_gate":
            run_fresh_annular_non_disguise_audit(
                args.target,
                args.field,
                context,
                fresh_annular_non_disguise_receipts,
            ),
        "fresh_annular_innovation_gate":
            run_fresh_annular_innovation_audit(
                args.target,
                args.field,
                context,
                fresh_annular_innovation_receipts,
            ),
        "section_fixed_unsigned_variation_gate":
            run_section_fixed_unsigned_variation_audit(
                args.target,
                args.field,
                context,
                section_fixed_unsigned_variation_receipts,
            ),
        "inequality_checks": check_inequalities(
            args.candidate_inequality,
            context,
            args.dimensional_features_json,
            extra_allowed=extra_allowed,
        ),
        "curriculum_variants": emit_curriculum_variants(
            args.target, transforms, out_dir) if args.emit_curriculum else [],
        "next_step_rule": (
            "Codex chooses a patch/falsifier route. Feed only verified snippets "
            "or summarized failure categories back into ZTARE briefing memory."
        ),
    }
    json_path = out_dir / "pack.json"
    md_path = out_dir / "pack.md"
    json_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(pack), encoding="utf-8")
    try:
        json_display = json_path.relative_to(REPO)
    except ValueError:
        json_display = json_path
    try:
        md_display = md_path.relative_to(REPO)
    except ValueError:
        md_display = md_path
    print(f"wrote: {json_display}")
    print(f"wrote: {md_display}")
    print(f"gap_type: {gap_type}")
    print(
        "source_currency_class: "
        f"{pack['source_currency_discriminator']['source_currency_class']}"
    )
    print(f"mathlib_lemmas: {len(pack['mathlib_lemmas'])}")
    print(f"auxiliary_families: {len(pack['auxiliary_families'])}")
    print(f"pde_craft_ops: {len(pack['pde_craft_ops'])}")
    print(f"estimate_skeletons: {len(pack['estimate_skeletons'])}")
    print(f"pde_execution_contract: {bool(pack.get('pde_execution_contract'))}")
    print(f"residual_normal_form: {bool(pack.get('residual_normal_form'))}")
    print(f"limit_passage_gate: {bool(pack.get('limit_passage_gate'))}")
    print(
        "moment_ratio_surplus_checks: "
        f"{len(pack['moment_ratio_surplus_checks'])}"
    )
    print(
        "bounded_ratio_support_checks: "
        f"{len(pack['bounded_ratio_support_checks'])}"
    )
    print(
        "finite_prefix_selection_checks: "
        f"{len(pack['finite_prefix_selection_checks'])}"
    )
    print(
        "event_family_binding_checks: "
        f"{len(pack['event_family_binding_checks'])}"
    )
    print(
        "analogical_transfer_receipt_checks: "
        f"{len(pack['analogical_transfer_receipt_checks'])}"
    )
    print(
        "prefix_count_bridge_checks: "
        f"{len(pack['prefix_count_bridge_checks'])}"
    )
    print(
        "source_prefix_budget_checks: "
        f"{len(pack['source_prefix_budget_checks'])}"
    )
    print(
        "final_slot_indexed_source_budget_checks: "
        f"{len(pack['final_slot_indexed_source_budget_checks'])}"
    )
    print(
        "target_indexed_event_assignment_checks: "
        f"{len(pack['target_indexed_event_assignment_checks'])}"
    )
    print(
        "incidence_derived_finite_injection_checks: "
        f"{len(pack['incidence_derived_finite_injection_checks'])}"
    )
    print(
        "bounded_incident_existence_eventdata_horizon_checks: "
        f"{len(pack['bounded_incident_existence_eventdata_horizon_checks'])}"
    )
    print(
        "target_event_candidate_cover_selection_checks: "
        f"{len(pack['target_event_candidate_cover_selection_checks'])}"
    )
    print(
        "target_cover_eventdata_incidence_checks: "
        f"{len(pack['target_cover_eventdata_incidence_checks'])}"
    )
    print(
        "cover_event_selector_finalslot_assignment_checks: "
        f"{len(pack['cover_event_selector_finalslot_assignment_checks'])}"
    )
    print(
        "target_slot_bounded_incidence_least_hit_checks: "
        f"{len(pack['target_slot_bounded_incidence_least_hit_checks'])}"
    )
    print(
        "bounded_incident_existence_sametree_eventdata_index_checks: "
        f"{len(pack['bounded_incident_existence_sametree_eventdata_index_checks'])}"
    )
    print(
        "target_eventdata_index_prefix_cover_checks: "
        f"{len(pack['target_eventdata_index_prefix_cover_checks'])}"
    )
    print(
        "finite_scale_cofinality_prefix_cover_checks: "
        f"{len(pack['finite_scale_cofinality_prefix_cover_checks'])}"
    )
    print(
        "event_to_badnode_selected_index_checks: "
        f"{len(pack['event_to_badnode_selected_index_checks'])}"
    )
    print(
        "event_prefix_coverage_selected_index_checks: "
        f"{len(pack['event_prefix_coverage_selected_index_checks'])}"
    )
    print(
        "coverage_choice_finite_selector_checks: "
        f"{len(pack['coverage_choice_finite_selector_checks'])}"
    )
    print(
        "typed_appearance_coverage_choice_checks: "
        f"{len(pack['typed_appearance_coverage_choice_checks'])}"
    )
    print(
        "typed_coverage_packet_appearance_checks: "
        f"{len(pack['typed_coverage_packet_appearance_checks'])}"
    )
    print(
        "event_prefix_enumeration_packet_checks: "
        f"{len(pack['event_prefix_enumeration_packet_checks'])}"
    )
    print(
        "bounded_natural_event_enumeration_checks: "
        f"{len(pack['bounded_natural_event_enumeration_checks'])}"
    )
    print(
        "unbounded_event_witness_prefix_bound_checks: "
        f"{len(pack['unbounded_event_witness_prefix_bound_checks'])}"
    )
    print(
        "cofinal_incidence_witness_bound_checks: "
        f"{len(pack['cofinal_incidence_witness_bound_checks'])}"
    )
    print(
        "explicit_cofinal_event_witness_bound_checks: "
        f"{len(pack['explicit_cofinal_event_witness_bound_checks'])}"
    )
    print(
        "cofinal_event_selector_final_prefix_bound_checks: "
        f"{len(pack['cofinal_event_selector_final_prefix_bound_checks'])}"
    )
    print(
        "finite_cofinal_event_selector_checks: "
        f"{len(pack['finite_cofinal_event_selector_checks'])}"
    )
    print(
        "positive_variation_bridge_checks: "
        f"{len(pack['positive_variation_bridge_checks'])}"
    )
    print(
        "positive_variation_quotient_wash_checks: "
        f"{len(pack['positive_variation_quotient_wash_checks'])}"
    )
    print(
        "quotient_minimal_carrier_payment_checks: "
        f"{len(pack['quotient_minimal_carrier_payment_checks'])}"
    )
    print(
        "quadratic_quotient_descent_checks: "
        f"{len(pack['quadratic_quotient_descent_checks'])}"
    )
    print(
        "nonadaptive_source_selection_checks: "
        f"{len(pack['nonadaptive_source_selection_checks'])}"
    )
    print(
        "support_index_law_checks: "
        f"{len(pack['support_index_law_checks'])}"
    )
    print(
        "support_index_injectivity_checks: "
        f"{len(pack['support_index_injectivity_checks'])}"
    )
    print(
        "support_index_affine_order_checks: "
        f"{len(pack['support_index_affine_order_checks'])}"
    )
    print(
        "support_index_fixed_step_checks: "
        f"{len(pack['support_index_fixed_step_checks'])}"
    )
    print(
        "support_index_adjacent_gap_checks: "
        f"{len(pack['support_index_adjacent_gap_checks'])}"
    )
    print(
        "support_index_unit_gap_checks: "
        f"{len(pack['support_index_unit_gap_checks'])}"
    )
    print(
        "support_index_no_hole_unit_gap_checks: "
        f"{len(pack['support_index_no_hole_unit_gap_checks'])}"
    )
    print(
        "support_index_endpoint_tight_no_hole_checks: "
        f"{len(pack['support_index_endpoint_tight_no_hole_checks'])}"
    )
    print(
        "support_index_base_anchored_strict_lower_bound_checks: "
        f"{len(pack['support_index_base_anchored_strict_lower_bound_checks'])}"
    )
    print(
        "support_index_final_endpoint_capacity_upper_bound_checks: "
        f"{len(pack['support_index_final_endpoint_capacity_upper_bound_checks'])}"
    )
    print(
        "support_index_final_slot_upper_bound_tail_capacity_checks: "
        f"{len(pack['support_index_final_slot_upper_bound_tail_capacity_checks'])}"
    )
    print(
        "support_index_tail_capacity_failure_witness_checks: "
        f"{len(pack['support_index_tail_capacity_failure_witness_checks'])}"
    )
    print(
        "support_index_skipped_slot_hostile_witness_checks: "
        f"{len(pack['support_index_skipped_slot_hostile_witness_checks'])}"
    )
    print(
        "support_index_interval_image_checks: "
        f"{len(pack['support_index_interval_image_checks'])}"
    )
    print(
        "support_index_interval_preimage_selector_checks: "
        f"{len(pack['support_index_interval_preimage_selector_checks'])}"
    )
    print(
        "support_index_least_interval_preimage_selector_checks: "
        f"{len(pack['support_index_least_interval_preimage_selector_checks'])}"
    )
    print(
        "support_index_first_hit_interval_preimage_selector_checks: "
        f"{len(pack['support_index_first_hit_interval_preimage_selector_checks'])}"
    )
    print(
        "support_index_vacuous_first_hit_adapter_checks: "
        f"{len(pack['support_index_vacuous_first_hit_adapter_checks'])}"
    )
    print(
        "finite_support_extraction_checks: "
        f"{len(pack['finite_support_extraction_checks'])}"
    )
    print(
        "finite_image_support_checks: "
        f"{len(pack['finite_image_support_checks'])}"
    )
    print(
        "no_rebilling_freshness_checks: "
        f"{len(pack['no_rebilling_freshness_checks'])}"
    )
    print(
        "same_carrier_packing_checks: "
        f"{len(pack['same_carrier_packing_checks'])}"
    )
    print(
        "metric_covering_selection_checks: "
        f"{len(pack['metric_covering_selection_checks'])}"
    )
    print(
        "pde_analytic_substance_checks: "
        f"{len(pack['pde_analytic_substance_checks'])}"
    )
    print(
        "pde_physical_accounting_checks: "
        f"{len(pack['pde_physical_accounting_checks'])}"
    )
    print(
        "pde_equality_provenance_checks: "
        f"{len(pack['pde_equality_provenance_checks'])}"
    )
    print(
        "pde_operator_admissibility_checks: "
        f"{len(pack['pde_operator_admissibility_checks'])}"
    )
    print(
        "pde_rigorous_numerics_checks: "
        f"{len(pack['pde_rigorous_numerics_checks'])}"
    )
    print(
        "pde_hostile_witness_checks: "
        f"{len(pack['pde_hostile_witness_checks'])}"
    )
    print(
        "theorem_applicability_checks: "
        f"{len(pack['theorem_applicability_checks'])}"
    )
    print(f"pi_group_checks: {len(pack['pi_group_checks'])}")
    print(
        "ambiguous_pi_pinning_checks: "
        f"{len(pack['ambiguous_pi_pinning_checks'])}"
    )
    print(
        "dimensionless_exponent_source_checks: "
        f"{len(pack["dimensionless_exponent_source_checks"])}"
    )
    print(
        "persistence_budget_exponent_checks: "
        f"{len(pack['persistence_budget_exponent_checks'])}"
    )
    print(
        "linear_observable_coercivity_checks: "
        f"{len(pack['linear_observable_coercivity_checks'])}"
    )
    print(f"single_spend_audit: {bool(pack['single_spend_audit'])}")
    print(f"receipt_strength_audit: {bool(pack['receipt_strength_audit'])}")
    print(
        "scaled_transfer_numeric_receipt_gate: "
        f"{bool(pack.get('scaled_transfer_numeric_receipt_gate'))}"
    )
    print(
        "owner_geometry_core_receipt_gate: "
        f"{bool(pack.get('owner_geometry_core_receipt_gate'))}"
    )
    print(
        "fresh_annular_anti_laundering_gate: "
        f"{bool(pack.get('fresh_annular_anti_laundering_gate'))}"
    )
    print(
        "fresh_annular_innovation_gate: "
        f"{bool(pack.get('fresh_annular_innovation_gate'))}"
    )
    print(
        "section_fixed_unsigned_variation_gate: "
        f"{bool(pack.get('section_fixed_unsigned_variation_gate'))}"
    )
    print(f"inequality_checks: {len(pack['inequality_checks'])}")
    print(f"curriculum_variants: {len(pack['curriculum_variants'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
