from unittest.mock import MagicMock, patch

import pytest
import yaml

from omni_comment.comments import create_blank_comment, edit_comment_body
from omni_comment.main import omni_comment


@pytest.fixture
def config_file(tmp_path):
    config = tmp_path / "omni-comment.yml"
    config.write_text(yaml.dump({"sections": ["test-section"]}))
    return str(config)


@pytest.fixture
def mock_github():
    with patch("omni_comment.main.Github") as mock:
        yield mock


@pytest.fixture
def mock_issue(mock_github):
    mock_repo = MagicMock()
    mock_issue = MagicMock()
    mock_github.return_value.get_repo.return_value = mock_repo
    mock_repo.get_issue.return_value = mock_issue
    return mock_issue


@pytest.mark.asyncio
async def test_should_fail_if_no_issue_number():
    with pytest.raises(AssertionError, match="Issue number is required"):
        await omni_comment(
            issue_number=0,
            repo="test-repo",
            section="test-section",
            token="faketoken",
        )


@pytest.mark.asyncio
async def test_should_create_new_comment_when_none_exists(config_file, mock_issue):
    mock_issue.get_comments.return_value = []
    mock_issue.create_reaction.return_value = MagicMock(delete=MagicMock())
    mock_comment = MagicMock(html_url="test-url", id=456)
    mock_issue.create_comment.return_value = mock_comment

    result = await omni_comment(
        config_path=config_file,
        issue_number=123,
        message="test message",
        repo="owner/repo",
        section="test-section",
        token="faketoken",
    )

    assert result is not None
    assert result.html_url == "test-url"
    assert result.id == 456
    assert result.status == "created"


@pytest.mark.asyncio
async def test_should_update_existing_comment(config_file, mock_github, mock_issue):
    blank_body = await create_blank_comment(config_file)
    existing_comment = MagicMock(body=blank_body, id=456, html_url="test-url")
    mock_issue.get_comments.return_value = [existing_comment]
    mock_issue.create_reaction.return_value = MagicMock(delete=MagicMock())

    mock_repo = mock_github.return_value.get_repo.return_value
    mock_repo.get_issue_comment.return_value = existing_comment

    result = await omni_comment(
        config_path=config_file,
        issue_number=123,
        message="updated message",
        repo="owner/repo",
        section="test-section",
        token="faketoken",
    )

    assert result is not None
    assert result.html_url == "test-url"
    assert result.id == 456
    assert result.status == "updated"
    existing_comment.edit.assert_called_once()


@pytest.mark.asyncio
async def test_should_noop_if_no_comment_and_empty_content(config_file, mock_issue):
    mock_issue.get_comments.return_value = []
    mock_issue.create_reaction.return_value = MagicMock(delete=MagicMock())

    result = await omni_comment(
        config_path=config_file,
        issue_number=123,
        message="",
        repo="owner/repo",
        section="test-section",
        token="faketoken",
    )

    assert result is None
    mock_issue.create_comment.assert_not_called()


@pytest.mark.asyncio
async def test_should_render_summary_details_when_title_specified(
    config_file, mock_issue
):
    mock_issue.get_comments.return_value = []
    mock_issue.create_reaction.return_value = MagicMock(delete=MagicMock())
    mock_comment = MagicMock(html_url="test-url", id=456)
    mock_issue.create_comment.return_value = mock_comment

    result = await omni_comment(
        config_path=config_file,
        issue_number=123,
        message="test message",
        repo="owner/repo",
        section="test-section",
        title="test title",
        token="faketoken",
    )

    assert result is not None
    assert result.status == "created"

    call_args = mock_issue.create_comment.call_args[0][0]
    assert "<details open>" in call_args
    assert "<summary><h2>test title</h2></summary>" in call_args


@pytest.mark.asyncio
async def test_can_render_collapsed_details(config_file, mock_issue):
    mock_issue.get_comments.return_value = []
    mock_issue.create_reaction.return_value = MagicMock(delete=MagicMock())
    mock_comment = MagicMock(html_url="test-url", id=456)
    mock_issue.create_comment.return_value = mock_comment

    await omni_comment(
        collapsed=True,
        config_path=config_file,
        issue_number=123,
        message="test message",
        repo="owner/repo",
        section="test-section",
        title="test title",
        token="faketoken",
    )

    call_args = mock_issue.create_comment.call_args[0][0]
    assert "<details>" in call_args
    assert "<details open>" not in call_args


class TestEditCommentBody:
    def test_replaces_section_content(self):
        body = "\n".join([
            '<!-- mskelton/omni-comment id="main" -->',
            "",
            '<!-- mskelton/omni-comment start="test" -->',
            "old content",
            '<!-- mskelton/omni-comment end="test" -->',
        ])

        result = edit_comment_body(body, "test", "new content")

        assert "new content" in result
        assert "old content" not in result

    def test_appends_when_section_not_found(self):
        body = '<!-- mskelton/omni-comment id="main" -->'

        result = edit_comment_body(body, "new-section", "new content")

        assert '<!-- mskelton/omni-comment start="new-section" -->' in result
        assert "new content" in result
        assert '<!-- mskelton/omni-comment end="new-section" -->' in result

    def test_wraps_in_details_with_title(self):
        body = '<!-- mskelton/omni-comment id="main" -->'

        result = edit_comment_body(body, "test", "content", title="My Title")

        assert "<details open>" in result
        assert "<summary><h2>My Title</h2></summary>" in result

    def test_collapsed_details(self):
        body = '<!-- mskelton/omni-comment id="main" -->'

        result = edit_comment_body(
            body, "test", "content", title="My Title", collapsed=True
        )

        assert "<details>" in result
        assert "<details open>" not in result
