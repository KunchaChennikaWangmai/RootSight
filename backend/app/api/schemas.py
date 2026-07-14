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

class HypothesisDetail(BaseModel):
    rank: int = Field(..., description="Likelihood rank starting at 1")
    probable_root_cause: str = Field(..., description="Root cause detail description")
    confidence_score: int = Field(..., description="Confidence score from 0 to 100")
    why_this_is_likely: str = Field(..., description="Detailed explanation why this hypothesis is likely")
    supporting_evidence: List[str] = Field(default_factory=list, description="List of supporting evidence citations")
    rejected_alternative_hypotheses: List[str] = Field(default_factory=list, description="List of rejected alternative hypotheses with reasons")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended remediation actions")

class HypothesisOutput(BaseModel):
    executive_summary: str = Field(..., description="Senior SRE executive synthesis of the incident")
    primary_hypothesis: HypothesisDetail = Field(..., description="The main most probable root cause hypothesis")
    secondary_hypotheses: List[HypothesisDetail] = Field(default_factory=list, description="List of alternative second/third ranked hypotheses")

class ReportJSON(BaseModel):
    incident_id: str = Field(..., description="Unique generated identifier")
    title: str = Field(..., description="Incident title")
    status: str = Field("COMPLETED")
    analysis_completed_at: datetime = Field(default_factory=datetime.now)
    evidence_summary: CorrelationEvidenceMap = Field(..., description="Grouped evidence details")
    hypothesis: HypothesisOutput = Field(..., description="LLM evaluated root cause hypothesis")
    remediation_recommendations: List[RecommendedAction] = Field(default_factory=list)

# Structured SRE Evidence schemas
class LogExceptionDetail(BaseModel):
    type: str = Field(..., description="Exception class type")
    class_name: str = Field(..., alias="class", description="Target class containing the throw")
    method: str = Field(..., description="Target method containing the throw")
    line: int = Field(..., description="Line number of exception frame")
    occurrences: int = Field(..., description="Frequency of this exception")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True

class LogEvidenceDetail(BaseModel):
    exceptions: List[LogExceptionDetail] = Field(default_factory=list)
    payment_failures: int = Field(0, description="Number of observed payment failures")
    circuit_breaker_triggered: bool = Field(False, description="Whether circuit breaker triggered during incident")
    cache_initialization_delayed: bool = Field(False, description="Whether cache loading initialized late")

class MetricsEvidenceDetail(BaseModel):
    cpu_before: Optional[float] = Field(None, description="CPU usage before outbreak")
    cpu_after: Optional[float] = Field(None, description="CPU usage peak during outage")
    latency_before: Optional[float] = Field(None, description="API Latency average before incident")
    latency_after: Optional[float] = Field(None, description="API Latency average peak during incident")
    error_rate_before: Optional[float] = Field(None, description="Error rate before incident")
    error_rate_after: Optional[float] = Field(None, description="Error rate peak during incident")

class DeploymentEvidenceDetail(BaseModel):
    deployment_version: Optional[str] = Field(None, description="Deployed revision version tag")
    deployment_completed: bool = Field(False, description="Whether deployment finished booting successfully")
    deployment_timestamp: Optional[str] = Field(None, description="UTC time deployment finalized")

class StackEvidenceDetail(BaseModel):
    exception_type: Optional[str] = Field(None, description="The type of exception captured in stacktrace")
    class_name: Optional[str] = Field(None, alias="class", description="Target class containing the throw")
    method: Optional[str] = Field(None, description="Target method containing the throw")
    line: Optional[int] = Field(None, description="Line number containing the throw")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True

class IncidentSummaryDetail(BaseModel):
    service: str = Field(..., description="Service name where the issue occurred")
    environment: str = Field(..., description="Target environment (e.g. production, staging)")
    deployment_version: str = Field(..., description="Deployed semantic release version or commit hash")

class CorrelationItem(BaseModel):
    type: str = Field(..., description="Correlation pattern type")
    description: str = Field(..., description="Details and observations of the correlated systems")

class InvestigationEvidence(BaseModel):
    incident_summary: Optional[IncidentSummaryDetail] = None
    timeline: List[CorrelatedEvidence] = Field(default_factory=list)
    exceptions: List[LogExceptionDetail] = Field(default_factory=list)
    metrics: Optional[MetricsEvidenceDetail] = None
    deployment: Optional[DeploymentEvidenceDetail] = None
    correlations: List[CorrelationItem] = Field(default_factory=list)
    recommended_focus: List[str] = Field(default_factory=list)

class ReportJSON(BaseModel):
    incident_id: str = Field(..., description="Unique generated identifier")
    title: str = Field(..., description="Incident title")
    status: str = Field("COMPLETED")
    analysis_completed_at: datetime = Field(default_factory=datetime.now)
    evidence_summary: CorrelationEvidenceMap = Field(..., description="Grouped evidence details")
    hypothesis: HypothesisOutput = Field(..., description="LLM evaluated root cause hypothesis")
    remediation_recommendations: List[RecommendedAction] = Field(default_factory=list)
    investigation_evidence: Optional[InvestigationEvidence] = Field(None, description="Unified structured JSON evidence")

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
    investigation_evidence: Optional[InvestigationEvidence] = Field(None, description="Unified structured JSON evidence")

