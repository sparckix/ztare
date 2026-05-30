#!/usr/bin/env python3
"""v32_corpus_real_content_retest.py — fair re-test of deterministic L2 classifier.

v32_meta_pattern_miner fed universal_classifier.classify_text() only the
theorem NAME + source path → it returned L2_no_signal on ~100% of rows →
verdict label_quality_binding.

But that may be an INPUT-IMPOVERISHMENT artifact, not a classifier weakness.
The keyword heuristic needs prose describing the mathematical move. A bare
name has none. The fair test: feed it the actual theorem STATEMENT +
PROOF BODY extracted from Mathlib source, then re-measure signal rate.

Decision:
  - If signal rate jumps materially with real content → v32 verdict was
    an artifact; re-run the miner with real-content corpus.
  - If signal rate stays ~0 even with real statement+proof → the
    deterministic classifier genuinely fails on Lean text; proceed to
    GPT-5.5 Case 2 (LLM-as-L2-classifier with ≥80% pass-gate).

No LLM. Deterministic. Reuses extract_signature / extract_proof_body.
"""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/public/control"))

from src.ztare.research_director.universal_classifier import classify_text  # type: ignore
from gp235_section_4_1_intra_cluster import extract_proof_body  # type: ignore
from v32_route_c_replay_batch import extract_signature  # type: ignore


def main():
    curated = json.load(open("/tmp/v32_curated_test_rows.json"))
    rows = [r for r in curated["rows"] if r.get("resolved_path") and r.get("theorem")]
    print(f"# v32 deterministic-L2 fair re-test on real content")
    print(f"Rows with resolvable Mathlib source + theorem name: {len(rows)}\n")

    name_only_signal = 0
    real_content_signal = 0
    detail = []
    for r in rows:
        thm = r["theorem"]
        src = r["resolved_path"]
        # (a) name-only input (what v32 miner used)
        name_text = f"{thm} {r.get('source_file','')}"
        c_name = classify_text(name_text)
        # (b) real content: signature + proof body
        sig = extract_signature(src, thm) or ""
        body = extract_proof_body(src, thm) or ""
        real_text = f"{sig}\n{body}"
        c_real = classify_text(real_text)

        n_sig = c_name.dominant_op not in (None,) and c_name.confidence != "low"
        r_sig = c_real.dominant_op not in (None,) and c_real.confidence != "low"
        if c_name.dominant_op:
            name_only_signal += 1
        if c_real.dominant_op:
            real_content_signal += 1
        detail.append({
            "theorem": thm,
            "name_only_op": c_name.dominant_op, "name_only_conf": c_name.confidence,
            "real_op": c_real.dominant_op, "real_conf": c_real.confidence,
            "sig_chars": len(sig), "body_chars": len(body),
        })

    n = len(rows)
    print(f"{'theorem':<40} {'name-only':<22} {'real-content':<22}")
    for d in detail:
        no = f"{d['name_only_op'] or '—'}({d['name_only_conf'][:3]})"
        rc = f"{d['real_op'] or '—'}({d['real_conf'][:3]})"
        print(f"  {d['theorem'][:38]:<38} {no:<22} {rc:<22} sig={d['sig_chars']} body={d['body_chars']}")

    print(f"\nName-only dominant_op present: {name_only_signal}/{n}")
    print(f"Real-content dominant_op present: {real_content_signal}/{n}")
    real_hi = sum(1 for d in detail if d["real_conf"] in ("high", "medium"))
    print(f"Real-content high/medium confidence: {real_hi}/{n}")

    # Verdict on the artifact question
    print(f"\n## Verdict on input-impoverishment hypothesis")
    if real_content_signal >= max(1, int(0.5 * n)) and real_hi >= max(1, int(0.3 * n)):
        verdict = "INPUT_IMPOVERISHMENT_ARTIFACT"
        rationale = (f"deterministic classifier produces signal on {real_content_signal}/{n} "
                     f"rows ({real_hi}/{n} high/med-conf) when given real statement+proof — "
                     f"v32 label_quality_binding was an artifact of feeding names not content. "
                     f"Re-run the miner with real-content corpus.")
    elif real_content_signal > name_only_signal:
        verdict = "PARTIAL_IMPROVEMENT_STILL_WEAK"
        rationale = (f"real content helps ({name_only_signal}→{real_content_signal}) but "
                     f"high/med-conf only {real_hi}/{n} — deterministic classifier still "
                     f"too weak; GPT-5.5 Case 2 (LLM-as-L2-classifier) is warranted.")
    else:
        verdict = "DETERMINISTIC_CLASSIFIER_GENUINELY_FAILS"
        rationale = (f"real statement+proof does not rescue signal ({real_content_signal}/{n}, "
                     f"hi/med {real_hi}/{n}) — keyword heuristic genuinely unfit for Lean text; "
                     f"GPT-5.5 Case 2 LLM-as-L2-classifier required.")
    print(f"VERDICT: {verdict} — {rationale}")

    out = {
        "n_rows": n,
        "name_only_signal": name_only_signal,
        "real_content_signal": real_content_signal,
        "real_content_high_med_conf": real_hi,
        "verdict": verdict,
        "rationale": rationale,
        "detail": detail,
    }
    Path(ROOT / "analytics/public/leanmill/results/v32_deterministic_L2_retest.json").write_text(
        json.dumps(out, indent=2, default=str))
    print(f"\nwrote analytics/public/leanmill/results/v32_deterministic_L2_retest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
