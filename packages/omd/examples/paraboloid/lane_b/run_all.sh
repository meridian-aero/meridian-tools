#!/bin/bash
# Run all paraboloid examples via omd-cli
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Paraboloid Analysis ==="
uv run omd-cli assemble "$DIR/analysis/"
uv run omd-cli run "$DIR/analysis/plan.yaml" --mode analysis
echo ""

echo "=== Paraboloid Optimization ==="
uv run omd-cli assemble "$DIR/optimization/"
uv run omd-cli run "$DIR/optimization/plan.yaml" --mode optimize
echo ""

echo "Done. Check hangar_data/omd/ for artifacts."
