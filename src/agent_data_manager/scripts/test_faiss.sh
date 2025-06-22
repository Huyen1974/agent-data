#!/bin/bash
# Script to send JSON with 1536-dimension vector in one server session
# Patch save_metadata_to_faiss_tool.py to log paths and save to /tmp
sed -i "" "s|faiss.write_index(index, local_index_path)|print(\"Saving FAISS index to: \" + local_index_path); faiss.write_index(index, local_index_path)|g" "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tools/save_metadata_to_faiss_tool.py" &&
sed -i "" "s|with open(local_metadata_path, \"wb\") as f:|print(\"Saving metadata to: \" + local_metadata_path); with open(local_metadata_path, \"wb\") as f:|g" "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tools/save_metadata_to_faiss_tool.py" &&
sed -i "" "s|local_index_path = .*$|local_index_path = \"/tmp/test_index.faiss\"|g" "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tools/save_metadata_to_faiss_tool.py" &&
sed -i "" "s|local_metadata_path = .*$|local_metadata_path = \"/tmp/test_index.meta\"|g" "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tools/save_metadata_to_faiss_tool.py" &&
# Patch load_metadata_from_faiss_tool.py to read from /tmp
sed -i "" "s|faiss.read_index\(.*\)|print(\"Loading FAISS index from: /tmp/test_index.faiss\"); faiss.read_index(\"/tmp/test_index.faiss\")|g" "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tools/load_metadata_from_faiss_tool.py" &&
sed -i "" "s|os.path.join\(.*\).meta.*|\"/tmp/test_index.meta\"|g" "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tools/load_metadata_from_faiss_tool.py" &&
# Patch query_metadata_faiss_tool.py to read from /tmp and fix NameError
sed -i "" "s|faiss.read_index\(.*\)|faiss.read_index(\"/tmp/test_index.faiss\")|g" "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tools/query_metadata_faiss_tool.py" &&
sed -i "" "s|\"status\": \"error\" if \"error\" in result else \"success\"|\"status\": \"error\" if \"error\" in results else \"success\"|g" "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tools/query_metadata_faiss_tool.py" &&
python3 "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/mcp/local_mcp_server.py" << EOF
$(python3 -c "import json; vector = [1.0] * 1536; print(json.dumps({\"tool\": \"save_metadata_to_faiss\", \"input\": {\"index_name\": \"test_index\", \"metadata_dict\": {\"doc1\": \"Test doc\"}, \"vector_data\": [vector]}}))")
$(python3 -c "import json; print(json.dumps({\"tool\": \"load_metadata_from_faiss\", \"input\": {\"index_name\": \"test_index\"}}))")
$(python3 -c "import json; vector = [1.0] * 1536; print(json.dumps({\"tool\": \"query_metadata_faiss\", \"input\": {\"index_name\": \"test_index\", \"query_vector\": [vector]}}))")
{"action": "exit"}
EOF
