from __future__ import annotations

import re
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig


class PolicyError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class PathPolicy:
    def __init__(self, config: ExcelMcpConfig):
        self.config = config

    def validate_input_file(self, path_text: str) -> Path:
        if "://" in path_text:
            raise PolicyError("unsupported_source", "Only local Excel file paths are supported.")

        path = Path(path_text).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        resolved = path.resolve()

        if not self._inside_allowed_root(resolved):
            raise PolicyError("path_not_allowed", "Path is outside configured allowed roots.")
        if not resolved.exists():
            raise PolicyError("file_not_found", "Workbook does not exist.")
        if not resolved.is_file():
            raise PolicyError("not_a_file", "Path is not a file.")
        if resolved.suffix.lower() != ".xlsx":
            raise PolicyError("unsupported_extension", "Only .xlsx files are supported in this phase.")
        return resolved

    def validate_output_file(self, path_text: str, overwrite: bool = False) -> Path:
        path = Path(path_text).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        resolved = path.resolve()
        if not self._inside_allowed_root(resolved):
            raise PolicyError("path_not_allowed", "Output path is outside configured allowed roots.")
        if resolved.exists() and not overwrite:
            raise PolicyError("output_exists", "Output path exists and overwrite=false.")
        if resolved.suffix.lower() != ".xlsx":
            raise PolicyError("unsupported_extension", "Output path must end in .xlsx.")
        return resolved

    def _inside_allowed_root(self, path: Path) -> bool:
        for root in self.config.normalized_allowed_roots():
            try:
                path.relative_to(root)
                return True
            except ValueError:
                continue
        return False


class SqlPolicy:
    _blocked = re.compile(
        r"\b(insert|update|delete|create|drop|alter|copy|attach|detach|install|load|call|pragma)\b",
        re.IGNORECASE,
    )

    def validate_readonly(self, sql: str) -> None:
        stripped = sql.strip().rstrip(";")
        if not stripped:
            raise PolicyError("empty_sql", "SQL query cannot be empty.")
        if self._blocked.search(stripped):
            raise PolicyError("mutating_sql_rejected", "Only read-only SELECT queries are allowed.")
        first = stripped.split(None, 1)[0].lower()
        if first not in {"select", "with"}:
            raise PolicyError("unsupported_sql", "SQL must start with SELECT or WITH.")

