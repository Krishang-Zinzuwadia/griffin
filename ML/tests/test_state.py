"""State reducers behave as the graph expects."""

from ML.state import merge_dicts


def test_merge_dicts_combines():
    assert merge_dicts({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_merge_dicts_right_wins():
    assert merge_dicts({"a": 1}, {"a": 2}) == {"a": 2}


def test_merge_dicts_does_not_mutate_left():
    left = {"a": 1}
    merge_dicts(left, {"b": 2})
    assert left == {"a": 1}
