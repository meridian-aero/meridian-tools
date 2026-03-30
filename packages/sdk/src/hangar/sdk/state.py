"""Module-level singletons for session and artifact management.

Migrated from: OpenAeroStruct/oas_mcp/tools/_state.py
"""

from hangar.sdk.session.manager import SessionManager
from hangar.sdk.artifacts.store import ArtifactStore

sessions = SessionManager()
artifacts = ArtifactStore()
