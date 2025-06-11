──────────────────────────────────────────────────────────────────────────────
PLAN – VectorDB & Qdrant v1.1  (FINAL after Grok feedback)
──────────────────────────────────────────────────────────────────────────────
TAG HIỆN TẠI : cli_cleanup_all_green
TEST PASS    : 49/49 (47 pass, 2 skip @slow)

╭────────┬──────────────────────────────┬────────────────────────────────────╮
│ GĐ     │  MỤC TIÊU                    │  CLI CHI TIẾT (Δ test)            │
├────────┼──────────────────────────────┼────────────────────────────────────┤
│ G1     │ Hardening & Completion       │ 102B_env_test          (+1 ➜ 50)  │
│        │ • đạt 50 test                │ 103A_slow_pipeline     (+0)       │
│        │ • CI @slow + drift check     │                                    │
├────────┼──────────────────────────────┼────────────────────────────────────┤
│ G2     │ Feature gaps                 │ 104A_vector_delete      (+0)      │
│        │ • API DELETE_BY_TAG          │ 104B_test_delete_tag    (+1)      │
│        │ • TTL placeholder            │                                    │
├────────┼──────────────────────────────┼────────────────────────────────────┤
│ G3     │ Performance / Bulk           │ 105A_bulk_upsert        (+0)      │
│        │ • batch upsert 1000 pts      │ 105B_test_bulk_upsert   (+1)      │
│        │ • asyncio parallel search    │ 106A_async_search       (+0)      │
│        │                              │ 106B_test_async_perf    (+1)      │
├────────┼──────────────────────────────┼────────────────────────────────────┤
│ G4     │ Observability & Migration    │ 107A_metrics_middleware (+0)      │
│        │ • Prom metrics + tracing     │ 107B_test_metrics       (+1)      │
│        │ • FAISS→Qdrant migrate tool  │ 108A_migration_cli      (+0)      │
│        │ • Smoke-test migration       │ 108B_test_migration     (+1)      │
╰────────┴──────────────────────────────┴────────────────────────────────────╯
*Sau G4*: tag **v1.1_qdrant_ready**; chuyển block Firestore sync.

BỔ SUNG - CHIA NHỎ CLI 103A

──────────────────────────────────────────────────────────────────────────────
REVISED MICRO-ROADMAP FOR CLI 103A (split into 6 sub-steps)
──────────────────────────────────────────────────────────────────────────────
Mốc trước: cli102b_all_green   •   Tests: 50/50 pass

┌─────┬────────────┬───────────────────────────┬───────────────┐
│ ID  │  MỤC TIÊU  │  NHIỆM VỤ CHÍNH           │ KẾT QUẢ/TAG    │
├─────┼────────────┼───────────────────────────┼───────────────┤
│103A1│ **Fix syntax**        │• Sửa IndentationError trong   │cli103a1_all_green│
│     │ (blocking errors)     │  ADK/agent_data/mcp/…          │                 │
│     │                       │• pytest -q 50/50               │                 │
├─────┼────────────┼───────────────────────────┼───────────────┤
│103A2│ **Portable drift hook**│• Refactor .pre-commit hook    │cli103a2_all_green│
│     │                       │  check_fixture_drift.py dùng   │                 │
│     │                       │  `$PRE_COMMIT_TOP_LEVEL`       │                 │
│     │                       │• Thêm README note; pytest ok   │                 │
├─────┼────────────┼───────────────────────────┼───────────────┤
│103A3│ **Flake8 pass – Part1**│• Fix flake8 F/E in            │cli103a3_all_green│
│     │ (small files)         │  local_mcp_server.py,          │                 │
│     │                       │  web_server.py                 │                 │
├─────┼────────────┼───────────────────────────┼───────────────┤
│103A4│ **Flake8 pass – Part2**│• Fix flake8 lỗi lớn trong     │cli103a4_all_green│
│     │ (big file)            │  query_metadata_faiss_tool.py  │                 │
├─────┼────────────┼───────────────────────────┼───────────────┤
│103A5│ **Flake8 pass – Rest** │• Quét & sửa F401/F841 nhỏ     │cli103a5_all_green│
│     │                       │  còn lại (tools/, tests/)      │                 │
├─────┼────────────┼───────────────────────────┼───────────────┤
│103A6│ **Finalize 103A**      │• Update README_PLAN.md        │cli103a_all_green │
│     │                       │• pytest -q 50/50               │(meta-tag)       │
│     │                       │• commit, tag, .cursor log      │                 │
└─────┴────────────┴───────────────────────────┴───────────────┘

