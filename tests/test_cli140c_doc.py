"""
CLI140c Documentation Validation Test

This test validates CSKH API specifications in documentation files:
- Agent_Data_Final_Report.md
- src/agent_data_manager/docs/INTEGRATE_WITH_CURSOR.md

Ensures consistency and completeness of CSKH API documentation.
"""

import re
from pathlib import Path

import pytest


class TestCLI140cDocumentation:
    """Test suite for CLI140c documentation validation."""

    @pytest.mark.doc
    @pytest.mark.unit
    def test_cskh_api_documentation_validation(self):
        """
        Validates CSKH API specifications in documentation files.

        This test ensures:
        1. CSKH API endpoint (/cskh_query) is documented in both files
        2. Request/response schemas are present and consistent
        3. Essential fields are documented (query_text, customer_context, etc.)
        4. Performance characteristics are mentioned
        5. Error handling examples are provided

        Follows CLI140c requirement for 1 test per CLI.
        """
        # Define file paths
        project_root = Path(__file__).parent.parent
        final_report_path = project_root / "Agent_Data_Final_Report.md"
        cursor_integration_path = (
            project_root
            / "src"
            / "agent_data_manager"
            / "docs"
            / "INTEGRATE_WITH_CURSOR.md"
        )

        # Verify files exist
        assert (
            final_report_path.exists()
        ), f"Agent_Data_Final_Report.md not found at {final_report_path}"
        assert (
            cursor_integration_path.exists()
        ), f"INTEGRATE_WITH_CURSOR.md not found at {cursor_integration_path}"

        # Read file contents
        final_report_content = final_report_path.read_text(encoding="utf-8")
        cursor_integration_content = cursor_integration_path.read_text(encoding="utf-8")

        # Define required CSKH API elements
        required_elements = {
            "endpoint": r"/cskh_query",
            "method": r"POST",
            "query_text": r"query_text",
            "customer_context": r"customer_context",
            "metadata_filters": r"metadata_filters",
            "response_schema": r"response.*schema|schema.*response",
            "performance": r"response.*time|performance|<1.*second",
            "error_handling": r"error.*handling|error.*response",
            "authentication": r"authorization|bearer.*token|jwt",
            "rate_limiting": r"rate.*limit|requests.*minute",
        }

        # Validate Final Report
        final_report_missing = []
        for element, pattern in required_elements.items():
            if not re.search(pattern, final_report_content, re.IGNORECASE):
                final_report_missing.append(element)

        # Validate Cursor Integration doc
        cursor_integration_missing = []
        for element, pattern in required_elements.items():
            if not re.search(pattern, cursor_integration_content, re.IGNORECASE):
                cursor_integration_missing.append(element)

        # Check for CSKH API section headers
        cskh_sections = [
            r"CSKH.*Agent.*API",
            r"Customer.*Care.*Agent",
            r"CSKH.*Query",
            r"CSKH.*Integration",
        ]

        final_report_has_cskh_section = any(
            re.search(pattern, final_report_content, re.IGNORECASE)
            for pattern in cskh_sections
        )

        cursor_integration_has_cskh_section = any(
            re.search(pattern, cursor_integration_content, re.IGNORECASE)
            for pattern in cskh_sections
        )

        # Validate JSON examples are present
        json_example_pattern = r'\{[^}]*"query_text"[^}]*\}'
        final_report_has_json = bool(
            re.search(json_example_pattern, final_report_content, re.DOTALL)
        )
        cursor_integration_has_json = bool(
            re.search(json_example_pattern, cursor_integration_content, re.DOTALL)
        )

        # Collect validation results
        validation_errors = []

        if final_report_missing:
            validation_errors.append(
                f"Agent_Data_Final_Report.md missing: {', '.join(final_report_missing)}"
            )

        if cursor_integration_missing:
            validation_errors.append(
                f"INTEGRATE_WITH_CURSOR.md missing: {', '.join(cursor_integration_missing)}"
            )

        if not final_report_has_cskh_section:
            validation_errors.append(
                "Agent_Data_Final_Report.md missing CSKH API section"
            )

        if not cursor_integration_has_cskh_section:
            validation_errors.append(
                "INTEGRATE_WITH_CURSOR.md missing CSKH API section"
            )

        if not final_report_has_json:
            validation_errors.append("Agent_Data_Final_Report.md missing JSON examples")

        if not cursor_integration_has_json:
            validation_errors.append("INTEGRATE_WITH_CURSOR.md missing JSON examples")

        # Assert all validations pass
        assert (
            not validation_errors
        ), "CSKH API documentation validation failed:\n" + "\n".join(validation_errors)

        # Success metrics for reporting
        total_elements = len(required_elements)
        final_report_coverage = (
            (total_elements - len(final_report_missing)) / total_elements * 100
        )
        cursor_integration_coverage = (
            (total_elements - len(cursor_integration_missing)) / total_elements * 100
        )

        print("✓ CSKH API documentation validation passed")
        print(f"✓ Agent_Data_Final_Report.md coverage: {final_report_coverage:.1f}%")
        print(
            f"✓ INTEGRATE_WITH_CURSOR.md coverage: {cursor_integration_coverage:.1f}%"
        )
        print("✓ Both files contain CSKH API sections and JSON examples")
