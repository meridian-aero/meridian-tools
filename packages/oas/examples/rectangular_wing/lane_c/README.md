# Lane C: Agent Prompts

These prompts are designed to be copied into Claude Code (CLI or IDE) or
claude.ai with the OAS MCP server connected.

## Setup

### Claude Code (CLI)

The MCP server is already configured if you have `hangar-oas` installed. Just
start Claude Code from the workspace root:

```bash
cd /path/to/the-hangar
claude
```

Then paste the contents of any `.prompt.md` file as your message.

### claude.ai

1. Go to claude.ai/code or claude.ai with MCP support
2. Connect the OpenAeroStruct MCP server
3. Paste the prompt contents

## Prompt Files

| File | Description |
|------|-------------|
| `aero_analysis.prompt.md` | Single-point aero analysis at alpha=5 deg |
| `drag_polar.prompt.md` | Drag polar sweep (-10 to 10 deg) |
| `opt_twist.prompt.md` | Twist optimisation (min CD, CL=0.5) |
| `opt_chord.prompt.md` | Chord optimisation (min CD, CL=0.5, S_ref=10) |
| `all_analyses.prompt.md` | All four analyses in sequence |

## Verification

Compare the agent's reported CL/CD values with the Lane A and Lane B outputs.
The values should match within a few percent (the agent uses the same MCP
tools as Lane B, so results should be identical to Lane B).
