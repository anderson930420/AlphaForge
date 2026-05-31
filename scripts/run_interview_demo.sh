#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${1:-artifacts/demo/interview_ml_demo_C}"
SUMMARY_PATH="$OUTPUT_DIR/research_validation/ml_demo_research_validation_summary.json"
FINAL_HOLDOUT_DIR="$OUTPUT_DIR/research_validation/ml_signal_single_symbol_validation/final_holdout"
REPORT_PATH="$OUTPUT_DIR/interview_artifact_report.html"

mkdir -p "$OUTPUT_DIR"

echo "[interview-demo] Running ML demo pipeline with optional research validation..."
PYTHONPATH=src python3 scripts/run_ml_demo_pipeline.py \
  --features tests/fixtures/ml_demo_pipeline/features.csv \
  --returns tests/fixtures/ml_demo_pipeline/monthly_returns.csv \
  --output-dir "$OUTPUT_DIR" \
  --model ridge_regressor \
  --feature-cols Mom12m,BM,Investment \
  --label-col ret_fwd_1m \
  --train-end 2024-03-31 \
  --long-quantile 0.8 \
  --short-quantile 0.2 \
  --diagnostic-quantiles 2 \
  --run-research-validation \
  --research-validation-market-data tests/fixtures/ml_signal_research_validation/market_data.csv \
  --research-validation-symbol C \
  --research-validation-development-start 2024-01-31 \
  --research-validation-development-end 2024-03-31 \
  --research-validation-holdout-start 2024-04-30 \
  --research-validation-holdout-end 2024-06-30 \
  --research-validation-train-size 2 \
  --research-validation-test-size 1 \
  --research-validation-step-size 1

echo "[interview-demo] Verifying demo health checks..."
python3 - <<'PY' "$SUMMARY_PATH"
from __future__ import annotations

import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
if not summary_path.exists():
    print(f"ERROR: summary file not found: {summary_path}", file=sys.stderr)
    raise SystemExit(1)

with open(summary_path) as f:
    summary = json.load(f)

nonzero = int(summary.get("nonzero_target_weight_count", 0))
extra_signal_dates = summary.get("date_alignment", {}).get("extra_signal_dates", None)
warnings = summary.get("warnings", [])

print(f"[interview-demo] nonzero_target_weight_count={nonzero}")
print(f"[interview-demo] extra_signal_dates={extra_signal_dates}")
print(f"[interview-demo] warnings={warnings}")

if nonzero <= 0:
    print(
        "ERROR: selected demo symbol has no nonzero exposure. "
        "Use a symbol with nonzero_target_weight_count > 0 before presenting this demo.",
        file=sys.stderr,
    )
    raise SystemExit(1)

if extra_signal_dates != []:
    print(
        "ERROR: selected signal dates are not fully covered by market data. "
        "custom_signal validation requires signal datetime values to be present in market_data.",
        file=sys.stderr,
    )
    raise SystemExit(1)

if warnings:
    print("WARNING: demo completed with health-check warnings:", file=sys.stderr)
    for warning in warnings:
        print(f"  - {warning}", file=sys.stderr)

print("[interview-demo] Health checks passed.")
PY

if [[ -d "$FINAL_HOLDOUT_DIR" ]]; then
  echo "[interview-demo] Rendering final holdout HTML artifact report..."
  PYTHONPATH=src python3 -m alphaforge.cli render-artifact-report \
    --artifact-dir "$FINAL_HOLDOUT_DIR" \
    --output "$REPORT_PATH"
  echo "[interview-demo] HTML report: $REPORT_PATH"
else
  echo "WARNING: final holdout directory not found: $FINAL_HOLDOUT_DIR" >&2
fi

echo "[interview-demo] Key artifacts:"
echo "  - $OUTPUT_DIR/ml_demo_summary.json"
echo "  - $OUTPUT_DIR/signal/ml_signal.csv"
echo "  - $SUMMARY_PATH"
echo "  - $FINAL_HOLDOUT_DIR/metrics_summary.json"
echo "  - $REPORT_PATH"
