from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir

from pydantic import BaseModel, Field


class ExcelMcpConfig(BaseModel):
    allowed_roots: list[Path] = Field(default_factory=lambda: [Path.cwd()])
    cache_dir: Path = Field(default_factory=lambda: Path(gettempdir()) / "excel_mcp")
    max_open_workbooks: int = 8
    session_ttl_seconds: int = 60 * 60
    query_row_limit: int = 1000
    max_response_chars: int = 50_000
    max_read_range_cells: int = 10_000
    repeat_read_small_cells: int = 64
    repeat_read_warn_threshold: int = 3
    overwrite_by_default: bool = False

    def normalized_allowed_roots(self) -> list[Path]:
        return [root.expanduser().resolve() for root in self.allowed_roots]

