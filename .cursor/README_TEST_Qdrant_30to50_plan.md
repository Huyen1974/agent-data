Nguyên tắc:

Thời gian: Hoàn thành trong 2 tuần (02/06/2025–16/06/2025, 10 CLI).
Tập trung: Hoàn thiện Agent Data (Knowledge Manager) với tích hợp Cursor qua MCP, API A2A cho CS Agent, observability cơ bản, metadata management, sử dụng Qdrant free tier (1 GB, us-east4-0, 210-305ms/call) và MacBook M1 (8-core CPU, 16GB RAM).
Loại bỏ: Không xem xét Vertex AI Vector Search/Embeddings.
Quy mô: Test nhỏ (8–50 documents), tránh quy mô lớn để không gây tắc nghẽn Qdrant free tier. Paid tier/test lớn có kế hoạch riêng.
Hạ tầng: Serverless (Cloud Functions, Cloud Run, Firestore, GCS), min-instances=0, Cursor chọn phương án phù hợp.
Rủi ro: Ngăn rate-limit, import errors, Firestore sync, MCP JSON, metrics propagation để tránh Cursor/Claude Sonnet 4 treo.
Tốc độ: CLI tinh gọn, mục tiêu rõ, test vừa đủ (>75% pass rate), tự động hóa nhật ký sớm.
Rủi ro & Giải pháp:

Qdrant Rate-limit:
Rủi ro: Timeout/hangs (CLI 119D4).
Giải pháp: Test 8–50 documents, timeout 10s, retry (0.5s, 1s, 2s), 350ms delay.
Import Errors:
Rủi ro: Subprocess import fails (CLI 119D5/D6).
Giải pháp: Chuẩn hóa package (CLI-120), test imports trước CI.
Firestore/GCS Sync:
Rủi ro: Metadata/vectorStatus không nhất quán.
Giải pháp: Sync logic đơn giản, test 8 documents, log errors.
MCP JSON Errors:
Rủi ro: Cursor prompt fails (CLI 119D6 echo test).
Giải pháp: Chuẩn hóa JSON schema, manual test trước.
Metrics Propagation:
Rủi ro: Cloud Function sai project/delay (CLI 119D6).
Giải pháp: Deploy trên chatgpt-db-project, fallback log vào GCS.
Kế hoạch CLI:

CLI 119D7: Metrics, Cursor Connectivity, Firestore Sync

Mục tiêu: Deploy metrics exporter, verify propagation, deploy alerting, test Cursor MCP stdio, implement Firestore sync.
Hành động:
Deploy Cloud Function qdrant-metrics-exporter (Python 3.10, asia-southeast1, gemini-service-account).
Verify metrics (qdrant_requests_total, documents_processed_total) in Cloud Monitoring.
Deploy alert_policy_latency.json (latency > 1s).
Test MCP stdio:
text

Thu gọn

Bọc lại

Sao chép
{"tool_name": "save_document", "kwargs": {"doc_id": "cursor_1", "content": "Test doc", "save_dir": "saved_documents"}}
{"tool_name": "semantic_search", "kwargs": {"query": "test", "limit": 5}}
Add Firestore sync (vectorStatus: pending → completed) in qdrant_vectorization_tool.
Test: 8 documents, >75% pass rate, 1 new test case (sync).
Hạ tầng: Cloud Function (exporter), Cloud Run (optional Gateway), Firestore (documents), GCS (agent-data-storage-test).
Kết quả: Metrics propagated, alerting deployed, Cursor pass 8/8, sync pass, cli119d7_all_green.
Rủi ro: Propagation delay (log to GCS), JSON errors (manual test).
CLI 119D8: Cursor Tích hợp, API A2A, Firestore Rules

Mục tiêu: Complete Cursor document storage, deploy API A2A, secure Firestore.
Hành động:
Test Cursor: Save document from IDE prompt → Agent Data (Qdrant/Firestore).
Deploy MCP Gateway (api_mcp_gateway.py) on Cloud Run (asia-southeast1).
Implement API A2A (/save, /query, /search) on Cloud Run, OpenAPI schema.
Deploy Firestore Rules:
text

