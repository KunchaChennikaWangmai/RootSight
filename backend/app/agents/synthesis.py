import json
from typing import Dict, Any, List
from datetime import datetime
from app.core.state import IncidentState
from app.api.schemas import (
    CorrelatedEvidence,
    RootCauseAnalysis,
    RecommendedAction,
    AnalysisFinding,
    CorrelationEvidenceMap,
    HypothesisOutput,
    ReportJSON,
    InvestigationEvidence,
    IncidentSummaryDetail,
    CorrelationItem
)
from app.core.base_agent import BaseAgent, debug_node
from app.core.llm_service import call_hypothesis_llm
import os

# ==========================================
# E2E Agent instantiations
# ==========================================
correlation_agent = BaseAgent(
    name="Evidence Correlation Agent",
    role="Structured Evidence Merger",
    system_prompt="Responsible for mapping and linking findings from disparate system sources into a timeline."
)

hypothesis_agent = BaseAgent(
    name="Hypothesis Agent",
    role="Deductive Specialist",
    system_prompt="Leverages generative AI to evaluate evidence and formulate incident hypotheses, confidence levels, and assumptions."
)

report_agent = BaseAgent(
    name="Report Agent",
    role="Structured JSON Report Compiler",
    system_prompt="Aggregates all findings, timeline elements, and LLM hypotheses into a final validated structured JSON object."
)

# Placeholder agent representations
recommender_agent = BaseAgent(
    name="Recommendation Agent (Placeholder)",
    role="Incident Mitigator",
    system_prompt="Generates resolutions checklist sheets."
)

# ==========================================
# LangGraph node executors
# ==========================================
@debug_node("EvidenceCorrelationAgent")
def run_correlation_agent(state: IncidentState) -> Dict[str, Any]:
    """
    Evidence Correlation Agent:
    Aggregates log findings and other records into a single structured Evidence Map object.
    Builds the chronological timeline intersections map.
    """
    findings: List[AnalysisFinding] = state.get("findings", [])
    timeline: List[CorrelatedEvidence] = []
    base_time = datetime.now()
    
    # Form chronological timeline items
    for idx, finding in enumerate(findings):
        timestamp = finding.timestamp or base_time
        source_name = "System"
        if "Log" in finding.agent_name:
            source_name = "log"
        elif "Stack" in finding.agent_name:
            source_name = "stack_trace"
        elif "Metrics" in finding.agent_name:
            source_name = "metric"
        elif "Deployment" in finding.agent_name:
            source_name = "deployment"
            
        desc = finding.message
        if finding.message.strip().startswith("{"):
            try:
                data = json.loads(finding.message)
                if source_name == "log":
                    desc = f"Log anomaly templates parsed with {len(data.get('exceptions', []))} exceptions and {data.get('payment_failures')} failed requests."
                elif source_name == "stack_trace":
                    desc = f"Stack failure: throw {data.get('exception_type')} in {data.get('class_name') or data.get('class')}.{data.get('method')} line {data.get('line')}."
                elif source_name == "metric":
                    desc = f"Metric thresholds breached: CPU/latency spike after (CPU: {data.get('cpu_after')}, Lat: {data.get('latency_after')}ms)."
                elif source_name == "deployment":
                    desc = f"Deployment release version {data.get('deployment_version')} completed."
            except Exception:
                pass
                
        timeline.append(
            CorrelatedEvidence(
                timestamp=timestamp,
                sources=[source_name],
                description=desc,
                impact_level=finding.severity
            )
        )
        
    timeline.sort(key=lambda item: item.timestamp)
    
    # Build Timestamp windows
    start_win = min(t.timestamp for t in timeline).strftime("%Y-%m-%d %H:%M:%S") if timeline else "No events"
    end_win = max(t.timestamp for t in timeline).strftime("%Y-%m-%d %H:%M:%S") if timeline else "No events"
    time_window = f"{start_win} to {end_win}"
    
    # Populate the structured evidence map
    evidence_map = CorrelationEvidenceMap(
        timestamp_range=time_window,
        grouped_findings=findings,
        events_timeline=timeline
    )

    # Gather evidence details
    log_evidence = state.get("log_evidence")
    stack_evidence = state.get("stack_evidence")
    metrics_evidence = state.get("metrics_evidence")
    deploy_evidence = state.get("deploy_evidence")

    # Build Incident Summary details
    service_name = "UnknownService"
    if stack_evidence and stack_evidence.class_name:
        service_name = stack_evidence.class_name
    elif log_evidence and log_evidence.exceptions:
        service_name = log_evidence.exceptions[0].class_name

    env_name = state.get("raw_deployment_data", {}).get("environment", "production") if state.get("raw_deployment_data") else "production"
    version_tag = deploy_evidence.deployment_version if deploy_evidence else "v1.0.0"

    summary_detail = IncidentSummaryDetail(
        service=service_name,
        environment=env_name,
        deployment_version=version_tag
    )

    # Correlate facts deterministically without summarizing
    correlations = []
    if deploy_evidence and log_evidence and len(log_evidence.exceptions) > 0:
        first_exc = log_evidence.exceptions[0]
        correlations.append(
            CorrelationItem(
                type="deployment_regression",
                description=f"{first_exc.type} started immediately after deployment version {deploy_evidence.deployment_version}."
            )
        )
    if metrics_evidence and metrics_evidence.cpu_after and metrics_evidence.cpu_after > 70.0:
        correlations.append(
            CorrelationItem(
                type="resource_impact",
                description="CPU usage and API transaction latencies increased sharply after application failures."
            )
        )

    # recommended focus paths
    recommended_focus = []
    if stack_evidence:
        recommended_focus.append(f"{stack_evidence.class_name}.{stack_evidence.method}()")
    elif log_evidence and log_evidence.exceptions:
        first_exc = log_evidence.exceptions[0]
        recommended_focus.append(f"{first_exc.class_name}.{first_exc.method}()")

    if deploy_evidence:
        recommended_focus.append(f"Deployment {deploy_evidence.deployment_version}")

    if log_evidence:
        if log_evidence.cache_initialization_delayed:
            recommended_focus.append("Cache initialization")
        if log_evidence.circuit_breaker_triggered:
            recommended_focus.append("Circuit breaker")

    # Build canonical InvestigationEvidence object
    exceptions_list = log_evidence.exceptions if log_evidence else []
    investigation_evidence = InvestigationEvidence(
        incident_summary=summary_detail,
        timeline=timeline,
        exceptions=exceptions_list,
        metrics=metrics_evidence,
        deployment=deploy_evidence,
        correlations=correlations,
        recommended_focus=recommended_focus
    )

    # Append correlation log finding to indicate correlation ran
    correlation_finding = AnalysisFinding(
        agent_name=correlation_agent.name,
        severity="INFO",
        message=f"Linked {len(timeline)} findings in incident window: {time_window}.",
        evidence_snippet=investigation_evidence.json(by_alias=True)
    )

    return {
        "timeline": timeline,
        "evidence": evidence_map,
        "investigation_evidence": investigation_evidence,
        "findings": [correlation_finding]
    }

