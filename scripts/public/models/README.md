# scripts/public/models/

> **Up:** [scripts/](../../README.md) · **Subdir:** [gnn_lemma_relevance/](gnn_lemma_relevance/README.md) · **Siblings:** [lean/](../lean/README.md) · [control/](../control/README.md)

Machine-learning training, inference, and data prep for the GP-225
lemma-relevance line. The question this whole tree exists to answer:
does a learned ranker beat the LeanHammer typeclass baseline. Each
version header states what it fixes over the prior, so the file series
is also the experiment record. Checkpoints and training pairs land
under `analytics/public/gnn/` (gitignored, regenerable); moat-grade
verdicts live in the GP-225 seams and memory, not here.

## GFlowNet baseline

| Script | What it does |
|---|---|
| `gflownet_data_extract.py` | GP-216f scale-8: extract labeled (state, target, outcome) triples from F-row history. |
| `gflownet_train.py` | Minimal GFlowNet baseline: graph-conditioned MLP predicting (target, obligation) closure. |

## GNN lemma-relevance ranker (version series)

| Script | What it does |
|---|---|
| `gnn_lemma_relevance_data_prep.py` | Graph2Tac-style training pairs from the NS Track B spine + Mathlib4 dependency graph. |
| `gnn_lemma_relevance_train.py` | v1 baseline ranker (target signature + candidate). |
| `gnn_lemma_relevance_train_v2.py` | v2: fixes v1 overfitting (v1 val peaked at epoch 40 then dropped). |
| `gnn_lemma_relevance_train_v3.py` | v3: bigger encoder + hard-negative mining. |
| `gnn_lemma_relevance_train_v4.py` | v4: fine-tuned encoder + hard-negs + bigger backbone. |
| `gnn_lemma_relevance_train_v6.py` | v6: InfoNCE loss + mixed negatives + warmup (v4/v5 showed feature collapse). |
| `gnn_lemma_relevance_v21_rerank.py` | Compatibility wrapper delegating to `gnn_lemma_relevance/v21_rerank.py`. |
| `gnn_lemma_relevance_v31_candidate_generator.py` | Compatibility wrapper delegating to `gnn_lemma_relevance/v31_candidate_generator.py`. |
| `v2_production_hit10_falsifier.py` | Compatibility wrapper delegating to the production hit@10 falsifier. |
| `ztare_lean_declaration_hygiene.py` | Compatibility wrapper delegating to the declaration-hygiene check. |

## GNN link-prediction (NS constraint graph)

| Script | What it does |
|---|---|
| `gnn_link_prediction_train.py` | Train a relational GCN (RGCN) on bootstrap snapshots of the NS Track B constraint graph. |
| `gnn_v3_train.py` | v3 tactical improvements over v2 for inductive generalization. |
| `gnn_v4_mathlib_pretrain.py` | The "100x" experiment: pre-train the encoder on mathlib4's dependency graph, then NS fine-tune. |
| `gnn_inductive_holdout.py` | Honest inductive holdout: does the link predictor generalize to unseen nodes (vs the transductive bootstrap)? |
| `gnn_inductive_v2.py` | Feature-aware GraphSAGE that fixes the v1 memorizer architecture errors. |
| `gnn_link_predict_score.py` | v2 inference: score candidate inequality edges with the trained checkpoint. |
| `gnn_link_predict_score_v3.py` | v3 inference (replaces the deprecated v2 scorer). |
| `gnn_novelty_filter.py` | TEST B: filter v3 GNN nominations by overlap with existing spine theorems. |
| `gnn_training_data_prep.py` | Build temporal constraint-graph snapshots + targets for link-prediction training. |

## Shared data prep

| Script | What it does |
|---|---|
| `mine_ztare_pairs_for_training.py` | Mine (target-signature, used-lemmas) pairs from the ZTARE Lean spine for v5 training. |
| `lora_dataset_prep.py` | GP-216f: extract closed `ns_*.lean` theorems as (prompt, completion) LoRA pairs. |

## Related

- The versioned ranker implementations: [gnn_lemma_relevance/](gnn_lemma_relevance/README.md)
- Lean side that produces the obligations: [lean/](../lean/README.md)
- Lemma-ranker visibility at RD ticks: `scripts/public/control/rd_tick_gnn_precheck.py`
