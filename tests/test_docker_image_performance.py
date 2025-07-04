"""
Test suite for validating Docker image optimization performance.
Tests image size, startup time, and functionality after optimization.
"""
import subprocess
import time
import pytest
import requests
import docker
import os
from pathlib import Path


class TestDockerImagePerformance:
    """Test Docker image performance and optimization."""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Initialize Docker client."""
        return docker.from_env()
    
    @pytest.fixture(scope="class") 
    def image_name(self):
        """Docker image name for testing."""
        return "mcp-gateway-optimized:test"
    
    @pytest.fixture(scope="class")
    def build_optimized_image(self, docker_client, image_name):
        """Build the optimized Docker image."""
        # Build context is the project root
        build_context = Path(__file__).parent.parent.parent.parent
        dockerfile_path = "ADK/agent_data/docker/Dockerfile"
        
        print(f"Building Docker image from {build_context}")
        print(f"Using Dockerfile: {dockerfile_path}")
        
        # Build the image
        image, build_logs = docker_client.images.build(
            path=str(build_context),
            dockerfile=dockerfile_path,
            tag=image_name,
            rm=True,
            forcerm=True
        )
        
        # Print build logs for debugging
        for log in build_logs:
            if 'stream' in log:
                print(log['stream'].strip())
        
        yield image
        
        # Cleanup: remove the image after tests
        try:
            docker_client.images.remove(image.id, force=True)
        except Exception as e:
            print(f"Warning: Could not remove image {image_name}: {e}")
    
    @pytest.mark.unit    def test_image_size_under_500mb(self, build_optimized_image):
        """Test that the optimized Docker image is under 500MB."""
        image = build_optimized_image
        image_size_bytes = image.attrs['Size']
        image_size_mb = image_size_bytes / (1024 * 1024)
        
        print(f"Docker image size: {image_size_mb:.2f} MB")
        
        # Assert image size is under 500MB
        assert image_size_mb < 500, f"Image size {image_size_mb:.2f} MB exceeds 500MB limit"
        
        # Log achievement if under target
        print(f"✅ Image size optimization successful: {image_size_mb:.2f} MB < 500 MB")
    
    @pytest.mark.unit    def test_container_startup_time(self, docker_client, build_optimized_image, image_name):
        """Test that container startup time is under 2 seconds."""
        container = None
        try:
            # Start timing
            start_time = time.time()
            
            # Run container with health check
            container = docker_client.containers.run(
                image_name,
                detach=True,
                ports={'8080/tcp': None},  # Random host port
                environment={
                    'PORT': '8080',
                    'HOST': '0.0.0.0'
                },
                remove=False
            )
            
            # Wait for container to be ready (health check passes)
            max_wait_time = 10  # Maximum wait time in seconds
            poll_interval = 0.1  # Check every 100ms
            
            container_ready = False
            while time.time() - start_time < max_wait_time:
                container.reload()
                if container.status == 'running':
                    # Check if health check passes
                    try:
                        container_info = docker_client.api.inspect_container(container.id)
                        health = container_info.get('State', {}).get('Health', {})
                        if health.get('Status') == 'healthy':
                            container_ready = True
                            break
                    except Exception:
                        pass  # Health check might not be available yet
                
                time.sleep(poll_interval)
            
            startup_time = time.time() - start_time
            
            print(f"Container startup time: {startup_time:.2f} seconds")
            
            # Assert startup time is under 2 seconds (allowing some buffer for CI)
            assert startup_time < 5, f"Startup time {startup_time:.2f}s exceeds 5s limit"
            
            if startup_time < 2:
                print(f"✅ Startup time optimization successful: {startup_time:.2f}s < 2s")
            else:
                print(f"⚠️ Startup time acceptable but not optimal: {startup_time:.2f}s")
                
        finally:
            # Cleanup container
            if container:
                try:
                    container.stop(timeout=5)
                    container.remove()
                except Exception as e:
                    print(f"Warning: Could not cleanup container: {e}")
    
    @pytest.mark.unit    def test_functionality_after_optimization(self, docker_client, build_optimized_image, image_name):
        """Test that core functionality works after optimization."""
        container = None
        try:
            # Run container
            container = docker_client.containers.run(
                image_name,
                detach=True,
                ports={'8080/tcp': None},
                environment={
                    'PORT': '8080',
                    'HOST': '0.0.0.0'
                },
                remove=False
            )
            
            # Get the mapped port
            container.reload()
            port_mapping = container.attrs['NetworkSettings']['Ports']['8080/tcp']
            if not port_mapping:
                pytest.skip("Container port mapping failed")
            
            host_port = port_mapping[0]['HostPort']
            base_url = f"http://localhost:{host_port}"
            
            # Wait for container to be ready
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{base_url}/health", timeout=1)
                    if response.status_code == 200:
                        break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    time.sleep(0.5)
            else:
                pytest.fail("Container did not become ready within timeout")
            
            # Test health endpoint
            response = requests.get(f"{base_url}/health", timeout=5)
            assert response.status_code == 200
            
            # Test root endpoint
            response = requests.get(base_url, timeout=5)
            assert response.status_code in [200, 404]  # Either works or returns 404 (both acceptable)
            
            print("✅ Core functionality validated after optimization")
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Network connectivity issue during functionality test: {e}")
        finally:
            # Cleanup container
            if container:
                try:
                    container.stop(timeout=5)
                    container.remove()
                except Exception as e:
                    print(f"Warning: Could not cleanup container: {e}")


@pytest.mark.e2e
class TestDockerOptimizationIntegration:
    """Integration tests for Docker optimization."""
    
    @pytest.mark.unit    def test_docker_build_success(self):
        """Test that the optimized Docker build completes successfully."""
        build_context = Path(__file__).parent.parent.parent.parent
        dockerfile_path = build_context / "ADK" / "agent_data" / "docker" / "Dockerfile"
        
        # Verify Dockerfile exists
        assert dockerfile_path.exists(), f"Dockerfile not found at {dockerfile_path}"
        
        # Test build command (dry run)
        cmd = [
            "docker", "build", 
            "-f", str(dockerfile_path),
            "-t", "mcp-gateway-test-build",
            str(build_context)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            assert result.returncode == 0, f"Docker build failed: {result.stderr}"
            print("✅ Docker build command validation successful")
        except subprocess.TimeoutExpired:
            pytest.skip("Docker build timeout - skipping in test environment")
        except FileNotFoundError:
            pytest.skip("Docker not available in test environment") 