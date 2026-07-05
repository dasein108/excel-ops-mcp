from __future__ import annotations

import difflib
import re
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig

# Bound the discovery scan so rglob over a large HOME never hangs the caller.
_MAX_SCAN_FILES = 5000
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache", "site-packages"}


class PolicyError(ValueError):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


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
            raise PolicyError(
                "path_not_allowed",
                "Path is outside configured allowed roots.",
                self._discovery_details(resolved),
            )
        if not resolved.exists():
            raise PolicyError(
                "file_not_found",
                f"No workbook at '{resolved}'.",
                self._discovery_details(resolved),
            )
        if not resolved.is_file():
            raise PolicyError("not_a_file", "Path is not a file.")
        if resolved.suffix.lower() != ".xlsx":
            raise PolicyError("unsupported_extension", "Only .xlsx files are supported in this phase.")
        return resolved

    def _discovery_details(self, attempted: Path) -> dict:
        """Teach the caller where paths resolve so one bad open fixes the next.

        Returns the allowed roots that were searched plus fuzzy basename
        matches (``did_you_mean``) so the caller can correct the path without a
        blind retry loop.
        """
        roots = self.config.normalized_allowed_roots()
        return {
            "attempted_path": str(attempted),
            "search_roots": [str(root) for root in roots],
            "did_you_mean": self._fuzzy_matches(attempted.name, roots),
            "note": "Paths resolve against the server host filesystem, relative to the search_roots above.",
        }

    def _fuzzy_matches(self, target_name: str, roots: list[Path], limit: int = 5) -> list[str]:
        target = target_name.lower()
        scanned = 0
        scored: list[tuple[float, str]] = []
        for root in roots:
            if not root.is_dir():
                continue
            for candidate in _iter_xlsx(root):
                scanned += 1
                if scanned > _MAX_SCAN_FILES:
                    break
                ratio = difflib.SequenceMatcher(None, target, candidate.name.lower()).ratio()
                if target in candidate.name.lower() or ratio >= 0.6:
                    scored.append((ratio, str(candidate)))
            if scanned > _MAX_SCAN_FILES:
                break
        scored.sort(key=lambda item: item[0], reverse=True)
        return [path for _, path in scored[:limit]]

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

    def list_workbooks(self, glob: str | None = None, limit: int = 200) -> list[dict]:
        """List .xlsx workbooks under the allowed roots for orientation.

        ``glob`` (optional) filters on the fnmatch pattern against each file's
        path relative to its root; without it every workbook is returned.
        """
        import fnmatch

        results: dict[str, dict] = {}
        scanned = 0
        for root in self.config.normalized_allowed_roots():
            if not root.is_dir():
                continue
            for candidate in _iter_xlsx(root):
                scanned += 1
                if scanned > _MAX_SCAN_FILES:
                    break
                if glob:
                    rel = candidate.relative_to(root).as_posix()
                    if not (fnmatch.fnmatch(rel, glob) or fnmatch.fnmatch(candidate.name, glob)):
                        continue
                key = str(candidate)
                if key in results:
                    continue
                try:
                    stat = candidate.stat()
                except OSError:
                    continue
                results[key] = {"path": key, "size": stat.st_size, "modified": stat.st_mtime}
                if len(results) >= limit:
                    break
            if len(results) >= limit or scanned > _MAX_SCAN_FILES:
                break
        return sorted(results.values(), key=lambda item: item["modified"], reverse=True)


def _iter_xlsx(root: Path):
    """Yield .xlsx files under ``root``, pruning noisy/hidden directories."""
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.lower().endswith(".xlsx") and not name.startswith("~$"):
                yield Path(dirpath) / name


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

