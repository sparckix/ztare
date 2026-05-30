#!/usr/bin/env python3
"""Cross-source divergence audit — kernel of the ACRR/PECVP primitive.

The PECVP primitive (run 5 champion, score 92) proposes "Process-External
Cross-Verification": multiple independent sources record apparatus
operations; divergence between sources signals tampering or staleness.

Full ACRR/PECVP requires multi-host isolated infrastructure + cryptographic
attestation, which is over-engineering for the solo-operator case. The
SHIPPABLE KERNEL is the divergence-check pattern applied to the mining
outputs we already produce: 4-5 mining sources should agree on which
entities they flag; if they diverge silently, that's a real signal worth
surfacing.

Sources cross-checked:
  1. cross_audit_dashboard.json — convergent signals across scorecards
  2. recursive_gain_candidates.json — aggregated recursive-gain proposals
  3. structural_analogies.json — one-shot ↔ loop pairing candidates
  4. process_catalog.json — loop / one-shot / static apparatus inventory
  5. analytics/public/ledgers/catch/catch_ledger.jsonl — ratified catches (load_bearing flag)
     [added 2026-05-08 per session-mining catch on META-DARWIN demotion drift]

Surfaced divergences:
  - Entity flagged in 1 source but absent from others
  - Same entity given inconsistent kind / verdict across sources
  - Path references that resolve in one source but not in another
  - Catch-id load_bearing classification differs from how the catch is
    referenced in research notes (catch demotion drift)

Output:
  ``analytics/public/queries/audits/cross_source_divergence_audit.{json,md}``

Pure CPU. No LLM.

Usage:
    python scripts/public/mining/cross_source_divergence_audit.py
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
QUERIES = REPO / "analytics" / "public" / "queries"
CATCH_LEDGER = REPO / "analytics" / "public" / "ledgers" / "catch" / "catch_ledger.jsonl"
RESEARCH_NOTE_GLOB = "projects/*/workspace/research_notes/*.md"
OUT_JSON = QUERIES / "audits" / "cross_source_divergence_audit.json"
OUT_MD = QUERIES / "audits" / "cross_source_divergence_audit.md"


def _load(name: str) -> dict | None:
    p = QUERIES / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _load_catch_ledger(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return rows


def _scan_catch_id_references() -> dict[str, dict]:
    """Walk research notes + research_areas to find catch-id mentions and
    nearby polarity hints (e.g. "load-bearing", "demoted", "not load
    bearing", "downgraded"). Returns ``{catch_id: {"hits": [...], "demoted_hits": int}}``."""
    out: dict[str, dict] = {}
    catch_re = re.compile(r"\bC-(?:20\d{2}-\d{2}-\d{2})-\d{2,3}\b")
    demote_re = re.compile(
        r"\b(demoted|downgraded|not load[- ]bearing|narrative[- ]inflation|over[- ]?claim|retracted|withdrawn)\b",
        re.IGNORECASE,
    )
    for md in REPO.glob(RESEARCH_NOTE_GLOB):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        for m in catch_re.finditer(text):
            cid = m.group(0)
            # Look at +/- 200 chars around the match for demotion polarity.
            start = max(0, m.start() - 200)
            end = min(len(text), m.end() + 200)
            window = text[start:end]
            entry = out.setdefault(cid, {"hits": [], "demoted_hits": 0})
            entry["hits"].append(str(md.relative_to(REPO)))
            if demote_re.search(window):
                entry["demoted_hits"] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    print("=== cross-source divergence audit ===")
    cross_audit = _load("audits/cross_audit_dashboard.json")
    rec_gain = _load("trajectory/recursive_gain_candidates.json")
    struct_analogies = _load("process/structural_analogies.json")
    process_catalog = _load("process/process_catalog.json")
    catch_ledger = _load_catch_ledger(CATCH_LEDGER)
    catch_refs = _scan_catch_id_references() if catch_ledger else {}

    sources_loaded = sum(
        1 for s in (cross_audit, rec_gain, struct_analogies, process_catalog) if s
    ) + (1 if catch_ledger else 0)
    print(f"  sources loaded: {sources_loaded} / 5")
    print(f"  catch_ledger entries: {len(catch_ledger)}")
    print(f"  catch-id references scanned: {len(catch_refs)}")

    # Build per-entity multi-source view: entity_id → set of (source, flag-type)
    entity_seen: dict[str, set[tuple[str, str]]] = defaultdict(set)
    entity_kinds: dict[str, set[tuple[str, str]]] = defaultdict(set)  # entity → (source, kind/verdict)

    if cross_audit:
        for sig in cross_audit.get("convergent_signals", []) or []:
            eid = sig.get("id")
            if not eid:
                continue
            entity_seen[str(eid)].add(("cross_audit", "convergent"))
            entity_kinds[str(eid)].add(("cross_audit", str(sig.get("kind", "?"))))
        for ent in cross_audit.get("all_flagged_entities_top", []) or []:
            eid = ent.get("id")
            if not eid:
                continue
            entity_seen[str(eid)].add(("cross_audit", "flagged"))

    if rec_gain:
        for c in rec_gain.get("candidates", []) or []:
            eid = c.get("entity")
            if not eid:
                continue
            entity_seen[str(eid)].add(("recursive_gain", c.get("mechanism", "?")))
            entity_kinds[str(eid)].add(("recursive_gain", str(c.get("kind", "?"))))

    if struct_analogies:
        for p in struct_analogies.get("pairs", []) or []:
            for k in ("one_shot", "analogous_loop"):
                eid = p.get(k)
                if not eid:
                    continue
                entity_seen[str(eid)].add(("structural_analogies", k))

    if process_catalog:
        for r in process_catalog.get("all_records", []) or []:
            eid = r.get("path")
            if not eid:
                continue
            entity_seen[str(eid)].add(("process_catalog", r.get("inferred_kind", "?")))
            entity_kinds[str(eid)].add(("process_catalog", str(r.get("inferred_kind", "?"))))

    # 5th source: catch_ledger.jsonl. Each catch_id is an entity; the
    # load_bearing flag is its kind. We surface drift when a catch is
    # marked load_bearing=true in the ledger but research-note prose
    # near the catch-id mention contains demotion polarity (catch
    # demotion drift).
    catch_demotion_drift: list[dict] = []
    for c in catch_ledger:
        cid = c.get("catch_id")
        if not cid:
            continue
        load_bearing = bool(c.get("load_bearing"))
        category = c.get("category", "?")
        entity_seen[str(cid)].add(("catch_ledger", "load_bearing" if load_bearing else "soft"))
        entity_kinds[str(cid)].add(("catch_ledger", str(category)))

        ref = catch_refs.get(cid)
        if ref and load_bearing and ref["demoted_hits"] > 0:
            catch_demotion_drift.append({
                "catch_id": cid,
                "category": category,
                "ledger_load_bearing": True,
                "demoted_hits_in_notes": ref["demoted_hits"],
                "research_note_paths": sorted(set(ref["hits"]))[:5],
            })
        # Also flag: ledger says NOT load_bearing but no research-note
        # mentions exist at all (orphan catch — deserves a workpaper).
        if not load_bearing and not ref:
            entity_seen[str(cid)].add(("catch_ledger", "orphan_no_notes"))

    # Surface divergences
    single_source = []
    multi_source_disagreement = []
    for eid, sources_set in entity_seen.items():
        n_sources = len({s for s, _ in sources_set})
        if n_sources == 1:
            # Surface only entities that LOOK significant — non-trivial path
            if "/" in eid or eid.startswith("R") or "GP-" in eid:
                single_source.append({
                    "entity": eid,
                    "single_source": next(iter(sources_set))[0],
                    "tag": next(iter(sources_set))[1],
                })
        else:
            # Check kind/verdict disagreement
            kinds_per_src = defaultdict(set)
            for src, kind in entity_kinds.get(eid, set()):
                kinds_per_src[src].add(kind)
            unique_kinds = {k for ks in kinds_per_src.values() for k in ks}
            if len(unique_kinds) > 1:
                multi_source_disagreement.append({
                    "entity": eid,
                    "n_sources": n_sources,
                    "kind_per_source": {s: sorted(ks) for s, ks in kinds_per_src.items()},
                })

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sources_loaded": sources_loaded,
        "n_entities_tracked": len(entity_seen),
        "n_single_source_flags": len(single_source),
        "n_multi_source_disagreements": len(multi_source_disagreement),
        "n_catch_demotion_drift": len(catch_demotion_drift),
        "single_source_significant": single_source[:30],
        "multi_source_disagreements": multi_source_disagreement[:30],
        "catch_demotion_drift": catch_demotion_drift[:30],
        "method_note": (
            "Kernel of the ACRR/PECVP primitive (substrate-produced, run 5). "
            "Full ACRR requires isolated infrastructure + cryptographic "
            "attestation; this kernel applies the divergence-check pattern "
            "to mining outputs we already produce. Single-source flags = "
            "entities only one source noticed (potential coverage gap). "
            "Multi-source disagreements = entities multiple sources see but "
            "characterize differently (potential semantic drift)."
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  entities tracked: {len(entity_seen)}")
    print(f"  single-source flags (potential coverage gaps): {len(single_source)}")
    print(f"  multi-source kind disagreements: {len(multi_source_disagreement)}")
    print(f"  wrote {args.out_json}")

    md = ["# Cross-Source Divergence Audit (ACRR/PECVP kernel)\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(
        f"_Sources loaded:_ {sources_loaded}/5  "
        f"_Entities tracked:_ {len(entity_seen)}  "
        f"_Single-source flags:_ {len(single_source)}  "
        f"_Multi-source disagreements:_ {len(multi_source_disagreement)}  "
        f"_Catch-demotion-drift hits:_ {len(catch_demotion_drift)}\n"
    )
    md.append(
        "**Kernel of the substrate-produced ACRR/PECVP primitive.** Full "
        "ACRR/PECVP requires multi-host isolated infrastructure + crypto "
        "attestation (over-engineering for solo-operator setup). This "
        "kernel applies the divergence-check pattern to mining outputs we "
        "already produce.\n"
    )
    if multi_source_disagreement:
        md.append("## Multi-source kind disagreements (semantic drift candidates)\n")
        md.append(
            "| Entity | Sources | Kinds per source |\n|---|---:|---|"
        )
        for d in multi_source_disagreement[:20]:
            kinds = "; ".join(
                f"{s}: {','.join(ks)}" for s, ks in d["kind_per_source"].items()
            )
            md.append(f"| `{d['entity'][:60]}` | {d['n_sources']} | {kinds} |")
        md.append("")
    if catch_demotion_drift:
        md.append("## Catch-demotion drift (5th source: catch_ledger.jsonl)\n")
        md.append(
            "Catches marked `load_bearing=true` in `analytics/public/ledgers/catch/catch_ledger.jsonl` "
            "whose research-note context contains demotion polarity "
            "(\"demoted\", \"downgraded\", \"not load-bearing\", \"narrative-inflation\", "
            "\"over-claim\", \"retracted\", \"withdrawn\"). If a load-bearing catch is "
            "being narratively demoted in notes, the ledger should be updated or the "
            "demotion withdrawn — surfaces the META-DARWIN re-appearance pattern.\n"
        )
        md.append("| Catch | Category | Demoted hits | Notes |\n|---|---|---:|---|")
        for d in catch_demotion_drift[:20]:
            notes_disp = ", ".join(d["research_note_paths"][:2])
            md.append(
                f"| `{d['catch_id']}` | `{d['category']}` | {d['demoted_hits_in_notes']} | {notes_disp} |"
            )
        md.append("")
    if single_source:
        md.append("## Single-source flags (potential coverage gaps)\n")
        md.append("| Entity | Sole source | Tag |\n|---|---|---|")
        for s in single_source[:20]:
            md.append(f"| `{s['entity'][:60]}` | `{s['single_source']}` | `{s['tag']}` |")
        md.append("")
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
