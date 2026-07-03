---
title: "Public Tool Contracts and JSON Schemas"
status: done
phase: P0
---

# Task 13 — Public Tool Contracts and JSON Schemas

Define the public MCP tool contracts before implementing the internals.

## Scope

- Stable JSON request/response schemas.
- Error envelope.
- Common source citation shape.
- Common telemetry shape.
- Common truncation shape.

## Tools

The initial tool surface is:

- `spreadsheet_open`
- `spreadsheet_describe`
- `spreadsheet_query`
- `spreadsheet_read_range`
- `spreadsheet_write`
- `spreadsheet_commit`
- `spreadsheet_diff`

## Common Response Fields

Every successful response should support:

```json
{
  "ok": true,
  "session_id": "ses_...",
  "source_refs": ["file.xlsx#Sheet1!A1:F20"],
  "warnings": [],
  "telemetry": {
    "cache": "hit",
    "elapsed_ms": 12
  }
}
```

Every failed response should use:

```json
{
  "ok": false,
  "error": {
    "code": "invalid_range",
    "message": "Range must be bounded",
    "details": {}
  }
}
```

## Request Sketches

`spreadsheet_open`:

```json
{
  "path": "/absolute/path/workbook.xlsx"
}
```

`spreadsheet_describe`:

```json
{
  "session_id": "ses_...",
  "detail": "compact"
}
```

`spreadsheet_query`:

```json
{
  "session_id": "ses_...",
  "sql": "select category, sum(amount) from Transactions group by 1",
  "limit": 1000
}
```

`spreadsheet_read_range`:

```json
{
  "session_id": "ses_...",
  "sheet": "Transactions",
  "range": "A1:F50",
  "include": ["values", "formulas"]
}
```

`spreadsheet_write`:

```json
{
  "session_id": "ses_...",
  "dry_run": true,
  "operations": []
}
```

`spreadsheet_commit`:

```json
{
  "session_id": "ses_...",
  "staged_id": "stg_...",
  "output_path": "/absolute/path/workbook.updated.xlsx",
  "overwrite": false
}
```

`spreadsheet_diff`:

```json
{
  "session_id": "ses_...",
  "staged_id": "stg_..."
}
```

## Acceptance Criteria

- Pydantic models exist for every request and response.
- JSON schema can be exported for each tool.
- Error codes are documented.
- The schemas are used by placeholder tools from Task 01.
- Tests validate example payloads.

## Notes

Locking schemas first prevents the implementation from leaking internal library details into the MCP interface.

