---
title: "Audit Log and Source Citation Model"
status: done
phase: P1
---

# Task 09 — Audit Log and Source Citation Model

Add durable audit records and consistent source citations to support trustworthy spreadsheet work.

## Scope

- Per-session audit log.
- Source range references in every read/query/write response.
- Operation history for staged and committed writes.

## Deliverables

- Audit event schema:
  - event ID
  - session ID
  - source fingerprint
  - tool name
  - input summary
  - affected source ranges
  - timestamp
  - status
  - warnings
- Source URI format:
  - `file.xlsx#Sheet!A1:F20`
- Query result table references.
- Write and diff responses include affected source URIs.

## Acceptance Criteria

- Every read response has at least one source reference.
- Every write/diff response lists affected ranges.
- Audit log survives server restart when backed by SQLite.
- Tests cover audit events for open, describe, query, write dry-run, and commit.

## Product Notes

Auditability is a core differentiator for bookkeeping, accounting, and operations workflows. The user should always be able to answer, "Where did this answer come from?" and "What changed?"

