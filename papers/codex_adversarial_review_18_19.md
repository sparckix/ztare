# Codex adversarial review of papers #18 + #19

Model: gpt-5.5
Returncode: 0

## Output

do-not-cite

**Paper 1: Failure Atlas**

1. **Core evidence overstates model-family independence.** §2 lists `claude`, `codex-gpt-5.5`, and `codex-gpt-5.4-mini` as the trio ([paper_draft_v1.md](/Users/daalami/figs_activist_loop/papers/failure_mode_atlas/paper_draft_v1.md:42)). §3.1 then calls F12 “three independent model families” ([line 72](/Users/daalami/figs_activist_loop/papers/failure_mode_atlas/paper_draft_v1.md:72)). Two are Codex variants. That makes the sign-consistency claim materially weaker.

2. **The abstract overclaims uniform evidentiary structure.** It says five findings each have “measured effect size, sample size, sign consistency across model families” ([line 12](/Users/daalami/figs_activist_loop/papers/failure_mode_atlas/paper_draft_v1.md:12)). F14 is a diagnostic confound warning, not a measured failure ([lines 87-97](/Users/daalami/figs_activist_loop/papers/failure_mode_atlas/paper_draft_v1.md:87)); F23 is structural reconciliation, “not a quantitative claim” ([line 160](/Users/daalami/figs_activist_loop/papers/failure_mode_atlas/paper_draft_v1.md:160)). The abstract is false as written.

3. **Cherry-picking risk is acknowledged but not neutralized.** The paper says positives exist in the same program ([lines 26, 170-172](/Users/daalami/figs_activist_loop/papers/failure_mode_atlas/paper_draft_v1.md:26)), but the atlas gives no selection rule for why these negatives, and not other negatives/positives, enter. “Honest negatives” is a label, not a sampling protocol.

4. **F19/F22 causal interpretation is too strong for the reported evidence.** §3.3 reports pooled Δ Brier +0.009 and pair-level anecdotes, but no CI, paired test, per-pair table, or correction for six directional comparisons ([lines 99-104](/Users/daalami/figs_activist_loop/papers/failure_mode_atlas/paper_draft_v1.md:99)). The operational recommendation “Do not deploy rationale-exchange ensembles” ([line 107](/Users/daalami/figs_activist_loop/papers/failure_mode_atlas/paper_draft_v1.md:107)) outruns a single protocol.

5. **Reproducibility claim is inflated.** §1.2 calls this “reproducibility-grade” ([line 30](/Users/daalami/figs_activist_loop/papers/failure_mode_atlas/paper_draft_v1.md:30)), but §5 admits no third-party blinded corpus replication, no open-weights/reasoning-class replication, wide CIs, and no prompt-variation stability ([lines 178-184](/Users/daalami/figs_activist_loop/papers/failure_mode_atlas/paper_draft_v1.md:178)). That is internal audit-grade, not citation-grade reproducibility.

do-not-cite

**Paper 2: Apparatus Testbed**

1. **“Reproducible testbed” is premature.** §5.6 admits every claim is internal to one operator and ZTARE-bench has no second-lab submission yet ([lines 394-398](/Users/daalami/figs_activist_loop/papers/apparatus_testbed/paper_draft_v1.md:394)). That directly undercuts the title and abstract’s testbed framing ([lines 14-24](/Users/daalami/figs_activist_loop/papers/apparatus_testbed/paper_draft_v1.md:14)).

2. **Basic enumeration error in the abstract.** It says “five components” but lists six: schema, scorer, pre-fire audit, checkpointing, agent aggregation, meta-Darwin ([lines 18-22](/Users/daalami/figs_activist_loop/papers/apparatus_testbed/paper_draft_v1.md:18)). This is small, but in a methodology paper it signals sloppy framing.

3. **Ground-truth blindness is overclaimed.** §4.3 says read-blindness is “enforceable mechanically” ([lines 319-326](/Users/daalami/figs_activist_loop/papers/apparatus_testbed/paper_draft_v1.md:319)), but §1 already admits dispatcher authors can leak GT via prompt wording, contract selection, and exclusion rules ([lines 58-62](/Users/daalami/figs_activist_loop/papers/apparatus_testbed/paper_draft_v1.md:58)). Static path scans and `chmod 000` do not solve author-level selection leakage.

4. **The external submission story is not actually external-ready.** The paper exposes a local operator filesystem path (`/Users/daalami/...`) as the testbed location ([lines 81-84](/Users/daalami/figs_activist_loop/papers/apparatus_testbed/paper_draft_v1.md:81)) and asks labs to clone/vendor internal paths and rituals ([lines 292-317](/Users/daalami/figs_activist_loop/papers/apparatus_testbed/paper_draft_v1.md:292)). That is not yet a packaged benchmark.

5. **Findings are used as scale evidence despite explicit non-results framing.** The draft says it is “not a results paper” ([lines 3-4](/Users/daalami/figs_activist_loop/papers/apparatus_testbed/paper_draft_v1.md:3)), then relies on “~13 pilots,” “~3500 calls,” and “24 findings” as evidence the apparatus scales ([lines 231-267](/Users/daalami/figs_activist_loop/papers/apparatus_testbed/paper_draft_v1.md:231)). Without independent replication, those numbers show internal throughput, not methodological validity.

