---
title: "CLI Parity Tests Against MCP Tool Layer"
status: done
phase: P1
---

# Task 18 — CLI Parity Tests Against MCP Tool Layer

Verify that the CLI returns behaviorally equivalent results to the direct `ExcelMcpTools` API.

## Scope

- Test the CLI as a subprocess.
- Compare representative output to direct tool-layer calls.
- Cover examples and generated fixtures.

## Test Cases

Use generated fixtures and real examples:

- `examples/MEXC.xlsx`
- `examples/VlaDeFi Stable _ Free.xlsx`
- generated write fixture from `tests/test_writes.py`

Required parity tests:

- `excel-ops describe PATH` matches direct `spreadsheet_describe` essentials.
- `excel-ops query PATH --sql ...` returns same rows as direct `spreadsheet_query`.
- `excel-ops read-range PATH ...` returns same cells as direct `spreadsheet_read_range`.
- `excel-ops write PATH --ops ops.json` does not mutate source.
- `excel-ops commit ... --output out.xlsx` creates the same workbook changes as direct commit.

## Acceptance Criteria

- CLI subprocess tests pass in `.venv`.
- Invalid SQL returns exit code `1` and JSON error.
- Invalid CLI args return exit code `2`.
- Tests do not depend on a long-running MCP server.
- Tests do not write outside temporary directories except reading `examples/`.

## Notes

These tests protect the core design: MCP and CLI are adapters over the same deterministic Excel engine.