Thu gọn

Bọc lại

Sao chép
match /documents/{docId} { allow read, write: if request.auth != null; }
match /agent_sessions/{sessionId} { allow read, write: if request.auth != null; }
Test: 10 queries (API), 8 documents (Cursor), >75% pass rate, 2 new test cases.
Hạ tầng: Cloud Run (Gateway, API), Firestore (documents, agent_sessions).
Kết quả: Cursor pass 8/8, API response <5s, Rules pass, cli119d8_all_green.
Rủi ro: Cursor latency (timeout 10s), Rules errors (test unauthorized access).
CLI 119D9: Metadata, Báo cáo, Nhật ký Tự động

Mục tiêu: Implement metadata logic, auto reporting, auto task report.
Hành động:
Add metadata in firestore_metadata_manager.py: versioning (version increment), hierarchy (level_1–level_6), auto-tagging (LLM, auto_tagging_tool).
Deploy Cloud Function change_report_function (Firestore trigger, JSON report).
Deploy write_task_report_function (GitHub API, update task_report.md).
Test: 8 documents (metadata), 10 changes (report), >75% pass rate, 2 new test cases.
Hạ tầng: Cloud Functions (reporting, task report), Firestore, GCS (backup).
Kết quả: Metadata pass 8/8, reports <5s, task report updated, cli119d9_all_green.
Rủi ro: Tagging latency (cache LLM results), GitHub rate-limit (retry).
CLI-120: Chuẩn hóa Package Python

Mục tiêu: Create editable package, fix import errors.
Hành động:
Create pyproject.toml:
text

Thu gọn

Bọc lại

Sao chép
[project]
name = "agent_data_manager"
version = "0.1.0"
dependencies = ["google-adk", "qdrant-client==1.14.*", "pydantic==2.11.*", "pytest"]
Structure: src/agent_data_manager/.
Update imports: from agent_data_manager.tools import save_document_tool.
Test CI: pip install -e ., pytest.
Test: 80/84 pass.
Hạ tầng: Local (MacBook M1, setup/venv), GitHub Actions.
Kết quả: Package installed, no import errors, CI pass, cli120_all_green.
Rủi ro: Import conflicts (review codebase), CI failure (verbose logs).
CLI-121: Latency Guard cho Qdrant Free Tier

Mục tiêu: Monitor Qdrant latency, reduce rate-limit risks.
Hành động:
Deploy Cloud Function latency_probe_function (hourly, log to logs/latency.log).
Set alert: P95 latency > 1s (email/Pub/Sub).
Add batch policy in qdrant_vectorization_tool: QDRANT_BATCH_SIZE=100, SLEEP=0.35s.
Test: 8 documents, >75% pass rate, 1 new test case.
Hạ tầng: Cloud Function (probe), Firestore (optional logs).
Kết quả: Latency <1s, batch pass 8/8, alert setup, cli121_all_green.
Rủi ro: Rate-limit (small batch, retry), probe failure (log to GCS).
CLI-122: EmbeddingProvider Interface

Mục tiêu: Abstract OpenAI embedding.
Hành động:
Define EmbeddingProvider:
text

Thu gọn

Bọc lại

Sao chép
class EmbeddingProvider(Protocol):
    async def embed(self, texts: List[str]) -> List[List[float]]: ...
Implement OpenAIEmbeddingProvider.
Update qdrant_vectorization_tool.
Test: 8 documents, >75% pass rate, 1 new test case.
Hạ tầng: Local, Cloud Functions (optional tool).
Kết quả: Embedding pass 8/8, cli122_all_green.
Rủi ro: Tool breakage (unit tests), latency (timeout 10s).
CLI-123: Session Memory, Pub/Sub A2A

