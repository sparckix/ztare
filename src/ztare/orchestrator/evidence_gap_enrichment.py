"""META-GATE 2 — G-EVIDENCE-GAP-ENRICHMENT (EGE).

When R26 (G-CROSS-CLASS-FEATURE-SUPPORT, in
`diagnostics/substrate_critic.py`) reports a non-empty
`withheld_class_feature_collapses` list, the substrate has a
within-withheld-class data ceiling that no apparatus tweak can break:
extra rows of the same constant feature value cannot create degrees of
freedom. The fix is OPERATOR-SIDE: enrich the substrate from
literature.

This module mechanizes the apparatus-side TRIGGER for that workflow.
For each `(class, feature)` collapse, an LLM with web-search capability
proposes literature sources that publish per-system values of the
collapsed feature for the class's system_ids. The output is a list of
PROPOSALS — the operator reviews, decides, and (separately) runs
`make enrich-substrate` to execute. Nothing here writes to the
substrate.

This is the apparatus side of the Karpathy "RAM-loop": ZTARE stays
ALU; external evidence accumulation is RAM. EGE is the apparatus's
hand raised when the RAM is the bottleneck.

Cost contract (degraded-mode, fail-graceful):
  * 60s wall-clock per gap
  * ~3K input tokens, ~3K output tokens
  * On any failure: log a warning, return empty proposals; the run
    continues normally.

Output: `workspace/evidence_gap_enrichment_proposals.json` —
operator reads + decides.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvidenceGapProposal:
    """A single literature proposal for a (class, feature) collapse."""
    paper_title: str = ""
    year: Optional[int] = None
    arxiv_id_or_url: str = ""
    system_id_overlap_estimate: str = ""  # e.g. "high", "moderate", "low"; or "%~30 of class C IDs"
    expected_dex_range: str = ""  # e.g. "0.5 dex" or "log10 mass 7.5–11.0"
    extraction_difficulty: str = ""  # e.g. "machine-readable table", "OCR from figure"
    confidence: str = ""  # e.g. "high", "moderate", "low"
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "paper_title": self.paper_title,
            "year": self.year,
            "arxiv_id_or_url": self.arxiv_id_or_url,
            "system_id_overlap_estimate": self.system_id_overlap_estimate,
            "expected_dex_range": self.expected_dex_range,
            "extraction_difficulty": self.extraction_difficulty,
            "confidence": self.confidence,
            "notes": self.notes,
        }


@dataclass
class EvidenceGapVerdict:
    attempted: bool = False
    n_gaps_seen: int = 0
    proposals_by_gap: list[dict] = field(default_factory=list)
    model_id_used: str = ""
    tokens_in_total: int = 0
    tokens_out_total: int = 0
    error: Optional[str] = None
    artifact_path: Optional[str] = None
    input_hash: Optional[str] = None
    cache_hit: bool = False

    def to_dict(self) -> dict:
        return {
            "attempted": self.attempted,
            "n_gaps_seen": self.n_gaps_seen,
            "proposals_by_gap": self.proposals_by_gap,
            "model_id_used": self.model_id_used,
            "tokens_in_total": self.tokens_in_total,
            "tokens_out_total": self.tokens_out_total,
            "error": self.error,
            "artifact_path": self.artifact_path,
            "input_hash": self.input_hash,
            "cache_hit": self.cache_hit,
        }


# ── Substrate-side metadata collection ────────────────────────────────


def _collect_class_system_ids(
    project_dir: Path,
    target_class: str,
    substrate_class_key: str,
    *,
    max_ids: int = 10,
) -> list[str]:
    """Best-effort: load features.py and extract up to `max_ids`
    system_id examples from the target_class. The substrate's
    `farther_tail_rows()` is read because R26 collapses fire on
    withheld classes. Returns string IDs; empty list on any failure.
    """
    try:
        import importlib.util as _ilu
        import sys as _sys
        feat_path = project_dir / "features.py"
        if not feat_path.exists():
            return []
        spec = _ilu.spec_from_file_location("_ege_features", str(feat_path))
        if spec is None or spec.loader is None:
            return []
        if str(project_dir) not in _sys.path:
            _sys.path.insert(0, str(project_dir))
        feat_mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(feat_mod)
    except Exception:
        return []
    rows: list[Any] = []
    if hasattr(feat_mod, "farther_tail_rows"):
        try:
            rows = list(feat_mod.farther_tail_rows())
        except Exception:
            rows = []
    if not rows and hasattr(feat_mod, "all_rows"):
        try:
            rows = list(feat_mod.all_rows())
        except Exception:
            rows = []
    out: list[str] = []
    for tup in rows:
        if len(tup) < 3:
            continue
        sid, _y, fx = tup[0], tup[1], tup[2]
        if not isinstance(fx, dict):
            continue
        cls = fx.get(substrate_class_key)
        if cls is None:
            continue
        if str(cls) != str(target_class):
            continue
        out.append(str(sid))
        if len(out) >= max_ids:
            break
    return out


# ── Prompt construction ───────────────────────────────────────────────


def _build_ege_prompt(
    *,
    target_class: str,
    feature_name: str,
    feature_meaning: str,
    system_id_examples: list[str],
    substrate_class: str,
    forbidden_domain: Optional[str],
    n_collapsed_rows: int,
) -> str:
    """Render the gap-enrichment prompt. The prompt explicitly hints at
    web search but does NOT call the WebSearch tool itself — operators
    typically run this with a model whose runtime backs literature
    lookup (e.g. a model with built-in browsing). The proposals are
    treated as suggestions regardless of whether the model actually
    browsed; the operator verifies."""
    examples_str = ", ".join(system_id_examples[:10]) or "(no examples available)"
    fbd = forbidden_domain or "(unspecified)"
    return (
        "You are a literature-search assistant for a symbolic-regression "
        "research apparatus. The apparatus has a SUBSTRATE-DATA CEILING: a "
        "feature collapses to a near-constant value within one withheld "
        "class. No apparatus tweak can fix this — the substrate must be "
        "enriched from literature.\n\n"
        f"Substrate class label: {substrate_class}\n"
        f"Within-class collapse: class={target_class!r}, feature={feature_name!r}\n"
        f"Feature meaning: {feature_meaning}\n"
        f"Number of collapsed rows: {n_collapsed_rows}\n"
        f"Example system_ids in this class: [{examples_str}]\n"
        f"Substrate's home-discipline hint: {fbd}\n\n"
        "TASK: Propose published catalogs/papers/datasets that provide "
        f"per-system values of {feature_name!r} for the system_ids above. "
        "If your runtime has WebSearch capability available, USE IT before "
        "answering — search arxiv, ADS, NASA/IPAC, NED, SIMBAD, Vizier, "
        "domain databases as appropriate. Return only proposals you can "
        "name a real reference for; do not invent papers.\n\n"
        "For each proposal, evaluate:\n"
        "  * paper_title, year, arxiv_id_or_url\n"
        "  * system_id_overlap_estimate — qualitative ('high'/'moderate'/'low') "
        "    or '%~N of listed IDs' if you can estimate\n"
        "  * expected_dex_range — what range of values your knowledge says the "
        f"    {feature_name!r} should span across these IDs (a substrate that "
        f"    is currently constant at one value must move at least 0.3 dex to "
        f"    add useful DoF)\n"
        "  * extraction_difficulty — 'machine-readable table' / 'paper appendix' / "
        "    'OCR from figure'\n"
        "  * confidence — 'high'/'moderate'/'low'\n"
        "  * notes — anything the operator should know\n\n"
        "Return at most 5 proposals. If you have NO candidates, return an empty "
        "list. Better to return 1 high-confidence proposal than 5 speculative ones.\n\n"
        "Output MUST be a single JSON object with this schema, no markdown:\n"
        "{\n"
        '  "proposals": [\n'
        "    {\n"
        '      "paper_title": "...",\n'
        '      "year": 2018,\n'
        '      "arxiv_id_or_url": "...",\n'
        '      "system_id_overlap_estimate": "...",\n'
        '      "expected_dex_range": "...",\n'
        '      "extraction_difficulty": "...",\n'
        '      "confidence": "...",\n'
        '      "notes": "..."\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Return ONLY the JSON object."
    )


def _parse_ege_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    s = raw.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        s = "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
    depth = 0
    start = -1
    for i, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(s[start:i + 1])
                except json.JSONDecodeError:
                    pass
    return None


# ── Public entry point ────────────────────────────────────────────────


def propose_evidence_gap_enrichment(
    project_dir: Path | str,
    *,
    rubric_data: Optional[dict] = None,
    mutator_model_id: Optional[str] = None,
    enrichment_model_id: Optional[str] = None,
    timeout_seconds: float = 60.0,
    max_input_tokens: int = 3000,
    max_output_tokens: int = 3000,
    runtime: Any = None,
) -> dict:
    """For each R26 (class, feature) collapse, ask an LLM for literature
    candidates. Writes proposals; the operator decides whether to act.

    Args:
        project_dir: project root.
        rubric_data: rubric dict (used for substrate_class_key + the
            forbidden_domain hint and the model-id sentinel).
        mutator_model_id: pass-through for the @mutator sentinel.
        enrichment_model_id: explicit override; if None, resolves
            rubric.evidence_gap_model_id (default: @mutator).
        timeout_seconds, max_input_tokens, max_output_tokens: cost cap.

    Returns:
        verdict.to_dict()
    """
    project_dir = Path(project_dir)
    workspace_dir = project_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    rubric_data = rubric_data or {}

    verdict = EvidenceGapVerdict(attempted=True)

    critique_path = workspace_dir / "substrate_critique.json"
    if not critique_path.exists():
        verdict.error = "no substrate_critique.json found; nothing to enrich"
        _persist_ege(workspace_dir, verdict)
        return verdict.to_dict()

    try:
        critique = json.loads(critique_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        verdict.error = f"could not load substrate_critique.json: {exc}"
        _persist_ege(workspace_dir, verdict)
        return verdict.to_dict()

    collapses = critique.get("withheld_class_feature_collapses") or []
    verdict.n_gaps_seen = len(collapses)
    if not collapses:
        # Nothing to do — exit clean
        _persist_ege(workspace_dir, verdict)
        return verdict.to_dict()

    # Cache check via the common LLMCallCache util (2026-04-28). EGE
    # makes one reasoning-model call per (class, feature) collapse; on
    # gp163d that is 6× gpt-5.5 calls @ ~$0.50-0.80 each, ~$3-5 every
    # run. Identical inputs (substrate critique + rubric domain + model
    # id) produce identical output, so cache by input hash. Operator
    # bypasses with rubric.evidence_gap_force_refresh=true.
    #
    # Hash-key invariant (audit-fix 2026-04-28): always use the
    # *resolved* model id in the cache key. The sentinel `@mutator`
    # collapses to `mutator_model_id` here so backfill scripts and the
    # live code agree on the same canonical form. The earlier version
    # used the unresolved sentinel + `mutator_model_id` as separate
    # fields, which produced different hashes for callers that handed
    # the resolved id directly vs. via the sentinel.
    from ztare.common.llm_cache import LLMCallCache, ttl_30_days
    raw_model_id = str(
        enrichment_model_id
        or rubric_data.get("evidence_gap_model_id")
        or "@mutator"
    ).strip()
    _resolved_model_id = (
        mutator_model_id if raw_model_id in ("@mutator", "mutator", "") else raw_model_id
    )
    _ege_cache = LLMCallCache(
        callsite="evidence_gap_enrichment",
        project_dir=project_dir,
        prompt_template_version=1,
        ttl_seconds=ttl_30_days,
        force_refresh_flag="evidence_gap_force_refresh",
    )
    _cache_hash = _ege_cache.compute_key({
        "critique_collapses": collapses,
        "forbidden_domain": rubric_data.get("forbidden_domain"),
        "substrate_class_key": rubric_data.get("substrate_class_key"),
        "model_id": _resolved_model_id,
    })
    _hit = _ege_cache.lookup(_cache_hash, rubric_data=rubric_data)
    if _hit is not None:
        logger.info("EGE cache hit (hash=%s); %d LLM call(s) skipped",
                    _cache_hash, len(collapses))
        cached_verdict = EvidenceGapVerdict(attempted=True)
        cached_verdict.n_gaps_seen = _hit.get("n_gaps_seen", len(collapses))
        cached_verdict.proposals_by_gap = _hit.get("proposals_by_gap", [])
        cached_verdict.model_id_used = _hit.get("model_id_used", raw_model_id)
        cached_verdict.tokens_in_total = _hit.get("tokens_in_total", 0)
        cached_verdict.tokens_out_total = _hit.get("tokens_out_total", 0)
        cached_verdict.error = _hit.get("error")
        cached_verdict.input_hash = _cache_hash
        cached_verdict.cache_hit = True
        # Persist the canonical proposals JSON for downstream readers
        # so consumers don't have to know about the cache layer.
        _persist_ege(workspace_dir, cached_verdict)
        return cached_verdict.to_dict()

    # Stamp the verdict with the input hash so the next run's cache
    # lookup can match against this run's payload.
    verdict.input_hash = _cache_hash

    # Resolve the enrichment model id.
    raw_id = (enrichment_model_id or rubric_data.get("evidence_gap_model_id") or "@mutator")
    raw_id = str(raw_id).strip()
    if raw_id in ("", "@mutator", "mutator"):
        if not mutator_model_id:
            verdict.error = (
                "evidence_gap_model_id is '@mutator' but no mutator_model_id "
                "supplied at dispatch — autoresearch_loop must pass it through"
            )
            _persist_ege(workspace_dir, verdict)
            return verdict.to_dict()
        model_id = str(mutator_model_id)
    else:
        model_id = raw_id
    verdict.model_id_used = model_id

    if runtime is None:
        try:
            from ztare.common.llm_runtime import LLMRuntime as _LLMRuntime
            runtime = _LLMRuntime()
        except Exception as exc:  # noqa: BLE001
            verdict.error = f"LLMRuntime unavailable: {exc}"
            _persist_ege(workspace_dir, verdict)
            return verdict.to_dict()

    substrate_class_key = str(rubric_data.get("substrate_class_key") or "")
    substrate_class_label = str(rubric_data.get("substrate_class") or critique.get("project") or "")
    forbidden_domain = rubric_data.get("cold_llm_seed_forbidden_domain")  # reuse the existing hint

    proposals_by_gap: list[dict] = []
    for collapse in collapses[:8]:  # cap gaps per run
        target_class = str(collapse.get("class", ""))
        feature_name = str(collapse.get("feature_key", ""))
        n_rows = int(collapse.get("n_rows") or 0)
        # Best-effort feature meaning: not in critique by default; leave blank
        feature_meaning = str(collapse.get("implication") or "")[:240]

        sids: list[str] = []
        if substrate_class_key:
            sids = _collect_class_system_ids(
                project_dir, target_class, substrate_class_key, max_ids=10,
            )

        prompt = _build_ege_prompt(
            target_class=target_class,
            feature_name=feature_name,
            feature_meaning=feature_meaning,
            system_id_examples=sids,
            substrate_class=substrate_class_label,
            forbidden_domain=forbidden_domain,
            n_collapsed_rows=n_rows,
        )
        # Truncate to budget
        max_chars = max_input_tokens * 4
        if len(prompt) > max_chars:
            prompt = prompt[:max_chars] + "\n[PROMPT TRUNCATED]"

        gap_record: dict[str, Any] = {
            "class": target_class,
            "feature_key": feature_name,
            "n_rows": n_rows,
            "system_id_examples": sids,
            "proposals": [],
            "error": None,
            "tokens_in": 0,
            "tokens_out": 0,
        }
        try:
            from ztare.common.dispatch_model import dispatch_call_text

            response = dispatch_call_text(
                "evidence_gap_enrichment",
                prompt,
                llm_response_call=lambda p: runtime.call_text(
                    p,
                    model_id=model_id,
                    timeout_seconds=int(timeout_seconds),
                    max_tokens=max_output_tokens,
                    request_label=f"evidence_gap_enrichment[{target_class}/{feature_name}]",
                    retries=1,
                ),
                timeout_seconds=int(timeout_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            gap_record["error"] = f"{type(exc).__name__}: {str(exc)[:280]}"
            proposals_by_gap.append(gap_record)
            continue

        usage = getattr(response, "usage", None)
        ti = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        to = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
        gap_record["tokens_in"] = ti
        gap_record["tokens_out"] = to
        verdict.tokens_in_total += ti
        verdict.tokens_out_total += to

        parsed = _parse_ege_json(response.text or "")
        if not parsed:
            gap_record["error"] = "could not parse JSON from response"
            proposals_by_gap.append(gap_record)
            continue
        raw_props = parsed.get("proposals") or []
        proposals_clean: list[dict] = []
        for p in raw_props[:5]:
            if not isinstance(p, dict):
                continue
            prop = EvidenceGapProposal(
                paper_title=str(p.get("paper_title", ""))[:200],
                year=_safe_int(p.get("year")),
                arxiv_id_or_url=str(p.get("arxiv_id_or_url", ""))[:200],
                system_id_overlap_estimate=str(p.get("system_id_overlap_estimate", ""))[:120],
                expected_dex_range=str(p.get("expected_dex_range", ""))[:120],
                extraction_difficulty=str(p.get("extraction_difficulty", ""))[:120],
                confidence=str(p.get("confidence", ""))[:40],
                notes=str(p.get("notes", ""))[:300],
            )
            proposals_clean.append(prop.to_dict())
        gap_record["proposals"] = proposals_clean
        proposals_by_gap.append(gap_record)

    verdict.proposals_by_gap = proposals_by_gap
    _persist_ege(workspace_dir, verdict)
    # Cache the fresh result so the next identical-input run hits.
    try:
        _ege_cache.store(
            _cache_hash,
            payload={
                "n_gaps_seen": verdict.n_gaps_seen,
                "proposals_by_gap": verdict.proposals_by_gap,
                "model_id_used": verdict.model_id_used,
                "tokens_in_total": verdict.tokens_in_total,
                "tokens_out_total": verdict.tokens_out_total,
                "error": verdict.error,
            },
            model_id_used=verdict.model_id_used,
        )
    except Exception as exc:                                        # noqa: BLE001
        logger.warning("EGE cache.store failed (non-fatal): %s", exc)
    return verdict.to_dict()


def _safe_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _persist_ege(workspace_dir: Path, verdict: EvidenceGapVerdict) -> None:
    out = workspace_dir / "evidence_gap_enrichment_proposals.json"
    try:
        out.write_text(json.dumps(verdict.to_dict(), indent=2), encoding="utf-8")
        verdict.artifact_path = str(out)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Per-iter EGE trigger (2026-04-27).
#
# Pre-iter-1 EGE fires only when R26 surfaces withheld_class collapses on a
# fresh substrate. After iter 1, EGE goes silent for the rest of the run.
# That's a recursion gap: when a champion promotes near the Newton-step
# threshold (raw judge score >= 70) AND a specific per-class farther-tail
# regime is the binding constraint, the LIVE-LOOP knowledge — "this class
# keeps failing in this specific way" — should re-fire EGE so the operator
# can enrich the substrate where it matters.
#
# Two triggers (either fires):
#   T6-A  Breakthrough-near-cap: champion just promoted, raw_judge_score
#         >= 70, capped score < raw_score, AND >= 1 per-class farther-tail
#         class fails — exactly the iter-8 gp163d Galaxy-Cluster Bridge
#         pattern. The failing class is the class needing enrichment.
#   T6-B  Persistent class failure: same per-class farther-tail class has
#         MRE > threshold for >= 3 consecutive iters with no improvement.
#         The class is structurally beyond the apparatus's reach — only
#         literature can move it.
#
# The per-iter trigger writes to
# `workspace/evidence_gap_enrichment_proposals_iter_NNN.json` (separate
# from the pre-iter-1 artifact, so neither path overwrites the other).
# ---------------------------------------------------------------------------


def detect_per_iter_ege_trigger(
    *,
    eval_history: list[dict],
    latest_eval: dict,
    iter_index: int,
    persistent_failure_threshold: int = 3,
    persistent_class_mre_threshold: float = 0.50,
    breakthrough_raw_threshold: int = 70,
) -> Optional[dict]:
    """Return a trigger-context dict if per-iter EGE should fire, else None.

    eval_history: list of records as written to eval_history.jsonl (ordered
        oldest-first). Each record has keys including `score`, `raw_judge_score`
        (post champion-telemetry-persistence), and `gate_verdicts`.
    latest_eval: the just-completed iter's `new_eval` dict (with `score`,
        `score_cap_applied`, `score_contract`).
    """
    cap_meta = latest_eval.get("score_cap_applied") or {}
    raw_score = cap_meta.get("original_judge_score") if isinstance(cap_meta, dict) else None
    if raw_score is None:
        raw_score = latest_eval.get("score") or 0
    capped_score = latest_eval.get("score") or 0

    # Pull per-class farther-tail MRE from the harness result if present
    sc = latest_eval.get("score_contract") or {}
    gh = sc.get("gate_harness") or sc.get("gate_harness_result") or {}
    per_class_ft = {}
    ft = gh.get("farther_tail") if isinstance(gh, dict) else None
    if isinstance(ft, dict):
        per_class_ft = ft.get("per_class_mre") or {}
    # also support the per-class blocks our gp163d harness emits
    for k, v in gh.items() if isinstance(gh, dict) else []:
        if isinstance(k, str) and k.startswith("farther_tail_class_") and isinstance(v, dict):
            cls = k.replace("farther_tail_class_", "")
            mre = v.get("mean_relative_error")
            if mre is not None:
                per_class_ft.setdefault(cls, mre)

    failing_classes = [
        cls for cls, mre in per_class_ft.items()
        if isinstance(mre, (int, float)) and mre > persistent_class_mre_threshold
    ]

    # T6-A — breakthrough near cap
    if (
        raw_score >= breakthrough_raw_threshold
        and capped_score < raw_score
        and failing_classes
    ):
        return {
            "trigger": "breakthrough_near_cap",
            "raw_judge_score": raw_score,
            "capped_score": capped_score,
            "cap_reason": cap_meta.get("reason") if isinstance(cap_meta, dict) else None,
            "failing_classes": failing_classes,
            "per_class_farther_tail_mre": per_class_ft,
            "iter_index": iter_index,
        }

    # T6-B — persistent same-class failure
    if len(eval_history) >= persistent_failure_threshold and failing_classes:
        # check if this same class has been failing for >= persistent_failure_threshold iters
        # use the simple heuristic: same class is in the recent score-stagnant window
        recent = eval_history[-persistent_failure_threshold:]
        recent_scores = [r.get("score") for r in recent]
        if len(set(recent_scores)) == 1 and recent_scores[0] is not None:
            return {
                "trigger": "persistent_class_failure",
                "score": recent_scores[0],
                "failing_classes": failing_classes,
                "per_class_farther_tail_mre": per_class_ft,
                "stagnant_for_iters": persistent_failure_threshold,
                "iter_index": iter_index,
            }

    return None


def _build_per_iter_ege_prompt(
    *,
    trigger_context: dict,
    substrate_class: str,
    forbidden_domain: Optional[str],
    bridge_form_summary: Optional[str] = None,
) -> str:
    """Render a prompt for the per-iter EGE call.

    Different framing from the pre-iter-1 prompt: this one knows the
    apparatus already has a champion-form and is asking *which literature
    can break the per-class cap*, not just *which catalogs publish the
    feature*. The mutator-side LLM is being asked to suggest enrichments
    that move the binding constraint, not just any feature gap.
    """
    failing = trigger_context.get("failing_classes") or []
    failing_str = ", ".join(failing) if failing else "(none specified)"
    per_class = trigger_context.get("per_class_farther_tail_mre") or {}
    per_class_str = "\n".join(
        f"  - class {cls}: per-class farther-tail MRE = {mre:.3f}"
        for cls, mre in per_class.items()
        if isinstance(mre, (int, float))
    ) or "  (no per-class breakdown surfaced)"
    trigger = trigger_context.get("trigger", "unspecified")
    raw = trigger_context.get("raw_judge_score")
    capped = trigger_context.get("capped_score")
    bridge_str = f"\nApparatus's current locked form (Sacred-DNA bridge):\n  {bridge_form_summary}" if bridge_form_summary else ""
    fbd = forbidden_domain or "(unspecified)"
    return (
        "You are a literature-search assistant for a symbolic-regression "
        "research apparatus that has already produced a champion-class "
        "result and is now bound by a specific per-class failure mode.\n\n"
        f"Substrate class label: {substrate_class}\n"
        f"Substrate's home-discipline hint: {fbd}\n"
        f"Trigger type: {trigger}\n"
        + (f"Champion raw judge score: {raw} (capped to {capped} by per-class enforcement)\n" if raw is not None else "")
        + f"Failing per-class farther-tail classes: [{failing_str}]\n"
        + f"Per-class farther-tail MREs:\n{per_class_str}\n"
        + bridge_str
        + "\n\n"
        "TASK: Propose published catalogs/papers/datasets that, if folded "
        "into the substrate, would let the apparatus break the per-class "
        "cap above. Specifically:\n"
        "  * For each failing class, what published per-system data would "
        "    add the missing degree of freedom (e.g., real per-system mass "
        "    if mass is currently synthesized, or alternative scale "
        "    variables that vary within the class)?\n"
        "  * If your knowledge suggests the failing class is a genuinely "
        "    different physical regime (not a substrate-data deficiency), "
        "    say so explicitly and propose what observable would let the "
        "    apparatus distinguish 'data ceiling' from 'physical regime'.\n"
        "  * Always cite real, published references. No invented papers.\n\n"
        "Return at most 5 proposals. If you have NO candidates, return an "
        "empty list — better one high-confidence proposal than five "
        "speculative ones.\n\n"
        "Output MUST be a single JSON object, no markdown:\n"
        "{\n"
        '  "proposals": [\n'
        "    {\n"
        '      "paper_title": "...",\n'
        '      "year": 2018,\n'
        '      "arxiv_id_or_url": "...",\n'
        '      "system_id_overlap_estimate": "...",\n'
        '      "expected_dex_range": "...",\n'
        '      "extraction_difficulty": "...",\n'
        '      "confidence": "...",\n'
        '      "notes": "..."\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Return ONLY the JSON object."
    )


def propose_per_iter_ege(
    project_dir: Path | str,
    *,
    trigger_context: dict,
    iter_index: int,
    rubric_data: Optional[dict] = None,
    mutator_model_id: Optional[str] = None,
    enrichment_model_id: Optional[str] = None,
    timeout_seconds: float = 60.0,
    max_input_tokens: int = 3000,
    max_output_tokens: int = 3000,
    runtime: Any = None,
) -> dict:
    """Per-iter EGE call. Same contract as propose_evidence_gap_enrichment
    but driven by a live trigger context (not by R26 collapses) and writes
    to a per-iter artifact so the pre-iter-1 file is never overwritten.

    Fail-graceful: any exception returns a verdict with `error` set; the
    autoresearch_loop never blocks on EGE.
    """
    project_dir = Path(project_dir)
    workspace_dir = project_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    rubric_data = rubric_data or {}

    verdict = EvidenceGapVerdict(attempted=True)
    verdict.n_gaps_seen = len(trigger_context.get("failing_classes") or [])

    raw_id = (enrichment_model_id or rubric_data.get("evidence_gap_model_id") or "@mutator")
    raw_id = str(raw_id).strip()
    if raw_id in ("", "@mutator", "mutator"):
        if not mutator_model_id:
            verdict.error = (
                "evidence_gap_model_id is '@mutator' but no mutator_model_id "
                "supplied at dispatch — autoresearch_loop must pass it through"
            )
            _persist_per_iter_ege(workspace_dir, iter_index, verdict)
            return verdict.to_dict()
        model_id = str(mutator_model_id)
    else:
        model_id = raw_id
    verdict.model_id_used = model_id

    if runtime is None:
        try:
            from ztare.common.llm_runtime import LLMRuntime as _LLMRuntime
            runtime = _LLMRuntime()
        except Exception as exc:  # noqa: BLE001
            verdict.error = f"LLMRuntime unavailable: {exc}"
            _persist_per_iter_ege(workspace_dir, iter_index, verdict)
            return verdict.to_dict()

    substrate_class_label = str(rubric_data.get("substrate_class") or "")
    forbidden_domain = rubric_data.get("cold_llm_seed_forbidden_domain")

    # Best-effort: pull the locked Sacred-DNA form summary if present
    bridge_form_summary: Optional[str] = None
    try:
        va_path = project_dir / "verified_axioms.json"
        if va_path.exists():
            blob = json.loads(va_path.read_text(encoding="utf-8"))
            axioms = blob.get("axioms") if isinstance(blob, dict) else (blob if isinstance(blob, list) else [])
            for ax in axioms or []:
                if isinstance(ax, dict) and ax.get("status") == "verified_axiom":
                    bridge_form_summary = ax.get("form_human_readable") or ax.get("parametric_form")
                    if bridge_form_summary:
                        break
    except Exception:
        bridge_form_summary = None

    prompt = _build_per_iter_ege_prompt(
        trigger_context=trigger_context,
        substrate_class=substrate_class_label,
        forbidden_domain=forbidden_domain,
        bridge_form_summary=bridge_form_summary,
    )
    max_chars = max_input_tokens * 4
    if len(prompt) > max_chars:
        prompt = prompt[:max_chars] + "\n[PROMPT TRUNCATED]"

    proposals_block: dict[str, Any] = {
        "trigger_context": trigger_context,
        "proposals": [],
        "error": None,
        "tokens_in": 0,
        "tokens_out": 0,
    }
    try:
        result = runtime.generate(
            model_id=model_id,
            system_prompt="",
            user_prompt=prompt,
            max_output_tokens=max_output_tokens,
            timeout_seconds=timeout_seconds,
        )
        raw_text = result.get("text") or ""
        proposals_block["tokens_in"] = int(result.get("input_tokens") or 0)
        proposals_block["tokens_out"] = int(result.get("output_tokens") or 0)
        verdict.tokens_in_total += proposals_block["tokens_in"]
        verdict.tokens_out_total += proposals_block["tokens_out"]
        parsed = _parse_ege_json(raw_text)
        if parsed is None:
            proposals_block["error"] = "could not parse JSON output"
        else:
            proposals_block["proposals"] = parsed.get("proposals") or []
    except Exception as exc:  # noqa: BLE001
        proposals_block["error"] = f"runtime error: {exc}"

    verdict.proposals_by_gap = [proposals_block]
    _persist_per_iter_ege(workspace_dir, iter_index, verdict)
    return verdict.to_dict()


def _persist_per_iter_ege(
    workspace_dir: Path,
    iter_index: int,
    verdict: EvidenceGapVerdict,
) -> None:
    out = workspace_dir / f"evidence_gap_enrichment_proposals_iter_{iter_index:03d}.json"
    try:
        out.write_text(json.dumps(verdict.to_dict(), indent=2), encoding="utf-8")
        verdict.artifact_path = str(out)
    except OSError:
        pass
