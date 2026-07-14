from typing import Dict, Any, List
from datetime import datetime
from app.core.state import IncidentState
from app.api.schemas import AnalysisFinding
from app.core.base_agent import BaseAgent, Tool

# Import raw deterministic function tools
from app.core.tools.log_parser import parse_logs, cluster_log_errors
from app.core.tools.stack_parser import parse_stack_trace
from app.core.tools.metrics_tool import analyze_metrics
from app.core.tools.config_diff import compute_config_diff

# ==========================================
# Tool registrations
# ==========================================
log_parse_tool = Tool(
    name="parse_logs",
    description="Scans log file for Error/Warning levels and returns matches.",
    func=parse_logs
)
log_cluster_tool = Tool(
    name="cluster_log_errors",
    description="Groups matching log error entries by standard templates.",
    func=cluster_log_errors
)

stack_trace_tool = Tool(
    name="parse_stack_trace",
    description="Parses Java, Python, and Node exceptions extracting active frames.",
    func=parse_stack_trace
)

metrics_scan_tool = Tool(
    name="analyze_metrics",
    description="Performs numeric statistical Z-score scans to find CPU/Latency spikes.",
    func=analyze_metrics
)

config_diff_tool = Tool(
    name="compute_config_diff",
    description="Performs env variable JSON comparisons against baseline histories.",
    func=compute_config_diff
)

# ==========================================
# Agent instantiations
# ==========================================
log_agent = BaseAgent(
    name="Log Analyst Agent",
    role="App Log Analysis",
    system_prompt="Responsible for discovering and clustering system warning and error trends.",
    tools=[log_parse_tool, log_cluster_tool]
)

stack_agent = BaseAgent(
    name="Stack Trace Analyst Agent",
    role="Exception Stack Analyst",
    system_prompt="Responsible for locating throw contexts and active crash stack code paths.",
    tools=[stack_trace_tool]
)

metrics_agent = BaseAgent(
    name="Metrics Analyst Agent",
    role="Numeric Telemetry Analyst",
    system_prompt="Responsible for isolating time-series outliers and utilization limits anomalies.",
    tools=[metrics_scan_tool]
)

deploy_agent = BaseAgent(
    name="Deployment Analyst Agent",
    role="Platform Config Analyst",
    system_prompt="Responsible for detecting deployment variable adjustments or commit differences.",
    tools=[config_diff_tool]
)

# ==========================================
# LangGraph node executors using Agent+Tool
# ==========================================
def run_log_analyst_agent(state: IncidentState) -> Dict[str, Any]:
    findings = []
    raw_logs = state.get("raw_logs")
    
    if raw_logs:
        # Run tools via Agent shell
        errors = log_agent.execute_tool("parse_logs", raw_logs)
        error_clusters = log_agent.execute_tool("cluster_log_errors", errors)
        
        for cluster in error_clusters:
            findings.append(
                AnalysisFinding(
                    agent_name=log_agent.name,
                    severity="CRITICAL" if cluster["level"] in ["ERROR", "FATAL", "CRITICAL"] else "WARNING",
                    message=f"Log anomaly template detected: '{cluster['template']}'. Repeated {cluster['count']} times.",
                    evidence_snippet=f"Template: {cluster['template']}\nExample line: {cluster['examples'][0]}"
                )
            )
            
    return {"findings": state.get("findings", []) + findings}

def run_stack_analyst_agent(state: IncidentState) -> Dict[str, Any]:
    findings = []
    raw_stack = state.get("raw_stack_trace")
    
    if raw_stack:
        # Run tools via Agent shell
        parsed = stack_agent.execute_tool("parse_stack_trace", raw_stack)
        frames = parsed["frames"]
        exc_type = parsed["exception_type"]
        exc_msg = parsed["exception_message"]
        
        evidence = f"Exception: {exc_type}: {exc_msg}\n"
        if frames:
            crash_frame = frames[0]
            evidence += f"Crash at {crash_frame['file']}:{crash_frame['line']} in function '{crash_frame['function']}'"
            
            findings.append(
                AnalysisFinding(
                    agent_name=stack_agent.name,
                    severity="CRITICAL",
                    message=f"Code failure detected: Throwing '{exc_type}' with message '{exc_msg}' in {crash_frame['file']} line {crash_frame['line']}.",
                    evidence_snippet=evidence
                )
            )
        else:
            findings.append(
                AnalysisFinding(
                    agent_name=stack_agent.name,
                    severity="WARNING",
                    message=f"Unparsed stack dump containing error syntax: '{exc_type}' message: '{exc_msg}'",
                    evidence_snippet=raw_stack[:250]
                )
            )
            
    return {"findings": state.get("findings", []) + findings}

def run_metrics_analyst_agent(state: IncidentState) -> Dict[str, Any]:
    findings = []
    raw_metrics = state.get("raw_metrics_data")
    
    if raw_metrics:
        # Run tools via Agent shell
        anomalies = metrics_agent.execute_tool("analyze_metrics", raw_metrics)
        
        for anomaly in anomalies:
            findings.append(
                AnalysisFinding(
                    agent_name=metrics_agent.name,
                    severity="CRITICAL" if anomaly["metric"] in ["error_rate", "latency_ms"] and anomaly["z_score"] > 3 else "WARNING",
                    timestamp=datetime.fromisoformat(anomaly["timestamp"]) if "T" in str(anomaly["timestamp"]) else None,
                    message=anomaly["deviation_desc"],
                    evidence_snippet=f"Metric: {anomaly['metric']}, Value: {anomaly['value']}, Mean: {anomaly['mean']}, Z-Score: {anomaly['z_score']}"
                )
            )
            
    return {"findings": state.get("findings", []) + findings}

def run_deploy_analyst_agent(state: IncidentState) -> Dict[str, Any]:
    findings = []
    raw_deploy = state.get("raw_deployment_data")
    
    if raw_deploy:
        # Run tools via Agent shell
        diffs = deploy_agent.execute_tool("compute_config_diff", raw_deploy)
        
        for diff in diffs:
            findings.append(
                AnalysisFinding(
                    agent_name=deploy_agent.name,
                    severity="WARNING" if diff["type"] == "MODIFIED" else "INFO",
                    message=diff["description"],
                    evidence_snippet=f"Change [{diff['type']}]: {diff['key']} => {diff['current']} (previously: {diff['previous']})"
                )
            )
            
    return {"findings": state.get("findings", []) + findings}
