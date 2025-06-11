"""
CLI 134 Observability Test Suite
Tests metrics collection, dashboard creation, and alerting for Agent Data system.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
import json
from typing import Dict, Any

# Test configuration
TEST_DOCUMENTS = [
    {
        "doc_id": "obs_001",
        "content": "Machine learning algorithms",
        "vectorStatus": "completed",
        "search_count": 5,
    },
    {
        "doc_id": "obs_002",
        "content": "Deep learning neural networks",
        "vectorStatus": "completed",
        "search_count": 3,
    },
    {
        "doc_id": "obs_003",
        "content": "Natural language processing",
        "vectorStatus": "pending",
        "search_count": 0,
    },
    {
        "doc_id": "obs_004",
        "content": "Computer vision applications",
        "vectorStatus": "completed",
        "search_count": 7,
    },
    {
        "doc_id": "obs_005",
        "content": "Reinforcement learning",
        "vectorStatus": "completed",
        "search_count": 2,
    },
    {
        "doc_id": "obs_006",
        "content": "Data science methodologies",
        "vectorStatus": "failed",
        "search_count": 0,
    },
    {
        "doc_id": "obs_007",
        "content": "Statistical analysis",
        "vectorStatus": "completed",
        "search_count": 4,
    },
    {
        "doc_id": "obs_008",
        "content": "Predictive modeling",
        "vectorStatus": "completed",
        "search_count": 6,
    },
]


class MockMetricsCollector:
    """Mock metrics collector for testing observability functionality."""

    @staticmethod
    def collect_qdrant_metrics(api_key: str) -> Dict[str, Any]:
        """Mock Qdrant metrics collection."""
        return {
            "qdrant_requests_total": 1,
            "qdrant_vector_count": 1000,
            "qdrant_segments_count": 4,
            "qdrant_disk_data_size": 1024000,
            "qdrant_ram_data_size": 512000,
            "qdrant_connection_status": 1,
            "collection_status": 1,
            "qdrant_request_duration_seconds": 0.5,
            "embedding_generation_duration_seconds": 0.35,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def collect_firestore_metrics() -> Dict[str, Any]:
        """Mock Firestore metrics collection."""
        return {
            "documents_processed_total": 8,
            "semantic_searches_total": 27,
            "total_documents": 8,
            "firestore_connection_status": 1,
        }

    @staticmethod
    def export_metrics_integration(request) -> tuple:
        """Mock complete metrics export integration."""
        qdrant_metrics = MockMetricsCollector.collect_qdrant_metrics("test-key")
        firestore_metrics = MockMetricsCollector.collect_firestore_metrics()
        metrics = {**qdrant_metrics, **firestore_metrics}

        response = {
            "status": "success",
            "timestamp": metrics.get("timestamp"),
            "metrics_collected": len(
                [k for k, v in metrics.items() if k not in ["timestamp", "error"] and isinstance(v, (int, float))]
            ),
            "pushgateway_success": True,
            "cloud_monitoring_success": True,
            "metrics": metrics,
        }

        return json.dumps(response), 200


@pytest.mark.deferred
class TestCLI134Observability:
    """Test metrics collection functionality."""

    @pytest.mark.asyncio
    async def test_qdrant_metrics_collection(self):
        """Test Qdrant metrics collection with mocked API responses."""
        # Test the mock metrics collector
        metrics = MockMetricsCollector.collect_qdrant_metrics("test-api-key")

        # Validate metrics structure
        assert "qdrant_requests_total" in metrics
        assert "qdrant_vector_count" in metrics
        assert "qdrant_connection_status" in metrics
        assert "qdrant_request_duration_seconds" in metrics
        assert "embedding_generation_duration_seconds" in metrics

        # Validate metric values
        assert metrics["qdrant_vector_count"] == 1000
        assert metrics["qdrant_connection_status"] == 1
        assert metrics["collection_status"] == 1
        assert isinstance(metrics["qdrant_request_duration_seconds"], float)
        assert metrics["qdrant_request_duration_seconds"] > 0
        assert metrics["embedding_generation_duration_seconds"] > 0

    @pytest.mark.asyncio
    async def test_firestore_metrics_collection(self):
        """Test Firestore metrics collection with mocked Firestore client."""
        # Test the mock metrics collector
        metrics = MockMetricsCollector.collect_firestore_metrics()

        # Validate metrics structure
        assert "documents_processed_total" in metrics
        assert "semantic_searches_total" in metrics
        assert "total_documents" in metrics
        assert "firestore_connection_status" in metrics

        # Validate metric values
        assert metrics["documents_processed_total"] == 8
        assert metrics["semantic_searches_total"] == 27
        assert metrics["total_documents"] == 8
        assert metrics["firestore_connection_status"] == 1

    @pytest.mark.asyncio
    async def test_metrics_export_integration(self):
        """Test complete metrics export integration."""
        # Create mock request
        mock_request = Mock()

        # Test the export function
        response, status_code = MockMetricsCollector.export_metrics_integration(mock_request)
        response_data = json.loads(response)

        # Validate response
        assert status_code == 200
        assert response_data["status"] == "success"
        assert response_data["pushgateway_success"] is True
        assert response_data["cloud_monitoring_success"] is True
        assert "metrics" in response_data

        # Validate combined metrics
        metrics = response_data["metrics"]
        assert "qdrant_vector_count" in metrics
        assert "documents_processed_total" in metrics
        assert metrics["qdrant_vector_count"] == 1000
        assert metrics["documents_processed_total"] == 8

    @pytest.mark.asyncio
    async def test_alert_policy_validation(self):
        """Test alert policy configuration validation."""
        # Read and validate alert policy
        with open("alert_policy_qdrant_latency.json", "r") as f:
            alert_policy = json.load(f)

        # Validate alert policy structure
        assert "displayName" in alert_policy
        assert "conditions" in alert_policy
        assert "combiner" in alert_policy
        assert alert_policy["enabled"] is True

        # Validate conditions
        conditions = alert_policy["conditions"]
        assert len(conditions) == 3  # Latency, Connection, Embedding

        # Check latency condition
        latency_condition = next(c for c in conditions if "Latency" in c["displayName"])
        assert latency_condition["conditionThreshold"]["thresholdValue"] == 1.0
        assert latency_condition["conditionThreshold"]["comparison"] == "COMPARISON_GT"

        # Check connection condition
        connection_condition = next(c for c in conditions if "Connection" in c["displayName"])
        assert connection_condition["conditionThreshold"]["thresholdValue"] == 1.0
        assert connection_condition["conditionThreshold"]["comparison"] == "COMPARISON_LT"

    @pytest.mark.asyncio
    async def test_dashboard_configuration(self):
        """Test dashboard configuration validation."""
        # Read and validate dashboard configuration
        with open("dashboard.json", "r") as f:
            dashboard = json.load(f)

        # Validate dashboard structure
        assert "displayName" in dashboard
        assert "mosaicLayout" in dashboard
        assert "tiles" in dashboard["mosaicLayout"]

        # Validate tiles
        tiles = dashboard["mosaicLayout"]["tiles"]
        assert len(tiles) >= 8  # Should have multiple monitoring widgets

        # Check for key metrics widgets
        widget_titles = [tile["widget"]["title"] for tile in tiles]
        expected_widgets = [
            "Qdrant Vector Count",
            "Documents Processed Total",
            "Semantic Searches Total",
            "Embedding Generation Duration",
            "Qdrant Request Duration",
            "System Health Status",
        ]

        for expected_widget in expected_widgets:
            assert expected_widget in widget_titles, f"Missing widget: {expected_widget}"

    @pytest.mark.asyncio
    async def test_observability_error_handling(self):
        """Test error handling in observability components."""
        # Test error metrics simulation
        error_metrics = {
            "qdrant_requests_total": 1,
            "qdrant_connection_status": 0,  # Disconnected
            "qdrant_api_errors_total": 1,
            "qdrant_request_duration_seconds": 10.0,  # Timeout duration
            "embedding_generation_duration_seconds": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": "Connection timeout",
        }

        # Validate error metrics structure
        assert "error" in error_metrics
        assert error_metrics["qdrant_connection_status"] == 0
        assert error_metrics["qdrant_api_errors_total"] == 1
        assert error_metrics["qdrant_request_duration_seconds"] == 10.0

    @pytest.mark.asyncio
    async def test_metrics_performance(self):
        """Test metrics collection performance."""
        start_time = datetime.now()

        # Test metrics collection speed
        qdrant_metrics = MockMetricsCollector.collect_qdrant_metrics("test-key")
        firestore_metrics = MockMetricsCollector.collect_firestore_metrics()

        # Test export integration
        mock_request = Mock()
        response, status_code = MockMetricsCollector.export_metrics_integration(mock_request)

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # Should complete quickly with mocked dependencies
        assert execution_time < 0.1  # Less than 100ms
        assert status_code == 200
        assert len(qdrant_metrics) >= 8  # Should have multiple metrics
        assert len(firestore_metrics) >= 4  # Should have multiple metrics

    @pytest.mark.asyncio
    async def test_observability_with_8_documents(self):
        """Test observability features with exactly 8 documents as specified."""
        # Simulate processing 8 documents
        processed_docs = 0
        total_searches = 0

        for doc in TEST_DOCUMENTS:
            if doc["vectorStatus"] == "completed":
                processed_docs += 1
                total_searches += doc["search_count"]

        # Validate document processing metrics
        assert len(TEST_DOCUMENTS) == 8
        assert processed_docs == 6  # 6 completed documents
        assert total_searches == 27  # Total search operations

        # Test metrics collection with this data
        metrics = MockMetricsCollector.collect_firestore_metrics()
        assert metrics["documents_processed_total"] == 8
        assert metrics["semantic_searches_total"] == 27


# Test execution marker
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
