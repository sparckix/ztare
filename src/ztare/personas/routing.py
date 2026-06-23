"""GP-079: LLM-driven persona routing with dynamic generation fallback.

Maps observed failure families (from latent_distance.jsonl) to domain
reviewer personas. Three-tier resolution:

  1. LLM router selects from static persona catalog (config/prompts/)
  2. If no good match → LLM generates a dynamic persona inline
  3. After use, dynamic personas that prove effective get promoted to static

Zero-oracle: driven entirely by what the run is failing at, not by the
operator knowing the ground truth.

Public API:
    select_personas_for_iteration(failure_families, seam_context) -> RouteResult
    load_failure_families_from_latent_distance(workspace_dir) -> list[str]
    auto_select_from_workspace(workspace_dir) -> RouteResult
    promote_dynamic_persona(persona) -> Path
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from ztare.personas.registry import (
    PersonaDefinition,
    format_many_for_injection,
    list_personas,
    load_persona,
)

# ---------------------------------------------------------------------------
# Static fallback table — used when LLM router is unavailable (no API key,
# transient failure, or ZTARE_DISABLE_LLM_ROUTER=1).
# ---------------------------------------------------------------------------

_STATIC_ROUTING_TABLE: dict[str, list[str]] = {
    "inductive_epistemology":               ["philosophy_of_science"],
    "lookup_table_epicycle_overfit":         ["symbolic_regression"],
    "model_class_constraint":               ["systems_ml"],
    "overfitting_non_uniqueness":           ["philosophy_of_science", "symbolic_regression"],
    "post_hoc_exceptions_ad_hoc_fitting":   ["munger_multidisciplinary"],
    "underdetermination":                   ["philosophy_of_science", "systems_ml"],
    "pattern_induction_algorithmic_parsimony": ["symbolic_regression", "philosophy_of_science"],
    "_default":                             ["philosophy_of_science"],
}

_MIN_REVIEWERS = 1
_MAX_REVIEWERS = 3

# Router model — cheap and fast. Override with ZTARE_ROUTER_MODEL env var.
# Default to gemini-2.5-flash (always available in production).
_ROUTER_MODEL_ID = os.environ.get("ZTARE_ROUTER_MODEL", "gemini-2.5-flash")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DynamicPersona:
    """A persona generated on-the-fly by the LLM router."""
    name: str
    role: str
    persona: str
    focus_area: str


@dataclass
class RouteResult:
    """Result of persona routing — may contain static and/or dynamic personas."""
    static_personas: list[PersonaDefinition] = field(default_factory=list)
    dynamic_personas: list[DynamicPersona] = field(default_factory=list)
    routing_method: str = "static_table"  # "static_table" | "llm_router"

    def format_for_injection(self) -> str:
        """Format all personas (static + dynamic) for prompt injection."""
        blocks: list[str] = []
        for p in self.static_personas:
            blocks.append(f"## {p.role}\n\n{p.persona}")
        for dp in self.dynamic_personas:
            blocks.append(f"## {dp.role}\n\n{dp.persona}")
            if dp.focus_area:
                blocks[-1] += f"\n\n**Focus area:** {dp.focus_area}"
        return "\n\n---\n\n".join(blocks)

    @property
    def all_names(self) -> list[str]:
        return [p.name for p in self.static_personas] + [
            dp.name for dp in self.dynamic_personas
        ]

    @property
    def is_empty(self) -> bool:
        return not self.static_personas and not self.dynamic_personas


# ---------------------------------------------------------------------------
# LLM Router
# ---------------------------------------------------------------------------

_ROUTER_PROMPT_TEMPLATE = """\
You are a persona routing system for an adversarial review engine. Your job \
is to select the best reviewer personas for a debate, given the observed \
failure patterns.

## Available Static Personas (already cached — prefer these)

{catalog}

## Observed Failure Families

{failure_families}

{seam_context_block}

## Instructions

1. Select 1-{max_reviewers} personas from the static catalog above that are \
best positioned to attack the observed failure families. Return their exact \
names from the catalog.

