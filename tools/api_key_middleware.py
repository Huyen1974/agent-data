"""API Key masking middleware for secure logging."""

import logging
import re
from typing import Any, Dict, Optional


class APIKeyMaskingFilter(logging.Filter):
    """Logging filter to mask API keys and other sensitive information."""

    # Patterns to match various API key formats
    API_KEY_PATTERNS = [
        # Qdrant API keys (typically long alphanumeric strings)
        (r'api_key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?', r'api_key="***MASKED***"'),
        # OpenAI API keys (sk-...)
        (r"sk-[a-zA-Z0-9]{48}", r"sk-***MASKED***"),
        # Generic API key patterns
        (r'["\']?api_key["\']?\s*[:=]\s*["\']?([^"\'\s,}]{10,})["\']?', r'"api_key": "***MASKED***"'),
        # Authorization headers
        (r"Authorization:\s*Bearer\s+([a-zA-Z0-9_-]{10,})", r"Authorization: Bearer ***MASKED***"),
        # URL embedded API keys
        (r"(\?|&)api_key=([^&\s]+)", r"\1api_key=***MASKED***"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record to mask sensitive information."""
        if hasattr(record, "msg") and record.msg:
            # Mask API keys in the message
            record.msg = self.mask_sensitive_data(str(record.msg))

        # Mask API keys in arguments
        if hasattr(record, "args") and record.args:
            masked_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    masked_args.append(self.mask_sensitive_data(arg))
                elif isinstance(arg, dict):
                    masked_args.append(self.mask_dict_values(arg))
                else:
                    masked_args.append(arg)
            record.args = tuple(masked_args)

        return True

    def mask_sensitive_data(self, text: str) -> str:
        """Mask sensitive data in text using regex patterns."""
        for pattern, replacement in self.API_KEY_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def mask_dict_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask sensitive values in dictionaries."""
        if not isinstance(data, dict):
            return data

        masked_data = {}
        for key, value in data.items():
            if isinstance(key, str) and any(
                sensitive in key.lower() for sensitive in ["api_key", "token", "secret", "password"]
            ):
                masked_data[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked_data[key] = self.mask_dict_values(value)
            elif isinstance(value, str):
                masked_data[key] = self.mask_sensitive_data(value)
            else:
                masked_data[key] = value

        return masked_data


def setup_api_key_masking(logger_name: Optional[str] = None) -> None:
    """
    Set up API key masking for a specific logger or root logger.

    Args:
        logger_name: Name of the logger to add masking to. If None, adds to root logger.
    """
    logger = logging.getLogger(logger_name)

    # Check if filter is already added to avoid duplicates
    for filter_obj in logger.filters:
        if isinstance(filter_obj, APIKeyMaskingFilter):
            return

    # Add the masking filter
    api_key_filter = APIKeyMaskingFilter()
    logger.addFilter(api_key_filter)


def setup_global_api_key_masking() -> None:
    """Set up API key masking for all loggers in the application."""
    # Add to root logger to catch all logging
    setup_api_key_masking()

    # Add to specific loggers that might handle sensitive data
    sensitive_loggers = [
        "ADK.agent_data.vector_store.qdrant_store",
        "ADK.agent_data.tools.qdrant_vector_tools",
        "ADK.agent_data.tools.qdrant_embedding_tools",
        "ADK.agent_data.config.settings",
        "qdrant_client",
    ]

    for logger_name in sensitive_loggers:
        setup_api_key_masking(logger_name)


# Convenience function to mask sensitive data in strings
def mask_api_key(text: str) -> str:
    """
    Mask API keys in a string.

    Args:
        text: Text that may contain API keys

    Returns:
        Text with API keys masked
    """
    filter_obj = APIKeyMaskingFilter()
    return filter_obj.mask_sensitive_data(text)


# Convenience function to mask sensitive data in dictionaries
def mask_config_dict(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive values in a configuration dictionary.

    Args:
        config: Configuration dictionary that may contain sensitive data

    Returns:
        Dictionary with sensitive values masked
    """
    filter_obj = APIKeyMaskingFilter()
    return filter_obj.mask_dict_values(config)
