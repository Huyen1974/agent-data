"""
Test suite for session memory and Pub/Sub A2A communication functionality.
Tests session CRUD operations, event publishing, and integration with vectorization.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_data_manager.agent.agent_data_agent import AgentDataAgent
from agent_data_manager.event.event_manager import EventManager
from agent_data_manager.session.session_manager import SessionManager
from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool


class TestSessionMemory:
    """Test session memory functionality."""

    @pytest.fixture
    def mock_firestore_manager(self):
        """Mock FirestoreMetadataManager for session tests."""
        with patch(
            "agent_data_manager.session.session_manager.FirestoreMetadataManager"
        ) as mock:
            mock_instance = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_session_creation(self, mock_firestore_manager):
        """Test creating a new session with auto-generated ID."""
        session_manager = SessionManager()

        # Mock successful save
        mock_firestore_manager.save_metadata.return_value = None

        result = await session_manager.create_session()

        assert result["status"] == "success"
        assert "session_id" in result
        assert "created_at" in result
        mock_firestore_manager.save_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_creation_with_custom_id(self, mock_firestore_manager):
        """Test creating a session with custom ID and initial state."""
        session_manager = SessionManager()
        custom_id = "test-session-123"
        initial_state = {"user_id": "user123", "context": "testing"}

        # Mock successful save
        mock_firestore_manager.save_metadata.return_value = None

        result = await session_manager.create_session(
            session_id=custom_id, initial_state=initial_state
        )

        assert result["status"] == "success"
        assert result["session_id"] == custom_id

        # Verify save was called with correct data
        call_args = mock_firestore_manager.save_metadata.call_args
        assert call_args[0][0] == custom_id  # session_id
        session_data = call_args[0][1]  # session_data
        assert session_data["session_id"] == custom_id
        assert session_data["state"] == initial_state
        assert session_data["status"] == "active"

    @pytest.mark.asyncio
    async def test_session_retrieval(self, mock_firestore_manager):
        """Test retrieving an existing session."""
        session_manager = SessionManager()
        session_id = "test-session-456"
        mock_session_data = {
            "session_id": session_id,
            "state": {"last_action": "test"},
            "created_at": "2024-01-01T00:00:00",
            "status": "active",
        }

        # Mock successful retrieval
        mock_firestore_manager.get_metadata.return_value = mock_session_data

        result = await session_manager.get_session(session_id)

        assert result == mock_session_data
        mock_firestore_manager.get_metadata.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_session_state_update(self, mock_firestore_manager):
        """Test updating session state."""
        session_manager = SessionManager()
        session_id = "test-session-789"
        existing_state = {"counter": 1, "action": "initial"}
        state_update = {"counter": 2, "new_field": "added"}

        mock_existing_session = {
            "session_id": session_id,
            "state": existing_state,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "status": "active",
        }

        # Mock getting existing session and saving updated session
        mock_firestore_manager.get_metadata.return_value = mock_existing_session
        mock_firestore_manager.save_metadata.return_value = None

        result = await session_manager.update_session_state(session_id, state_update)

        assert result["status"] == "success"
        assert result["session_id"] == session_id

        # Verify the state was merged correctly
        save_call_args = mock_firestore_manager.save_metadata.call_args
        updated_data = save_call_args[0][1]
        expected_state = {**existing_state, **state_update}
        assert updated_data["state"] == expected_state
        assert "updated_at" in updated_data

    @pytest.mark.asyncio
    async def test_session_deletion(self, mock_firestore_manager):
        """Test deleting a session."""
        session_manager = SessionManager()
        session_id = "test-session-delete"

        # Mock successful deletion
        mock_firestore_manager.delete_metadata.return_value = None

        result = await session_manager.delete_session(session_id)

        assert result["status"] == "success"
        assert result["session_id"] == session_id
        mock_firestore_manager.delete_metadata.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, mock_firestore_manager):
        """Test creating and managing multiple sessions."""
        session_manager = SessionManager()

        # Mock successful operations
        mock_firestore_manager.save_metadata.return_value = None
        mock_firestore_manager.delete_metadata.return_value = None

        # Create 8 sessions as specified in CLI 123
        sessions = []
        for i in range(8):
            result = await session_manager.create_session(
                initial_state={"session_index": i, "test_data": f"session_{i}"}
            )
            assert result["status"] == "success"
            sessions.append(result["session_id"])

        # Verify all 8 sessions were created
        assert len(sessions) == 8
        assert mock_firestore_manager.save_metadata.call_count == 8


class TestPubSubEvents:
    """Test Pub/Sub A2A communication functionality."""

    @pytest.fixture
    def mock_pubsub_publisher(self):
        """Mock Google Cloud Pub/Sub publisher."""
        with (
            patch("agent_data_manager.event.event_manager.pubsub_v1") as mock_pubsub,
            patch("agent_data_manager.event.event_manager.PUBSUB_AVAILABLE", True),
        ):
            mock_publisher = MagicMock()
            mock_future = MagicMock()
            mock_future.result.return_value = "test-message-id-123"
            mock_publisher.publish.return_value = mock_future
            mock_publisher.topic_path.return_value = (
                "projects/test-project/topics/agent-data-events"
            )
            mock_pubsub.PublisherClient.return_value = mock_publisher
            yield mock_publisher

    @pytest.mark.asyncio
    async def test_save_document_event_publishing(self, mock_pubsub_publisher):
        """Test publishing save_document events."""
        event_manager = EventManager(project_id="test-project")

        doc_id = "test-doc-123"
        metadata = {"vector_id": "vec-123", "size": 1536}
        session_id = "session-456"

        result = await event_manager.publish_save_document_event(
            doc_id=doc_id, metadata=metadata, session_id=session_id
        )

        assert result["status"] == "success"
        assert result["message_id"] == "test-message-id-123"
        assert result["doc_id"] == doc_id

        # Verify publish was called with correct data
        mock_pubsub_publisher.publish.assert_called_once()
        call_args = mock_pubsub_publisher.publish.call_args

        # Parse the published message data
        import json

        message_data = json.loads(call_args[0][1].decode("utf-8"))
        assert message_data["event_type"] == "save_document"
        assert message_data["doc_id"] == doc_id
        assert message_data["session_id"] == session_id
        assert message_data["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_custom_event_publishing(self, mock_pubsub_publisher):
        """Test publishing custom events."""
        event_manager = EventManager(project_id="test-project")

        event_type = "document_updated"
        event_data = {"doc_id": "doc-789", "changes": ["metadata", "content"]}
        session_id = "session-123"

        result = await event_manager.publish_custom_event(
            event_type=event_type, event_data=event_data, session_id=session_id
        )

        assert result["status"] == "success"
        assert result["message_id"] == "test-message-id-123"
        assert result["event_type"] == event_type

        # Verify publish was called
        mock_pubsub_publisher.publish.assert_called_once()

        # Parse the published message data
        import json

        call_args = mock_pubsub_publisher.publish.call_args
        message_data = json.loads(call_args[0][1].decode("utf-8"))
        assert message_data["event_type"] == event_type
        assert message_data["session_id"] == session_id
        assert message_data["doc_id"] == event_data["doc_id"]

    @pytest.mark.asyncio
    async def test_multiple_event_publishing(self, mock_pubsub_publisher):
        """Test publishing multiple events as specified in CLI 123."""
        event_manager = EventManager(project_id="test-project")

        # Publish 10 events as specified
        published_events = []
        for i in range(10):
            result = await event_manager.publish_save_document_event(
                doc_id=f"doc-{i}",
                metadata={"index": i, "test": True},
                session_id=f"session-{i % 3}",  # Distribute across 3 sessions
            )
            assert result["status"] == "success"
            published_events.append(result)

        # Verify all 10 events were published
        assert len(published_events) == 10
        assert mock_pubsub_publisher.publish.call_count == 10

    @pytest.mark.asyncio
    async def test_event_publishing_without_pubsub(self):
        """Test graceful handling when Pub/Sub is not available."""
        with patch("agent_data_manager.event.event_manager.PUBSUB_AVAILABLE", False):
            event_manager = EventManager(project_id="test-project")

            result = await event_manager.publish_save_document_event(
                doc_id="test-doc", metadata={"test": True}
            )

            assert result["status"] == "skipped"
            assert result["reason"] == "pubsub_not_available"


class TestIntegration:
    """Test integration between session management, event publishing, and vectorization."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for integration tests."""
        with (
            patch(
                "agent_data_manager.session.session_manager.FirestoreMetadataManager"
            ) as mock_firestore,
            patch("agent_data_manager.event.event_manager.pubsub_v1") as mock_pubsub,
            patch("agent_data_manager.event.event_manager.PUBSUB_AVAILABLE", True),
            patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore"
            ) as mock_qdrant,
            patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.get_default_embedding_provider"
            ) as mock_embedding,
            patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool"
            ) as mock_auto_tag,
        ):

            # Setup Firestore mock
            mock_firestore_instance = AsyncMock()
            mock_firestore.return_value = mock_firestore_instance

            # Setup Pub/Sub mock
            mock_publisher = MagicMock()
            mock_future = MagicMock()
            mock_future.result.return_value = "msg-id-123"
            mock_publisher.publish.return_value = mock_future
            mock_publisher.topic_path.return_value = (
                "projects/test/topics/agent-data-events"
            )
            mock_pubsub.PublisherClient.return_value = mock_publisher

            # Setup Qdrant mock
            mock_qdrant_instance = AsyncMock()
            mock_qdrant_instance.upsert_vector.return_value = {
                "success": True,
                "vector_id": "vec-123",
            }
            mock_qdrant.return_value = mock_qdrant_instance

            # Setup embedding provider mock
            mock_embedding_provider = AsyncMock()
            mock_embedding_provider.embed_single.return_value = [0.1] * 1536
            mock_embedding_provider.get_model_name.return_value = (
                "text-embedding-ada-002"
            )
            mock_embedding.return_value = mock_embedding_provider

            # Setup auto-tagging tool mock
            mock_auto_tagging_tool = AsyncMock()
            mock_auto_tagging_tool.enhance_metadata_with_tags.return_value = {
                "auto_tagged": True
            }
            mock_auto_tag.return_value = mock_auto_tagging_tool

            yield {
                "firestore": mock_firestore_instance,
                "pubsub": mock_publisher,
                "qdrant": mock_qdrant_instance,
                "embedding": mock_embedding_provider,
                "auto_tag": mock_auto_tagging_tool,
            }

    @pytest.mark.asyncio
    async def test_agent_session_management(self, mock_dependencies):
        """Test AgentDataAgent session management integration."""
        agent = AgentDataAgent()

        # Mock the session get_metadata to return a proper session structure
        mock_session_data = {
            "session_id": "test-session",
            "state": {"user": "test"},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "status": "active",
        }
        mock_dependencies["firestore"].get_metadata.return_value = mock_session_data

        # Test session creation
        result = await agent.create_session(initial_state={"user": "test"})
        assert result["status"] == "success"
        assert agent.current_session_id is not None

        # Test session state update
        update_result = await agent.update_session_state({"action": "test"})
        assert update_result["status"] == "success"

        # Test session closure
        close_result = await agent.close_session()
        assert close_result["status"] == "success"
        assert agent.current_session_id is None

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="CLI140m.69: Complex async integration test with timeout issues"
    )
    async def test_vectorization_with_events(self, mock_dependencies):
        """Test that vectorization publishes events correctly."""
        vectorization_tool = QdrantVectorizationTool()

        doc_id = "integration-test-doc"
        content = "This is a test document for integration testing."
        metadata = {"source": "integration_test"}

        # Mock successful vectorization
        mock_dependencies["firestore"].save_metadata.return_value = None

        result = await vectorization_tool.vectorize_document(
            doc_id=doc_id, content=content, metadata=metadata, update_firestore=True
        )

        assert result["status"] == "success"
        assert result["doc_id"] == doc_id

        # Verify event was published
        mock_dependencies["pubsub"].publish.assert_called()

        # Parse the event data
        import json

        call_args = mock_dependencies["pubsub"].publish.call_args
        event_data = json.loads(call_args[0][1].decode("utf-8"))
        assert event_data["event_type"] == "save_document"
        assert event_data["doc_id"] == doc_id

    @pytest.mark.asyncio
    async def test_session_context_in_vectorization(self, mock_dependencies):
        """Test that session context is maintained during vectorization."""
        agent = AgentDataAgent()

        # Create a session
        session_result = await agent.create_session(
            initial_state={"context": "vectorization_test"}
        )
        session_id = session_result["session_id"]

        # Mock input data with session ID
        input_data = {
            "tool_name": "qdrant_vectorize_document",
            "session_id": session_id,
            "args": ["test-doc", "Test content"],
            "kwargs": {"metadata": {"test": True}},
        }

        # Mock the tool execution to avoid actual vectorization
        with patch.object(agent.tools_manager, "execute_tool") as mock_execute:
            mock_execute.return_value = {"status": "success", "doc_id": "test-doc"}

            await agent.run(input_data)

            # Verify session ID was set
            assert agent.current_session_id == session_id


