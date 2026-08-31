# Coupling Tests

The tests included in this folder are designed to evaluate the coupled behavior of multiple subroutines through more complex cases. For example, the subroutine LEVEL_SET_PROPAGATION in elmfire_level_set.f90 invokes numerous other subroutines and functions, making simple input–output verification infeasible. Instead, synthetic scenarios with known solutions will be constructed. Given the complexity of these functions, verification cannot be achieved through a single case; rather, a suite of cases will be developed to assess their behavior under varying conditions. Although it is not possible to anticipate all error-inducing situations, this category of test cases will remain adaptive, with new cases added whenever problems are identified and resolved. If addressing such problems requires introducing new independent subroutines or functions, those components will also be subjected to functionality verification through independent unit tests.

All active coupling cases use the global identifiers registered in
`../CASE_REGISTRY.md`. `CASE01_BET` through `CASE14_SRS` are the Eulerian
spotting-model suite. `CASE20_PIG` through `CASE29_SUP` are repository-native
reformulations of the simplified end-to-end scenarios in Section 3.2 of the
ELMFIRE Guide. Their original harness and reference material are retained under
`__legacy__/` and are not active cases.

Use `../skills/elmfire-verification-case/SKILL.md` when creating or reviewing a
general verification case. The historical spotting-specific skill remains
under `__legacy__/spotting_model/` as domain reference material.

Each active case is runnable from a standalone V&V-suite checkout. Runtime
scripts resolve files from their own case root and use only the configured
`ELMFIRE_BIN` executable; they do not inspect or copy files from an ELMFIRE
source checkout. Spotting cases that launch ELMFIRE therefore retain their
reviewed fuel-model tables under their own `data/misc/` directory. Prospective
features are enabled only by explicit, reviewed case metadata, never by a
runtime source-code search.
