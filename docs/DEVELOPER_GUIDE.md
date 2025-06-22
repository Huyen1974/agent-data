# Agent Data System - Developer Guide

## Overview

The Agent Data system is a serverless knowledge management platform built on Google Cloud infrastructure. It provides automated document ingestion, vectorization, and retrieval capabilities using Qdrant vector database, Google Cloud Firestore, and Google Cloud Storage.

### Architecture

The system consists of several key components:

- **Ingestion Workflow**: Orchestrates the complete document processing pipeline
- **Vector Store (Qdrant)**: Stores document embeddings for semantic search
- **Firestore**: Manages document metadata and session information
- **Google Cloud Storage**: Stores original documents
- **API Endpoints**: RESTful APIs for document processing and search
- **Event System**: Pub/Sub integration for real-time notifications

### Key Features

- Automated document ingestion with vectorization
- Semantic search capabilities
- Auto-tagging using AI
- Session management for agent interactions
- Real-time event publishing
- Comprehensive monitoring and logging

## Ingestion Workflow

The ingestion workflow (`ingestion-workflow`) is the main entry point for processing documents. It orchestrates the complete pipeline from document storage to vectorization and tagging.

### Triggering the Workflow

The workflow is deployed as a Google Cloud Workflow and can be triggered via HTTP POST:

```bash
curl -X POST \
  "https://workflowexecutions-asia-southeast1.googleapis.com/v1/projects/chatgpt-db-project/locations/asia-southeast1/workflows/ingestion-workflow/executions" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "argument": "{\"doc_id\": \"example-doc-123\", \"content\": \"This is example document content for processing.\", \"metadata\": {\"author\": \"John Doe\", \"category\": \"research\"}, \"tag\": \"research-docs\"}"
  }'
```

### Workflow Input Format

```json
{
  "doc_id": "unique-document-identifier",
  "content": "The actual document content to be processed",
  "metadata": {
    "author": "Document author",
    "category": "Document category",
    "created_at": "2024-01-01T00:00:00Z",
    "custom_field": "Any custom metadata"
  },
  "tag": "document-tag-for-filtering"
}
```

### Workflow Output

```json
{
  "status": "success",
  "doc_id": "example-doc-123",
  "vectorize_result": {
    "status": "success",
    "doc_id": "example-doc-123",
    "metadata": {...},
    "api_response": {...}
  },
  "auto_tag_result": {
    "status": "success",
    "tags": ["research", "analysis", "data"],
    "metadata": {...}
  },
  "execution_time": 9.91
}
```

## API Endpoints

### /vectorize

Performs document ingestion including storage to GCS, vectorization with Qdrant, and Firestore metadata updates.

**Endpoint**: `https://api-a2a-1042559846495.asia-southeast1.run.app/vectorize`

**Method**: POST

**Input**:
```json
{
  "doc_id": "string",
  "content": "string",
  "metadata": "object",
  "tag": "string",
  "update_firestore": "boolean"
}
```

**Output**:
```json
{
  "status": "string",
  "doc_id": "string",
  "metadata": "object",
  "api_response": "object"
}
```

**Example**:
```bash
curl -X POST \
  "https://api-a2a-1042559846495.asia-southeast1.run.app/vectorize" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -d '{
    "doc_id": "test-doc-001",
    "content": "This is a test document about machine learning and AI.",
    "metadata": {
      "author": "AI Researcher",
      "category": "research",
      "created_at": "2024-01-01T00:00:00Z"
    },
    "tag": "ml-research",
    "update_firestore": true
  }'
```

### /auto_tag

Performs AI-powered auto-tagging of documents and updates Firestore metadata.

**Endpoint**: `https://api-a2a-1042559846495.asia-southeast1.run.app/auto_tag`

**Method**: POST

**Input**:
```json
{
  "content": "string",
  "metadata": "object",
  "max_tags": "integer"
}
```

**Output**:
```json
{
  "status": "string",
  "tags": "array",
  "metadata": "object"
}
```

**Example**:
```bash
curl -X POST \
  "https://api-a2a-1042559846495.asia-southeast1.run.app/auto_tag" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -d '{
    "content": "This document discusses neural networks and deep learning algorithms.",
    "metadata": {
      "doc_id": "test-doc-001",
      "author": "AI Researcher"
    },
    "max_tags": 5
  }'
```

## Firestore Collections

### document_metadata

Stores metadata for all processed documents.