Mục tiêu: Add session memory, Pub/Sub A2A.
Hành động:
Add agent_sessions collection (session ID, state).
Update event_manager.py for Pub/Sub (publish save_document events).
Test: 8 sessions, 10 events, >75% pass rate, 1 new test case.
Hạ tầng: Firestore (agent_sessions), Pub/Sub, Cloud Functions.
Kết quả: Sessions saved, events published, cli123_all_green.
Rủi ro: Pub/Sub latency (timeout 5s), session conflicts (unique IDs).
CLI-124: Logging Chuẩn hóa

Mục tiêu: Standardize logging, reduce costs.
Hành động:
Use structured_logger.py (JSON, 10% INFO sampling).
Log to logs/agent_server.log, error metrics to Cloud Monitoring.
Test: 10 logs, >75% pass rate, 1 new test case.
Hạ tầng: Cloud Logging, GCS (backup).
Kết quả: Logs standardized, costs < $1/day, cli124_all_green.
Rủi ro: High volume (sampling), format errors (validate JSON).
CLI-125: Cloud Workflows Orchestration

Mục tiêu: Automate ingestion/reporting workflows.
Hành động:
Create Workflow YAML: ingestion (save → vectorize → tag).
Deploy Workflow (asia-southeast1, gemini-service-account).
Test: 8 documents, >75% pass rate, 1 new test case.
Hạ tầng: Cloud Workflows, Cloud Functions.
Kết quả: Workflow pass 8/8, cli125_all_green.
Rủi ro: Timeout (limit steps), errors (retry).
CLI-126: Tài liệu, Testing Cơ bản

Mục tiêu: Complete documentation, basic E2E tests.
Hành động:
Update KH2_Grok Qdrant.txt, create Agent_Data_Final_Report.md.
Add E2E tests: Cursor → MCP → Qdrant/Firestore (8 documents).
Test: 80/84 pass, 2 new test cases.
Hạ tầng: Local, Firestore, Qdrant.
Kết quả: Docs complete, E2E pass 8/8, cli126_all_green.
Rủi ro: Test hangs (timeout 10s), doc gaps (review).
CLI-127: Firestore/GCS Backup

Mục tiêu: Setup Firestore/GCS backup for data safety.
Hành động:
Configure Firestore export (daily, agent-data-storage-test).
Setup GCS snapshot for Qdrant (qdrant-snapshots).
Test: 8 documents backup, >75% pass rate, 1 new test case.
Hạ tầng: Firestore, GCS.
Kết quả: Backup pass, cli127_all_green.
Rủi ro: Export failure (retry logic), storage costs (limit snapshots).
CLI-128: Tree View Backend

Mục tiêu: Implement Tree View backend (copy path, share content).
Hành động:
Add project_tree collection in Firestore.
Implement copy_path, share_content in project_tree_management_tool.
Test: 8 nodes, >75% pass rate, 1 new test case.
Hạ tầng: Firestore, Cloud Functions (tool).
Kết quả: Tree View pass, cli128_all_green.
Rủi ro: Tree conflicts (unique paths), latency (timeout 5s).
CLI-129: RAG Truy vấn Phức hợp

Mục tiêu: Support combined Qdrant/Firestore queries for RAG.
Hành động:
Update qdrant_search_tool for hybrid queries (vector + metadata).
Test: 8 queries, >75% pass rate, 1 new test case.
Hạ tầng: Qdrant, Firestore, Cloud Functions.
Kết quả: Queries pass 8/8, cli129_all_green.
Rủi ro: Query latency (timeout 10s), result mismatch (validate schema).
CLI-130: Observability Hoàn thiện

Mục tiêu: Finalize metrics, dashboards, alerting.
Hành động:
Update Pushgateway metrics (qdrant_*, business metrics).
Deploy dashboard in Cloud Monitoring.
Test: 10 metrics, >75% pass rate, 1 new test case.
Hạ tầng: Pushgateway, Cloud Monitoring.
Kết quả: Dashboard active, metrics pass, cli130_all_green.
Rủi ro: Metrics delay (log to GCS), dashboard errors (manual verify).
CLI-131: Testing Nâng cao

