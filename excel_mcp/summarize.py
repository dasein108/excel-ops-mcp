from __future__ import annotations

from numbers import Number

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.range_read import read_range
from excel_mcp.schemas import (
    SpreadsheetReadRangeRequest,
    SpreadsheetSummaryResponse,
)
from excel_mcp.session import WorkbookSession


def _numeric(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Number):
        return float(value)
    return None


def summarize_range(
    session: WorkbookSession,
    sheet: str,
    cell_range: str,
    config: ExcelMcpConfig,
    *,
    growth: bool = False,
) -> SpreadsheetSummaryResponse:
    read = read_range(
        session,
        SpreadsheetReadRangeRequest(session_id=session.session_id, sheet=sheet, range=cell_range, include=["values"]),
        config,
    )
    values: list[float] = []
    skipped = 0
    for row in read.cells:
        for cell in row:
            num = _numeric(cell.get("value"))
            if num is None:
                if cell.get("value") not in (None, ""):
                    skipped += 1
                continue
            values.append(num)
    if not values:
        return SpreadsheetSummaryResponse(ok=True, session_id=session.session_id, sheet=sheet, range=cell_range, skipped=skipped)
    yoy: list[float] = []
    if growth:
        for prev, cur in zip(values, values[1:]):
            yoy.append(round((cur - prev) / prev * 100, 1) if prev else 0.0)
    return SpreadsheetSummaryResponse(
        ok=True,
        session_id=session.session_id,
        sheet=sheet,
        range=cell_range,
        count=len(values),
        skipped=skipped,
        total=sum(values),
        mean=sum(values) / len(values),
        min=min(values),
        max=max(values),
        yoy_growth_pct=yoy,
    )
