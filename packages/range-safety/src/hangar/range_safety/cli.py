"""Click CLI for hangar-range-safety."""

from __future__ import annotations

import click


@click.group()
def cli() -> None:
    """range-safety -- plan validation and post-run assertions."""


def main() -> None:
    """Entry point for range-safety CLI."""
    cli()
