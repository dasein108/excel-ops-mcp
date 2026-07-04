# Development Guide

This guide covers local development, testing, packaging, and PyPI publishing for `excel-ops-mcp`.

## Local Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Run tests:

```bash
pytest -v
```

Run the CLI:

```bash
excel-ops sheets examples/saas.xlsx --pretty
```

Run the MCP server:

```bash
excel-ops-mcp
```

## Project Surfaces

When changing Excel behavior, keep these surfaces aligned:

- MCP tools in `excel_mcp/tools.py`
- CLI adapter in `excel_mcp/cli.py`
- Core modules under `excel_mcp/`
- Direct tests under `tests/`
- CLI subprocess tests under `tests/test_cli.py`
- Skill guidance under `.codex/skills/excel-ops/`
- Repository instructions in `AGENTS.md`

## Build Package Locally

Install build tooling:

```bash
pip install build twine
```

Build:

```bash
python -m build
```

If build isolation cannot download the build backend in a restricted environment, install `hatchling` into the active venv and run:

```bash
pip install hatchling
python -m build --no-isolation
```

Validate distributions:

```bash
twine check dist/*
```

Smoke-test a wheel in a clean environment:

```bash
python -m venv /tmp/excel-mcp-wheel-test
/tmp/excel-mcp-wheel-test/bin/pip install dist/*.whl
/tmp/excel-mcp-wheel-test/bin/excel-ops --help
```

## PyPI Publishing Model

Preferred publishing uses PyPI Trusted Publishing from GitHub Actions.

Do not store PyPI API tokens in GitHub secrets unless trusted publishing is unavailable.

## Configure PyPI Trusted Publishing

On PyPI:

1. Create the `excel-ops-mcp` project, or publish the first release manually if required by PyPI policy.
2. Go to the project publishing settings.
3. Add a trusted publisher:
   - Owner: GitHub repository owner.
   - Repository name: GitHub repository name.
   - Workflow filename: `publish-pypi.yml`.
   - Environment name: leave empty unless the workflow later adds one.

The GitHub workflow uses `id-token: write` and `pypa/gh-action-pypi-publish`.

## Release Process

1. Replace placeholder `project.urls` in `pyproject.toml` with the real GitHub repository URLs.
2. Update version in `pyproject.toml`.
3. Update docs if tool behavior changed.
4. Run:

```bash
pytest -v
python -m build
twine check dist/*
```

5. Commit the release changes.
6. Push to GitHub.
7. Create a GitHub release.
8. The `Publish to PyPI` workflow runs on `release: published`.
9. Verify:

```bash
uvx excel-ops-mcp --help
uvx --from excel-ops-mcp excel-ops --help
```

## Manual PyPI Fallback

Use only if trusted publishing is not available:

```bash
python -m build
twine check dist/*
twine upload dist/*
```

This requires a PyPI API token and should be avoided for normal releases.
