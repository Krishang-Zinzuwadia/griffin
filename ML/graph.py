"""
Graph — LangGraph Dynamic DAG

Registers all offices and wires them with conditional routing.
The CEO always runs first, selects which offices to activate, and
the graph routes through only the active offices to DevOps.
The Cost Optimizer always runs after the Architect to analyse token
costs before coding offices begin.

  START → CEO → [dynamically selected offices] → cost_optimizer → DevOps → END
"""

import json
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
from .offices.cost_optimizer import cost_optimizer_office
from .offices.devops import devops_office

# ── Expanded office catalog (documentation & design offices) ─────
from .offices.legal_compliance import legal_compliance_office
from .offices.ux_research import ux_research_office
from .offices.design_systems import design_systems_office
from .offices.localization import localization_office
from .offices.performance import performance_office
from .offices.accessibility import accessibility_office
from .offices.marketing import marketing_office
from .offices.data_science import data_science_office
from .offices.ai_ml import ai_ml_office
from .offices.three_d import three_d_office
from .offices.game_dev import game_dev_office
from .offices.mobile import mobile_office
from .offices.iot_embedded import iot_embedded_office


# ── Office Registry (ordered by canonical execution sequence) ────
# cost_optimizer is inserted after architect to analyse costs before coding
OFFICE_REGISTRY = OrderedDict([
    ("product_manager",    product_manager_office),
    ("architect",          architect_office),
    ("cost_optimizer",     cost_optimizer_office),
    ("ux_research",        ux_research_office),
    ("ui_designer",        ui_designer_office),
    ("design_systems",     design_systems_office),
    ("localization",       localization_office),
    ("api_designer",       api_designer_office),
    ("frontend_engineer",  frontend_engineer_office),
    ("backend_engineer",   backend_engineer_office),
    ("database_engineer",  database_engineer_office),
    ("mobile",             mobile_office),
    ("iot_embedded",       iot_embedded_office),
    ("ai_ml",              ai_ml_office),
    ("data_science",       data_science_office),
    ("three_d",            three_d_office),
    ("game_dev",           game_dev_office),
    ("qa_engineer",        qa_engineer_office),
    ("performance",        performance_office),
    ("accessibility",      accessibility_office),
    ("security_officer",   security_officer_office),
    ("legal_compliance",   legal_compliance_office),
    ("marketing",          marketing_office),
    ("tech_writer",        tech_writer_office),
])

# All possible routing targets (used by conditional edges)
ALL_TARGETS = list(OFFICE_REGISTRY.keys()) + ["devops_office"]


# ── Live status events ───────────────────────────────────────────
# Each node emits a machine readable status line on stdout so the ML service can
# forward it to the frontend and drive the Blueprint Canvas node states.
NODE_NAMES = {
    "ceo_office": "CEO Office",
    "product_manager": "Product Manager",
    "architect": "Architect",
    "cost_optimizer": "Cost Optimizer",
    "ux_research": "UX Research",
    "ui_designer": "UI Designer",
    "design_systems": "Design Systems",
    "localization": "Localization",
    "api_designer": "API Designer",
    "frontend_engineer": "Frontend Engineer",
    "backend_engineer": "Backend Engineer",
    "database_engineer": "Database Engineer",
    "mobile": "Mobile Engineering",
    "iot_embedded": "IoT & Embedded",
    "ai_ml": "AI & Machine Learning",
    "data_science": "Data Science",
    "three_d": "3D & Spatial",
    "game_dev": "Game Development",
    "qa_engineer": "QA Engineer",
    "performance": "Performance Engineering",
    "accessibility": "Accessibility",
    "security_officer": "Security Officer",
    "legal_compliance": "Legal & Compliance",
    "marketing": "Marketing & Growth",
    "tech_writer": "Tech Writer",
    "devops_office": "DevOps",
}

EVENT_PREFIX = "@@GRIFFIN_EVENT "


def _emit_status(office_id: str, status: str) -> None:
    """Print a status event that the ML service parses and forwards."""
    payload = {
        "kind": "office_status",
        "office": office_id,
        "name": NODE_NAMES.get(office_id, office_id),
        "status": status,
    }
    try:
        print(EVENT_PREFIX + json.dumps(payload), flush=True)
    except Exception:
        pass


def _instrument(office_id: str, fn):
    """Wrap an office node so it emits WORKING, then IDLE (or BLOCKED on error)."""

    def wrapped(state):
        _emit_status(office_id, "WORKING")
        try:
            result = fn(state)
        except Exception:
            _emit_status(office_id, "BLOCKED")
            raise
        _emit_status(office_id, "IDLE")
        return result

    return wrapped


def _get_next_office(state: dict, current_id: str) -> str:
    """Given the current office, return the next active office ID (or devops).

    cost_optimizer always runs if architect is active (right after architect).
    """
    active = state.get("active_offices", [])

    # Ensure cost_optimizer is always included when architect is active
    effective_active = list(active)
    if "architect" in effective_active and "cost_optimizer" not in effective_active:
        # Insert cost_optimizer right after architect
        idx = effective_active.index("architect")
        effective_active.insert(idx + 1, "cost_optimizer")

    # Filter to only offices in the registry, maintaining canonical order
    ordered_active = [oid for oid in OFFICE_REGISTRY if oid in effective_active]

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

    Every office in OFFICE_REGISTRY is registered as a node, but conditional
    routing ensures only CEO-selected offices are visited.
    """

    graph = StateGraph(OfficeState)

    # ── Add ALL nodes (wrapped to emit live status events) ───────
    graph.add_node("ceo_office", _instrument("ceo_office", ceo_office))
    for office_id, office_fn in OFFICE_REGISTRY.items():
        graph.add_node(office_id, _instrument(office_id, office_fn))
    graph.add_node("devops_office", _instrument("devops_office", devops_office))

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
