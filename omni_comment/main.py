from dataclasses import dataclass
from typing import Literal

from github import Github

from .acquire_lock import acquire_lock
from .comments import create_comment, find_comment, update_comment
from .logger import Logger
from .utils import Context, parse_repo


@dataclass
class OmniCommentResult:
    html_url: str
    id: int
    status: Literal["created", "updated"]


async def omni_comment(
    *,
    issue_number: int,
    repo: str,
    section: str,
    token: str,
    collapsed: bool = False,
    config_path: str = "omni-comment.yml",
    logger: Logger | None = None,
    message: str | None = None,
    title: str | None = None,
) -> OmniCommentResult | None:
    assert issue_number, "Issue number is required"
    assert repo, "Repo is required"
    assert section, "Section is required"
    assert token, "Token is required"

    ctx = Context(
        github=Github(token),
        repo=parse_repo(repo),
        logger=logger,
    )

    # Acquire a lock on the issue to prevent race conditions
    async with acquire_lock(issue_number, ctx):
        comment = await find_comment(issue_number, ctx)

        if comment:
            updated = await update_comment(
                comment.id,
                title or "",
                section,
                message or "",
                collapsed,
                ctx,
            )
            return OmniCommentResult(
                html_url=updated.html_url,
                id=updated.id,
                status="updated",
            )
        elif message:
            created = await create_comment(
                issue_number,
                title or "",
                section,
                message,
                collapsed,
                config_path,
                ctx,
            )
            return OmniCommentResult(
                html_url=created.html_url,
                id=created.id,
                status="created",
            )

    return None
