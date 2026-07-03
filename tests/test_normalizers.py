from __future__ import annotations

import unittest

from excel_mcp.normalizers import parse_percent_value


class PercentNormalizerTests(unittest.TestCase):
    def test_numeric_fraction(self) -> None:
        parsed = parse_percent_value(0.34)
        self.assertEqual(parsed.kind, "number")
        self.assertEqual(parsed.max, 0.34)

    def test_percent_range(self) -> None:
        parsed = parse_percent_value("10-30%")
        self.assertEqual(parsed.kind, "range")
        self.assertEqual(parsed.min, 0.10)
        self.assertEqual(parsed.max, 0.30)

    def test_russian_range_text(self) -> None:
        parsed = parse_percent_value("от 11% до 80%+")
        self.assertEqual(parsed.kind, "range")
        self.assertEqual(parsed.min, 0.11)
        self.assertEqual(parsed.max, 0.80)

    def test_formula_is_not_numeric(self) -> None:
        parsed = parse_percent_value("=AVERAGE(D3:D10)")
        self.assertEqual(parsed.kind, "formula")
        self.assertIsNone(parsed.max)


if __name__ == "__main__":
    unittest.main()

