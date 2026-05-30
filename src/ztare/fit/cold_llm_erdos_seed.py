"""GP-169 Phase 1 — Cold LLM as synthetic Erdős, iter-1 seed.

Runs a single, strictly-anonymized LLM call before iter 1 fires. The
prompt explicitly forbids the substrate's home discipline so the
model is forced to reach for cross-domain forms (the Erdős move:
known method, applied where no one thought to apply it). Returns
three structurally-distinct parametric forms that get injected into
iter-1's mutator briefing as MANDATORY-CONSIDER alternatives.

Distinct from the existing ANALOGY mechanism in three ways:

  1. Fires at iter 1, not on stagnation. The Erdős case shows the
     right move is at the start, not after exploring the home
     repertoire.
  2. Uses a SEPARATE LLM (cold call, no shared context with mutator
     or judge). The mutator is contaminated by the substrate's
     visible labels, residual diagnostics, and form vocabulary; a
     cold call is unburdened by all of that.
  3. The prompt explicitly forbids the substrate's home discipline
     (via `forbidden_domain` arg). This forces non-canonical
     application — the Erdős mechanism.

Per GP-169 seam §Phase 1.

Output is the new file `workspace/cold_llm_seed_iter0.json` consumed
by the cold_llm_seed briefing provider (see briefing_providers/).
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ColdSeedCandidate:
    name: str = ""
    form: str = ""
    field_of_origin: str = ""
    what_it_captures: str = ""
    valid_python: bool = False
    validation_error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "form": self.form,
            "field_of_origin": self.field_of_origin,
            "what_it_captures": self.what_it_captures,
            "valid_python": self.valid_python,
            "validation_error": self.validation_error,
        }


@dataclass
class ColdSeedResponse:
    candidates: list[ColdSeedCandidate] = field(default_factory=list)
    model_id_used: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    raw_text: str = ""
    error: Optional[str] = None
    forbidden_domain: Optional[str] = None
    fingerprint_signature: str = ""
    qualitative_mode: bool = False

    def to_dict(self) -> dict:
        return {
            "candidates": [c.to_dict() for c in self.candidates],
            "model_id_used": self.model_id_used,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "raw_text_excerpt": self.raw_text[:1000],
            "error": self.error,
            "forbidden_domain": self.forbidden_domain,
            "fingerprint_signature": self.fingerprint_signature,
            "qualitative_mode": self.qualitative_mode,
        }


# Vanilla baselines that signal the cold LLM degenerated to trivial forms.
# Same regex set as analogy.py's vanilla-rejector.
_VANILLA_BASELINES = [
    re.compile(r"^\s*(params\['?\w+'?\]|[a-zA-Z_]+)\s*$"),
    re.compile(r"^\s*params\['?\w+'?\]\s*\*\s*features\['?\w+'?\]\s*\+\s*params\['?\w+'?\]\s*$"),
    re.compile(r"^\s*params\['?\w+'?\]\s*\*\s*exp\s*\(\s*params\['?\w+'?\]\s*\*\s*features\['?\w+'?\]\s*\)\s*$"),
]

# Panel-Blindspot-1 (2026-04-27): quantize the fingerprint into broad buckets
# so a frontier LLM cannot reverse-identify the substrate from the signature.
# 11-decade dynamic range + 3 classes is a near-unique signature for the RAR;
# bucketed signatures match dozens of substrates.

def _bucket_dynamic_range(dec: float) -> str:
    if dec is None:
        return "unknown"
    try:
        d = float(dec)
    except (TypeError, ValueError):
        return "unknown"
    if d < 3:
        return "narrow_<3dec"
    if d < 6:
        return "moderate_3to6dec"
    return "wide_>6dec"


def _bucket_class_count(n: int) -> str:
    if n is None:
        return "unknown"
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "unknown"
    if n <= 1:
        return "single_class"
    if n <= 4:
        return "few_2to4"
    return "many_>4"


def quantize_fingerprint(fingerprint: dict) -> dict:
    """Apply Panel-Blindspot-1 anonymization: replace specific numeric values
    with broad buckets so the fingerprint matches many substrate templates
    rather than uniquely identifying one."""
    out = dict(fingerprint)  # shallow copy preserves any non-quantized fields
    if "y_dynamic_range_decades" in out:
        out["y_dynamic_range_decades"] = _bucket_dynamic_range(
            out.get("y_dynamic_range_decades")
        )
    if "n_visible_classes" in out:
        out["n_visible_classes"] = _bucket_class_count(out.get("n_visible_classes"))
    if "n_withheld_classes" in out:
        out["n_withheld_classes"] = _bucket_class_count(out.get("n_withheld_classes"))
    if "regime_break_count" in out:
        rb = out.get("regime_break_count")
        try:
            rb = int(rb) if rb is not None else 0
        except (TypeError, ValueError):
            rb = 0
        out["regime_break_count"] = "none" if rb == 0 else ("one" if rb == 1 else "multiple")
    return out


# Panel-Blindspot-4 (2026-04-27): stricter form validation. The cold LLM
# (without context for the apparatus's whitelist) frequently writes
# `numpy.exp`, `math.gamma`, `scipy.special.erfc`, or unbound names like
# `Sigmoid` or `BesselK`. These parse via `ast.parse` but fail at fit time.
# Validate identifiers against the apparatus whitelist at acceptance time.
_APPARATUS_FUNCTION_WHITELIST = frozenset({
    "abs", "bool", "cos", "erf", "exp", "float", "int", "len", "log",
    "log10", "max", "min", "sigmoid", "sin", "sqrt", "str", "tan", "tanh",
    "where",
})

# Subscript bases that are allowed (features dict, params dict)
_APPARATUS_ALLOWED_SUBSCRIPT_BASES = frozenset({"features", "params"})

# Module prefixes the cold LLM commonly emits — REJECTED (Blindspot 4).
_FORBIDDEN_MODULE_PREFIXES = frozenset({
    "math", "np", "numpy", "scipy", "torch", "tf", "jax", "sympy",
})

# Python control-flow keywords that the LLM may try to use — REJECTED.
# Detected via regex BEFORE ast.parse since some of these (lambda) parse
# fine and would otherwise pass the whitelist check.
_FORBIDDEN_CONTROL_FLOW_RE = re.compile(
    r"\b(if|else|for|while|lambda|yield|return|class|def|import|from|with)\b"
)


def _build_qualitative_cold_seed_prompt(
    substrate_domain: str,
    forbidden_domain: Optional[str],
) -> str:
    """Prompt for qualitative substrates: returns thesis argument structures,
    NOT Python expressions. The JSON schema uses `argument_structure` instead
    of `form` so the briefing provider can render prose, not code blocks."""
    forbid_clause = ""
    if forbidden_domain:
        forbid_clause = (
            f"\nFORBIDDEN FIELDS: do NOT draw argument structures from "
            f"{forbidden_domain} or directly adjacent fields. "
            f"The goal is cross-domain structural novelty — argument forms "
            f"the home field would NOT propose on its own.\n"
        )
    return (
        "You are a structural philosopher of science with cross-disciplinary "
        "fluency in causal inference, formal epistemology, measurement theory, "
        "decision theory, topology, information theory, and game theory. "
        "You are given a qualitative reasoning problem and asked to propose "
        "argument structures that could make the problem tractable.\n\n"
        f"The substrate domain is: {substrate_domain}\n"
        f"{forbid_clause}\n"
        "Propose 3 structurally distinct argument families, each from a "
        "DIFFERENT field. Each must specify a NON-TRIVIAL STRUCTURAL COMMITMENT "
        "— a formal move that transforms the problem, not a vague analogy.\n\n"
        "Output MUST be a JSON object with this exact schema "
        "(no markdown, no prose outside JSON):\n"
        "{\n"
        '  "qualitative_mode": true,\n'
        '  "candidates": [\n'
        "    {\n"
        '      "name": "short identifier",\n'
        '      "argument_structure": "the core formal move (2-4 sentences, '
        'precise — what object does it introduce, what does it prove or '
        'rule out, what condition makes it applicable)",\n'
        '      "field_of_origin": "the cross-domain field this comes from",\n'
        '      "what_it_captures": "what aspect of the problem this resolves"\n'
        "    },\n"
        '    ... (exactly 3 candidates) ...\n'
        "  ]\n"
        "}\n\n"
        "Return ONLY the JSON object."
    )


def _build_cold_seed_prompt(
    fingerprint: dict,
    forbidden_domain: Optional[str],
    k_law_budget: int,
) -> str:
    """Render the strictly-anonymized prompt for the cold LLM call.

    Routes to `_build_qualitative_cold_seed_prompt` for qualitative substrates
    (no Python expressions; returns thesis argument structures instead).
    """
    if fingerprint.get("_qualitative_substrate"):
        return _build_qualitative_cold_seed_prompt(
            substrate_domain=str(
                fingerprint.get("substrate_domain") or "qualitative reasoning"
            ),
            forbidden_domain=forbidden_domain,
        )

    fp_dict = {
        k: v for k, v in fingerprint.items()
        if k in {
            "shape",
            "monotonicity",
            "regime_break_count",
            "heavy_tail_flag",
            "sign_pattern",
            "y_dynamic_range_decades",
            "n_visible_classes",
            "n_withheld_classes",
        }
    }
    forbid_clause = ""
    if forbidden_domain:
        forbid_clause = (
            f"\nFORBIDDEN DOMAINS: do NOT use methods or forms from "
            f"{forbidden_domain}, or fields directly adjacent to it. The "
            f"point of this query is to surface forms the home discipline "
            f"would NOT propose. Pick three forms FROM DIFFERENT FIELDS — "
            f"e.g. one from economics (option pricing, dose-response, "
            f"yield curves), one from biology (enzyme kinetics, "
            f"population dynamics, allometric scaling), one from "
            f"statistical mechanics or pure math (RG flow, modular "
            f"forms, multifractal spectra, percolation, persistence "
            f"diagrams). The forms must be ALGEBRAICALLY DISTINCT — not "
            f"three variants of the same logistic; three structurally "
            f"different mathematical objects.\n"
        )
    return (
        "You are a structural mathematician with cross-disciplinary fluency in "
        "information geometry, scale-invariant analysis, modular forms, "
        "multifractal analysis, RG flow, persistent homology, dynamical "
        "systems, and special functions. You have NO knowledge of what "
        "this data represents.\n\n"
        "A symbolic regression apparatus needs three structurally-distinct "
        "closed-form candidates for fitting an unknown relation. The data "
        "has the following anonymized structural fingerprint:\n\n"
        f"{json.dumps(fp_dict, indent=2)}\n\n"
        f"Constraints:\n"
        f"  * K_law ≤ {k_law_budget} fitted constants per form\n"
        f"  * Available primitives: arithmetic, sqrt, exp, log, log10, "
        f"sin, cos, tan, tanh, sigmoid, erf, where, abs, max, min\n"
        f"  * Each form must be expressible as a single Python expression "
        f"using `features['<key>']` and `params['<name>']` accessors\n"
        f"  * Avoid trivial baselines (constant, linear, single exponential)\n"
        f"{forbid_clause}\n"
        "Output MUST be a JSON object with this exact schema (no markdown, "
        "no prose outside JSON):\n"
        "{\n"
        '  "candidates": [\n'
        "    {\n"
        '      "name": "short identifier",\n'
        '      "form": "single Python expression",\n'
        '      "field_of_origin": "the cross-domain field this form comes from",\n'
        '      "what_it_captures": "one sentence about what feature of '
        "the fingerprint this form captures\"\n"
        "    },\n"
        '    ... (exactly 3 candidates) ...\n'
        "  ]\n"
        "}\n\n"
        "Return ONLY the JSON object."
    )


def _validate_candidate_form(form_str: str) -> tuple[bool, Optional[str]]:
    """Strict validation per Panel-Blindspot-4 (2026-04-27). Catches:
      - empty / whitespace-only
      - Python control-flow keywords (regex pre-check before ast.parse)
      - module prefixes (numpy.exp, math.gamma, scipy.special.*)
      - identifiers outside the apparatus whitelist
      - vanilla-baseline trivial forms
      - subscript bases that are not features/params
    Returns (valid, error_message)."""
    if not form_str or not form_str.strip():
        return False, "empty form string"
    # Regex pre-check: Python control-flow keywords (caught before ast.parse
    # because lambda/yield parse fine but are forbidden).
    cf_match = _FORBIDDEN_CONTROL_FLOW_RE.search(form_str)
    if cf_match:
        return False, f"forbidden Python keyword '{cf_match.group(0)}' in form"
    try:
        import ast as _ast
        tree = _ast.parse(form_str, mode="eval")
    except SyntaxError as e:
        return False, f"SyntaxError: {e.msg}"
    for pat in _VANILLA_BASELINES:
        if pat.match(form_str):
            return False, "matched vanilla baseline regex (trivial form)"
    # AST walk: every Name node referenced as a function call must be in
    # the apparatus whitelist; every Subscript base must be features/params;
    # every Attribute access (math.exp etc.) is forbidden.
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name):
            if node.func.id not in _APPARATUS_FUNCTION_WHITELIST:
                return False, (
                    f"unknown function '{node.func.id}' (not in apparatus whitelist: "
                    f"{sorted(_APPARATUS_FUNCTION_WHITELIST)})"
                )
        elif isinstance(node, _ast.Attribute):
            # math.exp, np.log, scipy.special.erfc — all forbidden
            base = node.value
            base_id = base.id if isinstance(base, _ast.Name) else None
            if base_id in _FORBIDDEN_MODULE_PREFIXES:
                return False, (
                    f"forbidden module prefix '{base_id}.{node.attr}'; use bare "
                    f"function names (e.g. exp(x), not {base_id}.exp(x))"
                )
        elif isinstance(node, _ast.Subscript):
            base = node.value
            if isinstance(base, _ast.Name):
                if base.id not in _APPARATUS_ALLOWED_SUBSCRIPT_BASES:
                    return False, (
                        f"unknown subscript base '{base.id}'; only "
                        f"features['...'] and params['...'] are allowed"
                    )
    return True, None


def query_cold_llm_erdos_seed(
    fingerprint: dict,
    *,
    model_id: str,
    runtime: Optional[Any] = None,
    forbidden_domain: Optional[str] = None,
    k_law_budget: int = 7,
    timeout_seconds: float = 120.0,
    project_dir: Optional[Any] = None,
    rubric_data: Optional[dict] = None,
) -> ColdSeedResponse:
    """Run the cold-LLM Erdős seed query.

    Args:
        fingerprint: anonymized residual fingerprint (from substrate
            critic + noise profile baseline). Keys read:
            shape, monotonicity, regime_break_count, heavy_tail_flag,
            sign_pattern, y_dynamic_range_decades, n_visible_classes,
            n_withheld_classes. Anything else in the dict is IGNORED.
        model_id: required. Convention: a model from a different family
            than the run's mutator AND judge (cross-family hygiene).
            Operator picks via rubric.cold_llm_seed_model_id.
        runtime: LLMRuntime instance. Constructed if None.
        forbidden_domain: substrate's home discipline (e.g.
            "astrophysics" for gp163d, "computer_science" for gp154).
            The prompt explicitly forbids this domain.
        k_law_budget: max K per candidate form.
        timeout_seconds: LLM call timeout.

    Returns:
        ColdSeedResponse with up to 3 validated candidates.
    """
    if not model_id:
        return ColdSeedResponse(
            error="no model_id supplied; cold-LLM seed needs an explicit "
                  "model_id (operator picks via rubric.cold_llm_seed_model_id)",
            forbidden_domain=forbidden_domain,
        )
    if runtime is None:
        from src.ztare.common.llm_runtime import LLMRuntime as _LLMRuntime
        runtime = _LLMRuntime()

    fp_signature = json.dumps(
        {k: v for k, v in fingerprint.items() if not isinstance(v, (dict, list))},
        sort_keys=True,
    )[:200]

    # LLMCallCache lookup (2026-04-28). Same fingerprint + forbidden
    # domain + k_law budget + model id ⇒ same response. Activates only
    # when a project_dir is provided (legacy callers without it skip
    # caching). Operator override: rubric.cold_llm_seed_force_refresh.
    _cache = None
    _cache_key = None
    if project_dir is not None:
        try:
            from pathlib import Path as _Path
            from src.ztare.common.llm_cache import LLMCallCache, ttl_30_days
            _cache = LLMCallCache(
                callsite="cold_llm_erdos_seed",
                project_dir=_Path(project_dir),
                prompt_template_version=1,
                ttl_seconds=ttl_30_days,
                force_refresh_flag="cold_llm_seed_force_refresh",
            )
            _cache_key = _cache.compute_key({
                "fingerprint_signature": fp_signature,
                "forbidden_domain": forbidden_domain,
                "k_law_budget": k_law_budget,
                "model_id": model_id,
            })
            _hit = _cache.lookup(_cache_key, rubric_data=rubric_data)
            if _hit is not None:
                # Reconstruct ColdSeedResponse from cached payload.
                cached_candidates = [
                    ColdSeedCandidate(**c) for c in _hit.get("candidates", [])
                ]
                return ColdSeedResponse(
                    candidates=cached_candidates,
                    error=_hit.get("error"),
                    model_id_used=_hit.get("model_id_used", model_id),
                    forbidden_domain=forbidden_domain,
                    fingerprint_signature=fp_signature,
                )
        except Exception:                                              # noqa: BLE001
            _cache = None  # cache failure must never break the call

    prompt = _build_cold_seed_prompt(fingerprint, forbidden_domain, k_law_budget)

    try:
        response = runtime.call_text(
            prompt,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
            request_label="gp169_cold_llm_erdos_seed",
            retries=2,
        )
    except Exception as exc:
        return ColdSeedResponse(
            error=f"{type(exc).__name__}: {exc!s}"[:300],
            model_id_used=model_id,
            forbidden_domain=forbidden_domain,
            fingerprint_signature=fp_signature,
        )

    raw = response.text or ""
    usage = response.usage if hasattr(response, "usage") else None
    tokens_in = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
    tokens_out = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
    actual_model_id = getattr(response, "model_id_used", model_id) or model_id

    out = ColdSeedResponse(
        model_id_used=actual_model_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        raw_text=raw,
        forbidden_domain=forbidden_domain,
        fingerprint_signature=fp_signature,
    )

    parsed = _parse_cold_llm_json(raw)
    if not parsed:
        out.error = "cold_llm_response_unparseable"
        return out

    raw_candidates = parsed.get("candidates", [])
    if not isinstance(raw_candidates, list):
        out.error = "cold_llm_response_missing_candidates_list"
        return out

    is_qualitative = bool(
        fingerprint.get("_qualitative_substrate")
        or parsed.get("qualitative_mode")
    )
    out.qualitative_mode = is_qualitative

    for cand in raw_candidates[:3]:  # cap at 3 even if model returns more
        # Qualitative candidates use `argument_structure`; numerical use `form`.
        form_or_structure = str(
            cand.get("argument_structure") or cand.get("form", "")
        )[:1000]
        c = ColdSeedCandidate(
            name=str(cand.get("name", ""))[:80],
            form=form_or_structure,
            field_of_origin=str(cand.get("field_of_origin", ""))[:80],
            what_it_captures=str(cand.get("what_it_captures", ""))[:300],
        )
        if is_qualitative:
            # Argument structures are prose — Python validation doesn't apply.
            # Mark valid=True so the briefing provider surfaces them.
            c.valid_python = True
            c.validation_error = None
        else:
            ok, err = _validate_candidate_form(c.form)
            c.valid_python = ok
            c.validation_error = err
        out.candidates.append(c)

    if not any(c.valid_python for c in out.candidates):
        out.error = "all_candidates_failed_validation"

    # Cache the fresh response so the next identical-input run hits.
    if _cache is not None and _cache_key is not None:
        try:
            _cache.store(
                _cache_key,
                payload={
                    "candidates": [
                        {
                            "name": c.name,
                            "form": c.form,
                            "field_of_origin": c.field_of_origin,
                            "what_it_captures": c.what_it_captures,
                            "valid_python": c.valid_python,
                            "validation_error": c.validation_error,
                        } for c in out.candidates
                    ],
                    "error": out.error,
                    "model_id_used": out.model_id_used,
                },
                model_id_used=out.model_id_used,
            )
        except Exception:                                              # noqa: BLE001
            pass  # cache write failure must not break the return

    return out


def _parse_cold_llm_json(raw: str) -> Optional[dict]:
    """Parse the cold-LLM's JSON response. Strip markdown fences if
    present (anthropic and openai both occasionally wrap JSON in them
    despite the prompt asking for raw JSON)."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    stripped = raw.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        stripped = "\n".join(
            ln for ln in lines if not ln.strip().startswith("```")
        )
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        # Last resort: find the first balanced JSON object in the text
        depth = 0
        start = -1
        for i, ch in enumerate(stripped):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start >= 0:
                    candidate = stripped[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        pass
        return None


def write_cold_seed_log(
    workspace_dir: "Path",  # type: ignore
    response: ColdSeedResponse,
) -> "Path":  # type: ignore
    """Persist the cold-LLM seed response to workspace/cold_llm_seed_iter0.json."""
    from pathlib import Path
    out_path = Path(workspace_dir) / "cold_llm_seed_iter0.json"
    # 2026-04-26: ensure workspace/ exists (after `make wipe-sandbox`, the
    # workspace dir is deleted; pre-iter-1 dispatch fires before any other
    # workspace artifact is written, so we mkdir defensively here).
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(response.to_dict(), indent=2), encoding="utf-8")
    return out_path
