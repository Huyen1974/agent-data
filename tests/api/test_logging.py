"""Tests for structured logging functionality.

Tests the structured_logger module to verify:
1. JSON formatting of log entries
2. INFO log sampling (10% rate)
3. ERROR log metrics export
4. Log file output and stderr handling
5. Context field integration

Created for CLI 124 to validate logging implementation.
"""

import json
import os
import tempfile
import logging
from unittest.mock import patch, MagicMock

import pytest

# Import structured logging components
from agent_data_manager.utils.structured_logger import (
    StructuredLogger,
    StructuredJSONFormatter,
    SamplingFilter,
    ErrorMetricsHandler,
    get_logger,
)


@pytest.mark.logging
@pytest.mark.core
@pytest.mark.deferred
class TestStructuredJSONFormatter:
    """Test JSON formatting functionality."""

    @pytest.mark.deferred
    def test_basic_json_format(self):
        """Test basic log record JSON formatting."""
        formatter = StructuredJSONFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Format the record
        formatted = formatter.format(record)

        # Parse as JSON
        log_data = json.loads(formatted)

        # Verify required fields
        assert "timestamp" in log_data
        assert log_data["level"] == "INFO"
        assert log_data["module"] == "test.module"
        assert log_data["message"] == "Test message"
        assert "thread" in log_data
        assert "thread_name" in log_data

    @pytest.mark.deferred
    def test_context_fields(self):
        """Test that context fields are included in JSON output."""
        formatter = StructuredJSONFormatter()

        # Create a log record with context
        record = logging.LogRecord(
            name="test.module",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )

        # Add context fields
        record.session_id = "sess_123"
        record.doc_id = "doc_456"
        record.request_id = "req_789"
        record.duration_ms = 250

        # Format the record
        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verify context fields
        assert log_data["session_id"] == "sess_123"
        assert log_data["doc_id"] == "doc_456"
        assert log_data["request_id"] == "req_789"
        assert log_data["duration_ms"] == 250

    @pytest.mark.deferred
    def test_exception_formatting(self):
        """Test exception info formatting."""
        formatter = StructuredJSONFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test.module",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Exception occurred",
                args=(),
                exc_info=exc_info,
            )

            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            assert "exception" in log_data
            assert "ValueError: Test exception" in log_data["exception"]


@pytest.mark.logging
@pytest.mark.core
@pytest.mark.deferred
class TestSamplingFilter:
    """Test log sampling functionality."""

    @pytest.mark.deferred
    def test_error_always_passes(self):
        """Test that ERROR and above always pass the filter."""
        sampling_filter = SamplingFilter(info_sample_rate=0.0)  # 0% sampling

        error_record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py", lineno=1, msg="Error", args=(), exc_info=None
        )

        critical_record = logging.LogRecord(
            name="test", level=logging.CRITICAL, pathname="test.py", lineno=1, msg="Critical", args=(), exc_info=None
        )

        # Should always pass
        assert sampling_filter.filter(error_record) is True
        assert sampling_filter.filter(critical_record) is True

    @pytest.mark.deferred
    def test_warning_always_passes(self):
        """Test that WARNING always passes the filter."""
        sampling_filter = SamplingFilter(info_sample_rate=0.0)  # 0% sampling

        warning_record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="test.py", lineno=1, msg="Warning", args=(), exc_info=None
        )

        # Should always pass
        assert sampling_filter.filter(warning_record) is True

    @patch("random.random")
    @pytest.mark.deferred
    def test_info_sampling(self, mock_random):
        """Test INFO log sampling at 10% rate."""
        sampling_filter = SamplingFilter(info_sample_rate=0.1)

        info_record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py", lineno=1, msg="Info", args=(), exc_info=None
        )

        # Test pass case (random < 0.1)
        mock_random.return_value = 0.05
        assert sampling_filter.filter(info_record) is True

        # Test filter case (random >= 0.1)
        mock_random.return_value = 0.15
        assert sampling_filter.filter(info_record) is False


@pytest.mark.logging
@pytest.mark.integration
@pytest.mark.deferred
class TestErrorMetricsHandler:
    """Test error metrics functionality."""

    @pytest.mark.deferred
    def test_metrics_handler_initialization(self):
        """Test that metrics handler initializes correctly."""
        handler = ErrorMetricsHandler()

        assert handler.level == logging.ERROR
        assert hasattr(handler, "error_counter")
        assert hasattr(handler, "error_gauge")

    @patch("agent_data_manager.utils.structured_logger.PROMETHEUS_AVAILABLE", True)
    def test_error_metrics_emit(self):
        """Test that error metrics are emitted correctly."""
        handler = ErrorMetricsHandler()

        # Mock the counter and gauge
        handler.error_counter = MagicMock()
        handler.error_gauge = MagicMock()

        error_record = logging.LogRecord(
            name="test.module",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error",
            args=(),
            exc_info=None,
        )

        # Emit the record
        handler.emit(error_record)

        # Verify metrics were called
        handler.error_counter.labels.assert_called_with(module="test.module", level="ERROR")
        handler.error_counter.labels().inc.assert_called_once()


