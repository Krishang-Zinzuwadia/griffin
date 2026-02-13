"""
Graph — LangGraph Sequential DAG

Wires the four office nodes into a strictly linear chain:
  START → CEO → Product → Engineering → DevOps → END

Zero parallelism — only one LLM call happens at a time.
"""

from langgraph.graph import StateGraph, START, END
from .state import OfficeState
from .offices.ceo import ceo_office
from .offices.product import product_office
from .offices.engineering import engineering_office
from .offices.devops import devops_office


def build_graph():
    """Construct and compile the sequential office chain."""

    graph = StateGraph(OfficeState)

    # ── Add nodes ────────────────────────────────────────────────
    graph.add_node("ceo_office", ceo_office)
    graph.add_node("product_office", product_office)
    graph.add_node("engineering_office", engineering_office)
    graph.add_node("devops_office", devops_office)

    # ── Wire edges (strictly sequential) ─────────────────────────
    graph.add_edge(START, "ceo_office")
    graph.add_edge("ceo_office", "product_office")
    graph.add_edge("product_office", "engineering_office")
    graph.add_edge("engineering_office", "devops_office")
    graph.add_edge("devops_office", END)

    # ── Compile ──────────────────────────────────────────────────
    return graph.compile()
