#!/usr/bin/env python3
"""build_proof_health.py — GP-237 §0d-KILL/§0d-KILL-b survivors ONLY.

This is NOT a sophistication score (v1/v3/v4 killed — see GP-237 §00..
§0d-KILL-b). It ships the two things that survived adversary + Meta-Darwin:

  (1) LAUNDERING TRIPWIRE (binary, per reflexive-mine cycle): did this
      cycle's ztare_proofs/ obligations introduce laundering — sorry/
      admit/axiom, trivial-closer-only, or alpha-renamed duplicate
      (proof-fingerprint dedup)? Adversary-endorsed.
  (2) REGRESSION/REWORK RATE (non-accumulation, two-sided, bad=UP):
      fraction of previously-clean obligations that reverted to
      sorry/admit/axiom or vanished since the last cycle. Meta-Darwin-
      established as a self-measure that CAN return "treadmilling".

DETERMINISTIC, zero-token, no Lean re-run (STRUCTURAL proxy — honest
limit stated in output: a green decl silently broken by an UPSTREAM
change with no local sorry is NOT caught). Honest-null if ztare_proofs
absent. Pre-registered falsifier wired as a dogfood assert (F1): a
synthetic vacuous/sorry/trivial/dup calibration set MUST be flagged, or
the run is REJECTED. Out: analytics/public/ledgers/reflexive/proof_health.json
Snapshot: analytics/public/ledgers/reflexive/proof_fingerprints_prev.json
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
PROOFS = REPO / "ztare_proofs" / "ZtareProofs"
OUT = REPO / "analytics/public/ledgers/reflexive/proof_health.json"
PREV = REPO / "analytics/public/ledgers/reflexive/proof_fingerprints_prev.json"

DECL_RE = re.compile(r"^\s*(theorem|lemma)\s+([A-Za-z0-9_'.]+)", re.M)
LAUNDER_TOK = re.compile(r"\b(sorry|admit)\b|^\s*axiom\s", re.M)
# trivial-closer-only: proof body is solely one blacklisted finishing
# tactic. Expanded per the v4 adversary (grind/linarith/... were holes).
TRIVIAL_CLOSERS = ("rfl", "trivial", "simp", "decide", "omega", "aesop",
                   "grind", "linarith", "nlinarith", "norm_num", "ring",
                   "tauto", "bound", "positivity", "field_simp")


def _decls(text: str) -> list[tuple[str, str]]:
    """(name, body-until-next-decl) pairs."""
    out, pos = [], [(m.start(), m.group(2)) for m in DECL_RE.finditer(text)]
    for i, (s, name) in enumerate(pos):
        e = pos[i + 1][0] if i + 1 < len(pos) else len(text)
        out.append((name, text[s:e]))
    return out


def _norm_fp(body: str) -> str:
    """Alpha-rename-insensitive structural fingerprint: strip the decl
    name + identifiers' case + whitespace, hash the token shape."""
    b = re.sub(r"\b[a-z][A-Za-z0-9_']*\b", "x", body)
    b = re.sub(r"\s+", "", b)
    return hashlib.sha1(b.encode()).hexdigest()[:16]


def _laundered(name: str, body: str) -> str | None:
    if LAUNDER_TOK.search(body):
        return "sorry/admit/axiom"
    # proof-body after ':=' / 'by'
    m = re.search(r":=\s*by\b(.*)", body, re.S)
    proof = (m.group(1) if m else "").strip()
    toks = [t for t in re.findall(r"[A-Za-z_]+", proof)]
    if proof and toks and all(
            t in TRIVIAL_CLOSERS or t in ("by",) for t in toks[:3]) \
            and len(set(toks) - {"by"}) <= 1:
        return "trivial-closer-only"
    return None


def scan() -> dict[str, dict]:
    decls: dict[str, dict] = {}
    fps: dict[str, list[str]] = {}
    for f in sorted(PROOFS.rglob("*.lean")):
        if ".lake" in f.parts:
            continue
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for name, body in _decls(t):
            fp = _norm_fp(body)
            decls[name] = {"laundered": _laundered(name, body), "fp": fp}
            fps.setdefault(fp, []).append(name)
    return decls, fps


