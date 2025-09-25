#!/usr/bin/env bash
set -euo pipefail
MAIN_DIR="$ROOT_DIR/main_report"
CASES_DIR="$ROOT_DIR/cases"

# --- helper: escape LaTeX specials in titles/ToC (not paths) ---
latex_escape() {
  local s="$1"
  s=${s//\\/\\\\}   # \  -> \\
  s=${s//&/\\&}     # &  -> \&
  s=${s//%/\\%}     # %  -> \%
  s=${s//_/\\_}     # _  -> \_
  s=${s//#/\\#}     # #  -> \#
  s=${s//\$/\\$}    # $  -> \$
  printf '%s' "$s"
}

# Build all per-case PDFs (still useful for standalone viewing)
mapfile -t CASE_TEX_FILES < <(
  find "$CASES_DIR" -type f -path "*/report/case_report.tex" \
    ! -path "$CASES_DIR/case_template/*" | sort
)

for CASE_TEX in "${CASE_TEX_FILES[@]}"; do
  CASE_REPORT_DIR=$(dirname "$CASE_TEX")
  CASE_DIR=$(dirname "$CASE_REPORT_DIR")
  CASE_REL_PATH=${CASE_DIR#"$CASES_DIR/"}
  CASE_NAME=$(basename "$CASE_DIR")

  ( cd "$CASE_REPORT_DIR" && latexmk -pdf -silent case_report.tex )
  echo "[OK] Built $CASE_DIR/report/case_report.pdf"
done

# Generate main_report/cases.tex with natural sections via subfiles when available
OUT="$MAIN_DIR/cases.tex"
: > "$OUT"

for CASE_TEX in "${CASE_TEX_FILES[@]}"; do
  CASE_REPORT_DIR=$(dirname "$CASE_TEX")
  CASE_DIR=$(dirname "$CASE_REPORT_DIR")
  CASE_REL_PATH=${CASE_DIR#"$CASES_DIR/"}
  CASE_NAME=$(basename "$CASE_DIR")
  CASE_NAME_TEX=$(latex_escape "$CASE_NAME")

  BODY="$CASE_DIR/report/case_body.tex"

  if [[ -f "$BODY" ]]; then
    {
      echo "\\clearpage"
      echo "\\section{$CASE_NAME_TEX}"
      echo "\\subfile{../cases/$CASE_REL_PATH/report/case_body.tex}"
      echo ""
    } >> "$OUT"
    echo "[OK] Linked as subfile: $BODY"
  else
    echo "[WARN] No case_body.tex for $CASE_REL_PATH — skipping" >&2
  fi
done

echo "[OK] Updated $OUT"

# Build master report
( cd "$MAIN_DIR" && latexmk -pdf -silent main.tex )
echo "[OK] Built $MAIN_DIR/main.pdf"
