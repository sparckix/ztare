"""Poll Metaculus for resolution of OPEN forecastbench_metaculus_* contracts.

Task #40 diagnosis (2026-05-29): the 72 forecastbench_metaculus_* contracts in
the DB with y_known=NULL are NOT a wrong-endpoint bug. They are genuinely-open
future-resolving questions; the single-question API2 endpoint returns
`question.resolution = None` because the question has not resolved yet. There is
no resolution value to fetch until Metaculus resolves them.

This script is the periodic re-resolution poller: run it on a cron cadence; each
run lands y_known for any contract whose Metaculus question has since resolved
yes/no. Until then the contracts correctly stay y_known=NULL and are excluded
from Brier/Elo (which only score resolved contracts).

Rate-limit aware: Metaculus 429s aggressively on bursts; this throttles to ~1
req/1.5s and retries with backoff.

CLI:
  ztare forecast resolve-open-metaculus --dry-run
  ztare forecast resolve-open-metaculus --commit
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
API = "https://www.metaculus.com/api2/questions/"


def _get(qid: str, headers: dict, *, retries: int = 3) -> dict | None:
    url = f"{API}{qid}/"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt * 2)
                continue
            return None
        except Exception:
            return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--throttle-s", type=float, default=1.5)
    args = ap.parse_args()
    if not (args.dry_run or args.commit):
        print("specify --dry-run or --commit", file=sys.stderr)
        return 2
    tok = os.environ.get("METACULUS_API_KEY")
    if not tok:
        print("METACULUS_API_KEY not set (source .env)", file=sys.stderr)
        return 2
    headers = {"User-Agent": "ztare-forecast-calibration/1.0",
               "Authorization": f"Token {tok}"}
    con = sqlite3.connect(str(DB))
    rows = list(con.execute(
        "SELECT contract_id FROM contracts WHERE source='metaculus' AND y_known IS NULL"
    ))
    print(f"open metaculus contracts to poll: {len(rows)}")
    resolved, still_open, errors = [], 0, 0
    for (cid,) in rows:
        m = re.search(r"metaculus_(\d+)", cid)
        if not m:
            continue
        q = _get(m.group(1), headers)
        if q is None:
            errors += 1
            time.sleep(args.throttle_s)
            continue
        res = ((q.get("question") or {}).get("resolution"))
        if res in ("yes", "no"):
            resolved.append((cid, 1 if res == "yes" else 0, res))
        else:
            still_open += 1
        time.sleep(args.throttle_s)
    print(f"newly-resolved: {len(resolved)}, still-open: {still_open}, errors: {errors}")
    for cid, y, res in resolved:
        print(f"  {cid}: {res} (y={y})")
        if args.commit:
            con.execute("UPDATE contracts SET y_known=? WHERE contract_id=?", (y, cid))
    if args.commit and resolved:
        con.commit()
        print(f"committed {len(resolved)} resolutions")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
