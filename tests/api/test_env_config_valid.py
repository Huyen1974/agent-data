import os

import pytest
from dotenv import load_dotenv


@pytest.mark.unit
def test_env_config_valid():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..")
    env_sample_path = os.path.join(base_dir, ".env.sample")
    env_example_path = os.path.join(base_dir, ".env.example")

    env_path_to_load = None
    if os.path.exists(env_sample_path):
        env_path_to_load = env_sample_path
    elif os.path.exists(env_example_path):
        env_path_to_load = env_example_path

    assert (
        env_path_to_load is not None
    ), "Expected .env.sample or .env.example to exist in the project root"

    load_dotenv(env_path_to_load)
    required_keys = ["QDRANT_URL", "QDRANT_API_KEY"]
    for key in required_keys:
        assert (
            os.getenv(key) is not None
        ), f"Expected {key} in {os.path.basename(env_path_to_load)}"
