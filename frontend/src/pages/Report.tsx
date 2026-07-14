import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    ArrowLeft,
    Download,
    AlertTriangle,
    CheckCircle2,
    BarChart3,
    FileText,
    Lightbulb,
    Shield,
    Clock,
    ChevronDown,
    ChevronUp,
    Loader2,
} from 'lucide-react';
import { investigationsApi } from '../services/api';
import type {
    InvestigationReportResponse,
    AnalysisFinding,
    CorrelatedEvidence,
    RecommendedAction,
} from '../types';

// ─── Sub-components ────────────────────────────────────────────────────────

function ConfidenceRing({ score }: { score: number }) {
    const pct = Math.round(score > 1 ? score : score * 100);
    const r = 40;
    const circ = 2 * Math.PI * r;
    const dash = (pct / 100) * circ;
    const color = pct >= 80 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444';

    return (
        <div className="flex flex-col items-center gap-1">
            <svg width={96} height={96} viewBox="0 0 96 96">
                <circle cx={48} cy={48} r={r} fill="none" stroke="#1e293b" strokeWidth={8} />
                <circle
                    cx={48}
                    cy={48}
                    r={r}
                    fill="none"
                    stroke={color}
                    strokeWidth={8}
                    strokeDasharray={`${dash} ${circ}`}
                    strokeLinecap="round"
                    transform="rotate(-90 48 48)"
                    style={{ transition: 'stroke-dasharray 1s ease' }}
                />
                <text x={48} y={48} dominantBaseline="middle" textAnchor="middle" fill={color} fontSize={16} fontWeight={700}>
                    {pct}%
                </text>
            </svg>
            <span className="text-[10px] text-slate-500">Confidence</span>
        </div>
    );
}

function SeverityBadge({ severity }: { severity: string }) {
    const map: Record<string, string> = {
        CRITICAL: 'badge-critical',
        WARNING: 'badge-warning',
        INFO: 'badge-info',
    };
    return <span className={map[severity] ?? 'badge-info'}>{severity}</span>;
}

