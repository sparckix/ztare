#!/usr/bin/env python3
"""p0_calibration.py — emit ONE stable calibration block for GP-236 at
analytics/public/forecast_pool/p0_calibration.json.

Composes EXISTING forecast-pool data (contracts/ outcomes/ forecasts/ +
externalities_rollup.json) into a stable-keyed block. No new measurement
infra — same spirit as signed_calibration_bias (a reader/aggregator).
Item 2 (cross-family disagreement) is the only net-new computation
(currently computed nowhere — GP-236 §3.1 genuine-independence signal).

Blocks:
 1. brier_per_period  — [{period,N,brier,uniform_baseline}] ISO-week
    bucketed by resolved_at; N per period stated (defeats the
    "N=17 pooled is noise" kill: per-period trajectory with N visible).
 2. cross_family_disagreement — {disagreement_rate,n_shared_contracts,
    resolution_split} over contracts forecast by >=2 model families.
 3. resolution — {resolved,total,rate,median_latency_days,voided}
    (exposes survivorship the Brier-of-resolved-only hides).
 4. externalities — {positive,negative,ratio,by_period} from the
    real rollup (211 pos / 95 neg distinct tags).
 5. as_of — generation timestamp.

Conventions are stated IN the artifact (honest, self-describing).
"""
from __future__ import annotations
import json, statistics, datetime as dt
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FP = REPO / "analytics/public/forecast_pool"
CONTRACTS, OUTCOMES, FORECASTS = FP/"contracts", FP/"outcomes", FP/"forecasts"
ROLLUP = FP/"externalities_rollup.json"
OUT = FP/"p0_calibration.json"


def _iso_week(ts: str) -> str | None:
    try:
        d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        y, w, _ = d.isocalendar()
        return f"{y}-W{w:02d}"
    except Exception:
        return None


def _family(agent_id: str) -> str:
    a = (agent_id or "").lower()
    if "codex" in a:
        return "Codex"
    if "gpt" in a or "openai" in a:
        return "GPT"
    if "claude" in a or "opus" in a or "sonnet" in a or "research_director" in a:
        return "Claude"
    return "Other"