@debug_node("RootCauseReasoningAgent")
def run_hypothesis_agent(state: IncidentState) -> Dict[str, Any]:
    """
    Hypothesis Agent:
    Calls LLM or Fallback heuristics to form a probable root cause, confidence score, reasoning keys, and assumptions.
    """
    evidence = state.get("investigation_evidence")
    
    # Debug print the exact InvestigationEvidence JSON sent to the LLM before inference in dev environment
    is_debug = os.getenv("DEBUG", "false").lower() == "true"
    is_dev = os.getenv("ENV", "development").lower() not in ["production", "prod"] and \
             os.getenv("FASTAPI_ENV", "development").lower() not in ["production", "prod"]
             
    if is_debug and is_dev and evidence:
        print("\n--- [DEBUG] Raw InvestigationEvidence JSON Sent to LLM ---")
        print(json.dumps(json.loads(evidence.json()), indent=2))
        print("----------------------------------------------------------\n")
        
    # Invoke structured LLM Call using ONLY the structured evidence
    hypothesis = call_hypothesis_llm(evidence)
    
    return {
        "hypothesis": hypothesis
    }

@debug_node("ReportAgent")
def run_report_agent(state: IncidentState) -> Dict[str, Any]:
    """
    Report Agent:
    Compiles findings, timeline, and hypothesis into a final ReportJSON structured format.
    Generates a matching formatted markdown report for UI visualizations.
    """
    evidence: CorrelationEvidenceMap = state.get("evidence")
    hypothesis: HypothesisOutput = state.get("hypothesis")
    recommendations: List[RecommendedAction] = state.get("recommendations", [])
    investigation_evidence = state.get("investigation_evidence")
    
    # Extract remediations from the primary hypothesis and secondary hypotheses if available
    cause_remediations = []
    if hypothesis and hypothesis.primary_hypothesis:
        for action in hypothesis.primary_hypothesis.recommended_actions:
            a_type = "CONFIG"
            if "rollback" in action.lower() or "undo" in action.lower():
                a_type = "CONFIG"
            elif "inspect" in action.lower() or "debug" in action.lower() or "fix" in action.lower():
                a_type = "CODE"
            else:
                a_type = "RUNBOOK"
            cause_remediations.append(
                RecommendedAction(
                    action_type=a_type,
                    description=action,
                    command_or_code=action if ("kubectl" in action or "export" in action or "git" in action) else None,
                    risk_level="MEDIUM" if "rollback" in action.lower() else "LOW"
                )
            )
            
    # Combine lists
    all_recommendations = list(recommendations)
    for rec in cause_remediations:
        if not any(r.description == rec.description for r in all_recommendations):
            all_recommendations.append(rec)
            
    if not all_recommendations:
        all_recommendations = [
            RecommendedAction(
                action_type="CONFIG",
                description="Adjust connection timeout limits and roll back recent configuration variations.",
                command_or_code="kubectl rollout undo deployment/rootsight-app",
                risk_level="LOW"
            )
        ]
         
    # Build ReportJSON
    report_json = ReportJSON(
        incident_id=state.get("incident_id"),
        title=state.get("title", "Incident Outage Report"),
        status="COMPLETED",
        analysis_completed_at=datetime.now(),
        evidence_summary=evidence,
        hypothesis=hypothesis,
        remediation_recommendations=all_recommendations,
        investigation_evidence=investigation_evidence
    )
    
    # Build senior SRE styled markdown report
    primary = hypothesis.primary_hypothesis if hypothesis else None
    top_cause_desc = primary.probable_root_cause if primary else "Unknown"
    top_confidence = f"{primary.confidence_score}%" if primary else "0%"
    
    md = f"""# ROOTCAUSE INCIDENT REPORT: {report_json.title.upper()}
**Incident ID:** `{report_json.incident_id}`
**Generated:** `{report_json.analysis_completed_at.strftime('%Y-%m-%d %H:%M:%S')}`
**Status:** `ANALYSIS COMPLETED`

---

## 1. Executive Summary
The system has completed an automated incident investigation workflow using LangGraph orchestration.

### SRE Overview Summary
{hypothesis.executive_summary if hypothesis else "No summary available."}

### Primary Root Cause Hypothesis
- **Probable Cause:** {top_cause_desc}
- **Confidence Score:** `{top_confidence}`

---

## 2. Ranked Hypotheses Analysis
"""
    if primary:
        rejected = "\n".join(f"  * {r}" for r in primary.rejected_alternative_hypotheses) if primary.rejected_alternative_hypotheses else "  * None"
        evidence_points = "\n".join(f"  * {e}" for e in primary.supporting_evidence) if primary.supporting_evidence else "  * None"
        md += f"""### Rank #1: {primary.probable_root_cause}
- **Confidence Level:** `{primary.confidence_score}%`
- **Why This Is Likely:** {primary.why_this_is_likely}
- **Supporting Evidence:**
{evidence_points}
- **Alternative Hypothesis Rejection Logic:**
{rejected}

"""

    if hypothesis and hypothesis.secondary_hypotheses:
        for sec in hypothesis.secondary_hypotheses:
            rejected = "\n".join(f"  * {r}" for r in sec.rejected_alternative_hypotheses) if sec.rejected_alternative_hypotheses else "  * None"
            evidence_points = "\n".join(f"  * {e}" for e in sec.supporting_evidence) if sec.supporting_evidence else "  * None"
            md += f"""### Rank #{sec.rank}: {sec.probable_root_cause}
- **Confidence Level:** `{sec.confidence_score}%`
- **Why This Is Likely:** {sec.why_this_is_likely}
- **Supporting Evidence:**
{evidence_points}
- **Alternative Hypothesis Rejection Logic:**
{rejected}

"""

    md += """
---

## 3. Chronological Timeline
| Time | Source | Severity | Event Description |
| :--- | :--- | :--- | :--- |
"""
    for item in evidence.events_timeline:
        time_str = item.timestamp.strftime('%H:%M:%S') if hasattr(item.timestamp, 'strftime') else str(item.timestamp)
        sources_str = ", ".join(item.sources)
        md += f"| {time_str} | {sources_str} | `{item.impact_level}` | {item.description} |\n"

    md += "\n## 4. Recommended Remediation Actions\n"
    for idx, rec in enumerate(all_recommendations, 1):
        md += f"### Action #{idx}: {rec.action_type} (Risk: `{rec.risk_level}`)\n"
        md += f"- **Description:** {rec.description}\n"
        if rec.command_or_code:
            md += f"- **Code/Fix Script:**\n  ```bash\n  {rec.command_or_code}\n  ```\n"

    return {
        "report_json": report_json,
        "recommendations": all_recommendations,
        "markdown_report": md,
        "status": "COMPLETED"
    }

# Stub of previous rca and recommender so state maps compilation don't break
def run_rca_agent(state: IncidentState) -> Dict[str, Any]:
    # Placeholder: bypassed in actual workflow
    return {}

def run_recommender_agent(state: IncidentState) -> Dict[str, Any]:
    # Placeholder: bypassed in actual workflow
    return {}
