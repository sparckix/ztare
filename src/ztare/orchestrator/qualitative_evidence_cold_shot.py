"""Evidence-grounded cold shot for qualitative substrates (GP-193 / cold_shot v2).

Complements the Erdős de_anchor_seed (cross-domain, context-free) with a
domain-aware cold shot: gives a fresh LLM the full evidence brief, the
current champion's weakest point, and the rubric gate definitions, then
asks for 3 thesis family candidates that resolve the weakest point without
the same failure modes.

The two routes are complementary, not redundant:
  - de_anchor_seed: structural novelty through domain-blindness (cross-domain
    patterns the home field wouldn't propose)
  - qualitative_evidence_seed (this module): structural honesty through full
    context (gate-compliant families grounded in the evidence brief)

Activation: rubric flag `enable_qualitative_evidence_cold_shot: true`.
Output: `workspace/qualitative_evidence_cold_shot.json`
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ztare.common.cegis_membrane import EVALUATION, select_persona

log = logging.getLogger(__name__)

EVIDENCE_CHAR_LIMIT = 6000
WEAKEST_POINT_CHAR_LIMIT = 600
ARTIFACT_NAME = "qualitative_evidence_cold_shot.json"


@dataclass
class EvidenceColdShotCandidate:
    name: str = ""
    core_claim: str = ""
    structural_commitment: str = ""
    resolves_weakest_point: str = ""
    failure_modes_avoided: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "core_claim": self.core_claim,
            "structural_commitment": self.structural_commitment,
            "resolves_weakest_point": self.resolves_weakest_point,
            "failure_modes_avoided": self.failure_modes_avoided,
        }


@dataclass
class EvidenceColdShotResult:
    attempted: bool = False
    success: bool = False
    error: Optional[str] = None
    model_id_used: str = ""
    candidates: list[EvidenceColdShotCandidate] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    weakest_point_used: str = ""
    artifact_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "attempted": self.attempted,
            "success": self.success,
            "error": self.error,
            "model_id_used": self.model_id_used,
            "candidates": [c.to_dict() for c in self.candidates],
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "weakest_point_used": self.weakest_point_used,
        }


def _load_evidence(project_dir: Path, rubric_data: dict) -> str:
    """Read evidence.txt, truncated to EVIDENCE_CHAR_LIMIT."""
    ev_path = project_dir / "evidence.txt"
    if not ev_path.exists():
        return "(no evidence.txt found)"
    try:
        text = ev_path.read_text(encoding="utf-8")
        if len(text) > EVIDENCE_CHAR_LIMIT:
            text = text[:EVIDENCE_CHAR_LIMIT] + "\n...[truncated]"
        return text
    except Exception as exc:
        return f"(evidence.txt unreadable: {exc})"


def _load_weakest_point(workspace_dir: Path) -> str:
    """Read the most recent champion's weakest_point from eval_history."""
    eh_path = workspace_dir / "eval_history.jsonl"
    if not eh_path.exists():
        return ""
    best_score = -1
    best_wp = ""
    try:
        for line in eh_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            score = rec.get("score")
            wp = str(rec.get("weakest_point") or "")
            if isinstance(score, (int, float)) and score > best_score and wp:
                best_score = score
                best_wp = wp
    except Exception:
        pass
    return best_wp[:WEAKEST_POINT_CHAR_LIMIT]


def _load_gate_names(rubric_data: dict) -> list[str]:
    """Extract gate/dimension names from rubric for context."""
    dims = rubric_data.get("dimensions") or []
    return [str(d.get("name", "")) for d in dims if d.get("name")][:8]


def _apply_denylist(text: str, rubric_data: dict) -> str:
    """Redact rubric-level denylist terms from prompt text."""
    terms = rubric_data.get("cold_shot_prompt_denylist") or []
    for term in terms:
        if isinstance(term, str) and term.strip():
            text = text.replace(term, "[REDACTED]")
    return text


