"""Context de-identification — bypass the 'this is an open problem' refusal.

Per Google's "Accelerating Scientific Research with Gemini" (arXiv:2602.03837v3,
2026, §2.7):

  > "When shown the paper as context in the prompt, [the model] recognizes
     the statement to prove as a conjecture in the paper and refuses to
     attempt it on the grounds that it is an open problem. One way to
     bypass both issues is via context de-identification (remove the paper
     and provide only the problem statement and definitions), after which
     the model typically engages."

This is a real LLM failure mode: when the model recognizes context as a
specific paper containing an open conjecture, it's trained to be
conservative about claiming to solve it. Stripping the paper context and
giving only the problem statement (with necessary definitions) bypasses
the refusal mechanism.

# Where ZTARE doesn't already do this

ZTARE has charter-contamination defenses (sanitize ground-truth from the
mutator's view) and various "remove this from prompt" utilities. But the
SPECIFIC operation — strip paper attribution + arxiv ID + author names +
"conjecture" / "open problem" framing while keeping the mathematical
content — is the gap this script fills.

# Two operations

  1. `deidentify_text(text)` — strip paper-identifying phrases, arxiv IDs,
     author names, "open problem" / "conjecture" / "we prove" framing.
     Returns text with mathematical content preserved but identifying
     metadata removed.

  2. `extract_problem_statement(text)` — pull the bare problem statement
     + definitions, dropping all narrative. Returns the minimal content
     a model needs to engage.

# When to use

  - LLM refused with "# CANNOT PATCH" or "this is an open problem"
  - Codex wants to retry the same target with stripped context
  - Pre-feed a paper section into typed-endpoint pack but want to avoid
    triggering the conservatism

# Substrate-agnostic

Operates on arbitrary text. Defaults catch common patterns; extend
`SENSITIVE_PATTERNS` for substrate-specific identifiers.

Usage:
    python scripts/public/utilities/context_deidentifier.py --in paper.md --out paper_clean.md
    python scripts/public/utilities/context_deidentifier.py --diff paper.md  # shows what gets stripped
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# Patterns the model's "this is an open problem; I should be conservative"
# detector latches onto. Strip these while keeping math intact.
SENSITIVE_PATTERNS = [
    # arXiv IDs
    (re.compile(r"arXiv:\s*\d{4}\.\d{4,5}(?:v\d+)?", re.IGNORECASE), "[paper-ref-stripped]"),
    (re.compile(r"https?://arxiv\.org/[^\s)]+", re.IGNORECASE), "[arxiv-link-stripped]"),
    # Author attribution
    (re.compile(r"\b(?:by|due to)\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2}\s*(?:et al\.|and [A-Z][A-Za-z]+)?", re.IGNORECASE),
     "[author-attribution-stripped]"),
    # Conjecture / open-problem framing
    (re.compile(r"\bopen\s+(?:problem|question|conjecture)\b", re.IGNORECASE), "the problem"),
    (re.compile(r"\b(?:long-standing|outstanding|notorious)\s+(?:problem|conjecture)\b", re.IGNORECASE),
     "the problem"),
    (re.compile(r"\bunsolved\s+(?:problem|conjecture)\b", re.IGNORECASE), "the problem"),
    (re.compile(r"\bMillennium\s+(?:Prize|Problem)\b", re.IGNORECASE), "the problem"),
    (re.compile(r"\bClay\s+(?:Mathematics\s+Institute|Prize|Problem)\b", re.IGNORECASE), "the problem"),
    # "We prove" / "we show" / "main theorem" — paper-flavored framing
    (re.compile(r"\b(?:Theorem|Conjecture|Proposition)\s+\d+(?:\.\d+)*", re.IGNORECASE),
     "the statement"),
    (re.compile(r"\b(?:Main\s+(?:Theorem|Result)|Theorem\s+[A-Z])\b", re.IGNORECASE),
     "the statement"),
    # Citation brackets like [1], [Smi23], etc.
    (re.compile(r"\[\d+(?:[,\s\-]\d+)*\]"), ""),
    (re.compile(r"\[[A-Z][A-Za-z]+\d{2,4}[a-z]?\]"), ""),
    # "as shown in [Author Year]"
    (re.compile(r"\b(?:as\s+shown|proven|established)\s+(?:in|by)\s+\[[^\]]+\]", re.IGNORECASE),
     "(established)"),
]


def deidentify_text(text: str, extra_patterns: list[tuple] | None = None) -> tuple[str, list[str]]:
    """Strip identifying metadata; preserve math content.

    Returns (deidentified_text, list_of_changes_for_audit).
    """
    out = text
    changes = []
    patterns = list(SENSITIVE_PATTERNS)
    if extra_patterns:
        patterns.extend(extra_patterns)
    for pat, repl in patterns:
        matches = pat.findall(out)
        if matches:
            for m in (matches if not isinstance(matches[0], tuple) else [str(m) for m in matches][:5]):
                changes.append(f"  '{m if isinstance(m, str) else str(m)[:80]}' → '{repl}'")
        out = pat.sub(repl, out)
    return out, changes


def extract_problem_statement(text: str, max_chars: int = 3000) -> str:
    """Pull the minimum problem-statement content the model needs.

    Heuristic: extract the FIRST mathematical block (def / theorem / conjecture
    statement) plus surrounding definitions. Drop narrative paragraphs.
    """
    # Find the first "Let X be..." / "Define X..." / "Consider..." / theorem block
    starts = []
    for pat in (
        re.compile(r"^(?:Let|Define|Consider|Suppose)\b", re.MULTILINE),
        re.compile(r"^(?:Theorem|Conjecture|Proposition|Lemma)\b", re.MULTILINE | re.IGNORECASE),
        re.compile(r"\\begin\{theorem\}|\\begin\{conjecture\}|\\begin\{definition\}",
                    re.IGNORECASE),
    ):
        for m in pat.finditer(text):
            starts.append(m.start())
    if not starts:
        # No structured marker — return head
        return text[:max_chars]
    start = min(starts)
    # Take from first marker forward
    chunk = text[start:start + max_chars]
    # De-identify the chunk
    cleaned, _ = deidentify_text(chunk)
    return cleaned


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input_file", type=Path,
                    help="input file (markdown / text / Lean comments)")
    ap.add_argument("--text", help="inline text to de-identify (alternative to --in)")
    ap.add_argument("--out", type=Path, help="output file (default: stdout)")
    ap.add_argument("--diff", action="store_true",
                    help="show what gets stripped, don't write")
    ap.add_argument("--extract-statement", action="store_true",
                    help="also run extract_problem_statement to surface bare problem")
    args = ap.parse_args()

    if args.input_file:
        text = args.input_file.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        ap.print_help()
        return 1

    cleaned, changes = deidentify_text(text)

    if args.diff:
        print("=== de-identification changes ===")
        for c in changes:
            print(c)
        if not changes:
            print("  (no patterns matched)")
        print(f"\n  total replacements: {len(changes)}")
        print(f"  input length: {len(text)} → output length: {len(cleaned)}")
        return 0

    if args.extract_statement:
        cleaned = extract_problem_statement(cleaned)
        print("=== extracted problem statement (de-identified) ===")
        print(cleaned)
        print(f"\n  length: {len(cleaned)} chars")

    if args.out:
        args.out.write_text(cleaned)
        print(f"wrote {args.out} ({len(changes)} replacements)")
    else:
        print(cleaned)
    return 0


# Smoke test
if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Run a smoke test
        sample = """
This is the celebrated Navier-Stokes Millennium Problem from arXiv:2602.03837v3.
The Main Theorem (Theorem 1.2 in Smith and Jones 2024 [3]) states that...
We prove that the unsolved conjecture due to Tao et al. holds.
Let u be a smooth solution; consider the energy E(t) = ‖u‖_L².
"""
        cleaned, changes = deidentify_text(sample)
        print("=== smoke test ===")
        print("INPUT:", sample.strip())
        print("\nDEIDENTIFIED:")
        print(cleaned.strip())
        print("\nCHANGES:")
        for c in changes:
            print(c)
        sys.exit(0)
    sys.exit(main())
