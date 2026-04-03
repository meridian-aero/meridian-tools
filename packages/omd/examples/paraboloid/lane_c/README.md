# Lane C: Agent Prompts

These markdown files contain natural-language prompts for an AI agent
(Claude Code) to run the paraboloid examples via `omd-cli`.

## Usage

```bash
# Start Claude Code from the workspace root
claude

# Then paste the contents of any prompt file:
# - analysis.prompt.md     (single analysis)
# - optimization.prompt.md (optimization)
# - all.prompt.md          (both in sequence)
```

The agent calls `omd-cli` commands and reports results. Results should
match Lane A and Lane B within machine precision.
