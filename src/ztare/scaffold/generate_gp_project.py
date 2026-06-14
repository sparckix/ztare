"""GP-104 — General Purpose Project Generator.

Scaffolds a qualitative ZTARE project with correct Type B gate configuration,
LLM-drafted adversarial persona/criteria, and dual-path evidence scaffolding
(manual evidence.txt OR raw/ compile pipeline).

Usage:
    python -m src.ztare.scaffold.generate_gp_project \\
        --slug seattle_v2 \\
        --brief "Analyze whether Seattle tech firms face mandatory housing cost internalization" \\
        --judge-model gpt4.1

See: research_areas/specs/active/GP-104_general_purpose_project_generator_spec.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.ztare.common.llm_runtime import LLMRuntime, MODEL_MAP

PROJECTS_DIR = Path("projects")
RUBRICS_DIR = Path("rubrics")

# ---------------------------------------------------------------------------
# Type B gate opt-outs — always injected into generated rubrics
# ---------------------------------------------------------------------------

TYPE_B_GATE_CONFIG = {
    "farther_tail_region": None,
    "farther_tail_region_disable_reason": (
        "qualitative thesis project — no numerical holdout gate"
    ),
    "disable_evidence_fit_gate": True,
    "disable_evidence_fit_gate_reason": (
        "qualitative thesis — evidence surface is text documents, not a numerical "
        "curve; global_evidence_fit gate does not apply"
    ),
    "disable_uniqueness_gap_gate": True,
    "disable_uniqueness_gap_gate_reason": (
        "qualitative thesis — rival mechanisms scored by rubric criteria; "
        "mathematical-form keyword heuristic does not apply"
    ),
    "holdout_hard_gate": False,
    "enable_fit_primitive": False,
    "fit_score_mode": "none",
    "discovery_mode": False,
    "falsification_mode": "bounded_discriminator",
    "composition_stagnation_threshold": 5,
    "gp103_stagnation_threshold": 3,
    "holdout_budget": 0,
    # GP-105 M-Form Alignment Audit: runtime Goodhart detection.
    # General Office LLM audits thesis vs. charter (blinded to rubric).
    # general_office_model must differ from judge and mutator (Chandler separation).
    "enable_mform_audit": True,
    "general_office_model": "gpt4.1",
}

# ---------------------------------------------------------------------------
# LLM prompt for rubric drafting
# ---------------------------------------------------------------------------

RUBRIC_SYSTEM_PROMPT = """\
You are a ZTARE rubric designer. Generate an adversarial evaluation rubric for a qualitative thesis project.

Rules:
1. The persona must be a domain expert who is HOSTILE to easy answers. Give them a specific methodological commitment that rules out at least two common rhetorical moves in this domain. The persona should be 3-5 sentences, opinionated, and adversarial.
2. Generate exactly 4 dimensions. Weights must sum exactly to 100. Each dimension has:
   - name: string (short, descriptive)
   - weight: integer
   - description: 2-3 sentences naming specifically what earns full points AND what gets penalized
3. Generate a criteria dict with one key per dimension. AT LEAST ONE key must contain the word "rival" (e.g., "rival_hypothesis_falsification" or "rival_mechanism_enumeration"). Each criterion value is a 2-3 sentence scoring guide.
4. Output valid JSON only. No prose outside the JSON object. No markdown fences.
5. Every criterion must be specific to the thesis question provided — no generic criteria like "logical consistency" or "evidence quality."
6. The strongest criterion should penalize the single most common rhetorical cheat in this domain.
7. CRITICAL — persona modeling failure mode: The persona MUST name at least one specific modeling failure mode it will penalize even absent an explicit criterion. Examples: "hostile to any cost calculation that treats a variable as fixed without a sensitivity range when second-order market effects are knowable"; "will not credit dynamic claims backed only by static snapshots"; "penalizes distributional conclusions drawn from aggregate statistics when the distribution is the question." This is the mechanism that prevents high scores on technically correct but shallow analysis. Without it, a mutator can score 90+ on a narrow static answer to a broad dynamic question.

