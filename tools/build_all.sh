#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)
MAIN_DIR="$ROOT_DIR/main_report"
CASES_DIR="$ROOT_DIR/cases"


# Build all case PDFs
shopt -s nullglob
for CASE_TEX in "$CASES_DIR"/*/report/case_report.tex; do
( cd "$(dirname "$CASE_TEX")" && latexmk -pdf -silent case_report.tex )
echo "[OK] Built $(dirname "$CASE_TEX")/case_report.pdf"
done


# Generate main_report/cases.tex with \includepdf entries
OUT="$MAIN_DIR/cases.tex"
: > "$OUT"
for PDF in "$CASES_DIR"/*/report/case_report.pdf; do
CASE_NAME=$(basename "$(dirname "$(dirname "$PDF")")")
echo "\\section{$CASE_NAME}" >> "$OUT"
echo "\\includepdf[pages=-,pagecommand=\\section*{$CASE_NAME}\\addcontentsline{toc}{section}{$CASE_NAME}]{../cases/$CASE_NAME/report/case_report.pdf}" >> "$OUT"
echo "" >> "$OUT"
done


echo "[OK] Updated $OUT"


# Build master report
( cd "$MAIN_DIR" && latexmk -pdf -silent main.tex )
echo "[OK] Built $MAIN_DIR/main.pdf"
