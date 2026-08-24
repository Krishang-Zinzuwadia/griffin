"""The mock provider returns schema correct responses per office."""

import json

from ML.mock_llm import MockLLM


def _content(system: str, human: str) -> str:
    return MockLLM().invoke([("system", system), ("human", human)]).content


def test_ceo_returns_selection_json():
    data = json.loads(_content("You are the CEO of a software company.", "Project Idea: a todo app"))
    assert "architect" in data["active_offices"]
    assert len(data["file_manifest"]) >= 1
    assert data["project_name"]


def test_architect_returns_categories():
    data = json.loads(_content("You are the Software Architect.", "Project: x"))
    assert "file_categories" in data
    assert "tech_stack" in data


def test_coding_office_returns_html():
    content = _content(
        "You must respond with ONLY the raw file content",
        "FILE TO WRITE: index.html",
    )
    assert content.lstrip().startswith("<!DOCTYPE html")


def test_coding_office_returns_js():
    content = _content(
        "You must respond with ONLY the raw file content",
        "FILE TO WRITE: script.js",
    )
    assert "addEventListener" in content


def test_usage_metadata_present():
    response = MockLLM().invoke([("system", "You are the CEO"), ("human", "Project Idea: x")])
    assert response.usage_metadata["input_tokens"] > 0
    assert response.usage_metadata["output_tokens"] > 0
