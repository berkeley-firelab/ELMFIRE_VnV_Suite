# Report build dependencies and troubleshooting

Run the environment check before rebuilding a report on either the workstation
or Savio. It checks the selected Python interpreter, report tools, every TeX
package referenced by current reports, cache access, and actual compilation of
genuine Times New Roman regular, bold, italic, and bold italic.

```bash
# Activate the Python environment used for this suite first.
make report-check PYTHON_BIN=python
make reports PYTHON_BIN=python
```

`PYTHON_BIN` must identify the interpreter with PyYAML installed. On the current
Mac workstation, the Anaconda interpreter is an available option:

```bash
make report-check PYTHON_BIN=/opt/homebrew/anaconda3/bin/python
```

The diagnostic log is `tmp/report-environment/build.log.txt`; the TeX log is
`tmp/report-environment/font_probe.log`. The diagnostic PDF demonstrates all
four actual font faces. A successful dependency check does not establish that
scientific inputs, figures, or simulation results are present.

## LuaLaTeX reports no writeable cache path

The reproduced local failure occurs before the document preamble:

```text
luaotfload ... Failed to load "fontloader" module "basics-gen"
system : no writeable cache path, quiting
```

LuaLaTeX needs to write its font cache. In the installed TeX Live 2024, the TeX
file-access policy also rejects hidden or absolute cache paths even when the
operating system permits writing them. Every current report and the case
template now has a local `.latexmkrc` that places the cache in the relative
`tex-cache/` directory, chooses LuaLaTeX, and configures an optional font directory.
Those files are copies of `common/latexmkrc`; keep them synchronized.

Run `latexmk` from the report directory so it loads that configuration:

```bash
cd cases/Validation/landscape_scale/thomas_fire/report
latexmk -g -lualatex -interaction=nonstopmode -halt-on-error case_report.tex
```

The cache is ignored by Git and can be regenerated. To change its location, use
a non-hidden relative subdirectory of each report's working directory, for
example `ELMFIRE_TEX_CACHE=tex-cache-local`. Do not point it at an absolute
scratch path or a hidden directory on this installation. The configuration does
not enable unrestricted shell execution or change TeX's file-access policy.
If compiling by calling `lualatex` directly, `.latexmkrc` is not read; prefer
`latexmk`, or explicitly export `TEXMFCACHE=tex-cache` after creating that
directory in the report directory.

## Times New Roman cannot be found

The report style requires genuine Times New Roman in four faces. A successful
`fc-match` alone does not prove that LuaLaTeX can load the font: fontconfig can
return a substitute. The report check compiles the actual style and inspects
the resolved font names for all four faces.

On macOS these files are commonly installed under
`/System/Library/Fonts/Supplemental/`. If the fonts are in a separate directory,
point the build at that directory:

```bash
export ELMFIRE_REPORT_FONT_DIR="/absolute/path/to/times-new-roman-fonts"
make report-check PYTHON_BIN=python
```

The directory must contain the regular, bold, italic, and bold italic font
files. Obtain the genuine files through your institution or an installation you
are entitled to use. They are not bundled or committed in this repository.
`ELMFIRE_REPORT_FONT_DIR` adds an OpenType lookup path; it does not substitute
another font family. A font-only correction does not require running ELMFIRE.

## Required tools or TeX packages are missing

The build uses `latexmk`, `lualatex`, and `kpsewhich`. Common package dependencies
include `fontspec`, `luaotfload`, `siunitx`, `seqsplit`, `booktabs`, `titlesec`,
`caption`, `ragged2e`, and `pdfpages`; the check scans the actual report sources
and lists missing `.sty` files.

On an Ubuntu or Debian host where you manage system packages:

```bash
sudo apt-get update
sudo apt-get install latexmk texlive-luatex texlive-latex-extra texlive-science fontconfig
```

