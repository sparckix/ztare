"""GP-226 L2 + L3 briefing compression for charter-critic-accumulated content.

The MutatorBriefing tier system (paper 7 §11.15) already governs auxiliary
briefing PROVIDERS with a 12K char budget + T0-T5 gating. But it does NOT
govern the directly-read ``evidence.txt`` and ``project_charter.md``,
which charter-critic appends REFRAME PRESSURE blocks to over multiple
runs. After 5+ runs on a project, these artifacts can grow to 60-80KB
of accumulated pressures, drowning the mutator's signal.

This module provides:

  L2 — ACTIVE-PRESSURES SUMMARY header injection. Replaces 5KB+ of
       expanded REFRAME PRESSURE blocks with a 500-byte summary of which
       primitives have active patches and at what cross-run counts.
       Mutator sees the operational state at run-start, not the
       accumulated history.

  L3 — STALE-PRESSURE EXPIRY suppression. REFRAME PRESSURE blocks whose
       source patches in the ledger are older than ``expiry_runs``
       (default 5) without re-attestation are suppressed from the
       mutator-visible view. The block stays on disk for git history;
       only the mutator's read-time view drops it.

  BONUS — SAME-PRIMITIVE SUPERSESSION. When N patches in the same
       primitive exist (e.g., 4 velocity-vs-level patches all in BOUND),
       only the most recent ONE is shown — older ones are tagged
       superseded in the summary header.

Non-destructive: the on-disk evidence.txt and project_charter.md are
unchanged. Only the strings passed to the mutator-prompt-builder are
filtered.

Activation: rubric flag ``enable_briefing_compression: true``. Default
off so existing projects retain legacy behavior.

Hooked from ``autoresearch_loop.py`` at:
  - Line ~3420 (initial evidence read at run start)
  - Line ~4177 (evidence_reload_per_iter mid-run reread)
  - Line ~1536 (project_charter read)
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REFRAME_HEADER_PATTERN = re.compile(
    r"^(##\s+REFRAME\s+PRESSURE.*?)$",
    re.MULTILINE | re.IGNORECASE,
)


@dataclass
class CompressionTelemetry:
    enabled: bool = True
    pressure_blocks_seen: int = 0
    suppressed_expired: int = 0
    suppressed_superseded: int = 0
    summary_header_bytes: int = 0
    bytes_before: int = 0
    bytes_after: int = 0
    suppressed_block_titles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "pressure_blocks_seen": self.pressure_blocks_seen,
            "suppressed_expired": self.suppressed_expired,
            "suppressed_superseded": self.suppressed_superseded,
            "summary_header_bytes": self.summary_header_bytes,
            "bytes_before": self.bytes_before,
            "bytes_after": self.bytes_after,
            "bytes_saved": self.bytes_before - self.bytes_after,
            "suppressed_block_titles": self.suppressed_block_titles,
        }


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _read_ledger(project_dir: Path) -> list[dict[str, Any]]:
    ledger_path = project_dir / "workspace" / "charter_patches.jsonl"
    if not ledger_path.exists():
        return []
    out = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _split_pressure_blocks(text: str) -> list[tuple[str, str]]:
    """Split text into (header_or_intro, blocks) where each block is one
    `## REFRAME PRESSURE` H2 section. The first element is everything
    BEFORE the first REFRAME PRESSURE header (kept as-is)."""
    matches = list(REFRAME_HEADER_PATTERN.finditer(text))
    if not matches:
        return [("intro", text)]
    sections: list[tuple[str, str]] = []
    sections.append(("intro", text[:matches[0].start()]))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block_text = text[m.start():end]
        sections.append((m.group(1).strip(), block_text))
    return sections


def _block_signature(block_text: str) -> str:
    """Compute a normalized signature for deduplication of REFRAME PRESSURE
    blocks. Strips ALL leading `## REFRAME PRESSURE` lines (handles double-H2
    section_id wrappers from _apply_patch), then takes first 200 chars of
    body content, lowercased, whitespace-normalized."""
    body = block_text
    # Strip up to 3 leading H2 REFRAME PRESSURE headers (handles wrapper + body)
    for _ in range(3):
        new_body = re.sub(
            r"^##\s+REFRAME\s+PRESSURE.*?(?:\n|$)",
            "",
            body,
            count=1,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        if new_body == body:
            break
        body = new_body.lstrip()
    sig = re.sub(r"\s+", " ", body[:300].lower()).strip()
    return sig[:200]


# ----------------------------------------------------------------------------
# Active-pressures summary header (L2)
# ----------------------------------------------------------------------------

def _build_active_pressures_summary(
    project_dir: Path,
    rubric_data: dict[str, Any],
) -> str:
    """Build a compact summary of which primitives have active patches
    on this project, with cross-run counts and the PRIMITIVE-CEILING
    status. Returns a 300-700 byte markdown block."""
    try:
        from ztare.orchestrator.charter_critic import (
            SUBSTRATE_TAXONOMIES,
            PRIMITIVE_DERIVE,
            PRIMITIVE_BOUND,
            PRIMITIVE_OBSERVE,
            _count_cross_run_patches_for_primitive,
        )
    except Exception:
        return ""

    # Resolve substrate class via value spec or rubric cage_meta
    spec_path = project_dir / "operator_value_spec.yaml"
    substrate_class = "qualitative_thesis"
    if spec_path.exists():
        try:
            from ztare.orchestrator.charter_critic import load_value_spec
            spec = load_value_spec(project_dir, rubric_data=rubric_data, auto_generate=False)
            if spec:
                substrate_class = str(spec.get("substrate_class") or substrate_class)
        except Exception:
            pass
    taxonomy = SUBSTRATE_TAXONOMIES.get(substrate_class, {})
    if not taxonomy:
        return ""

    rows = []
    ceiling_fired = []
    for primitive in (PRIMITIVE_DERIVE, PRIMITIVE_BOUND, PRIMITIVE_OBSERVE):
        count = _count_cross_run_patches_for_primitive(project_dir, primitive, taxonomy)
        if count == 0:
            continue
        marker = ""
        if count >= 5:
            marker = " 🛑 PRIMITIVE-CEILING"
            ceiling_fired.append(primitive)
        elif count >= 3:
            marker = " ⚠️  escalation"
        rows.append(f"- **{primitive}**: {count} active patch(es) across buckets{marker}")

    if not rows:
        return ""

    ceiling_directive = ""
    if ceiling_fired:
        primitives_str = ", ".join(ceiling_fired)
        ceiling_directive = (
            f"\n\n**PRIMITIVE-CEILING DIRECTIVE:** the {primitives_str} "
            f"primitive(s) have been patched ≥5× across multiple bucket "
            "instantiations. Acknowledgment-without-derivation is exhausted "
            "as a response mode. The thesis must produce either (a) a "
            f"meta-{primitives_str.lower()} argument deriving why the "
            "thesis cannot be honored at this capability tier and a "
            "reformulated eigenquestion that is honorable, or (b) explicit "
            "admission that the substrate has reached its ceiling on this "
            "primitive and a scope-reduced eigenquestion the apparatus "
            "can answer with a derived (not asserted) boundary. Continued "
            "non-delivery is not admissible."
        )

    rows_block = "\n".join(rows)
    return (
        "<!-- GP-226 charter-critic state (briefing-compression L2 header) -->\n"
        "## ACTIVE PRESSURES (charter-critic state at run-start)\n\n"
        f"{rows_block}{ceiling_directive}\n\n"
        "Each primitive's expanded REFRAME PRESSURE blocks have been "
        "compressed into this summary; the full text remains in evidence.txt "
        "and project_charter.md on disk for audit. Older patches "
        f"(>{int(rubric_data.get('briefing_compression_expiry_runs', 5))} "
        "runs) and same-primitive predecessors are suppressed from the "
        "mutator view; only the latest patch per primitive is shown.\n\n"
        "---\n\n"
    )


# ----------------------------------------------------------------------------
# Block-level filtering (L3 + supersession)
# ----------------------------------------------------------------------------

def _select_blocks_to_keep(
    blocks: list[tuple[str, str]],
    project_dir: Path,
    rubric_data: dict[str, Any],
    telemetry: CompressionTelemetry,
) -> list[tuple[str, str]]:
    """Decide which REFRAME PRESSURE blocks survive into the mutator-
    visible view.

    Rules:
      1. The "intro" section (everything before first REFRAME PRESSURE) is
         always kept verbatim.
      2. Each REFRAME PRESSURE block is matched against the patch ledger
         by content signature.
         - If matched ledger entry is committed AND age <= expiry_runs:
           candidate KEEP.
         - If matched ledger entry is committed AND age > expiry_runs:
           SUPPRESS (expired, L3).
         - If no ledger match: KEEP (operator-authored or pre-charter-critic
           historical content).
      3. Among candidate-KEEP blocks tagged with the same primitive (via
         ledger entry), keep ONLY the most recent (latest created_run_id).
         Older ones are SUPPRESSED (superseded). Operator-authored blocks
         (no ledger match) are exempt — they're preserved.
    """
    expiry = int(rubric_data.get("briefing_compression_expiry_runs", 5))
    supersede = bool(rubric_data.get("briefing_compression_supersede_same_primitive", True))

    entries = _read_ledger(project_dir)
    distinct_runs = sorted({e.get("created_run_id", "") for e in entries if e.get("created_run_id")})
    # Backfill primitive from reframe_type via taxonomy for legacy ledger
    # entries that predate the `primitive` field on fingerprint_match.
    try:
        from ztare.orchestrator.charter_critic import (
            SUBSTRATE_TAXONOMIES, primitive_for_bucket,
        )
        from ztare.orchestrator.charter_critic import load_value_spec as _load_vs
        _vs = _load_vs(project_dir, rubric_data=rubric_data, auto_generate=False)
        _substrate = (_vs or {}).get("substrate_class", "qualitative_thesis")
        _taxonomy = SUBSTRATE_TAXONOMIES.get(_substrate, {})
    except Exception:
        _taxonomy = {}
        primitive_for_bucket = lambda *a, **k: None  # noqa: E731

    sig_to_entry: dict[str, dict[str, Any]] = {}
    for e in entries:
        body = e.get("body", "") or ""
        # Body already includes the H2 header for charter-critic patches;
        # _block_signature handles stripping any leading H2 wrappers.
        sig = _block_signature(body)
        # Backfill primitive from reframe_type if missing on the entry
        fm = e.get("fingerprint_match") or {}
        if fm.get("primitive") is None:
            inferred = primitive_for_bucket(e.get("reframe_type", ""), _taxonomy)
            if inferred:
                fm = {**fm, "primitive": inferred}
                e["fingerprint_match"] = fm  # in-memory only; doesn't write back
        if sig:
            sig_to_entry[sig] = e

    annotated: list[dict[str, Any]] = []
    for kind, block_text in blocks:
        if kind == "intro":
            annotated.append({"kind": "intro", "block_text": block_text, "keep": True})
            continue
        telemetry.pressure_blocks_seen += 1
        sig = _block_signature(block_text)
        entry = sig_to_entry.get(sig)
        if entry is None:
            annotated.append({"kind": "block", "block_text": block_text,
                              "title": kind, "entry": None, "primitive": None,
                              "created_run_id": None, "keep": True,
                              "reason": "no_ledger_match_(operator_or_legacy)"})
            continue
        creation_run = entry.get("created_run_id", "")
        age = sum(1 for r in distinct_runs if r > creation_run)
        primitive = (entry.get("fingerprint_match") or {}).get("primitive")
        if age >= expiry:
            telemetry.suppressed_expired += 1
            telemetry.suppressed_block_titles.append(f"{kind} [expired age={age}]")
            annotated.append({"kind": "block", "block_text": block_text,
                              "title": kind, "entry": entry, "primitive": primitive,
                              "created_run_id": creation_run, "keep": False,
                              "reason": f"expired:age={age}"})
            continue
        annotated.append({"kind": "block", "block_text": block_text,
                          "title": kind, "entry": entry, "primitive": primitive,
                          "created_run_id": creation_run, "keep": True,
                          "reason": "active"})

    # Same-primitive supersession: among kept blocks per primitive (with
    # ledger entry), only keep the most recent.
    if supersede:
        by_primitive: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for a in annotated:
            if a["kind"] != "block":
                continue
            if not a.get("keep"):
                continue
            if a.get("primitive") is None:
                continue
            by_primitive[a["primitive"]].append(a)
        for primitive, group in by_primitive.items():
            if len(group) <= 1:
                continue
            group_sorted = sorted(
                group, key=lambda d: d.get("created_run_id") or "", reverse=True,
            )
            for older in group_sorted[1:]:
                older["keep"] = False
                older["reason"] = f"superseded_by_same_primitive_latest"
                telemetry.suppressed_superseded += 1
                telemetry.suppressed_block_titles.append(
                    f"{older['title']} [superseded primitive={primitive}]"
                )

    return [
        (a.get("title", a["kind"]), a["block_text"])
        for a in annotated
        if a.get("keep")
    ]


# ----------------------------------------------------------------------------
# Public entry points
# ----------------------------------------------------------------------------

def compress_briefing(
    *,
    evidence_text: str,
    charter_text: str,
    project_dir: Path | str,
    rubric_data: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    """L2 + L3 briefing compression.

    Returns ``(compressed_evidence, compressed_charter, telemetry)``.
    Non-destructive — does not modify on-disk artifacts.

    When ``rubric.enable_briefing_compression`` is false (default), this
    is a no-op pass-through and the inputs are returned verbatim.
    """
    telemetry = CompressionTelemetry()
    telemetry.bytes_before = len(evidence_text.encode("utf-8")) + len(charter_text.encode("utf-8"))
    if not bool(rubric_data.get("enable_briefing_compression", False)):
        telemetry.enabled = False
        telemetry.bytes_after = telemetry.bytes_before
        return evidence_text, charter_text, telemetry.to_dict()

    project_dir = Path(project_dir)

    summary_header = _build_active_pressures_summary(project_dir, rubric_data)
    telemetry.summary_header_bytes = len(summary_header.encode("utf-8"))

    # Process evidence
    ev_blocks = _split_pressure_blocks(evidence_text)
    ev_kept = _select_blocks_to_keep(ev_blocks, project_dir, rubric_data, telemetry)
    compressed_evidence = "".join(b for _, b in ev_kept)
    if summary_header:
        compressed_evidence = summary_header + compressed_evidence

    # Process charter
    ch_blocks = _split_pressure_blocks(charter_text)
    ch_kept = _select_blocks_to_keep(ch_blocks, project_dir, rubric_data, telemetry)
    compressed_charter = "".join(b for _, b in ch_kept)

    telemetry.bytes_after = len(compressed_evidence.encode("utf-8")) + len(compressed_charter.encode("utf-8"))
    return compressed_evidence, compressed_charter, telemetry.to_dict()
