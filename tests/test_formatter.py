"""Unit tests for formatter validation logic."""

from src.formatter import validate_message


def test_valid_message():
    msg = "Td Sun 74 Tn Clr 57 Wed PCldy 68 WedN Clr 52"
    valid, reason = validate_message(msg)
    assert valid is True
    assert reason == ""


def test_message_over_160_chars():
    msg = "Td RnShw 58% 57 Tn RnShw 39% 41 Wed ChRn 40% 55 " + "A" * 120
    assert len(msg) > 160
    valid, reason = validate_message(msg)
    assert valid is False
    assert "Too long" in reason


def test_message_without_temperature():
    msg = "Td Sun Clr Wed PCldy"
    valid, reason = validate_message(msg)
    assert valid is False
    assert "temperature" in reason.lower()


def test_message_without_day_abbreviation():
    msg = "74 57 68 52 clear skies ahead"
    valid, reason = validate_message(msg)
    assert valid is False
    assert "day" in reason.lower()


def test_exactly_160_chars():
    # Build a valid message that is exactly 160 chars
    base = "Td Sun 74 Tn Clr 57"  # 20 chars
    padding = " " + "x" * (160 - len(base) - 1)
    msg = base + padding
    assert len(msg) == 160
    valid, reason = validate_message(msg)
    assert valid is True
    assert reason == ""


def test_161_chars_fails():
    base = "Td Sun 74 Tn Clr 57"  # 20 chars
    padding = " " + "x" * (161 - len(base) - 1)
    msg = base + padding
    assert len(msg) == 161
    valid, reason = validate_message(msg)
    assert valid is False
    assert "Too long" in reason


def test_wx_now_with_precip():
    msg = "Td RnShw 58% 57 Tn RnShw 39% 41 Wed ChRn 40% 55 WedN MCldy 18% 43"
    valid, reason = validate_message(msg)
    assert valid is True


def test_wx_week_packed():
    msg = "Sun 74 TnClr57 Mon 80 Clr59 Tue 81 Clr60 Wed 85 Clr62 Thu 82 Clr59 Fr 80"
    valid, reason = validate_message(msg)
    assert valid is True
