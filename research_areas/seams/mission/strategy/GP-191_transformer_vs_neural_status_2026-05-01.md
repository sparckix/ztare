# GP-191 Transformer vs Neural Status

> **Seam metadata** · `seam_id:` GP-191 · `track:` mission · `status:` unrecorded · `last_updated:` 2026-05-08


Status: active note  
Recorded: 2026-05-01 11:18:00 EDT

## Do Not Mix These Projects

GP116B transformer successor and GP154 neural scaling are separate tracks.

- **GP116B transformer successor** asks: what architecture substrate points to
  the next post-transformer / residual-state direction?
- **GP154 neural scaling** asks: does the normalized power-law / axis-exponent
  law transfer to modern neural training curves?

If an agent says "116B needs W&B OLMo scraping", it is mixing tracks. The W&B
OLMo work is GP154 neural scaling, not GP116B transformer successor.

## GP116B Transformer Successor

Project paths:

- Acquisition/source rows: `projects/gp116_cot_exchange/`
- Runnable substrate: `projects/gp116b_transformer_successor/`
- Rubric: `rubrics/gp116b_transformer_successor.json`

Current acquired row state:

- `workspace/external_residual_state_rows.json` has 12 source-backed
  architecture rows from the earlier acquisition packet.
- The May 1 refresh command currently returns 9 rows plus 3 blockers:
  RetNet, HGRN2, and xLSTM evidence needles need repair/updating because the
  stricter scraper cannot re-confirm them from current public metadata.
- Do not delete the prior 12-row packet unless the stricter reacquisition
  replacement is fixed and reviewed.

Latest ZTARE result:

- Score after the hardened 3-iter run: `0`.
- Read: informative negative, not just "bad score".
- The gate says mechanism/architecture flags did not add generalizable
  predictive value for GP116 measured residual cancellation over
  constant/training-only rivals.
- Therefore the next transformer-successor move is not "rerun harder"; it is
  either fix the target framing to architecture discovery / diagnostic coverage
  or acquire direct comparable cancellation/rank/survival measurements for
  successor mechanisms.

Exact commands:

```bash
python3 projects/gp116_cot_exchange/acquire_external_residual_state_rows.py --timeout 30
python3 projects/gp116_cot_exchange/build_transformer_successor_substrate.py
make validate-rubric PROJECT=gp116b_transformer_successor RUBRIC=gp116b_transformer_successor PYTHON=./venv/bin/python3
make experiment-loop PROJECT=gp116b_transformer_successor RUBRIC=gp116b_transformer_successor ITERS=3 MUTATOR_MODEL=gpt5.5 JUDGE_MODEL=gpt4.1
```

But do not rerun the last command expecting a high score until the scientific
target is reframed or direct measurement rows are added.

## GP154 Neural / Power Law

Project path:

- `projects/gp154_scaling_law_normalized/`

Current acquired row state:

- OLMo2 7B Stage 1 train CE rows acquired.
- OLMo2 13B Stage 1 train CE rows acquired.
- OLMo2 1B Stage 1 exact train CE rows not acquired.
- OLMo2 1B GitHub config/checkpoint metadata acquired.
- OLMo2 1B posttraining SFT/DPO W&B rows acquired but excluded from clean
  Stage 1 packet because they are not pretraining CE.
- Report-scrape script exists but did not yet access the W&B report spec/history
  through GraphQL.

Current backtest:

- External OLMo packet MAE: `0.053515559403500064` over 11,728 rows.
- 13B slice: `0.049729591883822415`.
- 7B slice: `0.12157720850320673`.
- Current anomaly audit favors engineering/acquisition artifact over physics
  failure because 7B and 13B differ in learning rate, batch size, and acquired
  row density. This is not settled until 1B exact rows or a matched-window
  discriminator is acquired.

Exact commands:

```bash
./venv/bin/python3 projects/gp154_scaling_law_normalized/external/build_olmo_external_packet.py
./venv/bin/python3 projects/gp154_scaling_law_normalized/external/eval_olmo_external_packet.py
./venv/bin/python3 projects/gp154_scaling_law_normalized/external/scrape_olmo1b_wandb_report.py
```

If exact 1B export remains blocked, populate
`projects/gp154_scaling_law_normalized/external/olmo2_1b_report_digitized_points_template.csv`
from reviewed chart points only, then run:

```bash
./venv/bin/python3 projects/gp154_scaling_law_normalized/external/build_olmo1b_digitized_backtest_packet.py
```

Do not put rough digitized rows into the clean evidence packet. Treat them as a
separate rough backtest.

## GP163D Side Note

The May 1 `L=6,N=240` field-slice wall-push was stopped fail-closed because no
GPU app appeared after warmup. This is a script/instrument issue: the field
slice path performs a CPU `_relax(...)` warmup before the selected JAX source
solver, and stdout is buffered into the log. Lower `n` working does not certify
the high-`n` path.

The fix is to add a GPU-resident phase preflight / no-CPU-warmup option before
launching another `N=240` wall-push.
