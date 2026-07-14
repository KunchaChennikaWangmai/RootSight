from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# Upload Sub-models
class LogArtifact(BaseModel):
    filename: str = Field(..., description="Name of the log file")
    content: str = Field(..., description="Raw log lines or text content")

class StackArtifact(BaseModel):
    filename: str = Field(..., description="Name of the stack trace file")
    content: str = Field(..., description="Raw stack trace traceback text")

class MetricPoint(BaseModel):
    timestamp: str = Field(..., description="ISO 8601 or unix timestamp")
    cpu_percent: Optional[float] = Field(None, description="CPU usage percentage")
    memory_percent: Optional[float] = Field(None, description="Memory usage percentage")
    latency_ms: Optional[float] = Field(None, description="API Latency in milliseconds")
    error_rate: Optional[float] = Field(None, description="API Error rate (percentage or fraction)")
    custom_metrics: Dict[str, Any] = Field(default_factory=dict, description="Additional custom metrics key-values")

class MetricsArtifact(BaseModel):
    filename: str = Field(..., description="Name of the metrics JSON file")
    data: List[MetricPoint] = Field(..., description="Chronological series of system metrics points")

class DeploymentArtifact(BaseModel):
    filename: str = Field(..., description="Name of the deployment metadata JSON file")
    environment: str = Field("production", description="Deploy target (e.g. production, staging)")
    version: str = Field(..., description="App release semantic version or commit hash")
    config_vars: Dict[str, str] = Field(default_factory=dict, description="Application environment variables")
    deployed_at: str = Field(..., description="ISO 8601 deploy timestamp")

# Request Model
class IncidentPayload(BaseModel):
    title: str = Field(..., description="A short name or summary of the incident")
    description: Optional[str] = Field(None, description="User provided context or symptoms")
    logs: Optional[LogArtifact] = Field(None, description="Application log file")
    stack_trace: Optional[StackArtifact] = Field(None, description="Raw thread dump/stack trace")
    metrics: Optional[MetricsArtifact] = Field(None, description="System metrics timelines")
    deployment: Optional[DeploymentArtifact] = Field(None, description="System revision and configuration info")

# Response Sub-models
class AnalysisFinding(BaseModel):
    agent_name: str = Field(..., description="Agent that produced the finding")
    severity: str = Field("INFO", description="Severity level: INFO, WARNING, CRITICAL")
    timestamp: Optional[datetime] = Field(None, description="Specific time at which finding was detected")
    message: str = Field(..., description="Semantic summary of what the agent observed")
    evidence_snippet: Optional[str] = Field(None, description="Extracted code syntax, log line, or config line")

class CorrelatedEvidence(BaseModel):
    timestamp: datetime = Field(..., description="Unified timestamp of the correlated events")
    sources: List[str] = Field(..., description="Sources contributing to this event (e.g. ['log', 'metric'])")
    description: str = Field(..., description="Chronological explanation of events happening simultaneously")
    impact_level: str = Field("INFO", description="Impact of this correlated node (INFO, WARNING, CRITICAL)")

class RootCauseAnalysis(BaseModel):
    primary_trigger: str = Field(..., description="Direct active system trigger or code pathway change that caused the issue")
    direct_cause: str = Field(..., description="Immediate downstream mechanical failure or logical bug")
    mitigation_urgency: str = Field("MEDIUM", description="Remediation urgency: LOW, MEDIUM, HIGH, IMMEDIATE")
    explanation: str = Field(..., description="A comprehensive 5-Whys reasoned chain explanation of the issue")

class RecommendedAction(BaseModel):
    action_type: str = Field(..., description="Type of fix: HOTFIX, REFACTOR, CONFIG, RUNBOOK")
    description: str = Field(..., description="Detailed instructions on how to patch the issue")
    command_or_code: Optional[str] = Field(None, description="Command to execute or code diff suggestion")
    risk_level: str = Field("LOW", description="Risk of execution (LOW, MEDIUM, HIGH)")

# E2E Incident Workflow additions
class CorrelationEvidenceMap(BaseModel):
    timestamp_range: str = Field(..., description="Start and end window of the incident environment")
    grouped_findings: List[AnalysisFinding] = Field(default_factory=list, description="All parsed findings across modules")
    events_timeline: List[CorrelatedEvidence] = Field(default_factory=list, description="Chronological log and metrics intersections")

class HypothesisOutput(BaseModel):
    probable_root_cause: str = Field(..., description="LLM reasoned probable cause")
    confidence_score: float = Field(..., description="Confidence fraction between 0.0 and 1.0")
    reasoning: List[str] = Field(default_factory=list, description="Step-by-step logic chains")
    assumptions: List[str] = Field(default_factory=list, description="Presumed facts that need verification")

class ReportJSON(BaseModel):
    incident_id: str = Field(..., description="Unique generated identifier")
    title: str = Field(..., description="Incident title")
    status: str = Field("COMPLETED")
    analysis_completed_at: datetime = Field(default_factory=datetime.now)
    evidence_summary: CorrelationEvidenceMap = Field(..., description="Grouped evidence details")
    hypothesis: HypothesisOutput = Field(..., description="LLM evaluated root cause hypothesis")
    remediation_recommendations: List[RecommendedAction] = Field(default_factory=list)

# Primary Response Model
class InvestigationReportResponse(BaseModel):
    incident_id: str = Field(..., description="Unique generated identifier for the incident investigation")
    status: str = Field("COMPLETED", description="Status of investigation: COMPLETED, FAILED")
    findings: List[AnalysisFinding] = Field(default_factory=list, description="Observations from specific agents")
    timeline: List[CorrelatedEvidence] = Field(default_factory=list, description="Chronologically correlated evidence network")
    root_cause: Optional[RootCauseAnalysis] = Field(None, description="Primary root cause identification")
    recommendations: List[RecommendedAction] = Field(default_factory=list, description="Remediation and fixing instructions")
    markdown_report: str = Field(..., description="Formated, presentable markdown report of the incident")
    
    # E2E Additions
    evidence: Optional[CorrelationEvidenceMap] = Field(None, description="Structured evidence object")
    hypothesis: Optional[HypothesisOutput] = Field(None, description="Structured hypothesis evaluation")
    report_json: Optional[ReportJSON] = Field(None, description="Final structured JSON report")

