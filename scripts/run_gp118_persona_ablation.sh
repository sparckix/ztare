#!/bin/bash
# GP-118: Three-Way Persona Ablation Experiment
#
# Tests whether the rubric persona (generation-time conditioning)
# has a measurable effect on convergence, gaming, and hypothesis diversity
# independent of the hard gates.
#
# Three conditions on the same substrate (gp088 Hardy-Ramanujan):
#   A: Skeptical scientist
#   B: Neutral evaluator
#   C: Enthusiastic explorer
#
# Same gates, same threshold, same GT, same model, 50 iterations each.
#
# Usage:
#   bash scripts/run_gp118_persona_ablation.sh
#
# Estimated cost: ~$4.50 (3 × 50 iterations × ~$0.03/iter)
# Estimated time: ~45 minutes total

set -e

BASE_PROJECT="gp088_calibration_a01"
ITERS=8
MUTATOR_MODEL="gpt4.1"
JUDGE_MODEL="gpt4.1"

echo "================================================================"
echo "  GP-118: Three-Way Persona Ablation Experiment"
echo "================================================================"
echo ""
echo "  Substrate: ${BASE_PROJECT} (Hardy-Ramanujan)"
echo "  Iterations per condition: ${ITERS}"
echo "  Model: ${MUTATOR_MODEL} / ${JUDGE_MODEL}"
echo "  Estimated cost: ~\$4.50"
echo ""

# Step 1: Freeze the base project
echo "[1/6] Freezing base project state..."
FREEZE_DIR="projects/${BASE_PROJECT}/frozen_for_gp118"
if [ ! -d "$FREEZE_DIR" ]; then
    mkdir -p "$FREEZE_DIR"
    cp projects/${BASE_PROJECT}/evidence.txt "$FREEZE_DIR/"
    cp projects/${BASE_PROJECT}/evidence_holdout.txt "$FREEZE_DIR/" 2>/dev/null || true
    cp projects/${BASE_PROJECT}/evidence_farther_tail.txt "$FREEZE_DIR/" 2>/dev/null || true
    cp projects/${BASE_PROJECT}/thesis.md "$FREEZE_DIR/" 2>/dev/null || true
    echo "  Frozen to ${FREEZE_DIR}"
else
    echo "  Already frozen"
fi

# Step 2: Create three isolated project copies
echo "[2/6] Creating isolated project copies..."
for COND in skeptical neutral enthusiastic; do
    DEST="projects/gp118_persona_${COND}"
    if [ -d "$DEST" ]; then
        echo "  ${DEST} exists — wiping for clean run"
        rm -rf "$DEST"
    fi

    cp -r "projects/${BASE_PROJECT}" "$DEST"

    # Clean all iteration state for a fresh start
    rm -rf "$DEST/history"
    rm -f "$DEST"/debate_log_iter_*.md
    rm -f "$DEST/current_iteration.md"
    rm -f "$DEST/champion_eval_results.json"
    rm -f "$DEST/latest_eval_results.json"
    rm -f "$DEST/latest_probability_dag.json"
    rm -f "$DEST/champion_probability_dag.json"
    rm -f "$DEST/workspace/derived_constraints.json"
    rm -rf "$DEST/frozen_for_gp118"
    rm -f "$DEST/test_model.py"
    rm -f "$DEST/latest_evidence_gaps.json"
    rm -rf "$DEST/__pycache__"
    mkdir -p "$DEST/history"

    echo "  Cleaned ${DEST}"

    echo "  Created ${DEST} (clean)"
done

# Step 3: Run condition A (Skeptical)
echo ""
echo "[3/6] Running Condition A: SKEPTICAL SCIENTIST (${ITERS} iterations)..."
echo "  Start: $(date)"
make loop PROJECT=gp118_persona_skeptical \
    RUBRIC=gp117_persona_skeptical \
    ITERS=${ITERS} \
    MUTATOR_MODEL=${MUTATOR_MODEL} \
    JUDGE_MODEL=${JUDGE_MODEL} \
    2>&1 | tee projects/gp118_persona_skeptical/run_log.txt
echo "  End: $(date)"

# Step 4: Run condition B (Neutral)
echo ""
echo "[4/6] Running Condition B: NEUTRAL EVALUATOR (${ITERS} iterations)..."
echo "  Start: $(date)"
make loop PROJECT=gp118_persona_neutral \
    RUBRIC=gp117_persona_neutral \
    ITERS=${ITERS} \
    MUTATOR_MODEL=${MUTATOR_MODEL} \
    JUDGE_MODEL=${JUDGE_MODEL} \
    2>&1 | tee projects/gp118_persona_neutral/run_log.txt
