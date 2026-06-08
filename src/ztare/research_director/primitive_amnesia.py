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
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from src.ztare.research_director.scientific_amnesia import tokenize, _score

REPO = Path(__file__).resolve().parents[3]
ARCH_INDEX = REPO / "analytics" / "public" / "index" / "architecture_index.jsonl"
ATLAS_PATH = REPO / "analytics" / "public" / "index" / "primitive_atlas_embeddings.json"
_LAST_EMBED_ERROR: str | None = None

# Deterministic TAXONOMY (tiers): module-path prefix → category. Makes a 500+ flat
# catalog navigable/scopable instead of a dump. Derived on read (no row rewrite).
_CATEGORY_BY_PREFIX = [
    ("src/ztare/experiment_stats", "statistical"),
    ("src/ztare/motion", "set-distance/metric"),
    ("src/ztare/validator", "validation/scoring"),
    ("src/ztare/leanmill/solver", "proof-search"),
    ("src/ztare/leanmill", "leanmill"),
    ("src/ztare/fit", "fit/regime"),
    ("src/ztare/framer", "framing"),
    ("src/ztare/research_director", "research-operator"),
    ("src/ztare/gates", "gate"),
    ("src/ztare/product_exports", "export/judgment"),
]


def _category_for(path: str) -> str:
    for prefix, cat in _CATEGORY_BY_PREFIX:
        if (path or "").startswith(prefix):
            return cat
    return "other"

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
    "src/ztare/leanmill/semantic_premise_shelf.py",
    "src/ztare/common/constraint_isomorphism.py",  # strange loop (common/ not auto-swept)
    "src/ztare/common/sandboxed_python.py",          # the ONE sandboxed-python exec home (2026-06-07)
    "src/ztare/common/symbolic_witness.py",          # SymPy witness/recurrence/linear-system builders
    "src/ztare/fit/analogy.py",                      # GP-164 curve-fit analogy (the specialization)
]
# Directories swept for additional primitive-bearing modules (every public def/class).
PRIMITIVE_DIRS = [
    "src/ztare/research_director",   # *_ops.py operators, generators, surfaces
    "src/ztare/validator/core",      # information yield, scoring cores
    "src/ztare/motion",              # set/vector distances, motion metrics
    "src/ztare/fit",                 # fit primitives, regime combinators
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
    "score_research_avenue": "research route rank avenue MDL information yield per complexity amnesia penalty source currency next lever what to pursue",
    "score_research_avenues": "portfolio rank research avenues MDL information yield density amnesia recurrence source currency proof route priority",
    "ResearchAvenue": "candidate research route avenue receipts kill conditions expected reuse exposure amnesia hits novelty hints MDL score",
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
        from src.ztare.common.llm_runtime import LLMRuntime
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
        resp = LLMRuntime().call_text(prompt, model_id=model,
                                      fallback_model_ids=("gemini-2.5-flash",),
                                      max_tokens=4000, request_label="primitive_quality_filter",
                                      timeout_seconds=90)
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
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
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
        new_rows.append({
            "id": cid, "path": p.module, "kind": "primitive",
            "description": (p.doc.splitlines()[0][:200] if p.doc else name),
            "applicability": appl[:24],
            "impact_factor_expost": 3 if aliases else 1,   # curated high-value rank above swept
            "last_used": "", "dependencies": [], "signature": p.signature,
        })
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
                from src.ztare.common.embeddings import embed_batch, make_client
            return embed_batch(make_client(key), [text], model="gemini-embedding-001",
                               dimensions=768, task_type=tt)[0]
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
    vecs = {}
    for p in inv:
        v = _embed(f"{p.name}. {p.doc} {p.when_to_use}".strip(), role="document", backend=backend)
        if v is not None:
            vecs[p.signature or p.name] = v
    if inv and not vecs:
        if path.exists():
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
                existing = current.get("embeddings") or {}
                if existing:
                    return len(existing)
            except Exception:
                pass
        return 0
    path.write_text(json.dumps({"backend": backend, "n": len(vecs), "embeddings": vecs}),
                    encoding="utf-8")
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
        cand.sort(key=lambda i: (sem.get(i, 0.0), lex_by_i.get(i, 0.0)), reverse=True)
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


def evaluate(top_k: int = 5, *, semantic: "bool | None" = None) -> dict:
    """Recall@k + MRR over the held-out benchmark. The world-class discipline:
    MEASURE retrieval, don't assert it. `semantic=False` forces the lexical baseline
    so the semantic lift is quantified on the same queries."""
    inv = build_inventory()
    hits_at_k = 0; rr_sum = 0.0; misses = []
    for query, targets in BENCHMARK:
        ranked = precheck(query, top_k=top_k, inventory=inv, semantic=semantic)
        names = [(h["name"] + " " + h["signature"]).lower() for h in ranked]
        rank = next((r for r, n in enumerate(names, 1)
                     if any(t in n for t in targets)), None)
        if rank:
            hits_at_k += 1; rr_sum += 1.0 / rank
        else:
            misses.append((query[:50], targets))
    n = len(BENCHMARK)
    return {"n": n, "recall_at_k": round(hits_at_k / n, 3), "k": top_k,
            "mrr": round(rr_sum / n, 3), "misses": misses}


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
        from src.ztare.common.embedder_liveness import embedder_live
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
    ap.add_argument("--semantic-live", action="store_true",
                    help="positive-control the semantic embedder + atlas and print the result")
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
        print(f"embedded {n} primitives into the semantic atlas (backend={a.embedder}).")
        return 0
    if a.eval:
        k = a.top_k if a.top_k != 8 else 5
        lex = evaluate(top_k=k, semantic=False)
        sem = evaluate(top_k=k, semantic=True)
        print(f"HELD-OUT BENCHMARK (n={sem['n']}, k={k}):")
        print(f"  lexical-only : recall@{k}={lex['recall_at_k']}  MRR={lex['mrr']}")
        print(f"  semantic     : recall@{k}={sem['recall_at_k']}  MRR={sem['mrr']}  (the lift)")
        for q, t in sem["misses"]:
            print(f"  semantic MISS: {q!r} -> wanted {t}")
        return 0
    if a.semantic_live:
        live, why = semantic_live()
        print(f"SEMANTIC_LIVE={str(live).lower()} reason={why}")
        return 0 if live else 2
    if a.selftest:
        return _selftest()
    if not a.query:
        ap.print_help(); return 1
    # FAIL-LOUD calibration: a dead embedder silently degrades to lexical; warn up front so a
    # 'no match' is never misread as 'safe to build' (the treadmill foot-gun).
    sem_live, sem_why = (False, "lexical-only forced") if a.lexical_only else semantic_live()
    if not sem_live:
        print(f"⚠️  SEMANTIC EMBEDDER DEAD/UNAVAILABLE: {sem_why}")
        print("    Running LEXICAL-ONLY (recall ~0.67 vs semantic 1.0). A 'no primitive matched'")
        print("    here is INADMISSIBLE — it may be a dead instrument, not a real absence. Set")
        print("    GEMINI_API_KEY (or --build-atlas) before concluding a capability must be built.\n")
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
