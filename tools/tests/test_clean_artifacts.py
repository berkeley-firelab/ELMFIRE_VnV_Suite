import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "clean_artifacts.py"
SPEC = importlib.util.spec_from_file_location("clean_artifacts", MODULE_PATH)
CLEAN = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = CLEAN
SPEC.loader.exec_module(CLEAN)


class ArtifactClassificationTests(unittest.TestCase):
    def test_all_cases_share_cleanup_rules_and_source_material_remains(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / "cases/Verification/coupling_tests/CASE01_BET"
            report = case / "report"
            outputs = case / "outputs"
            logs = case / "logs"
            report.mkdir(parents=True)
            outputs.mkdir()
            logs.mkdir()

            disposable = {
                case / "run_case_slurm.sh",
                case / "slurm-elmfire-CASE01_BET-123.stdout",
                case / "slurm-elmfire-CASE01_BET-123.stderr",
                report / "case_report.aux",
                report / "case_report.pdf",
                report / "metrics_macros.tex",
                case / ".DS_Store",
            }
            preserved = {
                report / "case_report.tex",
                report / "case_body.tex",
                case / "elmfire.data.in",
            }
            runtime_products = {
                outputs / "metrics.json",
                outputs / "time_of_arrival.tif",
                logs / "elmfire.stderr",
            }
            for path in disposable | preserved | runtime_products:
                path.write_text("test", encoding="utf-8")

            original_root = CLEAN.ROOT_DIR
            try:
                CLEAN.ROOT_DIR = root
                files, runtime_directories, _ = CLEAN.cleanup_inventory()
            finally:
                CLEAN.ROOT_DIR = original_root

            self.assertEqual(set(files), disposable)
            self.assertEqual(set(runtime_directories), {logs, outputs})
            self.assertTrue(preserved.isdisjoint(files))

    def test_common_slurm_headers_are_not_generated_artifacts(self) -> None:
        self.assertFalse(CLEAN.is_slurm_artifact(Path("slurm_verification_head.txt")))
        self.assertFalse(CLEAN.is_slurm_artifact(Path("slurm_validation_head.txt")))
        self.assertTrue(CLEAN.is_slurm_artifact(Path("slurm-123.out")))

    def test_runtime_contents_are_removed_but_directories_and_inputs_remain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / "cases/Validation/landscape_scale/fire"
            scratch = case / "logs/scratch"
            nested = scratch / "rank-01"
            outputs = case / "outputs"
            figures = case / "figures"
            input_directory = case / "data/inputs"
            nested.mkdir(parents=True)
            outputs.mkdir(parents=True)
            figures.mkdir(parents=True)
            input_directory.mkdir(parents=True)
            (scratch / "temporary.bsq").write_text("scratch", encoding="utf-8")
            (nested / "temporary.hdr").write_text("scratch", encoding="utf-8")
            scientific_output = outputs / "time_of_arrival.tif"
            scientific_output.write_text("result", encoding="utf-8")
            (figures / "arrival_time.pdf").write_text("plot", encoding="utf-8")
            source_input = input_directory / "fuel.tif"
            source_input.write_text("input", encoding="utf-8")

            original_root = CLEAN.ROOT_DIR
            try:
                CLEAN.ROOT_DIR = root
                _, runtime_directories, _ = CLEAN.cleanup_inventory()
                cleaned = CLEAN.empty_runtime_directories(runtime_directories, apply=True)
            finally:
                CLEAN.ROOT_DIR = original_root

            self.assertEqual(cleaned, 3)
            self.assertEqual(set(runtime_directories), {figures, case / "logs", outputs})
            for runtime_directory in runtime_directories:
                self.assertTrue(runtime_directory.is_dir())
                self.assertEqual(list(runtime_directory.iterdir()), [])
            self.assertEqual(source_input.read_text(encoding="utf-8"), "input")

    def test_legacy_runtime_products_are_not_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_scratch = root / "cases/Verification/__legacy__/case/scratch"
            legacy_outputs = root / "cases/Validation/__legacy__/case/outputs"
            legacy_scratch.mkdir(parents=True)
            legacy_outputs.mkdir(parents=True)
            (legacy_scratch / "reference.bsq").write_text("reference", encoding="utf-8")
            (legacy_outputs / "reference.tif").write_text("reference", encoding="utf-8")
            legacy_metadata = legacy_outputs.parent / ".DS_Store"
            legacy_metadata.write_text("reference", encoding="utf-8")

            original_root = CLEAN.ROOT_DIR
            try:
                CLEAN.ROOT_DIR = root
                files, runtime_directories, _ = CLEAN.cleanup_inventory()
            finally:
                CLEAN.ROOT_DIR = original_root

            self.assertNotIn(legacy_metadata, files)
            self.assertEqual(runtime_directories, [])
            self.assertTrue((legacy_scratch / "reference.bsq").is_file())
            self.assertTrue((legacy_outputs / "reference.tif").is_file())

    def test_aggregate_report_pdfs_are_generated_but_sources_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            main_report = root / "main_report"
            main_report.mkdir()
            pdf = main_report / "verification_report.pdf"
            source = main_report / "verification_report.tex"
            pdf.write_text("generated", encoding="utf-8")
            source.write_text("source", encoding="utf-8")

            original_root = CLEAN.ROOT_DIR
            try:
                CLEAN.ROOT_DIR = root
                classified = set(CLEAN.artifact_files())
            finally:
                CLEAN.ROOT_DIR = original_root

            self.assertIn(pdf, classified)
            self.assertNotIn(source, classified)
