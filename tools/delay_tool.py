import time
from typing import Any


def delay_tool(params: dict[str, Any]) -> dict[str, Any]:
    delay_seconds = min(float(params.get("delay", 2.0)), 2.0)
    time.sleep(delay_seconds)
    return {"status": "success", "delay_applied": delay_seconds}
