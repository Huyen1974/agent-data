"""
Test cases for CLI119D10 enhancements:
- Metadata validation and versioning enhancements
- Enhanced change reporting with analytics
- Firestore rules validation
- Alerting policy deployment verification
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import the enhanced modules
from agent_data_manager.vector_store.firestore_metadata_manager import (
    FirestoreMetadataManager,
)


class TestMetadataValidationEnhancements:
    """Test enhanced metadata validation functionality."""

    @pytest.fixture
    def metadata_manager(self):
        """Create a mock FirestoreMetadataManager for testing."""
        with patch(
            "agent_data_manager.vector_store.firestore_metadata_manager.FirestoreAsyncClient"
        ):
            manager = FirestoreMetadataManager(
                project_id="test-project", collection_name="test-collection"
            )
            manager.db = Mock()
            return manager

    def test_validate_metadata_valid_data(self, metadata_manager):
        """Test metadata validation with valid data."""
        valid_metadata = {
            "doc_id": "test_doc_123",
            "vectorStatus": "completed",
            "lastUpdated": "2025-01-27T19:00:00Z",
            "level_1": "document",
            "level_2": "test",
            "original_text": "This is a test document.",
        }

        result = metadata_manager._validate_metadata(valid_metadata)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_metadata_missing_required_fields(self, metadata_manager):
        """Test metadata validation with missing required fields."""
        invalid_metadata = {
            "vectorStatus": "completed",
            "lastUpdated": "2025-01-27T19:00:00Z",
        }

        result = metadata_manager._validate_metadata(invalid_metadata)

        assert result["valid"] is False
        assert "Missing required field: doc_id" in result["errors"]

    def test_validate_metadata_invalid_types(self, metadata_manager):
        """Test metadata validation with invalid data types."""
        invalid_metadata = {
            "doc_id": 123,  # Should be string
            "version": "not_a_number",  # Should be integer
            "level_1": ["not", "a", "string"],  # Should be string
        }

        result = metadata_manager._validate_metadata(invalid_metadata)

        assert result["valid"] is False
        assert "doc_id must be a string" in result["errors"]
        assert "version must be an integer" in result["errors"]
        assert "level_1 must be a string or None" in result["errors"]

    def test_validate_metadata_content_size_limits(self, metadata_manager):
        """Test metadata validation with content size limits."""
        large_text = "x" * 60000  # Exceeds 50KB limit
        long_level = "x" * 150  # Exceeds 100 character limit

        invalid_metadata = {
            "doc_id": "test_doc",
            "original_text": large_text,
            "level_1": long_level,
        }

        result = metadata_manager._validate_metadata(invalid_metadata)

        assert result["valid"] is False
        assert "original_text exceeds 50KB limit" in result["errors"]
        assert "level_1 must be 100 characters or less" in result["errors"]

    def test_validate_metadata_invalid_timestamps(self, metadata_manager):
        """Test metadata validation with invalid timestamp formats."""
        invalid_metadata = {
            "doc_id": "test_doc",
            "lastUpdated": "not-a-timestamp",
            "createdAt": "2025-13-45T99:99:99Z",  # Invalid date
        }

        result = metadata_manager._validate_metadata(invalid_metadata)

        assert result["valid"] is False
        assert any(
            "must be a valid ISO format timestamp" in error
            for error in result["errors"]
        )

    def test_validate_version_increment_valid(self, metadata_manager):
        """Test version increment validation with valid increments."""
        existing_data = {"version": 5}
        new_metadata = {"version": 6}

        result = metadata_manager._validate_version_increment(
            existing_data, new_metadata
        )

        assert result is True

    def test_validate_version_increment_auto_increment(self, metadata_manager):
        """Test version increment validation with auto-increment (no version specified)."""
        existing_data = {"version": 5}
        new_metadata = {"doc_id": "test"}  # No version specified

        result = metadata_manager._validate_version_increment(
            existing_data, new_metadata
        )

        assert result is True

    def test_validate_version_increment_decrease(self, metadata_manager):
        """Test version increment validation with version decrease."""
        existing_data = {"version": 5}
        new_metadata = {"version": 3}  # Decrease

        result = metadata_manager._validate_version_increment(
            existing_data, new_metadata
        )

        assert result is False

    def test_validate_version_increment_skip(self, metadata_manager):
        """Test version increment validation with version skip."""
        existing_data = {"version": 5}
        new_metadata = {"version": 8}  # Skip versions 6 and 7

        result = metadata_manager._validate_version_increment(
            existing_data, new_metadata
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_metadata_statistics(self, metadata_manager):
        """Test metadata statistics collection."""
        # Mock Firestore data
        mock_docs = [
            Mock(
                to_dict=lambda: {
                    "level_1": "document",
                    "version": 1,
                    "lastUpdated": "2025-01-27T19:00:00Z",
                    "createdAt": "2025-01-27T18:00:00Z",
                }
            ),
            Mock(
                to_dict=lambda: {
                    "level_1": "document",
                    "version": 2,
                    "lastUpdated": "2025-01-27T20:00:00Z",
                    "createdAt": "2025-01-27T17:00:00Z",
                }
            ),
            Mock(
                to_dict=lambda: {
                    "level_1": "report",
                    "version": 1,
                    "lastUpdated": "2025-01-27T18:30:00Z",
                    "createdAt": "2025-01-27T18:30:00Z",
                }
            ),
        ]

        async def mock_stream():
            for doc in mock_docs:
                yield doc

        metadata_manager.db.collection.return_value.stream.return_value = mock_stream()

        stats = await metadata_manager.get_metadata_statistics()

        assert stats["total_documents"] == 3
        assert stats["hierarchy_distribution"]["document"] == 2
        assert stats["hierarchy_distribution"]["report"] == 1
        assert stats["version_distribution"][1] == 2
        assert stats["version_distribution"][2] == 1
        assert stats["latest_update"] == "2025-01-27T20:00:00Z"
        assert stats["oldest_document"] == "2025-01-27T17:00:00Z"


class TestChangeReportingEnhancements:
    """Test enhanced change reporting functionality."""

    def _import_function_safely(self, function_name):
        """Helper to import functions from change_report_function without functions_framework."""
        try:
            # Import from our standalone module
            from tests.api.change_report_functions import (
                analyze_change_impact,
                analyze_changes,
                calculate_data_quality_metrics,
                calculate_string_similarity,
                generate_change_report,
            )

            function_map = {
                "calculate_string_similarity": calculate_string_similarity,
                "analyze_change_impact": analyze_change_impact,
                "calculate_data_quality_metrics": calculate_data_quality_metrics,
                "analyze_changes": analyze_changes,
                "generate_change_report": generate_change_report,
            }

            if function_name in function_map:
                return function_map[function_name]
            else:
                pytest.skip(
                    f"Function {function_name} not found in change_report_functions"
                )

        except ImportError as e:
            pytest.skip(f"Failed to import {function_name}: {e}")

    def test_calculate_string_similarity(self):
        """Test string similarity calculation."""
        calculate_string_similarity = self._import_function_safely(
            "calculate_string_similarity"
        )

        # Identical strings
        assert calculate_string_similarity("hello", "hello") == 1.0

        # Completely different strings
        assert calculate_string_similarity("hello", "world") < 1.0

        # Similar strings
        similarity = calculate_string_similarity("hello world", "hello earth")
        assert 0.0 < similarity < 1.0

        # Empty strings
        assert calculate_string_similarity("", "") == 0.0
        assert calculate_string_similarity("hello", "") == 0.0

    def test_analyze_change_impact(self):
        """Test change impact analysis."""
        analyze_change_impact = self._import_function_safely("analyze_change_impact")

        old_data = {"vectorStatus": "pending", "level_1": "document"}
        new_data = {"vectorStatus": "completed", "level_1": "document"}
        changes = {
            "modified_fields": [{"field": "vectorStatus"}],
            "significant_changes": [
                {"field": "vectorStatus", "importance": "critical"}
            ],
        }

        impact = analyze_change_impact(old_data, new_data, changes)

        assert impact["overall_impact"] == "critical"
        assert "vector_search" in impact["affected_systems"]
        assert "vectorization_completed" in impact["workflow_impact"]

    def test_calculate_data_quality_metrics(self):
        """Test data quality metrics calculation."""
        calculate_data_quality_metrics = self._import_function_safely(
            "calculate_data_quality_metrics"
        )

        old_data = {"doc_id": "test", "vectorStatus": None, "level_1": "document"}
        new_data = {
            "doc_id": "test",
            "vectorStatus": "completed",
            "level_1": "document",
            "level_2": "test",
            "lastUpdated": "2025-01-27T19:00:00Z",
        }

        metrics = calculate_data_quality_metrics(old_data, new_data)

        assert (
            metrics["completeness_score"] == 5 / 9
        )  # 5 out of 9 possible fields filled
        assert (
            metrics["consistency_score"] == 2 / 3
        )  # 2 out of 3 hierarchy levels filled
        assert metrics["validity_score"] == 1.0  # All required fields present
        assert metrics["quality_trend"] == "improving"  # More complete than before

    def test_enhanced_change_analysis(self):
        """Test enhanced change analysis with detailed metrics."""
        analyze_changes = self._import_function_safely("analyze_changes")

        old_value = {
            "stringValue": {"stringValue": "old text"},
            "numberValue": {"integerValue": "10"},
            "statusValue": {"stringValue": "pending"},
        }

        new_value = {
            "stringValue": {"stringValue": "new text"},
            "numberValue": {"integerValue": "15"},
            "statusValue": {"stringValue": "completed"},
            "newField": {"stringValue": "added"},
        }

        changes = analyze_changes(old_value, new_value)

        # Check that enhanced analysis is present
        assert "impact_analysis" in changes
        assert "data_quality_metrics" in changes
        assert len(changes["added_fields"]) == 1
        assert len(changes["modified_fields"]) == 3

        # Check detailed field analysis
        for field_change in changes["modified_fields"]:
            assert "change_type" in field_change
            assert "old_type" in field_change
            assert "new_type" in field_change


class TestFirestoreRulesValidation:
    """Test Firestore rules deployment and validation."""

    def test_firestore_rules_syntax(self):
        """Test that Firestore rules file has valid syntax."""
        import os

        rules_file = "firestore.rules"
        assert os.path.exists(rules_file), "Firestore rules file should exist"

        with open(rules_file) as f:
            content = f.read()

        # Basic syntax checks
        assert "rules_version = '2'" in content
        assert "service cloud.firestore" in content
        assert "match /databases/{database}/documents" in content

        # Check for required collections
        assert "document_metadata" in content
        assert "agent_sessions" in content
        assert "agent_data" in content

    def test_firebase_json_configuration(self):
        """Test Firebase configuration file."""
        import json
        import os

        firebase_file = "firebase.json"
        assert os.path.exists(firebase_file), "Firebase configuration file should exist"

        with open(firebase_file) as f:
            config = json.load(f)

        assert "firestore" in config
        assert config["firestore"]["rules"] == "firestore.rules"
        assert config["firestore"]["indexes"] == "firestore.indexes.json"

    def test_firestore_indexes_configuration(self):
        """Test Firestore indexes configuration."""
        import json
        import os

        indexes_file = "firestore.indexes.json"
        assert os.path.exists(indexes_file), "Firestore indexes file should exist"

        with open(indexes_file) as f:
            config = json.load(f)

        assert "indexes" in config
        assert "fieldOverrides" in config

        # Check for important indexes
        index_collections = [index["collectionGroup"] for index in config["indexes"]]
        assert "document_metadata" in index_collections
        assert "agent_sessions" in index_collections
        assert "change_reports" in index_collections


class TestAlertingPolicyValidation:
    """Test alerting policy configuration and deployment."""

    def test_alert_policy_configuration(self):
        """Test alerting policy JSON configuration."""
        import json
        import os

        policy_file = "alert_policy_latency.json"
        assert os.path.exists(policy_file), "Alert policy file should exist"

        with open(policy_file) as f:
            policy = json.load(f)

        # Check required fields
        assert "displayName" in policy
        assert "conditions" in policy
        assert "combiner" in policy
        assert "enabled" in policy

        # Check conditions
        assert len(policy["conditions"]) > 0
        for condition in policy["conditions"]:
            assert "displayName" in condition
            assert "conditionThreshold" in condition

            threshold = condition["conditionThreshold"]
            assert "filter" in threshold
            assert "comparison" in threshold
            assert "thresholdValue" in threshold

    def test_alert_policy_metrics_references(self):
        """Test that alert policy references correct metrics."""
        import json

        with open("alert_policy_latency.json") as f:
            policy = json.load(f)

        # Check that policy references Qdrant metrics
        filters = [
            condition["conditionThreshold"]["filter"]
            for condition in policy["conditions"]
        ]

        # Should reference custom Qdrant metrics
        assert any(
            "custom.googleapis.com/qdrant" in filter_str for filter_str in filters
        )


@pytest.mark.integration
class TestCLI119D10Integration:
    """Integration tests for CLI119D10 enhancements."""

    def _import_function_safely(self, function_name):
        """Helper to import functions from change_report_function without functions_framework."""
        try:
            # Import from our standalone module
            from tests.api.change_report_functions import (
                analyze_change_impact,
                analyze_changes,
                calculate_data_quality_metrics,
                calculate_string_similarity,
                generate_change_report,
            )

            function_map = {
                "calculate_string_similarity": calculate_string_similarity,
                "analyze_change_impact": analyze_change_impact,
                "calculate_data_quality_metrics": calculate_data_quality_metrics,
                "analyze_changes": analyze_changes,
                "generate_change_report": generate_change_report,
            }

            if function_name in function_map:
                return function_map[function_name]
            else:
                pytest.skip(
                    f"Function {function_name} not found in change_report_functions"
                )

        except ImportError as e:
            pytest.skip(f"Failed to import {function_name}: {e}")

    @pytest.mark.asyncio
    async def test_metadata_validation_integration(self):
        """Test metadata validation in real workflow."""
        # This would test the actual integration with Firestore
        # For now, we'll test the validation logic

        with patch(
            "agent_data_manager.vector_store.firestore_metadata_manager.FirestoreAsyncClient"
        ):
            manager = FirestoreMetadataManager(project_id="test-project")
            manager.db = Mock()

            # Test saving metadata with validation
            valid_metadata = {
                "doc_id": "integration_test_doc",
                "vectorStatus": "completed",
                "lastUpdated": datetime.utcnow().isoformat(),
                "level_1": "integration_test",
                "level_2": "cli119d10",
            }

            # Mock existing document
            mock_doc = Mock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {
                "version": 1,
                "lastUpdated": "2025-01-27T18:00:00Z",
            }

            manager.db.collection.return_value.document.return_value.get = AsyncMock(
                return_value=mock_doc
            )
            manager.db.collection.return_value.document.return_value.set = AsyncMock()

            # This should not raise an exception
            await manager.save_metadata("integration_test_doc", valid_metadata)

            # Verify that set was called (metadata was saved)
            manager.db.collection.return_value.document.return_value.set.assert_called_once()

    def test_change_reporting_integration(self):
        """Test change reporting with enhanced analytics."""
        generate_change_report = self._import_function_safely("generate_change_report")

        change_info = {
            "event_type": "google.cloud.firestore.document.v1.updated",
            "operation_type": "update",
            "collection": "document_metadata",
            "document_id": "test_doc_123",
            "timestamp": datetime.utcnow().isoformat(),
            "old_value": {
                "vectorStatus": {"stringValue": "pending"},
                "version": {"integerValue": "1"},
            },
            "new_value": {
                "vectorStatus": {"stringValue": "completed"},
                "version": {"integerValue": "2"},
                "level_1": {"stringValue": "document"},
            },
        }

        report = generate_change_report(change_info)

        # Verify enhanced report structure
        assert "report_id" in report
        assert "timestamp" in report
        assert "event_info" in report
        assert "changes" in report

        # Verify enhanced analytics are present
        changes = report["changes"]
        assert "impact_analysis" in changes
        assert "data_quality_metrics" in changes
        assert "significant_changes" in changes

        # Verify impact analysis
        impact = changes["impact_analysis"]
        assert impact["overall_impact"] in ["low", "medium", "high", "critical"]
        assert isinstance(impact["affected_systems"], list)
        assert isinstance(impact["workflow_impact"], list)
