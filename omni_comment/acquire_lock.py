from contextlib import asynccontextmanager
from typing import AsyncIterator

from .retry import retry
from .utils import Context


@asynccontextmanager
async def acquire_lock(issue_id: int, ctx: Context) -> AsyncIterator[None]:
    """
    Acquire a lock on an issue using reactions to prevent race conditions.
    Uses the 'eyes' reaction as a mutex.
    """
    repo = ctx.github.get_repo(f"{ctx.repo.owner}/{ctx.repo.repo}")
    issue = repo.get_issue(issue_id)
    reaction = None

    async def try_acquire(attempt: int, max_attempts: int):
        nonlocal reaction
        if ctx.logger:
            ctx.logger.debug(
                f"Attempting to acquire lock (attempt {attempt + 1}/{max_attempts})..."
            )

        # Create a reaction to act as a lock
        reaction = issue.create_reaction("eyes")

        # PyGithub doesn't return status codes directly, so we check if reaction exists
        # The lock is considered acquired if we successfully created the reaction
        if reaction:
            if ctx.logger:
                ctx.logger.debug("Lock acquired")
            return reaction

        # If we're on the last attempt, try to unlock to prevent deadlock
        if attempt + 1 == max_attempts:
            await _unlock()

        raise RuntimeError("Lock not acquired")

    async def _unlock():
        nonlocal reaction
        if reaction and ctx.logger:
            ctx.logger.debug("Releasing lock...")
        if reaction:
            reaction.delete()

    await retry(try_acquire, max_attempts=7, delay=1.0)

    try:
        yield
    finally:
        await _unlock()
