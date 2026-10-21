# GOFER source collection and legacy construction material

The four GOFER validation cases now live in
[`../landscape_scale/`](../landscape_scale/README.md). Their documentation has
been merged into that README, including data sources, configurations,
dependencies, commands, and remaining reproducibility requirements.

`tools/build_cases.py` and `tools/case_files/` remain here as legacy construction
material. No relocated case uses them at runtime. Each case owns its scripts,
supporting functions, configuration, and report resources.

Do not rerun the legacy builder to maintain the relocated cases: it still writes
case directories here and would recreate duplicate runnable cases. Make changes
in each case's own directory under `landscape_scale/`.

## Supplied source archive

`data/archive_payload/` retains inputs and observations for the other 24 GOFER
fires, plus the original collection-level preparation scripts, retrieval log,
and fire table from the user-supplied `ELMFIRE_GOFER_validation.tar.gz` archive.
These are source materials, not additional runnable validation cases. Original
scripts are retained as evidence; no current case executes them.

The four active fires' inputs, observations, and available historical outputs
were placed inside their respective `landscape_scale/<case>/data/archive_payload/`
directories. Collection-level provenance was also copied into each active case,
so none depends on this collection. `data/archive_inventory.json` records the
archive SHA-256 and the destination, size, and SHA-256 of every scientific/source
file. macOS resource-fork files and `.DS_Store` were omitted. The original
compressed archive remains unchanged at its supplied location in Downloads.

The expanded bulk data are local and ignored by Git. Each active case includes
its own `scripts/stage_data.py` to restore its files from the exact pinned
archive. To restore the remaining collection, extract that same archive and
retain the 24 other fire directories and collection-level files here; do not
run the archived launchers as part of the validation suite.
