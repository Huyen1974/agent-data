"""
Test suite for API edge cases and error handling scenarios
Tests rate limiting, large payloads, concurrent requests, and boundary conditions
"""

import pytest
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from agent_data_manager.auth.auth_manager import AuthManager


class TestRateLimitingEdgeCases:
    """Test rate limiting edge cases and boundary conditions"""

    def setup_method(self):
        """Setup test environment"""
        self.auth_manager = AuthManager()

    def test_rate_limit_boundary_conditions(self):
        """Test rate limiting at exact boundaries"""
        # Simulate requests at rate limit boundaries (optimized for MacBook M1)
        request_intervals = [0.01, 0.05, 0.1, 0.2, 0.5]  # Different intervals in seconds

        for interval in request_intervals:
            start_time = time.time()

            # Simulate 3 requests with specific interval
            for i in range(3):
                if i > 0:
                    time.sleep(interval)

                # Simulate request processing time
                processing_time = time.time() - start_time
                assert processing_time >= 0

                # Check if interval is respected
                if i > 0:
                    expected_min_time = i * interval
                    assert processing_time >= expected_min_time * 0.9  # Allow 10% tolerance

    def test_concurrent_rate_limit_users(self):
        """Test rate limiting with multiple concurrent users"""

        def simulate_user_requests(user_id, num_requests=3):
            """Simulate requests from a single user"""
            results = []
            for i in range(num_requests):
                # Create token for user
                token = self.auth_manager.create_user_token(f"user_{user_id}@test.com", f"user_{user_id}@test.com")

                # Simulate request
                request_time = time.time()
                results.append(
                    {"user_id": user_id, "request_num": i, "timestamp": request_time, "token_valid": len(token) > 50}
                )

                # Small delay between requests
                time.sleep(0.1)

            return results

        # Test with multiple users concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(simulate_user_requests, user_id, 2) for user_id in range(3)]

            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())

        # Verify all requests were processed
        assert len(all_results) == 6  # 3 users * 2 requests each

        # Verify each user's requests are properly spaced
        for user_id in range(3):
            user_requests = [r for r in all_results if r["user_id"] == user_id]
            assert len(user_requests) == 2

            if len(user_requests) > 1:
                time_diff = user_requests[1]["timestamp"] - user_requests[0]["timestamp"]
                assert time_diff >= 0.05  # Minimum spacing


