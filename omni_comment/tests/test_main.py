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


def make_mock_response(json_data, status_code=200):
    """Create a mock httpx response."""
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    return mock


@pytest.fixture
def mock_client():
    with patch("omni_comment.main.create_client") as mock:
        client = MagicMock()
        mock.return_value.__enter__.return_value = client
        mock.return_value.__exit__.return_value = None
        yield client


def test_should_fail_if_no_issue_number():
    with pytest.raises(AssertionError, match="Issue number is required"):
        omni_comment(
            issue_number=0,
            repo="test-repo",
            section="test-section",
            token="faketoken",
        )


def test_should_create_new_comment_when_none_exists(config_file, mock_client):
    # Mock lock acquisition (201 = created)
    mock_client.post.side_effect = [
        make_mock_response({"id": 1}, status_code=201),  # lock acquired
        make_mock_response({"id": 456, "html_url": "test-url"}),  # create comment
    ]
    # No existing comments
    mock_client.get.return_value = make_mock_response([])
    # Lock release
    mock_client.delete.return_value = make_mock_response({})

    result = omni_comment(
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


def test_should_update_existing_comment(config_file, mock_client):
    blank_body = create_blank_comment(config_file)
    existing_comment = {"id": 456, "html_url": "test-url", "body": blank_body}

    # Mock lock acquisition
    mock_client.post.return_value = make_mock_response({"id": 1}, status_code=201)

    # First get returns list of comments, second returns the specific comment
    mock_client.get.side_effect = [
        make_mock_response([existing_comment]),  # find_comment
        make_mock_response(existing_comment),  # update_comment fetch
    ]

    # Mock update
    mock_client.patch.return_value = make_mock_response(
        {"id": 456, "html_url": "test-url"}
    )
    mock_client.delete.return_value = make_mock_response({})

    result = omni_comment(
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
    mock_client.patch.assert_called_once()


def test_should_noop_if_no_comment_and_empty_content(config_file, mock_client):
    # Mock lock acquisition
    mock_client.post.return_value = make_mock_response({"id": 1}, status_code=201)
    # No existing comments
    mock_client.get.return_value = make_mock_response([])
    mock_client.delete.return_value = make_mock_response({})

    result = omni_comment(
        config_path=config_file,
        issue_number=123,
        message="",
        repo="owner/repo",
        section="test-section",
        token="faketoken",
    )

    assert result is None
    # Only one post call for lock, not for creating comment
    assert mock_client.post.call_count == 1


def test_should_render_summary_details_when_title_specified(config_file, mock_client):
    # Mock lock acquisition
    mock_client.post.side_effect = [
        make_mock_response({"id": 1}, status_code=201),  # lock
        make_mock_response({"id": 456, "html_url": "test-url"}),  # create comment
    ]
    mock_client.get.return_value = make_mock_response([])
    mock_client.delete.return_value = make_mock_response({})

    result = omni_comment(
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

    # Check the body passed to create_comment
    call_args = mock_client.post.call_args_list[1]
    body = call_args.kwargs["json"]["body"]
    assert "<details open>" in body
    assert "<summary><h2>test title</h2></summary>" in body


def test_can_render_collapsed_details(config_file, mock_client):
    # Mock lock acquisition
    mock_client.post.side_effect = [
        make_mock_response({"id": 1}, status_code=201),  # lock
        make_mock_response({"id": 456, "html_url": "test-url"}),  # create comment
    ]
    mock_client.get.return_value = make_mock_response([])
    mock_client.delete.return_value = make_mock_response({})

    omni_comment(
        collapsed=True,
        config_path=config_file,
        issue_number=123,
        message="test message",
        repo="owner/repo",
        section="test-section",
        title="test title",
        token="faketoken",
    )

    call_args = mock_client.post.call_args_list[1]
    body = call_args.kwargs["json"]["body"]
    assert "<details>" in body
    assert "<details open>" not in body


class TestEditCommentBody:
    def test_replaces_section_content(self):
        body = "\n".join(
            [
                '<!-- mskelton/omni-comment id="main" -->',
                "",
                '<!-- mskelton/omni-comment start="test" -->',
                "old content",
                '<!-- mskelton/omni-comment end="test" -->',
            ]
        )

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
