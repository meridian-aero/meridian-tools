#!/bin/bash
# Clone upstream engineering tool repos for local reference
# These are .gitignore'd — not part of the hangar repo

set -e
UPSTREAM_DIR="$(dirname "$0")/../upstream"
mkdir -p "$UPSTREAM_DIR"

echo "Cloning OpenAeroStruct..."
if [ ! -d "$UPSTREAM_DIR/OpenAeroStruct" ]; then
    # git clone -b <branch-name> https://github.com/acb-code/OpenAeroStruct "$UPSTREAM_DIR/OpenAeroStruct"
    # git clone https://github.com/mdolab/OpenAeroStruct "$UPSTREAM_DIR/OpenAeroStruct"
    git clone https://github.com/acb-code/OpenAeroStruct "$UPSTREAM_DIR/OpenAeroStruct"
else
    # git -C "$UPSTREAM_DIR/OpenAeroStruct" pull origin <branch-name>
    echo "  Already exists, pulling latest..."
    git -C "$UPSTREAM_DIR/OpenAeroStruct" pull
fi

echo "Cloning OpenConcept..."
if [ ! -d "$UPSTREAM_DIR/openconcept" ]; then
    git clone https://github.com/mdolab/openconcept "$UPSTREAM_DIR/openconcept"
else
    echo "  Already exists, pulling latest..."
    git -C "$UPSTREAM_DIR/openconcept" pull
fi

echo "Cloning pyCycle..."
if [ ! -d "$UPSTREAM_DIR/pyCycle" ]; then
    git clone https://github.com/OpenMDAO/pyCycle "$UPSTREAM_DIR/pyCycle"
else
    echo "  Already exists, pulling latest..."
    git -C "$UPSTREAM_DIR/pyCycle" pull
fi

echo "Cloning AeroSandbox..."
if [ ! -d "$UPSTREAM_DIR/AeroSandbox" ]; then
    git clone https://github.com/peterdsharpe/AeroSandbox "$UPSTREAM_DIR/AeroSandbox"
else
    echo "  Already exists, pulling latest..."
    git -C "$UPSTREAM_DIR/AeroSandbox" pull
fi

echo "Done. Upstream repos are in upstream/ (git-ignored)."
echo "To use editable installs, uncomment the [tool.uv.sources] line in packages/oas/pyproject.toml"
