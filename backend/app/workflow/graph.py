from langgraph.graph import END, START, StateGraph

from app.workflow import nodes
from app.workflow.state import AnalysisState

# Node -> approximate progress percentage, used by the background task
# consuming graph.stream() to update job progress for polling. Kept out of
# node return values so the parallel audit_rules/statistics branch never
# writes the same un-reduced state key twice in one superstep.
NODE_PROGRESS: dict[str, int] = {
    "ingest": 10,
    "clean": 20,
    "profile": 30,
    "schema_fit": 40,
    "validate_schema": 50,
    "audit_rules": 65,
    "statistics": 65,
    "risk_score": 80,
    "explain": 90,
    "persist": 100,
}


def build_graph():
    graph = StateGraph(AnalysisState)

    # Data ingestion and preprocessing (sequential)
    graph.add_node("ingest", nodes.ingest_node)
    graph.add_node("clean", nodes.clean_node)
    graph.add_node("profile", nodes.profile_node)
    graph.add_node("schema_fit", nodes.schema_fit_node)

    # Data quality validation gate
    graph.add_node("validate_schema", nodes.validate_schema_node)

    # Core analysis (parallel execution)
    graph.add_node("audit_rules", nodes.audit_rules_node)
    graph.add_node("statistics", nodes.statistics_node)

    # Risk scoring (depends on both parallel nodes)
    graph.add_node("risk_score", nodes.risk_score_node)

    # LLM enrichment and persistence
    graph.add_node("explain", nodes.explain_node)
    graph.add_node("persist", nodes.persist_node)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "clean")
    graph.add_edge("clean", "profile")
    graph.add_edge("profile", "schema_fit")
    graph.add_edge("schema_fit", "validate_schema")

    # === PARALLEL EXECUTION ===
    graph.add_edge("validate_schema", "audit_rules")
    graph.add_edge("validate_schema", "statistics")

    # === FAN-IN ===
    graph.add_edge("audit_rules", "risk_score")
    graph.add_edge("statistics", "risk_score")

    graph.add_edge("risk_score", "explain")
    graph.add_edge("explain", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


analysis_graph = build_graph()
