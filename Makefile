.PHONY: new run run-all run-verification run-validation build-all \
	report-inputs verification-report validation-report reports main clean configure

SUITE ?= all

# Find all ELMFIRE config files
ELMFIRE_CONFIGS := $(shell find cases -type f -name 'elmfire.data.in')

# Create a new case: make new CASE=case_id
new:
	@./tools/new_case.sh "$(CASE)"

# Run a single case locally: make run CASE=case_id
run:
	@./cases/"$(CASE)"/run_case.sh

# Run selected cases sequentially (or with Slurm if SLURM=1).
# Examples: make run-all SUITE=verification; make run-all SUITE=validation
run-all:
ifeq ($(SLURM),1)
	@python3 ./tools/run_all.py --suite "$(SUITE)" --slurm
else
	@python3 ./tools/run_all.py --suite "$(SUITE)"
endif

run-verification:
	@python3 ./tools/run_all.py --suite verification $(if $(filter 1,$(SLURM)),--slurm,)

run-validation:
	@python3 ./tools/run_all.py --suite validation $(if $(filter 1,$(SLURM)),--slurm,)

# Rebuild all utilities
build-all:
	@./tools/build_all.sh

# Generate aggregate include lists and scientific decision tables.
report-inputs:
	@python3 ./tools/generate_summary_reports.py

verification-report: report-inputs
	@cd main_report && latexmk -pdf -silent verification_report.tex

validation-report: report-inputs
	@cd main_report && latexmk -pdf -silent validation_report.tex

reports: verification-report validation-report

# Backward-compatible aggregate-report target.
main: reports

# Remove simulation rasters, logs, verification variants, Slurm files, LaTeX
# auxiliaries, and ELMFIRE scratch artifacts. Preserve compiled reports and all
# report-build inputs, including figures, result JSON, and generated TeX.
clean:
	@python3 ./tools/clean_artifacts.py --apply

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
