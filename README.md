# Agent Data Repository

This repository contains code, tests, and Terraform configurations for the Agent Data project, part of the MPC Backend. It uses Google Cloud (GCP) for infrastructure and GitHub Actions for CI/CD.

## Overview

The Agent Data project provides a comprehensive data management and search solution with the following components:

- **Vector Store**: Qdrant-based vector storage for semantic search
- **Metadata Management**: Firestore-based metadata storage
- **API Gateway**: FastAPI-based REST API for data operations
- **MCP Integration**: Model Context Protocol for agent interactions
- **Tools**: Various data processing and search tools
- **Testing Suite**: Comprehensive test coverage (~932 tests)

## Architecture

- **Backend**: Python FastAPI application
- **Vector Database**: Qdrant for vector storage
- **Metadata Store**: Google Firestore
- **Cloud Platform**: Google Cloud Platform (GCP)
- **CI/CD**: GitHub Actions with Workload Identity Federation
- **Containerization**: Docker with multi-stage builds

## Key Features

- Semantic search with vector embeddings
- Real-time data ingestion and processing
- Scalable cloud infrastructure
- Comprehensive monitoring and logging
- Automated testing and deployment

## Development

### Prerequisites

- Python 3.10+
- Docker
- Google Cloud SDK
- GitHub CLI

### Local Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see `.env.sample`)
4. Run tests: `pytest --qdrant-mock`

### Testing

The project includes a comprehensive test suite optimized for MacBook M1:
- Batch size ≤3 for memory efficiency
- 8-second timeout for stability
- Mock Qdrant for local testing
- ~932 unique tests covering all components (as of CLI 182.5)

## Infrastructure

- **Production**: `github-chatgpt-ggcloud` GCP project
- **Test**: `chatgpt-db-project` GCP project
- **Workload Identity**: GitHub Actions integration
- **Storage**: GCS buckets for data and state management

## CI/CD

GitHub Actions workflows handle:
- Automated testing with test count verification
- Docker image building
- GCP deployment
- Infrastructure provisioning

Recent CI/CD improvements include test count verification and enhanced stability.

## Contributing

1. Create feature branch
2. Run tests locally
3. Submit pull request
4. Ensure CI passes

## License

Internal project - All rights reserved.
