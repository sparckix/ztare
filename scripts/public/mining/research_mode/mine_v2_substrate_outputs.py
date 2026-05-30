#!/usr/bin/env python3
"""Mine ex-post the v2 substrate's run history for insights.

Walks projects/ztare_on_ztare_v2_expanded_scope/history/*.md +
debate_log_iter_*.md + workspace/charter_patches.jsonl, extracts:

  - Champion proposals (one per (run-id, score) pair in history)
  - Weakest-point critiques per iter (judge's running diagnosis)
  - Charter-critic patches that fired
  - Primitive-class proposals + their evidence anchors
  - Recurring failure modes across iters (clustering of weakest-points)

Output:
  ``analytics/public/queries/v2_substrate_postmortem.{json,md}``

This is the "mine ex-post" the user requested: instead of building a
tight Python integration with the GP-227 dashboard, just walk the
substrate's artifacts and produce a digest. Operator can review +
decide what to surface.

Pure CPU. No LLM (regex + path traversal only).

Usage:
    python scripts/public/mining/mine_v2_substrate_outputs.py
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROJECT = REPO / "projects" / "ztare_on_ztare_v2_expanded_scope"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "v2_substrate_postmortem.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "v2_substrate_postmortem.md"


_PROPOSAL_TITLE_RE = re.compile(
    r"^##+\s*(?:STRUCTURAL\s+(?:PIVOT|MUTATION)|RG-v2-\d+|Primitive\s+Proposal|Thesis|RESOLVED\s+THESIS)[:\s\-—]+(.+?)$",
    re.MULTILINE,
)
_MECHANISM_RE = re.compile(r"mechanism[\"']?\s*[:=]\s*[\"']?([\w_]+)[\"']?")
_CITED_PAPER_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+(?:et\s+al\.?|&\s+\w+))?)\s*\(?(\d{4})\)?\s*[\.,—\-]"
)
_LIBRARY_RE = re.compile(r"\b([a-z_][\w]*)(\.[a-z_][\w]*)+\b")
_NEGATIVE_EVIDENCE_RE = re.compile(
    r"(?i)(absence|lack|no|missing|never)\s+(of|in|for)\s+([^.]{8,80})"
)


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    print("=== mine v2 substrate outputs ===")
    if not PROJECT.exists():
        print(f"  ERROR: project dir not found at {PROJECT}")
        return 2

    # ---- Champion history
    history_dir = PROJECT / "history"
    champion_iters: list[dict] = []
    for p in sorted(history_dir.glob("*_iter*_score_*.md")):
        if "_dag" in p.name or "_meta" in p.name:
            continue
        m = re.match(r"(\d+)_iter(\d+)_score_(\d+)_", p.name)
        if not m:
            continue
        run_id, iter_idx, score = m.group(1), int(m.group(2)), int(m.group(3))
        text = _read(p)
        title_m = _PROPOSAL_TITLE_RE.search(text)
        title = (title_m.group(1) if title_m else "(no title parsed)").strip()[:120]
        mech_m = _MECHANISM_RE.search(text)
        mechanism = mech_m.group(1) if mech_m else None
        cited_papers = list({f"{a} {y}" for a, y in _CITED_PAPER_RE.findall(text)})[:5]
        libraries = list(set(
            "".join(g) for g in _LIBRARY_RE.findall(text[:3000])
        ))[:8]
        negative_evidence = list({
            m.group(0)[:140] for m in _NEGATIVE_EVIDENCE_RE.finditer(text[:4000])
        })[:5]
        champion_iters.append({
            "run_id": run_id,
            "iter": iter_idx,
            "score": score,
            "title": title,
            "mechanism": mechanism,
            "cited_papers": cited_papers,
            "libraries_named": libraries,
            "negative_evidence_clauses": negative_evidence,
            "file_size_bytes": p.stat().st_size,
        })
    print(f"  champion iters: {len(champion_iters)}")

    # ---- Weakest-point clustering across all iters
    weakest_points: list[dict] = []
    eval_files = list(PROJECT.glob("history/*_meta.json"))
    for p in sorted(eval_files):
        try:
            d = json.loads(_read(p))
            wp = d.get("weakest_point") or ""
            if wp:
                m = re.match(r"(\d+)_iter(\d+)_score_(\d+)_", p.name)
                if m:
                    weakest_points.append({
                        "run_id": m.group(1),
                        "iter": int(m.group(2)),
                        "score": int(m.group(3)),
                        "weakest_point": wp[:300],
                    })
        except Exception:  # noqa: BLE001
            continue
    print(f"  weakest-points: {len(weakest_points)}")

    # ---- Recurring critique themes (regex-based; LLM would do better)
    theme_patterns = {
        "common_mode_independence": r"(?i)common[\s-]*mode|independence\s+(assumption|critical|dependent)",
        "kill_criterion_gap": r"(?i)kill[\s-]*criterion|threshold\s+(not|missing)|deadline\s+(open|missing)",
        "single_substrate": r"(?i)single\s+substrate|narrow\s+scope|substrate[\s-]*specific",
        "cherry_picked_threshold": r"(?i)cherry[\s-]*picked|threshold\s+not\s+justified|domain\s+rates",
        "exhaustiveness": r"(?i)exhaustive|completeness\s+(of|in)\s+\w+\s+(detection|coverage)",
        "operator_dependency": r"(?i)operator[\s-]*(declared|side|registry|honesty|controlled)",
    }
    theme_hits: Counter = Counter()
    for wp in weakest_points:
        text = wp["weakest_point"]
        for theme, pat in theme_patterns.items():
            if re.search(pat, text):
                theme_hits[theme] += 1

    # ---- Charter-critic patches
    cc_patches_path = PROJECT / "workspace" / "charter_patches.jsonl"
    cc_patches: list[dict] = []
    if cc_patches_path.exists():
        for line in _read(cc_patches_path).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                cc_patches.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    print(f"  charter-critic patches: {len(cc_patches)}")

    # ---- Primitive-class iters
    explored_path = PROJECT / "workspace" / "explored_primitive_classes.jsonl"
    explored_classes: list[dict] = []
    if explored_path.exists():
        for line in _read(explored_path).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                explored_classes.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    print(f"  primitive classes explored (champion-promoted): {len(explored_classes)}")

    # ---- Synthesis
    by_run: dict[str, list[dict]] = defaultdict(list)
    for c in champion_iters:
        by_run[c["run_id"]].append(c)
    runs_summary = []
    for run_id, iters in sorted(by_run.items()):
        peak = max(iters, key=lambda c: c["score"])
        runs_summary.append({
            "run_id": run_id,
            "n_champion_iters": len(iters),
            "peak_score": peak["score"],
            "peak_iter": peak["iter"],
            "peak_title": peak["title"],
            "peak_mechanism": peak["mechanism"],
        })

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_runs_completed": len(by_run),
        "n_champion_iters_total": len(champion_iters),
        "n_weakest_points_collected": len(weakest_points),
        "n_charter_critic_patches": len(cc_patches),
        "n_primitive_classes_explored": len(explored_classes),
        "runs_summary": runs_summary,
        "recurring_critique_themes": dict(theme_hits.most_common()),
        "champion_iters": champion_iters,
        "primitive_classes_explored": explored_classes,
        "charter_critic_patches": [
            {
                "run_id": p.get("run_id"),
                "reframe_type": p.get("reframe_type"),
                "target": p.get("target"),
                "section_id": p.get("section_id"),
            }
            for p in cc_patches
        ],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")

    md = ["# ZTARE-on-ZTARE v2 Substrate — Postmortem (ex-post mining)\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(
        f"_Runs:_ {len(by_run)}  "
        f"_Champion iters:_ {len(champion_iters)}  "
        f"_Weakest-points:_ {len(weakest_points)}  "
        f"_Charter-critic patches:_ {len(cc_patches)}\n"
    )

    md.append("## Per-run summary\n")
    md.append("| Run | Champion iters | Peak score | Peak iter | Mechanism | Title |\n|---|---:|---:|---:|---|---|")
    for r in runs_summary:
        md.append(
            f"| `{r['run_id']}` | {r['n_champion_iters']} | "
            f"{r['peak_score']} | {r['peak_iter']} | "
            f"`{r['peak_mechanism'] or '?'}` | {r['peak_title'][:60]} |"
        )
    md.append("")

    md.append("## Recurring critique themes (across all weakest-points)\n")
    md.append("| Theme | Occurrences |\n|---|---:|")
    for theme, n in theme_hits.most_common():
        md.append(f"| `{theme}` | {n} |")
    md.append("")

    md.append("## Champion iter details\n")
    for c in champion_iters:
        md.append(f"### Run {c['run_id']} iter {c['iter']} — score {c['score']}")
        md.append(f"**Title:** {c['title']}")
        md.append(f"**Mechanism:** `{c['mechanism'] or '?'}`")
        if c["cited_papers"]:
            md.append(f"**Cited:** {', '.join(c['cited_papers'])}")
        if c["libraries_named"]:
            md.append(f"**Libraries named:** {', '.join('`' + l + '`' for l in c['libraries_named'])}")
        if c["negative_evidence_clauses"]:
            md.append(f"**Negative-evidence clauses:**")
            for ne in c["negative_evidence_clauses"]:
                md.append(f"  - {ne}")
        md.append("")

    md.append("## Charter-critic patches that fired\n")
    if cc_patches:
        md.append("| Run | Reframe-type | Target | Section |\n|---|---|---|---|")
        for p in cc_patches:
            md.append(
                f"| `{p.get('run_id', '?')}` | `{p.get('reframe_type', '?')}` | "
                f"`{p.get('target', '?')}` | {str(p.get('section_id', '?'))[:60]} |"
            )
        md.append("")
    else:
        md.append("(no charter-critic patches recorded)\n")

    md.append("## Primitive classes explored (champion-promoted only)\n")
    if explored_classes:
        md.append("| Run | Iter | Class | Score | Timestamp |\n|---|---:|---|---:|---|")
        for c in explored_classes:
            md.append(
                f"| `{c.get('run_id')}` | {c.get('iter')} | "
                f"`{c.get('class_name')}` | {c.get('score')} | "
                f"{c.get('ts_utc', '?')[:19]} |"
            )
        md.append("")
    else:
        md.append("(no primitive-class iters tracked yet)\n")

    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
