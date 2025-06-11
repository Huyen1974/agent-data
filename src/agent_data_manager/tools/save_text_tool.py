import os
import logging

logger = logging.getLogger(__name__)

# Define the base directory for saving files relative to this script
SAVE_DIR = os.path.join(os.path.dirname(__file__), "..", "test_outputs")

# Ensure the save directory exists
os.makedirs(SAVE_DIR, exist_ok=True)


def save_text(filename: str, content: str) -> dict:
    """Saves the given text content to a specified file in a designated directory.

    Args:
        filename: The name of the file to save.
        content: The text content to write to the file.

    Returns:
        A dictionary indicating success or failure.
    """
    logger.info(f"Executing save_text tool with filename: {filename}")
    try:
        # Sanitize filename to prevent directory traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            error_msg = "Invalid filename. Contains disallowed characters ('..', '/', '\\')."
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg}

        actual_path = os.path.join(SAVE_DIR, filename)

        with open(actual_path, "w") as f:
            f.write(content)

        logger.info(f"Successfully saved text to {filename} in {SAVE_DIR}")
        msg = f"Saved text: {filename}"
        return {"status": "success", "result": msg}
    except Exception as e:
        logger.error(f"Error saving text to {filename}: {e}", exc_info=True)
        return {"status": "failed", "error": f"Error saving file: {e}"}
