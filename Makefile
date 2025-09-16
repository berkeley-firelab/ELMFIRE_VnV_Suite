-.PHONY: new run build-all main clean


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
