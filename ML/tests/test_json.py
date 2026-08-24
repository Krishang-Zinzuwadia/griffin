"""JSON parsing and truncation repair are resilient to messy LLM output."""

import pytest

from ML.utils import parse_json_response, _repair_truncated_json


def test_parse_clean_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_fenced_json():
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_with_surrounding_text():
    assert parse_json_response('Here you go: {"a": 1} thanks') == {"a": 1}


def test_repair_truncated_string():
    assert _repair_truncated_json('{"a": "hello') == {"a": "hello"}


def test_repair_truncated_nested():
    result = _repair_truncated_json('{"a": {"b": "c"')
    assert result == {"a": {"b": "c"}}


def test_parse_recovers_truncated():
    assert parse_json_response('{"name": "demo", "value": "wor') == {
        "name": "demo",
        "value": "wor",
    }


def test_parse_unrecoverable_raises():
    with pytest.raises(ValueError):
        parse_json_response("this is not json at all")
