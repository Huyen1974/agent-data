"""
Performance Test for Cloud API A2A Gateway
Tests performance with 50 queries/documents across all endpoints
"""

import pytest
import asyncio
import os
import requests
import time
from typing import Dict, List, Any
from datetime import datetime
import statistics

# Test configuration
CLOUD_RUN_URL = "https://api-a2a-gateway-1042559846495.asia-southeast1.run.app"
TEST_USER_EMAIL = "test@cursor.integration"
TEST_USER_PASSWORD = "test123"
TEST_TIMEOUT = 30  # seconds
PERFORMANCE_TEST_COUNT = 50  # Test with 50 operations


@pytest.mark.deferred
class TestCloudPerformance:
    """Performance tests for Cloud API A2A Gateway"""

    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        cls.base_url = CLOUD_RUN_URL
        cls.access_token = None
        cls.test_session = requests.Session()
        cls.test_session.timeout = TEST_TIMEOUT
        cls.response_times = []
        cls.successful_operations = 0
        cls.rate_limited_operations = 0
        cls.failed_operations = 0

    @pytest.mark.deferred
    def test_01_authenticate_for_performance(self):
        """Authenticate user for performance testing"""
        try:
            login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}

            response = self.test_session.post(
                f"{self.base_url}/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 401:
                pytest.skip("Test user not found - performance test skipped")

            assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"

            data = response.json()
            self.__class__.access_token = data["access_token"]

            print(f"✅ Authentication successful for performance testing")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Authentication service not accessible: {e}")

    @pytest.mark.deferred
    def test_02_performance_save_documents(self):
        """Test saving 20 documents with performance monitoring"""
        if not self.access_token:
            pytest.skip("Authentication token not available")

        headers = {"Authorization": f"Bearer {self.access_token}"}
        save_times = []
        successful_saves = 0
        rate_limited_saves = 0

        print(f"🚀 Starting performance test: saving 20 documents...")

        for i in range(20):
            doc_data = {
                "doc_id": f"perf_test_doc_{i:03d}",
                "content": f"Performance test document {i} with substantial content for realistic testing. This document contains enough text to generate meaningful embeddings and test the full pipeline including OpenAI API calls, Qdrant vector storage, and Firestore metadata synchronization. Document number {i} created at {datetime.utcnow().isoformat()}.",
                "metadata": {
                    "source": "performance_test",
                    "test_type": "save_performance",
                    "doc_number": i,
                    "timestamp": datetime.utcnow().isoformat(),
                    "project": "agent_data_performance",
                },
                "tag": "performance_test_save",
                "update_firestore": True,
            }

            start_time = time.time()

            try:
                response = self.test_session.post(f"{self.base_url}/save", json=doc_data, headers=headers)

                end_time = time.time()
                response_time = end_time - start_time
                save_times.append(response_time)

                if response.status_code == 200:
                    successful_saves += 1
                    print(f"✅ Saved doc {i+1}/20 in {response_time:.2f}s")
                elif response.status_code == 429:
                    rate_limited_saves += 1
                    print(f"⏰ Doc {i+1}/20 rate limited, waiting...")
                    time.sleep(6)  # Wait for rate limit to reset
                else:
                    print(f"❌ Doc {i+1}/20 failed with status {response.status_code}")

                # Respect rate limits (10/minute = 6 seconds between requests)
                if response.status_code != 429:
                    time.sleep(6)

            except requests.exceptions.RequestException as e:
                print(f"❌ Doc {i+1}/20 failed with error: {e}")
                continue

        # Calculate statistics
        if save_times:
            avg_time = statistics.mean(save_times)
            max_time = max(save_times)
            min_time = min(save_times)

            print(f"📊 Save Performance Results:")
            print(f"  - Successful saves: {successful_saves}/20")
            print(f"  - Rate limited saves: {rate_limited_saves}")
            print(f"  - Average response time: {avg_time:.2f}s")
            print(f"  - Max response time: {max_time:.2f}s")
            print(f"  - Min response time: {min_time:.2f}s")

            # Verify performance requirements
            assert avg_time < 10.0, f"Average save time {avg_time:.2f}s exceeds 10s limit"
            assert successful_saves >= 15, f"Expected at least 15 successful saves, got {successful_saves}"

            self.__class__.successful_operations += successful_saves
            self.__class__.rate_limited_operations += rate_limited_saves
            self.__class__.response_times.extend(save_times)

    @pytest.mark.deferred
    def test_03_performance_search_queries(self):
        """Test 15 search queries with performance monitoring"""
        if not self.access_token:
            pytest.skip("Authentication token not available")

        headers = {"Authorization": f"Bearer {self.access_token}"}
        search_times = []
        successful_searches = 0
        rate_limited_searches = 0

        print(f"🔍 Starting performance test: 15 search queries...")

        search_queries = [
            "performance test document content",
            "OpenAI API integration testing",
            "Qdrant vector storage functionality",
            "Firestore metadata synchronization",
            "agent data performance testing",
            "document vectorization pipeline",
            "semantic search capabilities",
            "JWT authentication system",
            "rate limiting implementation",
            "Cloud Run deployment",
            "asia-southeast1 region testing",
            "real-time document processing",
            "scalable vector database",
            "machine learning embeddings",
            "production ready API",
        ]

        for i, query in enumerate(search_queries):
            start_time = time.time()

            try:
                response = self.test_session.post(
                    f"{self.base_url}/query",
                    json={"query_text": query, "limit": 5, "score_threshold": 0.5, "tag": "performance_test_save"},
                    headers=headers,
                )

                end_time = time.time()
                response_time = end_time - start_time
                search_times.append(response_time)

                if response.status_code == 200:
                    successful_searches += 1
                    result = response.json()
                    print(f"✅ Search {i+1}/15 completed in {response_time:.2f}s - {result['total_found']} results")
                elif response.status_code == 429:
                    rate_limited_searches += 1
                    print(f"⏰ Search {i+1}/15 rate limited")
                    time.sleep(3)  # Wait for rate limit to reset
                else:
                    print(f"❌ Search {i+1}/15 failed with status {response.status_code}")

                # Respect rate limits (20/minute = 3 seconds between requests)
                if response.status_code != 429:
                    time.sleep(3)

            except requests.exceptions.RequestException as e:
                print(f"❌ Search {i+1}/15 failed with error: {e}")
                continue

        # Calculate statistics
        if search_times:
            avg_time = statistics.mean(search_times)
            max_time = max(search_times)
            min_time = min(search_times)

            print(f"📊 Search Performance Results:")
            print(f"  - Successful searches: {successful_searches}/15")
            print(f"  - Rate limited searches: {rate_limited_searches}")
            print(f"  - Average response time: {avg_time:.2f}s")
            print(f"  - Max response time: {max_time:.2f}s")
            print(f"  - Min response time: {min_time:.2f}s")

            # Verify performance requirements
            assert avg_time < 5.0, f"Average search time {avg_time:.2f}s exceeds 5s limit"
            assert successful_searches >= 12, f"Expected at least 12 successful searches, got {successful_searches}"

            self.__class__.successful_operations += successful_searches
            self.__class__.rate_limited_operations += rate_limited_searches
            self.__class__.response_times.extend(search_times)

    @pytest.mark.deferred
    def test_04_performance_document_searches(self):
        """Test 15 document searches with performance monitoring"""
        if not self.access_token:
            pytest.skip("Authentication token not available")

        headers = {"Authorization": f"Bearer {self.access_token}"}
        doc_search_times = []
        successful_doc_searches = 0
        rate_limited_doc_searches = 0

        print(f"📄 Starting performance test: 15 document searches...")

        for i in range(15):
            start_time = time.time()

            try:
                response = self.test_session.post(
                    f"{self.base_url}/search",
                    json={
                        "tag": "performance_test_save",
                        "limit": 10,
                        "offset": i * 2,  # Vary offset for different results
                        "include_vectors": False,
                    },
                    headers=headers,
                )

                end_time = time.time()
                response_time = end_time - start_time
                doc_search_times.append(response_time)

                if response.status_code == 200:
                    successful_doc_searches += 1
                    result = response.json()
                    print(f"✅ Doc search {i+1}/15 completed in {response_time:.2f}s - {result['total_found']} docs")
                elif response.status_code == 429:
                    rate_limited_doc_searches += 1
                    print(f"⏰ Doc search {i+1}/15 rate limited")
                    time.sleep(2)  # Wait for rate limit to reset
                else:
                    print(f"❌ Doc search {i+1}/15 failed with status {response.status_code}")

                # Respect rate limits (30/minute = 2 seconds between requests)
                if response.status_code != 429:
                    time.sleep(2)

            except requests.exceptions.RequestException as e:
                print(f"❌ Doc search {i+1}/15 failed with error: {e}")
                continue

        # Calculate statistics
        if doc_search_times:
            avg_time = statistics.mean(doc_search_times)
            max_time = max(doc_search_times)
            min_time = min(doc_search_times)

            print(f"📊 Document Search Performance Results:")
            print(f"  - Successful doc searches: {successful_doc_searches}/15")
            print(f"  - Rate limited doc searches: {rate_limited_doc_searches}")
            print(f"  - Average response time: {avg_time:.2f}s")
            print(f"  - Max response time: {max_time:.2f}s")
            print(f"  - Min response time: {min_time:.2f}s")

            # Verify performance requirements
            assert avg_time < 3.0, f"Average doc search time {avg_time:.2f}s exceeds 3s limit"
            assert (
                successful_doc_searches >= 12
            ), f"Expected at least 12 successful doc searches, got {successful_doc_searches}"

            self.__class__.successful_operations += successful_doc_searches
            self.__class__.rate_limited_operations += rate_limited_doc_searches
            self.__class__.response_times.extend(doc_search_times)

    @pytest.mark.deferred
    def test_05_overall_performance_summary(self):
        """Summarize overall performance test results"""
        if not self.response_times:
            pytest.skip("No performance data available")

        total_operations = self.successful_operations + self.rate_limited_operations + self.failed_operations
        avg_response_time = statistics.mean(self.response_times)
        max_response_time = max(self.response_times)
        min_response_time = min(self.response_times)

        print(f"🎯 OVERALL PERFORMANCE SUMMARY:")
        print(f"  - Total operations attempted: {total_operations}")
        print(f"  - Successful operations: {self.successful_operations}")
        print(f"  - Rate limited operations: {self.rate_limited_operations}")
        print(f"  - Failed operations: {self.failed_operations}")
        print(f"  - Success rate: {(self.successful_operations/total_operations)*100:.1f}%")
        print(f"  - Average response time: {avg_response_time:.2f}s")
        print(f"  - Max response time: {max_response_time:.2f}s")
        print(f"  - Min response time: {min_response_time:.2f}s")

        # Verify overall performance requirements
        assert (
            self.successful_operations >= 40
        ), f"Expected at least 40 successful operations, got {self.successful_operations}"
        assert avg_response_time < 5.0, f"Average response time {avg_response_time:.2f}s exceeds 5s limit"
        assert (
            self.successful_operations / total_operations
        ) >= 0.8, f"Success rate {(self.successful_operations/total_operations)*100:.1f}% below 80%"

        print(f"✅ Performance test PASSED - All requirements met!")

    @classmethod
    def teardown_class(cls):
        """Cleanup after tests"""
        if cls.test_session:
            cls.test_session.close()
        print("✅ Performance tests completed")


if __name__ == "__main__":
    # Run performance tests
    test_instance = TestCloudPerformance()
    test_instance.setup_class()

    try:
        test_instance.test_01_authenticate_for_performance()
        test_instance.test_02_performance_save_documents()
        test_instance.test_03_performance_search_queries()
        test_instance.test_04_performance_document_searches()
        test_instance.test_05_overall_performance_summary()
        print("🎉 All performance tests passed!")
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
    finally:
        test_instance.teardown_class()
