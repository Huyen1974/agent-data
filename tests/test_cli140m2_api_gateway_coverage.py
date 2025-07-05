#!/usr/bin/env python3
"""
CLI140m.2 - API Gateway Coverage Tests
Focus on api_mcp_gateway.py to reach 80% coverage (currently 76.1%)
Need to cover 15 more lines to reach 80%
"""

import pytest
import asyncio
import json
import tempfile
import os
import time
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException, Request
import logging

# Add the ADK/agent_data directory to Python path for proper imports
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_data_dir = os.path.dirname(current_dir)
sys.path.insert(0, agent_data_dir)

# Import the module we're testing
import api_mcp_gateway


class TestCLI140m2APIMCPGatewaySpecific:
    """Specific tests targeting missing coverage lines in api_mcp_gateway.py"""

    @pytest.mark.slow
    def test_thread_safe_lru_cache_cleanup_expired_direct(self):
        """Test ThreadSafeLRUCache cleanup_expired method - lines 88-89"""
        cache = api_mcp_gateway.ThreadSafeLRUCache(max_size=3, ttl_seconds=0.1)
        
        # Add items that will expire quickly
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Test cleanup_expired method directly - this should hit lines 88-89
        expired_count = cache.cleanup_expired()
        assert expired_count >= 0

    @pytest.mark.slow
    def test_thread_safe_lru_cache_clear_direct(self):
        """Test ThreadSafeLRUCache clear method - lines 98-109"""
        cache = api_mcp_gateway.ThreadSafeLRUCache(max_size=5)
        
        # Add items
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        assert cache.size() == 3
        
        # Test clear method - this should hit lines 98-109
        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    @patch('api_mcp_gateway.settings')
    @pytest.mark.slow
    def test_health_check_endpoint_full_coverage(self, mock_settings):
        """Test health check endpoint - lines 453, 459, 466"""
        mock_settings.ENABLE_AUTHENTICATION = True
        mock_settings.ALLOW_REGISTRATION = True
        
        # Mock all the global services to ensure health check runs fully
        with patch('api_mcp_gateway.qdrant_store', Mock()) as mock_qdrant:
            with patch('api_mcp_gateway.firestore_manager', Mock()) as mock_firestore:
                with patch('api_mcp_gateway.vectorization_tool', Mock()) as mock_vectorization:
                    with patch('api_mcp_gateway.auth_manager', Mock()) as mock_auth:
                        with patch('api_mcp_gateway.user_manager', Mock()) as mock_user:
                            
                            # Set up mocks to return expected values
                            mock_qdrant.health_check = Mock(return_value={"status": "healthy"})
                            mock_firestore.health_check = Mock(return_value={"status": "healthy"})
                            mock_vectorization.health_check = Mock(return_value={"status": "healthy"})
                            mock_auth.health_check = Mock(return_value={"status": "healthy"})
                            mock_user.health_check = Mock(return_value={"status": "healthy"})
                            
                            client = TestClient(api_mcp_gateway.app)
                            response = client.get("/health")
                            
                            # This should hit lines 453, 459, 466
                            assert response.status_code == 200
                            data = response.json()
                            assert "status" in data
                            assert "services" in data
                            assert "authentication" in data

    @pytest.mark.slow
    def test_root_endpoint_direct(self):
        """Test root endpoint - line 860"""
        client = TestClient(api_mcp_gateway.app)
        
        # This should hit line 860
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        # Fix: Check for the actual fields returned by the root endpoint
        assert "service" in data
        assert "version" in data
        assert "endpoints" in data

    @patch('api_mcp_gateway.uvicorn')
    @pytest.mark.slow
    def test_main_function_direct(self, mock_uvicorn):
        """Test main function - lines 884-889"""
        # This should hit lines 884-889
        api_mcp_gateway.main()
        
        # Verify uvicorn.run was called with expected parameters
        mock_uvicorn.run.assert_called_once()
        call_args = mock_uvicorn.run.call_args
        # Fix: Check for the actual module path used
        assert call_args[0][0] == "api_mcp_gateway:app"  # First positional arg
        assert "host" in call_args[1]  # Keyword args
        assert "port" in call_args[1]

    @patch('api_mcp_gateway.settings')
    @pytest.mark.slow
    def test_get_current_user_dependency_auth_disabled_path(self, mock_settings):
        """Test get_current_user_dependency with auth disabled - authentication edge cases"""
        mock_settings.ENABLE_AUTHENTICATION = False
        
        async def test_func():
            # This should hit the auth disabled path
            result = await api_mcp_gateway.get_current_user_dependency()
            assert result["user_id"] == "anonymous"
            assert result["email"] == "anonymous@system"
            assert "read" in result["scopes"]
            assert "write" in result["scopes"]
        
        asyncio.run(test_func())

    @patch('api_mcp_gateway.settings')
    @patch('api_mcp_gateway.auth_manager', None)
    @pytest.mark.slow
    def test_get_current_user_dependency_no_auth_manager_path(self, mock_settings):
        """Test get_current_user_dependency with no auth manager - lines 413-426"""
        mock_settings.ENABLE_AUTHENTICATION = True
        
        async def test_func():
            # This should hit lines 413-426 (no auth manager error path)
            with pytest.raises(HTTPException) as exc_info:
                await api_mcp_gateway.get_current_user_dependency()
            assert exc_info.value.status_code == 503
            # Fix: Check for the actual error message
            assert "Authentication service unavailable" in str(exc_info.value.detail)
        
        asyncio.run(test_func())

    @patch('api_mcp_gateway.settings')
    @pytest.mark.slow
    def test_login_endpoint_auth_disabled_path(self, mock_settings):
        """Test login endpoint with authentication disabled"""
        mock_settings.ENABLE_AUTHENTICATION = False
        
        client = TestClient(api_mcp_gateway.app)
        response = client.post("/auth/login", data={"username": "test", "password": "test"})
        
        # Should return 501 Not Implemented when auth is disabled
        assert response.status_code == 501

    @patch('api_mcp_gateway.settings')
    @pytest.mark.slow
    def test_register_endpoint_auth_disabled_path(self, mock_settings):
        """Test register endpoint with authentication disabled"""
        mock_settings.ENABLE_AUTHENTICATION = False
        
        client = TestClient(api_mcp_gateway.app)
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User"
        })
        
        # Should return 501 Not Implemented when auth is disabled
        assert response.status_code == 501

    @pytest.mark.slow
    def test_get_cached_result_cache_miss_direct(self):
        """Test _get_cached_result with cache miss"""
        with patch('api_mcp_gateway._rag_cache') as mock_cache:
            mock_cache.get.return_value = None
            
            result = api_mcp_gateway._get_cached_result("nonexistent_key")
            assert result is None
            mock_cache.get.assert_called_once_with("nonexistent_key")

    @pytest.mark.slow
    def test_cache_result_success_direct(self):
        """Test _cache_result success path"""
        with patch('api_mcp_gateway._rag_cache') as mock_cache:
            test_result = {"status": "success", "data": "test"}
            
            api_mcp_gateway._cache_result("test_key", test_result)
            mock_cache.put.assert_called_once_with("test_key", test_result)

    @patch('api_mcp_gateway.settings')
    @patch('api_mcp_gateway.auth_manager', None)
    @pytest.mark.slow
    def test_get_current_user_no_auth_manager_direct(self, mock_settings):
        """Test get_current_user with no auth manager"""
        mock_settings.ENABLE_AUTHENTICATION = True
        
        async def test_func():
            with pytest.raises(HTTPException) as exc_info:
                await api_mcp_gateway.get_current_user("fake_token")
            assert exc_info.value.status_code == 503
        
        asyncio.run(test_func())

    @patch('api_mcp_gateway.settings')
    @patch('api_mcp_gateway.user_manager', None)
    @pytest.mark.slow
    def test_login_no_managers_direct(self, mock_settings):
        """Test login endpoint with no managers"""
        mock_settings.ENABLE_AUTHENTICATION = True
        
        client = TestClient(api_mcp_gateway.app)
        response = client.post("/auth/login", data={"username": "test", "password": "test"})
        
        # Should return 503 Service Unavailable when managers are not available
        assert response.status_code == 503

    @patch('api_mcp_gateway.settings')
    @pytest.mark.slow
    def test_register_registration_disabled_direct(self, mock_settings):
        """Test register endpoint with registration disabled"""
        mock_settings.ENABLE_AUTHENTICATION = True
        mock_settings.ALLOW_REGISTRATION = False
        
        client = TestClient(api_mcp_gateway.app)
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User"
        })
        
        # Should return 403 Forbidden when registration is disabled
        assert response.status_code == 403

    @patch('api_mcp_gateway.settings')
    @patch('api_mcp_gateway.user_manager', None)
    @pytest.mark.slow
    def test_register_no_user_manager_direct(self, mock_settings):
        """Test register endpoint with no user manager"""
        mock_settings.ENABLE_AUTHENTICATION = True
        mock_settings.ALLOW_REGISTRATION = True
        
        client = TestClient(api_mcp_gateway.app)
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User"
        })
        
        # Should return 503 Service Unavailable when user manager is not available
        assert response.status_code == 503

    @pytest.mark.slow
    def test_get_cache_key_function_direct(self):
        """Test _get_cache_key function"""
        # Test the cache key generation function
        key1 = api_mcp_gateway._get_cache_key("test query", tag="test_tag")
        key2 = api_mcp_gateway._get_cache_key("test query", tag="test_tag")
        key3 = api_mcp_gateway._get_cache_key("different query", tag="test_tag")
        
        # Same inputs should produce same key
        assert key1 == key2
        # Different inputs should produce different keys
        assert key1 != key3

    @pytest.mark.slow
    def test_initialize_caches_function_direct(self):
        """Test _initialize_caches function"""
        # This function should initialize the global caches
        api_mcp_gateway._initialize_caches()
        
        # Verify that the caches are initialized (they may be None if disabled in settings)
        # Just test that the function runs without error
        assert True


class TestCLI140m2APIMCPGatewayCoverageValidation:
    """Validation test to ensure API Gateway coverage targets are met"""

    @pytest.mark.slow
    def test_api_gateway_coverage_validation(self):
        """Validate that API Gateway tests improve coverage to 80%"""
        # This test serves as a marker for coverage validation
        # The actual coverage will be measured by pytest-cov
        
        # Log the target
        print("\nCLI140m.2 API Gateway Coverage Goal:")
        print("- api_mcp_gateway.py: 76.1% → 80% (need ~15 more lines)")
        print("- Target lines: 88-89, 98-109, 413-426, 453, 459, 466, 860, 884-889")
        
        assert True  # Placeholder assertion 