function ActionTypeChip({ type }: { type: string }) {
    const map: Record<string, string> = {
        HOTFIX: 'bg-red-500/10 text-red-400 border-red-500/20',
        CONFIG: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
        RUNBOOK: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
        REFACTOR: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    };
    return (
        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${map[type] ?? 'badge-info'}`}>
            {type}
        </span>
    );
}

function Collapsible({ title, children, defaultOpen = true }: { title: React.ReactNode; children: React.ReactNode; defaultOpen?: boolean }) {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div className="glass-card overflow-hidden">
            <button
                onClick={() => setOpen((o) => !o)}
                className="w-full flex items-center justify-between px-5 py-4 border-b border-slate-800 hover:bg-slate-800/30 transition"
            >
                <div className="text-sm font-semibold text-white">{title}</div>
                {open ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
            </button>
            {open && <div className="p-5">{children}</div>}
        </div>
    );
}

// ─── PDF Export ────────────────────────────────────────────────────────────

async function exportPDF(report: InvestigationReportResponse) {
    // Dynamically import jspdf/autotable to keep initial bundle lean
    const { jsPDF } = await import('jspdf');
    const { default: autoTable } = await import('jspdf-autotable');

    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const margin = 40;
    let y = margin;

    const addTitle = (text: string, size = 18) => {
        doc.setFontSize(size);
        doc.setFont('helvetica', 'bold');
        doc.text(text, margin, y);
        y += size + 6;
    };
    const addText = (text: string, size = 10, indent = 0) => {
        doc.setFontSize(size);
        doc.setFont('helvetica', 'normal');
        const lines = doc.splitTextToSize(text, 515 - indent);
        doc.text(lines, margin + indent, y);
        y += lines.length * (size + 3) + 4;
    };
    const addGap = (n = 12) => { y += n; };

    addTitle('RootSight Incident Report', 18);
    addText(`Incident ID: ${report.incident_id}`, 9);
    addText(`Status: ${report.status}`, 9);
    addGap();

    if (report.hypothesis) {
        addTitle('Root Cause Overview', 13);
        addText(report.hypothesis.executive_summary || 'No overview summary available.');
        addGap();

        addTitle('Ranked Outage Hypotheses', 13);
        const primary = report.hypothesis.primary_hypothesis;
        if (primary) {
            addTitle(`Rank #1 (Primary): ${primary.probable_root_cause}`, 11);
            addText(`Confidence Score: ${primary.confidence_score}%`, 9, 8);
            addText('Supporting Evidence:', 9, 8);
            (primary.supporting_evidence || []).forEach((ev: string) => addText(`• ${ev}`, 8, 16));
            addText(`Alternative Rejection Logic: ${primary.rejected_alternative_hypotheses?.join(', ') || 'N/A'}`, 9, 8);
            addGap(8);
        }

        const secondaries = report.hypothesis.secondary_hypotheses || [];
        secondaries.forEach((h: any) => {
            addTitle(`Rank #${h.rank || 2}: ${h.probable_root_cause}`, 11);
            addText(`Confidence Score: ${h.confidence_score}%`, 9, 8);
            addText('Supporting Evidence:', 9, 8);
            (h.supporting_evidence || []).forEach((ev: string) => addText(`• ${ev}`, 8, 16));
            addText(`Alternative Rejection Logic: ${h.rejected_alternative_hypotheses?.join(', ') || 'N/A'}`, 9, 8);
            addGap(8);
        });
    }

    if (report.findings?.length) {
        addTitle('Agent Findings', 13);
        autoTable(doc, {
            startY: y,
            margin: { left: margin },
            head: [['Agent', 'Severity', 'Message']],
            body: report.findings.map((f) => [f.agent_name, f.severity, f.message]),
            styles: { fontSize: 8 },
            headStyles: { fillColor: [63, 63, 70] },
        });
        y = (doc as any).lastAutoTable.finalY + 14;
    }

    if (report.recommendations?.length) {
        addTitle('Recommendations', 13);
        report.recommendations.forEach((rec) => {
            addText(`[${rec.action_type}] ${rec.description}`, 9);
            if (rec.command_or_code) addText(rec.command_or_code, 8, 12);
            addGap(6);
        });
    }

    doc.save(`RootSight-${report.incident_id}.pdf`);
}

// ─── Main Page ─────────────────────────────────────────────────────────────

