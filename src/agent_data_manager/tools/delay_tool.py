import asyncio
import logging
import time

logger = logging.getLogger(__name__)


async def delay_tool(delay_ms: int = 1000) -> dict:
    """Waits for a specified number of milliseconds.

    Args:
        delay_ms: The delay duration in milliseconds.

    Returns:
        A dictionary confirming the delay duration.
    """
    logger.info(f"Executing delay tool with delay_ms={delay_ms}")
    start_time = time.monotonic()
    try:
        delay_sec = delay_ms / 1000.0
        if delay_sec < 0:
            return {"status": "failed", "error": "Delay must be non-negative."}
        await asyncio.sleep(delay_sec)
        end_time = time.monotonic()
        actual_delay_ms = round((end_time - start_time) * 1000, 2)
        msg = f"Delayed for approximately {actual_delay_ms} ms (requested {delay_ms} ms)"
        logger.info(msg)
        return {
            "status": "success",
            "result": {"message": msg, "requested_delay_ms": delay_ms, "actual_delay_ms": actual_delay_ms},
        }
    except Exception as e:
        logger.error(f"Error during delay: {e}", exc_info=True)
        return {"status": "failed", "error": f"Error during delay: {e}"}


# Example usage (can be run directly for testing)
# async def main():
#     result = await delay_tool(2000)
#     print(result)
#     result = await delay_tool(6000)
#     print(result)
#     result = await delay_tool(-100)
#     print(result)

# if __name__ == "__main__":
#     asyncio.run(main())
