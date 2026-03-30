Scaffold a new MCP tool definition in the appropriate package.

## Arguments

$ARGUMENTS should be the tool package name (e.g. `propulsion`, `thermal`).

## Steps

1. **Create the package directory structure:**

```
packages/<toolname>/
  pyproject.toml
  Dockerfile
  CLAUDE.md
  skills/
  tests/
  src/
    hangar/
      <toolname>/
        __init__.py
        server.py
        tools/
          __init__.py
```

CRITICAL: Do NOT create `__init__.py` in `src/hangar/` -- only at the leaf
level (e.g. `src/hangar/<toolname>/__init__.py`). This is required for PEP 420
implicit namespace packages to work.

2. **Create `pyproject.toml`** following the `hangar-oas` pattern:

```toml
[project]
name = "hangar-<toolname>"
version = "0.1.0"
description = "<Tool description> MCP server for agentic analysis"
requires-python = ">=3.11"
dependencies = [
    "hangar-sdk",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/hangar"]

[tool.uv.sources]
hangar-sdk = { workspace = true }
```

3. **Create `server.py`** with a minimal FastMCP server:

```python
"""<Toolname> MCP server."""
from hangar.sdk.server import create_server

mcp = create_server("hangar-<toolname>", "<Description>")

# Import tool modules here
# from hangar.<toolname>.tools import ...

if __name__ == "__main__":
    mcp.run()
```

4. **Create `CLAUDE.md`** with tool-specific constraints and guidelines.

5. **Create a Dockerfile** following the OAS pattern:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .

RUN useradd -r -m -s /usr/sbin/nologin app && \
    mkdir -p /data && chown app:app /data

ENV MPLCONFIGDIR=/tmp/matplotlib
VOLUME /data
EXPOSE 8000
USER app

CMD ["python", "-m", "hangar.<toolname>.server"]
```

6. **Add to workspace** -- update the root `pyproject.toml` to include the new
   package as a workspace member.

7. **Add to docker-compose** -- add a service entry in `docker/docker-compose.yml`:

```yaml
  <toolname>:
    build:
      context: ../packages/<toolname>
      dockerfile: Dockerfile
    ports:
      - "<port>:8000"
    volumes:
      - ./<toolname>_data:/data
    environment:
      OAS_TRANSPORT: http
      OAS_HOST: 0.0.0.0
```

8. **Add upstream setup** -- if wrapping an external tool, add a clone step to
   `scripts/setup-upstream.sh`.

9. **Create initial skills** in `packages/<toolname>/skills/` -- at minimum:
   - A primary analysis workflow skill
   - A known-squawks skill for failure modes

10. **Create initial tests** in `packages/<toolname>/tests/`.

## Namespace checklist

- [ ] `src/hangar/` has NO `__init__.py`
- [ ] `src/hangar/<toolname>/__init__.py` exists
- [ ] PyPI name uses hyphens: `hangar-<toolname>`
- [ ] Python import uses dots: `hangar.<toolname>`
- [ ] Package is listed in workspace members