Mục tiêu: Add E2E/performance tests for stability.
Hành động:
Add E2E: Cursor → MCP → Qdrant/Firestore (10 documents).
Add performance: 50 queries (<10s).
Test: 80/84 pass, 2 new test cases.
Hạ tầng: Local, Qdrant, Firestore.
Kết quả: E2E pass, performance <10s, cli131_all_green.
Rủi ro: Hangs (timeout 10s), resource limits (small scale).
CLI-132: Tối ưu Chi phí

Mục tiêu: Optimize serverless costs.
Hành động:
Review Cloud Functions/Run usage, set min-instances=0.
Limit Firestore/GCS storage.
Test: Cost < $5/day, >75% pass rate, 1 new test case.
Hạ tầng: Cloud Functions, Cloud Run, Firestore, GCS.
Kết quả: Costs optimized, cli132_all_green.
Rủi ro: Overuse (monitor usage), misconfig (review IAM).
CLI-133: Qdrant Paid Tier Chuẩn bị

Mục tiêu: Plan Qdrant paid tier (Singapore).
Hành động:
Analyze costs (storage, API calls).
Test: 50 documents, >75% pass rate, 1 new test case.
Hạ tầng: Qdrant (free tier for test), Firestore.
Kết quả: Cost plan ready, cli133_all_green.
Rủi ro: Cost misestimate (small scale test), rate-limit (batch policy).
CLI-134: Qdrant Hybrid POC

Mục tiêu: Create POC for Qdrant hybrid (Cloud Run Docker).
Hành động:
Write qdrant_sync.py (pull GCS snapshot, restore Docker).
Test: 8 documents sync, >75% pass rate, 1 new test case.
Hạ tầng: Cloud Run (Docker), GCS (qdrant-snapshots).
Kết quả: POC pass, cli134_all_green.
Rủi ro: Sync failure (checksum verify), Docker latency (timeout 10s).
CLI-135: Auto Nhật ký CI/CD

Mục tiêu: Automate task_report.md updates.
Hành động:
Enhance write_task_report_function (GitHub API, CI trigger).
Test: 10 CI runs, >75% pass rate, 1 new test case.
Hạ tầng: Cloud Functions, GitHub Actions.
Kết quả: Task report auto-updated, cli135_all_green.
Rủi ro: API rate-limit (retry), CI failure (verbose logs).
CLI-136: Firestore Metadata Tối ưu

Mục tiêu: Optimize metadata queries.
Hành động:
Index level_1–level_6, version in Firestore.
Test: 10 queries, >75% pass rate, 1 new test case.
Hạ tầng: Firestore.
Kết quả: Queries <2s, cli136_all_green.
Rủi ro: Index overhead (limit fields), query errors (validate).
CLI-137: API A2A Mở rộng

Mục tiêu: Expand A2A for additional agents.
Hành động:
Add endpoints (/batch_save, /batch_query).
Test: 10 queries, >75% pass rate, 1 new test case.
Hạ tầng: Cloud Run, Firestore.
Kết quả: API pass, cli137_all_green.
Rủi ro: Latency (timeout 10s), schema errors (OpenAPI).
CLI-138: Tài liệu Cuối

Mục tiêu: Finalize project documentation.
Hành động:
Complete Agent_Data_Final_Report.md, update INTEGRATE_WITH_CURSOR.md.
Test: Docs verified, >75% pass rate, 1 new test case.
Hạ tầng: Local.
Kết quả: Docs complete, cli138_all_green.
Rủi ro: Missing details (review), format errors (manual check).
Lộ trình:

Tuần 1 (02-09/06): CLI 119D7–119D9, CLI-120–122, CLI-123–124.
Tuần 2 (10-16/06): CLI-125–138.
Hạ tầng Tổng quát:

Cloud Functions: Tools, metrics, reporting, task report, latency probe.
Cloud Run: MCP Gateway, API A2A (min-instances=0).
Firestore: documents, agent_sessions, project_tree (asia-southeast1).
GCS: agent-data-storage-test, qdrant-snapshots (asia-southeast1).
Qdrant: Free tier (us-east4-0, my_collection, 1536 dimensions).
Local: MacBook M1, setup/venv (Python 3.10.17).
