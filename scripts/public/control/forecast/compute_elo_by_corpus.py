"""Compute per-(family, corpus_class) Elo from head-to-head per-contract Brier.

Populates `family_elo_by_corpus_class` in forecaster_calibration.db.
Same shape as ensemble_elo_brier_probe.py but operates over ALL pilot_calls,
sliced by v_corpus_class (internal vs external).

Elo: K=16, init=1500. For each contract where >=2 families fired, run pairwise
matches: family with lower Brier wins, equal Brier = draw. Update Elos
iteratively. Per (family, corpus_class) Elo at end of pass.

CLI:
  python3 scripts/public/control/forecast/compute_elo_by_corpus.py --refresh
"""
from __future__ import annotations
import argparse
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
K = 16
INIT = 1500.0


def compute(con: sqlite3.Connection) -> dict:
    rows = list(con.execute("""
        SELECT pc.contract_id, pc.family, pc.brier, cc.corpus_class
        FROM pilot_calls pc
        JOIN v_corpus_class cc ON cc.contract_id = pc.contract_id
        WHERE pc.brier IS NOT NULL AND pc.family IS NOT NULL
    """))
    # Take the BEST (lowest) Brier per (family, contract_id, corpus_class) since
    # a single family may fire the same contract multiple times across pilots.
    best_brier = {}
    for cid, fam, b, cclass in rows:
        key = (cclass, cid, fam)
        if key not in best_brier or b < best_brier[key]:
            best_brier[key] = b
    # Bucket by (corpus_class, contract_id) -> {family: brier}
    by_contract = defaultdict(dict)
    for (cclass, cid, fam), b in best_brier.items():
        by_contract[(cclass, cid)][fam] = b
    # Per corpus_class, run Elo
    out = {}
    for cclass in {k[0] for k in by_contract.keys()}:
        elo = defaultdict(lambda: INIT)
        n_games = defaultdict(int)
        for (cc, cid), fams_brier in sorted(by_contract.items()):
            if cc != cclass: continue
            families = list(fams_brier.keys())
            if len(families) < 2: continue
            for i, f1 in enumerate(families):
                for f2 in families[i+1:]:
                    b1, b2 = fams_brier[f1], fams_brier[f2]
                    if b1 < b2:    s1, s2 = 1.0, 0.0
                    elif b2 < b1:  s1, s2 = 0.0, 1.0
                    else:          s1 = s2 = 0.5
                    exp1 = 1 / (1 + 10 ** ((elo[f2] - elo[f1]) / 400))
                    elo[f1] += K * (s1 - exp1)
                    elo[f2] += K * (s2 - (1 - exp1))
                    n_games[f1] += 1
                    n_games[f2] += 1
        out[cclass] = {fam: (e, n_games[fam]) for fam, e in elo.items()}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="Clear existing rows and recompute from scratch.")
    args = ap.parse_args()
    con = sqlite3.connect(str(DB))
    if args.refresh:
        con.execute("DELETE FROM family_elo_by_corpus_class")
    now = datetime.now(timezone.utc).isoformat()
    out = compute(con)
    for cclass, fams in sorted(out.items()):
        for fam, (e, n) in sorted(fams.items(), key=lambda x: -x[1][0]):
            con.execute(
                "INSERT OR REPLACE INTO family_elo_by_corpus_class (family, corpus_class, elo, n_games, computed_at) VALUES (?,?,?,?,?)",
                (fam, cclass, e, n, now),
            )
    con.commit()
    # Print
    print(f"{'corpus_class':<12} {'family':<22} {'elo':>8} {'n_games':>10}")
    for cclass, fams in sorted(out.items()):
        for fam, (e, n) in sorted(fams.items(), key=lambda x: -x[1][0]):
            print(f"{cclass:<12} {fam:<22} {e:>8.1f} {n:>10}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
