"""Primitive scientific-amnesia precheck — surface EXTRACTED CAPABILITIES for a task.

Recurring failure (operator-flagged ≥2×): an agent reinvents or, worse, IGNORES a
primitive that already exists in the codebase (Jaccard, information-yield, the
experiment-stats family, proof-state, …) because the existing tick-surface
(`primitive_tick_surface.py` → `architecture_index.jsonl`) indexes gates/miners/
reflexive-primitives but NOT the broad library of extracted analytical/utility
primitives — only 3 of ~249 index rows reference them.

This closes that gap: given a task description, it surfaces the relevant extracted
primitives (module + signature + when-to-use), so reuse is the default instead of
amnesia. It REUSES `scientific_amnesia.tokenize/_score` (the same deterministic,
source-pointing scorer NS uses on Lean evidence) — not a reimplementation — and
blends the semantic atlas when an embedder is available (vocabulary-invariant, so
"set overlap" finds "Jaccard" even with no shared tokens).

Substrate-agnostic kernel logic. CLI:
  python -m ztare.research_director.primitive_amnesia "<task description>" [--top-k 8]
  python -m ztare.research_director.primitive_amnesia --selftest
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

from ztare.research_director.primitive_catalog_taxonomy import (
    enrich_row,
    source_category_for_path,
)
from ztare.research_director.scientific_amnesia import tokenize, _score

REPO = Path(__file__).resolve().parents[3]
ARCH_INDEX = REPO / "analytics" / "public" / "index" / "architecture_index.jsonl"
ATLAS_PATH = REPO / "analytics" / "public" / "index" / "primitive_atlas_embeddings.json"
MISS_QUEUE_PATH = REPO / "analytics" / "public" / "queries" / "primitive_amnesia_miss_queue.jsonl"
_LAST_EMBED_ERROR: str | None = None

_EMBEDDING_DIMENSIONS = {
    "gemini-code": 768,
    "gemini": 768,
    "openai": 1024,
}


def _expected_embedding_dimension(backend: str) -> int | None:
    return _EMBEDDING_DIMENSIONS.get(backend)


def _valid_embedding_vector(vector: object, *, backend: str = "") -> bool:
    if (
        not isinstance(vector, list)
        or not vector
        or not all(isinstance(value, (int, float)) for value in vector)
    ):
        return False
    expected_dimension = _expected_embedding_dimension(backend)
    return expected_dimension is None or len(vector) == expected_dimension


def _category_for(path: str) -> str:
    return source_category_for_path(path)

# The EXTRACTED-CAPABILITY surface: curated modules holding reusable analytical /
# utility primitives that the architecture_index does NOT cover. Add a module here
# when it ships a reusable primitive (the one maintenance point).
# The EXTRACTED-CAPABILITY surface. Curated MODULES + DIRECTORIES whose public
# functions/classes are reusable analytical / utility / operator primitives.
# `populate_catalog` registers EVERY public primitive from these (completeness),
# so the catalog isn't missing capabilities; the WHEN_TO_USE aliases + impact rank
# keep the high-value ones on top in the surface.
PRIMITIVE_MODULES = [
    "src/ztare/experiment_stats.py",
    "src/ztare/validator/core/information_yield.py",
    "src/ztare/motion/set_distance.py",
    "src/ztare/leanmill/solver/proof_state.py",
    "src/ztare/leanmill/solver/statement_extract.py",
    "src/ztare/fit/primitive_library.py",
    "src/ztare/framer/primitives.py",
    "src/ztare/product_exports/judgment_primitives.py",
    "src/ztare/research_director/problem_solving_ops.py",
    "src/ztare/research_director/theory_building_ops.py",
    "src/ztare/research_director/graph_carrier_actions.py",
    "src/ztare/leanmill/semantic_premise_shelf.py",
    "src/ztare/leanmill/theory_interpretation.py",  # evidence-bound key idea + isomorphism projection
    "src/ztare/leanmill/theory_conflict_ledger.py",  # witness-replayed theory-search failure memory
    "src/ztare/common/constraint_isomorphism.py",  # strange loop (common/ not auto-swept)
    "src/ztare/common/factored_search.py",         # consumer-indexed projected search
    "src/ztare/common/graph_carrier.py",           # graph diagnostic carrier schema/receipt guard
    "src/ztare/workspace/source_freshness.py",     # source-bound artifact freshness / stale-provenance guard
    "src/ztare/forecasting/prediction_contract.py",  # neutral forecast/prediction contract read model
    "src/ztare/reports/forecast_capability_audit.py",  # forecast lifecycle / scratch / decision-use audit
    "src/ztare/validator/autoresearch_prediction_contract.py",  # in-loop adapter over neutral prediction contracts
    "src/ztare/validator/probability_dag_carrier.py",  # autoresearch probability-DAG scoring/carriers
    "src/ztare/validator/source_claim_graph_carrier.py",  # source/evidence/gap graph carriers
    "src/ztare/workspace/evidence_gaps.py",  # public evidence vs local verifier gap routing
    "src/ztare/common/sandboxed_python.py",          # the ONE sandboxed-python exec home (2026-06-07)
    "src/ztare/common/symbolic_witness.py",          # SymPy witness/recurrence/linear-system builders
    "src/ztare/fit/analogy.py",                      # GP-164 curve-fit analogy (the specialization)
    "src/ztare/gates/pde_physical_accounting_gate.py",  # PDE physical balance/dimension/flux invoice gate
    "src/ztare/gates/pde_equality_provenance_gate.py",  # PDE equality provenance / anti-laundering gate
    "src/ztare/gates/pde_operator_admissibility_gate.py",  # singular-integral/CZ/Riesz payment gate
    "src/ztare/gates/pde_rigorous_numerics_certificate_gate.py",  # interval/residual/tail certificate gate
    "src/ztare/gates/pde_hostile_witness_gate.py",   # pec_e hostile/sharpness witness receipt gate
]
# Directories swept for additional primitive-bearing modules (every public def/class).
PRIMITIVE_DIRS = [
    "src/ztare/research_director",   # *_ops.py operators, generators, surfaces
    "src/ztare/validator/core",      # information yield, scoring cores
    "src/ztare/motion",              # set/vector distances, motion metrics
    "src/ztare/fit",                 # fit primitives, regime combinators
    "src/ztare/pde",                 # PDE-engine facade, gate runner, leaf dispatch
    "src/ztare/leanmill/solver",     # proof-state, statement-extract, contract
]


# EFFECT-vocabulary aliases for primitives whose name/doc vocabulary diverges from
# how a TASK is phrased (the lexical gap the selftest exposed: "diversity/overlap"
# never matches a doc that says "Jaccard distance between sets"). Low-toil, high-value:
# only the primitives whose NAME != its USE-CASE words. This is also the "when to use"
# guidance the precheck surfaces. (Un-aliased primitives still match via doc / --semantic.)
WHEN_TO_USE = {
    "jaccard_distance": "set overlap similarity diversity redundancy complementarity shared distinct coverage union ensemble",
    "evaluate_information_yield": "stop iterating loop stagnation non-informative no new information convergence when to stop wasted",
    "IterationSignal": "stop iterating loop stagnation non-informative convergence repeated identical",
    "proof_state_signal": "partial progress gradient remaining goals proof state how close stuck best-first ranking",
    "extract_unsolved_goals": "residual goal remaining open continue stepwise what is left to prove",
    "n_required_for_rho": "statistical power sample size underpowered how many needed detectability correlation",
    "detectable_rho_at_n": "statistical power sample size underpowered detectability correlation at n",
    "power_aware_verdict": "underpowered inconclusive h0 h1 verdict power three outcomes",
    "bf_bic_paired_t": "model comparison bayes factor BIC paired conditions evidence ratio",
    "bootstrap_ci": "confidence interval uncertainty resample bootstrap error bars",
    "paired_permutation_test": "significance A/B comparison paired permutation sign-flip p-value",
    "tost_equivalence": "equivalence no difference indistinguishable two one-sided",
    "build_ablation_layers": "ablation inject premises helpers frontier distance how far above how much help",
    "build_semantic_premise_shelf": "lean proof mathlib semantic premise retrieval shelf candidate lemmas theorem search missing API exact lemma source context before proof attempt",
    "spearman_rho": "rank correlation monotone association ordinal",
    "IsomorphismLoop": "stuck structural ceiling blocked after many attempts find a theorem from another field cross-field isomorphism analogy orthogonal jump self-prompt next idea Barrington abstract the failure to pure math constraint surface established theorem that solves it transport structure when no progress what would unblock",
    "default_llm_query": "cross-field theorem search structural isomorphism query strip domain gravity name theorems that solve this abstract constraint orthogonal jump",
    "surface_for_research_ceiling": "research director stuck seam find a field where this seam is already solved transport structure cross-field isomorphism deanchor next idea abstract the frontier to operator seam leanmill architecture ceiling next Barrington",
    "build_pde_formal_feedback_card": "PDE leaf agent LeanMill theorem retrieval formal feedback semantic premise shelf compiler typed exit formal surface adapter proof obligation before Lean edit",
    "render_pde_formal_feedback_card": "PDE formal feedback card render LeanMill premise shelf compiler typed exit formalization next leaf summary",
    "PDEApplicabilityCard": "PDE applicability card profile obligation theorem profile missing fields rejected substitutes confuser applicability not lemma bank",
    "applicability_card_retrieval": "PDE applicability card retrieval theorem profile obligations missing fields rejected substitutes confuser not LeanMill premise shelf",
    "render_applicability_cards": "PDE applicability cards render profile obligations missing fields rejected substitutes workbench pack",
    "run_pde_physical_accounting_gate": "PDE physical accounting conservation balance law dimensions dimensional homogeneity flux boundary source sink localization carrier sign positivity operator projection cutoff tail hostile physical packet",
    "run_pde_equality_provenance_gate": "PDE equality provenance anti laundering record field projection assumed equality source binding constructor body assignments same stream target charge tracefree valuation proxy stream",
    "run_pde_operator_admissibility_gate": "PDE singular integral operator admissibility CZ Riesz Fourier multiplier kernel bandlimit cutoff carrier endpoint commutator tail payment",
    "run_pde_rigorous_numerics_certificate_gate": "PDE rigorous numerics certificate validated interval arithmetic residual bound truncation tail bound a posteriori theorem linkage reproducibility validator",
    "run_pde_hostile_witness_gate": "PDE hostile witness sharpness counterexample falsifier packet amplitude scaling support frequency hypotheses preserved conclusion stressed claim boundary update",
    "run_pde_gate": "PDE subkernel execute one registry gate stable gate id payload theorem applicability operator admissibility hostile witness",
    "run_pde_leaf_work_order_gates": "PDE subkernel execute all gate payloads for leaf work order normalized gate result envelope missing fields rejected substitutes",
    "PDEFormalSurfaceRecord": "PDE formal surface inventory status primitive Lean statement proof complete external citation numerical certificate missing evidence no proof credit",
    "normalize_pde_formal_surface_record": "PDE formal surface inventory normalize primitive status Lean statement proof citation numerical certificate missing evidence",
    "build_pde_formal_surface_map": "PDE formal surface map build status inventory required primitives Lean proof complete informal only external citation numerical certificate routing",
    "render_pde_formal_surface_map": "PDE formal surface map render status inventory missing evidence required primitives workbench pack",
    "PDELeafWorkOrder": "PDE leaf agent work order schema atomic task dispatch GP219 pec op gate requirements must return theorem retrieval estimate hostile packet formalization",
    "build_pde_leaf_work_order": "PDE leaf agent work order build atomic task dispatch GP219 pec op registry backed gates theorem retrieval estimate hostile packet formalization",
    "render_pde_leaf_work_order": "PDE leaf work order render dispatch prompt gate requirements must return GP219 pec op estimate theorem formalization task",
    "all_pde_gate_entries": "PDE gate registry list all gates workbench flags plugin boundary leaf agent work order GP219 pec ops",
    "entries_for_op": "PDE gate registry find gates for GP219 pec op leaf agent work order theorem applicability analytic substance same carrier coercivity",
    "entry_by_gate_id": "PDE gate registry stable gate id lookup workbench flag runner renderer section tags plugin boundary",
    "build_pde_subkernel_status": "PDE subkernel readiness status gate registry runner imports service boundaries LeanMill formal feedback project app separation",
    "score_research_avenue": "research route rank avenue MDL information yield per complexity amnesia penalty source currency next lever what to pursue",
    "score_research_avenues": "portfolio rank research avenues MDL information yield density amnesia recurrence source currency proof route priority",
    "ResearchAvenue": "candidate research route avenue receipts kill conditions expected reuse exposure amnesia hits novelty hints MDL score",
    "canonical_graph_kind_specs": "graph carrier registry context graph probability DAG primitive capability graph constraint basin source claim code dependency graph registered graph kinds",
    "validate_graph_carrier": "graph carrier schema receipt provenance diagnostics baseline noise filter decision effect strategy change no strategy change misleading graph metric route selection",
    "artifact_source_freshness": "source provenance freshness compare current raw source preflight rows to source index compiled evidence provenance stale count-only missing hash unverified kernel entry graph carrier",
    "raw_relative_path": "normalize source artifact path project raw relative absolute repo-relative raw directory compiled evidence source index provenance",
    "score_probability_dag_nodes": "autoresearch probability DAG steering score nodes urgency edge weight probability highest urgency watch signal graph diagnostic",
    "render_probability_dag_vulnerability_prompt": "autoresearch probability DAG prompt vulnerable assumptions weakest nodes thesis mutation watch signal",
    "build_probability_dag_graph_carrier": "autoresearch probability DAG graph carrier receipt latest_probability_dag dag steering log decision receipt trace",
    "summarize_probability_dag_graph_carrier": "autoresearch trace graph carrier compact summary decision receipt validation",
    "build_source_claim_graph_carrier": "autoresearch source claim graph carrier evidence provenance source index compiled evidence gaps recovery action decision receipt",
    "summarize_source_claim_graph_carrier": "autoresearch source claim graph carrier compact summary evidence gap decision receipt validation",
    "graph_carrier_action_rows": "research director graph carrier decision receipt out-of-loop evidence recovery in-loop focus advisory action rows",
    "evidence_gap_activity": "evidence gap active inactive resolved local artifact public source recovery state compile fetch trace",
    "evidence_gap_recovery": "evidence gap recovery kind classify public evidence versus local verification in-loop focus out-of-loop fetch schema first",
    "explicit_evidence_gap_recovery_kind": "schema first evidence gap recovery_kind recovery_channel action_type classify local verifier public evidence",
    "evidence_gap_is_local_verification": "local verifier evidence gap source preflight verification path integrity kernel runtime not public fetch",
    "evidence_gap_is_active": "active evidence gap state resolved waived justified missing artifact project local recovery",
    "normalize_prediction_contract": "forecast pool scratch prediction ledger autoresearch normalize contract provenance p_success question event horizon resolution",
    "validate_prediction_contract": "forecast pool scratch contract prediction ledger validate p_success tier provenance source surface seal",
    "score_binary_prediction_contract": "forecast Brier score p_success actual_success binary prediction constant baseline calibration",
    "summarize_prediction_contract_rows": "forecast prediction contracts measurement lane scratch forecast pool prediction ledger provenance counts Brier baseline",
    "read_prediction_rows": "prediction receipts JSONL forecast contract parser scratch forecast prediction ledger iteration predictions",
    "validate_prediction_row": "autoresearch adapter per-iteration prediction contract validate p_success horizon resolution tier seal forecast Brier",
    "score_prediction_row": "autoresearch adapter prediction Brier score p_success actual_success constant baseline calibration",
    "summarize_prediction_contracts": "autoresearch trace prediction receipts adapter measurement lane forecast Brier baseline scoreable rows",
    "build_forecast_capability_audit": "forecast pool lifecycle scratch forecast decision use calibration read model capability audit hidden scheduler boundary",
}


@dataclass
class Primitive:
    name: str
    module: str
    kind: str            # function | class | <arch-index kind>
    signature: str
    doc: str             # first docstring line (the "what")
    source: str          # "code" | "architecture_index"
    when_to_use: str = ""  # curated effect-vocabulary aliases (the "when")
    category: str = ""     # taxonomy tier (derived from module path)

    def searchable(self) -> str:
        # name + module tail + FULL doc + effect-vocabulary aliases → bridges the
        # gap between a primitive's own vocabulary and how a task is phrased.
        return f"{self.name} {Path(self.module).stem} {self.doc} {self.when_to_use}"


@dataclass
class AtlasFreshnessStatus:
    ok: bool
    catalog_path: str
    atlas_path: str
    catalog_count: int
    atlas_n: int
    embeddings_count: int
    backend: str
    catalog_digest: str
    atlas_catalog_digest: str
    catalog_digest_matches: bool
    missing_embeddings: int
    extra_embeddings: int
    invalid_embeddings: int
    vector_dimension: int
    duplicate_embedding_keys: int
    catalog_newer_than_atlas: bool
    warnings: list[str]

    def summary(self) -> str:
        status = "ok" if self.ok else "stale"
        bits = [
            f"status={status}",
            f"catalog={self.catalog_count}",
            f"atlas_n={self.atlas_n}",
            f"embeddings={self.embeddings_count}",
            f"backend={self.backend or 'unknown'}",
        ]
        if self.catalog_digest_matches:
            bits.append(f"catalog_digest={self.catalog_digest[:12]}")
        elif self.atlas_catalog_digest:
            bits.append("catalog_digest_mismatch=true")
        else:
            bits.append("catalog_digest_missing=true")
        if self.missing_embeddings:
            bits.append(f"missing={self.missing_embeddings}")
        if self.extra_embeddings:
            bits.append(f"extra={self.extra_embeddings}")
        if self.invalid_embeddings:
            bits.append(f"invalid_embeddings={self.invalid_embeddings}")
        if self.vector_dimension:
            bits.append(f"dimension={self.vector_dimension}")
        if self.duplicate_embedding_keys:
            bits.append(f"duplicate_embedding_keys={self.duplicate_embedding_keys}")
        if self.catalog_newer_than_atlas:
            bits.append("catalog_newer_than_atlas=true")
        return " ".join(bits)


def _primitive_embedding_key(primitive: Primitive) -> str:
    return primitive.signature or primitive.name


def _primitive_embedding_text(primitive: Primitive) -> str:
    return f"{primitive.name}. {primitive.doc} {primitive.when_to_use}".strip()


def primitive_catalog_digest(inventory: list[Primitive]) -> str:
    """Digest the catalog rows that determine primitive atlas embeddings."""
    rows = [
        {
            "key": _primitive_embedding_key(p),
            "name": p.name,
            "module": p.module,
            "kind": p.kind,
            "text": _primitive_embedding_text(p),
            "category": p.category,
        }
        for p in inventory
    ]
    rows.sort(key=lambda row: (row["key"], row["module"], row["name"], row["kind"]))
    payload = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def atlas_freshness_status(
    *,
    catalog_path: Path = ARCH_INDEX,
    atlas_path: Path = ATLAS_PATH,
) -> AtlasFreshnessStatus:
    """Fast consistency check for the primitive catalog and semantic atlas.

    The atlas is a cache of catalog primitives. A catalog row without an embedding
    is lexically visible but semantically invisible, so a stale atlas can make the
    amnesia precheck under-recall existing capabilities.
    """
    warnings: list[str] = []
    inventory = _extract_from_arch_index(catalog_path)
    catalog_digest = primitive_catalog_digest(inventory)
    expected_key_counts = Counter(_primitive_embedding_key(p) for p in inventory)
    expected_keys = set(expected_key_counts)
    duplicate_embedding_keys = sum(1 for count in expected_key_counts.values() if count > 1)
    atlas_n = 0
    backend = ""
    atlas_catalog_digest = ""
    embeddings: dict[str, object] = {}
    if not atlas_path.exists():
        warnings.append(f"atlas missing: {atlas_path}")
    else:
        try:
            payload = json.loads(atlas_path.read_text(encoding="utf-8"))
        except Exception as exc:
            payload = {}
            warnings.append(f"atlas unreadable: {type(exc).__name__}: {str(exc)[:160]}")
        if isinstance(payload, dict):
            backend = str(payload.get("backend") or "")
            atlas_catalog_digest = str(payload.get("catalog_digest") or "")
            raw_embeddings = payload.get("embeddings") or {}
            if isinstance(raw_embeddings, dict):
                embeddings = raw_embeddings
            else:
                warnings.append("atlas embeddings are not a dict")
            try:
                atlas_n = int(payload.get("n") or 0)
            except (TypeError, ValueError):
                warnings.append("atlas n is not an integer")
        elif payload:
            warnings.append("atlas payload is not an object")
    embedding_keys = set(embeddings)
    missing = expected_keys - embedding_keys
    extra = embedding_keys - expected_keys
    invalid_embeddings = 0
    vector_lengths: set[int] = set()
    for key, vector in embeddings.items():
        if not _valid_embedding_vector(vector):
            invalid_embeddings += 1
            continue
        vector_lengths.add(len(vector))
    vector_dimension = next(iter(vector_lengths)) if len(vector_lengths) == 1 else 0
    expected_dimension = _expected_embedding_dimension(backend)
    if atlas_n != len(inventory):
        warnings.append(f"atlas n {atlas_n} != catalog capability count {len(inventory)}")
    if len(embeddings) != atlas_n:
        warnings.append(f"embedding count {len(embeddings)} != atlas n {atlas_n}")
    catalog_digest_matches = bool(atlas_catalog_digest) and atlas_catalog_digest == catalog_digest
    if not atlas_catalog_digest:
        warnings.append("atlas is missing catalog_digest")
    elif not catalog_digest_matches:
        warnings.append("atlas catalog_digest does not match current catalog")
    if duplicate_embedding_keys:
        warnings.append(f"{duplicate_embedding_keys} catalog embedding keys are ambiguous")
    if missing:
        warnings.append(f"{len(missing)} catalog primitives lack atlas embeddings")
    if extra:
        warnings.append(f"{len(extra)} atlas embeddings have no catalog primitive")
    if invalid_embeddings:
        warnings.append(f"{invalid_embeddings} atlas embeddings are malformed")
    if len(vector_lengths) > 1:
        warnings.append(f"atlas embeddings have mixed dimensions: {sorted(vector_lengths)}")
    if expected_dimension is not None and vector_dimension and vector_dimension != expected_dimension:
        warnings.append(
            f"atlas embedding dimension {vector_dimension} != expected {expected_dimension} for {backend}"
        )
    catalog_newer = False
    if catalog_path.exists() and atlas_path.exists():
        try:
            catalog_newer = catalog_path.stat().st_mtime > atlas_path.stat().st_mtime + 1.0
        except OSError:
            catalog_newer = False
        if catalog_newer:
            warnings.append("catalog jsonl is newer than atlas embeddings")
    return AtlasFreshnessStatus(
        ok=not warnings,
        catalog_path=str(catalog_path),
        atlas_path=str(atlas_path),
        catalog_count=len(inventory),
        atlas_n=atlas_n,
        embeddings_count=len(embeddings),
        backend=backend,
        catalog_digest=catalog_digest,
        atlas_catalog_digest=atlas_catalog_digest,
        catalog_digest_matches=catalog_digest_matches,
        missing_embeddings=len(missing),
        extra_embeddings=len(extra),
        invalid_embeddings=invalid_embeddings,
        vector_dimension=vector_dimension,
        duplicate_embedding_keys=duplicate_embedding_keys,
        catalog_newer_than_atlas=catalog_newer,
        warnings=warnings,
    )


def _extract_from_module(path: Path) -> list[Primitive]:
    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    out: list[Primitive] = []
    rel = str(path.relative_to(REPO))
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name.startswith("_"):
            continue                                       # private = not a public primitive
        doc = (ast.get_docstring(node) or "").strip()
        first = doc.splitlines()[0] if doc else ""
        if isinstance(node, ast.ClassDef):
            sig, kind = node.name, "class"
        else:
            args = [a.arg for a in node.args.args]
            sig, kind = f"{node.name}({', '.join(args)})", "function"
        out.append(Primitive(node.name, rel, kind, sig, (doc[:240] or first), "code"))
    return out


# Catalog kinds surfaced by the amnesia precheck (FULL COVERAGE, 2026-06-07): every reusable capability +
# the reflexive "how we work" memory. (Set ZTARE_AMNESIA_PRIMITIVE_ONLY=1 to restrict back to the analytical-
# primitive view if a caller wants only those.)
_INVENTORY_KINDS_FULL = ("primitive", "reflexive_primitive", "op", "gate", "validator",
                         "orchestrator", "mining", "script", "pattern", "anti-pattern", "meta-pattern")
_INVENTORY_KINDS_PRIMITIVE = ("primitive", "reflexive_primitive", "op")
_SUBSTRATE_SPECIFIC_CATEGORIES = {
    "formal-artifact",
    "leanmill",
    "leanmill-script",
    "proof-search",
    "substrate-project",
}
_SUBSTRATE_SCOPE_TERMS = {
    "lean",
    "mathlib",
    "navier",
    "ns",
    "pde",
    "proof",
    "solver",
    "theorem",
    "ztare_proofs",
}
_SUBSTRATE_SPECIFIC_SCOPE_PENALTY = 0.08


def _extract_from_arch_index(path: Path = ARCH_INDEX) -> list[Primitive]:
    if not path.exists():
        return []
    _INVENTORY_KINDS = (_INVENTORY_KINDS_PRIMITIVE if os.environ.get("ZTARE_AMNESIA_PRIMITIVE_ONLY") == "1"
                        else _INVENTORY_KINDS_FULL)
    out: list[Primitive] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        # FULL COVERAGE (2026-06-07): embed/surface every CAPABILITY-bearing kind, not just analytical
        # primitives — gates, validators, orchestrators, mining ops, scripts ARE reusable capabilities, and
        # patterns / anti-patterns / meta-patterns are the reflexive "how we work" memory worth surfacing in a
        # "have we already built/learned this?" precheck. (Excludes only genuinely non-capability index rows.)
        if r.get("kind") not in _INVENTORY_KINDS:
            continue
        appl = r.get("applicability") or []
        appl_str = " ".join(appl) if isinstance(appl, list) else str(appl)
        out.append(Primitive(
            name=str(r.get("name") or r.get("id") or "?"),
            module=str(r.get("path") or r.get("module") or "architecture_index"),
            kind=str(r.get("kind")),
            signature=str(r.get("signature") or r.get("id") or r.get("name") or ""),
            doc=str(r.get("description") or r.get("summary") or "")[:240],
            source="architecture_index",
            when_to_use=appl_str,           # catalog applicability tags = the "when-to-use"
            category=_category_for(str(r.get("path") or r.get("module") or ""))))
    return out


def _id_for(name: str) -> str:
    return name.replace("_", "-").upper()


# Noise filter: utility/helper name patterns that are NOT reusable analytical
# capabilities (they pollute a capability catalog). Curated WHEN_TO_USE always pass.
_UTILITY_NAME_RE = re.compile(
    r"^(_|main$|run$|test|parse|load|save|dump|read|write|fmt|format|to_|from_|get_|set_|"
    r"safe_|slug|hash|sha|now|today|stable_|gh_|write_json|read_json|relpath|ensure_|"
    r"sanitize|serialize|deserialize)")


def _is_quality_primitive(name: str, doc: str) -> bool:
    """Keep a swept primitive only if it's a genuine reusable capability: has a real
    docstring AND is not an obvious utility/IO/serialization helper. Curated
    (WHEN_TO_USE) primitives always pass. This is the DETERMINISTIC noise floor on the
    500+ sweep (free, no key); the opt-in `_llm_quality_filter` sharpens the borderline."""
    if name in WHEN_TO_USE:
        return True
    if _UTILITY_NAME_RE.match(name):
        return False
    # internal code-STRING builders (build_*_script): the public API is the registered primitive
    # (solve_existential / find_linear_recurrence …), not the `build_*_script` that emits the snippet.
    if name.startswith("build_") and name.endswith("_script"):
        return False
    return len((doc or "").strip()) >= 40        # must describe what it does


def _llm_quality_filter(items: "list[tuple]",
                        model: str = "gemini-3.1-flash-lite-preview") -> "set[str]":
    """OPT-IN (`ZTARE_PRIMITIVE_LLM_FILTER=1`) cheap LLM precision pass over the regex-PASSING candidates:
    classify each (name, doc) as a reusable named CAPABILITY (keep) vs an INTERNAL helper / glue / one-off
    (drop) — the borderline the deterministic floor can't judge (a `build_*_script` from a real `build_atlas`).
    ONE batched gemini-flash-lite call. This is CURATION, not a soundness gate (a wrong call only adds/drops a
    catalog row — never launders), so an LLM judgment is acceptable here. CONSERVATIVE: on no-key / error /
    unparseable / drops-everything → KEEP ALL (never silently lose primitives on infra failure). Returns the
    set of names to KEEP."""
    names = [it[0] for it in items]
    if not names:
        return set()
    try:
        from ztare.common.llm_runtime import LLMRuntime
    except Exception:
        try:
            from ztare.common.llm_runtime import LLMRuntime
        except Exception:
            return set(names)        # no runtime → keep all (deterministic floor already applied)
    # richer informational value (2026-06-07): give the LLM the SIGNATURE (args disambiguate a builder from a
    # real op) + the full first docstring line — not a 140-char stub (the thin input wrongly dropped build_goal
    # = a real Lean-goal EXTRACTOR, read as a "builder").
    def _fmt(it):
        name = it[0]
        doc = (it[1] or "").splitlines()[0] if (len(it) > 1 and it[1]) else ""
        sig = it[2] if (len(it) > 2 and it[2]) else ""
        head = f"- {sig or name}" + (f"  [{name}]" if sig else "")
        return f"{head}: {doc[:240]}"
    listing = "\n".join(_fmt(it) for it in items)
    prompt = (
        "You are curating a catalog of REUSABLE engineering/analytical capabilities so future work REUSES them "
        "instead of rebuilding. Be VERY CONSERVATIVE — the cost of dropping a real capability (someone rebuilds "
        "it) FAR outweighs keeping a borderline one. DEFAULT TO KEEP.\n"
        "drop ONLY if you are CERTAIN it is pure internal PLUMBING: specifically a code-STRING builder that "
        "emits source text (e.g. `build_*_script`, `build_*_prompt`), or trivial glue with no standalone "
        "capability. If it is a named operation, solver, dispatcher, extractor, derivation, metric, gate, "
        "transform, selector, assembler, router, or anything you are even slightly unsure about → KEEP.\n"
        "Return ONLY a JSON object mapping each exact name to \"keep\" or \"drop\".\nITEMS:\n" + listing + "\n")
    try:
        from ztare.common.dispatch_model import dispatch_call_text

        runtime = LLMRuntime()
        resp = dispatch_call_text(
            "primitive_quality_filter",
            prompt,
            llm_response_call=lambda p: runtime.call_text(
                p, model_id=model,
                fallback_model_ids=("gemini-2.5-flash",),
                max_tokens=4000, request_label="primitive_quality_filter",
                timeout_seconds=90,
            ),
            timeout_seconds=90,
        )
        text = getattr(resp, "text", "") or ""
    except Exception:
        return set(names)            # error → keep all
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return set(names)
    try:
        verdicts = json.loads(m.group(0))
    except Exception:
        return set(names)
    keep = {n for n in names if str(verdicts.get(n, "keep")).lower().strip() != "drop"}
    return keep or set(names)        # distrust a total wipe → keep all


def populate_catalog(repo: Path = REPO, path: Path = ARCH_INDEX, *, clean: bool = False) -> int:
    """Register the curated extracted analytical primitives INTO architecture_index
    (the single catalog), so the WIRED `primitive_tick_surface` surfaces them at
    tick-start — instead of this module owning a parallel inventory. The effect-
    vocabulary `WHEN_TO_USE` aliases become the catalog `applicability` tags (which
    is what tick_surface matches on). Idempotent: skips ids already present. Returns
    the number of new rows appended. This is the ONE maintenance action; run it when
    a new reusable analytical primitive ships."""
    # Clean repopulate: drop rows THIS tool added (they carry a `signature` field) so
    # we re-register under the current noise filter instead of accumulating cruft.
    rows = [enrich_row(json.loads(l)) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if clean:
        rows = [r for r in rows if "signature" not in r]
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    existing = {r.get("id") for r in rows}
    # Gather EVERY public primitive from the curated modules + swept directories.
    by_name: dict[str, Primitive] = {}
    mods = list(PRIMITIVE_MODULES)
    for d in PRIMITIVE_DIRS:
        dpath = repo / d
        if dpath.exists():
            for f in sorted(dpath.glob("*.py")):
                if f.name.startswith("_") or "test" in f.name or "fixture" in f.name:
                    continue
                mods.append(str(f.relative_to(repo)))
    for m in dict.fromkeys(mods):                       # dedup, preserve order
        for p in _extract_from_module(repo / m):
            by_name.setdefault(p.name, p)
    # DETERMINISTIC floor first (free, no key): regex + the build_*_script rule.
    cands = [(name, p, _id_for(name)) for name, p in by_name.items()
             if _id_for(name) not in existing and _is_quality_primitive(name, p.doc)]
    # OPT-IN cheap LLM precision pass (ZTARE_PRIMITIVE_LLM_FILTER=1): drop the borderline internal helpers the
    # regex can't judge. ONE batched gemini-flash-lite call; conservative fallback = keep all. Curated
    # (WHEN_TO_USE) primitives are EXEMPT (never sent to the LLM — they are operator-blessed reuse).
    # ADVISORY, opt-in (ZTARE_PRIMITIVE_LLM_FILTER=1) — NOT a default. A single batched LLM call is
    # non-deterministic across batch contexts (it kept `build_goal` in a 4-item test but dropped it in the
    # 402-item run), so it is too unreliable to AUTO-drop when the bar is "lose nothing relevant"; the
    # deterministic regex floor stays the safe default and this is a review aid the operator opts into.
    if os.environ.get("ZTARE_PRIMITIVE_LLM_FILTER") == "1" and cands:
        _judge = [(n, p.doc, p.signature) for n, p, _ in cands if n not in WHEN_TO_USE]
        if _judge:
            _keep = _llm_quality_filter(_judge)
            cands = [(n, p, cid) for n, p, cid in cands if n in WHEN_TO_USE or n in _keep]
    new_rows = []
    for name, p, cid in cands:
        existing.add(cid)
        # applicability = curated effect-aliases if present, else name+module+doc tokens
        aliases = WHEN_TO_USE.get(name)
        appl = sorted(set(aliases.split())) if aliases else sorted(tokenize(f"{name} {Path(p.module).stem} {p.doc}"))
        row = {
            "id": cid, "path": p.module, "kind": "primitive",
            "description": (p.doc.splitlines()[0][:200] if p.doc else name),
            "applicability": appl[:24],
            "impact_factor_expost": 3 if aliases else 1,   # curated high-value rank above swept
            "last_used": "", "dependencies": [], "signature": p.signature,
        }
        new_rows.append(enrich_row(row))
    if new_rows:
        with path.open("a", encoding="utf-8") as f:
            for r in new_rows:
                f.write(json.dumps(r) + "\n")
    return len(new_rows)


def build_inventory(repo: Path = REPO) -> list[Primitive]:
    """Read the inventory from the CATALOG (architecture_index) — the single source
    of truth, shared with the wired `primitive_tick_surface`. No parallel runtime
    extraction (use `populate_catalog` to add primitives to the catalog instead)."""
    return _extract_from_arch_index()


def _embed(text: str, *, role: str = "query", backend: str = "gemini-code") -> "list[float] | None":
    """Code-aware, ASYMMETRIC embedding. role='document' for catalog primitives,
    role='query' for the task query (asymmetric query/doc embedding is a real
    retrieval-quality lever the old symmetric RETRIEVAL_QUERY-for-everything missed).
    Backends: 'gemini' (RETRIEVAL_QUERY/DOCUMENT), 'gemini-code' (CODE_RETRIEVAL_QUERY
    for the NL→code query side), 'openai' (text-embedding-3-large)."""
    global _LAST_EMBED_ERROR
    _LAST_EMBED_ERROR = None
    text = (text or "").strip()
    if not text:
        _LAST_EMBED_ERROR = "empty text"
        return None
    if backend in ("gemini", "gemini-code"):
        # Migrated to the canonical embedding engine (ztare.common.embeddings, §6n.14). The
        # code-aware asymmetric task type is preserved; the None-on-missing-key / None-on-error
        # contract (lexical fallback) is kept; make_client owns .env bootstrapping.
        key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        tt = ("RETRIEVAL_DOCUMENT" if role == "document"
              else ("CODE_RETRIEVAL_QUERY" if backend == "gemini-code" else "RETRIEVAL_QUERY"))
        try:
            try:
                from ztare.common.embeddings import embed_batch, make_client
            except ModuleNotFoundError:
                from ztare.common.embeddings import embed_batch, make_client
            return embed_batch(
                make_client(key, force_remote=True),
                [text],
                model="gemini-embedding-001",
                dimensions=768,
                task_type=tt,
                force_remote=True,
            )[0]
        except SystemExit as exc:
            _LAST_EMBED_ERROR = str(exc)[:240]
            return None
        except Exception as exc:
            _LAST_EMBED_ERROR = f"{type(exc).__name__}: {str(exc)[:240]}"
            return None
    if backend == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            _LAST_EMBED_ERROR = "missing OPENAI_API_KEY"
            return None
        try:
            import openai
            v = openai.OpenAI().embeddings.create(
                model="text-embedding-3-large", input=text, dimensions=1024)
            return list(v.data[0].embedding)
        except Exception as exc:
            _LAST_EMBED_ERROR = f"{type(exc).__name__}: {str(exc)[:240]}"
            return None
    _LAST_EMBED_ERROR = f"unknown backend: {backend}"
    return None


def build_primitive_atlas(path: Path = ATLAS_PATH, backend: str = "gemini-code") -> int:
    """Embed every catalog primitive ONCE into a cached atlas (signature → vector),
    as DOCUMENTS (asymmetric: queries embed as queries at search time). Code-aware
    backend by default. This is what makes semantic retrieval scale + generalize
    (vocabulary-invariant), removing the hand-tuned aliases as the mechanism."""
    inv = build_inventory()
    expected = {_primitive_embedding_key(p) for p in inv}
    catalog_digest = primitive_catalog_digest(inv)
    vecs: dict[str, list[float]] = {}
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
            if str(current.get("backend") or backend) == backend:
                existing = current.get("embeddings") or {}
                if isinstance(existing, dict):
                    vecs.update({
                        str(k): v for k, v in existing.items()
                        if k in expected and _valid_embedding_vector(v, backend=backend)
                    })
        except Exception:
            vecs = {}
    for p in inv:
        key = _primitive_embedding_key(p)
        if key in vecs:
            continue
        v = _embed(_primitive_embedding_text(p), role="document", backend=backend)
        if _valid_embedding_vector(v, backend=backend):
            vecs[key] = v
    if inv and len(vecs) != len(inv):
        return 0
    path.write_text(
        json.dumps(
            {
                "backend": backend,
                "n": len(vecs),
                "catalog_digest": catalog_digest,
                "embeddings": vecs,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return len(vecs)


def _load_atlas(path: Path = ATLAS_PATH) -> tuple[dict, str]:
    if not path.exists():
        return {}, "gemini-code"
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d.get("embeddings", {}), d.get("backend", "gemini-code")
    except Exception:
        return {}, "gemini-code"


def _cos(a, b) -> float:
    s = sa = sb = 0.0
    for x, y in zip(a, b):
        s += x * y; sa += x * x; sb += y * y
    return s / ((sa ** 0.5) * (sb ** 0.5)) if sa and sb else 0.0


def _query_names_substrate(query: str, primitive: Primitive) -> bool:
    """Return whether a substrate-specific catalog row is scoped by the query."""
    if primitive.category not in _SUBSTRATE_SPECIFIC_CATEGORIES:
        return True
    query_tokens = {token.lower() for token in tokenize(query)}
    if query_tokens & _SUBSTRATE_SCOPE_TERMS:
        return True
    query_l = query.lower()
    if any(re.search(rf"\b{re.escape(term)}\b", query_l) for term in _SUBSTRATE_SCOPE_TERMS):
        return True
    return False


def _scope_adjusted_score(score: float, query: str, primitive: Primitive) -> float:
    if score <= 0 or _query_names_substrate(query, primitive):
        return score
    return max(0.0, score - _SUBSTRATE_SPECIFIC_SCOPE_PENALTY)


def _semantic_blend(query: str, inv: list[Primitive]) -> dict:
    """Vocabulary-invariant scores via the CACHED atlas: embed the query ONCE (as a
    QUERY, with the atlas's backend), cosine against pre-embedded primitive DOCUMENTS
    (O(1) embed calls/query). Returns {idx: cosine}; empty → lexical fallback."""
    atlas, backend = _load_atlas()
    if not atlas:
        return {}
    qv = _embed(query, role="query", backend=backend)
    if qv is None:
        return {}
    out = {}
    for i, p in enumerate(inv):
        dv = atlas.get(p.signature or p.name)
        if dv is not None:
            out[i] = _cos(qv, dv)
    return out


def precheck(query: str, top_k: int = 8, *, semantic: "bool | None" = None,
             inventory: "list[Primitive] | None" = None) -> list[dict]:
    """Rank extracted primitives by relevance to `query`. SEMANTIC (cached atlas,
    vocabulary-invariant) is the PRIMARY mechanism whenever the atlas exists — it
    generalizes to paraphrased queries and scales to 500+, so the curated aliases
    are only a minor lexical boost, not the mechanism (the fix for the lexical
    overfit). Falls back to lexical-only when no atlas/embedder. `semantic=None`
    auto-detects; pass True/False to force."""
    inv = inventory if inventory is not None else build_inventory()
    qt = tokenize(query)
    if semantic is None:
        semantic = ATLAS_PATH.exists()
    sem = _semantic_blend(query, inv) if semantic else {}
    lex_by_i, matched_by_i = {}, {}
    for i, p in enumerate(inv):
        lex, jac, cov, matched = _score(qt, p.searchable())
        lex_by_i[i] = lex
        matched_by_i[i] = matched
    # FUSION POLICY (parameter-free, no magic constant): when the semantic atlas is
    # present it is the PRIMARY ranker (it generalizes; lexical is brittle) — rank by
    # cosine, lexical breaks ties. (Equal-weight RRF was tried and DEGRADED results
    # here: it gives the weak lexical ranker equal pull and dilutes the strong
    # semantic signal — RRF assumes comparable-quality rankers, which doesn't hold.)
    # Without an atlas, fall back to lexical-only.
    if sem:
        cand = [i for i in range(len(inv)) if sem.get(i, 0.0) > 0 or lex_by_i.get(i, 0.0) > 0]
        cand.sort(
            key=lambda i: (
                _scope_adjusted_score(sem.get(i, 0.0), query, inv[i]),
                sem.get(i, 0.0),
                lex_by_i.get(i, 0.0),
            ),
            reverse=True,
        )
        score_of = lambda i: round(sem.get(i, 0.0), 4)
    else:
        cand = [i for i in range(len(inv)) if lex_by_i.get(i, 0.0) > 0]
        cand.sort(key=lambda i: lex_by_i[i], reverse=True)
        score_of = lambda i: round(lex_by_i[i], 4)
    return [{"name": inv[i].name, "module": inv[i].module, "kind": inv[i].kind,
             "signature": inv[i].signature, "doc": inv[i].doc,
             "when_to_use": inv[i].when_to_use, "category": inv[i].category,
             "score": score_of(i), "matched_terms": matched_by_i.get(i, [])}
            for i in cand[:top_k]]


# HELD-OUT relevance benchmark: (task query, acceptable primitive id/name substrings).
# Queries are phrased in natural task language and deliberately AVOID the WHEN_TO_USE
# alias tokens, so a pass measures SEMANTIC generalization, not lexical leakage.
# Hand-labeled, n≈18 — a starting eval set, not a full IR benchmark.
BENCHMARK = [
    ("measure how much two collections of results share in common", ["jaccard"]),
    ("decide whether to keep iterating or stop because nothing new is appearing", ["information-yield", "iterationsignal"]),
    ("count how many subgoals are still open in a partially finished Lean proof", ["proof-state", "extract-unsolved"]),
    ("how many data points are needed to reliably detect a correlation", ["n-required-for-rho"]),
    ("smallest correlation I could detect with the sample I already have", ["detectable-rho-at-n"]),
    ("is the difference between condition A and B real, with matched pairs", ["paired-permutation"]),
    ("argue that two approaches are effectively the same, not just 'no difference found'", ["tost-equivalence"]),
    ("put error bars on a statistic by resampling the data", ["bootstrap-ci"]),
    ("compare two competing models while penalizing the more complex one", ["bf-bic-paired"]),
    ("association between two rankings ignoring exact values", ["spearman-rho"]),
    ("pull the theorem statement apart from the lemmas used only in its proof", ["statement", "build-goal", "build-ablation"]),
    ("decide if an experiment had enough power or the result is inconclusive", ["power-aware-verdict"]),
    ("turn a partial proof's leftover goal into something to attack next", ["extract-unsolved", "residual"]),
    ("score whether a proof attempt got close or was nowhere", ["proof-state"]),
    ("frame the single most decomposition-driving question for a problem", ["eigenquestion"]),
    ("control false positives across many simultaneous hypothesis tests", ["bh-fdr", "fdr"]),
    ("how far apart are two probability distributions / vectors", ["distance", "cosine", "set-distance"]),
    ("which capability already exists for a task before I build one", ["primitive-amnesia", "amnesia"]),
    # ── expanded 2026-06-07 to cover the leanmill-solver / common surface where the LLM filter wrongly
    #    dropped relevant primitives (the n=18 set couldn't DETECT those false drops). These targets all exist.
    ("dispatch an agentic coding task to codex or claude on the operator subscription", ["default_dispatch", "dispatch"]),
    ("run an untrusted model-written sympy script safely in a sandboxed subprocess", ["run_guarded_script", "sandboxed", "guarded"]),
    ("recover the linear recurrence behind a number sequence via hankel rank", ["find_linear_recurrence", "recurrence"]),
    ("find a counterexample to a universally-quantified arithmetic claim", ["find_counterexample", "counterexample"]),
    ("solve a determined system of equations for an integer witness", ["solve_linear_system", "solve_existential"]),
    ("derive predictions from a Lagrangian model specification", ["derive_from_action", "lagrangian"]),
    ("extract a fair provable goal for a target theorem from Lean source", ["build_goal"]),
    ("inject a computed witness into a Lean refine tactic", ["inject_witness_tactic", "witness"]),
    ("among several proofs that close the same goal pick the description-length shortest", ["mdl_shortest", "shortest"]),
    ("transport a proof technique from a field where the structure is solved, by analogy", ["surface_field_analogies", "isomorph", "analog"]),
    ("select which solver move to try next with a calibrated bandit", ["ucb_move_scores", "ucb"]),
]


def _case_id(query: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
    return f"case-{index:03d}-{slug[:48]}"


def _normalize_benchmark_case(case: object, index: int) -> dict:
    """Return a typed benchmark row while preserving the legacy tuple format."""
    if isinstance(case, dict):
        query = str(case.get("query", ""))
        targets = [str(t).lower() for t in case.get("targets", case.get("acceptable", []))]
        return {
            "case_id": str(case.get("case_id") or case.get("id") or _case_id(query, index)),
            "query": query,
            "targets": targets,
            "confusers": [str(t).lower() for t in case.get("confusers", [])],
            "family": str(case.get("family", "")),
            "repair_hint": str(case.get("repair_hint", "")),
        }
    query, targets = case  # legacy: (query, acceptable target substrings)
    return {
        "case_id": _case_id(str(query), index),
        "query": str(query),
        "targets": [str(t).lower() for t in targets],
        "confusers": [],
        "family": "",
        "repair_hint": "",
    }


def _stable_json_digest(payload: object) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _inventory_digest(inv: list[Primitive]) -> str:
    return _stable_json_digest([
        {
            "name": p.name,
            "module": p.module,
            "signature": p.signature,
            "source": p.source,
            "category": p.category,
        }
        for p in inv
    ])


def _candidate_excerpt(ranked: list[dict], limit: int = 5) -> list[dict]:
    out: list[dict] = []
    for row in ranked[:limit]:
        out.append(
            {
                "name": row.get("name", ""),
                "module": row.get("module", ""),
                "signature": row.get("signature", ""),
                "score": row.get("score"),
                "matched_terms": row.get("matched_terms", []),
            }
        )
    return out


def _primitive_match_text(row: Primitive | dict) -> str:
    if isinstance(row, Primitive):
        parts = [row.name, row.signature, row.module, row.kind, row.category]
    else:
        parts = [
            str(row.get("name", "")),
            str(row.get("signature", "")),
            str(row.get("module", "")),
            str(row.get("kind", "")),
            str(row.get("category", "")),
        ]
    return " ".join(parts).lower().replace("_", "-")


def _matches_any_target(row: Primitive | dict, targets: list[str]) -> bool:
    text = _primitive_match_text(row)
    return any(str(target).lower().replace("_", "-") in text for target in targets)


def _target_resolution(targets: list[str], inv: list[Primitive]) -> dict:
    matched = []
    for primitive in inv:
        if _matches_any_target(primitive, targets):
            matched.append(
                {
                    "name": primitive.name,
                    "module": primitive.module,
                    "signature": primitive.signature,
                }
            )
    return {"resolved": bool(matched), "matches": matched[:8], "match_count": len(matched)}


def evaluate(top_k: int = 5, *, semantic: "bool | None" = None) -> dict:
    """Recall@k + MRR over the held-out benchmark. The discipline:
    MEASURE retrieval, don't assert it. `semantic=False` forces the lexical baseline
    so the semantic lift is quantified on the same queries."""
    inv = build_inventory()
    ranker = "semantic" if semantic is not False else "lexical"
    cases = [_normalize_benchmark_case(case, i) for i, case in enumerate(BENCHMARK)]
    bench_digest = _stable_json_digest(cases)
    catalog_digest = _inventory_digest(inv)
    hits_at_k = 0; rr_sum = 0.0; misses = []
    miss_records = []
    unresolved_cases = []
    confuser_hits = []
    resolvable_n = 0
    for benchmark_index, case in enumerate(cases):
        query = case["query"]
        targets = case["targets"]
        resolution = _target_resolution(targets, inv)
        target_resolved = bool(resolution["resolved"])
        if target_resolved:
            resolvable_n += 1
        else:
            unresolved_cases.append(
                {
                    "case_id": case["case_id"],
                    "query": query,
                    "targets": targets,
                }
            )
        ranked = precheck(query, top_k=top_k, inventory=inv, semantic=semantic)
        rank = next((r for r, row in enumerate(ranked, 1)
                     if _matches_any_target(row, targets)), None)
        confuser_rank = next((r for r, row in enumerate(ranked, 1)
                              if case["confusers"] and _matches_any_target(row, case["confusers"])), None)
        if confuser_rank is not None:
            confuser_hits.append(
                {
                    "case_id": case["case_id"],
                    "query": query,
                    "confusers": case["confusers"],
                    "confuser_rank": confuser_rank,
                }
            )
        if rank:
            hits_at_k += 1; rr_sum += 1.0 / rank
        else:
            misses.append((query[:50], targets))
            miss_kind = "retrieval_miss" if target_resolved else "benchmark_target_unresolved"
            miss_id = _stable_json_digest(
                {
                    "case_id": case["case_id"],
                    "query": query,
                    "targets": targets,
                    "top_k": top_k,
                    "ranker": ranker,
                    "miss_kind": miss_kind,
                    "benchmark_digest": bench_digest,
                    "catalog_digest": catalog_digest,
                }
            )[:16]
            miss_records.append(
                {
                    "miss_id": miss_id,
                    "miss_kind": miss_kind,
                    "case_id": case["case_id"],
                    "benchmark_index": benchmark_index,
                    "query": query,
                    "targets": list(targets),
                    "target_resolution": resolution,
                    "confusers": case["confusers"],
                    "family": case["family"],
                    "top_k": top_k,
                    "ranker": ranker,
                    "benchmark_digest": bench_digest,
                    "catalog_digest": catalog_digest,
                    "top_candidates": _candidate_excerpt(ranked),
                    "repair_hint": case["repair_hint"],
                    "repair_policy": (
                        "If miss_kind=benchmark_target_unresolved, fix the benchmark target "
                        "or add the missing primitive/catalog row before treating this as a "
                        "retrieval failure. If miss_kind=retrieval_miss, inspect whether the "
                        "target primitive is missing an effect-vocabulary alias, stale in the "
                        "semantic atlas, or crowded out by a confuser. Fix the catalog/alias/atlas "
                        "first; change the benchmark only if the target label is wrong."
                    ),
                }
            )
    n = len(cases)
    denom = resolvable_n or n or 1
    return {"n": n, "resolvable_n": resolvable_n,
            "unresolved_target_cases": unresolved_cases,
            "unresolved_target_count": len(unresolved_cases),
            "confuser_hits": confuser_hits,
            "confuser_hit_count": len(confuser_hits),
            "recall_at_k": round(hits_at_k / denom, 3), "k": top_k,
            "mrr": round(rr_sum / denom, 3), "misses": misses,
            "miss_records": miss_records,
            "benchmark_digest": bench_digest,
            "catalog_digest": catalog_digest,
            "ranker": ranker}


def record_miss_queue(eval_result: dict, path: Path = MISS_QUEUE_PATH) -> dict:
    """Append new held-out retrieval misses to a deduped JSONL repair queue."""
    miss_records = list(eval_result.get("miss_records") or [])
    if eval_result.get("ranker") == "semantic" and eval_result.get("semantic_live") is False:
        return {
            "path": str(path),
            "misses": len(miss_records),
            "appended": 0,
            "existing_after": None,
            "skipped": True,
            "skip_reason": (
                "semantic embedder unavailable; refusing to record lexical-fallback "
                "misses as semantic retrieval debt"
            ),
            "semantic_liveness_reason": eval_result.get("semantic_liveness_reason"),
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            miss_id = row.get("miss_id")
            if isinstance(miss_id, str):
                existing_ids.add(miss_id)
    now = datetime.now(timezone.utc).isoformat()
    appended = 0
    with path.open("a", encoding="utf-8") as fh:
        for record in miss_records:
            miss_id = record.get("miss_id")
            if not isinstance(miss_id, str) or miss_id in existing_ids:
                continue
            row = {
                "schema_version": "primitive_amnesia_miss_v1",
                "recorded_at": now,
                "status": "open",
                **record,
            }
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            existing_ids.add(miss_id)
            appended += 1
    return {
        "path": str(path),
        "misses": len(miss_records),
        "appended": appended,
        "existing_after": len(existing_ids),
    }


def _compact_candidate_ref(row: dict) -> str:
    name = str(row.get("name") or "").strip()
    signature = str(row.get("signature") or "").strip()
    module = str(row.get("module") or "").strip()
    parts = [part for part in (name, signature, module) if part]
    return " | ".join(parts) if parts else "none"


def _miss_queue_promotion_review(row: dict) -> dict:
    """Classify one primitive-amnesia miss as a repair/promotion review.

    This is a read-only review contract. It does not register a primitive or
    close the miss; it names the next auditable action so open misses do not
    sit as undifferentiated debt.
    """
    miss_kind = str(row.get("miss_kind") or "unknown")
    target_resolution = row.get("target_resolution")
    if not isinstance(target_resolution, dict):
        target_resolution = {}
    top_candidates = [
        candidate for candidate in row.get("top_candidates") or []
        if isinstance(candidate, dict)
    ]
    nearest_confuser = _compact_candidate_ref(top_candidates[0]) if top_candidates else "none"
    resolved_matches = [
        _compact_candidate_ref(match)
        for match in target_resolution.get("matches") or []
        if isinstance(match, dict)
    ]
    target_resolved = bool(target_resolution.get("resolved"))
    if miss_kind == "retrieval_miss" or target_resolved:
        promotion_decision = "close_as_catalog_retrieval_repair"
        typed_carrier = "primitive_catalog_alias_or_atlas_repair"
        nearest_existing_surface = (
            "; ".join(resolved_matches[:3])
            or "architecture_index primitive exists but retrieval did not surface it"
        )
        kill_criterion = (
            "Do not add a new primitive while the target already exists; repair "
            "aliases, applicability tags, ranking, or stale atlas embeddings first."
        )
        non_claim = (
            "This miss is not evidence that a new primitive is needed; it is "
            "retrieval/catalog debt until the existing target fails a direct test."
        )
    elif miss_kind == "benchmark_target_unresolved":
        promotion_decision = "review_missing_catalog_or_benchmark_target"
        typed_carrier = "primitive_catalog_candidate_or_benchmark_repair"
        nearest_existing_surface = "no matching target primitive found in the catalog"
        kill_criterion = (
            "Do not promote until the benchmark target label is checked against "
            "existing primitives, duplicate/confuser candidates are ruled out, "
            "and a deterministic self-test proves the gap."
        )
        non_claim = (
            "This is not a promoted primitive; it is a candidate catalog or "
            "benchmark repair requiring duplicate and confuser checks."
        )
    else:
        promotion_decision = "review_only"
        typed_carrier = "primitive_amnesia_miss_review"
        nearest_existing_surface = "primitive_amnesia miss queue"
        kill_criterion = "Classify miss_kind before promotion or closure."
        non_claim = "Unclassified miss rows are review-only."
    review = {
        "schema_version": "primitive-amnesia-promotion-review-v1",
        "record_type": "primitive_amnesia_promotion_review",
        "miss_id": row.get("miss_id"),
        "case_id": row.get("case_id"),
        "miss_kind": miss_kind,
        "query": row.get("query"),
        "targets": row.get("targets") or [],
        "promotion_decision": promotion_decision,
        "nearest_existing_surface": nearest_existing_surface,
        "nearest_confuser": nearest_confuser,
        "typed_carrier": typed_carrier,
        "deterministic_validator": (
            "python -m ztare.research_director.primitive_amnesia --eval "
            "--record-misses"
        ),
        "ex_post_usage_criterion": (
            "A later primitive-amnesia eval surfaces the intended target within "
            "top-k, or the row is closed with a catalog/benchmark repair note."
        ),
        "primitive_amnesia_note": str(row.get("repair_policy") or ""),
        "non_claim": non_claim,
        "kill_criterion": kill_criterion,
        "top_candidates": [_compact_candidate_ref(candidate) for candidate in top_candidates[:5]],
    }
    required = (
        "miss_id",
        "case_id",
        "promotion_decision",
        "nearest_existing_surface",
        "nearest_confuser",
        "typed_carrier",
        "deterministic_validator",
        "ex_post_usage_criterion",
        "non_claim",
        "kill_criterion",
    )
    missing = [
        field for field in required
        if not str(review.get(field) or "").strip()
    ]
    review["validation"] = {"ok": not missing, "missing": missing}
    return review


def miss_queue_status(path: Path = MISS_QUEUE_PATH) -> dict:
    """Summarize primitive-amnesia repair debt from the JSONL miss queue."""
    rows: list[dict] = []
    malformed = 0
    if path.exists():
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if isinstance(obj, dict):
                rows.append(obj)
            else:
                malformed += 1
    status_counts = Counter(str(row.get("status") or "open") for row in rows)
    open_rows = [
        row
        for row in rows
        if str(row.get("status") or "open").lower() not in {"closed", "resolved", "retired"}
    ]
    open_rows.sort(key=lambda row: str(row.get("recorded_at") or ""), reverse=True)
    promotion_reviews = [_miss_queue_promotion_review(row) for row in open_rows]
    promotion_review_counts = Counter(
        str(review.get("promotion_decision") or "review_only")
        for review in promotion_reviews
    )
    return {
        "path": str(path),
        "exists": path.exists(),
        "row_count": len(rows),
        "open_count": len(open_rows),
        "malformed_count": malformed,
        "status_counts": dict(status_counts),
        "promotion_review_counts": dict(promotion_review_counts),
        "latest_open": [
            {
                "miss_id": row.get("miss_id"),
                "case_id": row.get("case_id"),
                "query": row.get("query"),
                "targets": row.get("targets"),
                "miss_kind": row.get("miss_kind"),
                "ranker": row.get("ranker"),
                "recorded_at": row.get("recorded_at"),
                "repair_hint": row.get("repair_hint"),
                "promotion_review": _miss_queue_promotion_review(row),
            }
            for row in open_rows[:5]
        ],
    }


def _selftest() -> int:
    inv = build_inventory()
    fails = []
    print(f"inventory size: {len(inv)} primitives across {len(PRIMITIVE_MODULES)} modules + arch-index")
    # The exact failure this tool exists to prevent: a leanmill orchestration task
    # MUST surface jaccard, information-yield, and proof-state.
    # FOCUSED per-need queries (one need each) — the correct test of "does the right
    # primitive surface for this need?" A kitchen-sink query conflates needs and the
    # most-central primitive wins, which is correct behaviour, not a miss.
    checks = [
        ("jaccard", "measure overlap / diversity between two sets of results"),
        ("information", "decide when to stop a loop that is no longer informative"),
        ("proof", "how many goals remain in a partial proof; partial progress"),
    ]
    for want, query in checks:
        names = {h["name"].lower() for h in precheck(query, top_k=8)}
        ok = any(want in n for n in names)
        print(f"  [{'PASS' if ok else 'FAIL'}] '{query[:40]}...' -> surfaces '{want}'")
        if not ok:
            fails.append(want)
    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


def semantic_live() -> "tuple[bool, str]":
    """Positive control for the SEMANTIC embedder — the analog of substrate_liveness for Lean.
    A dead embedder (no key / quota / network) makes `_embed` return None silently, the
    precheck degrades to brittle lexical, and a 'no primitive matched' becomes a FALSE
    NEGATIVE that green-lights re-derivation (the treadmill the amnesia firewall exists to
    prevent). Reuses the shared `common.embedder_liveness` positive control."""
    try:
        from ztare.common.embedder_liveness import embedder_live
    except ModuleNotFoundError:  # supports `python -m src.ztare...` from repo root
        from ztare.common.embedder_liveness import embedder_live
    atlas, backend = _load_atlas()
    live, why = embedder_live(lambda t: _embed(t, role="query", backend=backend),
                              atlas_nonempty=bool(atlas))
    if not live and _LAST_EMBED_ERROR:
        return live, _LAST_EMBED_ERROR
    return live, why


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Primitive scientific-amnesia precheck")
    ap.add_argument("query", nargs="?", help="task description to surface primitives for")
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--lexical-only", action="store_true",
                    help="disable the semantic atlas (use brittle lexical only; for comparison)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--populate-catalog", action="store_true",
                    help="register the extracted primitives into architecture_index "
                         "(the single catalog the wired primitive_tick_surface reads)")
    ap.add_argument("--build-atlas", action="store_true",
                    help="embed every catalog primitive into the semantic atlas")
    ap.add_argument("--repopulate", action="store_true",
                    help="CLEAN re-register: drop prior tool-added rows + re-add under the noise filter")
    ap.add_argument("--embedder", default="gemini-code",
                    choices=["gemini-code", "gemini", "openai"],
                    help="embedding backend for --build-atlas (default: code-aware gemini)")
    ap.add_argument("--eval", action="store_true",
                    help="recall@k + MRR over the held-out benchmark (MEASURE retrieval)")
    ap.add_argument("--record-misses", action="store_true",
                    help="with --eval, append semantic misses to the primitive-amnesia repair queue")
    ap.add_argument("--miss-queue", default=str(MISS_QUEUE_PATH),
                    help="JSONL path for --record-misses")
    ap.add_argument("--semantic-live", action="store_true",
                    help="positive-control the semantic embedder + atlas and print the result")
    ap.add_argument("--atlas-status", action="store_true",
                    help="check catalog/atlas freshness without embedding calls")
    a = ap.parse_args(argv)
    if a.repopulate:
        n = populate_catalog(clean=True)
        print(f"clean re-populate: {n} quality-filtered primitive rows in architecture_index.")
        return 0
    if a.populate_catalog:
        n = populate_catalog()
        print(f"appended {n} primitive rows to architecture_index.")
        return 0
    if a.build_atlas:
        n = build_primitive_atlas(backend=a.embedder)
        status = atlas_freshness_status()
        if status.ok:
            print(f"embedded {n} primitives into the semantic atlas (backend={a.embedder}).")
            return 0
        print(f"FAILED to build a complete semantic atlas (backend={a.embedder}, embedded={n}).")
        for warning in status.warnings:
            print(f"WARNING: {warning}")
        return 2
    if a.eval:
        k = a.top_k if a.top_k != 8 else 5
        lex = evaluate(top_k=k, semantic=False)
        sem = evaluate(top_k=k, semantic=True)
        live, why = semantic_live()
        sem["semantic_live"] = live
        sem["semantic_liveness_reason"] = why
        print(
            f"HELD-OUT BENCHMARK (n={sem['n']}, "
            f"resolvable={sem.get('resolvable_n', sem['n'])}, k={k}):"
        )
        print(f"  lexical-only : recall@{k}={lex['recall_at_k']}  MRR={lex['mrr']}")
        delta = round(float(sem["recall_at_k"]) - float(lex["recall_at_k"]), 3)
        print(
            f"  semantic     : recall@{k}={sem['recall_at_k']}  "
            f"MRR={sem['mrr']}  (delta={delta:+.3f})"
        )
        if not live:
            print(f"  semantic live: false ({why})")
        if sem.get("unresolved_target_count"):
            print(f"  benchmark debt: unresolved_targets={sem['unresolved_target_count']}")
        if sem.get("confuser_hit_count"):
            print(f"  confuser hits : {sem['confuser_hit_count']}")
        miss_label = "semantic MISS" if live else "fallback MISS"
        for miss in sem.get("miss_records", []):
            print(
                f"  {miss_label}: "
                f"{miss['query'][:50]!r} -> wanted {miss['targets']} "
                f"kind={miss.get('miss_kind', 'retrieval_miss')}"
            )
        if a.record_misses:
            queue = record_miss_queue(sem, path=Path(a.miss_queue))
            if queue.get("skipped"):
                print(
                    "  miss queue   : "
                    f"skipped=true misses={queue['misses']} reason={queue['skip_reason']}"
                )
            else:
                print(
                    "  miss queue   : "
                    f"appended={queue['appended']} misses={queue['misses']} path={queue['path']}"
                )
        return 0
    if a.semantic_live:
        live, why = semantic_live()
        print(f"SEMANTIC_LIVE={str(live).lower()} reason={why}")
        return 0 if live else 2
    if a.atlas_status:
        status = atlas_freshness_status()
        print(f"ATLAS_STATUS {status.summary()}")
        for warning in status.warnings:
            print(f"WARNING: {warning}")
        return 0 if status.ok else 2
    if a.selftest:
        return _selftest()
    if not a.query:
        ap.print_help(); return 1
    # FAIL-LOUD calibration: a dead embedder silently degrades to lexical; warn up front so a
    # 'no match' is never misread as 'safe to build' (the treadmill foot-gun).
    sem_live, sem_why = (False, "lexical-only forced") if a.lexical_only else semantic_live()
    if not sem_live:
        print(f"⚠️  SEMANTIC EMBEDDER DEAD/UNAVAILABLE: {sem_why}")
        print("    Running LEXICAL-ONLY. A 'no primitive matched' here is INADMISSIBLE —")
        print("    it may be a dead instrument, not a real absence. Run `--eval` for")
        print("    current retrieval calibration and fix GEMINI_API_KEY / atlas liveness")
        print("    before concluding a capability must be built.\n")
    hits = precheck(a.query, a.top_k, semantic=(False if a.lexical_only else None))
    if not hits:
        if sem_live:
            print("No primitive matched (semantic embedder LIVE — a real absence; the capability "
                  "may genuinely need building).")
        else:
            print(f"No primitive matched — but the SEMANTIC EMBEDDER IS DEAD ({sem_why}). This "
                  "result is INADMISSIBLE; fix the embedder and re-run before building anything.")
        return 0
    print(f"Relevant extracted primitives for: {a.query!r}\n")
    for h in hits:
        print(f"  [{h['score']:>5}] {h['signature']}   <{h.get('category','')}>")
        print(f"          {h['module']}  ({h['kind']})")
        if h["doc"]:
            print(f"          what: {h['doc'].splitlines()[0][:110]}")
        if h["when_to_use"]:
            print(f"          when: {h['when_to_use'][:110]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