2. If NONE of the static personas are a good fit for at least one failure \
family, generate ONE new dynamic persona. A dynamic persona should bring a \
genuinely different lens — do not duplicate what static personas already cover.

3. Respond in this exact JSON format (no other text):

{{
  "selected_static": ["persona_name_1", "persona_name_2"],
  "dynamic_persona": null
}}

OR if generating a dynamic persona:

{{
  "selected_static": ["persona_name_1"],
  "dynamic_persona": {{
    "name": "short_snake_case_name",
    "role": "Domain Lens: Descriptive Title",
    "persona": "You think like X. Apply these mental models: ...",
    "focus_area": "The specific angle this persona attacks from."
  }}
}}

Rules:
- ALWAYS select at least 1 static persona. Dynamic is a supplement, not replacement.
- Total personas (static + dynamic) must not exceed {max_reviewers}.
- Only generate a dynamic persona if the failure families genuinely need expertise \
none of the static personas provide.
"""


def _build_catalog_text() -> str:
    """Build a compact catalog of all static personas for the router prompt."""
    keys = list_personas(category="domain")
    lines: list[str] = []
    for key in keys:
        p = load_persona(key)
        # First sentence of persona as a one-line description
        first_line = p.persona.split("\n")[0][:200]
        lines.append(f"- **{p.name}**: {first_line}")
    return "\n".join(lines) if lines else "(no static personas available)"


def _call_llm_router(
    failure_families: list[str],
    seam_context: str = "",
    max_reviewers: int = _MAX_REVIEWERS,
) -> RouteResult:
    """Call the LLM router to select/generate personas."""
    from ztare.common.llm_runtime import LLMRuntime

    runtime = LLMRuntime()
    if not runtime.model_is_configured(_ROUTER_MODEL_ID):
        return _static_fallback(failure_families, max_reviewers=max_reviewers)

    catalog_text = _build_catalog_text()
    seam_block = ""
    if seam_context:
        seam_block = f"## Seam Context (what is being debated)\n\n{seam_context[:1000]}"

    prompt = _ROUTER_PROMPT_TEMPLATE.format(
        catalog=catalog_text,
        failure_families=", ".join(failure_families) if failure_families else "(none observed — use general-purpose lenses)",
        seam_context_block=seam_block,
        max_reviewers=max_reviewers,
    )

    try:
        response = runtime.call_text(
            prompt,
            model_id=_ROUTER_MODEL_ID,
            max_tokens=1000,
            retries=2,
            timeout_seconds=30,
            request_label="persona_router",
        )
        return _parse_router_response(response.text, max_reviewers=max_reviewers)
    except Exception as e:
        print(
            f"[persona-router] LLM router failed ({e}), falling back to static table",
            flush=True,
        )
        return _static_fallback(failure_families, max_reviewers=max_reviewers)


def _parse_router_response(
    raw_text: str,
    max_reviewers: int = _MAX_REVIEWERS,
) -> RouteResult:
    """Parse the JSON response from the LLM router."""
    # Extract JSON from possible markdown code fences
    json_match = re.search(r"\{[\s\S]*\}", raw_text)
    if not json_match:
        raise ValueError(f"No JSON found in router response: {raw_text[:200]}")

    data = json.loads(json_match.group())

    result = RouteResult(routing_method="llm_router")

    # Load static personas
    selected_names = data.get("selected_static", [])
    for name in selected_names[:max_reviewers]:
        try:
            result.static_personas.append(load_persona(name, category="domain"))
        except KeyError:
            print(
                f"[persona-router] LLM selected unknown persona '{name}', skipping",
                flush=True,
            )

    # Handle dynamic persona if present
    dp_data = data.get("dynamic_persona")
    if dp_data and len(result.static_personas) < max_reviewers:
        result.dynamic_personas.append(DynamicPersona(
            name=dp_data.get("name", "dynamic_generated"),
            role=dp_data.get("role", "Dynamic Reviewer"),
            persona=dp_data.get("persona", ""),
            focus_area=dp_data.get("focus_area", ""),
        ))

    # Ensure at least one persona
    if result.is_empty:
        result.static_personas.append(load_persona("philosophy_of_science", category="domain"))

    return result


# ---------------------------------------------------------------------------
# Static fallback (original GP-079 Option 3 table)
# ---------------------------------------------------------------------------

def _static_fallback(
    failure_families: list[str],
    *,
    max_reviewers: int = _MAX_REVIEWERS,
) -> RouteResult:
    """Original hand-authored routing table as fallback."""
    counts: dict[str, int] = {}
    recognized_any = False

    for family in failure_families:
        personas = _STATIC_ROUTING_TABLE.get(family)
        if personas:
            recognized_any = True
            for p in personas:
                counts[p] = counts.get(p, 0) + 1

    if not recognized_any:
        for p in _STATIC_ROUTING_TABLE["_default"]:
            counts[p] = counts.get(p, 0) + 1

    ranked = sorted(counts.keys(), key=lambda p: (-counts[p], p))
    names = ranked[:max_reviewers]

    result = RouteResult(routing_method="static_table")
    for name in names:
        try:
            result.static_personas.append(load_persona(name, category="domain"))
        except KeyError:
            pass
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def select_personas_for_iteration(
    failure_families: list[str],
    *,
    max_reviewers: int = _MAX_REVIEWERS,
    seam_context: str = "",
    use_llm_router: bool = True,
) -> RouteResult:
    """Return routed personas for the given failure families.

    When ``use_llm_router=True`` (default), uses the LLM to select from the
    static catalog and optionally generate a dynamic persona. Falls back to
    the static routing table if the LLM is unavailable.

    Set ``ZTARE_DISABLE_LLM_ROUTER=1`` to force static-table mode.
    """
    if os.environ.get("ZTARE_DISABLE_LLM_ROUTER") == "1":
        use_llm_router = False

    if use_llm_router:
        return _call_llm_router(
            failure_families,
            seam_context=seam_context,
            max_reviewers=max_reviewers,
        )
    return _static_fallback(failure_families, max_reviewers=max_reviewers)


def load_failure_families_from_latent_distance(workspace_dir: Path) -> list[str]:
    """Read the most recent failure_families from latent_distance.jsonl.

    Returns an empty list if the file doesn't exist or has no records.
    """
    ld_path = workspace_dir / "latent_distance.jsonl"
    if not ld_path.exists():
        return []

    last_record: dict | None = None
    for line in ld_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            last_record = json.loads(line)
        except json.JSONDecodeError:
            continue

    if last_record is None:
        return []

    sig = last_record.get("signature", {})
    return list(sig.get("failure_families", []))


def auto_select_from_workspace(
    workspace_dir: Path,
    *,
    max_reviewers: int = _MAX_REVIEWERS,
    seam_context: str = "",
) -> RouteResult:
    """Convenience: load families from workspace and return routed personas.

    Typical call site in findings runner or post-iteration hook:
        result = auto_select_from_workspace(project_dir / "workspace")
    """
    families = load_failure_families_from_latent_distance(workspace_dir)
    return select_personas_for_iteration(
        families,
        max_reviewers=max_reviewers,
        seam_context=seam_context,
    )


# ---------------------------------------------------------------------------
# Persona promotion — dynamic → static
# ---------------------------------------------------------------------------

def promote_dynamic_persona(persona: DynamicPersona) -> Path:
    """Write a dynamically generated persona to config/prompts/ as a static file.

    Returns the path to the newly created file. The persona becomes
    discoverable by the registry on the next ``list_personas()`` call.
    """
    prompts_dir = Path(__file__).parent.parent.parent.parent / "config" / "prompts"
    filename = f"reviewer_domain_{persona.name}.md"
    filepath = prompts_dir / filename

    if filepath.exists():
        print(
            f"[persona-router] promotion skipped: {filepath.name} already exists",
            flush=True,
        )
        return filepath

    content = f"# {persona.role}\n\n{persona.persona}"
    if persona.focus_area:
        content += f"\n\n**Focus area:** {persona.focus_area}"
    content += "\n"

    filepath.write_text(content, encoding="utf-8")
    print(
        f"[persona-router] promoted dynamic persona to static: {filepath.name}",
        flush=True,
    )
    return filepath
