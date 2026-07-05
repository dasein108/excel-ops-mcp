from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.session import SessionRegistry
from excel_mcp.summarize import summarize_range

EXAMPLE = Path("examples/saas.xlsx").resolve()


def _session(tmp_path):
    reg = SessionRegistry(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))
    session, _ = reg.open(EXAMPLE)
    return session


def test_summary_matches_known_dashboard_totals(tmp_path):
    session = _session(tmp_path)
    resp = summarize_range(session, "Dashboard", "B5:F5",
                           ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path),
                           growth=True)
    assert resp.ok
    assert resp.count == 5
    assert round(resp.total) == 12784732
    assert round(resp.max) == 3127445
    assert round(resp.mean) == 2556946
    assert [round(g, 1) for g in resp.yoy_growth_pct] == [68.8, 12.0, 8.0, 5.0]


def test_summary_skips_non_numeric(tmp_path):
    session = _session(tmp_path)
    resp = summarize_range(session, "Dashboard", "A5:F5",
                           ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))
    assert resp.count == 5
    assert resp.skipped >= 1