echo "  End: $(date)"

# Step 5: Run condition C (Enthusiastic)
echo ""
echo "[5/6] Running Condition C: ENTHUSIASTIC EXPLORER (${ITERS} iterations)..."
echo "  Start: $(date)"
make loop PROJECT=gp118_persona_enthusiastic \
    RUBRIC=gp117_persona_enthusiastic \
    ITERS=${ITERS} \
    MUTATOR_MODEL=${MUTATOR_MODEL} \
    JUDGE_MODEL=${JUDGE_MODEL} \
    2>&1 | tee projects/gp118_persona_enthusiastic/run_log.txt
echo "  End: $(date)"

# Step 6: Generate comparison report
echo ""
echo "[6/6] Generating comparison report..."
python3 -c "
import json, os, glob, re
import numpy as np

conditions = ['skeptical', 'neutral', 'enthusiastic']
results = {}

for cond in conditions:
    proj = f'projects/gp118_persona_{cond}'
    history = sorted(glob.glob(f'{proj}/history/*_meta.json'))

    scores = []
    for h in history:
        meta = json.load(open(h))
        scores.append(meta.get('score', 0))

    # Champion score
    champ_path = f'{proj}/champion_eval_results.json'
    champ_score = 0
    if os.path.exists(champ_path):
        champ_score = json.load(open(champ_path)).get('score', 0)

    # Count debate logs for gaming analysis
    debates = glob.glob(f'{proj}/debate_log_iter_*.md')

    # Count unique fit_declarations (hypothesis diversity)
    fit_forms = set()
    for h in history:
        md_path = h.replace('_meta.json', '.md')
        if os.path.exists(md_path):
            content = open(md_path).read()
            # Extract fit_declaration expression
            match = re.search(r'expression[\":\s]+(.*?)[\"\n]', content)
            if match:
                fit_forms.add(match.group(1).strip())

    results[cond] = {
        'total_iterations': len(scores),
        'champion_score': champ_score,
        'mean_score': round(np.mean(scores), 1) if scores else 0,
        'median_score': round(np.median(scores), 1) if scores else 0,
        'scores_above_50': sum(1 for s in scores if s > 50),
        'scores_at_zero': sum(1 for s in scores if s == 0),
        'unique_fit_forms': len(fit_forms),
        'score_trajectory': scores[:10],  # first 10 for quick view
    }

print()
print('GP-118 PERSONA ABLATION — COMPARISON REPORT')
print('='*65)
print(f'{\"Metric\":>25} | {\"Skeptical\":>10} | {\"Neutral\":>10} | {\"Enthusiastic\":>12}')
print('-'*65)

for metric in ['total_iterations', 'champion_score', 'mean_score',
               'median_score', 'scores_above_50', 'scores_at_zero',
               'unique_fit_forms']:
    vals = [str(results[c][metric]) for c in conditions]
    print(f'{metric:>25} | {vals[0]:>10} | {vals[1]:>10} | {vals[2]:>12}')

print()
print('Score trajectories (first 10 iterations):')
for cond in conditions:
    traj = results[cond]['score_trajectory']
    print(f'  {cond:>12}: {traj}')

print()

# Statistical test: are the distributions different?
from scipy.stats import kruskal
all_scores = {c: [] for c in conditions}
for cond in conditions:
    proj = f'projects/gp118_persona_{cond}'
    for h in sorted(glob.glob(f'{proj}/history/*_meta.json')):
        meta = json.load(open(h))
        all_scores[cond].append(meta.get('score', 0))

if all(len(v) >= 5 for v in all_scores.values()):
    stat, p = kruskal(*all_scores.values())
    print(f'Kruskal-Wallis test: H={stat:.2f}, p={p:.4f}')
    if p < 0.05:
        print('  SIGNIFICANT — persona affects score distribution')
    else:
        print('  NOT SIGNIFICANT — persona is decorative (kill criterion met)')
else:
    print('  Insufficient data for statistical test')

# Save full report
report = {'conditions': results, 'raw_scores': {c: list(v) for c, v in all_scores.items()}}
out = 'projects/gp118_persona_skeptical/../gp118_comparison_report.json'
# Use a cleaner path
out = 'projects/gp118_comparison_report.json'
json.dump(report, open(out, 'w'), indent=2)
print(f'Full report saved to {out}')
"

echo ""
echo "================================================================"
echo "  GP-118 COMPLETE"
echo "================================================================"
echo "  Check: projects/gp118_comparison_report.json"
echo "  Debate logs: projects/gp118_persona_*/debate_log_iter_*.md"
echo "  For Munger camouflage test: grep persona-vocabulary in debate logs"
echo ""
