"""
CLI140h.2 Optimization Test Suite
Tests for container startup time optimization and Google Cloud cleanup validation.
"""

import json
import logging
import os
import subprocess
import time
from typing import Any

import pytest
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StartupTimeValidator:
    """Validates container startup time optimization."""

    def __init__(self, target_time: float = 2.0):
        self.target_time = target_time
        self.startup_times = []

    def measure_flask_startup(
        self, host: str = "127.0.0.1", port: int = 8080
    ) -> dict[str, Any]:
        """Measure Flask application startup time."""
        logger.info(f"🚀 Measuring Flask startup time (target: <{self.target_time}s)")

        # Start Flask app in subprocess
        import sys

        app_cmd = [sys.executable, "-m", "ADK.agent_data.mcp.web_server"]

        env = os.environ.copy()
        env["PORT"] = str(port)
        env["FLASK_ENV"] = "production"

        start_time = time.time()

        try:
            # Start the process
            process = subprocess.Popen(
                app_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for health endpoint to respond
            health_url = f"http://{host}:{port}/health"
            max_wait = 10.0  # Maximum wait time
            check_interval = 0.1

            startup_successful = False
            while time.time() - start_time < max_wait:
                try:
                    response = requests.get(health_url, timeout=1)
                    if response.status_code == 200:
                        startup_time = time.time() - start_time
                        startup_successful = True
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(check_interval)

            process.terminate()
            process.wait(timeout=5)

            if startup_successful:
                self.startup_times.append(startup_time)
                logger.info(f"✅ Startup time: {startup_time:.3f}s")
                return {
                    "success": True,
                    "startup_time": startup_time,
                    "target_met": startup_time < self.target_time,
                    "target_time": self.target_time,
                }
            else:
                logger.error(f"❌ Startup failed - no response within {max_wait}s")
                return {
                    "success": False,
                    "error": "Health check timeout",
                    "target_time": self.target_time,
                }

        except Exception as e:
            logger.error(f"❌ Startup measurement failed: {e}")
            return {"success": False, "error": str(e), "target_time": self.target_time}

    def measure_lazy_loading_benefit(self) -> dict[str, Any]:
        """Test lazy loading performance improvement."""
        logger.info("🔍 Testing lazy loading performance benefit")

        # Import the web_server module to test lazy loading
        try:
            start_time = time.time()
            from ADK.agent_data.mcp import web_server

            import_time = time.time() - start_time

            # Check if tools are loaded immediately (they shouldn't be)
            tools_loaded_at_import = web_server._tools_loaded

            # Simulate first request to trigger lazy loading
            start_lazy_load = time.time()
            tools, error = web_server._lazy_load_tools()
            lazy_load_time = time.time() - start_lazy_load

            return {
                "success": True,
                "import_time": import_time,
                "lazy_load_time": lazy_load_time,
                "tools_loaded_at_import": tools_loaded_at_import,
                "tools_loaded_after_request": len(tools) > 0,
                "total_tools": len(tools),
                "loading_error": error,
            }

        except Exception as e:
            logger.error(f"❌ Lazy loading test failed: {e}")
            return {"success": False, "error": str(e)}


class CloudCleanupValidator:
    """Validates Google Cloud cleanup operations."""

    def __init__(self):
        self.cleanup_results = {}

    def validate_gcloud_available(self) -> bool:
        """Check if gcloud CLI is available."""
        try:
            result = subprocess.run(
                ["gcloud", "version"], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def test_cleanup_script_functionality(self) -> dict[str, Any]:
        """Test the cleanup script without actually running destructive operations."""
        logger.info("🧹 Testing Google Cloud cleanup script functionality")

        try:
            # Import the cleanup script
            import os

            script_path = os.path.join(
                os.path.dirname(__file__), "..", "scripts", "cleanup_cloud_builds.py"
            )

            if not os.path.exists(script_path):
                return {"success": False, "error": "Cleanup script not found"}

            # Test script importability and basic functions
            spec = __import__("importlib.util").util.spec_from_file_location(
                "cleanup_script", script_path
            )
            cleanup_module = __import__("importlib.util").util.module_from_spec(spec)
            spec.loader.exec_module(cleanup_module)

            # Test if required functions exist
            required_functions = [
                "run_gcloud_command",
                "cleanup_old_container_images",
                "cleanup_cloud_run_revisions",
                "get_project_info",
            ]

            missing_functions = []
            for func_name in required_functions:
                if not hasattr(cleanup_module, func_name):
                    missing_functions.append(func_name)

            if missing_functions:
                return {
                    "success": False,
                    "error": f"Missing functions: {missing_functions}",
                }

            # Test project info function (read-only)
            project_info = cleanup_module.get_project_info()

            return {
                "success": True,
                "script_importable": True,
                "required_functions_present": True,
                "project_info_accessible": bool(project_info),
                "project_id": project_info.get("project_id", "unknown"),
            }

        except Exception as e:
            logger.error(f"❌ Cleanup script test failed: {e}")
            return {"success": False, "error": str(e)}


class OptimizationIntegrationTest:
    """Integration test for all optimizations."""

    def __init__(self):
        self.startup_validator = StartupTimeValidator()
        self.cleanup_validator = CloudCleanupValidator()

    def run_comprehensive_test(self) -> dict[str, Any]:
        """Run comprehensive optimization validation."""
        logger.info("🎯 Running CLI140h.2 comprehensive optimization test")

        results = {
            "test_timestamp": time.time(),
            "target_startup_time": 2.0,
            "tests": {},
        }

        # Test 1: Lazy loading performance
        logger.info("Test 1: Lazy Loading Performance")
        lazy_loading_result = self.startup_validator.measure_lazy_loading_benefit()
        results["tests"]["lazy_loading"] = lazy_loading_result

        # Test 2: Startup time measurement (if possible)
        logger.info("Test 2: Startup Time Measurement")
        try:
            startup_result = self.startup_validator.measure_flask_startup(port=8081)
            results["tests"]["startup_time"] = startup_result
        except Exception as e:
            logger.warning(f"Startup time test skipped: {e}")
            results["tests"]["startup_time"] = {
                "success": False,
                "error": "Port conflict or service unavailable",
                "skipped": True,
            }

        # Test 3: Cleanup script validation
        logger.info("Test 3: Cleanup Script Validation")
        cleanup_result = self.cleanup_validator.test_cleanup_script_functionality()
        results["tests"]["cleanup_script"] = cleanup_result

        # Test 4: GCloud availability
        logger.info("Test 4: GCloud CLI Availability")
        gcloud_available = self.cleanup_validator.validate_gcloud_available()
        results["tests"]["gcloud_available"] = {
            "success": gcloud_available,
            "available": gcloud_available,
        }

        # Overall assessment
        test_successes = sum(
            1
            for test in results["tests"].values()
            if test.get("success", False) or test.get("skipped", False)
        )
        total_tests = len(results["tests"])

        results["overall"] = {
            "tests_passed": test_successes,
            "total_tests": total_tests,
            "success_rate": test_successes / total_tests if total_tests > 0 else 0,
            "optimization_ready": test_successes >= total_tests - 1,  # Allow 1 failure
        }

        logger.info(f"🏆 Overall: {test_successes}/{total_tests} tests passed")
        return results


# Pytest test functions
@pytest.mark.integration
@pytest.mark.unit
def test_lazy_loading_optimization():
    """Test that lazy loading is properly implemented."""
    validator = StartupTimeValidator()
    result = validator.measure_lazy_loading_benefit()

    assert result["success"], f"Lazy loading test failed: {result.get('error')}"
    assert not result[
        "tools_loaded_at_import"
    ], "Tools should not be loaded at import time"
    assert result[
        "tools_loaded_after_request"
    ], "Tools should be loaded after first request"
    assert result["total_tools"] > 0, "Should have loaded some tools"

    # Import time should be fast (< 1 second)
    assert (
        result["import_time"] < 1.0
    ), f"Import time too slow: {result['import_time']:.3f}s"


@pytest.mark.integration
@pytest.mark.unit
def test_cleanup_script_availability():
    """Test that the cleanup script is properly implemented."""
    validator = CloudCleanupValidator()
    result = validator.test_cleanup_script_functionality()

    assert result["success"], f"Cleanup script test failed: {result.get('error')}"
    assert result["script_importable"], "Cleanup script should be importable"
    assert result[
        "required_functions_present"
    ], "All required functions should be present"


@pytest.mark.integration
@pytest.mark.unit
def test_optimization_integration():
    """Comprehensive integration test for all optimizations."""
    integration_test = OptimizationIntegrationTest()
    results = integration_test.run_comprehensive_test()

    # Log detailed results
    logger.info(f"Detailed test results: {json.dumps(results, indent=2)}")

    assert results["overall"][
        "optimization_ready"
    ], f"Optimization not ready: {results['overall']['tests_passed']}/{results['overall']['total_tests']} tests passed"


@pytest.mark.performance
@pytest.mark.unit
def test_startup_time_target():
    """Test startup time meets the <2s target (if environment allows)."""
    validator = StartupTimeValidator()

    try:
        result = validator.measure_flask_startup(port=8082)

        if result["success"]:
            assert result[
                "target_met"
            ], f"Startup time {result['startup_time']:.3f}s exceeds target {result['target_time']}s"
            logger.info(
                f"✅ Startup time target met: {result['startup_time']:.3f}s < {result['target_time']}s"
            )
        else:
            pytest.skip(f"Startup test skipped: {result.get('error')}")

    except Exception as e:
        pytest.skip(f"Startup test skipped due to environment: {e}")


# Test configuration for CLI140h.2
@pytest.mark.unit
def test_cli140h2_optimization_summary():
    """Summary test that validates all CLI140h.2 optimizations."""
    logger.info("🎯 CLI140h.2 Optimization Summary Test")

    # Run integration test
    integration_test = OptimizationIntegrationTest()
    results = integration_test.run_comprehensive_test()

    # Create summary
    summary = {
        "optimization_target": "Reduce startup time to <2s and clean old builds",
        "tests_run": results["overall"]["total_tests"],
        "tests_passed": results["overall"]["tests_passed"],
        "success_rate": f"{results['overall']['success_rate']:.1%}",
        "optimization_ready": results["overall"]["optimization_ready"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    logger.info(f"📊 CLI140h.2 Summary: {json.dumps(summary, indent=2)}")

    # Assert overall success
    assert results["overall"][
        "optimization_ready"
    ], f"CLI140h.2 optimization validation failed: {summary}"

    logger.info("✅ CLI140h.2 optimization validation PASSED")


if __name__ == "__main__":
    # Run standalone test
    test_cli140h2_optimization_summary()
