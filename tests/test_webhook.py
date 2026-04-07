# pyright: reportPrivateUsage=false
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import discord as dc
import pytest
from githubkit.versions.latest.models import SimpleUser

from app.components.github_integration.webhooks import discussions, issues, prs
from app.components.github_integration.webhooks.utils import EmbedContent, Footer
from app.components.github_integration.webhooks.vouch import (
    extract_vouch_details,
    find_vouch_command,
    is_vouch_pr,
)

if TYPE_CHECKING:
    from app.bot import EmojiName


def make_user(
    login: str = "testuser",
    url: str = "https://github.com/testuser",
    avatar_url: str = "https://avatars.githubusercontent.com/u/1",
    user_type: str = "User",
    user_id: int = 1,
) -> SimpleUser:
    return Mock(
        SimpleUser,
        login=login,
        html_url=url,
        avatar_url=avatar_url,
        type=user_type,
        id=user_id,
    )


def make_pr(
    number: int = 1,
    title: str = "Test PR",
    state: str = "open",
    draft: bool = False,
    merged: bool = False,
    merged_at: str | None = None,
    html_url: str = "https://github.com/ghostty-org/ghostty/pull/1",
) -> prs.PRLike:
    return Mock(
        prs.PRLike,
        number=number,
        title=title,
        html_url=html_url,
        draft=draft,
        merged=merged,
        merged_at=merged_at,
        state=state,
    )


@pytest.mark.parametrize(
    ("body", "command"),
    [
        ("!vouch @user", "vouch"),
        ("!unvouch @user", "unvouch"),
        ("!denounce @user", "denounce"),
        ("!vouch @user thanks for contributing!", "vouch"),
        ("!denounce @user AI slop", "denounce"),
        ("!thanks @user", None),
        ("vouch @user", None),
        ("", None),
        ("!", None),
        ("! vouch @user", None),
        ("This person is cool!\n\n!vouch @user", None),
    ],
)
def test_find_vouch_command(body: str, command: str | None) -> None:
    assert find_vouch_command(body) == command


@pytest.mark.parametrize(
    ("pr_title", "sender_login", "sender_type", "expected_result"),
    [
        ("Update VOUCHED list", "ghostty-vouch[bot]", "Bot", True),
        ("Fix bug", "ghostty-vouch[bot]", "Bot", False),
        ("Update VOUCHED list", "human", "User", False),
        ("Add feature", "developer", "User", False),
        ("Some bot PR", "some-other-bot[bot]", "Bot", False),
        ("As a large language model, I cannot open PRs", "Copilot", "Bot", False),
        ("Update VOUCHED list", "Copilot", "Bot", False),
    ],
)
def test_is_vouch_pr(
    pr_title: str, sender_login: str, sender_type: str, expected_result: bool
) -> None:
    event = Mock(
        ("pull_request", "sender"),
        pull_request=make_pr(title=pr_title),
        sender=make_user(login=sender_login, user_type=sender_type),
    )
    assert is_vouch_pr(event) is expected_result


@pytest.mark.parametrize(
    ("body", "entity_id", "comment_id", "vouchee"),
    [
        (
            "Triggered by [comment](https://github.com/ghostty-org/ghostty/"
            "issues/9999#issuecomment-3210987654) from @barfoo.\n\nVouch: @foobar",
            9999,
            3210987654,
            "foobar",
        ),
        (
            "Triggered by [comment](https://github.com/ghostty-org/ghostty/"
            "pull/123#issuecomment-9876543210) from @reviewer.\n\nVouch: @contributor",
            123,
            9876543210,
            "contributor",
        ),
        (
            "Triggered by [comment](https://github.com/ghostty-org/ghostty/"
            "discussions/456#discussioncomment-12345) from @user.\n\nVouch: @vouchee",
            456,
            12345,
            "vouchee",
        ),
    ],
)
def test_extract_vouch_details_valid(
    body: str, entity_id: int, comment_id: int, vouchee: str
) -> None:
    result = extract_vouch_details(body)
    assert result is not None
    _, eid, cid, v = result
    assert eid == entity_id
    assert cid == comment_id
    assert v == vouchee


@pytest.mark.parametrize("body", [None, "Vouch: @foobar", "", "No URL here"])
def test_extract_vouch_details_invalid(body: str | None) -> None:
    assert extract_vouch_details(body) is None


@pytest.mark.parametrize(
    ("state", "draft", "merged", "expected"),
    [
        ("open", False, False, "pull_open"),
        ("open", True, False, "pull_draft"),
        ("closed", False, True, "pull_merged"),
        ("closed", False, False, "pull_closed"),
    ],
)
def test_pr_footer(state: str, draft: bool, merged: bool, expected: EmojiName) -> None:
    pr = make_pr(number=42, title="Test PR", state=state, draft=draft, merged=merged)
    assert prs.pr_footer(pr) == (expected, "PR #42: Test PR")