export default function ReportPage() {
    const { id } = useParams<{ id: string }>();
    const [report, setReport] = useState<InvestigationReportResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [exporting, setExporting] = useState(false);

    useEffect(() => {
        if (!id) return;
        investigationsApi
            .get(id)
            .then(setReport)
            .catch((e) => setError(e.message ?? 'Failed to load report'))
            .finally(() => setLoading(false));
    }, [id]);

    const handleExport = async () => {
        if (!report) return;
        setExporting(true);
        try {
            await exportPDF(report);
        } finally {
            setExporting(false);
        }
    };

    if (loading)
        return (
            <div className="flex flex-col items-center justify-center h-80 gap-4">
                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                <p className="text-sm text-slate-500">Loading investigation report…</p>
            </div>
        );

    if (error || !report)
        return (
            <div className="flex flex-col items-center justify-center h-80 gap-3">
                <AlertTriangle className="w-10 h-10 text-amber-400" />
                <p className="text-sm font-semibold text-white">Report not found</p>
                <p className="text-xs text-slate-500">{error}</p>
                <Link to="/" className="btn-ghost">
                    <ArrowLeft className="w-4 h-4" /> Back to Dashboard
                </Link>
            </div>
        );

    const { hypothesis, evidence, recommendations, findings, timeline } = report;
    const primaryHypothesis = hypothesis?.primary_hypothesis;
    const secondaryHypotheses = hypothesis?.secondary_hypotheses || [];

    return (
        <div className="max-w-4xl mx-auto space-y-5">
            {/* Header */}
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                    <Link to="/" className="btn-ghost text-slate-500">
                        <ArrowLeft className="w-4 h-4" />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-bold text-white">Investigation Report</h1>
                        <p className="text-xs text-slate-500 font-mono mt-0.5">{id}</p>
                    </div>
                </div>
                <button
                    onClick={handleExport}
                    disabled={exporting}
                    className="btn-primary shrink-0"
                >
                    {exporting ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                        <Download className="w-4 h-4" />
                    )}
                    Export PDF
                </button>
            </div>

            {/* Incident Summary row */}
            <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card p-5"
            >
                <div className="flex items-start justify-between gap-6">
                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                            <span className="w-1.5 h-3 rounded-full bg-indigo-500" />
                            <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">Incident Summary</span>
                        </div>
                        {report.root_cause ? (
                            <>
                                <p className="text-sm font-bold text-white">{report.root_cause.primary_trigger}</p>
                                <p className="text-xs text-slate-400 mt-1">{report.root_cause.direct_cause}</p>
                                <div className="mt-3 flex items-center gap-2">
                                    <span className={`badge-${report.root_cause.mitigation_urgency === 'HIGH' || report.root_cause.mitigation_urgency === 'IMMEDIATE'
                                        ? 'critical'
                                        : report.root_cause.mitigation_urgency === 'MEDIUM'
                                            ? 'warning'
                                            : 'info'
                                        }`}>
                                        {report.root_cause.mitigation_urgency} URGENCY
                                    </span>
                                    <span className="badge-success">{report.status}</span>
                                </div>
                            </>
                        ) : primaryHypothesis ? (
                            <>
                                <p className="text-sm font-bold text-white">{primaryHypothesis.probable_root_cause}</p>
                                <p className="text-xs text-slate-400 mt-1">{hypothesis.executive_summary}</p>
                                <div className="mt-3">
                                    <span className="badge-success">{report.status}</span>
                                </div>
                            </>
                        ) : (
                            <p className="text-sm text-slate-500">No root cause identified.</p>
                        )}
                    </div>
                    {primaryHypothesis && <ConfidenceRing score={primaryHypothesis.confidence_score} />}
                </div>
            </motion.div>

            {/* Hypothesis */}
            {hypothesis && (
                <Collapsible
                    title={
                        <span className="flex items-center gap-2">
                            <Lightbulb className="w-4 h-4 text-amber-400" />
                            Ranked SRE Hypotheses
                        </span>
                    }
                >
                    <div className="space-y-6">
                        <div className="p-4 bg-indigo-500/5 border border-indigo-500/10 rounded-lg">
                            <h4 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">Senior SRE Synthesis</h4>
                            <p className="text-sm text-slate-200 leading-relaxed font-sans">{hypothesis.executive_summary}</p>
                        </div>

                        <div className="space-y-4">
                            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Top Probable Root Causes</h4>

                            {/* Primary Hypothesis */}
                            {primaryHypothesis && (
                                <div className="border border-indigo-500/30 rounded-lg p-4 bg-slate-900/40 relative overflow-hidden">
                                    <div className="absolute top-0 right-0 w-24 h-24 translate-x-6 -translate-y-6 bg-indigo-500/5 rounded-full blur-xl pointer-events-none" />

                                    <div className="flex items-start gap-3 mb-3">
                                        <div className="shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 font-bold text-xs mt-0.5">
                                            #1
                                        </div>
                                        <div>
                                            <h5 className="text-sm font-bold text-white leading-snug">{primaryHypothesis.probable_root_cause}</h5>
                                            <p className="text-[10px] text-amber-400/90 font-semibold mt-1 font-mono uppercase tracking-wide">
                                                Confidence Factor: {primaryHypothesis.confidence_score}%
                                            </p>
                                        </div>
                                    </div>

                                    <p className="text-xs text-slate-350 bg-slate-950/20 p-2.5 rounded border border-slate-800/40 italic leading-relaxed mt-2 mb-3">
                                        <strong>Why This Is Likely:</strong> {primaryHypothesis.why_this_is_likely}
                                    </p>

                                    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-slate-800/60 pt-3">
                                        <div>
                                            <p className="text-[11px] font-semibold text-indigo-300 uppercase tracking-wider mb-2">Supporting Evidence</p>
                                            <ul className="space-y-1.5 font-sans">
                                                {(primaryHypothesis.supporting_evidence || []).map((ev: string, idx: number) => (
                                                    <li key={idx} className="flex gap-2 text-xs text-slate-300">
                                                        <span className="text-indigo-400 font-mono mt-0.5">•</span>
                                                        <span>{ev}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div className="bg-slate-950/45 p-3 rounded-lg border border-slate-800/40">
                                            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Alternative Rejection Logic</p>
                                            <ul className="space-y-1">
                                                {(primaryHypothesis.rejected_alternative_hypotheses || []).map((rej: string, idx: number) => (
                                                    <li key={idx} className="text-xs text-slate-400 italic flex gap-1.5 align-top">
                                                        <span className="text-slate-600 font-mono">•</span>
                                                        <span>{rej}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>

                                    {primaryHypothesis.recommended_actions && primaryHypothesis.recommended_actions.length > 0 && (
                                        <div className="mt-4 border-t border-slate-800/60 pt-3">
                                            <p className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider mb-2 font-mono">Recommended Remediation Checklist</p>
                                            <ul className="space-y-1.5">
                                                {primaryHypothesis.recommended_actions.map((act: string, idx: number) => (
                                                    <li key={idx} className="text-xs text-slate-300 flex items-start gap-2 bg-emerald-500/5 border border-emerald-500/10 p-2 rounded">
                                                        <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                                                        <span>{act}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Secondary Hypotheses */}
                            {secondaryHypotheses.map((h: any, i: number) => (
                                <div key={i} className="border border-slate-800/80 rounded-lg p-4 bg-slate-900/40 relative overflow-hidden">
                                    <div className="flex items-start gap-3 mb-3">
                                        <div className="shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-slate-400 font-bold text-xs mt-0.5">
                                            #{h.rank || i + 2}
                                        </div>
                                        <div>
                                            <h5 className="text-sm font-bold text-slate-200 leading-snug">{h.probable_root_cause}</h5>
                                            <p className="text-[10px] text-slate-400 font-semibold mt-1 font-mono uppercase tracking-wide">
                                                Confidence Factor: {h.confidence_score}%
                                            </p>
                                        </div>
                                    </div>

                                    <p className="text-xs text-slate-400 bg-slate-950/20 p-2.5 rounded border border-slate-800/50 italic leading-relaxed mt-2 mb-3">
                                        <strong>Why This Is Likely:</strong> {h.why_this_is_likely}
                                    </p>

                                    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-slate-800/60 pt-3">
                                        <div>
                                            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Supporting Evidence</p>
                                            <ul className="space-y-1.5 font-sans">
                                                {(h.supporting_evidence || []).map((ev: string, idx: number) => (
                                                    <li key={idx} className="flex gap-2 text-xs text-slate-400">
                                                        <span className="text-slate-500 font-mono mt-0.5">•</span>
                                                        <span>{ev}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div className="bg-slate-950/45 p-3 rounded-lg border border-slate-800/40">
                                            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Alternative Rejection Logic</p>
                                            <ul className="space-y-1">
                                                {(h.rejected_alternative_hypotheses || []).map((rej: string, idx: number) => (
                                                    <li key={idx} className="text-xs text-slate-450 italic flex gap-1.5 align-top">
                                                        <span className="text-slate-650">•</span>
                                                        <span>{rej}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {((hypothesis as any).key_assumptions || []).length > 0 && (
                            <div className="border-t border-slate-805 pt-4">
                                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Incident Key Assumptions</h4>
                                <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    {((hypothesis as any).key_assumptions || []).map((a: string, i: number) => (
                                        <li key={i} className="flex gap-2 text-xs text-slate-400">
                                            <span className="text-slate-600">—</span>
                                            <span>{a}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </Collapsible>
            )}

            {/* Supporting Evidence (Findings) */}
            {findings?.length > 0 && (
                <Collapsible
                    title={
                        <span className="flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 text-cyan-400" />
                            Supporting Evidence ({findings.length} findings)
                        </span>
                    }
                >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {findings.map((f, i) => (
                            <div key={i} className="border border-slate-800 rounded-lg p-3 bg-slate-900/40">
                                <div className="flex items-center justify-between mb-1.5">
                                    <span className="text-xs font-semibold text-white">{f.agent_name}</span>
                                    <SeverityBadge severity={f.severity} />
                                </div>
                                <p className="text-xs text-slate-300">{f.message}</p>
                                {f.evidence_snippet && (
                                    <pre className="mt-2 text-[10px] font-mono bg-black/40 border border-slate-800 rounded p-2 overflow-x-auto text-slate-400">
                                        {f.evidence_snippet}
                                    </pre>
                                )}
                            </div>
                        ))}
                    </div>
                </Collapsible>
            )}

            {/* Recommendations */}
            {recommendations?.length > 0 && (
                <Collapsible
                    title={
                        <span className="flex items-center gap-2">
                            <Shield className="w-4 h-4 text-emerald-400" />
                            Recommended Actions ({recommendations.length})
                        </span>
                    }
                >
                    <div className="space-y-3">
                        {recommendations.map((rec, i) => (
                            <div key={i} className="border border-slate-800 rounded-lg p-4 bg-slate-900/30">
                                <div className="flex items-center justify-between mb-2">
                                    <ActionTypeChip type={rec.action_type} />
                                    <span className="text-[10px] text-slate-500">
                                        Risk: <span className={rec.risk_level === 'HIGH' ? 'text-red-400' : rec.risk_level === 'MEDIUM' ? 'text-amber-400' : 'text-emerald-400'}>{rec.risk_level}</span>
                                    </span>
                                </div>
                                <p className="text-xs text-slate-200">{rec.description}</p>
                                {rec.command_or_code && (
                                    <pre className="mt-2 text-[10px] font-mono bg-black/50 border border-slate-800 rounded-lg p-3 overflow-x-auto text-cyan-300">
                                        {rec.command_or_code}
                                    </pre>
                                )}
                            </div>
                        ))}
                    </div>
                </Collapsible>
            )}

            {/* Timeline */}
            {timeline?.length > 0 && (
                <Collapsible
                    title={
                        <span className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-indigo-400" />
                            Investigation Timeline ({timeline.length} events)
                        </span>
                    }
                    defaultOpen={false}
                >
                    <div className="relative border-l border-slate-800 ml-3 space-y-4 pl-6">
                        {timeline.map((item, i) => {
                            const lvl = item.impact_level;
                            const dotColor =
                                lvl === 'CRITICAL' ? 'bg-red-500' : lvl === 'WARNING' ? 'bg-amber-500' : 'bg-slate-600';
                            return (
                                <div key={i} className="relative">
                                    <div className={`absolute -left-[27px] top-1 w-2.5 h-2.5 rounded-full border-2 border-[#080b12] ${dotColor}`} />
                                    <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
                                        {new Date(item.timestamp).toLocaleTimeString()}
                                        <span className="text-slate-700">·</span>
                                        <span className="text-cyan-500">{item.sources.join(', ')}</span>
                                    </div>
                                    <p className="text-xs text-slate-300 mt-0.5">{item.description}</p>
                                </div>
                            );
                        })}
                    </div>
                </Collapsible>
            )}

            {/* Raw markdown report */}
            {report.markdown_report && (
                <Collapsible
                    title={
                        <span className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-slate-400" />
                            Raw Markdown Report
                        </span>
                    }
                    defaultOpen={false}
                >
                    <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap overflow-x-auto leading-relaxed">
                        {report.markdown_report}
                    </pre>
                </Collapsible>
            )}
        </div>
    );
}
