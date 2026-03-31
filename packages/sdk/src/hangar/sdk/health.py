"""Lightweight health-check endpoint for Hangar MCP servers.

Provides a ``/healthz`` route that returns minimal JSON without
authentication.  Intended to be composed into the ASGI app *before*
the MCP handler so it is never gated by OIDC.

Usage in a server's ``main()``::

    from hangar.sdk.health import add_healthz

    mcp_asgi = mcp.streamable_http_app()
    app = add_healthz(mcp_asgi, server_name="oas")
"""

from __future__ import annotations

import json
import time
from importlib.metadata import PackageNotFoundError, version


def _get_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "dev"


def add_healthz(app, *, server_name: str, package: str | None = None):
    """Wrap *app* with a ``/healthz`` dispatcher.

    Parameters
    ----------
    app
        The downstream ASGI application (typically the MCP app or a
        viewer+MCP composition).
    server_name
        Short identifier (``"oas"``, ``"ocp"``, ``"pyc"``).
    package
        Python package name for version lookup.  Defaults to
        ``hangar-{server_name}``.

    Returns
    -------
    An ASGI callable that intercepts ``GET /healthz`` and forwards
    everything else to *app*.
    """
    pkg = package or f"hangar-{server_name}"
    ver = _get_version(pkg)
    body = json.dumps(
        {"status": "ok", "server": server_name, "version": ver}
    ).encode()

    async def healthz_dispatcher(scope, receive, send):
        if (
            scope["type"] == "http"
            and scope.get("path") == "/healthz"
            and scope.get("method", "GET") == "GET"
        ):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"cache-control", b"no-cache"],
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await app(scope, receive, send)

    return healthz_dispatcher
