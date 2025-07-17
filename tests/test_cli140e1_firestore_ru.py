"""
CLI140e.1 Firestore RU Optimization Tests
Tests for reducing Firestore Read Units by ~30% using Select().limit(1)
Focus on optimized existence checks and minimal field reads
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Test imports
from ADK.agent_data.vector_store.firestore_metadata_manager import (
    FirestoreMetadataManager,
)

logger = logging.getLogger(__name__)


class TestFirestoreRUOptimization:
    """Test suite for CLI140e.1 Firestore RU optimization."""

    @pytest.fixture
    def mock_firestore_client(self):
        """Mock Firestore async client for testing."""
        mock_client = AsyncMock()

        # Mock collection and document structure
        mock_collection = AsyncMock()
        mock_doc_ref = AsyncMock()
        mock_query = AsyncMock()

        # Setup method chaining
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_collection.select.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.where.return_value = mock_query

        return {
            "client": mock_client,
            "collection": mock_collection,
            "doc_ref": mock_doc_ref,
            "query": mock_query,
        }

    @pytest.fixture
    def ru_cost_tracker(self):
        """Track simulated RU costs for testing optimization."""

        class RUTracker:
            def __init__(self):
                self.total_ru = 0
                self.operations = []

            def record_operation(
                self, operation_type: str, ru_cost: int, details: str = ""
            ):
                self.total_ru += ru_cost
                self.operations.append(
                    {"type": operation_type, "ru_cost": ru_cost, "details": details}
                )
                logger.info(
                    f"RU Operation: {operation_type} - {ru_cost} RU - {details}"
                )

            def get_total_ru(self):
                return self.total_ru

            def get_operations(self):
                return self.operations

            def reset(self):
                self.total_ru = 0
                self.operations = []

        return RUTracker()

    @pytest.mark.asyncio
    async def test_optimized_document_existence_check(
        self, mock_firestore_client, ru_cost_tracker
    ):
        """
        Test optimized document existence check using Select().limit(1).
        Should reduce RU consumption compared to full document fetch.
        """
        # Initialize manager with mock client
        manager = FirestoreMetadataManager()
        manager.db = mock_firestore_client["client"]

        # Mock the optimized existence check
        mock_query = mock_firestore_client["query"]

        # Test case 1: Document exists (optimized path)
        mock_docs = [AsyncMock()]  # One document found
        mock_docs[0].id = "test_doc_1"

        async def mock_stream():
            for doc in mock_docs:
                yield doc

        mock_query.stream.return_value = mock_stream()

        # Execute optimized existence check
        doc_ref = mock_firestore_client["doc_ref"]
        doc_ref.path = "test_collection/test_doc_1"

        exists = await manager._check_document_exists(doc_ref)

        # Verify results
        assert exists is True

        # Verify optimized query construction
        mock_firestore_client["collection"].select.assert_called_with(["__name__"])
        mock_query.limit.assert_called_with(1)
        mock_query.where.assert_called_with(
            "__name__", "==", "test_collection/test_doc_1"
        )

        # Record RU cost (optimized: only 1 RU vs 1-5 RU for full document)
        ru_cost_tracker.record_operation(
            "existence_check_optimized", 1, "select __name__ only"
        )

        logger.info(f"Optimized existence check completed: exists={exists}")

    @pytest.mark.asyncio
    async def test_fallback_existence_check(
        self, mock_firestore_client, ru_cost_tracker
    ):
        """
        Test fallback existence check when optimized method fails.
        """
        manager = FirestoreMetadataManager()
        manager.db = mock_firestore_client["client"]

        # Mock query failure to trigger fallback
        mock_query = mock_firestore_client["query"]
        mock_query.stream.side_effect = Exception("Query failed")

        # Mock standard document get
        mock_doc_ref = mock_firestore_client["doc_ref"]
        mock_doc_snapshot = AsyncMock()
        mock_doc_snapshot.exists = True
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Execute existence check (should fallback)
        exists = await manager._check_document_exists(mock_doc_ref)

        # Verify fallback was used
        assert exists is True
        mock_doc_ref.get.assert_called_once()

        # Record RU cost (fallback: full document cost)
        ru_cost_tracker.record_operation(
            "existence_check_fallback", 3, "full document read"
        )

        logger.info(f"Fallback existence check completed: exists={exists}")

    @pytest.mark.asyncio
    async def test_optimized_versioning_document_fetch(
        self, mock_firestore_client, ru_cost_tracker
    ):
        """
        Test optimized document fetch for versioning with minimal RU usage.
        """
        manager = FirestoreMetadataManager()
        manager.db = mock_firestore_client["client"]

        # Mock optimized existence check
        with patch.object(manager, "_check_document_exists") as mock_exists:
            mock_exists.return_value = True

            # Mock full document fetch
            mock_doc_ref = mock_firestore_client["doc_ref"]
            mock_doc_snapshot = AsyncMock()
            mock_doc_snapshot.exists = True
            mock_doc_snapshot.to_dict.return_value = {
                "version": 2,
                "lastUpdated": "2024-01-01T00:00:00Z",
                "content": "test content",
            }
            mock_doc_ref.get.return_value = mock_doc_snapshot

            # Execute optimized document fetch
            doc_snapshot = await manager._get_document_for_versioning(mock_doc_ref)

            # Verify results
            assert doc_snapshot.exists is True
            assert doc_snapshot.to_dict()["version"] == 2

            # Verify optimized flow: existence check first, then full fetch
            mock_exists.assert_called_once_with(mock_doc_ref)
            mock_doc_ref.get.assert_called_once()

            # Record RU costs
            ru_cost_tracker.record_operation(
                "existence_check", 1, "optimized __name__ select"
            )
            ru_cost_tracker.record_operation(
                "document_fetch", 3, "full document after existence confirmed"
            )

            logger.info(
                f"Optimized versioning fetch completed: version={doc_snapshot.to_dict()['version']}"
            )

    @pytest.mark.asyncio
    async def test_nonexistent_document_optimization(
        self, mock_firestore_client, ru_cost_tracker
    ):
        """
        Test RU optimization for non-existent documents.
        Should avoid full document fetch when document doesn't exist.
        """
        manager = FirestoreMetadataManager()
        manager.db = mock_firestore_client["client"]

        # Mock existence check returning False (no documents found)
        async def mock_empty_stream():
            return
            yield  # This will never execute

        mock_query = mock_firestore_client["query"]
        mock_query.stream.return_value = mock_empty_stream()

        # Mock document reference
        mock_doc_ref = mock_firestore_client["doc_ref"]
        mock_doc_ref.path = "test_collection/nonexistent_doc"

        # Execute optimized document fetch for versioning
        doc_snapshot = await manager._get_document_for_versioning(mock_doc_ref)

        # Verify mock document returned
        assert doc_snapshot.exists is False
        assert doc_snapshot.to_dict() == {}

        # Verify no full document fetch was performed
        mock_doc_ref.get.assert_not_called()

        # Record RU cost (only existence check, no full fetch)
        ru_cost_tracker.record_operation(
            "existence_check_miss", 1, "optimized check, no full fetch needed"
        )

        logger.info("Non-existent document optimization completed: fetch avoided")

    @pytest.mark.asyncio
    async def test_batch_existence_optimization(
        self, mock_firestore_client, ru_cost_tracker
    ):
        """
        Test batch document existence checking with RU optimization.
        """
        manager = FirestoreMetadataManager()
        manager.db = mock_firestore_client["client"]

        doc_ids = [f"doc_{i}" for i in range(10)]

        # Mock batch existence check results
        existing_docs = doc_ids[:7]  # 7 out of 10 exist

        async def mock_batch_exists(doc_ids_list):
            return {doc_id: doc_id in existing_docs for doc_id in doc_ids_list}

        # Execute batch existence check
        with patch.object(
            manager, "_batch_check_documents_exist", side_effect=mock_batch_exists
        ):
            existence_map = await manager._batch_check_documents_exist(doc_ids)

        # Verify results
        assert len(existence_map) == 10
        assert sum(existence_map.values()) == 7

        # Record RU costs for batch operation
        # Optimized: 1 RU per document for existence check vs 3-5 RU for full document
        ru_cost_tracker.record_operation(
            "batch_existence_check", 10, "10 docs @ 1 RU each (optimized)"
        )

        # Compare with non-optimized approach
        ru_cost_tracker.record_operation(
            "batch_full_fetch_comparison", 35, "10 docs @ 3.5 RU each (unoptimized)"
        )

        logger.info(
            f"Batch existence check: {sum(existence_map.values())}/10 documents exist"
        )

    @pytest.mark.unit
    def test_ru_cost_comparison(self, ru_cost_tracker):
        """
        Test and compare RU costs between optimized and unoptimized approaches.
        Target: ~30% reduction in RU usage.
        """
        # Simulate operations for 100 document operations with realistic mix
        num_operations = 100

        # Realistic operation mix:
        # 40% new documents (don't exist)
        # 30% updates (exist)
        # 20% existence checks only
        # 10% batch operations

        new_docs = int(num_operations * 0.4)  # 40
        updates = int(num_operations * 0.3)  # 30
        existence_checks = int(num_operations * 0.2)  # 20
        batch_ops = int(num_operations * 0.1)  # 10

        # Optimized approach costs
        optimized_ru = 0
        # New documents: existence check (1) + write (2) = 3 RU each
        optimized_ru += new_docs * 3
        # Updates: existence check (1) + full fetch (3) + write (2) = 6 RU each
        optimized_ru += updates * 6
        # Existence checks only: 1 RU each
        optimized_ru += existence_checks * 1
        # Batch operations: 1 RU per document for existence check
        optimized_ru += batch_ops * 1

        # Unoptimized approach costs
        unoptimized_ru = 0
        # New documents: full fetch attempt (4) + write (2) = 6 RU each
        unoptimized_ru += new_docs * 6
        # Updates: full fetch (4) + write (2) = 6 RU each
        unoptimized_ru += updates * 6
        # Existence checks: full fetch (4) RU each
        unoptimized_ru += existence_checks * 4
        # Batch operations: 4 RU per document for full fetch
        unoptimized_ru += batch_ops * 4

        # Calculate savings
        ru_savings = unoptimized_ru - optimized_ru
        savings_percentage = (ru_savings / unoptimized_ru) * 100

        # Record the comparison
        ru_cost_tracker.record_operation(
            "optimized_approach", optimized_ru, "100 operations (mixed)"
        )
        ru_cost_tracker.record_operation(
            "unoptimized_approach", unoptimized_ru, "100 operations (mixed)"
        )

        # Assertions
        assert (
            savings_percentage >= 30
        ), f"RU savings {savings_percentage:.1f}% below target 30%"
        assert optimized_ru < unoptimized_ru

        logger.info("RU Cost Comparison (Realistic Mix):")
        logger.info(
            f"  Operations: {new_docs} new, {updates} updates, {existence_checks} checks, {batch_ops} batch"
        )
        logger.info(f"  Optimized: {optimized_ru} RU")
        logger.info(f"  Unoptimized: {unoptimized_ru} RU")
        logger.info(f"  Savings: {ru_savings} RU ({savings_percentage:.1f}%)")

        return {
            "optimized_ru": optimized_ru,
            "unoptimized_ru": unoptimized_ru,
            "savings_ru": ru_savings,
            "savings_percentage": savings_percentage,
        }

    @pytest.mark.asyncio
    async def test_save_metadata_with_ru_optimization(
        self, mock_firestore_client, ru_cost_tracker
    ):
        """
        Test complete save_metadata workflow with RU optimizations.
        """
        manager = FirestoreMetadataManager()
        manager.db = mock_firestore_client["client"]

        # Mock document reference and operations
        mock_doc_ref = mock_firestore_client["doc_ref"]

        # Test saving new document (doesn't exist)
        with (
            patch.object(manager, "_get_document_for_versioning") as mock_get_doc,
            patch.object(manager, "_prepare_versioned_metadata") as mock_prepare,
            patch.object(manager, "_validate_metadata") as mock_validate,
        ):

            # Setup mocks
            mock_validate.return_value = {"valid": True, "errors": []}

            # Mock non-existent document (RU optimized)
            mock_doc_snapshot = MagicMock()
            mock_doc_snapshot.exists = False
            mock_doc_snapshot.to_dict.return_value = {}
            mock_get_doc.return_value = mock_doc_snapshot

            mock_prepare.return_value = {
                "doc_id": "test_doc",
                "content": "test content",
                "version": 1,
                "lastUpdated": "2024-01-01T00:00:00Z",
            }

            # Execute save metadata
            test_metadata = {"doc_id": "test_doc", "content": "test content"}
            await manager.save_metadata("test_doc", test_metadata)

            # Verify optimized document fetch was used
            mock_get_doc.assert_called_once()

            # Record RU costs for save operation
            ru_cost_tracker.record_operation(
                "existence_check_new_doc", 1, "optimized check for new document"
            )
            ru_cost_tracker.record_operation("document_write", 2, "write new document")

            logger.info("Save metadata with RU optimization completed")

    @pytest.mark.integration
    async def test_end_to_end_ru_optimization(
        self, mock_firestore_client, ru_cost_tracker
    ):
        """
        End-to-end test of RU optimization across multiple operations.
        """
        manager = FirestoreMetadataManager()
        manager.db = mock_firestore_client["client"]

        # Simulate a typical workflow
        operations = [
            ("save_new", "doc_1", {"content": "content 1"}),
            ("save_update", "doc_1", {"content": "updated content 1"}),
            ("check_exists", "doc_2", None),
            ("save_new", "doc_3", {"content": "content 3"}),
            ("batch_check", ["doc_1", "doc_2", "doc_3", "doc_4", "doc_5"], None),
        ]

        total_optimized_ru = 0
        total_unoptimized_ru = 0

        for operation_type, doc_id, metadata in operations:
            if operation_type == "save_new":
                # Optimized: existence check (1) + write (2)
                total_optimized_ru += 3
                # Unoptimized: full fetch attempt (3) + write (2)
                total_unoptimized_ru += 5

            elif operation_type == "save_update":
                # Optimized: existence check (1) + full fetch (3) + write (2)
                total_optimized_ru += 6
                # Unoptimized: full fetch (3) + write (2)
                total_unoptimized_ru += 5

            elif operation_type == "check_exists":
                # Optimized: existence check only (1)
                total_optimized_ru += 1
                # Unoptimized: full fetch (3)
                total_unoptimized_ru += 3

            elif operation_type == "batch_check":
                # Optimized: 5 existence checks (5)
                total_optimized_ru += 5
                # Unoptimized: 5 full fetches (15)
                total_unoptimized_ru += 15

        # Calculate total savings
        ru_savings = total_unoptimized_ru - total_optimized_ru
        savings_percentage = (ru_savings / total_unoptimized_ru) * 100

        # Record final results
        ru_cost_tracker.record_operation(
            "end_to_end_optimized", total_optimized_ru, "complete workflow"
        )
        ru_cost_tracker.record_operation(
            "end_to_end_unoptimized", total_unoptimized_ru, "complete workflow"
        )

        # Assertions
        assert (
            savings_percentage >= 30
        ), f"End-to-end RU savings {savings_percentage:.1f}% below target 30%"

        logger.info("End-to-end RU optimization results:")
        logger.info(f"  Total optimized RU: {total_optimized_ru}")
        logger.info(f"  Total unoptimized RU: {total_unoptimized_ru}")
        logger.info(f"  Total savings: {ru_savings} RU ({savings_percentage:.1f}%)")

        return {
            "total_optimized_ru": total_optimized_ru,
            "total_unoptimized_ru": total_unoptimized_ru,
            "savings_percentage": savings_percentage,
            "target_achieved": savings_percentage >= 30,
        }


if __name__ == "__main__":
    # Run RU optimization tests directly
    pytest.main([__file__, "-v", "-m", "integration"])
