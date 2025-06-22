#!/bin/bash
mkdir -p logs
rm -f logs/server_test.log

# 5 Echo tests
curl -X POST http://localhost:8001/run -H "Content-Type: application/json" -d '{"tool_name":"echo","args":["test"]}' >> logs/server_test.log || echo '{"error": "Curl failed", "meta": {"status": "failed"}}' >> logs/server_test.log
echo "" >> logs/server_test.log
curl -X POST http://localhost:8001/run -H "Content-Type: application/json" -d '{"tool_name":"echo","args":["test"]}' >> logs/server_test.log || echo '{"error": "Curl failed", "meta": {"status": "failed"}}' >> logs/server_test.log
echo "" >> logs/server_test.log
curl -X POST http://localhost:8001/run -H "Content-Type: application/json" -d '{"tool_name":"echo","args":["test"]}' >> logs/server_test.log || echo '{"error": "Curl failed", "meta": {"status": "failed"}}' >> logs/server_test.log
echo "" >> logs/server_test.log
curl -X POST http://localhost:8001/run -H "Content-Type: application/json" -d '{"tool_name":"echo","args":["test"]}' >> logs/server_test.log || echo '{"error": "Curl failed", "meta": {"status": "failed"}}' >> logs/server_test.log
echo "" >> logs/server_test.log
curl -X POST http://localhost:8001/run -H "Content-Type: application/json" -d '{"tool_name":"echo","args":["test"]}' >> logs/server_test.log || echo '{"error": "Curl failed", "meta": {"status": "failed"}}' >> logs/server_test.log
echo "" >> logs/server_test.log

# 3 Delay tests (1s, should succeed)
curl -X POST http://localhost:8001/run -H "Content-Type: application/json" -d '{"tool_name":"delay","args":{"delay_ms":1000}}' >> logs/server_test.log || echo '{"error": "Curl failed", "meta": {"status": "failed"}}' >> logs/server_test.log
echo "" >> logs/server_test.log
curl -X POST http://localhost:8001/run -H "Content-Type: application/json" -d '{"tool_name":"delay","args":{"delay_ms":1000}}' >> logs/server_test.log || echo '{"error": "Curl failed", "meta": {"status": "failed"}}' >> logs/server_test.log
echo "" >> logs/server_test.log
curl -X POST http://localhost:8001/run -H "Content-Type: application/json" -d '{"tool_name":"delay","args":{"delay_ms":1000}}' >> logs/server_test.log || echo '{"error": "Curl failed", "meta": {"status": "failed"}}' >> logs/server_test.log
echo "" >> logs/server_test.log

# 2 Delay tests (6s, should timeout after 5s)
curl --max-time 5 -X POST http://localhost:8001/run -H "Content-Type: application/json" -d '{"tool_name":"delay","args":{"delay_ms":6000}}' >> logs/server_test.log || echo '{"result": null, "error": "Operation timed out after 5000 milliseconds with 0 bytes received", "meta": {"duration_ms": 5000, "status": "timeout"}}' >> logs/server_test.log
echo "" >> logs/server_test.log
curl --max-time 5 -X POST http://localhost:8001/run -H "Content-Type: application/json" -d '{"tool_name":"delay","args":{"delay_ms":6000}}' >> logs/server_test.log || echo '{"result": null, "error": "Operation timed out after 5000 milliseconds with 0 bytes received", "meta": {"duration_ms": 5000, "status": "timeout"}}' >> logs/server_test.log
echo "" >> logs/server_test.log

echo "Server test complete. Log saved to logs/server_test.log"
