#!/bin/bash
# Watch Round N's checkpoint files; when ALL hit their targets, fire Round N+1.
# Designed to be invoked manually per-round (autofire_next_round.sh roundN nextN).
# Polls every 60s. Writes status to /tmp/autofire_<from_round>_to_<to_round>.log.
set -e
cd /Users/daalami/figs_activist_loop

ROUND_FROM="${1:-round1}"
ROUND_TO="${2:-round2}"
LOG="/tmp/autofire_${ROUND_FROM}_to_${ROUND_TO}.log"

declare -A TARGETS
declare -A FILES

case "$ROUND_FROM" in
  round1)
    FILES["v9.1"]="projects/llm_forecasting_calibration_program/llm_self_calibration_v9/workspace/pilot_v9_1_calls.jsonl"
    TARGETS["v9.1"]=150
    FILES["v6_receiver"]="projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/pilot_v6_receiver_forecasts.jsonl"
    TARGETS["v6_receiver"]=240
    FILES["v6_control"]="projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/pilot_v6_control_forecasts.jsonl"
    TARGETS["v6_control"]=120
    ;;
  round2)
    FILES["v10"]="projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/pilot_v10_calls.jsonl"
    TARGETS["v10"]=360
    ;;
  round3)
    FILES["v10.1"]="projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/pilot_v10_1_calls.jsonl"
    TARGETS["v10.1"]=480  # 40 scored × 4 conds × 3 agents (we filter prospective in scoring)
    ;;
  round4)
    FILES["v5.1"]="projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/pilot_v5_1_forecasts_20260524T165817Z.jsonl"
    TARGETS["v5.1"]=240
    ;;
esac

case "$ROUND_TO" in
  round2)
    NEXT_CMD="nohup python3 projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/run_pilot_v10_dispatch.py --full --resume > /tmp/r2_v10.log 2>&1 &"
    ;;
  round3)
    NEXT_CMD="nohup python3 projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/run_pilot_v10_1_dispatch.py --full --resume > /tmp/r3_v10_1.log 2>&1 &"
    ;;
  round4)
    NEXT_CMD="nohup python3 projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/run_pilot_v5_1_skeptical_dispatch.py --full --resume --checkpoint projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/pilot_v5_1_forecasts_20260524T165817Z.jsonl > /tmp/r4_v5_1.log 2>&1 &"
    ;;
  round5)
    NEXT_CMD="nohup python3 projects/lean_proof_completability_v1/workspace/run_pilot_v7_2_dispatch.py --full --resume > /tmp/r5_v7_2.log 2>&1 &"
    ;;
esac

echo "[$(date)] autofire watcher: ${ROUND_FROM} → ${ROUND_TO}" | tee "$LOG"
echo "  monitoring ${#FILES[@]} files for completion..." | tee -a "$LOG"

while true; do
  ALL_DONE=true
  for k in "${!FILES[@]}"; do
    f="${FILES[$k]}"
    t="${TARGETS[$k]}"
    n=0
    if [ -f "$f" ]; then n=$(wc -l < "$f" | tr -d ' '); fi
    if [ "$n" -lt "$t" ]; then
      ALL_DONE=false
      echo "[$(date +%H:%M:%S)]   $k: $n/$t — waiting" | tee -a "$LOG"
    else
      echo "[$(date +%H:%M:%S)]   $k: $n/$t ✓" | tee -a "$LOG"
    fi
  done
  if [ "$ALL_DONE" = "true" ]; then
    echo "[$(date)] ALL ${ROUND_FROM} done — firing ${ROUND_TO}" | tee -a "$LOG"
    eval "$NEXT_CMD"
    echo "[$(date)] ${ROUND_TO} fired (cmd: $NEXT_CMD)" | tee -a "$LOG"
    exit 0
  fi
  sleep 60
done
