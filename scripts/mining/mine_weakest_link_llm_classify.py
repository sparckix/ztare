"""GP-148 Stage 3 lite: LLM classifier for unclustered weakest-point strings.

PURPOSE: The Stage 2 keyword-fingerprint taxonomy left 842 records (46%) in the
'other_unclustered' bucket. This script sends batches of unclustered weakest_point
strings to gpt-4.1-mini for classification into finer sub-categories. The taxonomy
is emergent — the LLM proposes category names from the data, then the script
deduplicates and consolidates.

METHODOLOGY: Batch classification with gpt-4.1-mini. Each batch of 20 weakest_point
strings is sent with a system prompt requiring: (a) a snake_case category name,
(b) a one-line description. Post-LLM: aggregate by category name, count members,
emit per-category summary with exemplars.

KNOWN LIMITATIONS: LLM classification is non-deterministic. Run twice and diff
to estimate stability. Categories with N<5 should be treated as noise. The LLM
may hallucinate categories that don't match the data — spot-check exemplars.
Cost estimate: ~842 records / 20 per batch = ~42 API calls to gpt-4.1-mini.
"""

import json
import os
import sys
import time
from pathlib import Path

# Use the project's LLM routing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ARCHIVE_PATH = "analytics/trajectory_archive_enriched.jsonl"
CLUSTERS_PATH = "analytics/queries/weakest_link_clusters_2026-04-24.json"
OUTPUT_PATH = f"analytics/queries/weakest_link_llm_subclasses_{time.strftime('%Y-%m-%d')}.json"

BATCH_SIZE = 20


def load_unclustered():
    """Join unclustered members back to archive for weakest_point text."""
    archive = {}
    with open(ARCHIVE_PATH) as f:
        for line in f:
            r = json.loads(line)
            archive[(r["project"], r["iter_timestamp"])] = r.get("weakest_point", "")

    with open(CLUSTERS_PATH) as f:
        data = json.load(f)

    for c in data["clusters"]:
        if c["cluster_id"] == "other_unclustered":
            records = []
            for proj, ts in c["members"]:
                wp = archive.get((proj, ts), "")
                if wp:
                    records.append({"project": proj, "iter_ts": ts, "weakest_point": wp})
            return records
    return []


def classify_batch(batch, model="gpt-4.1-mini"):
    """Send a batch of weakest_point strings to the LLM for classification."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    items_text = "\n".join(
        f"[{i}] {r['weakest_point'][:300]}" for i, r in enumerate(batch)
    )

    prompt = f"""You are classifying failure modes from an automated research engine.

Each numbered item below is a "weakest point" critique of a thesis. Classify each into
exactly ONE failure category using a short snake_case label.

Categories should describe the EPISTEMIC failure, not the domain. Good examples:
- unmeasurable_construct: critique says a key variable can't be measured
- missing_mechanism: critique says the thesis has no causal pathway
- definition_ambiguity: critique says a key term is undefined
- temporal_mismatch: critique says the timescale is wrong
- missing_counterfactual: critique says no alternative was tested
- overclaimed_scope: critique says the claim exceeds the evidence
- parameter_sensitivity: critique says results depend on untested parameters
- missing_baseline: critique says no null comparison exists
- unfalsifiable_claim: critique says the thesis can't be disproved

You may reuse these or invent new ones if needed. Be specific. Avoid generic labels.

ITEMS:
{items_text}

Respond with a JSON array of objects, one per item:
[{{"index": 0, "category": "snake_case_label", "reason": "one line why"}}]

Return ONLY the JSON array, no markdown fencing."""

    response_obj = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a research methodology classifier. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=4000,
    )
    response = response_obj.choices[0].message.content

    # Parse response
    text = response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"  WARNING: Failed to parse LLM response, skipping batch")
        return []


CHECKPOINT_PATH = OUTPUT_PATH + ".checkpoint.jsonl"


def _load_checkpoint():
    """Load previously classified records from checkpoint file."""
    done = {}
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH) as f:
            for line in f:
                r = json.loads(line)
                done[(r["project"], r["iter_ts"])] = r
        print(f"  Loaded {len(done)} from checkpoint")
    return done


def _append_checkpoint(records):
    """Append newly classified records to checkpoint file (crash-safe)."""
    with open(CHECKPOINT_PATH, "a") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def main():
    records = load_unclustered()
    print(f"Loaded {len(records)} unclustered records")

    checkpoint = _load_checkpoint()
    all_classifications = list(checkpoint.values())
    n_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        # Skip batches where all members are already classified
        unclassified = [r for r in batch if (r["project"], r["iter_ts"]) not in checkpoint]
        if not unclassified:
            print(f"  Batch {batch_num}/{n_batches} — already in checkpoint, skipping")
            continue

        print(f"  Batch {batch_num}/{n_batches} ({len(batch)} items, {len(unclassified)} new)...", end="", flush=True)
        results = classify_batch(batch)
        print(f" got {len(results)} classifications")

        new_records = []
        for r in results:
            idx = r.get("index", 0)
            if 0 <= idx < len(batch):
                key = (batch[idx]["project"], batch[idx]["iter_ts"])
                if key not in checkpoint:
                    rec = {
                        "project": batch[idx]["project"],
                        "iter_ts": batch[idx]["iter_ts"],
                        "category": r.get("category", "unknown"),
                        "reason": r.get("reason", ""),
                        "weakest_point_preview": batch[idx]["weakest_point"][:200],
                    }
                    new_records.append(rec)
                    all_classifications.append(rec)
                    checkpoint[key] = rec

        if new_records:
            _append_checkpoint(new_records)

    # Aggregate by category
    from collections import Counter, defaultdict

    cat_counts = Counter(c["category"] for c in all_classifications)
    cat_members = defaultdict(list)
    for c in all_classifications:
        cat_members[c["category"]].append(c)

    categories = []
    for cat, count in cat_counts.most_common():
        members = cat_members[cat]
        categories.append({
            "category": cat,
            "size": count,
            "project_count": len(set(m["project"] for m in members)),
            "exemplars": [m["weakest_point_preview"] for m in members[:3]],
            "members": [[m["project"], m["iter_ts"]] for m in members],
            "confidence": "sufficient" if count >= 10 else "insufficient (N<10)",
        })

    output = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": CLUSTERS_PATH,
        "total_classified": len(all_classifications),
        "total_input": len(records),
        "model": "gpt-4.1-mini",
        "category_count": len(categories),
        "categories": categories,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote {OUTPUT_PATH}")
    print(f"  {len(categories)} categories, {len(all_classifications)} classified")
    print(f"\nTop 10:")
    for c in categories[:10]:
        print(f"  {c['category']:40s} {c['size']:>4d} ({c['project_count']} projects) [{c['confidence']}]")


if __name__ == "__main__":
    main()
