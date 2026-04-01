# Example: Visualization & Output Modes

## The `visualize` tool output modes

| Mode | Behaviour | Best for |
|------|-----------|----------|
| `inline` | Returns `[metadata, ImageContent]` -- base64 PNG in JSON | claude.ai |
| `file` | Saves PNG to disk, returns `[metadata]` with `file_path` | CLI / scripts |
| `url` | Returns `[metadata]` with `dashboard_url` and `plot_url` | Remote / VPS |

**Important**: `visualize` returns a **list**, not a dict. The first element is
always a metadata dict. The second element (if present) is the image content.

```python
result = call("visualize", run_id="latest", plot_type="station_properties", output="file")
# result is a list: [{"plot_type": "...", "file_path": "/path/to/plot.png", ...}]
file_path = result[0]["file_path"]
```

## Set a session default

Avoid passing `--output` every time:

```bash
pyc-cli configure-session --visualization-output file
```

## The `plot` convenience command

Shorthand for `visualize` with `output="file"`:

```bash
pyc-cli plot latest station_properties          # auto-named file
pyc-cli plot latest ts_diagram -o ts.png        # custom output path
pyc-cli plot latest performance_summary
pyc-cli plot latest component_bars
```

For off-design runs, also:

```bash
pyc-cli plot <run_id> design_vs_offdesign
```

## Available plot types

| Plot type | Description | Applicable to |
|-----------|-------------|---------------|
| `station_properties` | 2x2 grid: Pt, Tt, Mach, mass flow vs engine station | design, off-design |
| `ts_diagram` | T-s diagram of the Brayton cycle with process annotations | design, off-design |
| `performance_summary` | Styled table with all key engine metrics by section | design, off-design |
| `component_bars` | Horizontal bars: PR, efficiency, power per component | design, off-design |
| `design_vs_offdesign` | 2x2 paired bars with delta % annotations | off-design only |

## Generating all plots for a run

```bash
for PT in station_properties ts_diagram performance_summary component_bars; do
  pyc-cli plot latest "$PT"
done
```

## Viewer dashboard

The `pyc-cli viewer` command starts an HTTP viewer on localhost (default port
7654). Access it at:

- **Dashboard**: `http://localhost:7654/dashboard?run_id=<id>` -- results + plots
- **Provenance**: `http://localhost:7654/viewer?session_id=<id>` -- DAG viewer

The `visualize(..., output="url")` mode returns clickable links to these.

```bash
pyc-cli viewer                    # start on default port
pyc-cli viewer --port 8080        # custom port
```
