"""
Unit tests for agent_data package functionality.
"""

import pytest
import sys


@pytest.mark.unit
class TestAgentDataCore:
    """Test core agent_data functionality."""

    def test_package_import(self):
        """Test that agent_data package can be imported."""
        import agent_data
        assert hasattr(agent_data, '__version__')
        assert agent_data.__version__ == "0.1.0"

    def test_get_version(self):
        """Test get_version function."""
        from agent_data import get_version
        assert get_version() == "0.1.0"

    def test_check_dependencies(self):
        """Test dependency checking."""
        from agent_data import check_dependencies
        deps = check_dependencies()
        assert isinstance(deps, dict)
        assert 'fastapi' in deps
        assert 'pydantic' in deps

    def test_get_info(self):
        """Test get_info function."""
        from agent_data import get_info
        info = get_info()
        assert isinstance(info, dict)
        assert 'version' in info
        assert 'author' in info
        assert info['version'] == "0.1.0"


@pytest.mark.unit
class TestCLI:
    """Test CLI functionality."""

    def test_cli_import(self):
        """Test that CLI module can be imported."""
        from agent_data import cli
        assert hasattr(cli, 'main')


@pytest.mark.unit  
class TestServer:
    """Test server functionality."""

    def test_server_import(self):
        """Test that server module can be imported."""
        from agent_data import server
        assert hasattr(server, 'app')

    def test_fastapi_app_creation(self):
        """Test FastAPI app is created properly."""
        from agent_data.server import app
        assert app is not None
        assert hasattr(app, 'title')
        assert app.title == "Agent Data Langroid" 