"""Token-budgeted context builder for GP-036 findings-runner prompts.

This module is Deliverable 5 of GP-036 Slice A. It assembles tiered
context blocks (board row, related-seam excerpts, cited-artifact
excerpts) that the findings runner injects into a debate-turn prompt so
the debate agents are not context-starved the way GP-034 demonstrated.

Design boundaries from the GP-036 seam + spec:

- No artifact discovery beyond explicit citations. The builder does not
  grep the workspace for files that "look related" — it only reads
  files the seam text names verbatim.
- No code-snippet injection in Slice A. ``src/ztare/*`` excerpts are
  behind a Tier 4 flag that does not ship in Slice A.
- Every injected block carries a provenance header naming its source
  path. Trust seam first, quality seam second.
- Token budget is a hard cap. Tiers 0-1 are mandatory (seam text + board
  row). Tiers 2-3 are best-effort within the remaining budget.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.ztare.common.paths import REPO_ROOT


DEFAULT_TOKEN_BUDGET = 30_000
"""Default total context budget in tokens. Leaves room for the agent's
own reasoning inside a typical 200k-token context window."""

_CHARS_PER_TOKEN = 4
"""Rough heuristic for token estimation from character count. Good
enough for budget enforcement; the runner is not trying to hit the
budget exactly, just to avoid blowing past it."""

RELATED_SEAM_LINE_LIMIT = 200
"""Maximum lines read from each related-seam file."""

CITED_ARTIFACT_LINE_LIMIT = 100
"""Maximum lines read from each cited workspace artifact."""

PRIVATE_BOARD_PATH = REPO_ROOT / "research_areas" / "private" / "ZTARE_BOARD.md"


@dataclass(frozen=True)
class ContextTier:
    """One provenance-tagged context block."""

    label: str
    """One of: ``BOARD_ROW``, ``RELATED_SEAM_EXCERPT``,
    ``CITED_ARTIFACT_EXCERPT``."""

    source_path: str
    """Path of the underlying file, relative to repo root when possible."""

    content: str
    """The raw text to inject."""

    token_estimate: int
    """Rough token count (chars / 4)."""


def estimate_tokens(text: str) -> int:
    """Very rough char/4 token estimate. Off by ~25% is fine here."""

    return max(1, len(text) // _CHARS_PER_TOKEN)


def _format_tier(tier: ContextTier) -> str:
    header = f"--- {tier.label} (source: {tier.source_path}) ---"
    return f"{header}\n{tier.content.rstrip()}\n"


def format_context_tiers(tiers: list[ContextTier]) -> str:
    """Render a list of tiers as a single prompt-injection string."""

    if not tiers:
        return ""
    return "\n".join(_format_tier(t) for t in tiers)


_GP_ID_RE = re.compile(r"\bGP-\d{3,4}\b")


def _extract_gp_id_from_seam_path(seam_path: Path) -> str | None:
    """Pick the first GP-ID token out of the seam filename."""

    match = _GP_ID_RE.search(seam_path.name)
    return match.group(0) if match else None


def _load_board_row_for(gp_id: str) -> ContextTier | None:
    """Find the first ZTARE board row whose leading cell names ``gp_id``.

    The private board is a pipe-delimited markdown table; rows start
    with ``| GP-NNN |``. We walk the file linearly because the board is
    only ~150 lines and parsing with a markdown library would be
    disproportionate."""

    if not PRIVATE_BOARD_PATH.exists():
        return None
    prefix = f"| {gp_id} "
    for raw_line in PRIVATE_BOARD_PATH.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith(prefix):
            content = raw_line.strip()
            try:
                rel_source = str(PRIVATE_BOARD_PATH.relative_to(REPO_ROOT))
            except ValueError:
                rel_source = str(PRIVATE_BOARD_PATH)
            return ContextTier(
                label="BOARD_ROW",
                source_path=rel_source,
                content=content,
                token_estimate=estimate_tokens(content),
            )
    return None


_SEAM_REFERENCE_RE = re.compile(
    r"(research_areas/(?:private/)?seams/[A-Za-z0-9_./-]+?\.md)"
)


def _extract_related_seam_paths(seam_text: str, self_path: Path) -> list[Path]:
    """Pull seam-file references out of the seam text.

    Matches anything of the form ``research_areas/seams/...md`` or
    ``research_areas/private/seams/...md``, excluding the seam file
    itself. Order is preserved and duplicates are removed."""

    seen: set[str] = set()
    ordered: list[Path] = []
    try:
        self_rel = str(self_path.relative_to(REPO_ROOT))
    except ValueError:
        self_rel = str(self_path)
    for match in _SEAM_REFERENCE_RE.finditer(seam_text):
        rel = match.group(1)
        if rel == self_rel:
            continue
        if rel in seen:
            continue
        seen.add(rel)
        ordered.append(REPO_ROOT / rel)
    return ordered


_SPEC_REFERENCE_RE = re.compile(
    r"(research_areas/(?:private/)?specs/active/[A-Za-z0-9_./-]+?\.md)"
)


def _extract_related_spec_paths(seam_text: str) -> list[Path]:
    """Pull spec-file references out of the seam text.

    Matches ``research_areas/specs/active/...md`` or
    ``research_areas/private/specs/active/...md``. Order preserved,
    duplicates removed. Specs are the distillation layer the seam
    feeds; when the seam cites a spec the debate agents need the
    current spec content to reason about 'does this turn change what
    the spec should say?' without the operator pasting excerpts by
    hand."""

    seen: set[str] = set()
    ordered: list[Path] = []
    for match in _SPEC_REFERENCE_RE.finditer(seam_text):
        rel = match.group(1)
        if rel in seen:
            continue
        seen.add(rel)
        ordered.append(REPO_ROOT / rel)
    return ordered


_WORKSPACE_ARTIFACT_RE = re.compile(
    r"(projects/[A-Za-z0-9_./-]+?/workspace/[A-Za-z0-9_./-]+)"
)


def _extract_cited_artifact_paths(seam_text: str) -> list[Path]:
    """Pull explicit ``projects/<name>/workspace/<file>`` citations.

    Slice A deliberately does NOT match ``src/ztare/*`` — code-snippet
    injection is a Tier 4 capability behind a flag that does not ship
    here. If the seam wants code, the operator can paste it in a
    turn."""

    seen: set[str] = set()
    ordered: list[Path] = []
    for match in _WORKSPACE_ARTIFACT_RE.finditer(seam_text):
        rel = match.group(1)
        if rel in seen:
            continue
        seen.add(rel)
        ordered.append(REPO_ROOT / rel)
    return ordered


def _read_head(path: Path, *, line_limit: int) -> str:
    """Read the first ``line_limit`` lines of ``path`` as UTF-8."""

    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    lines = text.splitlines()
    if len(lines) <= line_limit:
        return text
    truncated = "\n".join(lines[:line_limit])
    return truncated + f"\n\n[... truncated after {line_limit} lines ...]\n"


def _relative_source(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def build_findings_context(
    *,
    seam_path: Path,
    seam_text: str,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> list[ContextTier]:
    """Assemble tiered context blocks for a findings-debate turn.

    Tier ordering (deterministic, per GP-036 seam + spec):

    - Tier 1: board row for this seam's GP-ID (mandatory, small)
    - Tier 2: related-seam excerpts (bounded by budget)
    - Tier 2.5: related-spec excerpts (bounded by budget). A seam
      citing a spec gets the spec content auto-injected so the debate
      can reason about whether this turn changes what the spec should
      say.
    - Tier 3: cited workspace-artifact excerpts (bounded by remaining
      budget)

    Tier 0 (the full seam text itself) is NOT returned from this
    function. The runner already puts the seam text into its own
    ``--- BEGIN SEAM ---`` block; duplicating it here would waste
    budget. The token budget governs tiers 1-3 only.

    Budget behavior: blocks are added in tier order. A block that would
    push total tokens over ``token_budget`` is skipped; later (smaller)
    blocks in the same tier may still fit."""

    tiers: list[ContextTier] = []
    used_tokens = 0

    # Tier 1 — board row
    gp_id = _extract_gp_id_from_seam_path(seam_path)
    if gp_id is not None:
        row = _load_board_row_for(gp_id)
        if row is not None and used_tokens + row.token_estimate <= token_budget:
            tiers.append(row)
            used_tokens += row.token_estimate

    # Tier 2 — related seam excerpts
    for related in _extract_related_seam_paths(seam_text, seam_path):
        content = _read_head(related, line_limit=RELATED_SEAM_LINE_LIMIT)
        if not content:
            continue
        tier = ContextTier(
            label="RELATED_SEAM_EXCERPT",
            source_path=_relative_source(related),
            content=content,
            token_estimate=estimate_tokens(content),
        )
        if used_tokens + tier.token_estimate > token_budget:
            continue
        tiers.append(tier)
        used_tokens += tier.token_estimate

    # Tier 2.5 — related spec excerpts
    for spec in _extract_related_spec_paths(seam_text):
        content = _read_head(spec, line_limit=RELATED_SEAM_LINE_LIMIT)
        if not content:
            continue
        tier = ContextTier(
            label="SPEC_EXCERPT",
            source_path=_relative_source(spec),
            content=content,
            token_estimate=estimate_tokens(content),
        )
        if used_tokens + tier.token_estimate > token_budget:
            continue
        tiers.append(tier)
        used_tokens += tier.token_estimate

    # Tier 3 — cited workspace artifacts
    for artifact in _extract_cited_artifact_paths(seam_text):
        content = _read_head(artifact, line_limit=CITED_ARTIFACT_LINE_LIMIT)
        if not content:
            continue
        tier = ContextTier(
            label="CITED_ARTIFACT_EXCERPT",
            source_path=_relative_source(artifact),
            content=content,
            token_estimate=estimate_tokens(content),
        )
        if used_tokens + tier.token_estimate > token_budget:
            continue
        tiers.append(tier)
        used_tokens += tier.token_estimate

    return tiers
