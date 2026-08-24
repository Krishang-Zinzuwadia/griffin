"""The graph builds and registers the expected offices."""

from ML.graph import build_graph, OFFICE_REGISTRY, ALL_TARGETS


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_registry_has_core_offices():
    expected = {
        "product_manager",
        "architect",
        "cost_optimizer",
        "ui_designer",
        "api_designer",
        "frontend_engineer",
        "backend_engineer",
        "database_engineer",
        "qa_engineer",
        "security_officer",
        "tech_writer",
    }
    assert expected.issubset(set(OFFICE_REGISTRY.keys()))


def test_devops_is_a_routing_target():
    assert "devops_office" in ALL_TARGETS
