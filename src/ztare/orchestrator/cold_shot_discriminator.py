"""Cold-shot discriminator prompt and parser.

This is the GP-190 version of "send it to a cold model." The prompt is
designed to return queue-ready JSON instead of eloquent critique prose.
It does not call an LLM; callers decide which model/API to use.
"""
from __future__ import annotations

import json
from typing import Any

from src.ztare.orchestrator.discriminator_queue import SHORTCUT_LABELS


REQUIRED_KEYS = {
    "answer",
    "data_says",
    "data_does_not_say",
    "tightened_eigenquestion",
    "single_best_next_discriminator",
    "kill_condition",
    "severity_level",
    "license_stage",
    "main_risk",
    "do_not_do_next",
}


def build_cold_shot_discriminator_prompt(
    *,
    context: str,
    question: str,
    artifact_manifest: list[str] | None = None,
    forbidden_claims: list[str] | None = None,
) -> str:
    artifacts = artifact_manifest or []
    forbidden = forbidden_claims or []
    labels = ", ".join(sorted(SHORTCUT_LABELS))
    return f"""You are a cold-shot adversarial science-methods reviewer.

You are not here to improve prose. You are here to convert a live result into
the next decisive discriminator.

Rules:
1. Separate what the data says from what the data does not say.
2. Name the narrative shortcut that would make the claim overreach.
3. Return the single cheapest discriminator that attacks the shortcut.
4. Include a kill condition and required artifacts.
5. If the result is an instrument null, say so explicitly.
6. Do not claim cross-domain isomorphism unless the shared primitive and
   non-shared physics are both named.
7. Do not recommend more compute if an offline artifact replay can answer the
   question.
8. Assign severity honestly:
   - 1 = smoke/NaN/import check
   - 2 = sanity/instrument check
   - 3 = local falsifier
   - 4 = hostile control
   - 5 = decisive ladder or dark-domain discriminator
   Findings may not be promoted on severity < 4.
9. Use license_stage="scratchpad" for wild cross-domain analogy exploration;
   use license_stage="commit" only when the proposed discriminator is fit for
   F-row / INS-row promotion discipline.

Allowed narrative_shortcut labels:
{labels}

Forbidden claims for this review:
{json.dumps(forbidden, indent=2)}

Artifacts available:
{json.dumps(artifacts, indent=2)}

Question:
{question}

Context:
{context}

Return ONLY strict JSON with this schema:
{{
  "answer": "short verdict label",
  "data_says": ["bounded factual statement", "..."],
  "data_does_not_say": ["bounded non-claim", "..."],
  "narrative_shortcut": "one allowed label",
  "tightened_eigenquestion": "smallest question whose answer changes the next action",
  "single_best_next_discriminator": "specific test to run next",
  "kill_condition": "what result kills or demotes the claim",
  "severity_level": 1,
  "license_stage": "scratchpad|commit",
  "weak_test_risk": "why this discriminator might be too weak, or empty string",
  "required_artifacts": ["artifact needed to interpret the test", "..."],
  "if_more_compute_what_exact_run": "exact run, or empty string",
  "if_not_more_compute_what_exact_handoff": "offline/proof/ledger handoff, or empty string",
  "main_risk": "main way this result could be misleading",
  "do_not_do_next": ["wasteful or contaminating next move", "..."],
  "confidence": "low|medium|high"
}}
"""


def parse_cold_shot_discriminator_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(line for line in lines if not line.strip().startswith("```")).strip()
    data = json.loads(raw)
    missing = sorted(REQUIRED_KEYS - set(data))
    if missing:
        raise ValueError(f"cold-shot discriminator JSON missing keys: {', '.join(missing)}")
    shortcut = data.get("narrative_shortcut")
    if shortcut not in SHORTCUT_LABELS:
        raise ValueError(f"unknown narrative_shortcut: {shortcut}")
    try:
        severity = int(data.get("severity_level"))
    except (TypeError, ValueError) as exc:
        raise ValueError("severity_level must be an integer 1..5") from exc
    if not 1 <= severity <= 5:
        raise ValueError(f"severity_level must be 1..5, got {severity!r}")
    if data.get("license_stage") not in {"scratchpad", "commit"}:
        raise ValueError("license_stage must be 'scratchpad' or 'commit'")
    for key in ("data_says", "data_does_not_say", "required_artifacts", "do_not_do_next"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"{key} must be a list")
    return data