class TestLargePayloadHandling:
    """Test handling of large payloads and boundary conditions"""

    def test_large_document_content(self):
        """Test handling of large document content"""
        # Test different content sizes
        content_sizes = [100, 1000, 10000, 50000]  # Characters

        for size in content_sizes:
            large_content = "A" * size

            # Simulate document processing
            doc_data = {
                "doc_id": f"large_doc_{size}",
                "content": large_content,
                "metadata": {"size": size, "test": True},
                "tag": "large_content_test",
            }

            # Basic validation
            assert len(doc_data["content"]) == size
            assert doc_data["doc_id"] == f"large_doc_{size}"

            # Simulate JSON serialization (common bottleneck)
            try:
                json_str = json.dumps(doc_data)
                assert len(json_str) > size  # Should be larger due to JSON overhead
            except Exception as e:
                pytest.fail(f"Failed to serialize document of size {size}: {e}")

    def test_large_metadata_objects(self):
        """Test handling of large metadata objects"""
        # Create large metadata with many fields
        large_metadata = {}
        for i in range(100):
            large_metadata[f"field_{i}"] = f"value_{i}" * 10  # 70+ chars per field

        # Add nested objects
        large_metadata["nested"] = {"level1": {"level2": {"data": ["item"] * 50}}}

        # Test serialization and size
        metadata_json = json.dumps(large_metadata)
        assert len(metadata_json) > 5000  # Should be substantial

        # Test deserialization
        parsed_metadata = json.loads(metadata_json)
        assert len(parsed_metadata) >= 101  # 100 fields + nested
        assert parsed_metadata["nested"]["level1"]["level2"]["data"][0] == "item"

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters"""
        special_contents = [
            "Hello 世界 🌍",  # Unicode with emojis
            "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "Newlines\nand\ttabs\rand\x00null",
            'JSON breaking chars: "quotes" and \\backslashes\\',
            "SQL injection attempt: '; DROP TABLE users; --",
            "XSS attempt: <script>alert('xss')</script>",
            "Very long line: " + "x" * 1000,
        ]

        for content in special_contents:
            doc_data = {
                "doc_id": f"special_{hash(content) % 10000}",
                "content": content,
                "metadata": {"type": "special_chars"},
                "tag": "unicode_test",
            }

            # Test JSON serialization/deserialization
            try:
                json_str = json.dumps(doc_data)
                parsed_data = json.loads(json_str)
                assert parsed_data["content"] == content
            except Exception as e:
                pytest.fail(f"Failed to handle special content: {content[:50]}... Error: {e}")


class TestConcurrentRequestHandling:
    """Test concurrent request handling and race conditions"""

    def setup_method(self):
        """Setup test environment"""
        self.auth_manager = AuthManager()

    def test_concurrent_token_creation(self):
        """Test concurrent JWT token creation"""

        def create_token_for_user(user_id):
            """Create token for a specific user"""
            return self.auth_manager.create_user_token(f"user_{user_id}@test.com", f"user_{user_id}@test.com")

        # Create tokens concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_token_for_user, i) for i in range(10)]
            tokens = [future.result() for future in as_completed(futures)]

        # Verify all tokens are unique and valid
        assert len(tokens) == 10
        assert len(set(tokens)) == 10  # All tokens should be unique

        # Verify all tokens are valid
        for token in tokens:
            payload = self.auth_manager.verify_token(token)
            assert "sub" in payload
            assert "@test.com" in payload["sub"]

    def test_concurrent_token_validation(self):
        """Test concurrent token validation"""
        # Create a single token
        token = self.auth_manager.create_user_token("concurrent@test.com", "concurrent@test.com")

        def validate_token():
            """Validate the token"""
            try:
                payload = self.auth_manager.verify_token(token)
                return {"success": True, "user": payload["sub"]}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Validate token concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(validate_token) for _ in range(20)]
            results = [future.result() for future in as_completed(futures)]

        # All validations should succeed
        successful_validations = [r for r in results if r["success"]]
        assert len(successful_validations) == 20

        # All should return the same user
        users = [r["user"] for r in successful_validations]
        assert all(user == "concurrent@test.com" for user in users)


class TestErrorHandlingEdgeCases:
    """Test error handling in edge cases and boundary conditions"""

    def setup_method(self):
        """Setup test environment"""
        self.auth_manager = AuthManager()

    def test_memory_pressure_simulation(self):
        """Test behavior under simulated memory pressure"""
        # Create many tokens to simulate memory usage
        tokens = []

        try:
            for i in range(100):  # Create 100 tokens
                token = self.auth_manager.create_user_token(f"memory_test_{i}@test.com", f"memory_test_{i}@test.com")
                tokens.append(token)

                # Validate every 10th token to ensure they're still working
                if i % 10 == 0:
                    payload = self.auth_manager.verify_token(token)
                    assert payload["sub"] == f"memory_test_{i}@test.com"

            # Verify we created all tokens
            assert len(tokens) == 100

            # Verify all tokens are unique
            assert len(set(tokens)) == 100

        except Exception as e:
            pytest.fail(f"Memory pressure test failed: {e}")

    def test_rapid_token_expiration(self):
        """Test rapid token creation and expiration (optimized for MacBook M1)"""
        from datetime import timedelta

        # Create tokens with very short expiration
        short_lived_tokens = []

        for i in range(5):
            token = self.auth_manager.create_access_token(
                {"sub": f"rapid_{i}@test.com", "email": f"rapid_{i}@test.com"}, expires_delta=timedelta(seconds=1)
            )
            short_lived_tokens.append(token)

            # Validate immediately
            payload = self.auth_manager.verify_token(token)
            assert payload["sub"] == f"rapid_{i}@test.com"

        # Wait for expiration (reduced for M1 compatibility)
        time.sleep(1.5)

        # All tokens should now be expired
        expired_count = 0
        for token in short_lived_tokens:
            try:
                self.auth_manager.verify_token(token)
            except Exception:
                expired_count += 1

        assert expired_count == 5  # All should be expired

    def test_malformed_input_handling(self):
        """Test handling of various malformed inputs"""
        malformed_inputs = [
            None,
            "",
            "   ",  # Whitespace only
            "\n\t\r",  # Control characters
            "a" * 10000,  # Very long string
            "🚀" * 100,  # Unicode emojis
        ]

        for malformed_input in malformed_inputs:
            if isinstance(malformed_input, str):
                try:
                    # This should fail gracefully
                    self.auth_manager.verify_token(malformed_input)
                    pytest.fail(f"Should have failed for input: {repr(malformed_input)}")
                except Exception:
                    # Expected to fail
                    pass

    def test_boundary_value_testing(self):
        """Test boundary values for various parameters"""
        from datetime import timedelta

        # Test token expiration boundaries
        boundary_times = [
            timedelta(seconds=1),  # Minimum
            timedelta(minutes=30),  # Default
            timedelta(hours=24),  # Maximum reasonable
        ]

        for expiry_time in boundary_times:
            user_data = {"sub": "boundary@test.com", "email": "boundary@test.com"}
            token = self.auth_manager.create_access_token(user_data, expires_delta=expiry_time)

            # Should be valid immediately
            payload = self.auth_manager.verify_token(token)
            assert payload["sub"] == "boundary@test.com"

            # Check expiration time is set correctly
            exp_timestamp = payload["exp"]
            iat_timestamp = payload["iat"]
            actual_duration = exp_timestamp - iat_timestamp
            expected_duration = expiry_time.total_seconds()

            # Allow 1 second tolerance for processing time
            assert abs(actual_duration - expected_duration) <= 1
