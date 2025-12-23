from contextlib import contextmanager
from typing import Iterator

from .retry import retry
from .utils import Context


@contextmanager
def acquire_lock(issue_id: int, ctx: Context) -> Iterator[None]:
    """
    Acquire a lock on an issue using reactions to prevent race conditions.
    Uses the 'eyes' reaction as a mutex.
    """
    url = f"/repos/{ctx.repo.owner}/{ctx.repo.repo}/issues/{issue_id}/reactions"
    reaction_id: int | None = None

    def try_acquire(attempt: int, max_attempts: int):
        nonlocal reaction_id
        if ctx.logger:
            ctx.logger.debug(
                f"Attempting to acquire lock (attempt {attempt + 1}/{max_attempts})..."
            )

        # Create a reaction to act as a lock
        response = ctx.client.post(url, json={"content": "eyes"})
        data = response.json()
        reaction_id = data.get("id")

        # Check if the reaction was newly created (201) vs already existed (200)
        if response.status_code == 201:
            if ctx.logger:
                ctx.logger.debug("Lock acquired")
            return

        # If we're on the last attempt, try to unlock to prevent deadlock
        if attempt + 1 == max_attempts:
            _unlock()

        raise RuntimeError("Lock not acquired")

    def _unlock():
        nonlocal reaction_id
        if reaction_id:
            if ctx.logger:
                ctx.logger.debug("Releasing lock...")
            delete_url = f"/repos/{ctx.repo.owner}/{ctx.repo.repo}/issues/{issue_id}/reactions/{reaction_id}"
            ctx.client.delete(delete_url)

    retry(try_acquire, max_attempts=7, delay=1.0)

    try:
        yield
    finally:
        _unlock()
