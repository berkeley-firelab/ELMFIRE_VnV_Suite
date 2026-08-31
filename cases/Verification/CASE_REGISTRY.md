# Verification case registry

This is the authoritative mapping of stable verification identifiers to case purposes and locations. Identifiers are global across verification categories, are never reused, and remain independent of publication numbering.

| ID | Category | Verification purpose |
| --- | --- | --- |
| `CASE01_BET` | coupling | Biomass emission-time resolution independence |
| `CASE02_FGR` | coupling | Finite-duration firebrand generation |
| `CASE03_ETC` | coupling | Eulerian transport convergence |
| `CASE04_STI` | coupling | Steady transport and immediate ignition |
| `CASE05_TDW` | coupling | Firebrand transport in time-dependent wind |
| `CASE06_F2D` | coupling | Two-dimensional firebrand-driven spread |
| `CASE07_IPC` | coupling | Ignition probability and SFT convergence |
| `CASE08_FBC` | coupling | Deposited firebrand consumption |
| `CASE09_MMD` | coupling | Mixed-mode ignition-delay effects |
| `CASE10_WSR` | coupling | WUI structural resolution sensitivity |
| `CASE11_WSC` | coupling | WUI surface-coupling synchronization |
| `CASE12_TRS` | coupling | WUI temporal-resolution sensitivity |
| `CASE13_PRM` | coupling | WUI parametric response maps |
| `CASE14_SRS` | coupling | Two-dimensional spatial-resolution sensitivity |
| `CASE15_CRO` | unit | Constant rate of spread |
| `CASE16_NSP` | unit | No-spread limiting behavior |
| `CASE17_SCV` | unit | Spatial convergence |
| `CASE18_TCV` | unit | Temporal convergence |
| `CASE19_WTH` | coupling | Transient WU-E heat flux |
| `CASE20_PIG` | coupling | Point ignition and isotropic spread |
| `CASE21_WDE` | coupling | Wind-driven elliptical spread |
| `CASE22_VSL` | coupling | Spread across opposing valley slopes |
| `CASE23_FQD` | coupling | Spatially varying fuel quadrants |
| `CASE24_CXI` | coupling | Combined fuel, slope, and wind interactions |
| `CASE25_MQD` | coupling | Spatially varying moisture quadrants |
| `CASE26_CNF` | coupling | Surface, passive-crown, and active-crown fire |
| `CASE27_FBT` | coupling | Lagrangian firebrand generation and transport |
| `CASE28_OVA` | coupling | Overnight spread-rate adjustment |
| `CASE29_SUP` | coupling | Initial- and extended-attack suppression |

## Naming rules

- A case directory and its machine-readable `case_id` use `CASE##_<PURPOSE>`.
- `<PURPOSE>` is a short, stable, uppercase abbreviation.
- Report titles use `Case ##: <descriptive purpose>`.
- A rename does not change a case's scientific inputs, metrics, tolerances, or conclusions.
- Add new cases with the next unused global number; do not fill gaps by renumbering existing cases.

The former GUIDE names and source provenance remain documented inside `CASE20_PIG` through `CASE29_SUP` and under `coupling_tests/__legacy__/guide_cases/`.
