.PHONY: new run run-all build-all main clean configure

# Find all ELMFIRE config files
ELMFIRE_CONFIGS := $(shell find cases -type f -name 'elmfire.data.in')

# Create a new case: make new CASE=case_id
new:
	@./tools/new_case.sh "$(CASE)"

# Run a single case locally: make run CASE=case_id
run:
	@./cases/"$(CASE)"/run_case.sh

# Run all cases sequentially (or with Slurm if SLURM=1)
run-all:
ifeq ($(SLURM),1)
	@python3 ./tools/run_all_cases.py --slurm
else
	@python3 ./tools/run_all_cases.py
endif

# Rebuild all utilities
build-all:
	@./tools/build_all.sh

# Build the main report
main:
	@cd main_report && latexmk -pdf -silent main.tex

# Clean LaTeX and generated files
clean:
	@find . \( -name "*.aux" -o -name "*.log" -o -name "*.fls" -o -name "*.fdb_latexmk" \) -delete || true
	@find cases -type f -name "figures.tex" -delete || true

# Update GDAL paths + ensure all *.sh are executable
configure:
	@if [ -n "$(PATH_TO_GDAL)" ]; then \
		for cfg in $(ELMFIRE_CONFIGS); do \
			echo "Updating $$cfg"; \
			python3 ./tools/refresh_gdal_path.py "$$cfg" "$(PATH_TO_GDAL)"; \
		done; \
	else \
		echo "PATH_TO_GDAL is not set. Usage: make configure PATH_TO_GDAL=/opt/conda/bin"; \
	fi
	@echo "[INFO] Making all shell scripts in $(ROOT_DIR) executable..."
	@find "$(ROOT_DIR)" -type f -name "*.sh" -exec chmod +x {} \;
