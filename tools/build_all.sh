#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
MAIN_DIR="$ROOT_DIR/main_report"
PYTHON_BIN=${PYTHON_BIN:-python3}

"$PYTHON_BIN" "$ROOT_DIR/tools/generate_summary_reports.py"

(cd "$MAIN_DIR" && latexmk -pdf -silent verification_report.tex)
echo "[OK] Built $MAIN_DIR/verification_report.pdf"

(cd "$MAIN_DIR" && latexmk -pdf -silent validation_report.tex)
echo "[OK] Built $MAIN_DIR/validation_report.pdf"