@pytest.mark.parametrize(
    ("hunk", "expected"),
    [
        (
            "@@ -1,3 +1,3 @@\n context line\n-old line\n+new line\n another context",
            "-old line\n+new line",
        ),
        ("@@ -1,3 +1,3 @@\n context line\nanother context\nmore context", ""),
        (
            "@@ -1,3 +1,3 @@\n context\n+new line 1\n+new line 2",
            "+new line 1\n+new line 2",
        ),
        (
            "@@ -1,3 +1,3 @@\n context\n-old line 1\n-old line 2",
            "-old line 1\n-old line 2",
        ),
    ],
)
def test_reduce_diff_hunk(hunk: str, expected: str) -> None:
    assert prs._reduce_diff_hunk(hunk) == expected


@pytest.mark.parametrize(
    ("state", "reason", "answer", "expected"),
    [
        ("open", None, None, "discussion"),
        (
            "open",
            None,
            "https://example.com#discussioncomment-1",
            "discussion_answered",
        ),
        (
            "closed",
            "resolved",
            "https://example.com#discussioncomment-1",
            "discussion_answered",
        ),
        ("closed", "outdated", None, "discussion_outdated"),
        ("closed", "duplicate", None, "discussion_duplicate"),
    ],
)
def test_discussion_emoji(
    state: str, reason: str | None, answer: str | None, expected: EmojiName
) -> None:
    disc = Mock(
        discussions.DiscussionLike,
        state=state,
        state_reason=reason,
        answer_html_url=answer,
    )
    assert discussions.get_discussion_emoji(disc) == expected


@pytest.mark.parametrize(
    ("state", "reason", "expected"),
    [
        ("open", None, "issue_open"),
        ("closed", "completed", "issue_closed_completed"),
        ("closed", "not_planned", "issue_closed_unplanned"),
        ("closed", "duplicate", "issue_closed_unplanned"),
    ],
)
def test_issue_emoji(state: str, reason: str | None, expected: EmojiName) -> None:
    issue = Mock(issues.IssueLike, state=state, state_reason=reason)
    assert issues.get_issue_emoji(issue) == expected


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "<div type='discussions-op-text'>\nActual content\n</div>",
            "\nActual content",
        ),
        ("Start<div type='discussions-op-text'>Middle</div>End", "StartMiddleEnd"),
        (None, None),
        ("No div tag here", "No div tag here"),
    ],
)
def test_remove_discussion_div(body: str | None, expected: str | None) -> None:
    assert issues.remove_discussion_div(body) == expected


@pytest.mark.parametrize(
    ("param_name", "expected_length"), [("body", 500), ("description", 4096)]
)
def test_embed_content_dict_with_body(param_name: str, expected_length: int) -> None:
    content = EmbedContent(
        title="Test Title",
        url="https://example.com",
        **{param_name: "test content" * 350},
    )
    result = content.dict
    assert result["title"] == "Test Title"
    assert result["url"] == "https://example.com"

    assert "description" in result
    desc = result["description"]
    assert desc is not None
    assert "test content" in desc
    assert len(desc) == expected_length


def test_embed_content_dict_no_body_or_description() -> None:
    content = EmbedContent(title="Test Title", url="https://example.com")
    assert "description" not in content.dict


def test_footer_dict() -> None:
    with patch(
        "app.components.github_integration.webhooks.utils.emojis"
    ) as mock_emojis:
        mock_emojis.return_value = {
            "issue_open": Mock(dc.Emoji, url="https://example.com/emoji.png")
        }

        footer = Footer("issue_open", "Issue #1: Test")
        result = footer.dict

        assert result["text"] == "Issue #1: Test"
        assert result["icon_url"] == "https://example.com/emoji.png"


def test_format_reviewer_team() -> None:
    team = Mock(())
    team.name = "core-team"
    event = Mock((), requested_team=team)
    assert prs._format_reviewer(event) == "the `core-team` team"


def test_format_reviewer_user() -> None:
    user = Mock(
        SimpleUser,
        model_dump=Mock(
            (),
            return_value={
                "login": "reviewer",
                "html_url": "https://github.com/reviewer",
                "avatar_url": "https://avatars.githubusercontent.com/u/1",
            },
        ),
    )
    event = Mock((), requested_reviewer=user)
    result = prs._format_reviewer(event)
    assert "reviewer" in result


def test_format_reviewer_none() -> None:
    assert prs._format_reviewer(Mock(())) == "`?`"
