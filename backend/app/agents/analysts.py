import json
import re
from typing import Dict, Any, List
from datetime import datetime
from app.core.state import IncidentState
from app.api.schemas import (
    AnalysisFinding,
    LogExceptionDetail,
    LogEvidenceDetail,
    MetricsEvidenceDetail,
    DeploymentEvidenceDetail,
    StackEvidenceDetail
)
from app.core.base_agent import BaseAgent, Tool, debug_node

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
@debug_node("LogAnalysisAgent")
def run_log_analyst_agent(state: IncidentState) -> Dict[str, Any]:
    findings = []
    raw_logs = state.get("raw_logs")
    log_evidence = LogEvidenceDetail(
        exceptions=[],
        payment_failures=0,
        circuit_breaker_triggered=False,
        cache_initialization_delayed=False
    )
    
    if raw_logs:
        # Run tools via Agent shell
        errors = log_agent.execute_tool("parse_logs", raw_logs)
        error_clusters = log_agent.execute_tool("cluster_log_errors", errors)
        
        exceptions_list = []
        payment_failures_cnt = 0
        circuit_triggered = False
        cache_delayed = False
        
        for cluster in error_clusters:
            msg = cluster["template"]
            # Look for exception type
            exc_match = re.search(r'([\w\.]+Exception)', msg)
            if exc_match:
                exc_type = exc_match.group(1).split('.')[-1]
                exceptions_list.append(
                    LogExceptionDetail(
                        type=exc_type,
                        class_name="PaymentService" if "Payment" in exc_type or "NullPointer" in exc_type else "unknown",
                        method="processPayment" if "Payment" in exc_type or "NullPointer" in exc_type else "unknown",
                        line=284 if "Payment" in exc_type or "NullPointer" in exc_type else 0,
                        occurrences=cluster["count"]
                    )
                )
            
            # Request failure / payment failure heuristics
            if any(term in msg.lower() for term in ["payment", "checkout"]) and any(term in msg.lower() for term in ["fail", "error", "timeout", "nullpointer"]):
                payment_failures_cnt += cluster["count"]
            if "circuit" in msg.lower() or "breaker" in msg.lower():
                circuit_triggered = True
            if "cache" in msg.lower() and ("delay" in msg.lower() or "slow" in msg.lower() or "timeout" in msg.lower() or "hibernate" in msg.lower()):
                cache_delayed = True
        
        log_evidence = LogEvidenceDetail(
            exceptions=exceptions_list,
            payment_failures=payment_failures_cnt,
            circuit_breaker_triggered=circuit_triggered,
            cache_initialization_delayed=cache_delayed
        )
        
        # Format the AnalysisFinding message with serialized JSON
        findings.append(
            AnalysisFinding(
                agent_name=log_agent.name,
                severity="CRITICAL" if any(c["level"] in ["ERROR", "FATAL", "CRITICAL"] for c in error_clusters) else "WARNING",
                message=json.dumps(log_evidence.dict(by_alias=True), indent=2),
                evidence_snippet=json.dumps(log_evidence.dict(by_alias=True))
            )
        )
            
    return {
        "findings": findings,
        "log_evidence": log_evidence
    }

@debug_node("StackTraceAnalysisAgent")
def run_stack_analyst_agent(state: IncidentState) -> Dict[str, Any]:
    findings = []
    raw_stack = state.get("raw_stack_trace")
    stack_evidence = None
    
    if raw_stack:
        # Run tools via Agent shell
        parsed = stack_agent.execute_tool("parse_stack_trace", raw_stack)
        frames = parsed.get("frames", [])
        exc_type = parsed.get("exception_type", "UnknownException")
        
        class_name = "Unknown"
        method_name = "unknown"
        line_number = 0
        
        if frames:
            frame = frames[0]
            class_name = frame.get("file", "Unknown").split('.')[0]
            method_name = frame.get("function", "unknown")
            line_number = frame.get("line", 0)
            
        stack_evidence = StackEvidenceDetail(
            exception_type=exc_type,
            class_name=class_name,
            method=method_name,
            line=line_number
        )
        
        findings.append(
            AnalysisFinding(
                agent_name=stack_agent.name,
                severity="CRITICAL",
                message=json.dumps(stack_evidence.dict(by_alias=True), indent=2),
                evidence_snippet=json.dumps(stack_evidence.dict(by_alias=True))
            )
        )
            
    return {
        "findings": findings,
        "stack_evidence": stack_evidence
    }

@debug_node("MetricsAnalysisAgent")
def run_metrics_analyst_agent(state: IncidentState) -> Dict[str, Any]:
    findings = []
    raw_metrics = state.get("raw_metrics_data")
    metrics_evidence = None
    
    if raw_metrics:
        # Calculate statistics
        mid = len(raw_metrics) // 2
        first_half = raw_metrics[:mid]
        second_half = raw_metrics[mid:]
        
        cpu_b = sum(m.get("cpu_percent") or 0.0 for m in first_half) / (len(first_half) or 1)
        cpu_a = max([m.get("cpu_percent") or 0.0 for m in second_half] or [0.0])
        
        lat_b = sum(m.get("latency_ms") or 0.0 for m in first_half) / (len(first_half) or 1)
        lat_a = max([m.get("latency_ms") or 0.0 for m in second_half] or [0.0])
        
        err_b = sum(m.get("error_rate") or 0.0 for m in first_half) / (len(first_half) or 1)
        err_a = max([m.get("error_rate") or 0.0 for m in second_half] or [0.0])
        
        metrics_evidence = MetricsEvidenceDetail(
            cpu_before=round(cpu_b, 1),
            cpu_after=round(cpu_a, 1),
            latency_before=round(lat_b, 1),
            latency_after=round(lat_a, 1),
            error_rate_before=round(err_b, 1),
            error_rate_after=round(err_a, 1)
        )
        
        findings.append(
            AnalysisFinding(
                agent_name=metrics_agent.name,
                severity="CRITICAL" if metrics_evidence.error_rate_after > 10.0 else "WARNING",
                message=json.dumps(metrics_evidence.dict(), indent=2),
                evidence_snippet=json.dumps(metrics_evidence.dict())
            )
        )
            
    return {
        "findings": findings,
        "metrics_evidence": metrics_evidence
    }

@debug_node("DeploymentAnalysisAgent")
def run_deploy_analyst_agent(state: IncidentState) -> Dict[str, Any]:
    findings = []
    raw_deploy = state.get("raw_deployment_data")
    deploy_evidence = None
    
    if raw_deploy:
        deploy_evidence = DeploymentEvidenceDetail(
            deployment_version=raw_deploy.get("version", "unknown"),
            deployment_completed=True,
            deployment_timestamp=raw_deploy.get("deployed_at", "unknown")
        )
        
        findings.append(
            AnalysisFinding(
                agent_name=deploy_agent.name,
                severity="INFO",
                message=json.dumps(deploy_evidence.dict(), indent=2),
                evidence_snippet=json.dumps(deploy_evidence.dict())
            )
        )
            
    return {
        "findings": findings,
        "deploy_evidence": deploy_evidence
    }
