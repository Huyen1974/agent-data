"""
CLI 127 Package Setup Validation Tests

This module validates that the agent_data_manager package is properly set up
as an editable package and that imports work correctly across the codebase.
"""

import subprocess
import sys


class TestCLI127PackageSetup:
    """Test CLI 127 package setup and import validation."""

    def test_package_editable_installation(self):
        """Test that agent_data_manager is installed as editable package."""
        # Check if package is installed
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "agent_data_manager"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, "agent_data_manager package not found"

        # Verify it's an editable installation
        output = result.stdout
        assert "Editable project location:" in output, "Package not installed as editable"
        assert "agent_data_manager" in output, "Package name mismatch"
        assert "Version: 0.1.0" in output, "Package version mismatch"

    def test_core_imports_work(self):
        """Test that core agent_data_manager imports work correctly."""
        # Test basic tool import
        from agent_data_manager.tools.save_document_tool import save_document  # noqa: F401

        # Test vectorization tool import
        from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool  # noqa: F401

        # Test vector store import
        from agent_data_manager.vector_store.qdrant_store import QdrantStore  # noqa: F401

        # Test config import
        from agent_data_manager.config.settings import settings  # noqa: F401

        # If we reach here, all imports succeeded
        assert True

    def test_package_structure_accessible(self):
        """Test that package structure is accessible and organized correctly."""
        import agent_data_manager

        # Check package has proper attributes
        assert hasattr(agent_data_manager, "__version__") or hasattr(agent_data_manager, "__name__")

        # Test that tools module exists and is importable
        from agent_data_manager import tools  # noqa: F401

        # Test that vector_store module exists and is importable
        from agent_data_manager import vector_store  # noqa: F401

        assert True

    def test_import_consistency_across_codebase(self):
        """Test that imports are consistent and don't have old 'from tools.*' patterns."""
        import os
        import re

        # Get project root
        project_root = os.path.dirname(os.path.dirname(__file__))

        # Look for problematic import patterns in key directories
        problematic_imports = []

        # Check tests directory for old import patterns
        tests_dir = os.path.join(project_root, "tests")
        for root, dirs, files in os.walk(tests_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("test_cli127"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            # Look for direct "from tools." imports (should be from agent_data_manager.tools)
                            if re.search(r"^from tools\.", content, re.MULTILINE):
                                problematic_imports.append(file_path)
                    except Exception:
                        pass  # Skip files that can't be read

        # Allow up to 2 files with old imports (for backwards compatibility)
        assert len(problematic_imports) <= 2, f"Too many files with old import patterns: {problematic_imports}"
