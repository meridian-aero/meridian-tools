"""CLI framework for hangar tool servers.

Provides a generic CLI with three modes:

- **interactive** -- JSON-lines protocol over stdin/stdout
- **one-shot** -- subcommand per tool with argparse-derived flags
- **script** -- batch execution from a JSON workflow file

Migrated from: OpenAeroStruct/oas_mcp/cli.py, cli_state.py, cli_runner.py
"""

from hangar.sdk.cli.main import main, interactive_mode, oneshot_mode, run_script_mode
from hangar.sdk.cli.runner import (
    json_dumps,
    run_tool,
    run_tool_sync,
    interpolate_args,
    list_tools,
    get_registry,
    set_registry_builder,
)
from hangar.sdk.cli.state import load_surfaces, save_surfaces, clear_state

__all__ = [
    "main",
    "interactive_mode",
    "oneshot_mode",
    "run_script_mode",
    "json_dumps",
    "run_tool",
    "run_tool_sync",
    "interpolate_args",
    "list_tools",
    "get_registry",
    "set_registry_builder",
    "load_surfaces",
    "save_surfaces",
    "clear_state",
]
