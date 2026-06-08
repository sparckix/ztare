#!/usr/bin/env python3
"""Orchestration-alpha analyzer — does the GOVERNED multi-provider ensemble close
rows that NO single provider closes? (The operator's "orchestration is the alpha"
thesis, measured.)

Reads a solver_lane_attempts DB (provider, outcome, compile_ok, row_id) — which the
cascade/dag_search runs already populate per-provider — and computes:
  - per-provider closure set (distinct rows with compile_ok=1)
  - the ENSEMBLE union (any provider closes it)
  - best-single-provider baseline
  - ALPHA = rows the ensemble closes that the BEST single provider does NOT
  - per-provider UNIQUE contribution (rows only that provider closes)

Alpha > 0 means orchestration adds value over the best single prover. On an easy
(Munger-empty) corpus alpha ≈ 0 (everyone closes everything); the alpha only shows
on a hard corpus where single providers FAIL — which is exactly why it must be run
on the hard-but-provable corpus, not the spectral slice.

Usage: orchestration_alpha.py <attempts.db>
"""
import sys, sqlite3, json
from pathlib import Path

# Reuse the extracted Jaccard primitive (NOT a reimplementation) for provider
# complementarity: do providers close/reach the SAME rows (redundant ensemble) or
# DIFFERENT rows (latent orchestration value)?
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
try:
    from ztare.motion.set_distance import jaccard_distance
except Exception:  # pragma: no cover
    def jaccard_distance(a, b):
        u = len(a | b)
        return 1.0 - (len(a & b) / u) if u else 0.0


def _pairwise_jaccard(setmap: dict) -> list:
    """Pairwise Jaccard SIMILARITY between providers' row-sets. Low similarity =
    complementary (orchestration has value); high = redundant. Empty pairs skipped."""
    provs = sorted(p for p, s in setmap.items() if s)
    out = []
    for i in range(len(provs)):
        for j in range(i + 1, len(provs)):
            a, b = setmap[provs[i]], setmap[provs[j]]
            out.append({"pair": [provs[i], provs[j]],
                        "jaccard_similarity": round(1.0 - jaccard_distance(a, b), 3),
                        "shared": len(a & b), "union": len(a | b)})
    return out


def analyze(db):
    con = sqlite3.connect(db)
    rows = con.execute(
        "SELECT provider, row_id, MAX(compile_ok) FROM attempts GROUP BY provider, row_id"
    ).fetchall()
    closed = {}          # provider -> set(row_id) closed
    attempted = {}       # provider -> set(row_id) attempted
    for prov, rid, ok in rows:
        attempted.setdefault(prov, set()).add(rid)
        if ok == 1:
            closed.setdefault(prov, set()).add(rid)
    # Partial-progress sets (rows each provider got CLOSEST on) — informative even
    # at 0 closures, IF the DB carries a progress column (orchestration_matrix does).
    progressed = {}
    has_progress = any(r[1] == "progress" for r in con.execute("PRAGMA table_info(attempts)").fetchall())
    if has_progress:
        for prov, rid in con.execute(
                "SELECT provider, row_id FROM attempts WHERE progress >= 0.5"):
            progressed.setdefault(prov, set()).add(rid)
    all_rows = {r for s in attempted.values() for r in s}
    ensemble = {r for s in closed.values() for r in s}
    providers = sorted(attempted)
    best_prov = max(closed, key=lambda p: len(closed.get(p, set())), default=None)
    best_set = closed.get(best_prov, set()) if best_prov else set()
    alpha_rows = ensemble - best_set                      # ensemble gets, best-single misses
    out = {
        "db": db,
        "rows_total": len(all_rows),
        "ensemble_closed": len(ensemble),
        "best_single_provider": best_prov,
        "best_single_closed": len(best_set),
        "orchestration_alpha": len(alpha_rows),           # the headline number
        "alpha_rows": sorted(alpha_rows),
        "per_provider": {
            p: {
                "attempted": len(attempted.get(p, set())),
                "closed": len(closed.get(p, set())),
                "unique": len(closed.get(p, set()) - {r for q in closed if q != p for r in closed[q]}),
            } for p in providers
        },
        # Provider complementarity (Jaccard). On closures when present; else on the
        # partial-progress sets (which rows each provider reached 1-goal-on) so the
        # diversity signal is observable even at 0 closures.
        "closure_jaccard": _pairwise_jaccard(closed),
        "partial_progress_jaccard": _pairwise_jaccard(progressed) if progressed else [],
    }
    print(json.dumps(out, indent=2))
    if not out["closure_jaccard"] and out["partial_progress_jaccard"]:
        lows = [j for j in out["partial_progress_jaccard"] if j["jaccard_similarity"] < 0.5]
        print(f"\nPROVIDER COMPLEMENTARITY (0 closures → on partial progress): "
              f"{len(lows)}/{len(out['partial_progress_jaccard'])} provider-pairs reach 1-goal on "
              f"LARGELY DIFFERENT rows (Jaccard<0.5) → latent orchestration value; "
              f"high overlap → providers are redundant even in how they fall short.")
    print(f"\nORCHESTRATION ALPHA = {out['orchestration_alpha']} "
          f"(rows the ensemble closes that the best single provider '{best_prov}' does NOT).")
    if out["orchestration_alpha"] == 0:
        print("Alpha = 0 here → orchestration adds nothing over the best single provider on THIS corpus. "
              "Expected on an easy/Munger-empty slice; the test that matters is on the hard-but-provable corpus.")
    else:
        print("Alpha > 0 → multi-provider routing genuinely closes rows no single prover does. "
              "This is the orchestration value (subject to each closure being cert-ratified).")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: orchestration_alpha.py <attempts.db>"); sys.exit(1)
    analyze(sys.argv[1])
