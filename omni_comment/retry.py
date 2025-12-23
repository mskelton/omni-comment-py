import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


async def retry(
    operation: Callable[[int, int], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 1.0,
) -> T:
    """
    Retry an async operation with exponential backoff.

    Args:
        operation: Async function that takes (attempt, max_attempts) and returns T
        max_attempts: Maximum number of retry attempts
        delay: Initial delay in seconds between retries
    """
    attempt = 0

    while True:
        try:
            return await operation(attempt, max_attempts)
        except Exception as error:
            attempt += 1

            if attempt >= max_attempts:
                raise error

            current_delay = delay * (2 ** (attempt - 1))
            await asyncio.sleep(current_delay)