def dogfood_falsifier() -> None:
    """F1 pre-registered: the gate MUST flag a synthetic vacuous/sorry/
    trivial/dup set, else the gate is broken and the run is REJECTED."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "Calib.lean"
        p.write_text(
            "theorem c_sorry : True := by sorry\n"
            "theorem c_trivial : 1 = 1 := by rfl\n"
            "theorem c_grind : 2 = 2 := by grind\n"
            "theorem c_dupA (n:Nat) : n+0=n := by simp\n"
            "theorem c_dupB (m:Nat) : m+0=m := by simp\n")
        t = p.read_text()
        ds = _decls(t)
        flagged = sum(1 for nm, b in ds if _laundered(nm, b))
        fps = {}
        for nm, b in ds:
            fps.setdefault(_norm_fp(b), []).append(nm)
        dups = sum(1 for v in fps.values() if len(v) > 1)
        # MUST catch: sorry, trivial rfl, grind-only, and the alpha-dup pair
        if flagged < 3 or dups < 1:
            print(f"FATAL F1: laundering gate failed its own calibration "
                  f"(flagged={flagged}/expected>=3, dup-groups={dups}/>=1). "
                  f"Gate broken — run REJECTED, no proof_health emitted.")
            sys.exit(3)


def main() -> int:
    if not PROOFS.exists():
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "status": "not_computable",
            "reason": "ztare_proofs/ZtareProofs absent this cycle — "
                      "honest null, never a guessed number."}, indent=2))
        print("not_computable: ztare_proofs absent (honest null)")
        return 0

    dogfood_falsifier()                       # F1 must pass or exit 3
    decls, fps = scan()
    clean = {n for n, d in decls.items() if not d["laundered"]}
    laundered_now = {n: d["laundered"] for n, d in decls.items() if d["laundered"]}
    dup_groups = {fp: ns for fp, ns in fps.items() if len(ns) > 1}

    prev = None
    if PREV.exists():
        try:
            prev = json.loads(PREV.read_text())
        except Exception:
            prev = None

    if prev and prev.get("clean"):
        prev_clean = set(prev["clean"])
        regressed = sorted(
            n for n in prev_clean
            if n not in decls or decls[n]["laundered"])
        rate = round(len(regressed) / max(1, len(prev_clean)), 4)
        reg = {"prev_clean": len(prev_clean), "regressed": len(regressed),
               "rate": rate, "examples": regressed[:10],
               "verdict": ("regression" if rate > 0 else "no-regression")}
    else:
        reg = {"status": "baseline", "note": "first cycle — no prior "
               "snapshot; regression rate computes from next cycle on. "
               "NOT an ascent number (this metric is two-sided, bad=UP)."}

    tripwire = {
        "laundering_introduced": bool(laundered_now) or bool(dup_groups),
        "n_laundered_decls": len(laundered_now),
        "by_kind": {k: sum(1 for v in laundered_now.values() if v == k)
                    for k in set(laundered_now.values())},
        "n_duplicate_fp_groups": len(dup_groups),
        "examples": dict(list(laundered_now.items())[:10]),
    }
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "spec": "research_areas/private/seams/apparatus/instrumentation/GP-237_scope_evolution_seam.md §0d-KILL-b",
        "status": "ok",
        "frame": "NOT a sophistication score (v1/v3/v4 killed). (1) binary "
                 "laundering tripwire; (2) non-accumulation regression/"
                 "rework rate (two-sided, bad=UP, CAN say 'treadmilling').",
        "honest_limit": "STRUCTURAL proxy, no Lean re-run: a green decl "
                        "silently broken by an UPSTREAM change with no "
                        "local sorry is NOT caught. Decl-name regex; "
                        "conceptual triviality not detected (adversary's "
                        "known limit, stated not hidden).",
        "n_decls_scanned": len(decls),
        "n_clean": len(clean),
        "laundering_tripwire": tripwire,
        "regression_rework": reg,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    PREV.write_text(json.dumps({
        "snapshot_utc": payload["generated_utc"],
        "clean": sorted(clean)}, indent=2))
    print(f"proof_health: decls={len(decls)} clean={len(clean)} "
          f"laundering_introduced={tripwire['laundering_introduced']} "
          f"(launder={len(laundered_now)} dupgroups={len(dup_groups)}) "
          f"regression={reg.get('rate', reg.get('status'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
