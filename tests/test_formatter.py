"""Unit tests for formatter validation and deterministic formatting logic."""

from dataclasses import dataclass

from src.formatter import (
    _abbreviate_condition,
    _abbreviate_day,
    _format_deterministic,
    _format_period,
    validate_message,
)


@dataclass
class ForecastPeriod:
    name: str
    temperature: int
    precip_chance: int
    short_forecast: str


# ===================================================================
# Existing validate_message tests (unchanged)
# ===================================================================


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


# ===================================================================
# _abbreviate_day tests
# ===================================================================


def test_abbreviate_day_today():
    assert _abbreviate_day("Today") == "Td"


def test_abbreviate_day_tonight():
    assert _abbreviate_day("Tonight") == "Tn"


def test_abbreviate_day_this_afternoon():
    assert _abbreviate_day("This Afternoon") == "Td"


def test_abbreviate_day_weekdays():
    assert _abbreviate_day("Sunday") == "Sun"
    assert _abbreviate_day("Monday") == "Mon"
    assert _abbreviate_day("Tuesday") == "Tue"
    assert _abbreviate_day("Wednesday") == "Wed"
    assert _abbreviate_day("Thursday") == "Thu"
    assert _abbreviate_day("Friday") == "Fri"
    assert _abbreviate_day("Saturday") == "Sat"


def test_abbreviate_day_nights():
    assert _abbreviate_day("Sunday Night") == "SunN"
    assert _abbreviate_day("Monday Night") == "MonN"
    assert _abbreviate_day("Tuesday Night") == "TueN"
    assert _abbreviate_day("Wednesday Night") == "WedN"
    assert _abbreviate_day("Thursday Night") == "ThuN"
    assert _abbreviate_day("Friday Night") == "FriN"
    assert _abbreviate_day("Saturday Night") == "SatN"


def test_abbreviate_day_unknown_passthrough():
    assert _abbreviate_day("Overnight") == "Overnight"


# ===================================================================
# _abbreviate_condition tests
# ===================================================================


def test_abbreviate_condition_known():
    assert _abbreviate_condition("Sunny") == "Sun"
    assert _abbreviate_condition("Mostly Cloudy") == "MCldy"
    assert _abbreviate_condition("Rain Showers") == "RnShw"
    assert _abbreviate_condition("Thunderstorms") == "Tst"
    assert _abbreviate_condition("Snow") == "Snw"
    assert _abbreviate_condition("Fog") == "Fog"
    assert _abbreviate_condition("Clear") == "Clr"
    assert _abbreviate_condition("Partly Cloudy") == "PCldy"
    assert _abbreviate_condition("Freezing Rain") == "FzRn"
    assert _abbreviate_condition("Showers And Thunderstorms") == "ShTst"


def test_abbreviate_condition_prefix_stripping():
    assert _abbreviate_condition("Slight Chance Rain Showers") == "RnShw"
    assert _abbreviate_condition("Chance Rain") == "Rn"
    assert _abbreviate_condition("Likely Snow") == "Snw"
    assert _abbreviate_condition("Isolated Thunderstorms") == "Tst"
    assert _abbreviate_condition("Scattered Showers") == "Shw"
    assert _abbreviate_condition("Numerous Showers And Thunderstorms") == "ShTst"
    assert _abbreviate_condition("Areas Fog") == "Fog"
    assert _abbreviate_condition("Patchy Fog") == "Fog"


def test_abbreviate_condition_slight_chance_before_chance():
    """Slight Chance must be stripped fully, not leaving 'Slight'."""
    assert _abbreviate_condition("Slight Chance Snow Showers") == "SnShw"


def test_abbreviate_condition_suffix_stripping():
    """NWS sometimes puts probability as a suffix (e.g. 'Light Rain Likely')."""
    assert _abbreviate_condition("Light Rain Likely") == "LRn"
    assert _abbreviate_condition("Rain Showers Likely") == "RnShw"
    assert _abbreviate_condition("Snow Likely") == "Snw"


def test_abbreviate_condition_then_compound():
    assert _abbreviate_condition("Rain Showers then Partly Cloudy") == "RnShw"
    assert _abbreviate_condition("Mostly Cloudy then Chance Rain") == "MCldy"


def test_abbreviate_condition_prefix_and_then():
    assert _abbreviate_condition("Chance Rain Showers then Mostly Cloudy") == "RnShw"


def test_abbreviate_condition_unknown_multi_word():
    result = _abbreviate_condition("Volcanic Ash")
    assert result == "VA"


def test_abbreviate_condition_unknown_single_word():
    result = _abbreviate_condition("Sprinkles")
    assert result == "Spr"


# ===================================================================
# _format_period tests
# ===================================================================


