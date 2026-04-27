"""GP-149 cross-provider classifier agreement test.

Samples 100 weakest-point records stratified by score bucket and classifies
each under THREE LLM providers (OpenAI, Anthropic, Google). Measures pairwise
Cohen's kappa and per-class three-way agreement to detect whether the
classifier taxonomy is LLM-aesthetic-biased (separate from the judge-aesthetic
bias already measured via mine_judge_stratified.py).

Output: analytics/queries/cross_provider_classifier_agreement_<YYYY-MM-DD>.json

Requires three environment variables:
  OPENAI_API_KEY
  ANTHROPIC_API_KEY
  GEMINI_API_KEY

Cost estimate (2026-04-24 pricing):
  gpt-4.1-mini   ~$0.08
  claude-haiku   ~$0.27
  gemini-flash   ~$0.02
  Total          <$0.40

Runtime: ~10 minutes wall clock (3 providers × ~100 calls × sequential).

Plan reference: analytics/queries/cross_provider_classifier_plan_2026-04-24.md
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ARCHIVE = REPO / "analytics" / "trajectory_archive_enriched.jsonl"
OUT = REPO / "analytics" / "queries"

N_SAMPLE = 100
RANDOM_SEED = 17

# 15-class taxonomy (matches mine_weakest_link_llm_classify.py)
LABEL_SET = [
    "overclaimed_scope", "missing_mechanism", "missing_counterfactual",
    "parameter_sensitivity", "unfalsifiable_claim", "missing_baseline",
    "unmeasurable_construct", "temporal_mismatch", "definition_ambiguity",
    "overclaimed_exclusivity", "missing_derivation", "non_identifiability",
    "unsupported_assumption", "catastrophic_fit_failure", "other",
]

CLASSIFIER_PROMPT = """\
You are classifying a "weakest point" critique written by an AI judge against an AI-generated
scientific/mathematical thesis. Select exactly ONE label from the list below that best
describes the DOMINANT failure mode.

Labels:
  overclaimed_scope — thesis generalizes beyond its evidence envelope
  missing_mechanism — describes WHAT without the causal HOW
  missing_counterfactual — does not canvass rival explanations
  parameter_sensitivity — numerical threshold / bound set empirically without derivation
  unfalsifiable_claim — no operational test / no discriminator
  missing_baseline — no baseline for comparison
  unmeasurable_construct — definition is not operationalizable
  temporal_mismatch — time-scale issue (short window, wrong regime, asymptotic confusion)
  definition_ambiguity — ambiguous / self-referential definition
  overclaimed_exclusivity — claims uniqueness without proof of exhaustiveness
  missing_derivation — missing formal mathematical derivation of a specific step
  non_identifiability — parameters not identified by the evidence
  unsupported_assumption — a specific assumption asserted without support
  catastrophic_fit_failure — the fit fails on a specific critical test case
  other — none of the above fits

Return ONLY the label, lowercase, no punctuation, no explanation.

WEAKEST POINT:
{weakest_point}

