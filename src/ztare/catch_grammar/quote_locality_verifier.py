"""Deterministic sidecar for any LLM auditor output that makes quote-based
claims about a target document.

Purpose
-------
An LLM auditor running against a prose target will, by construction, produce
probabilistic output. The failure mode we care about is not "bad judgment"
(that is what the rule wording is for) but **confabulation dressed as
grounding**: an auditor output that names a quote, a line range, or a claim
location that does not actually exist in the target, or that pairs a claim
with a "mechanism" that lives in a completely different paragraph.

This sidecar catches that class of failure deterministically. It knows
nothing about semantics. It only checks:

1. **Quote existence**: the verbatim quote the auditor named is literally
   present in the target text.
2. **Line-range truthfulness**: the line range the auditor named actually
   contains the quote.
3. **Paragraph-locality**: the claim span and the mechanism span (if both
   are named) fall inside the **same paragraph**, where paragraph is
   defined strictly as a contiguous block of non-blank lines terminated by
   a blank line or end-of-file.

Every LLM hit that fails any of these checks is killed. A hit that passes
all three is still only **grounded**, not **correct** — the LLM's semantic
judgment that a sentence is a "strong claim" or that another sentence is a
"mechanism" is not checked here. That is the limit of the cage: the cage
prevents the probabilistic sensor from lying about where it looked, not
from misinterpreting what it saw.

Honest scope
------------
- This module prevents fabrication of quotes and cross-paragraph drift.
- It does not prevent misclassification (LLM calling a non-claim a claim).
- It does not prevent prompt injection embedded in the target itself.
- It does not provide independence from the LLM's model family.

Those are separate problems. This file fixes the narrowest one cleanly.

No LLM calls. Stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuditorHit:
    """Shape an LLM auditor is required to emit for a single flagged hit.

    Required fields:
      rule             — catch grammar rule id (e.g. "defining_yourself_into_victory")
      claim_quote      — verbatim substring of target; the sentence flagged as a claim
      claim_line_start — 1-indexed line number where claim_quote begins

    Optional (present when the rule requires a paired mechanism check):
      mechanism_quote      — verbatim substring of target
      mechanism_line_start — 1-indexed line number where mechanism_quote begins

    Rationale for a fixed-shape dataclass: the whole point of the sidecar is
    that the LLM cannot hand-wave. If a field is missing the hit is killed.
    """
    rule: str
    claim_quote: str
    claim_line_start: int
    mechanism_quote: str | None = None
    mechanism_line_start: int | None = None


@dataclass
class VerificationResult:
    verdict: str  # "verified" | "killed"
    reasons: list[str] = field(default_factory=list)
    paragraph_index_claim: int | None = None
    paragraph_index_mechanism: int | None = None


def _paragraphs(text: str) -> list[tuple[int, int]]:
    """Return [(start_line, end_line), ...] for each paragraph.

    Paragraph = maximal contiguous block of non-blank lines, 1-indexed,
    inclusive on both ends. Blank line = line whose stripped content is "".
    A target with no blank lines is a single paragraph spanning the whole
    file.
    """
    lines = text.split("\n")
    paragraphs: list[tuple[int, int]] = []
    start: int | None = None
    for idx, line in enumerate(lines, start=1):
        blank = line.strip() == ""
        if not blank and start is None:
            start = idx
        elif blank and start is not None:
            paragraphs.append((start, idx - 1))
            start = None
    if start is not None:
        paragraphs.append((start, len(lines)))
    return paragraphs


def _paragraph_index_for_line(paragraphs: list[tuple[int, int]], line: int) -> int | None:
    for i, (s, e) in enumerate(paragraphs):
        if s <= line <= e:
            return i
    return None


def _quote_present_at_line(text: str, quote: str, claimed_line_start: int) -> bool:
    """Check quote exists in target AND its first occurrence starts within
    a small window of the claimed line.

    The window (±2 lines) is deliberate: a multi-line quote may begin on a
    line that differs slightly from the LLM's report depending on how it
    counted. Zero tolerance would be brittle; unbounded tolerance would
    make the line-range field meaningless. ±2 is the smallest tolerance
    that accommodates off-by-one/off-by-two line counting without letting
    a cross-paragraph drift slip through (most paragraphs are > 4 lines).
    """
    if not quote:
        return False
    if quote not in text:
        return False
    lines = text.split("\n")
    first_quote_line = quote.split("\n", 1)[0]
    if not first_quote_line.strip():
        return False
    # find the first non-blank source line that contains the quote's first
    # line; for a multi-line quote, also require the full quote to appear
    # at that position in the joined remainder.
    actual_start: int | None = None
    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if first_quote_line in line:
            # for multi-line quotes, confirm the full quote appears starting
            # somewhere in the joined tail
            if "\n" in quote:
                tail = "\n".join(lines[idx - 1:])
                if quote not in tail:
                    continue
            actual_start = idx
            break
    if actual_start is None:
        return False
    return abs(actual_start - claimed_line_start) <= 2


def verify_hit(target_text: str, hit: AuditorHit, *, require_mechanism: bool) -> VerificationResult:
    """Verify a single auditor hit against the target text.

    Parameters
    ----------
    target_text
        The document the auditor was asked to audit, exactly as the auditor
        saw it. Paragraph detection is done on this text.
    hit
        The auditor's structured output for one flagged location.
    require_mechanism
        True for rules whose `verification_check` requires a paired
        mechanism in the same paragraph (e.g. rule 1). False for rules
        that only need a single claim location.

    Returns
    -------
    VerificationResult
        verdict == "verified" means the hit is grounded. verdict == "killed"
        means the hit failed at least one structural check; reasons list
        every failing check.
    """
    result = VerificationResult(verdict="verified")
    paragraphs = _paragraphs(target_text)

    # Claim quote existence + line truthfulness.
    if not _quote_present_at_line(target_text, hit.claim_quote, hit.claim_line_start):
        result.reasons.append(
            f"claim_quote not found at or near claim_line_start={hit.claim_line_start}"
        )

    claim_para = _paragraph_index_for_line(paragraphs, hit.claim_line_start)
    result.paragraph_index_claim = claim_para
    if claim_para is None:
        result.reasons.append(
            f"claim_line_start={hit.claim_line_start} is outside any paragraph (blank line or past EOF)"
        )

    if require_mechanism:
        if hit.mechanism_quote is None or hit.mechanism_line_start is None:
            result.reasons.append(
                "rule requires mechanism_quote and mechanism_line_start but one or both are missing"
            )
        else:
            if not _quote_present_at_line(
                target_text, hit.mechanism_quote, hit.mechanism_line_start
            ):
                result.reasons.append(
                    f"mechanism_quote not found at or near mechanism_line_start={hit.mechanism_line_start}"
                )
            mech_para = _paragraph_index_for_line(paragraphs, hit.mechanism_line_start)
            result.paragraph_index_mechanism = mech_para
            if mech_para is None:
                result.reasons.append(
                    f"mechanism_line_start={hit.mechanism_line_start} is outside any paragraph"
                )
            elif claim_para is not None and mech_para != claim_para:
                result.reasons.append(
                    f"paragraph-locality violated: claim in paragraph {claim_para}, "
                    f"mechanism in paragraph {mech_para}"
                )

    if result.reasons:
        result.verdict = "killed"
    return result


def verify_hits(
    target_text: str, hits: list[AuditorHit], *, require_mechanism: bool
) -> list[dict[str, Any]]:
    """Verify a batch of auditor hits. Returns a list of dicts suitable for
    JSON serialization into a ledger."""
    out: list[dict[str, Any]] = []
    for i, hit in enumerate(hits):
        r = verify_hit(target_text, hit, require_mechanism=require_mechanism)
        out.append(
            {
                "index": i,
                "rule": hit.rule,
                "claim_quote": hit.claim_quote,
                "claim_line_start": hit.claim_line_start,
                "mechanism_quote": hit.mechanism_quote,
                "mechanism_line_start": hit.mechanism_line_start,
                "verdict": r.verdict,
                "reasons": r.reasons,
                "paragraph_index_claim": r.paragraph_index_claim,
                "paragraph_index_mechanism": r.paragraph_index_mechanism,
            }
        )
    return out