def _build_evidence_cold_shot_prompt(
    evidence: str,
    weakest_point: str,
    gate_names: list[str],
    rubric_data: dict,
) -> str:
    gates_str = "\n".join(f"  - {g}" for g in gate_names) if gate_names else "  (see evidence brief)"
    wp_section = (
        f"\n## Current Champion's Weakest Point\n{weakest_point}\n"
        if weakest_point else ""
    )
    persona = select_persona(rubric_data, EVALUATION)[:400]
    persona_section = (
        f"\n## Judge Persona (for calibration)\n{persona}\n"
        if persona else ""
    )
    prompt = (
        "You are a fresh analytical agent. You have NOT seen any prior iteration "
        "of this project — you are starting cold with only the evidence brief below.\n\n"
        "## Evidence Brief\n"
        f"{evidence}\n"
        f"{wp_section}"
        f"{persona_section}"
        "## Rubric Gates (what the judge will penalize)\n"
        f"{gates_str}\n\n"
        "## Task\n"
        "Propose 3 STRUCTURALLY DISTINCT thesis families that:\n"
        "  1. Are grounded in the evidence brief above\n"
        "  2. Directly address the current champion's weakest point\n"
        "  3. Avoid the failure modes implied by the rubric gates\n"
        "  4. Each takes a DIFFERENT structural approach\n\n"
        "Each thesis family must specify:\n"
        "  - A concise core claim (1-2 sentences, falsifiable)\n"
        "  - The structural commitment: what formal object or move makes it tractable\n"
        "  - How it resolves the weakest point\n"
        "  - What failure modes it avoids\n\n"
        "Output MUST be a JSON object with this exact schema "
        "(no markdown, no prose outside JSON):\n"
        "{\n"
        '  "candidates": [\n'
        "    {\n"
        '      "name": "short identifier",\n'
        '      "core_claim": "the falsifiable claim (1-2 sentences)",\n'
        '      "structural_commitment": "the formal move that makes it tractable",\n'
        '      "resolves_weakest_point": "how this addresses the champion weakness",\n'
        '      "failure_modes_avoided": "which gate failures this sidesteps"\n'
        "    },\n"
        '    ... (exactly 3 candidates) ...\n'
        "  ]\n"
        "}\n\n"
        "Return ONLY the JSON object."
    )
    return _apply_denylist(prompt, rubric_data)


def _parse_response(raw: str) -> Optional[dict]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    stripped = raw.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        stripped = "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        depth, start = 0, -1
        for i, ch in enumerate(stripped):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        return json.loads(stripped[start:i + 1])
                    except json.JSONDecodeError:
                        pass
    return None


def run_qualitative_evidence_cold_shot(
    *,
    project_dir: Path,
    rubric_data: dict,
    workspace_dir: Optional[Path] = None,
    mutator_model_id: Optional[str] = None,
    timeout_seconds: float = 45.0,
    runtime: Any = None,
) -> EvidenceColdShotResult:
    """Fire the evidence-grounded cold shot. Fail-silent — never blocks a run."""
    result = EvidenceColdShotResult(attempted=True)
    workspace_dir = workspace_dir or (project_dir / "workspace")

    evidence = _load_evidence(project_dir, rubric_data)
    weakest_point = _load_weakest_point(workspace_dir)
    result.weakest_point_used = weakest_point
    gate_names = _load_gate_names(rubric_data)

    raw_model_id = str(rubric_data.get("qualitative_evidence_cold_shot_model_id") or "").strip()
    if raw_model_id in ("", "@mutator", "mutator"):
        model_id = str(mutator_model_id or "").strip() or "gpt-4.1"
    else:
        model_id = raw_model_id
    result.model_id_used = model_id

    prompt = _build_evidence_cold_shot_prompt(evidence, weakest_point, gate_names, rubric_data)

    try:
        if runtime is None:
            from ztare.common.llm_runtime import LLMRuntime
            runtime = LLMRuntime()
        from ztare.common.dispatch_model import dispatch_call_text

        response = dispatch_call_text(
            "qualitative_evidence_cold_shot",
            prompt,
            llm_response_call=lambda p: runtime.call_text(
                p,
                model_id=model_id,
                timeout_seconds=timeout_seconds,
                request_label="qualitative_evidence_cold_shot",
                retries=1,
            ),
            timeout_seconds=int(timeout_seconds),
        )
        raw = response.text or ""
        usage = getattr(response, "usage", None)
        result.tokens_in = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        result.tokens_out = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc!s}"[:300]
        log.warning("qualitative_evidence_cold_shot LLM call failed: %s", exc)
        _write_artifact(workspace_dir, result)
        return result

    parsed = _parse_response(raw)
    if not parsed:
        result.error = "response_unparseable"
        _write_artifact(workspace_dir, result)
        return result

    raw_cands = parsed.get("candidates") or []
    for cand in raw_cands[:3]:
        result.candidates.append(EvidenceColdShotCandidate(
            name=str(cand.get("name", ""))[:80],
            core_claim=str(cand.get("core_claim", ""))[:400],
            structural_commitment=str(cand.get("structural_commitment", ""))[:600],
            resolves_weakest_point=str(cand.get("resolves_weakest_point", ""))[:400],
            failure_modes_avoided=str(cand.get("failure_modes_avoided", ""))[:300],
        ))

    result.success = len(result.candidates) >= 2
    if not result.success:
        result.error = f"only {len(result.candidates)} candidates returned"
    _write_artifact(workspace_dir, result)
    return result


def _write_artifact(workspace_dir: Path, result: EvidenceColdShotResult) -> None:
    workspace_dir.mkdir(parents=True, exist_ok=True)
    path = workspace_dir / ARTIFACT_NAME
    path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    result.artifact_path = str(path)
