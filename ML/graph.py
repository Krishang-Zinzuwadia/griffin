"""
Graph — LangGraph Dynamic DAG

Registers all 12 offices and wires them with conditional routing.
The CEO always runs first, selects which offices to activate, and
the graph routes through only the active offices to DevOps.

  START → CEO → [dynamically selected offices] → DevOps → END
"""

from collections import OrderedDict
from langgraph.graph import StateGraph, START, END
from .state import OfficeState

# ── Office imports ───────────────────────────────────────────────
from .offices.ceo import ceo_office
from .offices.product_manager import product_manager_office
from .offices.architect import architect_office
from .offices.ui_designer import ui_designer_office
from .offices.api_designer import api_designer_office
from .offices.frontend_engineer import frontend_engineer_office
from .offices.backend_engineer import backend_engineer_office
from .offices.database_engineer import database_engineer_office
from .offices.qa_engineer import qa_engineer_office
from .offices.security_officer import security_officer_office
from .offices.tech_writer import tech_writer_office
from .offices.devops import devops_office


# ── Office Registry (ordered by canonical execution sequence) ────
OFFICE_REGISTRY = OrderedDict([
    ("product_manager",    product_manager_office),
    ("architect",          architect_office),
    ("ui_designer",        ui_designer_office),
    ("api_designer",       api_designer_office),
    ("frontend_engineer",  frontend_engineer_office),
    ("backend_engineer",   backend_engineer_office),
    ("database_engineer",  database_engineer_office),
    ("qa_engineer",        qa_engineer_office),
    ("security_officer",   security_officer_office),
    ("tech_writer",        tech_writer_office),
])

# All possible routing targets (used by conditional edges)
ALL_TARGETS = list(OFFICE_REGISTRY.keys()) + ["devops_office"]


def _get_next_office(state: dict, current_id: str) -> str:
    """Given the current office, return the next active office ID (or devops)."""
    active = state.get("active_offices", [])
    # Filter to only offices in the registry, maintaining canonical order
    ordered_active = [oid for oid in OFFICE_REGISTRY if oid in active]

    if current_id == "ceo_office":
        return ordered_active[0] if ordered_active else "devops_office"

    try:
        idx = ordered_active.index(current_id)
        if idx + 1 < len(ordered_active):
            return ordered_active[idx + 1]
        return "devops_office"
    except ValueError:
        return "devops_office"


def build_graph():
    """Construct and compile the dynamic office chain.

    All 12 offices are registered as nodes, but conditional routing
    ensures only CEO-selected offices are visited.
    """

    graph = StateGraph(OfficeState)

    # ── Add ALL nodes ────────────────────────────────────────────
    graph.add_node("ceo_office", ceo_office)
    for office_id, office_fn in OFFICE_REGISTRY.items():
        graph.add_node(office_id, office_fn)
    graph.add_node("devops_office", devops_office)

    # ── CEO always runs first ────────────────────────────────────
    graph.add_edge(START, "ceo_office")

    # ── CEO → first active office (conditional) ──────────────────
    target_map = {oid: oid for oid in ALL_TARGETS}
    graph.add_conditional_edges(
        "ceo_office",
        lambda state: _get_next_office(state, "ceo_office"),
        target_map,
    )

    # ── Each optional office → next active office (conditional) ──
    for office_id in OFFICE_REGISTRY:
        graph.add_conditional_edges(
            office_id,
            lambda state, oid=office_id: _get_next_office(state, oid),
            target_map,
        )

    # ── DevOps always runs last ──────────────────────────────────
    graph.add_edge("devops_office", END)

    # ── Compile ──────────────────────────────────────────────────
    return graph.compile()
