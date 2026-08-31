"""Regression checks for running verification cases outside an ELMFIRE source tree."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "cases" / "Verification"
SPOTTING = VERIFICATION / "coupling_tests"


class VerificationPortabilityTests(unittest.TestCase):
    def spotting_cases(self) -> list[Path]:
        return sorted(SPOTTING.glob("CASE[01][0-9]_*"))[:14]

    def active_cases(self) -> list[Path]:
        return sorted(
            path.parent
            for category in ("unit_tests", "coupling_tests")
            for path in (VERIFICATION / category).glob("CASE*/run_case.sh")
        )

    def test_all_fourteen_spotting_cases_are_present(self) -> None:
        cases = self.spotting_cases()
        self.assertEqual(len(cases), 14)
        self.assertEqual(
            [case.name[:6] for case in cases],
            [f"CASE{number:02d}" for number in range(1, 15)],
        )

    def test_spotting_preprocessors_do_not_search_elmfire_source_tree(self) -> None:
        forbidden = ("build/source", "repository_root", "feature_found_in_source")
        for case in self.spotting_cases():
            for script in (case / "scripts").glob("*.py"):
                text = script.read_text(encoding="utf-8")
                for token in forbidden:
                    self.assertNotIn(token, text, f"{script} contains {token!r}")

    def test_spotting_templates_use_only_reader_supported_domain_metadata(self) -> None:
        for case in self.spotting_cases():
            namelist = case / "elmfire.data.in"
            if namelist.is_file():
                self.assertNotIn("&COMPUTATIONAL_DOMAIN",
                                 namelist.read_text(encoding="utf-8"), case.name)

    def test_runnable_spotting_cases_own_required_model_tables(self) -> None:
        for case in self.spotting_cases():
            if case.name.startswith("CASE13_"):
                continue  # Capability-only design; it does not launch ELMFIRE.
            for name in ("fuel_models.csv", "building_fuel_models.csv"):
                self.assertTrue((case / "data" / "misc" / name).is_file(),
                                f"{case.name} is missing data/misc/{name}")

    def test_case_runners_are_location_independent(self) -> None:
        absolute_path = re.compile(r"/(?:Users|home|global)/")
        for case in self.active_cases():
            runner = (case / "run_case.sh").read_text(encoding="utf-8")
            self.assertIn("BASH_SOURCE[0]", runner, case.name)
            self.assertIsNone(absolute_path.search(runner), case.name)

    def test_adapter_modules_are_case_local(self) -> None:
        for case in self.active_cases():
            scripts = case / "scripts"
            combined = "\n".join(
                path.read_text(encoding="utf-8") for path in scripts.glob("*.py")
            )
            for module in ("case_adapter", "guide_verification"):
                if re.search(rf"(?:from|import)\s+{module}\b", combined):
                    self.assertTrue((scripts / f"{module}.py").is_file(),
                                    f"{case.name} imports non-local {module}")


if __name__ == "__main__":
    unittest.main()
