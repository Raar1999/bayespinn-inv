#!/usr/bin/env bash
# Top-level reproduction script: runs the full Weeks 5-12 pipeline.
#
# Usage:
#   bash scripts/reproduce_paper.sh [QUICK|FULL]
#
# QUICK   (default) uses the small-budget configs/train_smoke.yaml plus
#         tiny sweeps; finishes in roughly 10-20 minutes on CPU. Useful for
#         smoke-testing the full pipeline.
# FULL    uses configs/train_base.yaml and the publication-grade sweep sizes
#         from the proposal; needs ~25-50 GPU-hours.
#
# Outputs land in outputs/paper/. Resume-from-checkpoint is built into
# every training script, so re-invoking after a crash is safe.

set -euo pipefail

MODE="${1:-QUICK}"
PAPER_DIR="outputs/paper"
mkdir -p "$PAPER_DIR"

if [ "$MODE" == "QUICK" ]; then
  TRAIN_CFG="configs/train_smoke.yaml"
  N_TEST_PROFILES=5
  NOISE_LEVELS="0.0,0.05"
  N_AL_SEEDS=2
  N_AL_ROUNDS=5
  N_VAL_CAL=10
  N_TEST_CAL=15
else
  TRAIN_CFG="configs/train_base.yaml"
  N_TEST_PROFILES=50
  NOISE_LEVELS="0.0,0.01,0.05,0.10"
  N_AL_SEEDS=10
  N_AL_ROUNDS=25
  N_VAL_CAL=30
  N_TEST_CAL=50
fi

echo "================================================================"
echo "BayesPINN-Inv full pipeline reproduction ($MODE mode)"
echo "Output root: $PAPER_DIR"
echo "================================================================"

# ============================================================================
# Week 5: Production ensemble training (5 members)
# ============================================================================
echo
echo "--- Week 5: training 5-member ensemble ---"
ENSEMBLE_DIR="$PAPER_DIR/ensemble"
mkdir -p "$ENSEMBLE_DIR"
for seed in 0 1 2 3 4; do
  member_dir="$ENSEMBLE_DIR/member_${seed}"
  if [ -f "$member_dir/member_${seed}/ckpt_final.pt" ] \
     || [ -f "$member_dir/manifest.json" ]; then
    echo "  member $seed: already trained, skipping"
    continue
  fi
  echo "  training member $seed"
  PYTHONPATH=src python scripts/train.py --config "$TRAIN_CFG" \
    2>&1 | tee "$member_dir.log" || true
  # The train.py script writes to ${cfg.out_dir}; we move it where we expect
  if [ -d "outputs/$(date +%Y-%m-%d)"* ]; then
    mv outputs/$(date +%Y-%m-%d)* "$member_dir" 2>/dev/null || true
  fi
done
# Combine manifests
PYTHONPATH=src python scripts/combine_manifests.py \
  "$ENSEMBLE_DIR"/member_*/manifest.json \
  -o "$ENSEMBLE_DIR/manifest.json" || \
  echo "  (manifest combine failed; check member dirs)"

# ============================================================================
# Week 6: Forward-model benchmark
# ============================================================================
echo
echo "--- Week 6: SG vs PINN benchmark sweep ---"
PYTHONPATH=src python scripts/run_benchmark_sweep.py \
  --ensemble "$ENSEMBLE_DIR/manifest.json" \
  --n_test_profiles "$N_TEST_PROFILES" \
  --families step,graded,defect \
  --bias_grid 0.0,0.5,9 \
  --out "$PAPER_DIR/benchmarks/"

# ============================================================================
# Week 7: Inverse-design sweep
# ============================================================================
echo
echo "--- Week 7: inverse-design sweep ---"
PYTHONPATH=src python scripts/run_inverse_sweep.py \
  --ensemble "$ENSEMBLE_DIR/manifest.json" \
  --n_targets "$N_TEST_PROFILES" \
  --noise_levels "$NOISE_LEVELS" \
  --parameterizations free,step,graded \
  --bias_grid 0.05,0.5,8 \
  --out "$PAPER_DIR/inverse_sweep/"

