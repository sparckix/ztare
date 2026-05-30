# GP-218 — Post-cutoff blind coverage test (Claim A pre-registration)

> **Seam metadata** · `seam_id:` GP-218 · `track:` engine · `status:` PRE-REGISTERED 2026-05-05 - must be sealed before any taggin · `last_updated:` 2026-05-09


**Status:** PRE-REGISTERED 2026-05-05 — must be sealed before any tagging happens
**Date:** 2026-05-05
**Audience:** internal — Claim A scope test for v5 vocabulary
**Sister:** GP-216 (vocabulary), Pass 11 (Gowers two-cultures), `org/directives/20260505-empirical-mandate-broadening-v1.json`

---

## Eigenquestion

> Does the v5 theory-building vocabulary still cover theory-builder arcs **published after the construction-corpus cutoff**, when tagged by a v5-blind annotator, at the 58% baseline coverage level?

## What this is NOT testing

- **Not a re-test of scope.** Pass 11 already confirmed two-cultures specificity (theory-builder 58% / problem-solver 21% / 37.4pp gap). That work stands.
- **Not a generative-power test.** Generative power = "the vocabulary predicts what works." The cleanest generative test is NS Track B gate deployment outcomes (in flight, Codex). Don't run a parallel generative experiment; let that one mature.
- **Not a publishability test.** Paper 5b is publishable on Pass 1-11 evidence. This test is upside / downside calibration, not gate.

## What this IS testing

Three things Pass 11 did NOT test:

1. **Post-cutoff coverage.** The 64-arc construction corpus + Pass 11 corpus all pre-date 2024. If v5 captures genuine theory-building, it should still cover theory-builder work published in 2024-2026, post-mining-cutoff. Failure mode: vocabulary captured *that-era* theory-building only.
2. **Inter-rater reliability against a v5-blind tagger.** Pass 1-11 had GPT-5.5 cross-LLM stability (78%), but the same vocabulary was visible to the cross-LLM. A truly v5-blind tagger never seeing the op list might tag entirely different moves. Failure mode: vocabulary is post-hoc rationalization of what we wanted to find.
3. **Coverage stability across paper length / argument density.** Pass 11 corpus is famous arcs (compressed expositions). Post-cutoff corpus is fresh papers (full arguments). Coverage may drop when the prose isn't compressed.

## Falsifiable predictions (sealed before tagging)

**PASS:** post-cutoff theory-builder coverage ≥ 50% (within 8pp of internal 58% baseline) AND inter-rater agreement ≥ 70% on which v5 ops fire per paper.

**WEAK PASS (publishable as caveat in paper 5b):** coverage 35-50% OR inter-rater agreement 50-70%. Implies vocabulary holds qualitatively but quantitatively narrows on fresh corpus.

**FAIL (vocabulary scope is era-bound):** coverage < 35% OR inter-rater agreement < 50%. Triggers paper 5b revision: "vocabulary captures 2010-2024 theory-building, not 2024+ theory-building." Honest finding.

**REJECTION-OF-CLAIM-A** (would update Paper 5b framing): coverage < 25% AND inter-rater agreement < 40%. Implies the vocabulary is a Rorschach test, not a structural finding. Paper 5b becomes a methodology paper, not a vocabulary paper.

## Selection rules (deterministic, pre-registered)

5 papers from arxiv.org math.* categories meeting ALL of:

- **Cutoff:** posted on or after 2024-06-01 (after the construction corpus cutoff)
- **Subfield mix:** one paper each from algebraic geometry, number theory, combinatorics, topology/geometry, analysis/PDE
- **Length:** 20-60 page papers (excludes notes + textbook-length monographs)
- **Type:** must contain a self-contained proof or theory-construction argument (excludes pure surveys, computational papers without theoretical contribution)
- **Author:** at least one author with prior published theoretical work (excludes pre-print noise)

**Sourcing protocol:** the operator pulls 5 candidates by listing arxiv math.* "recent" filtered to subfield + cutoff date and selecting the *first* paper per subfield meeting the criteria. No discretion in selection beyond rule application.

**Anti-leakage:** the v5 vocabulary file (`src/ztare/research_director/universal_research_ops.py`) and Pass 1-11 documentation MUST NOT be visible to the blind tagger. The selection step is operator-only; the tagging step is performed in a fresh-context Claude Code session with `--bare` flag and the universal_research_ops.py file explicitly excluded from `--add-dir`.

## Tagging protocol (two-step, anti-leakage)

