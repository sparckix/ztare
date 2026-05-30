"""Print the per-(family, corpus_class) Brier + Elo roll-up.

Reads:
  v_family_brier_by_corpus_class  (Brier mean per family × corpus_class)
  family_elo_by_corpus_class      (Elo per family × corpus_class)
  v_family_brier_by_subsource     (Brier mean per family × corpus_class × sub_source)

CLI:
  ztare forecast brier-elo                       # summary (top-level)
  ztare forecast brier-elo --by-subsource        # include sub-source breakdown
  ztare forecast brier-elo --corpus-class internal
"""
from __future__ import annotations
import argparse
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DB = REPO / "analytics/public/calibration/forecaster_calibration.db"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--by-subsource", action="store_true")
    ap.add_argument("--corpus-class", choices=["internal", "external", "all"], default="all")
    args = ap.parse_args()
    con = sqlite3.connect(str(DB))
    where = ""
    if args.corpus_class != "all":
        where = f" WHERE corpus_class = '{args.corpus_class}'"
    print("=== Brier + Elo per (family, corpus_class) — apples-to-apples panel ===")
    print(f"{'family':<14} {'corpus_class':<12} {'n_calls':>8} {'mean_brier':>12} {'elo':>8} {'n_games':>10}")
    rows = list(con.execute(f"""
        SELECT b.family, b.corpus_class, b.n_calls, b.mean_brier,
               COALESCE(e.elo, NULL) AS elo, COALESCE(e.n_games, 0) AS n_games
        FROM v_family_brier_by_corpus_class b
        LEFT JOIN family_elo_by_corpus_class e
          ON e.family = b.family AND e.corpus_class = b.corpus_class
        {where}
        ORDER BY b.corpus_class, b.mean_brier
    """))
    cur_class = None
    for fam, cclass, n, brier, elo, ng in rows:
        if cclass != cur_class and cur_class is not None: print()
        cur_class = cclass
        elo_s = f"{elo:>8.1f}" if elo is not None else "       -"
        print(f"{fam:<14} {cclass:<12} {n:>8} {brier:>12.4f} {elo_s} {ng:>10}")
    if args.by_subsource:
        print()
        print("=== Brier per (family, corpus_class, sub_source) — drill-down ===")
        print(f"{'family':<14} {'corpus_class':<10} {'sub_source':<26} {'corpus':<32} {'n':>6} {'brier':>10}")
        for fam, cclass, sub, corp, n, brier in con.execute(f"""
            SELECT family, corpus_class, COALESCE(sub_source, '(null)'),
                   COALESCE(source_corpus, '(null)'), n_calls, mean_brier
            FROM v_family_brier_by_subsource
            {where}
            ORDER BY corpus_class, sub_source, family
        """):
            print(f"{fam:<14} {cclass:<10} {sub:<26} {corp:<32} {n:>6} {brier:>10.4f}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
