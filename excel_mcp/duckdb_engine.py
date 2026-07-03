from __future__ import annotations

import time
from typing import Any

from openpyxl.utils.cell import range_boundaries

from excel_mcp.normalizers import is_percent_like_column, parse_percent_value
from excel_mcp.policy import PolicyError, SqlPolicy
from excel_mcp.schemas import SpreadsheetQueryResponse, Telemetry
from excel_mcp.session import WorkbookSession
from excel_mcp.utils import cell_value_for_json
from excel_mcp.values import get_value_resolver


class DuckDbUnavailable(RuntimeError):
    pass


class DuckDbEngine:
    def __init__(self) -> None:
        try:
            import duckdb  # type: ignore
        except Exception as exc:
            raise DuckDbUnavailable("duckdb is not installed") from exc
        self.duckdb = duckdb
        self.sql_policy = SqlPolicy()

    def ensure_materialized(self, session: WorkbookSession) -> None:
        if session.duckdb_connection is not None:
            return
        conn = self.duckdb.connect(database=":memory:")
        session.duckdb_connection = conn
        if not session.regions:
            from excel_mcp.describe import describe_workbook

            describe_workbook(session, detail="standard")
        for region in session.regions:
            rows = _region_rows(session, region)
            rows, derived_columns = _add_derived_columns(rows, [column.name for column in region.columns])
            # Matrix (transposed) regions get a first-class Year-1 total so agents
            # don't have to sum the twelve month columns by hand — the mistake that
            # makes them grab a later annual column (Year 2) instead.
            if getattr(region, "orientation", "tabular") == "matrix":
                rows, year1 = _add_year1_total(rows, [column.name for column in region.columns])
                derived_columns = derived_columns + year1
            columns = [column.name for column in region.columns] + derived_columns
            # Infer types from the materialized (computed) values so formula columns
            # that resolve to numbers get a numeric type instead of the static text
            # type inferred from their formula strings during region detection.
            column_types = {
                column.name: _duckdb_type_from_values(
                    [row.get(column.name) for row in rows], _duckdb_type(column.type)
                )
                for column in region.columns
            }
            for derived in derived_columns:
                column_types[derived] = "double" if not derived.endswith("__kind") else "varchar"
            col_defs = ", ".join(f'"{col}" {column_types[col]}' for col in columns)
            if not col_defs:
                col_defs = '"empty" varchar'
            conn.execute(f'create table "{region.table_name}" ({col_defs})')
            if rows and columns:
                placeholders = ", ".join("?" for _ in columns)
                quoted_columns = ", ".join(f'"{column}"' for column in columns)
                values = [tuple(row.get(column) for column in columns) for row in rows]
                conn.executemany(f'insert into "{region.table_name}" ({quoted_columns}) values ({placeholders})', values)

    def query(self, session: WorkbookSession, sql: str, limit: int) -> SpreadsheetQueryResponse:
        started = time.perf_counter()
        self.sql_policy.validate_readonly(sql)
        self.ensure_materialized(session)
        conn = session.duckdb_connection
        wrapped_sql = f"select * from ({sql.rstrip().rstrip(';')}) as q limit {limit + 1}"
        result = conn.execute(wrapped_sql)
        columns = [item[0] for item in result.description]
        raw_rows = result.fetchall()
        truncated = len(raw_rows) > limit
        raw_rows = raw_rows[:limit]
        rows = [dict(zip(columns, [cell_value_for_json(value) for value in row], strict=False)) for row in raw_rows]
        elapsed = int((time.perf_counter() - started) * 1000)
        return SpreadsheetQueryResponse(
            ok=True,
            session_id=session.session_id,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            telemetry=Telemetry(elapsed_ms=elapsed, rows_returned=len(rows), truncated=truncated),
        )


def _region_rows(session: WorkbookSession, region: Any) -> list[dict[str, Any]]:
    ws = session.workbook[region.sheet]
    resolver = get_value_resolver(session)
    start = region.data_start_row or 1
    min_col, _, _, max_row = range_boundaries(region.bounds)
    rows: list[dict[str, Any]] = []
    for row_idx in range(start, max_row + 1):
        item: dict[str, Any] = {}
        for offset, column in enumerate(region.columns):
            cell = ws.cell(row_idx, min_col + offset)
            # Materialize the computed number so SQL can aggregate formula cells,
            # instead of storing the formula string as text.
            value = resolver.resolve(region.sheet, cell.coordinate, cell.value)
            item[column.name] = cell_value_for_json(value)
        if any(value is not None and str(value).strip() != "" for value in item.values()):
            rows.append(item)
    return rows


def _add_year1_total(rows: list[dict[str, Any]], columns: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    from excel_mcp.regions import matrix_month_columns

    month_cols = matrix_month_columns(columns)
    if len(month_cols) < 2:
        return rows, []
    for row in rows:
        nums = [row.get(m) for m in month_cols]
        nums = [n for n in nums if isinstance(n, (int, float)) and not isinstance(n, bool)]
        row["year_1_total"] = sum(nums) if nums else None
    return rows, ["year_1_total"]


def _add_derived_columns(rows: list[dict[str, Any]], columns: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    derived_columns: list[str] = []
    for column in columns:
        values = [row.get(column) for row in rows]
        if not is_percent_like_column(column, values):
            continue
        kind_col = f"{column}__kind"
        num_col = f"{column}__num"
        min_col = f"{column}__min"
        max_col = f"{column}__max"
        derived_columns.extend([kind_col, num_col, min_col, max_col])
        for row in rows:
            parsed = parse_percent_value(row.get(column))
            row[kind_col] = parsed.kind
            row[num_col] = parsed.num
            row[min_col] = parsed.min
            row[max_col] = parsed.max
    return rows, derived_columns


def _duckdb_type_from_values(values: list[Any], fallback: str) -> str:
    """Pick a duckdb column type from the actual materialized values.

    Numeric columns become ``double`` so aggregates work; otherwise keep the
    statically inferred type. Mixed/non-numeric data falls back to ``varchar``.
    """
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return fallback
    if all(isinstance(v, bool) for v in non_null):
        return "boolean"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_null):
        return "double"
    return "varchar"


def _duckdb_type(type_name: str) -> str:
    return {
        "boolean": "boolean",
        "integer": "bigint",
        "decimal": "double",
        "date": "varchar",
        "timestamp": "varchar",
        "text": "varchar",
    }.get(type_name, "varchar")


def query_or_error(session: WorkbookSession, sql: str, limit: int) -> SpreadsheetQueryResponse:
    try:
        return DuckDbEngine().query(session, sql, limit)
    except PolicyError:
        raise