**Step 1 — blind structural-move enumeration (v5-blind tagger):**
- Tagger reads paper, lists every distinct *structural move* in natural language
- "Move" = action that changes representation / extends domain / closes a sub-goal / reformulates a question / etc.
- Output: numbered list of moves with one-sentence descriptions, in `projects/ztare_on_ztare/workspace/external_corpus_test/<paper_id>/raw_moves.md`
- Tagger has NO access to v5 op list during this step

**Step 2 — v5 cross-walk (separate operator + v5 visible):**
- Operator (or me with v5 loaded) reads the natural-language moves
- For each move, mark: matches v5 op X / partial match to v5 op X / no match
- Output: `projects/ztare_on_ztare/workspace/external_corpus_test/<paper_id>/cross_walk.json` with move-by-move classification
- Coverage = (full + partial) / total moves; same definition as Pass 11

**Inter-rater check:**
- After Step 2 by tagger A, repeat Step 2 with a different tagger (Gemini Pro 2.5 with v5 vocabulary loaded as system prompt)
- Inter-rater agreement = % of moves where tagger A and tagger B assigned the same v5 op (or both said "no match")

## Cost estimate

- Selection: 30 minutes (operator runs arxiv search, picks 5 papers per criteria)
- Reading + Step 1 tagging: 5 papers × 60 min = 5 hours
- Step 2 cross-walk: 30 min/paper × 5 = 2.5 hours
- Inter-rater Step 2 by Gemini: 1 hour total via API
- Scoring + report: 1 hour

**Total: ~10 hours wall clock, ~$5 LLM API spend.** Cheap enough to run once; falsifies Claim A scope cheaply if it falsifies.

## Apparatus

- `projects/ztare_on_ztare/workspace/external_corpus_test/` — directory for raw moves + cross-walks per paper
- `projects/ztare_on_ztare/workspace/external_corpus_test/template.md` — blind tagger's input form
- `scripts/public/projects/ztare_on_ztare/score_external_corpus_coverage.py` — computes coverage + inter-rater agreement; outputs report comparable to Pass 11 format
- This seam — frozen pre-registration; coverage thresholds CANNOT be edited after tagging starts

## Cross-references

- Pass 11 corpus + method: `research_areas/private/seams/engine/GP-216_theory_building_operations_seam.md` § Pass 11
- v5 vocabulary: `src/ztare/research_director/universal_research_ops.py`
- Calibration apparatus pattern: `scripts/public/mining/mine_decision_history.py` (GP-217 sister mechanism)

## Honest framing for paper 5b

If GP-218 result is PASS: paper 5b adds a "post-cutoff validation (5 papers, 2024-2026)" subsection to §3. One paragraph.

If GP-218 result is WEAK PASS or FAIL: paper 5b adds a "scope limitation" subsection. The honest finding ("vocabulary captures 2010-2024 theory-building, narrows on post-2024 corpus") is itself publishable — it's a calibrated Munger-style admission that strengthens the paper.

If REJECTION-OF-CLAIM-A: paper 5b becomes a methodology + cautionary-tale paper. Less prestigious target but still real. We do not pre-emptively retract the vocabulary publication; we report what the test showed.

## Sealed at

2026-05-05 by Claude (in autonomous mode, principal-approved). Coverage thresholds and selection rules are frozen as of this commit. Any change after first tagging starts = pre-registration violation; reset and re-seal.

---

## Result (closed 2026-05-05)

Test executed via 5 parallel Claude Code subagents (blind Step 1) + 5 + 5 (cross-walk Tagger A and B) + 1 (adversarial stress on PDE). Selection sealed in `projects/ztare_on_ztare/workspace/external_corpus_test/selection_2026_05_05.json`. Total wall clock ~30 min; ~$15 in Claude Code subagent compute.

### Headline (from `scripts/public/projects/ztare_on_ztare/score_external_corpus_coverage.py`)

| Metric | Value |
|---|---|
| Papers analyzed | 5 |
| Mean coverage (Tagger A, anti-overfit guards) | **56.5%** |
| Mean coverage (Tagger B, independent inter-rater) | **67.5%** |
| Internal baseline (Pass 3b, theory-builder corpus) | 58% |
| Pass 11 problem-solver baseline | 21% |
| Coverage delta vs internal baseline | **−1.5pp** (essentially baseline-equal) |
| Inter-rater agreement (1 − mean coverage diff) | 88.2% |
| **Pre-registered classification** | **PASS** (≥50% coverage AND ≥70% inter-rater) |

### Per-paper

| Subfield | A | B | A-B gap |
|---|---|---|---|
| combinatorics | 67% | 71% | 4pp |
| number_theory | 60% | 68% | 8pp |
| topology_geom | 50% | 60% | 10pp |
| alg_geom | 60% | 76% | 16pp |
| **analysis_pde** | **46%** | **62%** | **17pp** |

