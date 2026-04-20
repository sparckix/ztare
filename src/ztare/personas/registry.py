"""Persona registry — indexes named persona definitions from ``config/prompts/``.

DISCLAIMER: Personas named after real individuals (e.g., "Dijkstra," "Munger,"
"Knuth," "Norvig") are stylistic shorthand for reasoning approaches loosely
inspired by their published work. They do not represent the views, endorsements,
or actual reasoning of those individuals. The same applies to debater labels
used in seam debate logs.

Sources (all live under config/prompts/):
  - Domain lenses:   ``reviewer_domain_<name>.md``   → category="domain"
  - Audit roles:     ``audit_persona_<name>.md``      → category="audit"
  - Methodology:     ``methodology_persona_<name>.md``→ category="methodology"

Shadow-board roles (inline in shadow_board.py) are exposed here as a thin
adapter so callers get a unified interface without requiring a file migration.

Do NOT conflate with dynamic committee generation (generate_committee.py).
The registry is a static library; committee composition is one consumer of it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "config" / "prompts"

_PREFIX_TO_CATEGORY: dict[str, str] = {
    "reviewer_domain_": "domain",
    "audit_persona_": "audit",
    "methodology_persona_": "methodology",
}


@dataclass(frozen=True)
class PersonaDefinition:
    name: str
    category: str        # domain | audit | methodology
    role: str
    persona: str
    focus_area: str
    tags: tuple[str, ...]
    profile_key: str     # "<category>/<name>" — for traceability


def _parse_md(path: Path, category: str, name: str) -> PersonaDefinition:
    text = path.read_text(encoding="utf-8").strip()
    # Role: first # heading
    role_match = re.match(r"^#\s+(.+)", text, re.MULTILINE)
    role = role_match.group(1).strip() if role_match else name.replace("_", " ").title()
    # Remove heading from persona body
    persona_body = re.sub(r"^#\s+.+\n?", "", text, count=1).strip()
    return PersonaDefinition(
        name=name,
        category=category,
        role=role,
        persona=persona_body,
        focus_area="",   # not structured in markdown files; callers use full persona text
        tags=(),
        profile_key=f"{category}/{name}",
    )


def _discover_file_personas() -> dict[str, PersonaDefinition]:
    result: dict[str, PersonaDefinition] = {}
    if not _PROMPTS_DIR.exists():
        return result
    for path in sorted(_PROMPTS_DIR.glob("*.md")):
        for prefix, category in _PREFIX_TO_CATEGORY.items():
            if path.stem.startswith(prefix):
                name = path.stem[len(prefix):]
                key = f"{category}/{name}"
                result[key] = _parse_md(path, category, name)
                break
    return result


def _shadow_board_personas() -> dict[str, PersonaDefinition]:
    """Expose shadow-board ROLE_DEFINITIONS as audit personas without file migration."""
    try:
        from src.ztare.validator.shadow_board import ROLE_DEFINITIONS  # type: ignore
    except ImportError:
        return {}
    result: dict[str, PersonaDefinition] = {}
    for role_enum, defn in ROLE_DEFINITIONS.items():
        name = role_enum.value.lower()
        key = f"audit/{name}"
        result[key] = PersonaDefinition(
            name=name,
            category="audit",
            role=defn["role"],
            persona=defn["persona"],
            focus_area=defn.get("focus_area", ""),
            tags=("audit", "shadow-board"),
            profile_key=key,
        )
    return result


def _all_personas() -> dict[str, PersonaDefinition]:
    personas = _shadow_board_personas()
    personas.update(_discover_file_personas())   # file-based wins on conflict
    return personas


def load_persona(name: str, category: str | None = None) -> PersonaDefinition:
    """Load a single persona by name (and optionally category).

    ``name`` may be a bare name (``"philosophy_of_science"``) or a
    qualified key (``"domain/philosophy_of_science"``).

    Raises ``KeyError`` if not found.
    """
    if "/" in name and category is None:
        category, name = name.split("/", 1)

    all_p = _all_personas()
    if category:
        key = f"{category}/{name}"
        if key in all_p:
            return all_p[key]
    else:
        for key, p in all_p.items():
            if p.name == name:
                return p

    raise KeyError(
        f"Persona {name!r} (category={category!r}) not found. "
        f"Available: {sorted(all_p)}"
    )


def list_personas(category: str | None = None) -> list[str]:
    """Return sorted list of profile_keys (``<category>/<name>``)."""
    keys = list(_all_personas())
    if category:
        keys = [k for k in keys if k.startswith(f"{category}/")]
    return sorted(keys)


def load_personas(names: list[str], category: str | None = None) -> list[PersonaDefinition]:
    """Load multiple personas by name list."""
    return [load_persona(n, category=category) for n in names]


def format_for_injection(persona: PersonaDefinition, *, include_focus: bool = True) -> str:
    """Return a text block suitable for injecting into an LLM prompt."""
    lines = [f"## {persona.role}", "", persona.persona]
    if include_focus and persona.focus_area:
        lines += ["", f"**Focus area:** {persona.focus_area}"]
    return "\n".join(lines)


def format_many_for_injection(
    personas: list[PersonaDefinition], *, include_focus: bool = True
) -> str:
    """Concatenate multiple persona blocks with a separator."""
    blocks = [format_for_injection(p, include_focus=include_focus) for p in personas]
    return "\n\n---\n\n".join(blocks)
