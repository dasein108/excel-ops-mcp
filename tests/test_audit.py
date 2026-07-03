from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools


ROOT = Path(__file__).resolve().parents[1]


def make_audit_workbook(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Transactions"
    ws.append(["Vendor", "Amount"])
    ws.append(["Acme", 100])
    ws.append(["Beta", 200])
    wb.save(path)


class AuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cache = self.root / "cache"
        self.workbook = self.root / "audit.xlsx"
        make_audit_workbook(self.workbook)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_tool_audit_records_query_and_failure(self) -> None:
        tools = ExcelMcpTools(ExcelMcpConfig(allowed_roots=[self.root], cache_dir=self.cache))
        opened = tools.spreadsheet_open({"path": str(self.workbook)})
        described = tools.spreadsheet_describe({"session_id": opened["session_id"], "detail": "compact"})
        table = described["sheets"][0]["regions"][0]["table_name"]
        query = tools.spreadsheet_query({"session_id": opened["session_id"], "sql": f'select count(*) as n from "{table}"'})
        failure = tools.spreadsheet_query({"session_id": opened["session_id"], "sql": f'delete from "{table}"'})

        self.assertTrue(query["ok"], query)
        self.assertFalse(failure["ok"], failure)

        events = tools.audit_events(session_id=opened["session_id"])["events"]
        operations = [event["operation"] for event in events]
        self.assertIn("open", operations)
        self.assertIn("describe", operations)
        self.assertIn("query", operations)
        self.assertTrue(any(event["operation"] == "query" and event["error_code"] == "mutating_sql_rejected" for event in events))

    def run_cli(self, *args: str, expect: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, "-m", "excel_mcp.cli", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expect, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def common(self) -> list[str]:
        return ["--allowed-root", str(self.root), "--cache-dir", str(self.cache)]

    def test_cli_audit_survives_separate_invocations(self) -> None:
        opened = self.run_cli("open", str(self.workbook), *self.common())
        session_id = opened["session_id"]
        self.run_cli("sheets", "--session", session_id, *self.common())
        self.run_cli("tables", "--session", session_id, *self.common())
        self.run_cli("query", "--session", session_id, "--sql", 'select count(*) as n from "transactions_ledger_1"', *self.common())
        self.run_cli("query", "--session", session_id, "--sql", 'delete from "transactions_ledger_1"', *self.common(), expect=1)

        audit = self.run_cli("audit", "--session", session_id, *self.common())
        self.assertTrue(audit["ok"], audit)
        operations = [event["operation"] for event in audit["events"]]
        self.assertIn("open", operations)
        self.assertIn("sheets", operations)
        self.assertIn("tables", operations)
        self.assertIn("query", operations)
        self.assertTrue(any(event["operation"] == "query" and event["error_code"] == "mutating_sql_rejected" for event in audit["events"]))


if __name__ == "__main__":
    unittest.main()

