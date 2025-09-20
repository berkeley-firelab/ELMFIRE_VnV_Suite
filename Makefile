.PHONY: new run build-all main clean configure
ELMFIRE_CONFIGS := $(wildcard cases/*/elmfire.data.in)

new:
@./tools/new_case.sh $(CASE)


run:
@./cases/$(CASE)/run_case.sh


build-all:
@./tools/build_all.sh


main:
@cd main_report && latexmk -pdf -silent main.tex


clean:
@find . -name "*.aux" -o -name "*.log" -o -name "*.fls" -o -name "*.fdb_latexmk" -delete || true
@find cases -type f -name "figures.tex" -delete || true

configure:
ifndef PATH_TO_GDAL
	$(error PATH_TO_GDAL is not set. Usage: make configure PATH_TO_GDAL=/opt/conda/bin)
endif
	@for cfg in $(ELMFIRE_CONFIGS); do \
		printf 'Updating %s\n' "$$cfg"; \
		python3 - "$$cfg" "$(PATH_TO_GDAL)" <<'PY'; \
import sys, pathlib, re
path = pathlib.Path(sys.argv[1])
target = sys.argv[2]
text = path.read_text()
pattern = re.compile(r"(PATH_TO_GDAL\s*=\s*)'[^']*'")
updated, count = pattern.subn(lambda m: f"{m.group(1)}'{target}'", text)
if not count:
    raise SystemExit(f"PATH_TO_GDAL line not found in {path}")
path.write_text(updated)
PY \
	done