──────────────────────────────────────────────────────────────────────────────
HƯỚNG DẪN CHUNG CHO MỌI PROMPT 103A*
──────────────────────────────────────────────────────────────────────────────
* Always try `edit_file`. **If it fails** (timeout / buffer limit), fall back
  to:
  `sed -i '' -e '<pattern>' <file>`
  Afterwards, run `git diff --staged` to verify the change.

* Each sub-CLI:
  1. Checkout new branch `cli103aX`.
  2. Run `pytest -q` → expect 50/50 pass.
  3. `git add` only modified files.
  4. `git commit -m "CLI103AX: <summary>"`.
  5. `git tag cli103aX_all_green`.
  6. Write 5-line summary to `.cursor/CLI103AX_all_green.txt`.

* Pre-commit hooks (added in 103A2):
```yaml
repos:
  - repo: local
    hooks:
      - id: flake8
        entry: flake8 .
      - id: py_compile
        entry: python -m py_compile $(git ls-files '*.py')
      - id: check_fixture_drift
        entry: python scripts/check_fixture_drift.py


──────────────────────────────────────────────────────────────────────────────
CLI DETAILS
──────────────────────────────────────────────────────────────────────────────

### CLI 102B_env_test (auto-run)
CONTEXT   : branch cli_cleanup_all_green → checkout -b cli102b
GOAL      : +1 test → 50/50; kiểm .env.sample.
TASKS
1) set tests/test__meta_count.py → EXPECTED_TOTAL_TESTS = 50
2) add tests/api/test_env_config_valid.py (load .env.sample, assert QDRANT_URL &
   QDRANT_API_KEY).
3) pytest -q  ⇒ 50/50 green.
4) git add tests/*
5) git commit -m "CLI102B: add env config test → 50 tests"
6) git tag cli102b_all_green
7) echo summary > .cursor/CLI102B_all_green.txt
VALIDATION: pytest green; tag exists.

### CLI 103A_slow_pipeline (auto-run)
CONTEXT   : branch cli102b_all_green → checkout -b cli103a
GOAL      : CI @slow weekly, flake8 & py_compile pre-commit, drift-check script,
            update README plan.
TASKS
1) .github/workflows/slow-tests.yml  (cron "0 3 * * 1")
   steps: run pytest -m slow; on failure notify via Actions summary.
2) extend .pre-commit-config.yaml:
   • flake8 .
   • python -m py_compile $(git ls-files '*.py')
3) scripts/check_fixture_drift.py:
   – introspect FakeQdrantClient / firestore_fake.py vs real client classes
     (inspect.signature) → report mismatch.
4) hook script into pre-commit (args: --fail-on-drift).
5) run pre-commit -a ; pytest -q 50/50.
6) docs: update README_TEST_Qdrant_30to50_plan.md (status 50 tests,
   removed 102A, new roadmap).
7) git add .github/workflows scripts/ .pre-commit-config.yaml docs/ README*
8) git commit -m "CLI103A: slow pipeline, drift check, flake8, docs update"
9) git tag cli103a_all_green
10) echo summary > .cursor/CLI103A_all_green.txt
VALIDATION: pre-commit passes; act workflow lint OK; pytest fast suite green.

### CLI 104A_vector_delete (auto-run)
CONTEXT   : branch cli103a_all_green → checkout -b cli104a
GOAL      : implement DELETE_BY_TAG endpoint.
TASKS
1) run scripts/check_fixture_drift.py (fail if drift).
2) code api/qdrant_store.py → def delete_by_tag(tag).
3) route DELETE /vectors?tag=…
4) update OpenAPI docs.
5) py_compile, flake8, pytest 50/50.
6) git add api/ app/ docs/
7) git commit -m "CLI104A: implement delete_by_tag"
8) git tag cli104a_all_green
9) echo summary > .cursor/CLI104A_all_green.txt

### CLI 104B_test_delete_tag (auto-run)
CONTEXT   : branch cli104a_all_green → checkout -b cli104b
GOAL      : add delete_by_tag test, meta-count 51.
TASKS
1) new tests/api/test_delete_by_tag.py
2) set tests/test__meta_count.py → 51
3) pytest -q ⇒ 51/51
4) git add tests/*
5) git commit -m "CLI104B: delete_by_tag test → 51 tests"
6) git tag cli104b_all_green
7) echo summary > .cursor/CLI104B_all_green.txt
VALIDATION: pytest green; meta-count correct.

### CLI 105A_bulk_upsert … (same 9-step pattern; run drift check first)
### CLI 105B_test_bulk_upsert … (+1 test → 52)
### CLI 106A_async_search …
### CLI 106B_test_async_perf … (+1 test → 53)
### CLI 107A_metrics_middleware …
### CLI 107B_test_metrics … (+1 test → 54)
### CLI 108A_migration_cli …
### CLI 108B_test_migration … (+1 test → 55)

──────────────────────────────────────────────────────────────────────────────
NOTES
──────────────────────────────────────────────────────────────────────────────
• Mỗi “A-prep” chạy scripts/check_fixture_drift.py trước khi sửa code.
• EXPECTED_TOTAL_TESTS cập nhật trong mọi “B-test”, kèm pytest assert.
• Tag chuẩn: <cliNN[a|b]_all_green>.  Báo cáo tóm tắt ghi .cursor/<TAG>.txt.
• CI fast suite luôn < 10 s; cron @slow bảo vệ perf / delay tool.



# Các lưu ý bổ sung trong quá trình thực hiện:
Các CLI con đề xuất Chia nhỏ CLI 103A
1. CLI 103A1: Sửa hook check-fixture-drift để chạy đúng scripts/check_fixture_drift.py bằng cách cải thiện portability (dùng git rev-parse hoặc language: python).

  Đề xuất bổ sung trước CLI 103A2:
Để đảm bảo mọi thứ ổn định trước khi soạn CLI 103A2, tôi đề xuất hai CLI con bổ sung để khắc phục test fail và cải thiện hook check-fixture-drift, sau đó tiếp tục với các nhiệm vụ còn lại của CLI 103A:
  1. CLI 103A1.1: Sửa lỗi test test_clear_embeddings để đạt 50/50 pass bằng cách:
    - Kiểm tra phiên bản qdrant-client và pydantic, thử tạo PointsSelector khác cách (e.g., dùng points=[] thay vì filter).
    - Nếu không được, sửa FakeQdrantClient.delete_points để bỏ qua PointsSelector và xóa tất cả điểm trực tiếp.
  2. CLI 103A1.2: Cải thiện hook check-fixture-drift để portable (dùng language: python hoặc sửa CWD), loại bỏ absolute path cứng.
  3. CLI 103A2-103A6: Tiếp tục như kế hoạch (sửa IndentationError, lỗi flake8, tài liệu).
-------
2. CLI 103A2: Sửa IndentationError trong ADK/agent_data/mcp/local_mcp_server.py bằng sed -i nếu edit_file tiếp tục thất bại.
3. CLI 103A3: Sửa lỗi flake8 trong ADK/agent_data/mcp/local_mcp_server.py và mcp/web_server.py (các file đã gần hoàn thiện).
4. CLI 103A4: Sửa lỗi flake8 trong ADK/agent_data/tools/query_metadata_faiss_tool.py (file lớn, cần chia nhỏ hơn nếu thất bại).
5. CLI 103A5: Sửa lỗi flake8 còn lại trong ADK/agent_data/tools/* và tests/* (tập trung vào F401, F841 nhỏ).
6. CLI 103A6: Cập nhật README_TEST_Qdrant_30to50_plan.md, chạy pytest -q, commit tất cả thay đổi, tag cli103a_all_green, và tạo .cursor/CLI103A_all_green.txt.
