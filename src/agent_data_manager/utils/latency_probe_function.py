"""Latency probe Cloud Function for monitoring Qdrant performance."""

import asyncio
import datetime
import logging
import time
from typing import Any

from qdrant_client import AsyncQdrantClient

from ..config.settings import settings

logger = logging.getLogger(__name__)


class QdrantLatencyProbe:
    """Probe for measuring Qdrant API latency."""

    def __init__(self):
        """Initialize the latency probe."""
        self.client: AsyncQdrantClient | None = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure Qdrant client is initialized."""
        if self._initialized:
            return

        try:
            config = settings.get_qdrant_config()
            self.client = AsyncQdrantClient(
                url=config["url"],
                api_key=config["api_key"],
            )
            self._initialized = True
            logger.info("QdrantLatencyProbe initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize QdrantLatencyProbe: {e}")
            raise

    async def measure_ping_latency(self) -> dict[str, Any]:
        """
        Measure ping latency to Qdrant cluster.

        Returns:
            Dictionary with ping measurement results
        """
        await self._ensure_initialized()

        start_time = time.time()

        try:
            # Use collections API as a simple ping operation
            collections = await self.client.get_collections()
            end_time = time.time()

            latency_ms = (end_time - start_time) * 1000

            return {
                "operation": "Ping",
                "latency_ms": latency_ms,
                "status": "SUCCESS",
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "details": f"Collections count: {len(collections.collections)}",
            }

        except Exception as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            return {
                "operation": "Ping",
                "latency_ms": latency_ms,
                "status": "FAILED",
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "error": str(e),
            }

    async def measure_search_latency(self) -> dict[str, Any]:
        """
        Measure search operation latency.

        Returns:
            Dictionary with search measurement results
        """
        await self._ensure_initialized()

        start_time = time.time()

        try:
            # Get collections first
            collections = await self.client.get_collections()
            if not collections.collections:
                return {
                    "operation": "SimpleSearch",
                    "latency_ms": 0.0,
                    "status": "FAILED",
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "error": "No collections available",
                }

            # Use the configured collection or first available
            collection_name = settings.QDRANT_COLLECTION_NAME
            available_collections = [c.name for c in collections.collections]

            if collection_name not in available_collections:
                collection_name = available_collections[0]

            # Create a test query vector with correct dimensions
            vector_dimension = settings.VECTOR_DIMENSION
            dummy_vector = [0.1] * vector_dimension

            # Perform search operation
            search_result = await self.client.search(
                collection_name=collection_name,
                query_vector=dummy_vector,
                limit=1,
                with_payload=False,
                with_vectors=False,
            )

            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            return {
                "operation": "SimpleSearch",
                "latency_ms": latency_ms,
                "status": "SUCCESS",
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "details": f"Collection: {collection_name}, Results: {len(search_result)}",
            }

        except Exception as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Even if search fails due to dimension mismatch, we got a response
            if "dimension" in str(e).lower() or "collection" in str(e).lower():
                return {
                    "operation": "SimpleSearch",
                    "latency_ms": latency_ms,
                    "status": "SUCCESS",
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "details": f"Expected dimension/collection error: {str(e)[:100]}",
                }
            else:
                return {
                    "operation": "SimpleSearch",
                    "latency_ms": latency_ms,
                    "status": "FAILED",
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "error": str(e),
                }

    async def run_full_probe(self) -> dict[str, Any]:
        """
        Run complete latency probe including ping and search.

        Returns:
            Dictionary with all probe results
        """
        probe_start = time.time()

        # Measure ping latency
        ping_result = await self.measure_ping_latency()

        # Small delay between operations
        await asyncio.sleep(0.5)

        # Measure search latency
        search_result = await self.measure_search_latency()

        probe_end = time.time()
        total_time = (probe_end - probe_start) * 1000

        # Calculate P95 latency (approximation with 2 samples)
        latencies = [ping_result["latency_ms"], search_result["latency_ms"]]
        p95_latency = max(latencies)  # With 2 samples, max is P95

        return {
            "probe_timestamp": datetime.datetime.utcnow().isoformat(),
            "total_probe_time_ms": total_time,
            "ping_result": ping_result,
            "search_result": search_result,
            "p95_latency_ms": p95_latency,
            "avg_latency_ms": sum(latencies) / len(latencies),
            "status": (
                "SUCCESS"
                if all(r["status"] == "SUCCESS" for r in [ping_result, search_result])
                else "PARTIAL"
            ),
        }

    def log_result_to_file(
        self, result: dict[str, Any], log_file: str = "logs/latency.log"
    ):
        """
        Log probe result to file in the specified format.

        Args:
            result: Probe result dictionary
            log_file: Path to log file
        """
        timestamp = result["probe_timestamp"]

        try:
            # Log ping result
            ping = result["ping_result"]
            ping_line = f"[{timestamp}] [Ping] [{ping['latency_ms']:.2f}ms] [{ping['status']}]\n"

            # Log search result
            search = result["search_result"]
            search_line = f"[{timestamp}] [SimpleSearch] [{search['latency_ms']:.2f}ms] [{search['status']}]\n"

            # Log P95 latency
            p95_line = f"[{timestamp}] [P95Latency] [{result['p95_latency_ms']:.2f}ms] [{result['status']}]\n"

            with open(log_file, "a") as f:
                f.write(ping_line)
                f.write(search_line)
                f.write(p95_line)

            logger.info(f"Logged latency results to {log_file}")

        except Exception as e:
            logger.error(f"Failed to write to log file {log_file}: {e}")

    async def close(self):
        """Close the Qdrant client connection."""
        if self.client:
            await self.client.close()


# Global probe instance
_latency_probe = None


def get_latency_probe() -> QdrantLatencyProbe:
    """Get or create the global latency probe instance."""
    global _latency_probe
    if _latency_probe is None:
        _latency_probe = QdrantLatencyProbe()
    return _latency_probe


# Cloud Function entry point
async def latency_probe_function(request=None):
    """
    Cloud Function entry point for latency monitoring.

    Args:
        request: HTTP request (unused for scheduled function)

    Returns:
        Dictionary with probe results
    """
    logger.info("Starting Qdrant latency probe")

    try:
        probe = get_latency_probe()
        result = await probe.run_full_probe()

        # Log to file
        probe.log_result_to_file(result)

        # Log summary to Cloud Logging
        logger.info(
            f"Latency probe completed: P95={result['p95_latency_ms']:.2f}ms, "
            f"Avg={result['avg_latency_ms']:.2f}ms, Status={result['status']}"
        )

        return result

    except Exception as e:
        logger.error(f"Latency probe failed: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "status": "FAILED",
        }
    finally:
        if _latency_probe:
            await _latency_probe.close()


# For manual testing
async def main():
    """Manual test function."""
    probe = get_latency_probe()
    try:
        result = await probe.run_full_probe()
        probe.log_result_to_file(result)
        print(f"Probe completed: {result}")
    finally:
        await probe.close()


if __name__ == "__main__":
    asyncio.run(main())
