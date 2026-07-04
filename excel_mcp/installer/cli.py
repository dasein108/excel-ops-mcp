from __future__ import annotations

import argparse
import sys

from .adapters.base import ApplyResult
from .registry import adapter_by_key, build_registry
from .spec import default_spec


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="excel-ops-mcp-install",
                                description="Install excel-ops-mcp into your LLM agents.")
    p.add_argument("--version", action="store_true", help="print version and exit")
    p.add_argument("--list", action="store_true", help="list supported agents + detection, then exit")
    p.add_argument("--dry-run", action="store_true", help="show what would change; write nothing")
    p.add_argument("--yes", action="store_true", help="no prompt; apply to detected (or --agents) set")
    p.add_argument("--agents", help="comma-separated agent keys to target")
    return p.parse_args(argv)


def _select_keys(args, adapters, detected) -> list[str]:
    if args.agents:
        return [k.strip() for k in args.agents.split(",") if k.strip()]
    if args.yes or not sys.stdout.isatty():
        return sorted(detected)
    from .tui import select_agents

    return select_agents(adapters, detected)


def _print_summary(results: list[ApplyResult]) -> None:
    print("\nSummary:")
    for r in results:
        if r.action == "dry-run":
            line = f"  ~ {r.key}: would write {r.path or r.note}"
        elif r.ok:
            where = r.path or "(via CLI)"
            line = f"  ✓ {r.key}: {r.action} → {where}"
            if r.backup:
                line += f"  (backup {r.backup})"
        else:
            line = f"  ✗ {r.key}: {r.error}"
        print(line)
        if r.ok and r.note and r.action != "dry-run":
            print(f"      next: {r.note}")


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    if args.version:
        print("excel-ops-mcp-install (excel-ops-mcp installer)")
        return 0

    adapters = build_registry()
    detected = {a.key for a in adapters if a.detect()}

    if args.list:
        print("Supported agents:")
        for a in adapters:
            mark = "detected" if a.key in detected else "not found"
            print(f"  [{mark:>9}] {a.label:<16} {a.key}")
        return 0

    keys = _select_keys(args, adapters, detected)

    # Validate keys.
    valid = {a.key for a in adapters}
    unknown = [k for k in keys if k not in valid]
    if unknown:
        print(f"error: unknown agent(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"valid keys: {', '.join(sorted(valid))}", file=sys.stderr)
        return 2

    if not keys:
        print("No agents selected. Nothing to do.")
        return 0

    spec = default_spec()
    results: list[ApplyResult] = []
    for key in keys:
        adapter = adapter_by_key(key)
        assert adapter is not None  # validated above
        results.append(adapter.apply(spec, dry_run=args.dry_run))

    _print_summary(results)
    return 1 if any(not r.ok for r in results) else 0
