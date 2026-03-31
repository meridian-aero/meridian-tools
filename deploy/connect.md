# Connecting to Hangar MCP Servers

## Available servers

| Tool | Description | URL |
|------|-------------|-----|
| OAS (OpenAeroStruct) | Aerostructural analysis and optimization | `https://mcp.lakesideai.dev/oas/mcp` |
| OCP (OpenConcept) | Aircraft conceptual design and mission analysis | `https://mcp.lakesideai.dev/ocp/mcp` |
| PYC (pyCycle) | Gas turbine engine cycle analysis | `https://mcp.lakesideai.dev/pyc/mcp` |

## Authentication

All servers use Keycloak OIDC. The first time you connect, your browser
will open for login. You can sign in with Google or a username/password
provided by an admin.

## Claude Code (CLI)

```bash
claude mcp add --transport http oas https://mcp.lakesideai.dev/oas/mcp
claude mcp add --transport http ocp https://mcp.lakesideai.dev/ocp/mcp
claude mcp add --transport http pyc https://mcp.lakesideai.dev/pyc/mcp
```

Start a Claude Code session — the tools are available immediately.
On first use, your browser opens for Keycloak login.

### Managing servers

```bash
claude mcp list              # show configured servers
claude mcp remove oas        # remove a server
```

## claude.ai (web)

1. Go to [claude.ai](https://claude.ai)
2. **Settings** -> **Integrations** -> **Add MCP Server**
3. Enter the URL for the tool you want (e.g. `https://mcp.lakesideai.dev/oas/mcp`)
4. Sign in when redirected to Keycloak

Repeat for each tool. You can add all three.

## OpenAI Codex (CLI)

```bash
codex mcp add oas --url https://mcp.lakesideai.dev/oas/mcp
codex mcp add ocp --url https://mcp.lakesideai.dev/ocp/mcp
codex mcp add pyc --url https://mcp.lakesideai.dev/pyc/mcp
```

Then authenticate:

```bash
codex mcp login oas --scopes mcp:tools
codex mcp login ocp --scopes mcp:tools
codex mcp login pyc --scopes mcp:tools
```