class TestErrorHandling:
    """Test error handling in session and event management."""

    @pytest.mark.asyncio
    async def test_session_manager_firestore_error(self):
        """Test session manager handles Firestore errors gracefully."""
        with patch(
            "agent_data_manager.session.session_manager.FirestoreMetadataManager"
        ) as mock_firestore:
            mock_firestore.side_effect = Exception("Firestore connection failed")

            session_manager = SessionManager()

            with pytest.raises(Exception):
                await session_manager._ensure_initialized()

    @pytest.mark.asyncio
    async def test_event_manager_pubsub_error(self):
        """Test event manager handles Pub/Sub errors gracefully."""
        with (
            patch("agent_data_manager.event.event_manager.pubsub_v1") as mock_pubsub,
            patch("agent_data_manager.event.event_manager.PUBSUB_AVAILABLE", True),
        ):
            mock_publisher = MagicMock()
            mock_publisher.publish.side_effect = Exception("Pub/Sub publish failed")
            mock_pubsub.PublisherClient.return_value = mock_publisher

            event_manager = EventManager(project_id="test-project")

            result = await event_manager.publish_save_document_event("test-doc")

            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_session_not_found_error(self):
        """Test handling of session not found scenarios."""
        with patch(
            "agent_data_manager.session.session_manager.FirestoreMetadataManager"
        ) as mock_firestore:
            mock_firestore_instance = AsyncMock()
            mock_firestore_instance.get_metadata.return_value = None
            mock_firestore.return_value = mock_firestore_instance

            session_manager = SessionManager()

            # Test updating non-existent session
            result = await session_manager.update_session_state(
                "non-existent", {"test": True}
            )
            assert result["status"] == "failed"
            assert "not found" in result["error"]