**Schema**:
```json
{
  "doc_id": "string",
  "content_preview": "string (first 200 chars)",
  "metadata": {
    "author": "string",
    "category": "string",
    "created_at": "timestamp",
    "updated_at": "timestamp",
    "version": "integer",
    "custom_fields": "object"
  },
  "tag": "string",
  "vector_id": "string",
  "embedding_model": "string",
  "processing_status": "string",
  "auto_tags": ["array of strings"],
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### agent_sessions

Manages agent session state and memory.

**Schema**:
```json
{
  "session_id": "string",
  "agent_id": "string",
  "state": "object",
  "memory": "object",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "last_activity": "timestamp",
  "status": "string"
}
```

### project_tree

Stores hierarchical project structure information.

**Schema**:
```json
{
  "node_id": "string",
  "parent_id": "string",
  "name": "string",
  "type": "string",
  "metadata": "object",
  "children": ["array of node_ids"],
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### change_reports

Tracks changes and modifications to documents.

**Schema**:
```json
{
  "report_id": "string",
  "doc_id": "string",
  "change_type": "string",
  "old_value": "object",
  "new_value": "object",
  "timestamp": "timestamp",
  "user_id": "string",
  "impact_score": "number"
}
```

### auto_tag_cache

Caches auto-tagging results for performance optimization.

**Schema**:
```json
{
  "content_hash": "string",
  "tags": ["array of strings"],
  "confidence_scores": "object",
  "model_version": "string",
  "created_at": "timestamp",
  "expires_at": "timestamp"
}
```

## Google Cloud Storage

### agent-data-storage-test

**Purpose**: Store original documents during ingestion
**Region**: asia-southeast1
**Access**: Service account has `roles/storage.objectAdmin`

**Usage**:
- Documents are stored with path: `documents/{doc_id}/{timestamp}.txt`
- Supports versioning for document updates
- Lifecycle policies can be configured for cost optimization

### qdrant-snapshots

**Purpose**: Store Qdrant database snapshots for backup
**Region**: asia-southeast1
**Project**: github-chatgpt-ggcloud

## Setup Instructions

### Prerequisites

1. **Google Cloud Project**: `chatgpt-db-project`
2. **Service Account**: `gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com`
3. **Required IAM Roles**:
   - `roles/run.invoker`
   - `roles/cloudfunctions.invoker`
   - `roles/pubsub.publisher`
   - `roles/secretmanager.secretAccessor`
   - `roles/storage.objectAdmin`
   - `roles/cloudbuild.builds.builder`
   - `roles/workflows.editor`
   - `roles/workflows.invoker`
   - `roles/iam.serviceAccountTokenCreator`
   - `roles/iam.serviceAccountUser`
   - `roles/run.admin`

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mpc_back_end_for_agents
   ```

2. **Set up Python environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install the package in development mode**:
   ```bash
   pip install -e .
   ```

4. **Set up Google Cloud authentication**:
   ```bash
   gcloud auth login
   gcloud config set project chatgpt-db-project
   gcloud auth application-default login
   ```

5. **Set up environment variables**:
   ```bash
   export GOOGLE_CLOUD_PROJECT=chatgpt-db-project
   export FIRESTORE_DATABASE=test-default
   export QDRANT_URL=https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io
   export QDRANT_API_KEY=$(gcloud secrets versions access latest --secret="qdrant-api-key-sg" --project=chatgpt-db-project)
   ```

6. **Run tests**:
   ```bash
   # Run all tests (full suite - ~10 minutes)
   pytest

   # Run specific test categories
   pytest -m "unit"
   pytest -m "integration"
   pytest -m "e2e"

   # Run with coverage
   pytest --cov=agent_data_manager

   # OPTIMIZED TEST COMMANDS (CLI 126A)
   # Fast selective tests (development) - excludes slow tests, uses testmon
   pytest -q -m 'not slow and not deferred' --testmon

   # Fast parallel execution (full suite before commit)
   pytest -n 8 --dist worksteal

   # Quick E2E validation (~2 seconds)
   pytest -m "e2e" -v

   # Test aliases for efficiency:
   # ptfast: pytest -q -m 'not slow and not deferred' --testmon
   # ptfull: pytest -n 8 --dist worksteal
   ```

### Required Credentials

1. **Qdrant API Key**: Stored in Secret Manager as `qdrant-api-key-sg`
2. **OpenAI API Key**: Required for embedding generation (set as environment variable)
3. **Google Cloud Service Account**: JSON key file or Application Default Credentials

### Configuration

The system uses the following configuration:

- **Region**: All resources deployed in `asia-southeast1` (Singapore)
- **Qdrant Cluster**: Free tier (1GB storage, 210-305ms latency)
- **Firestore**: Native mode in `asia-southeast1`
- **Logging**: JSON format with 10% INFO sampling for cost optimization
- **Monitoring**: Cloud Monitoring with custom metrics and alerts

## Development Workflow

### Adding New Features

1. **Create feature branch**:
   ```bash
   git checkout -b feature/new-feature-name
   ```

2. **Implement changes**:
   - Add new functionality
   - Write comprehensive tests
   - Update documentation

3. **Run tests**:
   ```bash
   pytest -n 8  # Parallel execution
   ```

4. **Update test count** (if adding tests):
   ```python
   # In tests/test__meta_count.py
   EXPECTED_TOTAL_TESTS = <new_count>
   ```

5. **Commit and push**:
   ```bash
   git add .
   git commit -m "feat: description of new feature"
   git push origin feature/new-feature-name
   ```

### Testing Guidelines

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **E2E Tests**: Test complete workflows end-to-end (4 tests, ~2 seconds)
- **Performance Tests**: Validate latency and throughput requirements
- **Mock External Dependencies**: Use mocks for OpenAI, Qdrant, etc. in tests

**Test Optimization Strategy (CLI 126A)**:
- **Selective Execution**: Use `pytest -m "e2e"` for quick validation during development
- **Parallel Testing**: Use `pytest -n 8 --dist worksteal` for full suite runs
- **Test Monitoring**: Use `pytest --testmon` to run only affected tests
- **Development Workflow**: Run E2E tests (~2s) for quick feedback, full suite before commits
- **Current Status**: 259 total tests, 98.84% pass rate (256 passed, 3 skipped)

### Deployment

1. **API Deployment**:
   ```bash
   ./deploy_api_a2a_production.sh
   ```

2. **Workflow Deployment**:
   ```bash
   gcloud workflows deploy ingestion-workflow \
     --source=workflows/ingestion-workflow.yaml \
     --location=asia-southeast1
   ```

## Monitoring and Observability

### Logging

- **Format**: Structured JSON logging
- **Sampling**: 10% INFO level sampling for cost optimization
- **Location**: Cloud Logging in `chatgpt-db-project`

### Metrics

- **Qdrant Latency**: P95 latency monitoring with alerts >1s
- **API Response Times**: Track /vectorize and /auto_tag performance
- **Error Rates**: Monitor 4xx/5xx responses
- **Document Processing**: Track ingestion success/failure rates

### Alerts

- **Qdrant Latency Alert**: Triggers when P95 > 1 second
- **Workflow Failures**: Alert on ingestion-workflow errors
- **API Errors**: Alert on high error rates

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**:
   - Verify service account has required IAM roles
   - Check that resources are in the correct region (asia-southeast1)

2. **Qdrant Connection Issues**:
   - Verify API key in Secret Manager
   - Check cluster status in Qdrant Cloud console

3. **Firestore Access Issues**:
   - Ensure Firestore is in Native mode
   - Verify database name is `test-default`

4. **Test Failures**:
   - Check if external dependencies (OpenAI, Qdrant) are available
   - Verify environment variables are set correctly
   - Run tests with `-v` flag for detailed output

### Performance Optimization

- **Batch Processing**: Use batch size of 100 with 0.35s sleep between batches
- **Connection Pooling**: Reuse HTTP connections where possible
- **Caching**: Leverage auto_tag_cache for repeated content
- **Monitoring**: Use Cloud Monitoring to identify bottlenecks

## Security Considerations

- **API Keys**: Store in Secret Manager, never in code
- **IAM**: Follow principle of least privilege
- **Network**: Use private endpoints where possible
- **Data**: Encrypt data at rest and in transit
- **Audit**: Enable Cloud Audit Logs for compliance

## Support and Resources

- **Documentation**: See `docs/` directory for additional guides
- **Test Plans**: Reference `.cursor/README_TEST_Qdrant_30_to_50_plan.md`
- **API Reference**: See `openapi.json` for complete API specification
- **Monitoring Dashboard**: Available in Google Cloud Console

For additional support, refer to the project's issue tracker or contact the development team.
