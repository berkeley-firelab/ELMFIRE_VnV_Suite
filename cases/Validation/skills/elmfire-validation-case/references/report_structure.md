# Validation report structure

Write a standalone scientific validation record for a reader who has not read
the source paper, thesis, dataset documentation, or another case report. Use the
following numbered sections in order.

## 1. Validation objective and scope

Identify the event or experiment, physical behavior, ELMFIRE pathways exercised,
prediction quantities, reference observations, validation question, intended
claim, and exclusions. State whether any evaluated data were also used for
calibration.

## 2. Reference event, experiment, and observations

Describe geometry, chronology, environmental context, experimental apparatus or
historical event, sensors or observation products, sampling, uncertainty,
coverage, missingness, detection thresholds and citations. Explain what each
observation represents and what it cannot establish.

## 3. Input data provenance and characterization

Provide a source table for meteorology, terrain, fuels, moisture, canopy,
buildings/WUI, ignition, barriers, interventions and observations. Include
provider/citation, version/vintage, native resolution, units, CRS/time basis,
processing and uncertainty. Present the input statistics and figures required
by `statistics_and_visualization.md` so the reader understands the modeled
conditions rather than only filenames.

## 4. Model configuration and rationale

Document domain, mesh, duration, timestep, ensemble design, random seed,
ignition, outputs and active/disabled physical pathways. For consequential
namelist choices, state the configured value, units, role, evidence source and
basis label: documented, derived, inferred, user-specified or calibrated.
Explain spotting, WUI/building and other specialized parameters explicitly.
Unresolved unsupported choices are blocking.

## 5. Preprocessing and reproducibility

Explain extraction, integrity verification, projection, clipping, resampling,
interpolation, rasterization, unit conversion, time alignment, nodata treatment,
derived fields and software dependencies. Distinguish immutable raw evidence
from generated model inputs.

## 6. Validation metrics and comparison framework

Define and justify every metric. Give formulas, data fields, file/time/member
selection, spatial masks, alignment method, aggregation, uncertainty treatment,
baseline and acceptance rule. Explain why each metric is sensitive to the
phenomenon of interest and why plausible alternatives were not sufficient.
State the complete status rule before presenting calculated results.

## 7. Simulation results and field-level comparison

Identify source revision/executable and run completeness. Show representative
whole-domain two-dimensional simulation fields with units and time/member
context. Compare them with observation or experiment fields when applicable.
Never substitute synthetic or historical figures for missing current outputs.

## 8. Integrated statistics and calculated metrics

Present higher-level time histories, ensemble distributions, area growth,
structure damage, heat exposure or other case-relevant summaries. Then present
one row per metric with baseline/observation, calculated value, uncertainty or
limit, and component status. Source values mechanically from
`outputs/metrics.json` through `metrics_macros.tex`.

## 9. Interpretation and uncertainty

Explain agreements and discrepancies using the evidence. Distinguish model-form
error, parameter uncertainty, input uncertainty, observation limitations,
resolution, stochastic variability, alignment choices and postprocessing error.
Do not equate visual agreement with validation.

## 10. Conclusions and limitations

State exactly what the evidence supports, what remains unevaluated, whether the
case passed a predeclared criterion or was only characterized, calibration
dependence, transferability limits and recommended additional evidence.

## Standalone and guide-compatible report

Use the six-file report project defined in `case_contract.md`. The case report
must compile independently and remain suitable for aggregation into an ELMFIRE
Validation Guide. Define symbols, acronyms, citations and case-specific macros
locally. Every calculated value must originate from case-local artifacts; absent
values must render visibly as missing and cannot produce a passing status.
