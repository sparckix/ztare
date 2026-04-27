# Cross-Provider LLM Classifier Agreement Test — Plan

**Created:** 2026-04-24
**Motivation:** stratified judge analysis confirmed the Oracle Illusion at the JUDGE layer (same thesis scores differently under different judges). A separate question: is my CLASSIFIER (gpt-4.1-mini regex+LLM taxonomy on weakest-points) ALSO LLM-aesthetic-specific?

If a weakest-point that gpt-4.1-mini labels `missing_mechanism` gets labeled differently (e.g., `unverified_bound`) by claude-haiku and gemini-flash-lite, the 15-class taxonomy is LLM-specific and downstream mining is compromised. If they agree, the taxonomy is robust.

## Method

1. **Sample 100 weakest-point records** uniformly at random from `analytics/trajectory_archive_enriched.jsonl`. Stratify by score bucket (33 low, 33 mid, 34 high) to cover distribution shape. Fix seed for reproducibility.
2. **Classify each record under three providers** with identical 15-class label list + identical system prompt structure:
   - OpenAI gpt-4.1-mini (existing classifier; baseline)
   - Anthropic claude-haiku-4.5 (second provider; check OpenAI-specific bias)
   - Google gemini-3.1-flash-lite-preview (third provider; check US-vs-non-US training bias)
3. **Compute pairwise agreement:**
   - Cohen's κ per provider pair
   - Confusion matrices for most-common classes
   - Per-record disagreement rate
4. **Compute per-class stability:**
   - For each of the 15 classes, how often do all 3 providers agree that label applies?
   - Classes with <70% three-way agreement are LLM-specific aesthetic, not structural.

## Cost estimate

At ~500 tokens prompt + ~30 tokens response per classification:
- gpt-4.1-mini: 100 × 530 × ($0.4/M in + $1.6/M out) = ~$0.08
- claude-haiku-4.5 (est $1/M in, $5/M out): 100 × 530 × ~$0.27
- gemini-3.1-flash-lite (est $0.1/M in, $0.4/M out): 100 × 530 × ~$0.02

**Total: under $0.40 for the full 3-provider run.**

## Runtime

~2-3 minutes per provider at typical rate limits. ~10 minutes wall clock including setup.

## Output

Script: `scripts/mine_cross_provider_classifier_agreement.py` (to be written)
Output: `analytics/queries/cross_provider_classifier_agreement_<date>.json`

Report shape:
```json
{
  "generated": "...",
  "n_records": 100,
  "providers": ["gpt-4.1-mini", "claude-haiku-4.5", "gemini-3.1-flash-lite-preview"],
  "pairwise_kappa": {"gpt4.1mini_claudehaiku": 0.xx, ...},
  "three_way_agreement_rate": 0.xx,
  "per_class_stability": {
    "overclaimed_scope": {"three_way_agree": 0.xx, "sample_n": xx},
    ...
  },
  "records": [{"record_id": "...", "weakest_point_snippet": "...",
               "labels": {"gpt4.1mini": "x", "claudehaiku": "y", "gemini": "z"},
               "all_agree": true/false}]
}
```

## Operator requirements

- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` exported in shell (never pasted in chat)
- Network access for all three providers
- ~10 min wall time

## Decision criteria after the run

- **If three-way agreement rate ≥ 80%:** taxonomy is robust. Current mining-derived conclusions stand. The LLM classifier is not meaningfully LLM-aesthetic-biased.
- **If agreement rate 60–80%:** taxonomy is partially robust. Classes with <70% individual stability flagged as LLM-specific and demoted from universal-intervention recommendations.
- **If agreement rate < 60%:** taxonomy fails cross-LLM validation. All downstream mining findings should be re-examined.

## Why this matters in context

Stratified judge analysis showed:
- Structural blockers (lift 0.00 under every judge) are universally bad → cross-JUDGE validated
- Ceiling-breakers show direction flips between judges → JUDGE-specific

If the cross-provider classifier test ALSO shows disagreement on ceiling-breaker labels, we have TWO layers of aesthetic bias compounding: the judge's critique vocabulary AND the classifier's interpretation of that vocabulary.

The $0.40 spend here is risk mitigation before promoting any mining-derived heuristic to kernel default.

## Next action

Operator approves → another agent (or operator) implements `mine_cross_provider_classifier_agreement.py` and runs with the three API keys set in env. Report lands at the specified path.
