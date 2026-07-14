from typing import Dict, Any
from app.core.state import IncidentState
from app.api.schemas import AnalysisFinding
from app.core.base_agent import debug_node

@debug_node("PlannerAgent")
def run_planner_agent(state: IncidentState) -> Dict[str, Any]:
    """
    Planner Agent Node:
    Assesses raw artifacts, sets objectives, and determines which analysis agents need to run.
    """
    logs_present = state.get("raw_logs") is not None
    stack_present = state.get("raw_stack_trace") is not None
    metrics_present = state.get("raw_metrics_data") is not None
    deploy_present = state.get("raw_deployment_data") is not None

    agents_to_run = []
    focus_areas = []

    # Simple routing rule base (acting as the structured planner reasoning)
    if logs_present:
        agents_to_run.append("log_analysis")
        focus_areas.append("Log pattern extraction & error categorization")
    if stack_present:
        agents_to_run.append("stack_analysis")
        focus_areas.append("Call stack frame debugging & exception parsing")
    if metrics_present:
        agents_to_run.append("metrics_analysis")
        focus_areas.append("Time-series anomaly threshold scanning")
    if deploy_present:
        agents_to_run.append("deployment_analysis")
        focus_areas.append("Configuration change and release analysis")

    # Add planning log entry to findings
    planning_finding = AnalysisFinding(
        agent_name="Planner Agent",
        severity="INFO",
        message=f"Created investigation plan focusing on: {', '.join(focus_areas)}",
        evidence_snippet=f"Inputs checking: logs={logs_present}, stack={stack_present}, metrics={metrics_present}, deployment={deploy_present}"
    )

    return {
        "agents_to_run": agents_to_run,
        "focus_areas": focus_areas,
        "findings": state.get("findings", []) + [planning_finding]
    }
