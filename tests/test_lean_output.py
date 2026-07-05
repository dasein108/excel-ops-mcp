from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.schemas import SpreadsheetReadRangeRequest
from excel_mcp.range_read import read_range
from excel_mcp.session import SessionRegistry

EXAMPLE = Path("examples/saas.xlsx").resolve()


def _session(tmp_path):
    reg = SessionRegistry(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))
    return reg.open(EXAMPLE)[0]


def test_read_range_truncates_large_range(tmp_path):
    cfg = ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path, read_row_limit=3)
    session = _session(tmp_path)
    resp = read_range(session, SpreadsheetReadRangeRequest(session_id=session.session_id, sheet="Revenue Model", range="A1:A50"), cfg)
    assert len(resp.cells) == 3
    assert resp.telemetry.truncated is True


def test_read_range_full_bypasses_cap(tmp_path):
    cfg = ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path, read_row_limit=3)
    session = _session(tmp_path)
    resp = read_range(session, SpreadsheetReadRangeRequest(session_id=session.session_id, sheet="Revenue Model", range="A1:A50"), cfg, full=True)
    assert len(resp.cells) > 3
