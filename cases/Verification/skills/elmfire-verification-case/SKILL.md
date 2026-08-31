---
name: elmfire-verification-case
description: Create, extend, or review independently runnable ELMFIRE verification cases in this repository. Use for unit or coupling cases with explicit expected behavior, metrics, acceptance criteria, scripts, and a case report. Do not use for validation against real-world observations or for structure-only repository reorganization.
---

# ELMFIRE verification case

Create one auditable verification case without changing unrelated cases or scientific behavior.

## Establish the case contract

1. Read the repository `README.md`, `cases/Verification/CASE_REGISTRY.md`, the relevant category README, and `cases/case_template/`.
2. Inspect the current ELMFIRE implementation for the exact variables, namelist keys, units, sign conventions, grid conventions, and output names being tested. Do not infer these from old case files alone.
3. State the controlled behavior, analytic or otherwise known response, observables, metrics, tolerances, failure conditions, and limitations before implementing the case.
4. Put an isolated function or known-response test in `unit_tests/`; put a multi-component interaction in `coupling_tests/`.
5. Obtain the next unused identifier from the registry. Use `CASE##_<PURPOSE>`, where `<PURPOSE>` is a short stable uppercase abbreviation. Never renumber or reuse an existing identifier.
6. Add a narrow `namelist_contract` to `case.yaml` following
   `docs/namelist-versioning.md`. Record only values whose change would alter
   the experiment or make a required metric unavailable. Keep purpose,
   derivations, metric rationale, tolerances, and conclusions in the report; do
   not create `scientific_intent.yaml` for ordinary cases.

## Keep the case self-contained

Treat self-containment as a hard requirement. The case must own every operational input, script, report source, and local artifact needed to generate inputs, run ELMFIRE, postprocess outputs, evaluate acceptance, and compile its report.

- Do not import, source, copy at runtime, or otherwise depend on `common/`, a sibling case, `__legacy__/`, or suite-level helper scripts.
- A repository tool may discover or invoke the case, but the case must also run directly from its own root.
- External references are acceptable only when necessary for scientific provenance or to identify the ELMFIRE executable. Cite them in the report; do not make them runtime dependencies.
- If useful logic exists elsewhere, copy the smallest necessary logic into the case and rewrite it as clear case-specific code.
- Resolve all case resources relative to the case root, not the caller's working directory.

Read [case_contract.md](references/case_contract.md) before adding or changing files.

## Write readable scripts

Make each Python script understandable without reading another file. Include a short purpose header, a compact parameter block, units and coordinate conventions, descriptive names, docstrings for nontrivial functions, and comments that explain scientific or numerical choices. Avoid framework layers, hidden defaults, clever abstractions, and unexplained constants.

Keep `run_case.sh` as a transparent orchestration script. It should resolve its directory, create local output directories, run preprocessing when needed, invoke `${ELMFIRE_BIN:-elmfire}` for each explicit variant, run postprocessing, and compile the report. Use `${PYTHON_BIN:-python3}` for Python. Do not add argument parsers, executable search logic, resume systems, timeouts, or unrelated diagnostics.

## Produce an auditable decision

Use explicit outcomes: `PASS`, `FAIL`, `NOT RUN`, `INCOMPLETE`, `BLOCKED`, or `NOT EVALUABLE`. A missing executable, missing output, parsing failure, skipped required variant, placeholder value, or absent metric is never a pass. Keep computed values in `outputs/metrics.json` and generated TeX values in `report/metrics_macros.tex`; do not hand-copy results into prose.

Read [report_structure.md](references/report_structure.md) before writing or reviewing the report. Treat the report as the permanent scientific verification record, not a summary of script execution. It must make the verification purpose explicit, derive or justify the expected mathematical or algorithmic behavior, define and justify every metric, and connect those metrics to a reproducible decision.

The report must be self-contained: use only TeX sources and figures inside the case, with external material appearing only as necessary citations. It must compile independently and also be suitable for aggregation into the single ELMFIRE Verification Guide. The master guide is a consumer of case reports, never a dependency of them; do not rely on another case or the guide for definitions, derivations, bibliography entries, macros, figures, or context.

## Validate and register

Before finishing:

1. Confirm the directory name, `case.yaml` `case_id`, `case.json` identifier when present, report title, and registry entry agree.
2. Confirm no runtime path or import reaches outside the case root, except the configured ELMFIRE executable.
3. Run shell syntax checks and parse Python without writing bytecode.
4. Run the repository's dry-run discovery and confirm the case is found exactly once.
5. Verify every required metric maps to a derived expected property, explains why it was selected, has a justified acceptance criterion, and comes from a local artifact.
6. Update `cases/Verification/CASE_REGISTRY.md` without changing existing IDs.
7. Report checks that could not be run. Do not describe an unexecuted scientific case as verified.
