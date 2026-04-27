#!/bin/bash
# GP-116 TDO-LR multi-seed replication sweep (falsifies single-seed +19.9%).
#
# Assumes test_tdo_falsification.py has been shipped to the instance.
# Run from the instance, inside the projects/gp116_cot_exchange/ dir.
#
# Each seed produces workspace/tdo_falsification_seed<N>.json.
# ~30-60 min per seed on A100; 5 seeds => 2.5-5h total.
#
# Survival threshold (from test_tdo_falsification.py docstring):
#     TDO arm reaches val_perplexity target in ≥10% fewer wall-clock
#     steps than baseline, holding across ≥3 of 5 seeds.
#
# Usage (on the instance):
#     bash tdo_multiseed_sweep.sh 2>&1 | tee sweep.log

set -e
cd "$(dirname "$0")"

SEEDS=(42 137 256 1337 2024)
STEPS=3000
ARCH="EleutherAI/pythia-160m"

mkdir -p workspace
echo "=== TDO multi-seed sweep start: $(date -u +%FT%TZ) ==="
echo "seeds: ${SEEDS[*]}; arch: $ARCH; steps: $STEPS"

for seed in "${SEEDS[@]}"; do
    echo "--- seed $seed start: $(date -u +%FT%TZ) ---"
    python3 test_tdo_falsification.py \
        --seed "$seed" \
        --arch "$ARCH" \
        --steps "$STEPS" \
        --device cuda \
        2>&1 | tee "workspace/tdo_sweep_seed${seed}.log"
    # The script writes workspace/tdo_falsification.json — rename per seed.
    if [ -f workspace/tdo_falsification.json ]; then
        mv workspace/tdo_falsification.json "workspace/tdo_falsification_seed${seed}.json"
    fi
    echo "--- seed $seed end: $(date -u +%FT%TZ) ---"
done

echo "=== TDO multi-seed sweep done: $(date -u +%FT%TZ) ==="
ls -la workspace/tdo_falsification_seed*.json
