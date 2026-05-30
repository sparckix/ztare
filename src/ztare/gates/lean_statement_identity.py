"""GP-241 forward-spec Contract C3 — Lean-kernel statement identity.

Promotes SM3's HARD path from a regex text-hash (which cold findings
4/5 proved has a next adversarial input by construction) to Lean
*definitional-equality* of the proved theorem's statement against the
operator-registered target's statement.

DESIGN CONSTRAINTS (operator, 2026-05-18):
  - Does NOT modify `src/ztare/formal/lean_repl.py`, `vendor/lean_repl`,
    or the toolchain — another agent owns/tests that surface. This
    module only *consumes* `lean_repl.check_lean` read-only (it is
    concurrency-safe: unique tempfile per call).
  - Returns a 3-valued verdict matching the precommitted C3 contract:
      "PASS"    proven statement is defeq to the registered target,
      "FAIL"    they elaborate but are NOT defeq (real divergence),
      "BLOCKED" the toolchain could not run (timeout / lean missing /
                env mismatch) — the caller MUST keep SM3 advisory and
                route to the human residual, NEVER silently PASS.

The defeq probe: two Props A, B are definitionally equal iff a term
of A typechecks at expected type B (Lean accepts `(x : A) : B := x`
iff A and B are defeq). We test BOTH directions so the relation is
symmetric and a one-way coercion (e.g. via instance/coe) cannot
launder a non-identity as identity. Imports + toolchain are hashed
into `env_hash`; the registered target's env_hash must match (caller
enforces) so notation/instance drift is caught, not laundered.

MUST NOT claim: defeq identity of the proved statement to the
registered one is NOT evidence the registered statement captures the
informal problem — that is P16, fenced, human-only.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

_DEFAULT_IMPORTS = ("import Mathlib",)


def env_hash(imports: tuple[str, ...] | list[str],
             project_dir: str | Path | None) -> str:
    """Deterministic hash of the elaboration environment: the import
    set + the pinned lean-toolchain string of the project. Bound at
    target registration; a close whose env_hash differs is a FAIL
    (instance/notation drift), not a silent PASS."""
    toolchain = ""
    try:
        proj = (Path(project_dir) if project_dir
                else Path(__file__).resolve().parents[3] / "ztare_proofs")
        tc = proj / "lean-toolchain"
        if tc.is_file():
            toolchain = tc.read_text(encoding="utf-8").strip()
    except Exception:
        toolchain = ""
    payload = "|".join(sorted(set(imports))) + "||" + toolchain
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _probe(code: str, project_dir: str | Path | None,
           timeout: int) -> dict[str, Any]:
    # Read-only consumption of the existing wrapper; never modified.
    from src.ztare.formal.lean_repl import check_lean
    return check_lean(code, timeout=timeout, project_dir=project_dir)


def _tooling_failed(r: dict[str, Any]) -> bool:
    # returncode -1 / raw TIMEOUT / lean|lake not found ⇒ BLOCKED,
    # NOT a semantic FAIL. Fail-closed only in the sense that the
    # caller must not treat BLOCKED as PASS.
    if r.get("returncode") == -1:
        return True
    raw = str(r.get("raw", "")).lower()
    return ("timeout" in raw
            or "command not found" in raw
            or "no such file or directory" in raw
            or "lake: not found" in raw)


def statements_defeq(
    registered_stmt: str,
    proven_stmt: str,
    *,
    imports: tuple[str, ...] | list[str] = _DEFAULT_IMPORTS,
    project_dir: str | Path | None = None,
    timeout: int = 90,
) -> tuple[str, str]:
    """Return (verdict, detail) where verdict ∈ {PASS, FAIL, BLOCKED}.

    Bidirectional defeq: both `(x : A) : B := x` and `(x : B) : A := x`
    must elaborate. Any tooling failure on EITHER direction ⇒ BLOCKED
    (caller keeps SM3 advisory). Both elaborate ⇒ PASS. Elaborates but
    rejects ⇒ FAIL (genuinely not the same statement)."""
    A = registered_stmt.strip()
    B = proven_stmt.strip()
    if not A or not B:
        return "BLOCKED", "empty registered or proven statement text"
    imp = "\n".join(imports)
    fwd = (f"{imp}\n"
           f"private theorem _c3_fwd (x : ({A})) : ({B}) := x\n")
    rev = (f"{imp}\n"
           f"private theorem _c3_rev (x : ({B})) : ({A}) := x\n")
    r1 = _probe(fwd, project_dir, timeout)
    if _tooling_failed(r1):
        return "BLOCKED", f"toolchain failure (fwd): {r1.get('raw','')[:200]}"
    r2 = _probe(rev, project_dir, timeout)
    if _tooling_failed(r2):
        return "BLOCKED", f"toolchain failure (rev): {r2.get('raw','')[:200]}"
    if r1.get("success") and r2.get("success"):
        return "PASS", "bidirectional defeq holds (Lean kernel)"
    return "FAIL", (
        "proven statement is NOT defeq to the registered target "
        f"(fwd_ok={bool(r1.get('success'))} "
        f"rev_ok={bool(r2.get('success'))}); "
        f"fwd_err={(r1.get('errors') or [''])[0][:160]}")
