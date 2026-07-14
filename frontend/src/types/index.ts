// Shared TypeScript types matching FastAPI Pydantic schemas

export interface AnalysisFinding {
    agent_name: string;
    severity: 'INFO' | 'WARNING' | 'CRITICAL';
    timestamp?: string;
    message: string;
    evidence_snippet?: string;
}

export interface CorrelatedEvidence {
    timestamp: string;
    sources: string[];
    description: string;
    impact_level: 'INFO' | 'WARNING' | 'CRITICAL';
}

export interface CorrelationEvidenceMap {
    timestamp_range: string;
    grouped_findings: AnalysisFinding[];
    events_timeline: CorrelatedEvidence[];
}

export interface HypothesisItem {
    rank: number;
    probable_root_cause: string;
    confidence_score: number;
    supporting_evidence: string[];
    alternative_rejected_reason: string;
    recommended_remediations: RecommendedAction[];
}

export interface HypothesisOutput {
    top_hypotheses: HypothesisItem[];
    sre_summary: string;
    key_assumptions: string[];
}

export interface RecommendedAction {
    action_type: 'HOTFIX' | 'REFACTOR' | 'CONFIG' | 'RUNBOOK';
    description: string;
    command_or_code?: string;
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface RootCauseAnalysis {
    primary_trigger: string;
    direct_cause: string;
    mitigation_urgency: 'LOW' | 'MEDIUM' | 'HIGH' | 'IMMEDIATE';
    explanation: string;
}

export interface ReportJSON {
    incident_id: string;
    title: string;
    status: string;
    analysis_completed_at: string;
    evidence_summary: CorrelationEvidenceMap;
    hypothesis: HypothesisOutput;
    remediation_recommendations: RecommendedAction[];
}

export interface InvestigationReportResponse {
    incident_id: string;
    status: string;
    findings: AnalysisFinding[];
    timeline: CorrelatedEvidence[];
    root_cause?: RootCauseAnalysis;
    recommendations: RecommendedAction[];
    markdown_report: string;
    evidence?: CorrelationEvidenceMap;
    hypothesis?: HypothesisOutput;
    report_json?: ReportJSON;
}

// Upload payload types
export interface IncidentPayload {
    title: string;
    description?: string;
    logs?: { filename: string; content: string };
    stack_trace?: { filename: string; content: string };
    metrics?: { filename: string; data: object[] };
    deployment?: object;
}

// Dashboard list item
export interface InvestigationListItem {
    incident_id: string;
    title: string;
    status: string;
    findings_count: number;
    recommendations_count: number;
}

// Local agent progress state (frontend only)
export type AgentStatus = 'waiting' | 'running' | 'completed' | 'error' | 'skipped';

export interface AgentProgressItem {
    id: string;
    name: string;
    description: string;
    status: AgentStatus;
    startedAt?: string;
    completedAt?: string;
}
