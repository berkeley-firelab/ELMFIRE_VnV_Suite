# Developer checks

These tests check the suite's tooling, input preparation, and interpretation of
evidence. They do not run ELMFIRE, establish scientific verification of the
model, or serve as dependencies of individual cases.

Run from the repository root using the Python environment installed for the suite:

```bash
make test PYTHON_BIN=python
make test-reports PYTHON_BIN=python
make test-all PYTHON_BIN=python
```

`PYTHON_BIN` defaults to `python3`. The default checks need the scientific Python
dependencies used by the cases, including NumPy, Rasterio, Matplotlib, and PyYAML.
They do not need an ELMFIRE executable, an MPI installation, Slurm, LaTeX, or the
large landscape archives. Archive tests use small synthetic fixtures. Runner
tests substitute executables and never submit jobs or invoke a real simulator.

| Command | Scope |
| --- | --- |
| `make test` | Files named `test_*.py`: evidence validity, numerical data handling, staging integrity, cleanup, namelists, discovery, runner behavior, and report decision/value preservation. |
| `make test-reports` | Files named `*_checks.py`: optional typography, heading structure, and editorial wording checks. No PDF build. |
| `make test-all` | Both groups. |

For one test file:

```bash
python -m unittest discover -s tools/tests -p 'test_gofer_postprocess.py' -v
```

Preparation tests copy case-owned source material to temporary directories,
starting without generated variants. They check the resulting rasters and time
controls. Runner probes also use isolated copies, including paths with spaces.
Tracked case inputs, saved results, and reports are not rewritten by these tests.

Behavioral checks should assert observable results rather than particular
variable names or source-code expressions. Static checks remain appropriate for
declared contracts, resource ownership, forbidden imports, and namelist fields.
Different cases may implement helpers differently; file-hash equality is not a
correctness requirement. Test helpers may be shared within this directory, but
case execution must never depend on them.

The previously failing sweep fixtures lacked required timestep/meteorology
metadata; the CASE40 fixture also used an obsolete directory layout. The
landscape report fixture omitted its local language module. Those fixtures have
been repaired without relaxing evidence checks. A new runner regression covers
serial execution on older Bash, where an empty array under `set -u` fails.
