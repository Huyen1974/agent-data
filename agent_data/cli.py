#!/usr/bin/env python3
"""
Agent Data Langroid CLI - Command Line Interface for agent data operations
"""

import click
from typing import Optional


@click.group()
@click.version_option()
def main():
    """Agent Data Langroid - Multi-agent knowledge management system."""
    pass


@main.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def serve(host: str, port: int, reload: bool):
    """Start the Agent Data API server."""
    try:
        import uvicorn
        from agent_data.server import app
        
        click.echo(f"Starting Agent Data server on {host}:{port}")
        uvicorn.run(
            "agent_data.server:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except ImportError as e:
        click.echo(f"Error: Missing dependencies - {e}")
        click.echo("Please install with: pip install -e .[dev]")


@main.command()
def info():
    """Show agent data information."""
    import sys
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    import agent_data
    import importlib
    importlib.reload(agent_data)
    
    info_data = agent_data.get_info()
    
    click.echo("Agent Data Langroid Information:")
    click.echo(f"  Version: {info_data['version']}")
    click.echo(f"  Author: {info_data['author']}")
    click.echo(f"  Langroid Available: {info_data['langroid_available']}")
    if info_data['langroid_version']:
        click.echo(f"  Langroid Version: {info_data['langroid_version']}")
    
    click.echo("\nDependencies:")
    for dep, available in info_data['dependencies'].items():
        status = "✓" if available else "✗"
        click.echo(f"  {status} {dep}")


@main.command()
def test():
    """Run basic functionality tests."""
    click.echo("Running Agent Data tests...")
    
    try:
        from agent_data import check_dependencies
        deps = check_dependencies()
        
        failed_deps = [dep for dep, status in deps.items() if not status]
        
        if failed_deps:
            click.echo(f"❌ Missing dependencies: {', '.join(failed_deps)}")
            return 1
        else:
            click.echo("✅ All dependencies available")
            
        # Test basic imports
        try:
            import langroid
            click.echo("✅ Langroid import successful")
        except ImportError:
            click.echo("⚠️  Langroid not available (optional)")
            
        click.echo("✅ Agent Data CLI test completed successfully")
        return 0
        
    except Exception as e:
        click.echo(f"❌ Test failed: {e}")
        return 1


if __name__ == '__main__':
    main() 