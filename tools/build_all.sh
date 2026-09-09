#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
MAIN_DIR="$ROOT_DIR/main_report"
PYTHON_BIN=${PYTHON_BIN:-python3}

compile_missing_case_reports() {
  local case_file case_dir report_dir compile_script
  local primary_succeeded
  local failures=0

  while IFS= read -r -d '' case_file; do
    case_dir=${case_file%/case.yaml}
    report_dir="$case_dir/report"
    compile_script="$case_dir/compile_case.sh"

    if [[ -f "$report_dir/case_report.pdf" ]]; then
      continue
    fi

    if [[ ! -f "$report_dir/case_report.tex" ]]; then
      echo "[WARN] Cannot build case report; missing $report_dir/case_report.tex" >&2
      failures=1
      continue
    fi

    echo "[INFO] Building missing case report: $report_dir/case_report.pdf"
    primary_succeeded=0
    if [[ -f "$compile_script" ]]; then
      # Invoke through Bash so a transferred repository does not require the
      # executable bit to be restored before reports can be assembled.
      if PYTHON_BIN="$PYTHON_BIN" bash "$compile_script"; then
        primary_succeeded=1
      fi
    elif (
      cd "$report_dir"
      latexmk -pdf -silent -interaction=nonstopmode -halt-on-error case_report.tex
    ); then
      primary_succeeded=1
    fi

    if [[ "$primary_succeeded" -ne 1 || ! -f "$report_dir/case_report.pdf" ]]; then
      echo "[WARN] Normal case report build failed; retrying with result graphics in draft mode: $case_dir" >&2
      # A case that has not been evaluated may legitimately lack generated
      # result figures. Graphicx draft mode keeps the scientific narrative and
      # visibly marks the absent graphics without inventing evidence. -g is
      # required because latexmk remembers the preceding failed invocation.
      if ! (
        cd "$report_dir"
        latexmk -g -pdf -silent -interaction=nonstopmode -halt-on-error \
          -usepretex='\PassOptionsToPackage{draft}{graphicx}' \
          case_report.tex
      ); then
        echo "[WARN] Case report build failed even in draft-graphics mode: $case_dir" >&2
        failures=1
        continue
      fi
    fi

    if [[ ! -f "$report_dir/case_report.pdf" ]]; then
      echo "[WARN] Case report build did not create $report_dir/case_report.pdf" >&2
      failures=1
    fi
  done < <(
    find "$ROOT_DIR/cases/Verification" "$ROOT_DIR/cases/Validation" \
      -type f -name case.yaml -print0
  )

  return "$failures"
}

case_report_failures=0
compile_missing_case_reports || case_report_failures=1

# Generate the include lists only after attempting the standalone reports so
# newly created case_report.pdf files are included in this aggregate build.
# Scientific decisions remain derived solely from outputs/metrics.json.
"$PYTHON_BIN" "$ROOT_DIR/tools/generate_summary_reports.py"

(cd "$MAIN_DIR" && latexmk -pdf -silent verification_report.tex)
echo "[OK] Built $MAIN_DIR/verification_report.pdf"

(cd "$MAIN_DIR" && latexmk -pdf -silent validation_report.tex)
echo "[OK] Built $MAIN_DIR/validation_report.pdf"

if [[ "$case_report_failures" -ne 0 ]]; then
  echo "[ERROR] One or more standalone case reports could not be built." >&2
  echo "[ERROR] Aggregate reports use explicit placeholders for those cases." >&2
  exit 1
fi
