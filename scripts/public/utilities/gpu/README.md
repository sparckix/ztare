# scripts/public/utilities/gpu/

> **Up:** [utilities/](../README.md) · [scripts/](../../../README.md)

External GPU / API run bootstrap and registration. The neural-scaling
and oe-eval lines run off-box on remote GPU hosts; these are the glue
that registers and resumes those runs. Not part of the local pipeline.

| Script | What it does |
|---|---|
| `register_external_gpu_run.py` | Register an external GPU/API run in the ZTARE kernel run registry. |
| `run_oe_eval_checkpoint_sequence.py` | Run an oe-eval command sheet as a sequence of checkpoint jobs with restart markers (resumable). |
| `patch_lm_eval_vllm_prompt_tokens.py` | Patch lm_eval 0.4.x token-prompt calls so the pinned `lm_eval==0.4.3` + `vllm==0.11.0` pair runs. |
| `lambda_olmes_vllm_bootstrap.sh` | Bootstrap OLMES + vLLM on a fresh Lambda host. |
| `neural_transformer_probe_bootstrap.sh` | Bootstrap the neural-transformer probe environment. |
| `pull_oe_eval_gate_artifacts.sh` | Pull the oe-eval gate artifacts back from the remote host. |

## Related

- Run registry these write to: the ZTARE kernel run registry (see `scripts/public/control/register_external_gpu_run.py` and `external_run_monitor.py`).
