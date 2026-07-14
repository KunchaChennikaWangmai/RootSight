from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from app.api.schemas import (
    IncidentPayload,
    AnalysisFinding,
    CorrelatedEvidence,
    RootCauseAnalysis,
    RecommendedAction
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
    findings: List[AnalysisFinding]
    
    # Correlation & Synthesis Phase outputs
    timeline: List[CorrelatedEvidence]
    root_cause: Optional[RootCauseAnalysis]
    recommendations: List[RecommendedAction]
    
    # Final Presentation output
    markdown_report: str
    status: str
