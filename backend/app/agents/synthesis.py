from typing import Dict, Any, List
from datetime import datetime
from app.core.state import IncidentState
from app.api.schemas import (
    CorrelatedEvidence,
    RootCauseAnalysis,
    RecommendedAction,
    AnalysisFinding
)
from app.core.base_agent import BaseAgent

# ==========================================
# Synthesis Agent instantiations
# ==========================================
correlation_agent = BaseAgent(
    name="Correlation Agent",
    role="Event Correlation",
    system_prompt="Responsible for mapping and linking findings from disparate system sources into a timeline."
)

rca_agent = BaseAgent(
    name="Root Cause Analysis Agent",
    role="Deductive Specialist",
    system_prompt="Responsible for tracing events chronologically to formulate a 5-Whys diagnostic chain."
)

recommender_agent = BaseAgent(
    name="Recommendation Agent",
    role="Resolution Planner",
    system_prompt="Responsible for producing concrete immediate hotfixes and long-term operating runbooks."
)

report_agent = BaseAgent(
    name="Report Generator Agent",
    role="Report Compiler",
    system_prompt="Responsible for aggregating outputs of all agents into a production-ready Markdown report."
)

# ==========================================
# LangGraph node executors
# ==========================================
def run_correlation_agent(state: IncidentState) -> Dict[str, Any]:
    findings: List[AnalysisFinding] = state.get("findings", [])
    timeline: List[CorrelatedEvidence] = []
    base_time = datetime.now()
    
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
            
        timeline.append(
            CorrelatedEvidence(
                timestamp=timestamp,
                sources=[source_name],
                description=finding.message,
                impact_level=finding.severity
            )
        )
        
    timeline.sort(key=lambda item: item.timestamp)
    
    correlation_finding = AnalysisFinding(
        agent_name=correlation_agent.name,
        severity="INFO",
        message=f"Linked {len(timeline)} findings into a chronological path correlation.",
        evidence_snippet=f"Timestamps mapped between {min(t.timestamp for t in timeline) if timeline else None} and {max(t.timestamp for t in timeline) if timeline else None}"
    )

    return {
        "timeline": timeline,
        "findings": findings + [correlation_finding]
    }

def run_rca_agent(state: IncidentState) -> Dict[str, Any]:
    findings = state.get("findings", [])
    timeline = state.get("timeline", [])
    
    has_deploy = any("Deployment" in f.agent_name for f in findings)
    has_code_error = any("Stack Trace" in f.agent_name for f in findings)
    has_metrics_spike = any("Metrics" in f.agent_name for f in findings)
    
    primary_trigger = "Unknown system state transition"
    direct_cause = "Unhandled runtime disruption"
    explanation = "Critical runtime failure was encountered but insufficient input metrics/configs were provided to build a detailed root cause chain."
    urgency = "MEDIUM"
    
    if has_deploy and has_metrics_spike and has_code_error:
        primary_trigger = "Recent deployment environment configuration modification"
        direct_cause = "Environment/resource parameters starvation causing downstream runtime exceptions"
        explanation = (
            "1. Why: The application crashed returning uncaught runtime exceptions.\n"
            "2. Why: The JVM/runtime pool was exhausted, causing memory/latency spikes.\n"
            "3. Why: A recent deployment configuration modified pool boundaries without testing.\n"
            "4. Why: Evidence suggests the CPU peaked/resource configuration was decreased in deployment parameters.\n"
            "5. Why: Lack of multi-env config validation allowed incorrect environment limits to pass to production."
        )
        urgency = "HIGH"
    elif has_code_error:
        type_finding = next((f for f in findings if "Stack Trace" in f.agent_name), None)
        exc_info = type_finding.message if type_finding else "traceback code error"
        primary_trigger = "Trigger code execution pathway"
        direct_cause = exc_info
        explanation = f"1. Why: Code throw exception error: {exc_info}.\n2. Why: Input parameters violated conditions.\n3. Why: Validation logic was missing or bypassed."
        urgency = "HIGH"
    elif has_metrics_spike:
        metric_finding = next((f for f in findings if "Metrics" in f.agent_name), None)
        metric_info = metric_finding.message if metric_finding else "metric outlier"
        primary_trigger = "Traffic load surge or system block"
        direct_cause = metric_info
        explanation = f"1. Why: Metric spike observed: {metric_info}.\n2. Why: System reached capacity threshold limits.\n3. Why: Missing alert trigger lines."
        
    rca = RootCauseAnalysis(
        primary_trigger=primary_trigger,
        direct_cause=direct_cause,
        mitigation_urgency=urgency,
        explanation=explanation
    )
    
    return {"root_cause": rca}

