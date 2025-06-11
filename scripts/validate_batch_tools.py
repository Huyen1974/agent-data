import json
import sys
import os
import argparse


def load_tools_list(file_path: str) -> set:
    """Loads a list of tools from a JSON file."""
    try:
        with open(file_path, "r") as f:
            tools = json.load(f)
            if not isinstance(tools, list):
                print(f"Error: Content of {file_path} is not a JSON list.", file=sys.stderr)
                return set()
            return set(tools)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {file_path}", file=sys.stderr)
        return set()
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}", file=sys.stderr)
        return set()
    except Exception as e:
        print(f"Error loading {file_path}: {e}", file=sys.stderr)
        return set()


def validate_tools(input_tool_names: list, production_tools: set, test_only_tools: set) -> dict:
    """Validates a list of tool names against allowed and prohibited lists."""
    valid_tools = []
    invalid_tools = []
    prohibited_tools = []

    for tool_name in input_tool_names:
        if tool_name in test_only_tools:
            print(
                f"Warning: Tool '{tool_name}' is prohibited in production (found in test_only_tools.json).",
                file=sys.stderr,
            )
            prohibited_tools.append(tool_name)
        elif tool_name in production_tools:
            valid_tools.append(tool_name)
        else:
            print(
                f"Error: Tool '{tool_name}' is not recognized or not allowed in production (not in production_tools.json).",
                file=sys.stderr,
            )
            invalid_tools.append(tool_name)

    return {"valid_tools": valid_tools, "invalid_tools": invalid_tools, "prohibited_tools": prohibited_tools}


def main():
    parser = argparse.ArgumentParser(
        description="Validate tool names in a batch request against allowed/prohibited lists."
    )
    parser.add_argument(
        "input_json_string",
        type=str,
        help='A JSON string representing a list of tool names (e.g., \'["add_numbers", "delay"]\' )',
    )
    parser.add_argument(
        "--prod-config",
        type=str,
        default="config/production_tools.json",
        help="Path to the production tools config file.",
    )
    parser.add_argument(
        "--test-config",
        type=str,
        default="config/test_only_tools.json",
        help="Path to the test-only tools config file.",
    )

    args = parser.parse_args()

    # Load configuration files
    production_tools = load_tools_list(args.prod_config)
    test_only_tools = load_tools_list(args.test_config)

    if not production_tools:
        print("Error: Failed to load production tools list. Aborting.", file=sys.stderr)
        sys.exit(1)
    # Allow test_only_tools to be empty

    # Parse input JSON string
    try:
        input_tool_names = json.loads(args.input_json_string)
        if not isinstance(input_tool_names, list):
            raise ValueError("Input JSON string must be a list.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON string provided as input.", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate tools
    validation_result = validate_tools(input_tool_names, production_tools, test_only_tools)

    # Print the result as JSON to stdout
    print(json.dumps(validation_result, indent=2))


if __name__ == "__main__":
    main()
