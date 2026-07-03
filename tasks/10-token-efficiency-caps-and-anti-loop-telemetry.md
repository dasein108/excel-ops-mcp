---
title: "Token Efficiency, Caps, and Anti-Loop Telemetry"
status: done
phase: P2
---

# Task 10 — Token Efficiency, Caps, and Anti-Loop Telemetry

Add safeguards that keep spreadsheet work compact and prevent repeated range-read loops.

## Scope

- Hard response caps.
- Compact output profile.
- Cache hit/miss telemetry.
- Repeated small-read detection.
- Token-saved estimates.

## Deliverables

- Server-level output profile:
  - `compact` default
  - `verbose` opt-in
- Default caps:
  - query rows: 1,000
  - response chars: 50,000
  - read range cells: configurable
- Telemetry fields:
  - cache hit/miss
  - rows scanned
  - rows returned
  - estimated raw cells avoided
  - estimated tokens avoided
  - execution time
- Anti-loop warning:
  - detects many small range reads from the same workbook
  - suggests `spreadsheet_describe` or `spreadsheet_query`

## Acceptance Criteria

- Large query results truncate cleanly with metadata.
- Repeated small range reads trigger a warning.
- Describe and query responses include token-efficiency telemetry.
- Tests cover truncation and anti-loop warnings.

## Notes

This is where the MCP becomes meaningfully better than generic Excel wrappers that dump raw cells.

