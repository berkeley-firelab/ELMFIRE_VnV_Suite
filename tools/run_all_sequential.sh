#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)
CASES_DIR="$ROOT_DIR/cases"

usage() {
  cat <<'USAGE'
Usage: $(basename "$0") [OPTIONS]

Run every case's run_case.sh sequentially (excluding the template).

Options:
  -l, --list        List the resolved case scripts and exit
  -n, --dry-run     Show the commands without executing them
  -h, --help        Show this help message
USAGE
}

LIST_ONLY=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
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
  printf '%s' "${rel%/run_case.sh}"
}

if (( LIST_ONLY )); then
  echo "Discovered $TOTAL case(s):"
  for script in "${CASE_SCRIPTS[@]}"; do
    printf '  - %s\n' "$(format_case "$script")"
  done
  exit 0
fi

if (( DRY_RUN )); then
  echo "[DRY-RUN] $TOTAL case(s) would be executed sequentially:"
  for script in "${CASE_SCRIPTS[@]}"; do
    local_path=$(format_case "$script")
    printf '  - %s (command: %s)\n' "$local_path" "$script"
  done
  exit 0
fi

printf '[INFO] Running %d case(s) sequentially...\n' "$TOTAL"

count=0
for script in "${CASE_SCRIPTS[@]}"; do
  rel=$(format_case "$script")
  printf '\n[INFO] [%d/%d] Running %s...\n' $((count+1)) "$TOTAL" "$rel"
  if "$script"; then
    printf '[OK] Completed %s\n' "$rel"
  else
    rc=$?
    printf '[ERROR] %s failed with exit code %d\n' "$rel" "$rc" >&2
    exit "$rc"
  fi
  ((count++))

done

printf '\n[OK] All %d case(s) completed successfully.\n' "$TOTAL"