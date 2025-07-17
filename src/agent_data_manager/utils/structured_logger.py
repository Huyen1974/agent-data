"""Structured logging utility with JSON format and sampling for cost optimization.

This module provides a structured logger that:
1. Formats logs as JSON for better integration with Cloud Logging
2. Implements 10% sampling for INFO level logs to reduce costs
3. Sends ERROR and above levels at 100% rate for reliability
4. Exports error metrics to Cloud Monitoring using prometheus_client
5. Outputs to both file (logs/agent_server.log) and stderr

Created for CLI 124 to standardize logging, reduce costs (<$1/day), and improve observability.
"""

import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from typing import Any

# Import prometheus_client for Cloud Monitoring integration
try:
    from prometheus_client import Counter, Gauge

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Create dummy metrics if prometheus_client is not available
    class DummyCounter:
        def inc(self, amount=1):
            pass

        def labels(self, **kwargs):
            return self

    class DummyGauge:
        def set(self, value):
            pass

        def labels(self, **kwargs):
            return self

    def Counter(*args, **kwargs):
        return DummyCounter()

    def Gauge(*args, **kwargs):
        return DummyGauge()


class StructuredJSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON with structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Extract standard fields
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "thread": record.thread,
            "thread_name": record.threadName,
        }

        # Add context fields if available
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id
        if hasattr(record, "doc_id"):
            log_entry["doc_id"] = record.doc_id
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        # Add exception info if present
        if record.exc_info and record.exc_info is not True:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from the record
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False)


class SamplingFilter(logging.Filter):
    """Filter that implements sampling for INFO level logs (10% rate)."""

    def __init__(self, info_sample_rate: float = 0.1):
        """Initialize with sample rate for INFO logs.

        Args:
            info_sample_rate: Fraction of INFO logs to keep (0.0 to 1.0)
        """
        super().__init__()
        self.info_sample_rate = info_sample_rate

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records based on level and sampling."""
        # Always allow ERROR and above
        if record.levelno >= logging.ERROR:
            return True

        # Always allow WARNING
        if record.levelno >= logging.WARNING:
            return True

        # Sample INFO and DEBUG logs
        if record.levelno >= logging.INFO:
            return random.random() < self.info_sample_rate

        # For DEBUG and below, sample at a lower rate
        return random.random() < (self.info_sample_rate * 0.1)


class ErrorMetricsHandler(logging.Handler):
    """Handler that exports error metrics to Cloud Monitoring."""

    _metrics_initialized = False
    _error_counter = None
    _error_gauge = None

    def __init__(self):
        super().__init__()
        self.setLevel(logging.ERROR)

        # Initialize metrics only once (class-level)
        if not ErrorMetricsHandler._metrics_initialized and PROMETHEUS_AVAILABLE:
            try:
                ErrorMetricsHandler._error_counter = Counter(
                    "agent_data_errors_total",
                    "Total number of errors in Agent Data system",
                    ["module", "level"],
                )

                ErrorMetricsHandler._error_gauge = Gauge(
                    "agent_data_error_rate", "Current error rate per minute", ["module"]
                )

                ErrorMetricsHandler._metrics_initialized = True
            except ValueError:
                # Metrics already registered, ignore
                pass

        # Reference class-level metrics
        self.error_counter = ErrorMetricsHandler._error_counter
        self.error_gauge = ErrorMetricsHandler._error_gauge

        # Track errors per minute
        self.error_window = {}
        self.window_size = 60  # 60 seconds

    def emit(self, record: logging.LogRecord):
        """Emit error metrics to prometheus."""
        if not PROMETHEUS_AVAILABLE or not self.error_counter or not self.error_gauge:
            return

        try:
            # Increment error counter
            self.error_counter.labels(module=record.name, level=record.levelname).inc()

            # Update error rate gauge
            current_time = int(time.time())
            minute_key = current_time // 60

            if minute_key not in self.error_window:
                self.error_window[minute_key] = 0
            self.error_window[minute_key] += 1

            # Clean old entries
            cutoff = minute_key - 5  # Keep last 5 minutes
            self.error_window = {
                k: v for k, v in self.error_window.items() if k >= cutoff
            }

            # Calculate current rate
            current_rate = sum(self.error_window.values()) / len(self.error_window)
            self.error_gauge.labels(module=record.name).set(current_rate)
        except Exception:
            # Silently ignore metrics errors to avoid disrupting logging
            pass


class StructuredLogger:
    """Main structured logger class with JSON formatting and sampling."""

    def __init__(self, name: str, log_file: str = "logs/agent_server.log"):
        """Initialize structured logger.

        Args:
            name: Logger name (typically __name__)
            log_file: Path to log file relative to project root
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers if logger already configured
        if any(
            isinstance(h, logging.FileHandler)
            and getattr(h, "baseFilename", "").endswith(log_file)
            for h in self.logger.handlers
        ):
            return

        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Create JSON formatter
        json_formatter = StructuredJSONFormatter()

        # Create sampling filter
        sampling_filter = SamplingFilter(info_sample_rate=0.1)

        # File handler with JSON format and sampling
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(sampling_filter)

        # Stderr handler for errors only (no sampling)
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.ERROR)
        stderr_handler.setFormatter(json_formatter)

        # Error metrics handler
        metrics_handler = ErrorMetricsHandler()

        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stderr_handler)
        self.logger.addHandler(metrics_handler)

    def debug(self, message: str, **context):
        """Log debug message with optional context."""
        self._log(logging.DEBUG, message, context)

    def info(self, message: str, **context):
        """Log info message with optional context."""
        self._log(logging.INFO, message, context)

    def warning(self, message: str, **context):
        """Log warning message with optional context."""
        self._log(logging.WARNING, message, context)

    def error(self, message: str, exc_info: bool = False, **context):
        """Log error message with optional context and exception info."""
        self._log(logging.ERROR, message, context, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False, **context):
        """Log critical message with optional context and exception info."""
        self._log(logging.CRITICAL, message, context, exc_info=exc_info)

    def _log(
        self, level: int, message: str, context: dict[str, Any], exc_info: bool = False
    ):
        """Internal logging method."""
        # Create log record with extra context
        extra = {"extra_fields": context} if context else {}

        # Handle exc_info properly - get current exception info if True
        if exc_info and exc_info is True:
            import sys

            exc_info = sys.exc_info()

        self.logger.log(level, message, exc_info=exc_info, extra=extra)


# Global logger registry
_loggers: dict[str, StructuredLogger] = {}


def get_logger(name: str, log_file: str = "logs/agent_server.log") -> StructuredLogger:
    """Get or create a structured logger instance.

    Args:
        name: Logger name (typically __name__)
        log_file: Path to log file relative to project root

    Returns:
        StructuredLogger instance
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, log_file)
    return _loggers[name]


# Create default logger for this module
logger = get_logger(__name__)
