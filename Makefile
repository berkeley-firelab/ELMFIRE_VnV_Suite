.PHONY: new run build-all main clean configure

ELMFIRE_CONFIGS := $(shell find cases -type f -name 'elmfire.data.in')

new:
	@./tools/new_case.sh "$(CASE)"

run:
	@./cases/"$(CASE)"/run_case.sh

build-all:
	@./tools/build_all.sh

main:
	@cd main_report && latexmk -pdf -silent main.tex

clean:
	@find . \( -name "*.aux" -o -name "*.log" -o -name "*.fls" -o -name "*.fdb_latexmk" \) -delete || true
	@find cases -type f -name "figures.tex" -delete || true

configure:
	@if [ -n "$(PATH_TO_GDAL)" ]; then \
		for cfg in $(ELMFIRE_CONFIGS); do \
			echo "Updating $$cfg"; \
			python3 ./tools/refresh_gdal_path.py "$$cfg" "$(PATH_TO_GDAL)"; \
		done; \
	else \
		echo "PATH_TO_GDAL is not set. Usage: make configure PATH_TO_GDAL=/opt/conda/bin"; \
	fi
