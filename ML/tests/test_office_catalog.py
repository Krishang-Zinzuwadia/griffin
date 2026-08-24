"""The expanded office catalog registers new offices and they run offline.

Verifies that every new office is wired into the graph registry, exposed to
the CEO via OFFICE_CATALOG, and emits status events via NODE_NAMES. Also runs
a few new office nodes directly with the mock provider and asserts each one
returns its artifact file in the codebase update. Fully offline via conftest.
"""

from ML.graph import OFFICE_REGISTRY, NODE_NAMES, ALL_TARGETS
from ML.prompts import OFFICE_CATALOG


# (office id, artifact file the office must produce) for every new office.
NEW_OFFICES = {
    "legal_compliance": "TERMS.md",
    "ux_research": "docs/USER_FLOWS.md",
    "design_systems": "design_tokens.json",
    "localization": "i18n/en.json",
    "performance": "docs/PERFORMANCE.md",
    "accessibility": "docs/ACCESSIBILITY.md",
    "marketing": "docs/MARKETING.md",
    "data_science": "docs/DATA_SCIENCE.md",
    "ai_ml": "docs/AI_INTEGRATION.md",
    "three_d": "docs/3D_NOTES.md",
    "game_dev": "docs/GAME_DESIGN.md",
    "mobile": "docs/MOBILE_PLAN.md",
    "iot_embedded": "docs/IOT_NOTES.md",
}


def _base_state(goal: str = "build a full stack marketplace with legal pages") -> dict:
    return {
        "project_goal": goal,
        "project_name": "demo-marketplace",
        "active_offices": [],
        "file_manifest": ["index.html"],
        "file_descriptions": {},
        "requirements": [],
        "tech_stack": {"languages": ["HTML", "CSS", "JavaScript"]},
        "folder_structure": "",
        "file_categories": {},
        "design_system": {},
        "api_schema": {},
        "codebase": {"index.html": "<!DOCTYPE html><html></html>"},
        "execution_logs": [],
        "github_url": "",
        "token_usage": {},
    }


def test_new_offices_registered():
    for office_id in NEW_OFFICES:
        assert office_id in OFFICE_REGISTRY, f"{office_id} missing from OFFICE_REGISTRY"
        assert office_id in ALL_TARGETS, f"{office_id} missing from ALL_TARGETS"


def test_new_offices_have_node_names():
    for office_id in NEW_OFFICES:
        assert office_id in NODE_NAMES, f"{office_id} missing from NODE_NAMES"
        assert NODE_NAMES[office_id], f"{office_id} has an empty node name"


def test_new_offices_in_catalog():
    for office_id in NEW_OFFICES:
        assert office_id in OFFICE_CATALOG, f"{office_id} missing from OFFICE_CATALOG"


def test_registry_functions_are_callable():
    for office_id in NEW_OFFICES:
        assert callable(OFFICE_REGISTRY[office_id])


def test_legal_office_writes_artifacts():
    from ML.offices.legal_compliance import legal_compliance_office

    update = legal_compliance_office(_base_state())
    codebase = update["codebase"]
    assert "TERMS.md" in codebase
    assert "PRIVACY.md" in codebase
    assert len(codebase["TERMS.md"]) > 10


def test_design_systems_writes_valid_json_tokens():
    import json

    from ML.offices.design_systems import design_systems_office

    update = design_systems_office(_base_state())
    assert "design_tokens.json" in update["codebase"]
    # The artifact content must itself parse as JSON.
    tokens = json.loads(update["codebase"]["design_tokens.json"])
    assert "color" in tokens


def test_localization_writes_valid_json_catalog():
    import json

    from ML.offices.localization import localization_office

    update = localization_office(_base_state())
    assert "i18n/en.json" in update["codebase"]
    catalog = json.loads(update["codebase"]["i18n/en.json"])
    assert catalog, "localization catalog should not be empty"


def test_every_new_office_returns_its_artifact():
    for office_id, artifact in NEW_OFFICES.items():
        node = OFFICE_REGISTRY[office_id]
        update = node(_base_state())
        codebase = update.get("codebase", {})
        assert artifact in codebase, (
            f"{office_id} did not produce {artifact}; got {list(codebase)}"
        )
        assert isinstance(codebase[artifact], str) and len(codebase[artifact]) > 10
        # The node must return an append-only execution log entry too.
        assert update.get("execution_logs"), f"{office_id} returned no execution logs"