def test_format_period_no_precip():
    p = ForecastPeriod("Today", 74, 0, "Sunny")
    assert _format_period(p) == "Td Sun 74"


def test_format_period_with_precip():
    p = ForecastPeriod("Tonight", 44, 70, "Showers And Thunderstorms")
    assert _format_period(p) == "Tn ShTst 70% 44"


def test_format_period_with_prefix():
    p = ForecastPeriod("Wednesday", 55, 40, "Chance Rain Showers")
    assert _format_period(p) == "Wed RnShw 40% 55"


# ===================================================================
# End-to-end fixture tests
# ===================================================================


def _seattle_periods():
    """Seattle: rain, showers."""
    return [
        ForecastPeriod("Today", 52, 80, "Rain Showers"),
        ForecastPeriod("Tonight", 44, 70, "Showers And Thunderstorms"),
        ForecastPeriod("Wednesday", 55, 40, "Chance Rain Showers"),
        ForecastPeriod("Wednesday Night", 43, 18, "Mostly Cloudy"),
        ForecastPeriod("Thursday", 58, 0, "Partly Cloudy"),
        ForecastPeriod("Thursday Night", 45, 0, "Mostly Clear"),
        ForecastPeriod("Friday", 60, 25, "Slight Chance Showers"),
        ForecastPeriod("Friday Night", 47, 10, "Chance Light Rain"),
        ForecastPeriod("Saturday", 56, 50, "Rain Showers"),
        ForecastPeriod("Saturday Night", 42, 30, "Chance Showers"),
    ]


def _nyc_periods():
    """NYC: cloudy, chance rain."""
    return [
        ForecastPeriod("This Afternoon", 65, 0, "Mostly Cloudy"),
        ForecastPeriod("Tonight", 52, 20, "Slight Chance Rain Showers"),
        ForecastPeriod("Thursday", 68, 30, "Chance Rain"),
        ForecastPeriod("Thursday Night", 55, 10, "Mostly Cloudy"),
        ForecastPeriod("Friday", 70, 0, "Partly Sunny"),
        ForecastPeriod("Friday Night", 58, 0, "Mostly Clear"),
        ForecastPeriod("Saturday", 72, 0, "Sunny"),
        ForecastPeriod("Saturday Night", 60, 0, "Clear"),
    ]


def _phoenix_periods():
    """Phoenix: sunny, clear."""
    return [
        ForecastPeriod("Today", 105, 0, "Sunny"),
        ForecastPeriod("Tonight", 82, 0, "Clear"),
        ForecastPeriod("Wednesday", 107, 0, "Sunny"),
        ForecastPeriod("Wednesday Night", 84, 0, "Clear"),
        ForecastPeriod("Thursday", 108, 0, "Sunny"),
        ForecastPeriod("Thursday Night", 83, 0, "Clear"),
        ForecastPeriod("Friday", 106, 0, "Mostly Sunny"),
        ForecastPeriod("Friday Night", 80, 0, "Mostly Clear"),
        ForecastPeriod("Saturday", 104, 0, "Sunny"),
        ForecastPeriod("Saturday Night", 78, 0, "Clear"),
    ]


def _denver_periods():
    """Denver: snow mix."""
    return [
        ForecastPeriod("Today", 38, 60, "Rain And Snow Showers"),
        ForecastPeriod("Tonight", 28, 40, "Chance Snow Showers"),
        ForecastPeriod("Wednesday", 45, 20, "Slight Chance Flurries"),
        ForecastPeriod("Wednesday Night", 30, 0, "Mostly Cloudy"),
        ForecastPeriod("Thursday", 52, 0, "Partly Sunny"),
        ForecastPeriod("Thursday Night", 35, 0, "Mostly Clear"),
        ForecastPeriod("Friday", 58, 10, "Slight Chance Rain Showers"),
        ForecastPeriod("Friday Night", 40, 0, "Clear"),
    ]


def _miami_periods():
    """Miami: mostly sunny."""
    return [
        ForecastPeriod("Today", 88, 0, "Mostly Sunny"),
        ForecastPeriod("Tonight", 75, 0, "Partly Cloudy"),
        ForecastPeriod("Wednesday", 89, 10, "Slight Chance Showers"),
        ForecastPeriod("Wednesday Night", 76, 0, "Mostly Clear"),
        ForecastPeriod("Thursday", 90, 20, "Isolated Thunderstorms"),
        ForecastPeriod("Thursday Night", 77, 10, "Partly Cloudy then Mostly Clear"),
        ForecastPeriod("Friday", 88, 0, "Sunny"),
        ForecastPeriod("Friday Night", 74, 0, "Clear"),
    ]


