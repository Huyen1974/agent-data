#!/bin/bash
python3 "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/mcp/local_mcp_server.py" << EOF
$(python3 -c "import json; vector = [1.0] * 1536; print(json.dumps({\"tool\": \"save_metadata_to_faiss\", \"input\": {\"index_name\": \"test_index\", \"metadata_dict\": {\"doc1\": \"Test doc\"}, \"vector_data\": [vector]}}))")
$(python3 -c "import json; print(json.dumps({\"tool\": \"load_metadata_from_faiss\", \"input\": {\"index_name\": \"test_index\"}}))")
$(python3 -c "import json; vector = [1.0] * 1536; print(json.dumps({\"tool\": \"query_metadata_faiss\", \"input\": {\"index_name\": \"test_index\", \"query_vector\": [vector]}}))")
{"action": "exit"}
EOF
