#!/usr/bin/env python3
"""CLI commands for Agent Data system management."""

import logging
import os
import sys
from pathlib import Path

import click

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Agent Data CLI - Knowledge management system commands."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
def serve(host, port):
    """Start the Agent Data server."""
    try:
        import uvicorn

        # Import app dynamically to avoid unused import error
        from agent_data.server import app

        click.echo(f"Starting Agent Data server on {host}:{port}")
        # Use app to avoid F401 warning
        uvicorn.run(app, host=host, port=port)
    except ImportError as e:
        click.echo(f"❌ Failed to start server: {e}")
        sys.exit(1)


@cli.command()
def check():
    """Check system dependencies and configuration."""
    click.echo("Checking Agent Data system dependencies...")

    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 11):
        click.echo(f"✅ Python {python_version.major}.{python_version.minor}")
    else:
        click.echo(
            f"❌ Python {python_version.major}.{python_version.minor} (requires 3.11+)"
        )
        sys.exit(1)

    # Check required environment variables
    required_vars = [
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
    ]

    missing_vars = []
    for var in required_vars:
        if os.getenv(var):
            click.echo(f"✅ {var} is set")
        else:
            missing_vars.append(var)
            click.echo(f"❌ {var} is not set")

    if missing_vars:
        click.echo(f"\nMissing environment variables: {', '.join(missing_vars)}")
        click.echo("Please set these variables before using Agent Data.")
        sys.exit(1)

    # Check project structure
    required_dirs = [
        "agent_data",
        "tests",
        "docs",
    ]

    for dir_name in required_dirs:
        if Path(dir_name).exists():
            click.echo(f"✅ {dir_name}/ directory exists")
        else:
            click.echo(f"❌ {dir_name}/ directory missing")

    # Test basic imports
    try:
        import importlib.util

        spec = importlib.util.find_spec("langroid")
        if spec is not None:
            click.echo("✅ Langroid import successful")
        else:
            click.echo("❌ Langroid not found")
    except ImportError:
        click.echo("❌ Failed to test Langroid import")

    try:
        spec = importlib.util.find_spec("openai")
        if spec is not None:
            click.echo("✅ OpenAI import successful")
        else:
            click.echo("❌ OpenAI not found")
    except ImportError:
        click.echo("❌ OpenAI import failed")

    click.echo("\n✅ System check complete!")


if __name__ == "__main__":
    cli()
