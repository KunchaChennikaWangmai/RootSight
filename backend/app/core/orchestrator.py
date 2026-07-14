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
    run_rca_agent,
    run_recommender_agent,
    run_report_generator_agent
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
        "status": "IN_PROGRESS"
    }

    if HAS_LANGGRAPH:
        # Define and compile the LangGraph workflow structure
        workflow = StateGraph(IncidentState)
        
        # Add Nodes
        workflow.add_node("planner", run_planner_agent)
        workflow.add_node("log_analysis", run_log_analyst_agent)
        workflow.add_node("stack_analysis", run_stack_analyst_agent)
        workflow.add_node("metrics_analysis", run_metrics_analyst_agent)
        workflow.add_node("deployment_analysis", run_deploy_analyst_agent)
        workflow.add_node("correlation", run_correlation_agent)
        workflow.add_node("rca", run_rca_agent)
        workflow.add_node("recommendations", run_recommender_agent)
        workflow.add_node("report_generation", run_report_generator_agent)
        
        # Add Edges (Planner parses and routes execution)
        workflow.add_edge(START, "planner")
        
        # Conditional routers from Planner
        def route_planner(state: IncidentState):
            # Returns a list of target node names based on active schedules
            return state["agents_to_run"]
            
        workflow.add_conditional_edges(
            "planner",
            route_planner,
            {
                "log_analysis": "log_analysis",
                "stack_analysis": "stack_analysis",
                "metrics_analysis": "metrics_analysis",
                "deployment_analysis": "deployment_analysis"
            }
        )
        
        # Analysts merge into Evidence Correlation Node
        workflow.add_edge("log_analysis", "correlation")
        workflow.add_edge("stack_analysis", "correlation")
        workflow.add_edge("metrics_analysis", "correlation")
        workflow.add_edge("deployment_analysis", "correlation")
        
        # Synthesis Pipeline Flow
        workflow.add_edge("correlation", "rca")
        workflow.add_edge("rca", "recommendations")
        workflow.add_edge("recommendations", "report_generation")
        workflow.add_edge("report_generation", END)
        
        # Compile graph and invoke it
        app_graph = workflow.compile()
        final_state = app_graph.invoke(state)
    else:
        # Fallback executor matching identical LangGraph graph execution sequentially
        # Step 1: Run Planner
        new_vars = run_planner_agent(state)
        state.update(new_vars)
        
        # Step 2: Run active scheduled analysts
        if "log_analysis" in state["agents_to_run"]:
            res = run_log_analyst_agent(state)
            state["findings"] = res["findings"]
        if "stack_analysis" in state["agents_to_run"]:
            res = run_stack_analyst_agent(state)
            state["findings"] = res["findings"]
        if "metrics_analysis" in state["agents_to_run"]:
            res = run_metrics_analyst_agent(state)
            state["findings"] = res["findings"]
        if "deployment_analysis" in state["agents_to_run"]:
            res = run_deploy_analyst_agent(state)
            state["findings"] = res["findings"]
            
        # Step 3: Run Correlation Pipeline
        state.update(run_correlation_agent(state))
        state.update(run_rca_agent(state))
        state.update(run_recommender_agent(state))
        state.update(run_report_generator_agent(state))
        
        final_state = state

    # Map the final LangGraph state to standard Investigation API Schema
    return InvestigationReportResponse(
        incident_id=final_state["incident_id"],
        status=final_state["status"],
        findings=final_state["findings"],
        timeline=final_state["timeline"],
        root_cause=final_state["root_cause"],
        recommendations=final_state["recommendations"],
        markdown_report=final_state["markdown_report"]
    )
