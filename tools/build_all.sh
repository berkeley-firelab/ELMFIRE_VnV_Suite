#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)
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
shopt -s nullglob
for CASE_TEX in "$CASES_DIR"/*/report/case_report.tex; do
  CASE_DIR=$(dirname "$(dirname "$CASE_TEX")")
  CASE_NAME=$(basename "$CASE_DIR")
  [[ "$CASE_NAME" == "case_template" ]] && continue
  ( cd "$(dirname "$CASE_TEX")" && latexmk -pdf -silent case_report.tex )
  echo "[OK] Built $CASE_DIR/report/case_report.pdf"
done

# Generate main_report/cases.tex with natural sections via subfiles when available
OUT="$MAIN_DIR/cases.tex"
: > "$OUT"

for CASE_DIR in "$CASES_DIR"/*; do
  [[ -d "$CASE_DIR" ]] || continue
  CASE_NAME=$(basename "$CASE_DIR")
  [[ "$CASE_NAME" == "case_template" ]] && continue

  BODY="$CASE_DIR/report/case_body.tex"
  PDF="$CASE_DIR/report/case_report.pdf"
  CASE_NAME_TEX=$(latex_escape "$CASE_NAME")

  if [[ -f "$BODY" ]]; then
    {
      echo "\\clearpage"
      echo "\\section{$CASE_NAME_TEX}"
      echo "\\subfile{../cases/$CASE_NAME/report/case_body.tex}"
      echo ""
    } >> "$OUT"
    echo "[OK] Linked as subfile: $BODY"
  elif [[ -f "$PDF" ]]; then
    # Fallback: include the compiled PDF, hide master page numbers to avoid duplicates
    {
      echo "\\clearpage"
      echo "\\section{$CASE_NAME_TEX}"
      echo "\\includepdf[pages=1,linktodoc=true,pagecommand={\\section*{$CASE_NAME_TEX}\\addcontentsline{toc}{section}{$CASE_NAME_TEX}\\thispagestyle{empty}}]{../cases/$CASE_NAME/report/case_report.pdf}"
      echo "\\includepdf[pages=2-,linktodoc=true,pagecommand={\\thispagestyle{empty}}]{../cases/$CASE_NAME/report/case_report.pdf}"
      echo ""
    } >> "$OUT"
    echo "[OK] Fallback includepdf: $PDF"
  else
    echo "[WARN] No case_body.tex or case_report.pdf for $CASE_NAME — skipping" >&2
  fi
done

echo "[OK] Updated $OUT"

# Build master report
( cd "$MAIN_DIR" && latexmk -pdf -silent main.tex )
echo "[OK] Built $MAIN_DIR/main.pdf"
