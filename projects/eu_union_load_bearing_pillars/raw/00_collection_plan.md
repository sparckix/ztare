---
source_type: collection_todo
---

# EU Load-Bearing Pillars: Evidence Collection Plan

Current blocker from the latest baseline:

- the thesis still hard-fails as self-reference because the thresholds for:
  - `functionally material` fiscal capacity
  - `reduced recurrent constitutional contestation`
  are not independently grounded outside the thesis's own ontology

So the next evidence pass should target externally grounded threshold material, not more prose defending the ontology.

## Priority source classes

1. Evidence on what counts as materially meaningful central fiscal stabilization in established federations
   - comparative federal budget size
   - automatic stabilizer capacity
   - fiscal transfer intensity during asymmetric shocks
   - why specific scales are or are not considered materially stabilizing

2. Evidence on legal supremacy consolidation in established federations
   - indicators of uncontested versus contested supremacy
   - recurring constitutional challenge frequency or severity
   - how comparative federal systems distinguish normal legal disagreement from persistent supremacy contestation

3. Comparative cases that stress-test the EU ontology
   - cases where discretionary resilience might still be treated as equilibrium
   - cases where standing federal mechanisms clearly existed and can anchor the Mode DE boundary

## What to add into `raw/`

Add small `.md` or `.txt` source notes, one file per source, with:

```md
---
source_type: source_evidence
---

Title: ...
URL: ...
Date: ...

Claim / relevance:
- ...

Key facts / excerpts:
- ...
- ...

Why this matters for the thesis:
- ...
```

Important:

- `compile_evidence.py` does not ingest PDFs directly
- if the source is a PDF or webpage, extract the relevant text into markdown or text first
- keep one source per file so provenance stays clean

## First concrete targets

- one source grounding fiscal stabilization scale in a mature federation
- one source grounding legal supremacy consolidation / contestation in a mature federation
- one comparator source testing whether discretionary resilience can still count as equilibrium