Output format (JSON object with exactly these three keys):
{
  "persona": "...",
  "dimensions": [{"name": "...", "weight": ..., "description": "..."}, ...],
  "criteria": {"criterion_key_1": "...", "rival_..._2": "...", ...}
}
"""


def _draft_rubric_via_llm(brief: str, model_family: str) -> dict:
    """Call LLM to draft persona + dimensions + criteria from brief."""
    model_id = MODEL_MAP.get(model_family, model_family)
    runtime = LLMRuntime()

    prompt = f"{RUBRIC_SYSTEM_PROMPT}\n\nProject brief: {brief}\n\nOutput the JSON object now:"

    print(f"[generate-gp] Drafting rubric via {model_id}...")
    try:
        response = runtime.call_text(prompt, model_id=model_id, max_tokens=4000)
        raw_text = response.text.strip()
    except Exception as exc:
        print(f"[generate-gp] LLM call failed: {exc}", file=sys.stderr)
        return _placeholder_rubric(brief)

    # Strip markdown fences if present
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        raw_text = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"[generate-gp] Failed to parse LLM JSON: {exc}", file=sys.stderr)
        print(f"[generate-gp] Raw LLM output:\n{raw_text}", file=sys.stderr)
        return _placeholder_rubric(brief)

    # Validate required keys
    for key in ("persona", "dimensions", "criteria"):
        if key not in parsed:
            print(
                f"[generate-gp] LLM output missing required key '{key}' — using placeholder",
                file=sys.stderr,
            )
            return _placeholder_rubric(brief)

    # Validate weights sum to 100
    try:
        total = sum(int(d["weight"]) for d in parsed["dimensions"])
        if total != 100:
            print(
                f"[generate-gp] Dimension weights sum to {total} (expected 100) — using placeholder",
                file=sys.stderr,
            )
            return _placeholder_rubric(brief)
    except (KeyError, TypeError, ValueError):
        return _placeholder_rubric(brief)

    # Validate at least one criterion key contains "rival"
    criteria_keys = list(parsed.get("criteria", {}).keys())
    if not any("rival" in k.lower() for k in criteria_keys):
        print(
            "[generate-gp] Warning: no criterion key contains 'rival' — global_uniqueness_gap may fire. "
            "Edit rubric to add a 'rival_...' criterion key.",
            file=sys.stderr,
        )

    return parsed


def _placeholder_rubric(brief: str) -> dict:
    """Fallback rubric when LLM call fails or returns invalid JSON."""
    return {
        "persona": (
            f"You are a rigorous analyst evaluating a thesis on: {brief}. "
            "You are hostile to vague causal claims, unsupported analogies, "
            "and proposals that ignore the political economy of why the status quo exists. "
            "You reward exact mechanism identification, falsifiable predictions, and "
            "honest engagement with the strongest objections."
        ),
        "dimensions": [
            {
                "name": "Causal Mechanism",
                "weight": 30,
                "description": (
                    "Does the thesis identify a specific causal mechanism — not a correlation? "
                    "Award full points if the mechanism names an intermediate variable and specifies "
                    "the conditions under which it would NOT produce the claimed effect. "
                    "Penalize temporal co-occurrence presented as causation."
                ),
            },
            {
                "name": "rival_hypothesis_falsification",
                "weight": 25,
                "description": (
                    "Does the thesis enumerate at least two rival explanations and falsify them? "
                    "Award full points if each rival is falsified on the evidence surface, "
                    "not dismissed rhetorically. Penalize if rivals are strawmanned or ignored."
                ),
            },
            {
                "name": "Mechanism Tractability",
                "weight": 25,
                "description": (
                    "Does the thesis propose a tractable mechanism and explain why it has not "
                    "already been implemented? Award full points if the political economy barrier "
                    "is named and assessed as contingent vs. structural. "
                    "Penalize proposals that treat feasibility as purely technical."
                ),
            },
            {
                "name": "Verdict Calibration",
                "weight": 20,
                "description": (
                    "Does the thesis deliver a specific, falsifiable verdict? "
                    "Award full points if the verdict names an observable that would change the "
                    "conclusion and assigns a specific condition for reversal. "
                    "Penalize vague conclusions and 'on the one hand / on the other hand' hedging."
                ),
            },
        ],
        "criteria": {
            "1_Causal_Mechanism": (
                "Does the thesis name a specific mechanism with an intermediate variable? "
                "Does it specify the conditions for mechanism failure? "
                "Is the causal claim anchored to at least one quantitative anchor from evidence?"
            ),
            "2_rival_hypothesis_falsification": (
                "Does the thesis enumerate two distinct rival explanations? "
                "Does it falsify each on the evidence surface with specific evidence citations? "
                "Penalize if rivals are strawmanned or if the falsification is not evidence-grounded."
            ),
            "3_Mechanism_Tractability": (
                "Does the thesis identify a tractable implementation mechanism? "
                "Does it name the specific political economy barrier and assess its contingency? "
                "Penalize if feasibility is assumed without addressing the status quo."
            ),
            "4_Verdict_Calibration": (
                "Does the thesis deliver a verdict with a named falsifying observable? "
                "Is the scope of the verdict explicitly bounded? "
                "Penalize omnibus conclusions and claims that cannot be disconfirmed."
            ),
        },
    }


def _build_rubric(llm_draft: dict, slug: str) -> dict:
    """Merge LLM draft with Type B gate config into final rubric."""
    rubric = {}
    # Gate config first so it's visible at top of file
    rubric.update(TYPE_B_GATE_CONFIG)
    # LLM content
    rubric["persona"] = llm_draft["persona"]
    rubric["dimensions"] = llm_draft["dimensions"]
    rubric["criteria"] = llm_draft["criteria"]
    return rubric


def _write_evidence_txt(proj_dir: Path, slug: str) -> None:
    content = f"""\
