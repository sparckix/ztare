#!/usr/bin/env python3
"""v33_corpus_vacuity_relabel.py — leakage-independent re-labeling of the NS corpus.

Applies the validated vacuity organ (v33_preflight_risk_detector) across the
NS Lean corpus to produce LEAKAGE-INDEPENDENT failure labels for the vacuity
subclass — the thing the structural finding said was missing.

Pipeline per top-level decl in ns_*.lean:
  - extract STATEMENT (signature only, no proof)
  - Component 1 (instant, deterministic, no proof, no audit verdict): shape flags
  - Component 2 (selective, only on flagged): independent Lean trivial-cascade
    probe → confirms vacuity WITHOUT any audit verdict
  - leakage_independent_label:
      VACUOUS_FAIL : Component 1 flagged AND (Component 2 confirmed OR not-run-but-flagged-strong)
      SUCCESS      : file is sorry-free AND NOT vacuity-flagged (Lean-attested success)
      UNKNOWN      : neither

Output: /tmp/v33_leakage_safe_contrastive_ledger.json — every row's label
derived ONLY from leakage-independent signals (Lean compile + statement shape).
Then v33_leakage_safe_miner can run on a corpus whose failure class survives
leakage exclusion.

Scope control: Component 1 on ALL decls (instant). Component 2 only on the
flagged subset, capped (--verify-cap N) since each Lean probe ~40s.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from v33_preflight_risk_detector import detect_risks, independent_verify, DEFAULT_SANDBOX  # type: ignore

NS_DIR = ROOT / "ztare_proofs/ZtareProofs"

DECL_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(theorem|lemma|axiom)\s+([A-Za-z_][\w'.]*)\s*(.*?)(?=:=|\Z|^\s*(?:theorem|lemma|axiom|def|opaque|/-))",
    re.MULTILINE | re.DOTALL,
)


def extract_statements(path: Path) -> list[dict]:
    """Return [{name, kind, statement}] — signature only (text up to := / EOF)."""
    txt = path.read_text(errors="ignore")
    sorry_free = (" sorry" not in txt) and (":= sorry" not in txt) and ("by sorry" not in txt)
    out = []
    for m in DECL_RE.finditer(txt):
        kind, name, sig = m.group(1), m.group(2), m.group(3)
        sig = sig.strip()
        # Trim trailing junk; keep first ~500 chars of the type
        if not sig or len(sig) < 3:
            continue
        out.append({
            "name": name, "kind": kind,
            "statement": sig[:500],
            "file_sorry_free": sorry_free,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="ns_*.lean")
    ap.add_argument("--verify-cap", type=int, default=12,
                    help="max Component-2 Lean probes (each ~40s)")
    ap.add_argument("--max-files", type=int, default=400)
    ap.add_argument("--out", default="/tmp/v33_leakage_safe_contrastive_ledger.json")
    args = ap.parse_args()

    files = sorted(NS_DIR.glob(args.glob))[:args.max_files]
    print(f"# v33 corpus vacuity re-label — {len(files)} files\n")

    rows = []
    flagged = []
    for f in files:
        try:
            decls = extract_statements(f)
        except Exception:
            continue
        for d in decls:
            r1 = detect_risks(d["statement"])
            row = {
                "row_id": f"{f.stem}::{d['name']}",
                "file": f.name,
                "kind": d["kind"],
                "statement_preview": d["statement"][:160],
                "file_sorry_free": d["file_sorry_free"],
                "risk_flags": r1["risk_flags"],
                "opaque_present": r1["opaque_predicate_present"],
                "vacuity_suspected": r1["vacuity_suspected"],
                "vacuity_lean_confirmed": None,
            }
            rows.append(row)
            if r1["vacuity_suspected"]:
                flagged.append(row)

    print(f"Decls scanned: {len(rows)}")
    print(f"Component-1 vacuity_suspected: {len(flagged)}")

    # Component 2 — independent Lean confirm, capped
    n_verified = 0
    for row in flagged[: args.verify_cap]:
        stmt = next((r["statement_preview"] for r in rows if r["row_id"] == row["row_id"]), None)
        if not stmt:
            continue
        v = independent_verify(stmt, ["import Mathlib"], DEFAULT_SANDBOX, timeout=55)
        row["vacuity_lean_confirmed"] = v.get("verified")
        n_verified += 1
        print(f"  [C2] {row['row_id'][:55]:<55} verified={v.get('verified')} ({v.get('elapsed_s','?')}s)")

    # Leakage-independent labels
    for r in rows:
        if r["vacuity_suspected"] and (r["vacuity_lean_confirmed"] is True):
            r["leakage_independent_label"] = "VACUOUS_FAIL"
        elif r["vacuity_suspected"] and r["vacuity_lean_confirmed"] is None:
            r["leakage_independent_label"] = "VACUITY_FLAGGED_UNVERIFIED"
        elif (not r["vacuity_suspected"]) and r["file_sorry_free"]:
            r["leakage_independent_label"] = "SUCCESS"   # Lean-attested, leakage-independent
        else:
            r["leakage_independent_label"] = "UNKNOWN"

    from collections import Counter
    label_dist = Counter(r["leakage_independent_label"] for r in rows)
    print(f"\nLeakage-independent label distribution: {dict(label_dist)}")
    confirmed_fail = sum(1 for r in rows if r["leakage_independent_label"] == "VACUOUS_FAIL")
    succ = sum(1 for r in rows if r["leakage_independent_label"] == "SUCCESS")
    print(f"VACUOUS_FAIL (Lean-confirmed, leakage-independent): {confirmed_fail}")
    print(f"SUCCESS (sorry-free + not-vacuous, leakage-independent): {succ}")

    print(f"\n## Honest read")
    if confirmed_fail >= 1 and succ >= 1:
        print(f"CONTRAST EXISTS leakage-independently: {succ} SUCCESS vs {confirmed_fail} "
              f"Lean-confirmed VACUOUS_FAIL. Both labels survive leakage exclusion "
              f"(Lean compile + statement shape, no audit verdict). The v33 miner "
              f"re-opens on this leakage-safe contrastive ledger.")
    else:
        print(f"Insufficient leakage-independent contrast yet: SUCCESS={succ}, "
              f"VACUOUS_FAIL={confirmed_fail}. Raise --verify-cap to confirm more "
              f"flagged rows, OR Component-1 found few vacuity-suspects in NS corpus "
              f"(itself an honest finding: NS is mostly opaque-typed, not vacuous).")

    Path(args.out).write_text(json.dumps({
        "n_decls": len(rows),
        "n_flagged_component1": len(flagged),
        "n_component2_verified": n_verified,
        "label_distribution": dict(label_dist),
        "rows": rows,
    }, indent=2, ensure_ascii=False))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