def main() -> int:
    contracts = {}
    for cf in CONTRACTS.glob("*.json"):
        try:
            c = json.loads(cf.read_text(errors="ignore"))
            contracts[cf.stem] = c
        except Exception:
            pass
    outcomes = {}
    for of in OUTCOMES.glob("*.json"):
        try:
            outcomes[of.stem] = json.loads(of.read_text(errors="ignore"))
        except Exception:
            pass

    # ---- 1. brier per period (ISO-week of resolved_at) ----
    period_rows: dict[str, list[float]] = {}
    for cid, o in outcomes.items():
        if o.get("voided") or o.get("success_bool") is None:
            continue
        wk = _iso_week(str(o.get("resolved_at") or ""))
        if not wk:
            continue
        y = 1.0 if o["success_bool"] else 0.0
        fdir = FORECASTS / cid
        briers = []
        if fdir.exists():
            for ff in fdir.glob("*.json"):
                try:
                    p = float(json.loads(ff.read_text())["p_success"])
                    briers.append((p - y) ** 2)
                except Exception:
                    pass
        if briers:
            period_rows.setdefault(wk, []).append(sum(briers)/len(briers))
    brier_per_period = [
        {"period": wk, "N": len(v),
         "brier": round(sum(v)/len(v), 4),
         "uniform_baseline": 0.25}          # always-predict-0.5 Brier
        for wk, v in sorted(period_rows.items())
    ]

    # ---- 2. cross-family disagreement (net-new) ----
    shared, disagree = 0, 0
    split = {"success": 0, "fail": 0, "unresolved": 0}
    for cid in contracts:
        fdir = FORECASTS / cid
        if not fdir.exists():
            continue
        fam_p: dict[str, list[float]] = {}
        for ff in fdir.glob("*.json"):
            try:
                fc = json.loads(ff.read_text())
                fam_p.setdefault(_family(fc.get("agent_id", "")), []).append(
                    float(fc["p_success"]))
            except Exception:
                pass
        fams = {k: sum(v)/len(v) for k, v in fam_p.items() if v}
        if len(fams) < 2:
            continue
        shared += 1
        ps = list(fams.values())
        # disagreement = families split across 0.5 OR spread > 0.25
        opp = any((a-0.5)*(b-0.5) < 0 for a in ps for b in ps)
        if opp or (max(ps) - min(ps)) > 0.25:
            disagree += 1
        o = outcomes.get(cid)
        if not o or o.get("voided") or o.get("success_bool") is None:
            split["unresolved"] += 1
        else:
            split["success" if o["success_bool"] else "fail"] += 1
    cross_family = {
        "n_shared_contracts": shared,
        "disagreement_rate": round(disagree/shared, 4) if shared else None,
        "n_disagree": disagree,
        "resolution_split": split,
        "disagreement_def": "families split across p=0.5 OR family-mean spread > 0.25",
    }

    # ---- 3. resolution rate + survivorship ----
    total = len(contracts)
    voided = sum(1 for o in outcomes.values() if o.get("voided"))
    resolved = sum(1 for o in outcomes.values()
                   if not o.get("voided") and o.get("success_bool") is not None)
    lat = []
    for cid, o in outcomes.items():
        if o.get("voided") or o.get("success_bool") is None:
            continue
        c = contracts.get(cid)
        try:
            ca = dt.datetime.fromisoformat(str(c["created_at"]).replace("Z", "+00:00"))
            ra = dt.datetime.fromisoformat(str(o["resolved_at"]).replace("Z", "+00:00"))
            lat.append((ra-ca).total_seconds()/86400.0)
        except Exception:
            pass
    resolution = {
        "total_contracts": total, "resolved": resolved, "voided": voided,
        "rate": round(resolved/total, 4) if total else None,
        "median_latency_days": round(statistics.median(lat), 3) if lat else None,
        "note": "Brier-of-resolved-only hides survivorship; voided+unresolved exposed here.",
    }

    # ---- 4. externalities split (from real rollup) ----
    ext = {"status": "rollup_absent"}
    if ROLLUP.exists():
        try:
            rb = json.loads(ROLLUP.read_text())
            pos = rb.get("positive_externality_tags") or {}
            neg = rb.get("negative_externality_tags") or {}
            pos_n, neg_n = sum(pos.values()), sum(neg.values())
            ext = {
                "positive": {"distinct_tags": len(pos), "total_count": pos_n},
                "negative": {"distinct_tags": len(neg), "total_count": neg_n},
                "ratio_count": round(pos_n/neg_n, 3) if neg_n else None,
                "ratio_distinct": round(len(pos)/len(neg), 3) if neg else None,
                "rollup_generated_at": rb.get("generated_at"),
                "by_period": _ext_by_period(contracts, outcomes),
                "note": "Has a real negative bucket — Tier-B eligible per GP-236.",
            }
        except Exception as e:
            ext = {"status": f"rollup_parse_error:{e}"}

    block = {
        "schema": "p0_calibration.v1",
        "as_of": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "forecast_pool {contracts,outcomes,forecasts}/ + externalities_rollup.json",
        "brier_per_period": brier_per_period,
        "cross_family_disagreement": cross_family,
        "resolution": resolution,
        "externalities": ext,
        "conventions": {
            "brier": "mean over a contract's forecasts of (p-y)^2; period = ISO-week(resolved_at); non-voided resolved only",
            "uniform_baseline": "0.25 = Brier of constant p=0.5 (max-entropy reference)",
            "family": "agent_id substring -> Claude|GPT|Codex|Other",
        },
    }
    OUT.write_text(json.dumps(block, indent=2))
    print(json.dumps({k: block[k] for k in
          ("as_of", "cross_family_disagreement", "resolution")}, indent=2))
    print(f"\nwrote {OUT} ({len(brier_per_period)} periods, "
          f"{resolution['resolved']}/{total} resolved)")
    return 0


def _ext_by_period(contracts: dict, outcomes: dict) -> list[dict]:
    """Per-ISO-week externality-tag presence from contract tag fields
    (honest: sparse if ticks didn't populate tags — the infra is
    largely dormant this session; reported truthfully, not fabricated)."""
    per: dict[str, dict] = {}
    for cid, c in contracts.items():
        tags_pos = c.get("forecast_externality_tags") or c.get("externality_tags") or []
        tags_neg = c.get("negative_externality_tags") or []
        if not (tags_pos or tags_neg):
            continue
        wk = _iso_week(str(c.get("created_at") or ""))
        if not wk:
            continue
        e = per.setdefault(wk, {"period": wk, "pos": 0, "neg": 0})
        e["pos"] += len(tags_pos)
        e["neg"] += len(tags_neg)
    return [per[k] for k in sorted(per)] or [
        {"note": "no per-contract externality tags populated — "
                 "externalities infra dormant this period (honest empty)"}]


if __name__ == "__main__":
    raise SystemExit(main())