# Evidence for {slug}
# ─────────────────────────────────────────────────────────────────
# Manual curation lane: add observations directly below this header.
#   Format: one observation per line, e.g.:
#   [Source 2024] Claim text here. [Strength: high/medium/low]
#
# Compiled-evidence lane: drop source documents into projects/{slug}/raw/
#   then run: make evidence-compile PROJECT={slug} MODEL=gpt4.1
#   The compiler will produce a structured evidence.txt from your raw docs.
#   Use raw/source_type_map.json to type each document
#   (source_evidence, seed_hypothesis, research_question, etc.)
# ─────────────────────────────────────────────────────────────────

"""
    (proj_dir / "evidence.txt").write_text(content, encoding="utf-8")


def _write_source_type_map(raw_dir: Path) -> None:
    content = {
        "__instructions__": (
            "Map filename → source_type. Values: source_evidence, seed_hypothesis, "
            "research_question, collection_todo, untyped. "
            "Delete this key before running make evidence-compile."
        )
    }
    (raw_dir / "source_type_map.json").write_text(
        json.dumps(content, indent=2) + "\n", encoding="utf-8"
    )


def _write_thesis_md(proj_dir: Path, slug: str) -> None:
    content = f"""\
# Thesis — {slug}

## Core Claim

[State your core thesis here. Be specific: name the mechanism, the direction of effect,
and the scope conditions. Avoid hedging — a clear falsifiable claim earns more than
a nuanced non-answer.]

## Evidence Base

[Summarize the key evidence. Reference specific items from evidence.txt by line number
or label. Do not import domain knowledge not present in the evidence surface.]

## Rival Hypotheses

[Name at least two rival explanations for the same observed pattern.
Explain specifically why each fails on your evidence — not why it seems unlikely
in the abstract.]

## Strongest Objection

[State the single strongest objection to your thesis in the objector's own terms.
Then explain why it does not overturn the core claim, or why it narrows but does
not falsify it.]

## Fit Declaration

```json
{{"variables": [], "expression": "0", "parameter_names": []}}
```
"""
    (proj_dir / "thesis.md").write_text(content, encoding="utf-8")


def _write_project_charter(proj_dir: Path, slug: str, brief: str) -> None:
    content = f"""\
# Project Charter — {slug}

## Core Question

{brief}

## Observable

[What would confirm or disconfirm the core claim? Name at least one specific
observable that would move you from one verdict to another. The observable must
be measurable from existing or obtainable evidence, not a future study you
cannot run.]

## Task

Propose a thesis that:
1. Identifies the strongest causal mechanism linking the inputs to the observed outcome
2. Enumerates and falsifies rival explanations on the evidence surface
3. Assesses tractability of any proposed intervention
4. Delivers a specific, bounded verdict with a named falsifying condition

## Constraints

- Use only evidence in evidence.txt
- Do not import frameworks, analogies, or data not grounded in the evidence surface
- The most interesting finding is a genuine falsification or a correctly bounded
  "not solvable from this evidence" verdict — not a rubber-stamp confirmation
