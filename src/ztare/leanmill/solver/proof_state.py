"""Proof-state signal — the missing partial-progress gradient (GP-187 middle layer).

The solver lane historically recorded only a BINARY `compile_ok` per attempt.
A binary outcome gives a best-first / DAG search nothing to climb: every
non-closure looks identical, so the DAG degenerates to the fixed cascade (this
is the measured reason orchestration_alpha was 0 on real attempts — no gradient
to exploit, only a cost edge).

This module extracts a cheap PARTIAL-PROGRESS signal from the Lean compiler
output that `_verify_compile` already captures, at zero extra compile cost:

  - error_class:     what KIND of failure (clean / unsolved_goals / tactic_failed /
                     unknown_identifier / type_mismatch / timeout / other_error)
  - goals_remaining: how many goals are still open (0 on a clean close; the count
                     of `⊢` turnstiles inside the unsolved-goals block otherwise)
  - progress:        a coarse 0..1 score (1.0 closed; partial credit when the proof
                     advanced but left goals; low for hard syntactic/name errors)

`goals_remaining` going 7 → 3 → 1 across attempts is the gradient a DAG can
order candidates by; `error_class` lets the router pick the next move (a
`tactic_failed` says "try a different closer", an `unknown_identifier` says
"the premise shelf is missing a name", a `type_mismatch` says "the statement
encoding is off"). The parser is Lean-free and unit-tested on captured output;
the wiring records it per attempt so the DAG finally has something to search.
"""
from __future__ import annotations
import re

# Lean prints `unsolved goals` then one or more goal displays, each ending in a
# `⊢ <type>` turnstile line. The turnstile count inside that block = open goals.
_TURNSTILE = "⊢"
_UNSOLVED_RE = re.compile(r"unsolved goals", re.IGNORECASE)
_NUM_GOALS_RE = re.compile(r"\b(\d+)\s+goals?\b")  # Lean sometimes prefixes "N goals"

# Benign substrate noise that otherwise pollutes error-class extraction: a dev `.lake` package with
# uncommitted edits prints `warning: <pkg>: repository '…' has local changes` on EVERY compile. It is
# never an error; left in, it buries the real Lean error line so a genuine failure mis-buckets to
# other_error (then mis-tags as `apparatus`). Strip it before classifying (warnings ≠ errors).
_BENIGN_WARN_RE = re.compile(r"(?m)^.*\bhas local changes\b.*$\n?")

# Failure-class signatures, checked in priority order (most specific first).
_CLASS_SIGNATURES = (
    ("timeout", re.compile(r"timed out|timeout|deterministic timeout", re.IGNORECASE)),
    # parse_error: the leaf produced SYNTACTICALLY INVALID Lean (it could not even write a parseable
    # proof). This is a leaf-capability miss — NOT a toolchain artifact (apparatus) and NOT a confirmed
    # math dead-end (math); failure_class routes it to `unknown` (re-prompt), never laundering it either way.
    ("parse_error",
     re.compile(r"unexpected (?:identifier|token|end of input)|"
                r"expected (?:command|term|declaration|'[^']*')|unterminated", re.IGNORECASE)),
    ("unknown_identifier",
     re.compile(r"unknown (identifier|constant|namespace)|unknown ", re.IGNORECASE)),
    ("type_mismatch",
     re.compile(r"type mismatch|has type|application type mismatch|expected type",
                re.IGNORECASE)),
    ("unsolved_goals", _UNSOLVED_RE),
    ("tactic_failed",
     re.compile(r"tactic '?\w+'? failed|failed to|made no progress|no goals|"
                r"linarith failed|nlinarith failed|ring failed|simp made no progress|"
                r"aesop|omega could not", re.IGNORECASE)),
)


def _count_unsolved_goals(output: str) -> int:
    """Count open goals inside the FIRST `unsolved goals` block.

    Scoped to the text after the first 'unsolved goals' marker so a turnstile
    the provider may have echoed elsewhere is not counted. Falls back to an
    explicit 'N goals' header if Lean printed one.
    """
    m = _UNSOLVED_RE.search(output)
    if not m:
        return 0
    region = output[m.start():]
    # Cut the region at the next distinct error line so we count only THIS block.
    nxt = re.search(r"\n\S*\.lean:\d+:\d+: (error|warning):", region[1:])
    if nxt:
        region = region[: nxt.start() + 1]
    header = _NUM_GOALS_RE.search(region)
    if header:
        return int(header.group(1))
    n = region.count(_TURNSTILE)
    return max(1, n)  # an unsolved-goals block always means at least one open goal


def extract_unsolved_goals(output: str) -> list[str]:
    """Return the open-goal block(s) from Lean's `unsolved goals` output — the
    hypotheses + `⊢ <goal>` display the kernel left open. This is the residual a
    STEPWISE continuation attacks: a whole-proof attempt that type-checks down to
    one goal can be continued by handing this exact proof state back to a prover,
    instead of buying a stronger one-shot prover. Pure parse, no toolchain.

    Returns one string per `unsolved goals` block (each block may itself contain
    several `case`/`⊢` goals); [] if the output has no unsolved-goals block.
    """
    out = output or ""
    blocks: list[str] = []
    for m in _UNSOLVED_RE.finditer(out):
        region = out[m.end():]
        # Block runs until the next distinct lean error/warning line, or end.
        nxt = re.search(r"\n\S*\.lean:\d+:\d+: (error|warning):", region)
        block = region[: nxt.start()] if nxt else region
        block = block.strip("\n")
        if block.strip():
            blocks.append(block)
    return blocks


def proof_state_signal(returncode: "int | None", output: str) -> dict:
    """Extract (error_class, goals_remaining, progress) from a compile result.

    Pure function over the compiler output `_verify_compile` already returns,
    so it adds zero compile cost. Returns a dict safe to persist per attempt.
    """
    out = _BENIGN_WARN_RE.sub("", output or "")  # drop dev-substrate "local changes" warning noise first
    # Clean close: exit 0, no error line, no sorry. Mirror lean_compile_primitives'
    # oracle loosely here (the caller still owns the authoritative compile_ok).
    has_error = bool(re.search(r"(?m)^\s*\S*\.lean:\d+:\d+: error:|^\s*error:", out))
    has_sorry = "sorry" in out or "declaration uses" in out
    if returncode == 0 and not has_error and not has_sorry:
        return {"error_class": "clean", "goals_remaining": 0, "progress": 1.0}

    error_class = "other_error"
    for name, rx in _CLASS_SIGNATURES:
        if rx.search(out):
            error_class = name
            break

    goals = _count_unsolved_goals(out)

    # Coarse progress score: unsolved_goals means the proof TYPE-CHECKED up to the
    # remaining goals (real partial progress) → score decays with goal count;
    # tactic_failed means a closer was attempted on a well-formed goal (some
    # progress); syntactic/name/type errors mean the candidate barely parsed.
    if error_class == "unsolved_goals":
        progress = round(1.0 / (1.0 + goals), 3)        # 1 goal→0.5, 3→0.25, …
    elif error_class == "tactic_failed":
        progress = 0.2
    elif error_class in ("unknown_identifier", "type_mismatch"):
        progress = 0.05
    elif error_class == "parse_error":
        progress = 0.02        # malformed Lean — barely parsed; the leaf could not write a valid proof
    elif error_class == "timeout":
        progress = 0.1
    else:
        progress = 0.0
    return {"error_class": error_class, "goals_remaining": goals, "progress": progress}
