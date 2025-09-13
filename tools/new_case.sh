#!/usr/bin/env bash
set -euo pipefail # Ensure the script won’t continue in a half-broken state.
ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)
TEMPLATE="$ROOT_DIR/cases/case_template"
CASES_DIR="$ROOT_DIR/cases"


if [[ $# -lt 1 ]]; then
echo "Usage: $0 <case_id>" >&2
exit 1
fi
CASE_ID="$1"
DEST="$CASES_DIR/$CASE_ID"


if [[ -e "$DEST" ]]; then
echo "[ERROR] Case already exists: $DEST" >&2
exit 2
fi


rsync -a --exclude "figures" --exclude "output" --exclude "logs" "$TEMPLATE/" "$DEST/"


# Token replacement
sed -i.bak -e "s/{{CASE_ID}}/$CASE_ID/g" "$DEST/case.yaml" "$DEST/report/case_macros.tex" 
rm -f "$DEST"/*.bak "$DEST"/report/*.bak || true


echo "[OK] Created case at $DEST"


echo "Next steps:"
echo "- cd $DEST, and edit the following:"
echo "case.yaml: Case Metadata"
echo "report/case_macros.tex: Case report Metadata"
echo "report/case_report.tex: Detailed report"
echo "scripts/postprocess.py: Case-specific Postprocessing pipeline"
echo "- ./run_case.sh"