- Do not reference external domain knowledge the evidence does not support
"""
    (proj_dir / "project_charter.md").write_text(content, encoding="utf-8")


def generate(slug: str, brief: str, judge_model: str) -> None:
    proj_dir = PROJECTS_DIR / slug
    rubric_path = RUBRICS_DIR / f"{slug}.json"

    # Guard: don't overwrite existing project
    if proj_dir.exists():
        print(
            f"[generate-gp] ERROR: projects/{slug}/ already exists. "
            "Delete it first or choose a different slug.",
            file=sys.stderr,
        )
        sys.exit(1)

    if rubric_path.exists():
        print(
            f"[generate-gp] ERROR: rubrics/{slug}.json already exists. "
            "Delete it first or choose a different slug.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate model
    if judge_model not in MODEL_MAP:
        print(
            f"[generate-gp] Warning: '{judge_model}' not in MODEL_MAP. "
            f"Known models: {list(MODEL_MAP.keys())}. Proceeding anyway.",
            file=sys.stderr,
        )

    # Create directory structure
    print(f"[generate-gp] Creating projects/{slug}/")
    proj_dir.mkdir(parents=True, exist_ok=False)
    (proj_dir / "workspace").mkdir()
    raw_dir = proj_dir / "raw"
    raw_dir.mkdir()

    # Write scaffold files
    _write_evidence_txt(proj_dir, slug)
    _write_source_type_map(raw_dir)
    _write_thesis_md(proj_dir, slug)
    _write_project_charter(proj_dir, slug, brief)

    print(f"[generate-gp] Scaffold written to projects/{slug}/")

    # Draft rubric via LLM
    llm_draft = _draft_rubric_via_llm(brief, judge_model)
    rubric = _build_rubric(llm_draft, slug)

    # Write rubric
    RUBRICS_DIR.mkdir(parents=True, exist_ok=True)
    rubric_path.write_text(json.dumps(rubric, indent=2) + "\n", encoding="utf-8")
    print(f"[generate-gp] Rubric written to rubrics/{slug}.json")

    # Check that at least one criterion has 'rival'
    criteria_keys = list(rubric.get("criteria", {}).keys())
    has_rival = any("rival" in k.lower() for k in criteria_keys)
    if not has_rival:
        print(
            "[generate-gp] WARNING: no criterion key contains 'rival'. "
            "The global_uniqueness_gap gate may fire during the run. "
            f"Edit rubrics/{slug}.json and rename one criterion to include 'rival_'.",
            file=sys.stderr,
        )

    # Print next steps
    print()
    print("=" * 60)
    print(f"  Project '{slug}' created successfully.")
    print("=" * 60)
    print()
    print("Next steps:")
    print()
    print(f"  1. Add your evidence:")
    print(f"       # Option A (manual): edit projects/{slug}/evidence.txt directly")
    print(f"       # Option B (compile): add docs to projects/{slug}/raw/ then:")
    print(f"       make evidence-compile PROJECT={slug} MODEL=gpt4.1")
    print()
    print(f"  2. Seal the project:")
    print(f"       make seal PROJECT={slug} RUBRIC=rubrics/{slug}.json")
    print()
    print(f"  3. Run the loop:")
    print(
        f"       make loop PROJECT={slug} RUBRIC=rubrics/{slug}.json ITERS=10 "
        "MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gpt4.1"
    )
    print()
    print(f"  Review and edit the rubric before sealing:")
    print(f"    rubrics/{slug}.json")
    print(f"  Review the charter before sealing:")
    print(f"    projects/{slug}/project_charter.md")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a qualitative ZTARE project scaffold with correct gate configuration."
    )
    parser.add_argument(
        "--slug",
        required=True,
        help="Project slug (used as directory name and rubric filename)",
    )
    parser.add_argument(
        "--brief",
        required=True,
        help="One-paragraph plain-English description of the thesis question",
    )
    parser.add_argument(
        "--judge-model",
        default="gpt4.1",
        help="LLM model to use for rubric drafting (default: gpt4.1)",
    )
    args = parser.parse_args()
    generate(slug=args.slug, brief=args.brief, judge_model=args.judge_model)


if __name__ == "__main__":
    main()
