from __future__ import annotations

import json
import shutil
from pathlib import Path

import tomlkit
from tomlkit.exceptions import ParseError as TomlParseError

from .errors import MalformedConfig


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_name(path.name + ".bak")
    shutil.copy2(path, backup)
    return backup


def json_upsert_server(path: Path, root_key: str, name: str, entry: dict) -> str:
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if text.strip():
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise MalformedConfig(f"{path}: {exc}") from exc
        else:
            data = {}
        if not isinstance(data, dict):
            raise MalformedConfig(f"{path}: top-level JSON is not an object")
    else:
        data = {}

    servers = data.setdefault(root_key, {})
    if not isinstance(servers, dict):
        raise MalformedConfig(f"{path}: '{root_key}' is not an object")

    existed = name in servers
    servers[name] = entry

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return "updated" if existed else "added"


def json_has_server(path: Path, root_key: str, name: str) -> bool:
    """Whether ``name`` is present. Unreadable/malformed config counts as absent."""
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return False
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    servers = data.get(root_key)
    return isinstance(servers, dict) and name in servers


def json_remove_server(path: Path, root_key: str, name: str) -> str:
    """Return ``"removed"`` if the entry existed and was deleted, else ``"absent"``."""
    if not path.exists():
        return "absent"
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return "absent"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MalformedConfig(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise MalformedConfig(f"{path}: top-level JSON is not an object")
    servers = data.get(root_key)
    if not isinstance(servers, dict) or name not in servers:
        return "absent"
    del servers[name]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return "removed"


def toml_upsert_server(path: Path, name: str, command: str, args: list[str]) -> str:
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if text.strip():
            try:
                doc = tomlkit.parse(text)
            except TomlParseError as exc:
                raise MalformedConfig(f"{path}: {exc}") from exc
        else:
            doc = tomlkit.document()
    else:
        doc = tomlkit.document()

    servers = doc.get("mcp_servers")
    if servers is None:
        servers = tomlkit.table()
        doc["mcp_servers"] = servers

    existed = name in servers
    table = tomlkit.table()
    table["command"] = command
    table["args"] = args
    servers[name] = table

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return "updated" if existed else "added"


def toml_has_server(path: Path, name: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return False
    try:
        doc = tomlkit.parse(text)
    except TomlParseError:
        return False
    servers = doc.get("mcp_servers")
    return servers is not None and name in servers


def toml_remove_server(path: Path, name: str) -> str:
    if not path.exists():
        return "absent"
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return "absent"
    try:
        doc = tomlkit.parse(text)
    except TomlParseError as exc:
        raise MalformedConfig(f"{path}: {exc}") from exc
    servers = doc.get("mcp_servers")
    if servers is None or name not in servers:
        return "absent"
    del servers[name]
    path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return "removed"