@pytest.mark.logging
@pytest.mark.core
@pytest.mark.deferred
class TestStructuredLogger:
    """Test the main StructuredLogger class."""

    @pytest.mark.deferred
    def test_logger_initialization(self):
        """Test logger initialization with temporary file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")

            logger = StructuredLogger("test.logger", log_file)

            assert logger.logger.name == "test.logger"
            assert logger.logger.level == logging.DEBUG
            assert len(logger.logger.handlers) >= 2  # File + stderr handlers

    def test_log_levels(self):
        """Test all log level methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")

            logger = StructuredLogger("test.logger", log_file)

            # Test all levels (should not raise exceptions)
            logger.debug("Debug message", session_id="test_session")
            logger.info("Info message", doc_id="test_doc")
            logger.warning("Warning message", request_id="test_request")
            logger.error("Error message", exc_info=False, duration_ms=100)
            logger.critical("Critical message", exc_info=False)

    @pytest.mark.deferred
    def test_log_file_creation(self):
        """Test that log file is created and contains JSON entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "logs", "test.log")

            logger = StructuredLogger("test.logger", log_file)

            # Log a message
            logger.error("Test error message", doc_id="test_doc_123")

            # Verify file was created
            assert os.path.exists(log_file)

            # Read and verify content
            with open(log_file, "r") as f:
                content = f.read().strip()

            # Should contain JSON
            log_data = json.loads(content)
            assert log_data["level"] == "ERROR"
            assert log_data["message"] == "Test error message"
            assert log_data["doc_id"] == "test_doc_123"


@pytest.mark.logging
@pytest.mark.core
@pytest.mark.deferred
class TestLoggerRegistry:
    """Test the global logger registry functionality."""

    @pytest.mark.deferred
    def test_get_logger_singleton(self):
        """Test that get_logger returns the same instance for the same name."""
        logger1 = get_logger("test.singleton")
        logger2 = get_logger("test.singleton")

        assert logger1 is logger2

    @pytest.mark.deferred
    def test_get_logger_different_names(self):
        """Test that different names return different logger instances."""
        logger1 = get_logger("test.logger1")
        logger2 = get_logger("test.logger2")

        assert logger1 is not logger2
        assert logger1.logger.name != logger2.logger.name


@pytest.mark.logging
@pytest.mark.integration
@pytest.mark.deferred
class TestLoggingIntegration:
    """Integration tests for the complete logging system."""

    def test_ten_log_entries_cli124_requirement(self):
        """Test generating 10 log entries as required by CLI 124.

        This test generates exactly 10 log entries (7 INFO, 3 ERROR) to verify
        JSON formatting, sampling, and file output as specified in CLI 124.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "cli124_test.log")

            logger = StructuredLogger("cli124.test", log_file)

            # Generate 7 INFO logs (will be sampled at 10%)
            info_contexts = [
                {"session_id": "sess_001", "operation": "document_save"},
                {"session_id": "sess_002", "operation": "vector_search"},
                {"doc_id": "doc_123", "operation": "metadata_update"},
                {"request_id": "req_456", "operation": "embedding_generate"},
                {"session_id": "sess_003", "doc_id": "doc_789", "operation": "sync_firestore"},
                {"duration_ms": 150, "operation": "query_qdrant"},
                {"session_id": "sess_004", "operation": "session_cleanup"},
            ]

            for i, context in enumerate(info_contexts, 1):
                logger.info(f"CLI124 INFO test message {i}", **context)

            # Generate 3 ERROR logs (will always be logged)
            error_contexts = [
                {"session_id": "sess_error_1", "error_code": "QDRANT_TIMEOUT"},
                {"doc_id": "doc_error_2", "error_code": "FIRESTORE_PERMISSION"},
                {"request_id": "req_error_3", "error_code": "OPENAI_RATE_LIMIT"},
            ]

            for i, context in enumerate(error_contexts, 1):
                logger.error(f"CLI124 ERROR test message {i}", **context)

            # Verify log file exists and contains content
            assert os.path.exists(log_file)

            # Read log entries
            with open(log_file, "r") as f:
                log_lines = [line.strip() for line in f.readlines() if line.strip()]

            # Parse JSON entries
            log_entries = []
            for line in log_lines:
                try:
                    log_entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON in log line: {line}")

            # Should have at least the 3 ERROR logs (INFO logs may be sampled)
            assert len(log_entries) >= 3

            # Verify ERROR logs are present
            error_logs = [entry for entry in log_entries if entry["level"] == "ERROR"]
            assert len(error_logs) == 3

            # Verify JSON structure
            for entry in log_entries:
                assert "timestamp" in entry
                assert "level" in entry
                assert "module" in entry
                assert "message" in entry

            # Verify context fields are preserved
            error_with_session = next((entry for entry in error_logs if "session_id" in entry), None)
            assert error_with_session is not None
            assert error_with_session["session_id"] == "sess_error_1"

            # Verify we have the expected log entries for CLI 124 requirement
            assert len(log_entries) >= 3  # At least 3 ERROR logs
