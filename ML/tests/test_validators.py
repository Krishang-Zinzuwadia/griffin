"""CEO and engineering validators sanitize and reject bad output."""

import pytest

from ML.utils import validate_ceo_response, validate_engineering_output


def test_ceo_slugifies_project_name():
    result = validate_ceo_response(
        {"project_name": "My Cool App!", "file_manifest": ["index.html"]}
    )
    assert result["project_name"] == "my-cool-app"


def test_ceo_rejects_empty_manifest():
    with pytest.raises(ValueError):
        validate_ceo_response({"project_name": "x", "file_manifest": []})


def test_ceo_requires_project_name():
    with pytest.raises(ValueError):
        validate_ceo_response({"file_manifest": ["a.txt"]})


def test_engineering_passes_real_code():
    assert validate_engineering_output("const x = 1;", "a.js") == "const x = 1;"


def test_engineering_rejects_empty():
    with pytest.raises(ValueError):
        validate_engineering_output("   ", "a.js")


def test_engineering_rejects_only_fences():
    with pytest.raises(ValueError):
        validate_engineering_output("```js\n```", "a.js")
