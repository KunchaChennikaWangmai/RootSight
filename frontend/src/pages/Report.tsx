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
    const pct = Math.round(score * 100);
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
        addTitle('Root Cause Hypothesis', 13);
        addText(report.hypothesis.probable_root_cause);
        addText(`Confidence Score: ${Math.round(report.hypothesis.confidence_score * 100)}%`);
        addGap();
        addTitle('Reasoning', 11);
        report.hypothesis.reasoning.forEach((r) => addText(`• ${r}`, 9, 8));
        addGap();
        addTitle('Assumptions', 11);
        report.hypothesis.assumptions.forEach((a) => addText(`• ${a}`, 9, 8));
        addGap();
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
                        ) : hypothesis ? (
                            <>
                                <p className="text-sm font-bold text-white">{hypothesis.probable_root_cause}</p>
                                <div className="mt-2">
                                    <span className="badge-success">{report.status}</span>
                                </div>
                            </>
                        ) : (
                            <p className="text-sm text-slate-500">No root cause identified.</p>
                        )}
                    </div>
                    {hypothesis && <ConfidenceRing score={hypothesis.confidence_score} />}
                </div>
            </motion.div>

            {/* Hypothesis */}
            {hypothesis && (
                <Collapsible
                    title={
                        <span className="flex items-center gap-2">
                            <Lightbulb className="w-4 h-4 text-amber-400" />
                            Root Cause Hypothesis
                        </span>
                    }
                >
                    <div className="space-y-4">
                        <div className="p-4 bg-amber-500/5 border border-amber-500/15 rounded-lg">
                            <p className="text-sm font-semibold text-white">{hypothesis.probable_root_cause}</p>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Reasoning Chain</h4>
                                <ol className="space-y-1.5">
                                    {hypothesis.reasoning.map((r, i) => (
                                        <li key={i} className="flex gap-2 text-xs text-slate-300">
                                            <span className="shrink-0 text-indigo-400 font-mono">{i + 1}.</span>
                                            {r}
                                        </li>
                                    ))}
                                </ol>
                            </div>
                            <div>
                                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Assumptions</h4>
                                <ul className="space-y-1.5">
                                    {hypothesis.assumptions.map((a, i) => (
                                        <li key={i} className="flex gap-2 text-xs text-slate-400">
                                            <span className="shrink-0 text-slate-600">—</span> {a}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
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
