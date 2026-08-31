#!/usr/bin/env python3
"""Unit tests for deterministic namelist parsing and schema extraction."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from extract_namelist_schema import extract  # noqa: E402
from namelist_lib import (  # noqa: E402
    assignment_map, parse_namelist, parse_scalar, schema_paths, values_equal,
)


class NamelistTests(unittest.TestCase):
    def test_parser_preserves_array_identity_and_quoted_comment_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "elmfire.data.in"
            path.write_text(
                "&SPOTTING\n"
                "  GENERATION_MODEL = 'PER-MW' ! reviewed selector\n"
                "  SOURCE_FUEL_IGN_MULT(91) = 1.0\n"
                "  ALPHA = 1, BETA = 2\n"
                "  LABEL = 'value!not-comment'\n/\n",
                encoding="utf-8",
            )
            parsed = assignment_map(parse_namelist(path))
            self.assertEqual(parse_scalar(parsed["SPOTTING.GENERATION_MODEL"].value), "PER-MW")
            self.assertEqual(parsed["SPOTTING.SOURCE_FUEL_IGN_MULT(91)"].base_path,
                             "SPOTTING.SOURCE_FUEL_IGN_MULT")
            self.assertEqual(parse_scalar(parsed["SPOTTING.LABEL"].value), "value!not-comment")
            self.assertEqual(parse_scalar(parsed["SPOTTING.ALPHA"].value), 1)
            self.assertEqual(parse_scalar(parsed["SPOTTING.BETA"].value), 2)

    def test_numeric_and_boolean_comparison(self) -> None:
        self.assertTrue(values_equal(parse_scalar("1.0D+00"), 1))
        self.assertTrue(values_equal(parse_scalar(".TRUE."), True))
        self.assertFalse(values_equal(parse_scalar(".FALSE."), True))

    def test_schema_extracts_continued_group_and_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "build/source/elmfire_namelists.f90"
            source.parent.mkdir(parents=True)
            source.write_text(
                "MODULE X\nCONTAINS\nSUBROUTINE READ_TEST\n"
                "NAMELIST /TEST/ ALPHA, &\n  BETA\n"
                "ALPHA = 1.0\nBETA = 'X'\n"
                "READ(LUINPUT,NML=TEST,IOSTAT=IOS)\n"
                "END SUBROUTINE\nEND MODULE\n",
                encoding="utf-8",
            )
            schema = extract(source, root)
            self.assertEqual(schema_paths(schema), {"TEST.ALPHA", "TEST.BETA"})
            self.assertEqual(schema["groups"]["TEST"]["variables"]["ALPHA"]["default"], "1.0")


if __name__ == "__main__":
    unittest.main()