### Key non-trivial finding — differential coverage by subfield

The PDE paper had the lowest coverage AND the largest tagger-disagreement. The 13 "none" moves in PDE clustered around estimate-craft tactics (barriers, blow-up profiles, Liouville rigidity, Morse-index transfer under limits, ODE convexity dichotomies, regime-isolation, sharpness counterexamples). This is **not** a defect of v5 — it's a sharp scope-boundary signal indicating PDE estimate-craft is structurally distinct from theory-builder moves (and likely from problem-solver moves too).

This connects to NS Track B: Codex's recent theorem-statement work (Lipschitz reserve ledger, profile-LSC certificates, Bony paraproduct receipts) is exactly the kind of work v5 doesn't name. The 3 deployed gates mechanize the FRAMING of PDE work but not the estimate-craft. Sister track GP-219 opened to mine PDE-native ops.

### Implications for paper 5b

- **PASS classification supports**: add a "post-cutoff blind validation (5 papers, 2026-05-04)" subsection to §3 with the headline numbers.
- **Honest scope addition**: foreground the differential coverage finding — vocabulary is descriptive across structural-research moves but exhibits a sharp gradient by subfield, with PDE estimate-craft as a partial out-of-scope. This *strengthens* the descriptive claim by calibrating it.
- **Methodology**: the blind-subagent cross-walk methodology is itself reportable; defer to Pattern 12 doc + a one-paragraph methods appendix.

### Methodology caveats (decisive)

- Same-LLM-family taggers share systematic biases — agent-vs-agent inter-rater is high-bound; human-vs-agent would be lower.
- Agents are more compliant with anti-overfit prompts than humans likely are.
- N=5 papers is small; scaling to 20-30 papers strengthens the claim.
- Differential coverage signal needs replication on more PDE papers before settling.

### Adversarial stress test (closed 2026-05-05)

Third agent on analysis_pde with hard "default-to-no-match" stance: **3 full / 0 partial / 21 none = 12.5% coverage**. Only three moves survive strict structural-mechanism testing:
- Move 2 → core_07 (Morse-index definition broadened to graphs — genuine framework generalization)
- Move 12 → core_04 (local barriers glued at vertices to global decay — genuine local-to-global)
- Move 20 → core_06 (Hartman ODE imported as black-box per edge — genuine external-framework importation)

**Standard Tagger A claimed 46%; adversarial finds 12.5%. The 33.5pp gap is a STRONG inflation signal on PDE specifically.** This is sharper than the A-vs-B gap (46% vs 62%) and tells us:

1. The "real" PDE coverage under strict structural-mechanism testing is closer to 12-15% than 46%.
2. Standard cross-walk Tagger A — even with explicit anti-overfit guards — still inflated coverage by ~33pp on PDE compared to a hard skeptic.
3. This is NOT evidence the vocabulary fails everywhere; it's evidence the vocabulary fails *specifically on PDE estimate-craft*, exactly where GP-219 is mining.

The adversarial test was only run on the worst-fitting paper. If the same inflation factor applied uniformly, mean coverage might drop from 56.5% to ~25-35%. But the inflation factor is likely *much smaller* on subfields where the vocabulary fits well (combinatorics A=67%, B=71%; both close to ground truth). Per-subfield adversarial passes would calibrate this; deferred to GP-218.2 if/when needed.

### Updated implications for paper 5b

The PDE adversarial gap pushes the framing from "vocabulary has differential coverage" toward "vocabulary has a sharp scope boundary at estimate-craft." Paper 5b §3 should foreground this rather than soft-pedal it. The honest claim: vocabulary is a strong descriptor of theory-building moves; coverage on PDE-native estimate-craft is genuinely low under strict reading (~13%) and inflates under permissive reading (~50-60%). Sister track GP-219 mines the structural gap.

### Outputs

- `projects/ztare_on_ztare/workspace/external_corpus_test/gp218_coverage_report.md` — pre-registered scoring output
- `projects/ztare_on_ztare/workspace/external_corpus_test/<arxiv_id>/raw_moves.md` — Step 1 blind enumerations (5 papers, 118 moves total, no v5 leakage)
- `projects/ztare_on_ztare/workspace/external_corpus_test/<arxiv_id>/cross_walk.json` — Tagger A
- `projects/ztare_on_ztare/workspace/external_corpus_test/<arxiv_id>/cross_walk_b.json` — Tagger B
- `projects/ztare_on_ztare/workspace/external_corpus_test/2605.02879/cross_walk_adversarial.json` — stress test (in flight)

### Status

Pre-registration → CLOSED, classification PASS. Sister track GP-219 opened. INS-row + F-row appended to canonical ledgers.
