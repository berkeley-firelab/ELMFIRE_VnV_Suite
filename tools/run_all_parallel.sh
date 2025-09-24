#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)
CASES_DIR="$ROOT_DIR/cases"

usage() {
  cat <<'USAGE'
Usage: $(basename "$0") [OPTIONS]

Run every case's run_case.sh in parallel (excluding the template).

Options:
  -j, --jobs N      Maximum number of concurrent cases (default: auto)
  -l, --list        List the resolved case scripts and exit
  -n, --dry-run     Show the planned execution without running anything
  -h, --help        Show this help message
USAGE
}

LIST_ONLY=0
DRY_RUN=0
JOBS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -j|--jobs)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] Missing value for $1" >&2
        usage >&2
        exit 2
      fi
      JOBS="$2"
      shift 2
      ;;
    -l|--list)
      LIST_ONLY=1
      shift
      ;;
    -n|--dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "[ERROR] Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ $# -gt 0 ]]; then
  echo "[ERROR] Unexpected argument: $1" >&2
  usage >&2
  exit 2
fi

if [[ ! -d "$CASES_DIR" ]]; then
  echo "[ERROR] Cases directory not found: $CASES_DIR" >&2
  exit 1
fi

mapfile -t CASE_SCRIPTS < <(
  find "$CASES_DIR" -type f -name 'run_case.sh' \
    ! -path '*/case_template/*' | sort
)

TOTAL=${#CASE_SCRIPTS[@]}

if (( TOTAL == 0 )); then
  echo "[WARN] No case scripts were discovered under $CASES_DIR" >&2
  exit 0
fi

format_case() {
  local script="$1"
  local rel=${script#"$ROOT_DIR/"}
  printf '%s' "${rel%/run_case.sh}";
}

if (( LIST_ONLY )); then
  echo "Discovered $TOTAL case(s):"
  for script in "${CASE_SCRIPTS[@]}"; do
    printf '  - %s\n' "$(format_case "$script")"
  done
  exit 0
fi

if [[ -n "$JOBS" ]]; then
  if ! [[ "$JOBS" =~ ^[0-9]+$ ]]; then
    echo "[ERROR] --jobs expects a positive integer" >&2
    exit 2
  fi
  if (( JOBS < 1 )); then
    echo "[ERROR] --jobs must be at least 1" >&2
    exit 2
  fi
else
  if command -v nproc &>/dev/null; then
    JOBS=$(nproc --all)
  elif command -v getconf &>/dev/null; then
    JOBS=$(getconf _NPROCESSORS_ONLN)
  else
    JOBS=$TOTAL
  fi
  if ! [[ "$JOBS" =~ ^[0-9]+$ ]] || (( JOBS < 1 )); then
    JOBS=$TOTAL
  fi
fi

if (( JOBS > TOTAL )); then
  JOBS=$TOTAL
fi

if (( DRY_RUN )); then
  echo "[DRY-RUN] $TOTAL case(s) would be executed with up to $JOBS concurrent job(s):"
  for script in "${CASE_SCRIPTS[@]}"; do
    printf '  - %s (command: %s)\n' "$(format_case "$script")" "$script"
  done
  exit 0
fi

if ! command -v python3 &>/dev/null; then
  echo "[ERROR] python3 is required to coordinate parallel execution" >&2
  exit 1
fi

printf '[INFO] Running %d case(s) with up to %d parallel worker(s)...\n' "$TOTAL" "$JOBS"

PYTHONUNBUFFERED=1 python3 - "$JOBS" "$ROOT_DIR" "${CASE_SCRIPTS[@]}" <<'PY'
import concurrent.futures
import os
import subprocess
import sys
import threading

max_workers = int(sys.argv[1])
root_dir = sys.argv[2]
case_scripts = sys.argv[3:]

lock = threading.Lock()
failures = []
successes = 0

def rel_case(script):
    rel = os.path.relpath(script, root_dir)
    if rel.endswith('run_case.sh'):
        rel = rel[:-len('run_case.sh')]
    return rel.rstrip('/')

def run_case(script):
    rel = rel_case(script)
    with lock:
        print(f"[INFO] Starting {rel}", flush=True)
    proc = subprocess.run([script])
    return rel, proc.returncode

with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_map = {executor.submit(run_case, script): script for script in case_scripts}
    try:
        for future in concurrent.futures.as_completed(future_map):
            script = future_map[future]
            rel = rel_case(script)
            try:
                rel_name, returncode = future.result()
            except Exception as exc:  # noqa: BLE001
                with lock:
                    print(f"[ERROR] {rel} raised an exception: {exc}", flush=True)
                    failures.append((rel, None))
                continue
            if returncode == 0:
                with lock:
                    successes += 1
                    print(f"[OK] {rel_name}", flush=True)
            else:
                with lock:
                    failures.append((rel_name, returncode))
                    print(f"[FAIL] {rel_name} (exit {returncode})", flush=True)
    except KeyboardInterrupt:  # pragma: no cover - interactive use
        with lock:
            print("\n[WARN] Interrupt received, signalling subprocesses...", flush=True)
        for future in future_map:
            future.cancel()
        raise

total = len(case_scripts)
failed = len(failures)
print("\nSummary:", flush=True)
print(f"  Total cases:    {total}", flush=True)
print(f"  Successful:     {successes}", flush=True)
print(f"  Failed:         {failed}", flush=True)

if failures:
    print("\nFailed cases:", flush=True)
    for rel, code in failures:
        if code is None:
            print(f"  - {rel}: exception during execution", flush=True)
        else:
            print(f"  - {rel}: exit code {code}", flush=True)
    sys.exit(1)
else:
    sys.exit(0)
PY