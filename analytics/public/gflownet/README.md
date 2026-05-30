# analytics/public/gflownet/

GFlowNet baseline artifacts for the GP-225 lemma-relevance line:
training data + the trained baseline MLP checkpoint.

- `training_data.jsonl` - extracted training pairs.
- `baseline_mlp.pt` - the trained graph-conditioned MLP baseline.

Produced by `scripts/public/models/gflownet_*`. Regenerable;
the moat-grade verdicts live in the GP-225 seams, not here.
