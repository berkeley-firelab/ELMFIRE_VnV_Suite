#!/usr/bin/env bash
set -euo pipefail


# --- Configuration ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
CASE_DIR="$SCRIPT_DIR"


YAML="$CASE_DIR/case.yaml"
ELMFIRE_BIN_RAW=$(awk '/^elmfire:/,/^postprocess:/' "$YAML" | awk -F 'bin:' 'NF>1{gsub(/^[ \t]+|[ \t]+$/, "", $2); gsub(/["\047]/, "", $2); print $2}')
ELMFIRE_CFG=$(awk '/^elmfire:/,/^postprocess:/' "$YAML" | awk -F 'config:' 'NF>1{gsub(/[ "]/,"",$2); print $2}')
RUNTIME_LIMIT=$(awk '/^elmfire:/,/^postprocess:/' "$YAML" | awk -F 'runtime_limit_s:' 'NF>1{gsub(/[ "]/,"",$2); print $2}')

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

mkdir -p "$CASE_DIR/data/outputs" "$CASE_DIR/data/logs" "$CASE_DIR/data/logs/scratch"

# Generate ELMFIRE input files from templates
python3 "$CASE_DIR/scripts/generate_inputs.py"

# Run ELMFIRE for each generated data subfolder (e.g. data/1024, data/512...)
for d in "$CASE_DIR/data"/*; do
	if [[ ! -d "$d" ]]; then
		continue
	fi
	# require an inputs/elmfire.data file
	if [[ ! -f "$d/inputs/elmfire.data" ]]; then
		continue
	fi

	RES_NAME=$(basename "$d")
	echo "[INFO] Running ELMFIRE for resolution: $RES_NAME"
	mkdir -p "$d/logs" "$d/logs/scratch" "$d/outputs"

	# Run elmfire inside the resolution folder (elmfire.data was configured to use ./inputs and ./outputs)
	SECS_START=$(date +%s)
	set +e
	(cd "$d" && "$ELMFIRE_BIN_RESOLVED" "inputs/elmfire.data" > "logs/elmfire.stdout" 2> "logs/elmfire.stderr")
	RC=$?
	set -e
	SECS_END=$(date +%s)
	ELAPSED=$((SECS_END-SECS_START))

	if [[ $RC -ne 0 ]]; then
		echo "[ERROR] ELMFIRE failed for $RES_NAME (exit $RC). See $d/logs/elmfire.stderr" >&2
		continue
	fi
	if [[ $ELAPSED -gt ${RUNTIME_LIMIT:-999999} ]]; then
		echo "[WARN] Runtime exceeded limit for $RES_NAME ($ELAPSED s > ${RUNTIME_LIMIT}s)" >&2
	fi

	# leave per-resolution outputs in place; postprocessing will run after all simulations
	echo "[OK] Completed resolution: $RES_NAME"
done

echo "[OK] Done Running $CASE_DIR"

# --- Postprocess & Figures ---
python3 "$CASE_DIR/scripts/postprocess.py"