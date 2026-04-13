"""Unit tests for inreach_parser."""

from src.inreach_parser import InReachRequest, parse_body

SAMPLE_BODY = """\
Wx now

View the location or send a reply to Jane Doe:
https://inreachlink.com/gifNuqslgVb6olfzfJevecA

Jane Doe sent this message from: Lat 47.756259 Lon -122.350252

Do not reply directly to this message.

This message was sent to you using the inReach two-way satellite communicator with GPS. To learn more, visit http://explore.garmin.com/inreach.
"""

MSG_ID = "<DMsYgc6IQqyfXwvT4ZoAfw@geopod-ismtpd-40>"


def test_parse_sample_body():
    result = parse_body(SAMPLE_BODY, MSG_ID)
    assert result is not None
    assert result.command == "wx now"
    assert result.latitude == 47.756259
    assert result.longitude == -122.350252
    assert result.message_id == MSG_ID
    assert result.reply_url == "https://inreachlink.com/gifNuqslgVb6olfzfJevecA"


def test_wx_now_uppercase():
    body = SAMPLE_BODY.replace("Wx now", "WX NOW")
    result = parse_body(body, MSG_ID)
    assert result is not None
    assert result.command == "wx now"


def test_wx_week():
    body = SAMPLE_BODY.replace("Wx now", "wx week")
    result = parse_body(body, MSG_ID)
    assert result is not None
    assert result.command == "wx week"


def test_wx_week_mixed_case():
    body = SAMPLE_BODY.replace("Wx now", "Wx Week")
    result = parse_body(body, MSG_ID)
    assert result is not None
    assert result.command == "wx week"


def test_unrecognized_command_returns_none():
    body = SAMPLE_BODY.replace("Wx now", "hello there")
    result = parse_body(body, MSG_ID)
    assert result is None


def test_empty_body_returns_none():
    result = parse_body("", MSG_ID)
    assert result is None


def test_latlon_extraction():
    result = parse_body(SAMPLE_BODY, MSG_ID)
    assert result is not None
    assert abs(result.latitude - 47.756259) < 1e-6
    assert abs(result.longitude - (-122.350252)) < 1e-6


def test_missing_latlon_returns_none():
    body = "wx now\n\nSome other content without coordinates."
    result = parse_body(body, MSG_ID)
    assert result is None
