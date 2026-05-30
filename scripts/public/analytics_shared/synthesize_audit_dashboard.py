#!/usr/bin/env python3
"""Cross-audit synthesis dashboard.

We have 9 audit/scorecard outputs that each look at one axis:

  - reflexive_audit_report.json — failure-mode audit (machinery_broken classifier)
  - reflexive_primitive_roi.json — per-primitive engagement / hit rate
  - seam_health_report.json — seam corpus health
  - miner_roi_report.json — per-miner alive/dead
  - cap_kind_distribution.json — cap-kind across substrate classes
  - triangulation_per_target.json — per-target compounding signal
  - closure_patterns.json — v5-op closure rate distribution
  - endpoint_compression_audit.json — GP-223 Layer 3 candidates
  - gate_telemetry_diagnosis.json — cage-engagement-name health

This dashboard joins them by entity (project / target / primitive /
seam / miner / gate-name) and surfaces convergent signals — entries
that are flagged in N independent scorecards. That's the
compounding-evidence move: a single flag is noise; flags from 3
independent scorecards is signal.

Output:
  ``analytics/public/queries/audits/cross_audit_dashboard.json``
  ``analytics/public/queries/audits/cross_audit_dashboard.md``

Pure CPU, no LLM.

Usage:
    python scripts/public/analytics_shared/synthesize_audit_dashboard.py
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
QUERIES = REPO / "analytics" / "public" / "queries"
NS_QUERIES = REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
SEAMS_REFL = REPO / "research_areas" / "private" / "seams" / "reflexive"

OUT_JSON = QUERIES / "audits" / "cross_audit_dashboard.json"
OUT_MD = QUERIES / "audits" / "cross_audit_dashboard.md"


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


_PRIMITIVE_DESCRIPTIVE_NAMES: dict[str, str] = {}


def _build_descriptive_name_map(primitive_roi_data: dict | None) -> dict[str, str]:
    """Map primitive_id ('R10') → 'cross_class_extrapolation'.

    Reads the primitive_roi audit's own 'name' field so the dashboard
    stays in sync if names change in the registry. Fallback parses
    descriptive name from the gate_telemetry rename_candidate's actual
    field (e.g. ``R10_cross_class_extrapolation`` → ``cross_class_extrapolation``)
    so primitives present in logs but not in the registry still get
    a friendly label.
    """
    out: dict[str, str] = {}
    for p in (primitive_roi_data or {}).get("primitives") or []:
        pid = p.get("primitive_id") or ""
        name = p.get("name") or ""
        if pid and name and pid != name:
            out[pid] = name
    return out


def _label(kind: str, eid: str) -> str:
    """User-facing entity label. ``primitive/R10`` → ``R10 (cross_class_extrapolation)``."""
    if kind == "primitive":
        desc = _PRIMITIVE_DESCRIPTIVE_NAMES.get(eid)
        if desc:
            return f"{eid} ({desc})"
    return eid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    print("=== cross-audit synthesis ===")

    # Load each scorecard
    sources = {
        "reflexive_audit": load_json(SEAMS_REFL / "reflexive_audit_report.json"),
        "primitive_roi": load_json(QUERIES / "reflexive" / "reflexive_primitive_roi.json"),
        "seam_health": load_json(QUERIES / "audits" / "seam_health_report.json"),
        "miner_roi": load_json(QUERIES / "audits" / "miner_roi_report.json"),
        "cap_kind": load_json(QUERIES / "classification" / "cap_kind_distribution.json"),
        "triangulation": load_json(NS_QUERIES / "triangulation_per_target.json"),
        "closure_patterns": load_json(QUERIES / "reflexive" / "closure_patterns.json"),
        "endpoint_compression": load_json(QUERIES / "lean" / "endpoint_compression_audit.json"),
        "gate_telemetry": load_json(QUERIES / "audits" / "gate_telemetry_diagnosis.json"),
    }
    available = [k for k, v in sources.items() if v is not None]
    print(f"  scorecards loaded: {len(available)} / {len(sources)}")
    for name in sources:
        present = "✓" if sources[name] is not None else "—"
        print(f"    {present} {name}")

    # Build descriptive-name map so MD output reads
    # "R10 (cross_class_extrapolation)" instead of just "R10". Stays
    # in sync with the primitive_roi registry — the single source of
    # truth for primitive_id → descriptive name.
    global _PRIMITIVE_DESCRIPTIVE_NAMES
    _PRIMITIVE_DESCRIPTIVE_NAMES = _build_descriptive_name_map(sources["primitive_roi"])

    # ---- Per-entity flags. Each flag is a tuple (scorecard, severity, detail).
    # entity_flags[(entity_kind, entity_id)] = list of flags
    entity_flags: dict[tuple, list] = defaultdict(list)

    # 1. Reflexive audit — projects flagged machinery_broken
    refl = sources["reflexive_audit"] or {}
    for r in (refl.get("results") or []):
        if r.get("verdict") in ("machinery_broken", "ambiguous"):
            entity_flags[("project", r["project_id"])].append({
                "source": "reflexive_audit",
                "severity": "warn" if r["verdict"] == "machinery_broken" else "info",
                "detail": (
                    f"verdict={r['verdict']} "
                    f"failure_mode={r.get('failure_mode')} "
                    f"stuck={r.get('stuck_layer')}"
                ),
            })

    # 2. Primitive ROI — primitives in dead / decorative band
    roi = sources["primitive_roi"] or {}
    for p in (roi.get("primitives") or []):
        verdict = p.get("verdict")
        if verdict in ("dead", "decorative_candidate", "noisy_detector_candidate"):
            entity_flags[("primitive", p["primitive_id"])].append({
                "source": "primitive_roi",
                "severity": "warn",
                "detail": (
                    f"verdict={verdict} engagement={p.get('engagement_rate', 0):.2%} "
                    f"engaged={p.get('n_engaged', 0)} refused={p.get('n_refused', 0)}"
                ),
            })

    # 3. Seam health — orphan / stale / implemented_unmarked
    sh = sources["seam_health"] or {}
    for s in (sh.get("orphan_candidates") or [])[:30]:
        entity_flags[("seam", s["seam_id"])].append({
            "source": "seam_health",
            "severity": "warn",
            "detail": f"orphan: open + no spec + no code, age={s['age_days']}d",
        })
    for s in (sh.get("stale_candidates") or [])[:30]:
        entity_flags[("seam", s["seam_id"])].append({
            "source": "seam_health",
            "severity": "info",
            "detail": f"stale: no F-row mention, age={s['age_days']}d",
        })
    for s in (sh.get("implemented_unmarked") or [])[:30]:
        entity_flags[("seam", s["seam_id"])].append({
            "source": "seam_health",
            "severity": "info",
            "detail": f"implemented_unmarked: code traces exist, status still open",
        })

    # 4. Miner ROI — dead / dormant
    mr = sources["miner_roi"] or {}
    for m in (mr.get("miners") or []):
        v = m.get("verdict")
        if v in ("dead_no_output", "dead_stale", "dormant"):
            entity_flags[("miner", m["script"])].append({
                "source": "miner_roi",
                "severity": "warn" if "dead" in v else "info",
                "detail": (
                    f"verdict={v} last_run_age={m.get('last_run_age_days')} "
                    f"refs={m.get('downstream_references')}"
                ),
            })

    # 5. Cap-kind distribution — projects with high stagnation + dominant cap_kind
    ck = sources["cap_kind"] or {}
    for proj_name, info in (ck.get("per_project") or {}).items():
        if info.get("dominant_cap_kind") not in (None, "none"):
            entity_flags[("project", proj_name)].append({
                "source": "cap_kind",
                "severity": "info",
                "detail": (
                    f"dominant_cap_kind={info['dominant_cap_kind']} "
                    f"n_iters={info.get('n_iters')}"
                ),
            })

    # 6. Triangulation — high compounding score targets
    tri = sources["triangulation"] or {}
    for d in (tri.get("dossiers") or [])[:10]:
        if d.get("compounding_score", 0) >= 4:
            entity_flags[("target", d["target"])].append({
                "source": "triangulation",
                "severity": "warn",
                "detail": (
                    f"compounding_score={d['compounding_score']} "
                    f"events={d.get('n_cannot_patch_events', 0)}"
                ),
            })

    # 7. Closure patterns — primitive_candidates (none today, but check)
    cp = sources["closure_patterns"] or {}
    for c in (cp.get("candidates") or []):
        if c.get("verdict") == "primitive_candidate":
            entity_flags[("v5_op", c["v5_op"])].append({
                "source": "closure_patterns",
                "severity": "info",
                "detail": (
                    f"closures={c.get('closure_count', 0)} "
                    f"classes={c.get('n_substrate_classes', 0)} "
                    "no existing gate covers"
                ),
            })

    # 8. Endpoint compression candidates
    ec = sources["endpoint_compression"] or {}
    for c in (ec.get("candidates") or []):
        target_name = c.get("target", "?")
        entity_flags[("target", target_name)].append({
            "source": "endpoint_compression",
            "severity": "info",
            "detail": (
                f"GP-223 Layer 3 candidate: field={c.get('field')} "
                f"pattern={c.get('name_pattern')}"
            ),
        })

    # 9. Gate telemetry — rename candidates
    # Dual-key the flag: once by the expected gate_name (for gate-name
    # readers) and once by the primitive_id parsed out of the actual
    # name (e.g. ``R10_cross_class_extrapolation`` → ``R10``). The
    # second key lets the convergent-signal join match these flags
    # against ``primitive_roi`` flags on the same primitive — without
    # the alias the dashboard misses obvious cross-scorecard matches.
    gt = sources["gate_telemetry"] or {}
    import re
    _prim_re = re.compile(r"^(R\d+)_")
    for r in (gt.get("rename_candidates") or [])[:15]:
        flag = {
            "source": "gate_telemetry",
            "severity": "info",
            "detail": (
                f"expected name absent; actual='{r['actual']}' (count={r['actual_count']})"
            ),
        }
        entity_flags[("gate_name", r["expected"])].append(flag)
        m = _prim_re.match(r.get("actual", ""))
        if m:
            entity_flags[("primitive", m.group(1))].append({
                **flag,
                "detail": (
                    f"gate_telemetry alias of {r['expected']} → "
                    f"{r['actual']} (count={r['actual_count']})"
                ),
            })

    # ---- Compute convergent signals: entities flagged in ≥2 sources ----
    convergent = []
    for (kind, eid), flags in entity_flags.items():
        sources_seen = {f["source"] for f in flags}
        if len(sources_seen) >= 2:
            severity = "critical" if any(f["severity"] == "warn" for f in flags) and len(sources_seen) >= 3 else "warn" if any(f["severity"] == "warn" for f in flags) else "info"
            convergent.append({
                "kind": kind,
                "id": eid,
                "n_sources": len(sources_seen),
                "sources": sorted(sources_seen),
                "severity": severity,
                "flags": flags,
            })
    convergent.sort(key=lambda c: (-c["n_sources"], c["kind"], c["id"]))

    # All flagged entities (single + multi)
    all_flagged = []
    for (kind, eid), flags in entity_flags.items():
        all_flagged.append({
            "kind": kind,
            "id": eid,
            "n_sources": len({f["source"] for f in flags}),
            "n_flags": len(flags),
            "flags": flags,
        })
    all_flagged.sort(key=lambda e: (-e["n_sources"], -e["n_flags"]))

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scorecards_loaded": available,
        "n_entities_flagged": len(all_flagged),
        "n_convergent_signals": len(convergent),
        "convergent_signals": convergent,
        "all_flagged_entities_top": all_flagged[:50],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")

    md = ["# Cross-Audit Synthesis Dashboard\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(
        f"_Scorecards joined:_ {len(available)}  "
        f"_Entities flagged:_ {len(all_flagged)}  "
        f"_Convergent signals (≥2 scorecards):_ {len(convergent)}\n"
    )
    md.append("## Convergent signals (≥2 independent scorecards)\n")
    if convergent:
        md.append(
            "| Severity | Kind | Entity | # sources | Sources | Detail |\n"
            "|---|---|---|---:|---|---|"
        )
        for c in convergent:
            details = " | ".join(f["detail"] for f in c["flags"])
            label = _label(c["kind"], c["id"])
            md.append(
                f"| `{c['severity']}` | `{c['kind']}` | `{label}` | "
                f"{c['n_sources']} | {', '.join(c['sources'])} | {details[:200]} |"
            )
        md.append("")
    else:
        md.append("(none — all flags came from single scorecards)\n")
    md.append("## Top single-source flags\n")
    md.append(
        "| Kind | Entity | # flags | Sources |\n|---|---|---:|---|"
    )
    for e in all_flagged[:30]:
        if e["n_sources"] == 1:
            srcs = sorted({f["source"] for f in e["flags"]})
            label = _label(e["kind"], e["id"])
            md.append(
                f"| `{e['kind']}` | `{label}` | {e['n_flags']} | "
                f"{', '.join(srcs)} |"
            )
    md.append("")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