LABEL:"""


def sample_records() -> list[dict]:
    random.seed(RANDOM_SEED)
    records = []
    with ARCHIVE.open() as f:
        for line in f:
            r = json.loads(line)
            wp = r.get("weakest_point")
            if wp and len(wp.strip()) > 20:  # non-trivial
                records.append(r)
    # Stratify
    high = [r for r in records if isinstance(r.get("score"), (int, float)) and r["score"] >= 85]
    mid = [r for r in records if isinstance(r.get("score"), (int, float)) and 60 <= r["score"] < 85]
    low = [r for r in records if isinstance(r.get("score"), (int, float)) and r["score"] < 60]
    # Take equal strata; fill with remaining if bucket too small
    n_per = N_SAMPLE // 3
    chosen = (
        random.sample(high, min(n_per, len(high)))
        + random.sample(mid, min(n_per, len(mid)))
        + random.sample(low, min(n_per + (N_SAMPLE - 3 * n_per), len(low)))
    )
    random.shuffle(chosen)
    return chosen[:N_SAMPLE]


# --------------------- OpenAI provider ---------------------

def classify_openai(weakest_point: str) -> str:
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = CLASSIFIER_PROMPT.format(weakest_point=weakest_point[:400])
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20,
        temperature=0,
    )
    label = resp.choices[0].message.content.strip().lower().split()[0] if resp.choices[0].message.content else "other"
    return label if label in LABEL_SET else "other"


# --------------------- Anthropic provider ---------------------

def classify_anthropic(weakest_point: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = CLASSIFIER_PROMPT.format(weakest_point=weakest_point[:400])
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )
    content = resp.content[0].text if resp.content else ""
    label = content.strip().lower().split()[0] if content else "other"
    return label if label in LABEL_SET else "other"


# --------------------- Google provider ---------------------

def classify_gemini(weakest_point: str) -> str:
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = CLASSIFIER_PROMPT.format(weakest_point=weakest_point[:400])
    resp = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=prompt,
    )
    text = (resp.text or "").strip().lower().split()[0] if resp.text else "other"
    return text if text in LABEL_SET else "other"


PROVIDERS = {
    "openai_gpt-4.1-mini": classify_openai,
    "anthropic_claude-haiku-4.5": classify_anthropic,
    "google_gemini-3.1-flash-lite": classify_gemini,
}


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """Cohen's kappa between two raters on categorical labels."""
    if len(labels_a) != len(labels_b) or not labels_a:
        return 0.0
    n = len(labels_a)
    # Observed agreement
    po = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    # Expected agreement assuming independent marginals
    ca = Counter(labels_a)
    cb = Counter(labels_b)
    pe = sum((ca[x] / n) * (cb[x] / n) for x in set(ca) | set(cb))
    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def main() -> None:
    missing = [k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY") if not os.environ.get(k)]
    if missing:
        print(f"ERROR: missing env vars: {missing}", file=sys.stderr)
        print(f"Set them with: export VAR='...' (from a newly-issued key; never paste into chat)", file=sys.stderr)
        sys.exit(1)

    records = sample_records()
    print(f"Sampled {len(records)} records; classifying under {len(PROVIDERS)} providers...")

    all_labels: dict[str, list[str]] = {p: [] for p in PROVIDERS}
    per_record: list[dict] = []

    for i, r in enumerate(records):
        wp = r.get("weakest_point", "")
        labels_for_record = {}
        for provider_name, fn in PROVIDERS.items():
            try:
                label = fn(wp)
            except Exception as e:
                print(f"  [{i:>3}] {provider_name} ERROR: {e}", file=sys.stderr)
                label = "other"
            labels_for_record[provider_name] = label
            all_labels[provider_name].append(label)
            time.sleep(0.1)  # gentle rate limit
        all_agree = len(set(labels_for_record.values())) == 1
        per_record.append({
            "project": r.get("project"),
            "iter_timestamp": r.get("iter_timestamp"),
            "score": r.get("score"),
            "weakest_point_snippet": wp[:200],
            "labels": labels_for_record,
            "all_agree": all_agree,
        })
        if (i + 1) % 10 == 0:
            print(f"  progress: {i+1}/{len(records)}")

    # Pairwise kappa + three-way agreement
    provider_names = list(PROVIDERS.keys())
    pairwise_kappa = {}
    for i, p1 in enumerate(provider_names):
        for p2 in provider_names[i + 1:]:
            k = cohens_kappa(all_labels[p1], all_labels[p2])
            pairwise_kappa[f"{p1}__{p2}"] = round(k, 3)

    three_way_agree = sum(1 for rec in per_record if rec["all_agree"])
    three_way_rate = three_way_agree / max(len(per_record), 1)

    # Per-class stability (for classes where all 3 providers labeled at least once)
    per_class_stability: dict[str, dict] = {}
    for label in LABEL_SET:
        in_any = [rec for rec in per_record if label in rec["labels"].values()]
        if not in_any:
            continue
        all_3 = sum(1 for rec in in_any if all(l == label for l in rec["labels"].values()))
        per_class_stability[label] = {
            "n_at_least_one": len(in_any),
            "n_three_way_agreement": all_3,
            "stability_rate": round(all_3 / len(in_any), 3),
        }

    out = {
        "generated": str(date.today()),
        "n_sampled": len(records),
        "providers": provider_names,
        "random_seed": RANDOM_SEED,
        "pairwise_kappa": pairwise_kappa,
        "three_way_agreement_count": three_way_agree,
        "three_way_agreement_rate": round(three_way_rate, 3),
        "per_class_stability": per_class_stability,
        "verdict_band": (
            "robust_taxonomy (>=0.80)" if three_way_rate >= 0.80
            else "partially_robust (0.60-0.80)" if three_way_rate >= 0.60
            else "FAILS_cross_llm_validation (<0.60)"
        ),
        "records": per_record,
    }

    out_path = OUT / f"cross_provider_classifier_agreement_{date.today()}.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")
    print(f"three-way agreement rate: {three_way_rate:.1%}")
    print(f"verdict band: {out['verdict_band']}")
    print(f"pairwise kappa:")
    for k, v in pairwise_kappa.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
