from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
REPO_ROOT = Path(__file__).resolve().parents[1]


class TraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tools = ExcelMcpTools(
            ExcelMcpConfig(allowed_roots=[REPO_ROOT], cache_dir=Path(self.tmp.name) / ".cache")
        )
        response = self.tools.spreadsheet_open({"path": str(EXAMPLES / "saas.xlsx")})
        self.session_id = response["session_id"]

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_trace_cross_sheet_range_precedent(self) -> None:
        # Dashboard Total Revenue = SUM('P&L Projection'!B7:M7)
        r = self.tools.spreadsheet_trace(
            {"session_id": self.session_id, "sheet": "Dashboard", "cell": "B5", "depth": 1}
        )
        self.assertTrue(r["ok"], r)
        target = r["target"]
        self.assertEqual(target["value"], 1458480)
        self.assertIn("SUM", target["formula"])
        prec = target["precedents"][0]
        self.assertEqual(prec["sheet"], "P&L Projection")
        self.assertTrue(prec["is_range"])
        self.assertEqual(prec["values"][0], 87680)

    def test_trace_net_income_two_line_items(self) -> None:
        # Net Income = B47 (EBT) - B49 (Income Tax)
        r = self.tools.spreadsheet_trace(
            {"session_id": self.session_id, "sheet": "P&L Projection", "cell": "B51", "depth": 1}
        )
        self.assertEqual(r["target"]["formula"], "=B47-B49")
        refs = {p["cell"] for p in r["target"]["precedents"]}
        self.assertEqual(refs, {"B47", "B49"})

    def test_trace_depth_recurses(self) -> None:
        r = self.tools.spreadsheet_trace(
            {"session_id": self.session_id, "sheet": "P&L Projection", "cell": "B51", "depth": 2}
        )
        b47 = next(p for p in r["target"]["precedents"] if p["cell"] == "B47")
        # B47 (EBT) = B42 - B45, so depth 2 exposes its own precedents.
        self.assertIn("precedents", b47)
        self.assertTrue(len(b47["precedents"]) >= 1)

    def test_trace_bad_sheet_errors(self) -> None:
        r = self.tools.spreadsheet_trace(
            {"session_id": self.session_id, "sheet": "Nope", "cell": "A1", "depth": 1}
        )
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["code"], "sheet_not_found")


class MatrixOrientationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tools = ExcelMcpTools(
            ExcelMcpConfig(allowed_roots=[REPO_ROOT], cache_dir=Path(self.tmp.name) / ".cache")
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_projection_sheets_flagged_matrix(self) -> None:
        session = self.tools.spreadsheet_open({"path": str(EXAMPLES / "saas.xlsx")})["session_id"]
        described = self.tools.spreadsheet_describe({"session_id": session})
        orientations = {
            sheet["name"]: [r["orientation"] for r in sheet["regions"]]
            for sheet in described["sheets"]
        }
        # The time-series projection sheets have at least one matrix region.
        self.assertIn("matrix", orientations["Revenue Model"])
        self.assertIn("matrix", orientations["P&L Projection"])
        # The stacked key/value Assumptions sheet is not a matrix.
        self.assertNotIn("matrix", orientations["Assumptions"])

    def test_matrix_columns_named_by_time_axis(self) -> None:
        session = self.tools.spreadsheet_open({"path": str(EXAMPLES / "saas.xlsx")})["session_id"]
        tables = self.tools.spreadsheet_describe({"session_id": session})
        pl = next(s for s in tables["sheets"] if s["name"] == "P&L Projection")
        band = next(r for r in pl["regions"] if r["orientation"] == "matrix" and r["row_count"] > 1)
        names = [c["name"] for c in band["columns"]]
        self.assertEqual(names[0], "line_item")
        self.assertIn("jan", names)
        self.assertIn("dec", names)

    def test_year1_total_matches_manual_sum(self) -> None:
        try:
            import duckdb  # noqa: F401
        except Exception:
            self.skipTest("duckdb is not installed")
        session = self.tools.spreadsheet_open({"path": str(EXAMPLES / "saas.xlsx")})["session_id"]
        # Infrastructure COGS Year-1 total = sum of Jan..Dec = 226044.
        r = self.tools.spreadsheet_query(
            {
                "session_id": session,
                "sql": "select line_item, year_1_total from p_l_projection_table_3 "
                "where line_item like '%Infrastructure%'",
            }
        )
        self.assertTrue(r["ok"], r)
        self.assertAlmostEqual(float(r["rows"][0]["year_1_total"]), 226044.0, places=0)


if __name__ == "__main__":
    unittest.main()
