from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..spec import ServerSpec


@dataclass
class ApplyResult:
    key: str
    ok: bool
    action: str  # "added" | "updated" | "skipped" | "dry-run"
    path: str | None
    backup: str | None
    note: str | None = None
    error: str | None = None


class Adapter(ABC):
    key: str
    label: str
    gui: bool

    @abstractmethod
    def detect(self) -> bool: ...

    @abstractmethod
    def is_installed(self) -> bool: ...

    @abstractmethod
    def target(self) -> str | None: ...

    @abstractmethod
    def apply(self, spec: ServerSpec, *, dry_run: bool) -> ApplyResult: ...

    @abstractmethod
    def remove(self, *, dry_run: bool) -> ApplyResult: ...
