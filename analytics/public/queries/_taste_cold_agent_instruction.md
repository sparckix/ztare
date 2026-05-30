Read the apparatus-artifact taste sample at:
    analytics/public/queries/taste/_taste_sample.md

Apply the following rubric and produce ratings:

Rate each sample 0-5 on insight density:
  0 = boilerplate, scaffolding, or restated apparatus state
  1 = trivially observable; doesn't change downstream reasoning
  2 = useful but expected; consolidates known
  3 = non-obvious finding or sharp framing; would help a future reader
  4 = surprising / load-bearing / mechanism-revealing
  5 = paradigm-shifting; reframes the problem or apparatus

For each sample, output exactly one line in this format:
  SAMPLE_NNN | <integer score 0-5> | <one-line rationale, ≤120 chars>

Output ONLY the rating lines. No preamble, no summary, no commentary.


Each sample is delimited by `## SAMPLE_NNN (kind)` followed by a code
block with the artifact content (truncated to 1.2KB).

Output your ratings to:
    analytics/public/queries/taste/_taste_ratings.md

In the exact format specified by the rubric — one line per sample,
no preamble, no commentary, no summary. Output 60 lines total
(SAMPLE_001 through SAMPLE_060).

You are deliberately a COLD agent here — you have no context from
this codebase's recent work. Score on the artifact text alone.
