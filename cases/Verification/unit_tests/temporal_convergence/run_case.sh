#!/usr/bin/env bash
set -euo pipefail


SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
CASE_DIR="$SCRIPT_DIR"

YAML="$CASE_DIR/case.yaml"
ELMFIRE_BIN_RAW=$(awk '/^elmfire:/,/^postprocess:/' "$YAML" | awk -F 'bin:' 'NF>1{gsub(/^[ \t]+|[ \t]+$/, "", $2); gsub(/["\047]/, "", $2); print $2}')
RUNTIME_LIMIT=$(awk '/^elmfire:/,/^postprocess:/' "$YAML" | awk -F 'runtime_limit_s:' 'NF>1{gsub(/[ "\t]/, "", $2); print $2}')

if [[ -z "${ELMFIRE_BIN_RAW:-}" ]]; then
	ELMFIRE_BIN_RESOLVED="${ELMFIRE_BIN:-}"
elif [[ "$ELMFIRE_BIN_RAW" == "\$ELMFIRE_BIN" || "$ELMFIRE_BIN_RAW" == "\${ELMFIRE_BIN}" ]]; then
	ELMFIRE_BIN_RESOLVED="${ELMFIRE_BIN:-}"
else
	ELMFIRE_BIN_RESOLVED="$ELMFIRE_BIN_RAW"
fi

if [[ -z "${ELMFIRE_BIN_RESOLVED:-}" ]]; then
	echo "[ERROR] ELMFIRE binary is not set. Define elmfire.bin in case.yaml or export ELMFIRE_BIN." >&2
	exit 2
fi

mkdir -p "$CASE_DIR/data/outputs" "$CASE_DIR/data/logs" "$CASE_DIR/data/scratch"

# Clean previous temporal outputs and scratch to avoid GDAL/create conflicts
echo "[INFO] Cleaning previous outputs and scratch directories"
rm -rf "$CASE_DIR/data/outputs"/* || true
rm -rf "$CASE_DIR/data/scratch"/* || true

python3 "$CASE_DIR/scripts/generate_inputs.py"

shopt -s nullglob
for cfg in "$CASE_DIR"/data/inputs/elmfire_[0-9]*.data; do
	CFG_NAME=$(basename "$cfg")
	TIME_GRID=${CFG_NAME#elmfire_}
	TIME_GRID=${TIME_GRID%.data}
	OUTPUT_DIR="$CASE_DIR/data/outputs/$TIME_GRID"
	LOG_DIR="$CASE_DIR/data/logs/$TIME_GRID"
	SCRATCH_DIR="$CASE_DIR/data/scratch/$TIME_GRID"

	echo "[INFO] Running ELMFIRE for time grid: $TIME_GRID"
	mkdir -p "$OUTPUT_DIR" "$LOG_DIR" "$SCRATCH_DIR"

	SECS_START=$(date +%s)
	set +e
	(cd "$CASE_DIR" && "$ELMFIRE_BIN_RESOLVED" "data/inputs/$CFG_NAME" > "$LOG_DIR/elmfire.stdout" 2> "$LOG_DIR/elmfire.stderr")
	RC=$?
	set -e
	SECS_END=$(date +%s)
	ELAPSED=$((SECS_END-SECS_START))

	if [[ $RC -ne 0 ]]; then
		echo "[ERROR] ELMFIRE failed for $TIME_GRID (exit $RC). See $LOG_DIR/elmfire.stderr" >&2
		continue
	fi
	if [[ $ELAPSED -gt ${RUNTIME_LIMIT:-999999} ]]; then
		echo "[WARN] Runtime exceeded limit for $TIME_GRID ($ELAPSED s > ${RUNTIME_LIMIT}s)" >&2
	fi

	echo "[OK] Completed time grid: $TIME_GRID"
done
shopt -u nullglob

echo "[OK] Done Running $CASE_DIR"

python3 "$CASE_DIR/scripts/postprocess.py"

# Clean outputs and scratch after postprocessing to free space
echo "[INFO] Cleaning outputs and scratch after postprocessing"
rm -rf "$CASE_DIR/data/outputs"/* || true
rm -rf "$CASE_DIR/data/scratch"/* || true
echo "[OK] Cleaned outputs and scratch"