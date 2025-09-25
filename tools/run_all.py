#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

def usage():
    return """Usage: run_all_cases.py [OPTIONS]

Run every case's run_case.sh sequentially (excluding the template).

Options:
  -l, --list        List the resolved case scripts and exit
  -n, --dry-run     Show the commands without executing them
  -s, --slurm       Submit jobs via Slurm (sbatch run_case_slurm.sh)
  -h, --help        Show this help message

Notes:
  - Each case is executed from its own case directory so ELMFIRE
    sees inputs in the current working directory (as required).
  - With --slurm, a run_case_slurm.sh wrapper is generated per case
    using tools/slurm.sbatch as the universal header.
"""

def discover_cases(cases_dir):
    """Find all run_case.sh under cases_dir, excluding template."""
    scripts = []
    for dirpath, _, filenames in os.walk(cases_dir):
        if "case_template" in dirpath:
            continue
        if "run_case.sh" in filenames:
            scripts.append(os.path.join(dirpath, "run_case.sh"))
    scripts.sort()
    return scripts

def format_case(script, root_dir):
    """Pretty relative path like cases/wue_transient_heatflux"""
    rel = os.path.relpath(script, root_dir)
    return rel.removesuffix("/run_case.sh")

def make_slurm_wrapper(case_dir, header_path):
    """Create run_case_slurm.sh by combining slurm_head.txt + run_case.sh."""
    wrapper = os.path.join(case_dir, "run_case_slurm.sh")
    run_case = os.path.join(case_dir, "run_case.sh")

    if not os.path.isfile(header_path):
        print(f"[ERROR] Missing Slurm header file: {header_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(run_case):
        print(f"[ERROR] Missing run_case.sh in {case_dir}", file=sys.stderr)
        sys.exit(1)

    with open(wrapper, "w") as f:
        f.write("#!/usr/bin/env bash\n\n")
        with open(header_path, "r") as hdr:
            f.write(hdr.read().rstrip() + "\n\n")
        with open(run_case, "r") as rc:
            f.write(rc.read().rstrip() + "\n")

    os.chmod(wrapper, 0o755)
    return wrapper

def main():
    parser = argparse.ArgumentParser(add_help=False, usage=usage())
    parser.add_argument("-l", "--list", action="store_true")
    parser.add_argument("-n", "--dry-run", action="store_true")
    parser.add_argument("-s", "--slurm", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")
    args, extra = parser.parse_known_args()

    if args.help:
        print(usage())
        sys.exit(0)

    if extra:
        print(f"[ERROR] Unexpected argument: {extra[0]}", file=sys.stderr)
        print(usage(), file=sys.stderr)
        sys.exit(2)

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cases_dir = os.path.join(root_dir, "cases")
    header_path = os.path.join(root_dir, "common", "slurm_head.txt")

    if not os.path.isdir(cases_dir):
        print(f"[ERROR] Cases directory not found: {cases_dir}", file=sys.stderr)
        sys.exit(1)

    case_scripts = discover_cases(cases_dir)
    total = len(case_scripts)

    if total == 0:
        print(f"[WARN] No case scripts were discovered under {cases_dir}", file=sys.stderr)
        sys.exit(0)

    if args.list:
        print(f"Discovered {total} case(s):")
        for script in case_scripts:
            print(f"  - {format_case(script, root_dir)}")
        sys.exit(0)

    if args.dry_run:
        mode = "Slurm submission" if args.slurm else "local execution"
        print(f"[DRY-RUN] {total} case(s) would be run with {mode}:")
        for script in case_scripts:
            rel = format_case(script, root_dir)
            case_dir = os.path.dirname(script)
            if args.slurm:
                print(f"  - {rel} (cd {case_dir} && sbatch run_case_slurm.sh)")
            else:
                print(f"  - {rel} (cd {case_dir} && ./run_case.sh)")
        sys.exit(0)

    # Actual execution
    if args.slurm:
        print(f"[INFO] Preparing & submitting {total} case(s) via Slurm ...")
    else:
        print(f"[INFO] Running {total} case(s) sequentially ...")

    for idx, script in enumerate(case_scripts, start=1):
        rel = format_case(script, root_dir)
        case_dir = os.path.dirname(script)
        print(f"\n[INFO] [{idx}/{total}] {rel}")

        if not os.path.isdir(case_dir):
            print(f"[ERROR] Cannot cd into {case_dir}", file=sys.stderr)
            sys.exit(1)

        if args.slurm:
            wrapper = make_slurm_wrapper(case_dir, header_path)
            try:
                subprocess.run(["sbatch", wrapper], cwd=case_dir, check=True)
                print(f"[OK] Submitted {rel}")
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] sbatch failed in {case_dir}", file=sys.stderr)
                sys.exit(e.returncode)
        else:
            try:
                subprocess.run(["bash", "./run_case.sh"], cwd=case_dir, check=True)
                print(f"[OK] Completed {rel}")
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] run_case.sh failed in {case_dir}", file=sys.stderr)
                sys.exit(e.returncode)

    if args.slurm:
        print(f"\n[OK] Submitted {total} job(s).")
    else:
        print(f"\n[OK] All {total} case(s) completed simulation successfully.")

if __name__ == "__main__":
    main()
