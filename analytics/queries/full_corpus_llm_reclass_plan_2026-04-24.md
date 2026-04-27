# Full-Corpus LLM Reclassification — Scoping Plan

**Date:** 2026-04-24
**Author:** bounded read + limited-write scoping pass
**Target script:** `scripts/mine_weakest_link_llm_classify.py` (extend, do NOT replace)
**Target source:** `analytics/trajectory_archive_enriched.jsonl` (refreshed today, 1,859 records, 1,748 with `weakest_point`)
**Prior LLM run:** `analytics/queries/weakest_link_llm_subclasses_2026-04-24.json` (842 classified from the `other_unclustered` keyword-fingerprint bucket, 118 emergent categories)

---

## 1. Problem statement

The current pipeline is two-stage:

1. **Stage 2 (keyword fingerprint)** — `weakest_link_clusters_2026-04-24.json`. Regex/keyword matches labeled ~54% of records; the remaining 842 fell into `other_unclustered`.
2. **Stage 3 lite (LLM)** — `mine_weakest_link_llm_classify.py` only loaded the 842 `other_unclustered` members and asked gpt-4.1-mini to emergent-label them into 118 snake_case categories.

**Goal now:** extend LLM labeling to the **full corpus** (not just unclustered) so the taxonomy is uniform, then treat LLM labels as the authoritative layer that overrides regex matches.

---

## 2. Cost estimate (gpt-4.1-mini)

Pricing (from `supervisor/model_pricing.json`): input $0.40/M, output $1.60/M.

Assumptions:
- Current `weakest_point` mean length ≈ 315 chars, median ≈ 290 chars. Script already truncates to 300 chars per item (`r['weakest_point'][:300]`).
- 300 chars ≈ ~75 tokens per item.
- Batch of 20 items: ~1,500 item tokens + ~400 tokens system/user prompt overhead ≈ **1,900 input tokens/batch**.
- Output ≈ 40 tokens per item × 20 = **800 output tokens/batch**.

| Scope | Records (N) | Batches (N/20) | Input tok | Output tok | Input $ | Output $ | **Total $** |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full reclassify all records with wp | 1,748 | 88 | 167,200 | 70,400 | 0.067 | 0.113 | **$0.18** |
| Incremental (only the ~906 never-LLM-seen) | 906 | 46 | 87,400 | 36,800 | 0.035 | 0.059 | **$0.094** |
| All records minus already-labeled 842 | 1,017 | 51 | 96,900 | 40,800 | 0.039 | 0.065 | **$0.10** |

All three scopes are under **$0.20** — cost is not the binding constraint. The recommended scope is **incremental** (second row): classify only records the LLM hasn't seen, preserve the 842 existing labels from the 2026-04-24 run.

Safety buffer: budget **$0.50** to cover prompt overhead drift, retries on parse failures, and the inevitable few wp strings that exceed 300-char truncation after we raise the cap.

---

## 3. Batching & rate-limit strategy