These packages provide the report tools and TeX dependencies. Times New Roman
is an additional dependency. The repository Dockerfiles include the TeX package
set above; supply genuine Times New Roman files separately, for example through
a read-only font volume and `ELMFIRE_REPORT_FONT_DIR`. The Ubuntu package
catalog describes the [science collection](https://packages.ubuntu.com/jammy/texlive-science).

With a TeX Live installation managed by `tlmgr`, install the specific missing
packages reported by the check using that installation's package manager. On
macOS, use the TeX Live installation associated with MacTeX or BasicTeX rather
than mixing binaries from multiple TeX installations. Restart the shell after
installing a toolchain if its executable directory is not yet on `PATH`.

## Savio environment

Activate the dedicated suite Conda environment, and inspect the TeX modules
available on that system. Module names vary; use the available site-provided
TeX Live module rather than assuming a particular name:

```bash
module avail tex
conda activate YOUR_SUITE_ENV
command -v latexmk lualatex kpsewhich
make report-check PYTHON_BIN="$CONDA_PREFIX/bin/python"
```

If the TeX tools are missing and no suitable module exists, use a user-managed
TeX Live installation or request the tools from the cluster administrators.
System package installation commands requiring `sudo` are not a Savio workflow.
If Times New Roman is missing, put the four genuine faces in your own font
directory and export `ELMFIRE_REPORT_FONT_DIR` before building. Ensure that
directory and the report working directory are visible on the build node.

After the check succeeds:

```bash
make reports PYTHON_BIN="$CONDA_PREFIX/bin/python"
```

For a single case, compile its existing report directly as shown above.
`run_case.sh` also runs the simulation; it is not needed to repair a report.

## Python cannot import yaml

`ModuleNotFoundError: No module named 'yaml'` is a Python environment error.
Activate the suite environment, or install PyYAML into the chosen interpreter:

```bash
python -m pip install PyYAML
make report-check PYTHON_BIN=python
```

The report Make targets and case compile scripts honor `PYTHON_BIN`; the
preflight reports exactly which interpreter it checked.

## Summary status and GOFER case chapters disagree

The summary table reads `outputs/metrics.json`, while each detailed chapter is
an included standalone PDF. The four GOFER report converters previously used
an exact method-version check and silently replaced newer metrics with an empty
result. This produced `NOT EVALUABLE` and zero simulations in chapters even
when the summary correctly showed `CHARACTERIZED`.

GOFER result metrics no longer carry a manually maintained method-version label.
The converters check the fields needed to render the report, including statuses,
run counts, overlap values and arrival-time statistics. Malformed metrics fail
with a field-specific error without replacing report inputs. Older files that
still contain a method-version label are accepted based on their contents;
the extra label is ignored.

Rebuild the standalone PDFs before the guide. From the repository root, with
the suite Python environment active:

```bash
for fire in caldor_2021 czu_lightning_complex_2020 glass_2020 kincade_2019; do
  PYTHON_BIN=python bash "cases/Validation/landscape_scale/$fire/compile_case.sh" || break
done
make validation-report PYTHON_BIN=python
```

These commands use existing metrics and figures; they do not run ELMFIRE or
recalculate comparisons. `make validation-report` assembles existing case PDFs;
it does not refresh their metrics macros. An earlier configuration without
results can still correctly show `NOT EVALUABLE` alongside a characterized
current configuration in the same chapter.

## Figures are missing or a TeX error persists

If aggregate logs report multiply defined `case-detail` labels, check for copied
case folders with the same case ID. Report discovery prefers a unique case in
the documented category folder (`landscape_scale`, `structure_scale`,
`unit_tests`, or `coupling_tests`) and warns about an older copy outside those
categories. It leaves all copied data untouched. Multiple canonical copies
remain an explicit ambiguity error that requires resolving the case identity.

After dependency checks pass, inspect the first `!` or `LaTeX Error` entry in
the case's `case_report.log` or the aggregate report's `.log`. Missing figures
are a separate evidence problem. Preserve the original metrics and observations
while repairing the build. The missing-figure fallback in `tools/build_all.sh`
cannot repair absent fonts, packages, or Python dependencies; the environment
check now runs before those fallback attempts.
