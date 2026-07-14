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
    ReportJSON
)
from app.core.base_agent import BaseAgent
from app.core.llm_service import call_hypothesis_llm

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
            
        timeline.append(
            CorrelatedEvidence(
                timestamp=timestamp,
                sources=[source_name],
                description=finding.message,
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

    # Append correlation log finding to indicate correlation ran
    correlation_finding = AnalysisFinding(
        agent_name=correlation_agent.name,
        severity="INFO",
        message=f"Linked {len(timeline)} findings in incident window: {time_window}.",
        evidence_snippet=f"Timeline covers {len(timeline)} points."
    )

    return {
        "timeline": timeline,
        "evidence": evidence_map,
        "findings": findings + [correlation_finding]
    }

def run_hypothesis_agent(state: IncidentState) -> Dict[str, Any]:
    """
    Hypothesis Agent:
    Calls LLM or Fallback heuristcs to form a probable root cause, confidence score, reasoning keys, and assumptions.
    """
    findings = state.get("findings", [])
    raw_logs = state.get("raw_logs", "")
    timeline = state.get("timeline", [])
    
    # Build timeline outline string for LLM prompt
    timeline_desc = "\n".join(
        f"- [{t.timestamp.strftime('%H:%M:%S') if hasattr(t.timestamp, 'strftime') else str(t.timestamp)}][{','.join(t.sources)}] {t.description}"
        for t in timeline
    )
    
    # Invoke structured LLM Call
    hypothesis = call_hypothesis_llm(findings, raw_logs, timeline_desc)
    
    return {
        "hypothesis": hypothesis
    }

def run_report_agent(state: IncidentState) -> Dict[str, Any]:
    """
    Report Agent:
    Compiles findings, timeline, and hypothesis into a final ReportJSON structured format.
    Generates a matching formatted markdown report for UI visualizations.
    """
    evidence: CorrelationEvidenceMap = state.get("evidence")
    hypothesis: HypothesisOutput = state.get("hypothesis")
    recommendations: List[RecommendedAction] = state.get("recommendations", [])
    
    # Extract remediations from the top hypothesis if available
    cause_remediations = []
    if hypothesis and hypothesis.top_hypotheses:
        cause_remediations = hypothesis.top_hypotheses[0].recommended_remediations
        
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
        remediation_recommendations=all_recommendations
    )
    
    # Build senior SRE styled markdown report
    top_cause_desc = hypothesis.top_hypotheses[0].probable_root_cause if hypothesis.top_hypotheses else "Unknown"
    top_confidence = f"{int(hypothesis.top_hypotheses[0].confidence_score * 100)}%" if hypothesis.top_hypotheses else "0%"
    
    md = f"""# ROOTCAUSE INCIDENT REPORT: {report_json.title.upper()}
**Incident ID:** `{report_json.incident_id}`
**Generated:** `{report_json.analysis_completed_at.strftime('%Y-%m-%d %H:%M:%S')}`
**Status:** `ANALYSIS COMPLETED`

---

## 1. Executive Summary
The system has completed an automated incident investigation workflow using LangGraph orchestration.

### SRE Overview Summary
{hypothesis.sre_summary}

### Primary Root Cause Hypothesis
- **Probable Cause:** {top_cause_desc}
- **Confidence Score:** `{top_confidence}`

---

## 2. Ranked Hypotheses Analysis
"""
    for h in hypothesis.top_hypotheses:
        md += f"### Rank #{h.rank}: {h.probable_root_cause}\n"
        md += f"- **Confidence Level:** `{int(h.confidence_score * 100)}%`\n"
        md += "- **Supporting Evidence:**\n"
        for ev in h.supporting_evidence:
            md += f"  * {ev}\n"
        md += f"- **Alternative Hypothesis Rejection Logic:** {h.alternative_rejected_reason}\n\n"

    md += "\n### Operational Key Assumptions\n"
    for a in hypothesis.key_assumptions:
        md += f"- {a}\n"

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