def run_recommender_agent(state: IncidentState) -> Dict[str, Any]:
    rca: RootCauseAnalysis = state.get("root_cause")
    recommendations: List[RecommendedAction] = []
    
    if rca:
        if "deployment" in rca.primary_trigger.lower():
            recommendations.append(
                RecommendedAction(
                    action_type="CONFIG",
                    description="Rollback the recent environment configuration changes immediately.",
                    command_or_code="kubectl rollout undo deployment/rootsight-app",
                    risk_level="LOW"
                )
            )
            recommendations.append(
                RecommendedAction(
                    action_type="RUNBOOK",
                    description="Audit capacity limits against previous stable version settings before setting release config vars.",
                    risk_level="LOW"
                )
            )
        elif "code" in rca.primary_trigger.lower() or "exception" in rca.direct_cause.lower():
            recommendations.append(
                RecommendedAction(
                    action_type="HOTFIX",
                    description="Deliver hotfix adding null-checks or bounding conditions to prevent the index out of bounds or exception.",
                    command_or_code="try:\n    # code block\nexcept Exception as e:\n    logger.error('Graceful failure')\n    return default",
                    risk_level="MEDIUM"
                )
            )
        else:
            recommendations.append(
                RecommendedAction(
                    action_type="RUNBOOK",
                    description="Initiate node/container restarts to flush thread pool locks.",
                    command_or_code="docker restart $(docker ps -q)",
                    risk_level="MEDIUM"
                )
            )
    else:
        recommendations.append(
            RecommendedAction(
                action_type="RUNBOOK",
                description="Review application architecture logs manually to extract context.",
                risk_level="LOW"
            )
        )
        
    return {"recommendations": recommendations}

def run_report_generator_agent(state: IncidentState) -> Dict[str, Any]:
    title = state.get("title", "Production Incident Analysis")
    incident_id = state.get("incident_id")
    findings = state.get("findings", [])
    timeline = state.get("timeline", [])
    rca: RootCauseAnalysis = state.get("root_cause")
    recs = state.get("recommendations", [])
    
    md = f"""# ROOTCAUSE INCIDENT REPORT: {title.upper()}
**Incident ID:** `{incident_id}`
**Generated:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
**Status:** `ANALYSIS COMPLETED`

---

## 1. Executive Summary
The system has completed an automated multi-agent investigation. A total of **{len(findings)} agent findings** were gathered, and **{len(timeline)} chronological nodes** were correlated.
"""

    if rca:
        md += f"""
### Root Cause Overview
- **Primary Trigger:** {rca.primary_trigger}
- **Direct Cause:** {rca.direct_cause}
- **Remediation Urgency:** `{rca.mitigation_urgency}`

### Reasoning Chain (5-Whys)
```
{rca.explanation}
```
"""
    else:
        md += "\n*No definitive root cause could be synthesized due to incomplete input parameters.*\n"

    md += "\n## 2. Chronological Timeline\n"
    if timeline:
        md += "| Time | Source | Severity | Event Description |\n"
        md += "| :--- | :--- | :--- | :--- |\n"
        for item in timeline:
            time_str = item.timestamp.strftime('%H:%M:%S') if hasattr(item.timestamp, 'strftime') else str(item.timestamp)
            sources_str = ", ".join(item.sources)
            md += f"| {time_str} | {sources_str} | `{item.impact_level}` | {item.description} |\n"
    else:
        md += "*Timeline correlation is empty.*\n"

    md += "\n## 3. Detailed Findings by Agent\n"
    for idx, f in enumerate(findings, 1):
        md += f"### {idx}. {f.agent_name} ({f.severity})\n"
        md += f"- **Message:** {f.message}\n"
        if f.evidence_snippet:
            md += f"- **Evidence:**\n  ```\n  {f.evidence_snippet}\n  ```\n"
        md += "\n"

    md += "\n## 4. Actionable Remediation Actions\n"
    if recs:
        for idx, rec in enumerate(recs, 1):
            md += f"### Recovery Action #{idx}: {rec.action_type} (Risk: `{rec.risk_level}`)\n"
            md += f"- **Description:** {rec.description}\n"
            if rec.command_or_code:
                md += f"- **Execution Script/Code:**\n  ```bash\n  {rec.command_or_code}\n  ```\n"
            md += "\n"
    else:
        md += "*No explicit remediation actions defined.*\n"
        
    return {"markdown_report": md, "status": "COMPLETED"}
