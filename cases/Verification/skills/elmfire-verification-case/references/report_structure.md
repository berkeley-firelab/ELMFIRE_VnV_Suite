# Verification report structure

Write the report as a self-contained scientific verification argument for a reader who knows ELMFIRE but has not read the source publication, another case report, or the implementation notes used by the author.

Use numbered `\\section{...}` commands with these exact names and in this order. Do not merge or reorder them around the chronology of file generation.

## 1. Verification purpose

State:

- the physical, mathematical, numerical, or algorithmic behavior being verified;
- why that behavior matters to ELMFIRE;
- the exact implementation path exercised, including relevant modules, routines, selectors, or state updates;
- the defects the case is capable of exposing;
- what is controlled, varied, enabled, and disabled; and
- why this is implementation verification rather than physical validation.

End with one precise verification question naming the observable, required variants or parameter range, and acceptance condition. Do not describe the case only by its publication origin or input geometry.

## 2. Mathematical formulation and numerical implementation

Present the governing equations, variables, units, assumptions, coordinate and sign conventions, discretization, timestep and mesh dependence, update order, source terms, boundary treatment, and output semantics needed to understand the test.

Connect the formulation to the actual ELMFIRE implementation. Explain what the relevant namelist settings and input fields cause the code to do; do not merely list filenames or routine names.

When equations do not adequately describe the behavior, provide readable pseudocode, an algorithm summary, state-transition logic, or a discrete update equation. If no nontrivial mathematical derivation applies, say so and explain the algorithmic property or invariant that replaces it.

## 3. Derivation of expected behavior

Derive the expectation for the configured experiment, not just the general model. Use the appropriate form of reference evidence:

- an analytical or manufactured solution;
- a conservation or symmetry property;
- a limiting behavior or invariant;
- a convergence order or mesh/time-step trend;
- an independently calculated algorithmic result;
- a controlled comparison between variants; or
- another documented known response.

Show enough intermediate reasoning that the expected value, profile, ordering, trend, or state can be reproduced. Identify approximations and distinguish exact expectations from numerical estimates. If the reference depends on run-derived quantities, explain how those quantities enter the reference without making the simulation output its own circular standard.

Do not rely on unexplained phrases such as “the thesis value,” “Equation 3.11,” or “the expected curve.” Restate and derive the material needed by this case, then cite the external source for provenance.

## 4. Verification metrics and acceptance criteria

Define metrics only after deriving the expected behavior. Trace every metric to one expected property and explain both how and why it was selected.

For every metric document:

- its name and mathematical formula;
- the expected property it measures;
- why it is sensitive to the defect or implementation error of interest;
- why it is preferable to plausible alternatives and robust to irrelevant variation;
- the source output field and exact file-selection rule;
- spatial region, masks, nodata handling, and buffer exclusion;
- temporal selection or ensemble statistic;
- normalization and aggregation;
- required output completeness;
- tolerance or limit and the scientific or numerical basis for that tolerance; and
- the component pass/fail rule.

Use a compact traceability table when several metrics are present, with columns such as expected property, observable, metric, selection rationale, tolerance rationale, and component decision.

State the complete Boolean rule for the overall decision. A metric must not be chosen merely because it is easy to extract or visually attractive. Missing, stale, malformed, or insufficient outputs are non-passing and `NOT EVALUABLE`; they are never evidence of a pass.

## 5. Simulation configuration and predicted outcome

Document enough information to reproduce the experiment: domain and coordinate system, physical and buffer cells, grid resolution, timestep, initialization or ignition, fuels, terrain, moisture, weather, relevant model selectors, coupled or disabled processes, variants, duration, and output cadence.

Use a table with columns for parameter, configured value, units, and role in isolating the behavior. Include a whole-domain configuration figure when nonuniform or localized fields control the test. Before showing actual output, state the predicted qualitative appearance and quantitative values of every result that will be used in the decision.

## 6. Actual simulation results

Present only results read from actual case-local artifacts. Record the executable or source revision when available, selected output files, completed and required variants, and incomplete or failed runs.

For a completed spatial case, include at least one representative whole-domain result before or beside derived profiles, convergence curves, tables, or scalar summaries. Every figure must identify the data source, reference where applicable, physical units, variant, output time or ensemble statistic, and acceptance limits. Do not manufacture results, substitute a synthetic curve for missing output, or show only a cropped region when domain behavior matters.

## 7. Calculated metrics and verification decision

Present one row per acceptance component with the metric, expected value or limit, calculated value, and component status. State the overall result prominently as `PASS`, `FAIL`, or `NOT EVALUABLE`; use the more specific workflow states `NOT RUN`, `INCOMPLETE`, or `BLOCKED` in metadata when applicable.

Source values and the decision directly from `outputs/metrics.json` through generated `metrics_macros.tex`. Do not recompute, hand-copy, or override the decision in LaTeX.

## 8. Technical interpretation

Explain why the result passed, failed, or could not be evaluated. Relate the evidence to the derivation and metric rationale. Distinguish among source-code defects, incorrect configuration, inadequate resolution, statistical variability, output selection, postprocessing errors, reference limitations, and missing output. Do not merely restate the table or describe the plot.

## 9. Scope and limitations

Conclude with what was demonstrated, what remains unverified, assumptions restricting the conclusion, additional variants or observables that may be needed, and whether the evidence supplies code verification only or any limited physical-validation evidence.

Maintain this narrative progression:

```text
purpose -> formulation or algorithm -> derived expectation -> justified metrics
        -> configuration -> predicted outcome -> actual results -> decision
        -> interpretation and limitations
```

## Self-contained LaTeX project

Use `case_metadata.tex` as the single source for `CaseNumber`, `CaseID`, `CaseTitle`, and `PurposeAbbreviation`. Use `case_macros.tex` for stable case constants, `technical_macros.tex` for technical definitions, generated `metrics_macros.tex` for computed results, `case_body.tex` for the nine-section argument, and `case_report.tex` for the standalone wrapper and preamble. Keep all six files present, using intentionally empty macro files when appropriate.

Every `\\input`, `\\include`, `\\includegraphics`, bibliography, and style dependency must resolve inside the case directory. Define every acronym, symbol, and case-specific term locally. External scientific material may be cited when necessary, but the case must restate the formulation or reference result needed to understand and reproduce its verification logic.

Require every metric key used by the report to exist in `metrics_macros.tex`. Render a conspicuous `MISSING` marker for an absent key and treat that marker as report-validation failure.

## ELMFIRE Verification Guide integration

Each case report has two obligations:

1. It must compile independently from its own `report/` directory when no other case and no master-report source is available.
2. It must be consumable by the repository's master build to form the single ELMFIRE Verification Guide.

The master guide is an aggregator, not a source of case content. A case must not depend on the guide for its preamble fragments, definitions, macros, bibliography entries, figures, derivation, or scientific context. Prefer aggregation of the successfully compiled standalone report artifact when that avoids macro, label, bibliography, or package collisions. If the repository instead includes `case_body.tex` directly, keep the body free of document-level commands, use case-prefixed labels and macro names, and ensure the master explicitly loads the case's local metadata and macro files.

Use consistent terminology, units, section names, and status vocabulary across cases. Do not assume that the reader encountered another case first, and do not create cross-case references needed to understand or evaluate the current case. Cross-case comparisons may be added to the master guide as separate synthesis material, but they cannot replace a case's local derivation or decision argument.
