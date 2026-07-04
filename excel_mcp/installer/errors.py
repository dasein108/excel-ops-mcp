from __future__ import annotations


class MalformedConfig(Exception):
    """Existing agent config could not be parsed; refuse to overwrite it."""
