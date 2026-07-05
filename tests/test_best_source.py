from pathlib import Path

from excel_mcp.best_source import rank_sources
from excel_mcp.config import ExcelMcpConfig
from excel_mcp.describe import describe_workbook
from excel_mcp.schemas import RegionInfo, SheetInfo
from excel_mcp.session import SessionRegistry

EXAMPLE = Path("examples/saas.xlsx").resolve()


def _region(kind, conf):
    return RegionInfo(region_id="r", table_name="t", sheet="s", bounds="A1:F5",
                      row_count=5, column_count=6, region_kind=kind, confidence=conf, source_ref="s!A1")


def test_summary_region_ranks_above_raw_table():
    sheets = [
        SheetInfo(name="Revenue Model", bounds="A1:Q40", source_ref="Revenue Model!A1",
                  regions=[_region("table", 0.6), _region("unknown", 0.3)]),
        SheetInfo(name="Dashboard", bounds="A1:F13", source_ref="Dashboard!A1",
                  regions=[_region("summary", 0.9)]),
    ]
    ranked = rank_sources(sheets)
    assert ranked[0]["sheet"] == "Dashboard"
    assert ranked[0]["score"] > ranked[1]["score"]


def test_describe_populates_best_source(tmp_path):
    reg = SessionRegistry(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))
    session, _ = reg.open(EXAMPLE)
    resp = describe_workbook(session, detail="compact")
    assert resp.best_source
    assert "sheet" in resp.best_source[0]
