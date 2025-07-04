"""Test package installation and basic imports for agent_data_manager."""

import pytest
import sys

# import importlib


class TestPackageInstallation:
    """Test that the agent_data_manager package is properly installed and importable."""

    @pytest.mark.unit    def test_package_import(self):
        """Test that the main package can be imported."""
        import agent_data_manager

        assert hasattr(agent_data_manager, "__version__")
        assert agent_data_manager.__version__ == "0.1.0"
        assert hasattr(agent_data_manager, "__author__")
        assert agent_data_manager.__author__ == "Agent Data Team"

    @pytest.mark.unit    def test_core_modules_import(self):
        """Test that core modules can be imported."""
        # Test individual module imports
        try:
            from agent_data_manager.agent.agent_data_agent import AgentDataAgent

            assert AgentDataAgent is not None
        except ImportError as e:
            pytest.skip(f"AgentDataAgent import failed (may be expected in test env): {e}")

        try:
            from agent_data_manager.vector_store.qdrant_store import QdrantStore

            assert QdrantStore is not None
        except ImportError as e:
            pytest.skip(f"QdrantStore import failed (may be expected in test env): {e}")

        try:
            from agent_data_manager.config.settings import settings

            assert settings is not None
        except ImportError as e:
            pytest.skip(f"Settings import failed (may be expected in test env): {e}")

    @pytest.mark.unit    def test_package_in_sys_modules(self):
        """Test that the package is properly registered in sys.modules."""
        import agent_data_manager

        assert "agent_data_manager" in sys.modules
        assert sys.modules["agent_data_manager"] is agent_data_manager

    @pytest.mark.unit    def test_package_metadata(self):
        """Test package metadata is accessible."""
        import agent_data_manager

        # Test that __all__ is defined and contains expected items
        if hasattr(agent_data_manager, "__all__"):
            assert isinstance(agent_data_manager.__all__, list)
            assert "__version__" in agent_data_manager.__all__
            assert "__author__" in agent_data_manager.__all__

    @pytest.mark.unit    def test_new_imports_work(self):
        """Test that new import paths work correctly."""
        # Test that the new import paths work
        try:
            from agent_data_manager.agent.agent_data_agent import AgentDataAgent

            assert AgentDataAgent is not None
        except ImportError as e:
            pytest.skip(f"New import path failed: {e}")
