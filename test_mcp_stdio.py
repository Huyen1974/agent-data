#!/usr/bin/env python3
"""Simple MCP stdio test for Cursor connectivity."""

import json
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def save_document_simple(
    doc_id: str, content: str, save_dir: str = "saved_documents"
) -> dict:
    """Simple document save function for testing."""
    try:
        # Create directory if it doesn't exist
        save_path = Path(save_dir)
        save_path.mkdir(exist_ok=True)

        # Save document
        doc_path = save_path / f"{doc_id}.txt"
        doc_path.write_text(content, encoding="utf-8")

        return {
            "status": "success",
            "doc_id": doc_id,
            "path": str(doc_path),
            "content_length": len(content),
        }
    except Exception as e:
        return {"status": "failed", "error": str(e), "doc_id": doc_id}


def semantic_search_simple(query: str, limit: int = 5) -> dict:
    """Simple semantic search mock for testing."""
    try:
        # Mock search results
        results = []
        for i in range(min(limit, 3)):  # Return max 3 mock results
            results.append(
                {
                    "doc_id": f"mock_doc_{i}",
                    "content": f"Mock document {i} content related to: {query}",
                    "score": 0.9 - (i * 0.1),
                }
            )

        return {
            "status": "success",
            "query": query,
            "results": results,
            "total_found": len(results),
        }
    except Exception as e:
        return {"status": "failed", "error": str(e), "query": query, "results": []}


def main():
    """Main MCP stdio handler."""
    logger.info("Simple MCP Server started. Waiting for JSON input via stdin...")

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            logger.info(f"Received input: {line}")

            try:
                input_data = json.loads(line)
            except json.JSONDecodeError as e:
                error_response = json.dumps({"error": f"Invalid JSON: {e}"})
                print(error_response, flush=True)
                continue

            tool_name = input_data.get("tool_name")
            kwargs = input_data.get("kwargs", {})

            if tool_name == "save_document":
                result = save_document_simple(
                    doc_id=kwargs.get("doc_id", ""),
                    content=kwargs.get("content", ""),
                    save_dir=kwargs.get("save_dir", "saved_documents"),
                )
            elif tool_name == "semantic_search":
                result = semantic_search_simple(
                    query=kwargs.get("query", ""), limit=kwargs.get("limit", 5)
                )
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            # Send result
            response = json.dumps({"result": result})
            print(response, flush=True)
            logger.info(f"Sent response: {response}")

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")


if __name__ == "__main__":
    main()
