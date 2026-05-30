# Session Handoff: Three Frontier Tracks

> **Seam metadata** · `seam_id:` SESSION_HANDOFF_2026-05-01_three_frontier_tracks · `track:` mission · `status:` unrecorded · `last_updated:` 2026-05-08


Recorded: 2026-05-01 11:25:00 EDT  
Status: disconnect-safe handoff

Update: 2026-05-01 11:35:00 EDT

## GP163D Gravity

Current result:

- `gpu_gamma0p25_faceflux_jaxbg_L4p0_n160` completed on `141.148.130.171`.
- Artifacts are saved under
  `projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/remote_results/20260501_141148130171_gamma0p25_jaxbg_n160_complete/`.
- Instrument repair: all minimal source AQUAL solves were finite/converged and
  below the `1e-5` residual gate.
- Physics signal: old "boost" gate is the wrong frame. The meaningful product
  is the orientation discriminator:
  - UDG tidal/uniform: `3.4607`, `2.2838`, `3.7695` for `0/45/90`.
  - Binary tidal/uniform: `0.6999`, `0.7051`, `0.7116`.
- Code was patched so `run_minimal_aqual_sandbox.py` now records
  `orientation_discriminator_candidate` instead of only
  `instrument_not_promoted` when anisotropic sensitivity passes but old boost
  predicates fail.

L6 wall-push status:

- Attempted `L=6,N=240` field-slice launch on `141.148.130.171`.
- It was stopped after no GPU app appeared during the initial warmup window and
  no log/artifacts had appeared.
- This may have been conservative/premature: code inspection shows the
  field-slice path performs CPU `_relax(...)` warmup before the selected JAX
  source solver, and stdout is redirected/buffered, so lack of immediate GPU
  residency does not prove eventual failure.
- It is still not safe to let this run for hours as a "GPU run" without phase
  telemetry.

Next gravity task:

- Patch field-slice launcher/script to print phase logs unbuffered and expose a
  true GPU-resident/no-CPU-warmup source path or explicit CPU-warmup ETA.
- Then rerun `L=6,N=240` wall-push on the new IP.

Patch status:

- `run_field_slice_diagnostics.py` now has `--skip-source-warmup`, timestamped
  flush logs, and per-source elapsed seconds.
- `launch_field_slice_checkpointed_remote.sh` now runs Python with `-u` and
  forwards `SKIP_SOURCE_WARMUP`.
- `deploy_and_launch_field_slice.sh` now forwards `SKIP_SOURCE_WARMUP`.
- Local smoke passed with `--skip-source-warmup`; no remote rerun has been
  launched after this patch because the next host/IP is pending.

Next gravity command on the new host:

```bash
N=240 BOX_HALF_SIZE=6.0 BACKGROUND_AQUAL_SOLVER=jax_residual SOURCE_SOLVER=scipy_jax_residual SKIP_SOURCE_WARMUP=1 LABEL_PREFIX=fieldslice_L6p0_n240_gamma0p25_jaxbg_skipwarmup KEY_PATH=~/.ssh/id_ed25519 REMOTE_USER=ubuntu bash projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/deploy_and_launch_field_slice.sh <NEW_IP>
```

## GP116B Transformer Successor

Current result:

- This is the transformer / residual-state / "next architecture" project, not
  the neural power-law project.
- Latest hardened 3-iter run scored `0`.
- Interpretation: informative negative. Mechanism/architecture flags did not
  show generalizable predictive value for measured GP116 residual cancellation
  over constant/training-only rivals.
- The earlier iter-0 score `92` is invalid for science because it happened
  before substrate/gate hardening.

Acquisition state:

- Existing `projects/gp116_cot_exchange/workspace/external_residual_state_rows.json`
  has 12 source-backed architecture rows.
- Reacquirer is fixed and now returns `12` rows with `blockers=[]`.
- Root causes fixed: arXiv API defaulted to 10 results while the manifest
  requested 11 arXiv IDs, dropping xLSTM; two evidence needles were stricter
  than primary abstract wording.

Next GP116B task:

- Do not rerun expecting a high score unless reframing the target from measured
  cancellation to architecture discovery/diagnostic coverage, or unless direct
  cancellation/rank/survival measurements are acquired for successor mechanisms.

Commands:

```bash
python3 projects/gp116_cot_exchange/acquire_external_residual_state_rows.py --timeout 30
python3 projects/gp116_cot_exchange/build_transformer_successor_substrate.py
make validate-rubric PROJECT=gp116b_transformer_successor RUBRIC=gp116b_transformer_successor PYTHON=./venv/bin/python3
```

## GP154 Neural / Power Law

Current result:

- This is the neural scaling-law / normalized power-law project.
- OLMo2 7B and 13B Stage 1 W&B train CE rows are acquired.
- OLMo2 1B Stage 1 exact train CE rows are not acquired.
- 1B GitHub config/checkpoint metadata is acquired.
- 1B SFT/DPO posttraining W&B rows are acquired but excluded from clean Stage 1
  evidence.

Current backtest:

- External OLMo packet MAE: `0.053515559403500064` over 11,728 rows.
- 13B slice: `0.049729591883822415`.
- 7B slice: `0.12157720850320673`.
- Audit currently favors engineering/acquisition artifact over physics failure:
  7B and 13B differ in LR, batch size, and row density.

Next GP154 task:

- Acquire or approximate OLMo2 1B Stage 1 report rows.
- Exact W&B history export is still blocked, but a browser probe is now working.
- `scrape_olmo1b_wandb_report_browser.py` was added and Playwright Chromium was
  installed. It loads the W&B report and writes sanitized network/run/metric
  hints without persisting secrets.
- Direct GraphQL `view` access outside the browser remains blocked; continue by
  reproducing the browser-captured W&B grouped-runs/history query or use manual
  chart digitization.
- If exact export remains blocked, use reviewed chart digitization as a rough
  backtest only; do not merge rough rows into clean evidence.

Commands:

```bash
./venv/bin/python3 projects/gp154_scaling_law_normalized/external/build_olmo_external_packet.py
./venv/bin/python3 projects/gp154_scaling_law_normalized/external/eval_olmo_external_packet.py
./venv/bin/python3 projects/gp154_scaling_law_normalized/external/scrape_olmo1b_wandb_report.py
./venv/bin/python3 projects/gp154_scaling_law_normalized/external/scrape_olmo1b_wandb_report_browser.py
```

Rough fallback:

```bash
./venv/bin/python3 projects/gp154_scaling_law_normalized/external/build_olmo1b_digitized_backtest_packet.py
```
