from typing import Dict, Any
from app.api.schemas import (
    IncidentPayload,
    InvestigationReportResponse,
    AnalysisFinding,
    CorrelatedEvidence,
    RootCauseAnalysis,
    RecommendedAction
)
from app.core.state import IncidentState
from app.agents.planner import run_planner_agent
from app.agents.analysts import (
    run_log_analyst_agent,
    run_stack_analyst_agent,
    run_metrics_analyst_agent,
    run_deploy_analyst_agent
)
from app.agents.synthesis import (
    run_correlation_agent,
    run_hypothesis_agent,
    run_report_agent
)

# Standard LangGraph logic (Conceptual & execution compatible)
try:
    from langgraph.graph import StateGraph, START, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

def run_incident_investigation(incident_id: str, payload: IncidentPayload) -> InvestigationReportResponse:
    """
    Initializes root cause state and executes the Multi-Agent incident workflow.
    Uses LangGraph if available; otherwise uses deterministic state propagation loop.
    """
    # 1. Initialize State
    state: IncidentState = {
        "incident_id": incident_id,
        "title": payload.title,
        "description": payload.description,
        "raw_logs": payload.logs.content if payload.logs else None,
        "raw_stack_trace": payload.stack_trace.content if payload.stack_trace else None,
        "raw_metrics_data": [m.dict() for m in payload.metrics.data] if payload.metrics else None,
        "raw_deployment_data": payload.deployment.dict() if payload.deployment else None,
        
        "agents_to_run": [],
        "focus_areas": [],
        "findings": [],
        "timeline": [],
        "root_cause": None,
        "recommendations": [],
        "markdown_report": "",
        
        # E2E Added State Targets
        "evidence": None,
        "hypothesis": None,
        "report_json": None,
        "status": "IN_PROGRESS"
    }

    if HAS_LANGGRAPH:
        # Define and compile the LangGraph workflow structure
        workflow = StateGraph(IncidentState)
        
        # Add Nodes
        workflow.add_node("planner", run_planner_agent)
        workflow.add_node("log_analysis", run_log_analyst_agent)
        
        # Placeholders for future modules (not participating in active chains yet)
        workflow.add_node("stack_analysis", run_stack_analyst_agent)
        workflow.add_node("metrics_analysis", run_metrics_analyst_agent)
        workflow.add_node("deployment_analysis", run_deploy_analyst_agent)
        
        # Core active nodes
        workflow.add_node("correlation", run_correlation_agent)
        workflow.add_node("hypothesis", run_hypothesis_agent)
        workflow.add_node("report_generation", run_report_agent)
        
        # Add Edges (Planner parses and routes execution)
        workflow.add_edge(START, "planner")
        
        # Conditional routers from Planner
        def route_planner(state: IncidentState):
            # Only execute log_analysis or bypass stack/metrics/deployment for now
            destinations = []
            if "log_analysis" in state["agents_to_run"]:
                destinations.append("log_analysis")
            # If nothing matches, go directly to correlation
            if not destinations:
                destinations.append("correlation")
            return destinations
            
        workflow.add_conditional_edges(
            "planner",
            route_planner,
            {
                "log_analysis": "log_analysis",
                "correlation": "correlation"
            }
        )
        
        # Active analytical chains connect to Evidence Correlation Node
        workflow.add_edge("log_analysis", "correlation")
        
        # E2E graph timeline pipeline
        workflow.add_edge("correlation", "hypothesis")
        workflow.add_edge("hypothesis", "report_generation")
        workflow.add_edge("report_generation", END)
        
        # Compile graph and invoke it
        app_graph = workflow.compile()
        final_state = app_graph.invoke(state)
    else:
        # Fallback executor matching sequential graph flow
        # Step 1: Run Planner
        new_vars = run_planner_agent(state)
        state.update(new_vars)
        
        # Step 2: Run active scheduled analysts (only LogAnalysisAgent is active)
        if "log_analysis" in state["agents_to_run"]:
            res = run_log_analyst_agent(state)
            state["findings"] = res["findings"]
            
        # Step 3: Run E2E Correlation -> Hypothesis -> Report pipeline
        state.update(run_correlation_agent(state))
        state.update(run_hypothesis_agent(state))
        state.update(run_report_agent(state))
        
        final_state = state

    # Map the final state to the response model
    return InvestigationReportResponse(
        incident_id=final_state["incident_id"],
        status=final_state["status"],
        findings=final_state["findings"],
        timeline=final_state["timeline"],
        root_cause=final_state["root_cause"],
        recommendations=final_state["recommendations"],
        markdown_report=final_state["markdown_report"],
        
        # E2E Added structured fields
        evidence=final_state["evidence"],
        hypothesis=final_state["hypothesis"],
        report_json=final_state["report_json"]
    )
