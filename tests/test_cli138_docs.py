"""
CLI 138 Documentation Validation Tests

This module contains tests to validate the completeness and accuracy of project documentation,
ensuring that all required sections exist and contain appropriate content.
"""

import pytest
from pathlib import Path



class TestCLI138Docs:
    """Test suite for CLI 138 documentation validation."""

    def test_agent_data_final_report_exists(self):
        """Test that Agent_Data_Final_Report.md exists and is readable."""
        report_path = Path("Agent_Data_Final_Report.md")
        assert report_path.exists(), "Agent_Data_Final_Report.md file does not exist"
        assert report_path.is_file(), "Agent_Data_Final_Report.md is not a file"

        # Test that file is readable and not empty
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert len(content) > 1000, "Agent_Data_Final_Report.md appears to be too short"
        assert content.strip(), "Agent_Data_Final_Report.md appears to be empty"

    def test_agent_data_final_report_required_sections(self):
        """Test that Agent_Data_Final_Report.md contains all required sections."""
        report_path = Path("Agent_Data_Final_Report.md")

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_sections = [
            "# Agent Data (Knowledge Manager) - Final Report",
            "## Executive Summary",
            "## Project Overview",
            "## Architecture Overview",
            "## Key Features",
            "## Technical Specifications",
            "## API Reference",
            "## MCP Integration Guide",
            "## Deployment Guide",
            "## Monitoring & Observability",
            "## Testing Strategy",
            "## Security Considerations",
            "## Cost Optimization",
            "## Future Roadmap",
            "## Conclusion",
        ]

        for section in required_sections:
            assert section in content, f"Missing required section: {section}"

    def test_agent_data_final_report_technical_details(self):
        """Test that Agent_Data_Final_Report.md contains key technical details."""
        report_path = Path("Agent_Data_Final_Report.md")

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Test for key technical information
        technical_details = [
            "337 comprehensive tests",
            "90.2% pass rate",
            "Google Cloud",
            "Qdrant Cloud",
            "MCP",
            "A2A API",
            "batch_save",
            "batch_query",
            "chatgpt-db-project",
            "asia-southeast1",
            "us-east4-0",
        ]

        for detail in technical_details:
            assert detail in content, f"Missing technical detail: {detail}"

    def test_integrate_with_cursor_updated(self):
        """Test that INTEGRATE_WITH_CURSOR.md has been updated with CLI 138 information."""
        cursor_doc_path = Path("ADK/agent_data/docs/INTEGRATE_WITH_CURSOR.md")
        assert cursor_doc_path.exists(), "INTEGRATE_WITH_CURSOR.md file does not exist"

        with open(cursor_doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Test for CLI 138 updates
        cli138_updates = [
            "## CLI 138 Updates - Latest Features and Enhancements",
            "### New A2A API Batch Endpoints (CLI 137-138)",
            "POST /batch_save",
            "POST /batch_query",
            "### Performance Optimizations (CLI 138)",
            "337 tests",
            "### Latest Test Statistics (CLI 138)",
        ]

        for update in cli138_updates:
            assert update in content, f"Missing CLI 138 update: {update}"

    def test_documentation_api_examples_valid_json(self):
        """Test that API examples in documentation contain valid JSON."""
        report_path = Path("Agent_Data_Final_Report.md")

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for JSON code blocks
        import re

        json_blocks = re.findall(r"```json\n(.*?)\n```", content, re.DOTALL)

        assert len(json_blocks) > 0, "No JSON examples found in documentation"

        # Test that JSON blocks are not empty
        for i, json_block in enumerate(json_blocks):
            assert json_block.strip(), f"JSON block {i+1} is empty"
            # Basic JSON structure validation (should contain braces)
            assert (
                "{" in json_block and "}" in json_block
            ), f"JSON block {i+1} doesn't appear to be valid JSON structure"

    def test_documentation_contains_performance_metrics(self):
        """Test that documentation includes current performance metrics."""
        report_path = Path("Agent_Data_Final_Report.md")

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        performance_metrics = [
            "<1s",  # Response time
            "<10s",  # Batch processing time
            "2m27s",  # Test suite execution
            "210-305ms",  # Qdrant latency
            "337 tests",  # Test count
            "304 passed",  # Passed tests
        ]

        for metric in performance_metrics:
            assert metric in content, f"Missing performance metric: {metric}"

    def test_documentation_deployment_instructions(self):
        """Test that documentation includes comprehensive deployment instructions."""
        report_path = Path("Agent_Data_Final_Report.md")

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        deployment_elements = [
            "## Deployment Guide",
            "### Prerequisites",
            "### Deployment Steps",
            "pip install -r requirements.txt",
            "gcloud functions deploy",
            "python -m pytest",
            "OPENAI_API_KEY",
            "QDRANT_API_KEY",
        ]

        for element in deployment_elements:
            assert element in content, f"Missing deployment element: {element}"

    @pytest.mark.performance
    def test_documentation_validation_performance(self):
        """Test that documentation validation completes quickly."""
        import time

        start_time = time.time()

        # Run basic validation
        report_path = Path("Agent_Data_Final_Report.md")
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for key sections
        assert "## Executive Summary" in content
        assert "## Conclusion" in content

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete in under 1 second
        assert execution_time < 1.0, f"Documentation validation took too long: {execution_time:.2f}s"

    def test_documentation_file_sizes_reasonable(self):
        """Test that documentation files are reasonably sized."""
        report_path = Path("Agent_Data_Final_Report.md")
        cursor_doc_path = Path("ADK/agent_data/docs/INTEGRATE_WITH_CURSOR.md")

        # Check file sizes
        report_size = report_path.stat().st_size
        cursor_doc_size = cursor_doc_path.stat().st_size

        # Agent_Data_Final_Report.md should be substantial but not excessive
        assert 10000 < report_size < 500000, f"Agent_Data_Final_Report.md size unexpected: {report_size} bytes"

        # INTEGRATE_WITH_CURSOR.md should be comprehensive
        assert 5000 < cursor_doc_size < 1000000, f"INTEGRATE_WITH_CURSOR.md size unexpected: {cursor_doc_size} bytes"

    def test_documentation_encoding_utf8(self):
        """Test that documentation files use UTF-8 encoding."""
        docs_to_check = [Path("Agent_Data_Final_Report.md"), Path("ADK/agent_data/docs/INTEGRATE_WITH_CURSOR.md")]

        for doc_path in docs_to_check:
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # If we can read it as UTF-8, the test passes
                assert len(content) > 0, f"{doc_path} appears to be empty"
            except UnicodeDecodeError:
                pytest.fail(f"{doc_path} is not valid UTF-8 encoded")


# Performance marker for selective test execution
pytestmark = pytest.mark.cli138
