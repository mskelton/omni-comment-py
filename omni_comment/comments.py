from .metadata import read_metadata
from .utils import Context


def _create_identifier(key: str, value: str) -> str:
    return f'<!-- mskelton/omni-comment {key}="{value}" -->'


def find_comment(pr_number: int, ctx: Context):
    if ctx.logger:
        ctx.logger.debug("Searching for existing comment...")

    comment_tag_pattern = _create_identifier("id", "main")
    url = f"/repos/{ctx.repo.owner}/{ctx.repo.repo}/issues/{pr_number}/comments"

    # Paginate through all comments
    page = 1
    while True:
        response = ctx.client.get(url, params={"page": page, "per_page": 100})
        response.raise_for_status()
        comments = response.json()

        if not comments:
            break

        for comment in comments:
            if comment.get("body") and comment_tag_pattern in comment["body"]:
                return comment

        page += 1

    return None


def create_comment(
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

    url = f"/repos/{ctx.repo.owner}/{ctx.repo.repo}/issues/{issue_number}/comments"

    body = edit_comment_body(
        body=create_blank_comment(config_path),
        section=section,
        content=content,
        title=title,
        collapsed=collapsed,
    )

    response = ctx.client.post(url, json={"body": body})
    response.raise_for_status()
    return response.json()


def update_comment(
    comment_id: int,
    title: str,
    section: str,
    content: str,
    collapsed: bool,
    ctx: Context,
):
    if ctx.logger:
        ctx.logger.debug("Updating comment...")

    url = f"/repos/{ctx.repo.owner}/{ctx.repo.repo}/issues/comments/{comment_id}"

    # Fetch the existing comment
    response = ctx.client.get(url)
    response.raise_for_status()
    comment = response.json()

    if not comment.get("body"):
        raise ValueError("Comment body is empty")

    new_body = edit_comment_body(
        body=comment["body"],
        section=section,
        content=content,
        title=title,
        collapsed=collapsed,
    )

    # Update the comment
    response = ctx.client.patch(url, json={"body": new_body})
    response.raise_for_status()
    return response.json()


def create_blank_comment(config_path: str) -> str:
    metadata = read_metadata(config_path)

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
