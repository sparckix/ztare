#!/bin/bash
# Resume all in-flight pilots after rate-limit pause.
# Each pilot is checkpoint-resumable via --resume flag.
# Idempotent: rows already in checkpoint are skipped.
set -e
cd /Users/daalami/figs_activist_loop

echo "[$(date)] resuming all in-flight pilots..."

nohup python3 projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/run_pilot_v5_1_skeptical_dispatch.py --full --resume > /tmp/pilot_v5_1_resume.log 2>&1 &
echo "  v5.1 skeptical PID=$!"

nohup python3 projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/run_pilot_v6_transfer_dispatch.py --stage receiver --full --resume > /tmp/pilot_v6_receiver_resume.log 2>&1 &
echo "  v6 receiver PID=$!"

# v6 control waits for receiver to complete (per the chain), but we can fire it as a separate process
# once receiver is done; for now leave it queued under the v6 chain logic
# (manually launch when needed)

nohup python3 projects/lean_proof_completability_v1/workspace/run_pilot_v7_2_dispatch.py --full --resume > /tmp/pilot_v7_2_resume.log 2>&1 &
echo "  v7.2 mech (5-cond) PID=$!"

nohup python3 projects/llm_forecasting_calibration_program/llm_self_calibration_v9/workspace/run_pilot_v9_1_dispatch.py --full --resume > /tmp/pilot_v9_1_resume.log 2>&1 &
echo "  v9.1 injected-memory PID=$!"

nohup python3 projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/run_pilot_v10_dispatch.py --full --resume > /tmp/pilot_v10_resume.log 2>&1 &
echo "  v10 mech apparatus PID=$!"

nohup python3 projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/run_pilot_v10_1_dispatch.py --full --resume > /tmp/pilot_v10_1_resume.log 2>&1 &
echo "  v10.1 mech external PID=$!"

sleep 3
echo
echo "[$(date)] verifying all launched:"
ps -eo pid,etime,command | grep -E "run_pilot_v[5-9]|run_pilot_v10" | grep -v grep | awk '{printf "  PID %s elapsed=%s\n", $1, $2}'
