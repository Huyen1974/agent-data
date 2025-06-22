#!/usr/bin/env python3
"""
Profiling script for CSKH API and RAG search performance optimization.
CLI 140e: Measures latency and identifies bottlenecks.
"""

import asyncio
import cProfile
import pstats
import time
import logging
from typing import Dict, Any, List
import sys
import os

from agent_data_manager.tools.qdrant_vectorization_tool import qdrant_rag_search
from agent_data_manager.api_mcp_gateway import _get_cache_key, _get_cached_result, _cache_result

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CSKHProfiler:
    """Profiler for CSKH API and RAG search performance."""

    def __init__(self):
        self.results = {}

    async def profile_rag_search(self, query_text: str, limit: int = 10) -> Dict[str, Any]:
        """Profile RAG search performance."""
        logger.info(f"Profiling RAG search for query: '{query_text[:50]}...'")

        start_time = time.time()

        try:
            # Profile the RAG search
            result = await qdrant_rag_search(
                query_text=query_text, metadata_filters={}, tags=[], path_query=None, limit=limit, score_threshold=0.6
            )

            end_time = time.time()
            latency = end_time - start_time

            profile_result = {
                "query": query_text,
                "latency_ms": latency * 1000,
                "status": result.get("status", "unknown"),
                "result_count": result.get("count", 0),
                "rag_info": result.get("rag_info", {}),
                "success": result.get("status") == "success",
            }

            logger.info(f"RAG search completed in {latency*1000:.2f}ms, {result.get('count', 0)} results")
            return profile_result

        except Exception as e:
            end_time = time.time()
            latency = end_time - start_time

            logger.error(f"RAG search failed after {latency*1000:.2f}ms: {e}")
            return {
                "query": query_text,
                "latency_ms": latency * 1000,
                "status": "error",
                "error": str(e),
                "success": False,
            }

    def profile_cache_operations(self, queries: List[str]) -> Dict[str, Any]:
        """Profile cache operations performance."""
        logger.info("Profiling cache operations")

        cache_results = {"cache_hits": 0, "cache_misses": 0, "cache_operations": []}

        for query in queries:
            start_time = time.time()

            # Test cache key generation
            cache_key = _get_cache_key(query, {}, [], "")

            # Test cache retrieval
            cached_result = _get_cached_result(cache_key)

            # Test cache storage
            if not cached_result:
                test_data = {"results": [], "total_found": 0, "rag_info": {}}
                _cache_result(cache_key, test_data)
                cache_results["cache_misses"] += 1
            else:
                cache_results["cache_hits"] += 1

            end_time = time.time()

            cache_results["cache_operations"].append(
                {
                    "query": query,
                    "cache_key": cache_key,
                    "hit": cached_result is not None,
                    "latency_ms": (end_time - start_time) * 1000,
                }
            )

        return cache_results

    async def run_performance_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive performance benchmark."""
        logger.info("Starting CSKH API performance benchmark")

        # Test queries for different scenarios
        test_queries = [
            "Customer service best practices",
            "How to handle billing disputes",
            "Technical support troubleshooting",
            "Account management procedures",
            "Product return policy",
            "Service level agreements",
            "Customer satisfaction metrics",
            "Support ticket escalation",
        ]

        benchmark_results = {"timestamp": time.time(), "rag_search_results": [], "cache_results": {}, "summary": {}}

        # Profile RAG searches
        for query in test_queries[:5]:  # Limit to 5 queries to avoid rate limits
            result = await self.profile_rag_search(query, limit=10)
            benchmark_results["rag_search_results"].append(result)

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        # Profile cache operations
        benchmark_results["cache_results"] = self.profile_cache_operations(test_queries)

        # Calculate summary statistics
        successful_searches = [r for r in benchmark_results["rag_search_results"] if r["success"]]
        if successful_searches:
            latencies = [r["latency_ms"] for r in successful_searches]
            benchmark_results["summary"] = {
                "total_queries": len(benchmark_results["rag_search_results"]),
                "successful_queries": len(successful_searches),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "target_met_500ms": all(latency < 500 for latency in latencies),
                "target_met_700ms": all(latency < 700 for latency in latencies),
            }

        return benchmark_results


def run_cprofile_analysis():
    """Run cProfile analysis on RAG search."""
    logger.info("Running cProfile analysis")

    async def profile_target():
        profiler = CSKHProfiler()
        return await profiler.profile_rag_search("Customer service performance test", limit=8)

    # Run with cProfile
    pr = cProfile.Profile()
    pr.enable()

    result = asyncio.run(profile_target())

    pr.disable()

    # Save profile results
    pr.dump_stats("profile.out")

    # Print top functions by cumulative time
    stats = pstats.Stats(pr)
    stats.sort_stats("cumulative")

    print("\n=== Top 20 functions by cumulative time ===")
    stats.print_stats(20)

    print(f"\nProfile result: {result}")
    print("Profile saved to profile.out")


async def main():
    """Main profiling function."""
    logger.info("Starting CSKH API profiling - CLI 140e")

    try:
        # Run performance benchmark
        profiler = CSKHProfiler()
        results = await profiler.run_performance_benchmark()

        # Log results
        logger.info("=== Performance Benchmark Results ===")
        logger.info(f"Summary: {results['summary']}")

        # Save results to file
        import json

        with open("logs/latency_probe.log", "w") as f:
            json.dump(results, f, indent=2)

        logger.info("Results saved to logs/latency_probe.log")

        # Run cProfile analysis
        run_cprofile_analysis()

    except Exception as e:
        logger.error(f"Profiling failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