def _anchorage_periods():
    """Anchorage: snow."""
    return [
        ForecastPeriod("Today", 35, 80, "Rain And Snow"),
        ForecastPeriod("Tonight", 28, 50, "Chance Light Snow"),
        ForecastPeriod("Wednesday", 33, 40, "Chance Snow Showers"),
        ForecastPeriod("Wednesday Night", 25, 30, "Scattered Flurries"),
        ForecastPeriod("Thursday", 38, 0, "Mostly Cloudy"),
        ForecastPeriod("Thursday Night", 27, 0, "Partly Cloudy"),
        ForecastPeriod("Friday", 40, 10, "Slight Chance Rain"),
        ForecastPeriod("Friday Night", 30, 0, "Mostly Clear"),
    ]


class TestE2ESeattle:
    def test_wx_now(self):
        result = _format_deterministic("wx now", _seattle_periods())
        valid, _ = validate_message(result)
        assert valid
        assert "Td" in result
        assert "Tn" in result
        assert len(result) <= 160

    def test_wx_week(self):
        result = _format_deterministic("wx week", _seattle_periods())
        valid, _ = validate_message(result)
        assert valid
        assert len(result) <= 160

    def test_wx_now_contains_temps(self):
        result = _format_deterministic("wx now", _seattle_periods())
        assert "52" in result
        assert "44" in result

    def test_wx_now_contains_precip(self):
        result = _format_deterministic("wx now", _seattle_periods())
        assert "80%" in result
        assert "70%" in result


class TestE2ENYC:
    def test_wx_now(self):
        result = _format_deterministic("wx now", _nyc_periods())
        valid, _ = validate_message(result)
        assert valid
        assert "Td" in result  # "This Afternoon" maps to Td
        assert len(result) <= 160

    def test_wx_week(self):
        result = _format_deterministic("wx week", _nyc_periods())
        valid, _ = validate_message(result)
        assert valid
        assert len(result) <= 160


class TestE2EPhoenix:
    def test_wx_now(self):
        result = _format_deterministic("wx now", _phoenix_periods())
        valid, _ = validate_message(result)
        assert valid
        assert "105" in result
        assert len(result) <= 160

    def test_wx_now_no_precip(self):
        result = _format_deterministic("wx now", _phoenix_periods())
        assert "%" not in result

    def test_wx_week(self):
        result = _format_deterministic("wx week", _phoenix_periods())
        valid, _ = validate_message(result)
        assert valid
        assert len(result) <= 160


class TestE2EDenver:
    def test_wx_now(self):
        result = _format_deterministic("wx now", _denver_periods())
        valid, _ = validate_message(result)
        assert valid
        assert "RnSnShw" in result  # Rain And Snow Showers
        assert "60%" in result
        assert len(result) <= 160

    def test_wx_week(self):
        result = _format_deterministic("wx week", _denver_periods())
        valid, _ = validate_message(result)
        assert valid
        assert len(result) <= 160


class TestE2EMiami:
    def test_wx_now(self):
        result = _format_deterministic("wx now", _miami_periods())
        valid, _ = validate_message(result)
        assert valid
        assert "MSun" in result  # Mostly Sunny
        assert len(result) <= 160

    def test_wx_week(self):
        result = _format_deterministic("wx week", _miami_periods())
        valid, _ = validate_message(result)
        assert valid
        assert len(result) <= 160

    def test_then_compound_handled(self):
        """Miami Thursday Night has 'Partly Cloudy then Mostly Clear'."""
        result = _format_deterministic("wx week", _miami_periods())
        # Should use PCldy (first part), not the full compound
        assert "PCldy" in result


class TestE2EAnchorage:
    def test_wx_now(self):
        result = _format_deterministic("wx now", _anchorage_periods())
        valid, _ = validate_message(result)
        assert valid
        assert "RnSn" in result  # Rain And Snow
        assert "80%" in result
        assert len(result) <= 160

    def test_wx_week(self):
        result = _format_deterministic("wx week", _anchorage_periods())
        valid, _ = validate_message(result)
        assert valid
        assert len(result) <= 160


class TestWxNowLimitsFourPeriods:
    def test_only_four_periods(self):
        periods = _phoenix_periods()  # 10 periods
        result = _format_deterministic("wx now", periods)
        # Should only have 4 day codes
        day_codes = ["Td", "Tn", "Wed", "WedN"]
        for code in day_codes:
            assert code in result
        # Thursday should NOT appear
        assert "Thu" not in result


class TestWxWeekTruncation:
    def test_long_week_truncates(self):
        """With many periods with precip, output should truncate at token boundary."""
        periods = _seattle_periods()
        result = _format_deterministic("wx week", periods)
        assert len(result) <= 160
        # Should not end mid-token
        assert not result.endswith("%")
        valid, _ = validate_message(result)
        assert valid
