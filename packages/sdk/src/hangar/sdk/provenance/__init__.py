"""Provenance tracking for the hangar SDK.

Captures every tool call's inputs, outputs, timing, and status in a local
SQLite database, and provides a log_decision tool for recording reasoning.
"""

from hangar.sdk.provenance.flush import flush_session_graph

__all__ = ["flush_session_graph"]
