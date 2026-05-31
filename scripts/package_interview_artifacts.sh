#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  cat >&2 <<'EOF'
Usage:
  bash scripts/package_interview_artifacts.sh <artifact_run_dir> <output_zip> [--allow-missing-html]

Example:
  bash scripts/package_interview_artifacts.sh \
    artifacts/demo/interview_ml_demo_C \
    artifacts/demo/interview_ml_demo_C.zip

The output ZIP is intended for the Interview Streamlit Showcase upload flow.
EOF
  exit 2
fi

RUN_DIR="$1"
OUTPUT_ZIP="$2"
ALLOW_MISSING_HTML="${3:-}"

if [[ ! -d "$RUN_DIR" ]]; then
  echo "ERROR: artifact run directory not found: $RUN_DIR" >&2
  exit 1
fi

REQUIRED_FILES=(
  "ml_demo_summary.json"
  "signal/ml_signal.csv"
  "research_validation/ml_demo_research_validation_summary.json"
  "research_validation/ml_signal_single_symbol_validation/final_holdout/metrics_summary.json"
  "research_validation/ml_signal_single_symbol_validation/final_holdout/equity_curve.csv"
  "research_validation/ml_signal_single_symbol_validation/final_holdout/trade_log.csv"
)

for relpath in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "$RUN_DIR/$relpath" ]]; then
    echo "ERROR: required artifact missing: $RUN_DIR/$relpath" >&2
    exit 1
  fi
done

if [[ ! -f "$RUN_DIR/interview_artifact_report.html" && "$ALLOW_MISSING_HTML" != "--allow-missing-html" ]]; then
  echo "ERROR: interview_artifact_report.html missing." >&2
  echo "Run scripts/run_interview_demo.sh or pass --allow-missing-html." >&2
  exit 1
fi

python3 - <<'PY' "$RUN_DIR/research_validation/ml_demo_research_validation_summary.json"
from __future__ import annotations

import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
with open(summary_path) as f:
    summary = json.load(f)

nonzero = int(summary.get("nonzero_target_weight_count", 0))
extra_signal_dates = summary.get("date_alignment", {}).get("extra_signal_dates")
if nonzero <= 0:
    print("ERROR: nonzero_target_weight_count must be > 0 before packaging.", file=sys.stderr)
    raise SystemExit(1)
if extra_signal_dates != []:
    print("ERROR: extra_signal_dates must be [] before packaging.", file=sys.stderr)
    raise SystemExit(1)
print(f"[package-interview-artifacts] nonzero_target_weight_count={nonzero}")
print(f"[package-interview-artifacts] extra_signal_dates={extra_signal_dates}")
PY

mkdir -p "$(dirname "$OUTPUT_ZIP")"
rm -f "$OUTPUT_ZIP"

PARENT_DIR="$(dirname "$RUN_DIR")"
RUN_BASENAME="$(basename "$RUN_DIR")"
(
  cd "$PARENT_DIR"
  zip -r "$(pwd)/$(basename "$OUTPUT_ZIP")" "$RUN_BASENAME" >/dev/null
)

# Move zip if requested output path was not directly under RUN_DIR parent.
CREATED_ZIP="$PARENT_DIR/$(basename "$OUTPUT_ZIP")"
if [[ "$CREATED_ZIP" != "$OUTPUT_ZIP" ]]; then
  mv "$CREATED_ZIP" "$OUTPUT_ZIP"
fi

echo "[package-interview-artifacts] Wrote $OUTPUT_ZIP"
