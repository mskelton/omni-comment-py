from .metadata import read_metadata
from .utils import Context


def _create_identifier(key: str, value: str) -> str:
    return f'<!-- mskelton/omni-comment {key}="{value}" -->'


async def find_comment(pr_number: int, ctx: Context):
    if ctx.logger:
        ctx.logger.debug("Searching for existing comment...")

    comment_tag_pattern = _create_identifier("id", "main")
    repo = ctx.github.get_repo(f"{ctx.repo.owner}/{ctx.repo.repo}")
    issue = repo.get_issue(pr_number)

    for comment in issue.get_comments():
        if comment.body and comment_tag_pattern in comment.body:
            return comment

    return None


async def create_comment(
    issue_number: int,
    title: str,
    section: str,
    content: str,
    collapsed: bool,
    config_path: str,
    ctx: Context,
):
    if ctx.logger:
        ctx.logger.debug("Creating comment...")

    repo = ctx.github.get_repo(f"{ctx.repo.owner}/{ctx.repo.repo}")
    issue = repo.get_issue(issue_number)

    body = edit_comment_body(
        body=await create_blank_comment(config_path),
        section=section,
        content=content,
        title=title,
        collapsed=collapsed,
    )

    comment = issue.create_comment(body)
    return comment


async def update_comment(
    comment_id: int,
    title: str,
    section: str,
    content: str,
    collapsed: bool,
    ctx: Context,
):
    if ctx.logger:
        ctx.logger.debug("Updating comment...")

    repo = ctx.github.get_repo(f"{ctx.repo.owner}/{ctx.repo.repo}")
    comment = repo.get_issue_comment(comment_id)

    if not comment.body:
        raise ValueError("Comment body is empty")

    new_body = edit_comment_body(
        body=comment.body,
        section=section,
        content=content,
        title=title,
        collapsed=collapsed,
    )

    comment.edit(new_body)
    return comment


async def create_blank_comment(config_path: str) -> str:
    metadata = await read_metadata(config_path)

    parts: list[str] = [_create_identifier("id", "main")]

    if metadata.title:
        parts.append(f"# {metadata.title}")

    if metadata.intro:
        parts.append(metadata.intro)

    for section in metadata.sections:
        parts.append(_create_identifier("start", section))
        parts.append(_create_identifier("end", section))

    return "\n\n".join(parts)


def edit_comment_body(
    body: str,
    section: str,
    content: str,
    title: str | None = None,
    collapsed: bool = False,
) -> str:
    lines = body.split("\n")
    start_marker = _create_identifier("start", section)
    end_marker = _create_identifier("end", section)

    start_index = next((i for i, line in enumerate(lines) if start_marker in line), -1)
    end_index = next((i for i, line in enumerate(lines) if end_marker in line), -1)

    if title:
        open_attr = "" if collapsed else " open"
        content = "\n".join(
            [
                f"<details{open_attr}>",
                f"<summary><h2>{title}</h2></summary>",
                "",
                content,
                "",
                "</details>",
            ]
        )

    # If the section is not found, append the content to the end of the comment
    # This is necessary as you add new comment sections
    if start_index == -1 or end_index == -1:
        return "\n".join(
            [
                *lines,
                "",
                start_marker,
                content,
                end_marker,
            ]
        )

    return "\n".join([*lines[: start_index + 1], content, *lines[end_index:]])
