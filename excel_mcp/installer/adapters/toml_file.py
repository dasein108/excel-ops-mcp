from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..errors import MalformedConfig
from ..merge import backup_file, toml_has_server, toml_remove_server, toml_upsert_server
from ..spec import SERVER_NAME, ServerSpec
from .base import Adapter, ApplyResult


@dataclass
class TomlDescriptor:
    key: str
    label: str
    path_fn: Callable[[], Path | None]
    gui: bool = False
    detect_dirs: tuple[Path | None, ...] = ()
    cli_name: str | None = None
    restart_note: str | None = None


class TomlFileAdapter(Adapter):
    def __init__(self, desc: TomlDescriptor) -> None:
        self.desc = desc
        self.key = desc.key
        self.label = desc.label
        self.gui = desc.gui

    def detect(self) -> bool:
        path = self.desc.path_fn()
        if path is not None and path.exists():
            return True
        for d in self.desc.detect_dirs:
            if d is not None and d.exists():
                return True
        if self.desc.cli_name and shutil.which(self.desc.cli_name):
            return True
        return False

    def is_installed(self) -> bool:
        path = self.desc.path_fn()
        return path is not None and toml_has_server(path, SERVER_NAME)

    def target(self) -> str | None:
        path = self.desc.path_fn()
        return str(path) if path else None

    def remove(self, *, dry_run: bool) -> ApplyResult:
        path = self.desc.path_fn()
        if path is None:
            return ApplyResult(self.key, False, "skipped", None, None,
                               error="no config path on this platform")
        if dry_run:
            return ApplyResult(self.key, True, "dry-run", str(path), None,
                               note="would remove excel-ops-mcp")
        try:
            backup = backup_file(path)
            action = toml_remove_server(path, SERVER_NAME)
        except MalformedConfig as exc:
            return ApplyResult(self.key, False, "skipped", str(path), None, error=str(exc))
        return ApplyResult(self.key, True, action, str(path),
                           str(backup) if backup else None,
                           note=self.desc.restart_note if action == "removed" else None)

    def apply(self, spec: ServerSpec, *, dry_run: bool) -> ApplyResult:
        path = self.desc.path_fn()
        if path is None:
            return ApplyResult(self.key, False, "skipped", None, None,
                               error="no config path on this platform")
        if dry_run:
            return ApplyResult(self.key, True, "dry-run", str(path), None,
                               note=self.desc.restart_note)
        try:
            backup = backup_file(path)
            action = toml_upsert_server(path, spec.name, spec.command_for(self.gui), list(spec.args))
        except MalformedConfig as exc:
            return ApplyResult(self.key, False, "skipped", str(path), None, error=str(exc))
        return ApplyResult(self.key, True, action, str(path),
                           str(backup) if backup else None, note=self.desc.restart_note)
