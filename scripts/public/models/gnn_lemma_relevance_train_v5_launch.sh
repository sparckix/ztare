#!/bin/bash
# v5 launch — same architecture as v4 (mpnet + encoder fine-tune + hard-neg
# mining + bigger backbone), but augmented with ZTARE-internal pairs from
# `analytics/public/leanmill/gnn_ranker/ztare_pairs.jsonl` mixed into training.
#
# Per the v2 production hit@10 falsifier finding (2026-05-06): production
# targets cite ZTARE-internal lemmas the v2/v4 model never saw at train
# time. v5 closes that gap by augmenting mathlib_pairs (~57K) with
# ztare_pairs (~880, but high-signal since distribution matches production).
#
# Run AFTER v4 finishes (per the rule: don't kill long-running compute on
# noisy diagnostics; v4 has general-purpose value for non-NS substrates,
# v5 is the NS-targeted complement).
#
# Usage on GPU machine:
#     bash scripts/public/models/gnn_lemma_relevance_train_v5_launch.sh

set -e
cd /home/ubuntu

# Verify v4 finished + checkpoint exists
if [ ! -f /home/ubuntu/analytics/public/leanmill/gnn_ranker/ranker_checkpoint_v4.pt ]; then
    echo "WARNING: v4 checkpoint not found. Either v4 is still running or it crashed."
    echo "If v4 is still running, wait for it to finish before launching v5 (auto-mode discipline)."
    exit 1
fi

# Verify ZTARE pairs uploaded
if [ ! -f /home/ubuntu/analytics/public/leanmill/gnn_ranker/ztare_pairs.jsonl ]; then
    echo "ERROR: ztare_pairs.jsonl missing. Run scripts/public/models/mine_ztare_pairs_for_training.py locally + scp to GPU."
    exit 1
fi

# v5 reuses v4 script. The training data side already loads
# mathlib_pairs.jsonl when --mix-mathlib is set (default). Adding
# ZTARE pairs requires extending the data loader to also concatenate
# ztare_pairs.jsonl when present. The flag --mix-ztare is added to v5.
echo "v5 launch:"
echo "  encoder: mpnet (frozen except last 4 layers)"
echo "  data: mathlib_pairs (~57K) + ztare_pairs (~880, high-signal)"
echo "  hidden: 512  dropout: 0.25  hard-neg per target: 64"
echo "  epochs: 60  patience: 10"
echo

nohup python3 scripts/public/models/gnn_lemma_relevance_train_v5.py \
    --device cuda \
    --epochs 60 \
    --patience 10 \
    --hidden 512 \
    --dropout 0.25 \
    --mine-every 5 \
    --neg-per-target 64 \
    --unfreeze-layers 4 \
    --batch-size 32 \
    --grad-accum 2 \
    --mix-ztare \
    --out-checkpoint /home/ubuntu/analytics/public/leanmill/gnn_ranker/ranker_checkpoint_v5.pt \
    > /home/ubuntu/v5_train.log 2>&1 &
echo "started v5; pid=$!"
echo "monitor with: tail -f /home/ubuntu/v5_train.log"
