from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SUITE = REPO_ROOT / "evals" / "saas_v1"
WORKBOOK = REPO_ROOT / "examples" / "saas.xlsx"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_checks", REPO_ROOT / "evals" / "run_checks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DeterministicChecksTests(unittest.TestCase):
    """The structured checks must be exact and byte-stable — no model, no sampling."""

    def setUp(self) -> None:
        try:
            import duckdb  # noqa: F401
        except Exception:
            self.skipTest("duckdb is not installed")
        self.rc = _load_runner()

    def _run(self):
        from excel_mcp.config import ExcelMcpConfig
        from excel_mcp.tools import ExcelMcpTools
        import tempfile

        checks = self.rc.load_jsonl(SUITE / "checks.jsonl")
        with tempfile.TemporaryDirectory() as tmp:
            tools = ExcelMcpTools(ExcelMcpConfig(allowed_roots=[WORKBOOK.parent], cache_dir=Path(tmp) / ".cache"))
            session = tools.spreadsheet_open({"path": str(WORKBOOK)})["session_id"]
            out = []
            for spec in checks:
                answer = self.rc.extract(tools, session, spec["extract"])
                ok, _ = self.rc.check(answer, spec["expect"])
                out.append((spec["id"], ok, answer))
        return out

    def test_all_checks_pass(self) -> None:
        results = self._run()
        failed = [rid for rid, ok, _ in results if not ok]
        self.assertEqual(failed, [], f"failing checks: {failed}")
        self.assertEqual(len(results), 20)

    def test_runs_are_identical(self) -> None:
        a = [(rid, ans) for rid, _, ans in self._run()]
        b = [(rid, ans) for rid, _, ans in self._run()]
        self.assertEqual(a, b)  # deterministic: same extraction twice -> same structured answers


if __name__ == "__main__":
    unittest.main()
