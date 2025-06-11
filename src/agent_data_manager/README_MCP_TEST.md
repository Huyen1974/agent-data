# README: Testing Local MCP Server

This document describes how to run and manually test the `local_mcp_server.py`.

## Running the Server

Open a terminal, navigate to the `ADK/agent_data` directory, and run:

```bash
python3 local_mcp_server.py
```

The server will start and print log messages to stderr. It will wait for JSON input on stdin.

## Manual Testing

Once the server is running, you can send JSON requests directly via stdin. Each request must be a single line of valid JSON.

1.  **Paste the JSON** for the tool call you want to test into the terminal where the server is running.
2.  **Press Enter**.
3.  The server will process the request.
4.  The **result (or error)** will be printed to stdout as a JSON string.
5.  Log messages will appear on stderr.

## Example Tests

Here are a few examples you can paste directly into the running server's terminal:

1.  **Test `save_text`:**
    ```json
    {"tool_name": "save_text", "args": ["Testing MCP server connection!"]}
    ```
    *Expected stdout:* `{"result": "Saved text: Testing MCP server connection!"}`

2.  **Test `add_numbers`:**
    ```json
    {"tool_name": "add_numbers", "kwargs": {"number1": 15, "number2": 27.5}}
    ```
    *Expected stdout:* `{"result": 42.5}`

3.  **Test Non-existent Tool:**
    ```json
    {"tool_name": "non_existent_tool", "args": []}
    ```
    *Expected stdout:* `{"error": "Tool 'non_existent_tool' not found."}`

4.  **Test Invalid JSON:**
    ```
    This is not JSON
    ```
    *Expected stdout:* `{"error": "Invalid JSON input: Expecting value: line 1 column 1 (char 0)"}` (Error message might vary slightly)
