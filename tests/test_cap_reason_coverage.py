"""Taxonomy-coverage planted test: every score_cap_reason the codebase can
emit must classify to a KNOWN cap kind. 'unknown' lawfully never triggers
REFRAME, so an unclassified reason silently disables the jump-forcer for
that failure mode (2026-07-12 incident: 'pre_judge_gate_harness_failed'
classified unknown through two 8-iteration stagnation rounds)."""
import re
from pathlib import Path

from ztare.orchestrator.cap_kind import classify_cap_kind

SRC = Path(__file__).resolve().parents[1]
PATTERNS = (
    re.compile(r'"score_cap_reason"\s*:\s*"([^"]+)"'),
    re.compile(r'score_cap_reason\s*=\s*"([^"]+)"'),
)


def _emitted_reasons():
    reasons = set()
    for root in (SRC / "src" / "ztare", SRC / "scripts" / "public"):
        for py in root.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pat in PATTERNS:
                for m in pat.finditer(text):
                    val = m.group(1)
                    if "{" not in val:  # skip f-string templates
                        reasons.add(val)
    return reasons


def test_every_emitted_cap_reason_classifies_known():
    reasons = _emitted_reasons()
    assert reasons, "no cap reasons found — pattern drift; fix the scan"
    unknown = sorted(r for r in reasons if classify_cap_kind(r) == "unknown")
    assert not unknown, (
        f"cap reasons classify 'unknown' — REFRAME is silently unreachable "
        f"for these failure modes: {unknown}. Add patterns to cap_kind.py."
    )