# ============================================================================
# Week 8: Active learning ablations
# ============================================================================
echo
echo "--- Week 8: active learning ablations ---"
mkdir -p "$PAPER_DIR/al"
for seed in $(seq 0 $((N_AL_SEEDS - 1))); do
  for strategy in random max_std ucb; do
    run_dir="$PAPER_DIR/al/${strategy}_seed${seed}"
    if [ -f "$run_dir/$strategy/log.json" ]; then
      echo "  AL[$strategy seed=$seed]: already done"
      continue
    fi
    mkdir -p "$run_dir"
    # Inline-edit a config to set the strategy + seed
    cat > "$run_dir/cfg.yaml" <<EOF
seed: $seed
forward_ckpt: $ENSEMBLE_DIR
target:
  family: defect
  N_A: 1.0e22
  N_D: 1.0e22
  x_junction: 5.0e-7
  defect_amplitude: 5.0e22
  defect_center: 7.0e-7
  defect_width: 5.0e-8
active_learning:
  n_rounds: $N_AL_ROUNDS
  candidate_biases: {start: 0.0, stop: 0.5, num: 21}
  initial_biases: [0.0, 0.2, 0.4]
  measurement_noise_rel: 0.02
  n_inverse_iters: 200
strategies: [$strategy]
inverse:
  lr: 5.0e-3
  lambda_TV: 0.5
  lambda_smooth: 1.0e-4
out_dir: $run_dir
EOF
    PYTHONPATH=src python scripts/active_learning.py --config "$run_dir/cfg.yaml" \
      2>&1 | tee "$run_dir/run.log" || \
      echo "  AL[$strategy seed=$seed] FAILED"
  done
done
# Aggregate
PYTHONPATH=src python scripts/aggregate_al.py "$PAPER_DIR/al/" \
  -o "$PAPER_DIR/al_aggregated.json" || true

# ============================================================================
# Week 9: Calibration sweep
# ============================================================================
echo
echo "--- Week 9: calibration sweep ---"
# DeepEnsemble + MC-Dropout + SWAG. We only run DeepEnsemble in this script
# (MC-Dropout/SWAG need separate training runs; uncomment to add).
PYTHONPATH=src python scripts/run_calibration.py \
  --ensemble "$ENSEMBLE_DIR/manifest.json" \
  --n_val_profiles "$N_VAL_CAL" \
  --n_test_profiles "$N_TEST_CAL" \
  --bias_grid 0.0,0.5,8 \
  --out "$PAPER_DIR/calibration/"
# To add MC-Dropout / SWAG:
#   bash scripts/train_mc_dropout.py --config "$TRAIN_CFG" --dropout 0.15 \
#       --out_dir "$PAPER_DIR/mc_dropout"
#   bash scripts/train_swag.py       --config "$TRAIN_CFG" \
#       --out_dir "$PAPER_DIR/swag"
# then re-invoke run_calibration.py with --mc_dropout / --swag arguments.

# ============================================================================
# Week 10: Defect case study
# ============================================================================
echo
echo "--- Week 10: defect case study ---"
PYTHONPATH=src python scripts/defect_case_study.py \
  --ensemble "$ENSEMBLE_DIR/manifest.json" \
  --defect_position 7.0e-7 \
  --defect_amplitude 5.0e22 \
  --defect_width 5.0e-8 \
  --n_iv_points 10 \
  --measurement_noise 0.02 \
  --n_inverse_iters 800 \
  --lambda_TV 0.5 \
  --out "$PAPER_DIR/defect_study/"

# ============================================================================
# Week 12: Freeze tables for the paper
# ============================================================================
echo
echo "--- Week 12: freezing results into LaTeX/Markdown tables ---"
PYTHONPATH=src python scripts/freeze_results.py \
  --benchmark   "$PAPER_DIR/benchmarks/summary.json"          \
  --inverse     "$PAPER_DIR/inverse_sweep/aggregate.json"     \
  --al          "$PAPER_DIR/al_aggregated.json"               \
  --calibration "$PAPER_DIR/calibration/summary.json"         \
  --defect      "$PAPER_DIR/defect_study/metrics.json"        \
  --out_tex     "$PAPER_DIR/results_tables.tex"               \
  --out_md      "$PAPER_DIR/results_summary.md"

echo
echo "================================================================"
echo "Done. Inspect:"
echo "  $PAPER_DIR/results_summary.md           # Markdown results"
echo "  $PAPER_DIR/results_tables.tex           # LaTeX tables for paper"
echo "  $PAPER_DIR/{benchmarks,inverse_sweep,al,calibration,defect_study}"
echo "================================================================"
