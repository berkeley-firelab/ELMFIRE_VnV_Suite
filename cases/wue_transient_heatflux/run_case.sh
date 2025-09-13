#!/usr/bin/env bash
set -euo pipefail


# --- Configuration ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
CASE_DIR="$SCRIPT_DIR"
ROOT_DIR=$(cd "$CASE_DIR/../../" && pwd)


YAML="$CASE_DIR/case.yaml"
ELMFIRE_BIN=$(awk '/^elmfire:/,/^postprocess:/' "$YAML" | awk -F 'bin:' 'NF>1{gsub(/[ \"]/, "", $2); print $2}')
ELMFIRE_CFG=$(awk '/^elmfire:/,/^postprocess:/' "$YAML" | awk -F 'config:' 'NF>1{gsub(/[ \"]/, "", $2); print $2}')
RUNTIME_LIMIT=$(awk '/^elmfire:/,/^postprocess:/' "$YAML" | awk -F 'runtime_limit_s:' 'NF>1{gsub(/[ \"]/, "", $2); print $2}')
PATH_TO_GDAL=$(awk '/^elmfire:/,/^postprocess:/' "$YAML" | awk -F 'path_to_gdal:' 'NF>1{gsub(/[ \"]/, "", $2); print $2}')

mkdir -p "$CASE_DIR/output" "$CASE_DIR/figures" "$CASE_DIR/logs" 
mkdir -p "$CASE_DIR/logs/scratch"

# --- Run ELMFIRE ---
echo "[INFO] Running ELMFIRE..."
SECS_START=$(date +%s)
set +e
"$ELMFIRE_BIN" "$CASE_DIR/$ELMFIRE_CFG" > "$CASE_DIR/logs/elmfire.stdout" 2> "$CASE_DIR/logs/elmfire.stderr"
RC=$?
set -e
SECS_END=$(date +%s)
ELAPSED=$((SECS_END-SECS_START))


if [[ $RC -ne 0 ]]; then
echo "[ERROR] ELMFIRE failed (exit $RC). See logs/elmfire.stderr" >&2
exit $RC
fi
if [[ $ELAPSED -gt ${RUNTIME_LIMIT:-999999} ]]; then
echo "[WARN] Runtime exceeded limit ($ELAPSED s > ${RUNTIME_LIMIT}s)" >&2
fi


# (Optional) move/copy model outputs into ./output
# Example: mv *.csv "$CASE_DIR/output/" || true


# --- Postprocess & Figures ---
python3 "$CASE_DIR/scripts/postprocess.py" --case-dir "$CASE_DIR"


# --- Build case report PDF ---
( cd "$CASE_DIR/report" && latexmk -pdf -silent case_report.tex )


# --- Update main report index ---
"$ROOT_DIR/tools/refresh_main.sh"


# --- Done ---
echo "[OK] Built $CASE_DIR/report/case_report.pdf"
