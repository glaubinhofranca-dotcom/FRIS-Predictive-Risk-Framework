import pandas as pd
import pytest
from fris_utils import normalize_str, normalize_str_upper, to_numeric, clean_currency


def test_normalize_str_strips_whitespace():
    s = pd.Series(["  hello  ", "world", "  "])
    assert list(normalize_str(s)) == ["hello", "world", ""]


def test_normalize_str_strips_mixed_whitespace():
    s = pd.Series(["\t  foo \n", "bar  ", "baz"])
    result = normalize_str(s)
    assert list(result) == ["foo", "bar", "baz"]


def test_normalize_str_upper_strips_and_uppercases():
    s = pd.Series(["  hello  ", "World", "ug"])
    assert list(normalize_str_upper(s)) == ["HELLO", "WORLD", "UG"]


def test_to_numeric_converts_valid():
    s = pd.Series(["1.5", "3", "0"])
    result = to_numeric(s)
    assert result[0] == pytest.approx(1.5)
    assert result[1] == pytest.approx(3.0)


def test_to_numeric_coerces_invalid_to_nan():
    s = pd.Series(["abc", None, "N/A"])
    result = to_numeric(s)
    assert all(pd.isna(result))


def test_clean_currency_removes_symbols():
    s = pd.Series(["$1,234.56", "$0.00", "500"])
    result = clean_currency(s)
    assert result[0] == pytest.approx(1234.56)
    assert result[1] == pytest.approx(0.0)
    assert result[2] == pytest.approx(500.0)


def test_clean_currency_non_numeric_becomes_nan():
    s = pd.Series(["N/A", "unknown", None])
    result = clean_currency(s)
    assert all(pd.isna(result))
