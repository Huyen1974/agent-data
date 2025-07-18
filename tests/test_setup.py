"""
Basic setup tests for Agent Data Langroid project.
Tests core functionality, imports, and version requirements.
"""

import os
import sys

import pytest


class TestProjectSetup:
    """Test project basic setup and configuration."""

    def test_python_version(self):
        """Test that Python version is compatible."""
        version_info = sys.version_info
        assert version_info >= (3, 10), f"Python 3.10+ required, got {version_info}"
        assert version_info < (
            3,
            13,
        ), f"Python <3.13 required for Langroid, got {version_info}"

    @pytest.mark.langroid
    def test_langroid_import_and_version(self):
        """Test that Langroid can be imported and has correct version."""
        try:
            import langroid

            # Check version
            version = langroid.__version__
            assert version is not None, "Langroid version should not be None"
            assert "0.58" in version, f"Expected Langroid 0.58.x, got {version}"

            print(f"✓ Langroid version: {version}")

        except ImportError as e:
            pytest.fail(f"Failed to import langroid: {e}")

    @pytest.mark.langroid
    def test_langroid_basic_functionality(self):
        """Test basic Langroid functionality."""
        try:

            # Test basic imports
            from langroid.language_models import OpenAIGPTConfig

            # Test creating a basic config (without API key)
            config = OpenAIGPTConfig(chat_model="gpt-4o", use_chat_for_completion=True)
            assert config is not None

            print("✓ Basic Langroid functionality working")

        except Exception as e:
            pytest.fail(f"Basic Langroid functionality test failed: {e}")

    def test_required_dependencies(self):
        """Test that all required dependencies can be imported."""
        required_modules = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "openai",
            "qdrant_client",
            "google.cloud.storage",
            "google.cloud.firestore",
            "pandas",
            "numpy",
            "scikit_learn",
            "python_dotenv",
            "click",
            "rich",
            "typer",
        ]

        failed_imports = []
        for module in required_modules:
            try:
                __import__(module)
                print(f"✓ {module}")
            except ImportError as e:
                failed_imports.append(f"{module}: {e}")

        if failed_imports:
            pytest.fail(
                "Failed to import required modules:\n" + "\n".join(failed_imports)
            )

    def test_project_structure(self):
        """Test that basic project structure exists."""
        expected_dirs = [
            "agent_data",
            "tests",
            "scripts",
            "terraform",
            "functions",
            "containers",
            "workflows",
        ]

        missing_dirs = []
        for dir_name in expected_dirs:
            if not os.path.exists(dir_name):
                missing_dirs.append(dir_name)

        if missing_dirs:
            pytest.fail(f"Missing project directories: {missing_dirs}")

    def test_configuration_files(self):
        """Test that required configuration files exist."""
        required_files = [
            "pyproject.toml",
            "requirements.txt",
            "README.md",
            "LICENSE",
            ".gitignore",
            "pytest.ini",
        ]

        missing_files = []
        for file_name in required_files:
            if not os.path.exists(file_name):
                missing_files.append(file_name)

        if missing_files:
            pytest.fail(f"Missing configuration files: {missing_files}")


class TestDummyApplications:
    """Test dummy applications for CI/CD."""

    def test_dummy_function_structure(self):
        """Test that dummy function has correct structure."""
        function_files = [
            "functions/dummy_function/main.py",
            "functions/dummy_function/requirements.txt",
        ]

        for file_path in function_files:
            assert os.path.exists(file_path), f"Missing file: {file_path}"

    def test_dummy_cloudrun_structure(self):
        """Test that dummy Cloud Run app has correct structure."""
        cloudrun_files = [
            "containers/cloudrun_dummy/app.py",
            "containers/cloudrun_dummy/requirements.txt",
            "containers/cloudrun_dummy/Dockerfile",
        ]

        for file_path in cloudrun_files:
            assert os.path.exists(file_path), f"Missing file: {file_path}"

    def test_dummy_workflow_structure(self):
        """Test that dummy workflow has correct structure."""
        workflow_files = ["workflows/dummy_workflow.yaml"]

        for file_path in workflow_files:
            assert os.path.exists(file_path), f"Missing file: {file_path}"


class TestTerraformSetup:
    """Test Terraform configuration setup."""

    def test_terraform_files_exist(self):
        """Test that all Terraform files exist."""
        terraform_files = [
            "terraform/provider.tf",
            "terraform/variables.tf",
            "terraform/gcs_buckets.tf",
            "terraform/artifact_registry.tf",
            "terraform/backend.tf",
            "terraform/outputs.tf",
        ]

        for file_path in terraform_files:
            assert os.path.exists(file_path), f"Missing Terraform file: {file_path}"

    def test_terraform_syntax_basic(self):
        """Basic test that Terraform files have valid syntax."""
        # This is a very basic check - just ensure files are not empty
        terraform_files = [
            "terraform/provider.tf",
            "terraform/variables.tf",
            "terraform/gcs_buckets.tf",
            "terraform/artifact_registry.tf",
        ]

        for file_path in terraform_files:
            with open(file_path) as f:
                content = f.read().strip()
                assert len(content) > 0, f"Terraform file {file_path} is empty"
                assert (
                    "terraform" in content
                    or "resource" in content
                    or "variable" in content
                ), f"Terraform file {file_path} doesn't appear to contain valid Terraform syntax"
