import operator
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from datetime import datetime
from app.api.schemas import (
    IncidentPayload,
    AnalysisFinding,
    CorrelatedEvidence,
    RootCauseAnalysis,
    RecommendedAction,
    CorrelationEvidenceMap,
    HypothesisOutput,
    ReportJSON,
    InvestigationEvidence,
    LogEvidenceDetail,
    MetricsEvidenceDetail,
    DeploymentEvidenceDetail,
    StackEvidenceDetail
)

class IncidentState(TypedDict):
    # Raw incident inputs
    incident_id: str
    title: str
    description: Optional[str]
    raw_logs: Optional[str]
    raw_stack_trace: Optional[str]
    raw_metrics_data: Optional[List[Dict[str, Any]]]
    raw_deployment_data: Optional[Dict[str, Any]]
    
    # Run-time planning details
    agents_to_run: List[str]
    focus_areas: List[str]
    
    # Individual Agent Findings outputs (Appended)
    findings: Annotated[List[AnalysisFinding], operator.add]
    
    # Correlation & Synthesis Phase outputs
    timeline: List[CorrelatedEvidence]
    root_cause: Optional[RootCauseAnalysis]
    recommendations: List[RecommendedAction]
    
    # E2E Additions
    evidence: Optional[CorrelationEvidenceMap]
    hypothesis: Optional[HypothesisOutput]
    report_json: Optional[ReportJSON]
    investigation_evidence: Optional[InvestigationEvidence]
    
    # Individual Agent Evidence schemas (preserves data across nodes in LangGraph)
    log_evidence: Optional[LogEvidenceDetail]
    metrics_evidence: Optional[MetricsEvidenceDetail]
    deploy_evidence: Optional[DeploymentEvidenceDetail]
    stack_evidence: Optional[StackEvidenceDetail]
    
    # Final Presentation output
    markdown_report: str
    status: str