- **Batch size:** keep `BATCH_SIZE = 20` (matches existing script; well within gpt-4.1-mini's 4,000-output-token ceiling).
- **Parallelism:** 4 concurrent requests via `concurrent.futures.ThreadPoolExecutor`. gpt-4.1-mini Tier-1 default RPM (500) and TPM (200k) comfortably accommodate 4-way at this volume.
- **Retry:** wrap `classify_batch` with exponential backoff on `openai.RateLimitError` / `APIError` (3 retries, base=2s). Current script silently drops parse failures — upgrade to one retry with a stricter "Return ONLY JSON" reminder before dropping.
- **Checkpoint:** the script already has `_load_checkpoint` / `_append_checkpoint` with a `.checkpoint.jsonl` sidecar. Keep this; it is the crash-safety + deduplication mechanism.

---

## 4. How to preserve the existing 842 LLM labels (override regex)

The critical requirement: **LLM labels are authoritative; regex labels are fallback.** Two concrete mechanisms:

### 4.1 Feed the existing checkpoint forward

The existing 842 records live in `weakest_link_llm_subclasses_2026-04-24.json` under `categories[*].members`. Before the new run starts:

```python
prior = json.load(open("analytics/queries/weakest_link_llm_subclasses_2026-04-24.json"))
seen = {}
for cat in prior["categories"]:
    for proj, ts in cat["members"]:
        seen[(proj, ts)] = {"category": cat["category"], "source": "prior_run_2026-04-24"}
```

Seed `CHECKPOINT_PATH` with these 842 records before the main loop, so `unclassified = [r for r in batch if (r["project"], r["iter_ts"]) not in checkpoint]` correctly skips them. This is already the script's idiom — no new logic needed, just a seeding step.

### 4.2 Change the input source

Current `load_unclustered()` only pulls the `other_unclustered` bucket. Refactor to `load_all_with_weakest_point()`:

```python
def load_all_with_wp():
    out = []
    with open(ARCHIVE_PATH) as f:
        for line in f:
            r = json.loads(line)
            wp = r.get("weakest_point", "")
            if wp:
                out.append({"project": r["project"], "iter_ts": r["iter_timestamp"], "weakest_point": wp})
    return out
```

The checkpoint seeding from §4.1 ensures the 842 already-labeled records don't consume new API calls.

### 4.3 Merge convention in downstream artifact

When writing the output JSON, tag each record with `source ∈ {"llm_2026-04-24", "llm_full_corpus_YYYY-MM-DD"}` so downstream consumers can trace label provenance. Regex labels from `weakest_link_clusters_2026-04-24.json` become **strictly fallback** — used only for records where the LLM returns `unknown` or a parse error persists.

---

## 5. Expected end-to-end runtime

Incremental scope, 46 batches:
- **Sequential** (current script design): 46 × ~3s/call = **~2.3 minutes**
- **4-way parallel** (recommended): 46 / 4 × ~3s = **~35 seconds**

Add ~10s for checkpoint seeding + final aggregation. Full wall clock with parallelism: **under 1 minute**.

The bottleneck is not compute — it's the emergent-category post-processing. After classification, expect to spend ~10 minutes manually reviewing categories with N<10 (script already flags these as `insufficient`). Taxonomy stability: the doc warns this is non-deterministic; a second run for stability check costs another $0.10 — worth doing.

---

## 6. Operator-action requirements

1. **`OPENAI_API_KEY`** must be set in the shell environment (script reads `os.environ.get("OPENAI_API_KEY")`).
2. **OpenAI Tier 1+** (≥500 RPM for gpt-4.1-mini). Any active OpenAI account is fine; the run consumes ~50 requests total.
3. **Disk space:** negligible; output JSON + checkpoint = < 2 MB.
4. **Pre-run seeding step:** operator or script author must copy prior LLM labels into `{OUTPUT_PATH}.checkpoint.jsonl` before `main()` runs, OR the refactored script must do it internally (preferred — less footgun).
5. **Budget cap:** set `MAX_BATCHES = 100` constant in the script as a hard guard against runaway if a bug causes infinite retries.
6. **Dry-run mode:** add `--dry-run` flag that reports batch count + token estimate without calling the API. Run this first before any real spend.

---

## 7. Open questions / decisions for operator

- **Taxonomy stability:** the 2026-04-24 run produced 118 categories from 842 records (1 category per ~7 records) — likely over-fragmented. Should the new run include the existing 118 categories as a **hint list** in the system prompt to encourage reuse? This tightens taxonomy but biases toward first-run labels.
- **Truncation cap:** 300 chars drops ~40% of records' wp text. Raising to 600 chars doubles input tokens (~$0.07 extra) but may catch nuance. Recommend 500 chars as the compromise.
- **Audit sample:** before trusting full-corpus labels, spot-check 50 random records (operator-manual) against the LLM label. At 94% agreement threshold, ship. At <90%, redesign the prompt.

---

## 8. Recommended execution order (NOT executed in this scoping pass)

1. Add `--dry-run` flag + checkpoint-seeding to script.
2. Run dry-run; confirm N=906, batches=46, est. cost ~$0.09.
3. Run actual, 4-way parallel; wall ~1 min, actual cost ~$0.10.
4. Second run for stability diff; cost ~$0.10.
5. Merge final taxonomy: LLM labels authoritative, regex fallback only for `unknown` residual.
6. Write `weakest_link_llm_full_corpus_YYYY-MM-DD.json`; preserve 2026-04-24 output untouched for provenance.
