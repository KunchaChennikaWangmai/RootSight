import React, { useState } from "react";

// Mock types matching the FastAPI schemas
interface Finding {
    agent_name: str;
    severity: "INFO" | "WARNING" | "CRITICAL";
    timestamp?: string;
    message: string;
    evidence_snippet?: string;
}

interface TimelineItem {
    timestamp: string;
    sources: string[];
    description: string;
    impact_level: "INFO" | "WARNING" | "CRITICAL";
}

interface RootCause {
    primary_trigger: string;
    direct_cause: string;
    mitigation_urgency: "LOW" | "MEDIUM" | "HIGH" | "IMMEDIATE";
    explanation: string;
}

interface Recommendation {
    action_type: "HOTFIX" | "REFACTOR" | "CONFIG" | "RUNBOOK";
    description: string;
    command_or_code?: string;
    risk_level: "LOW" | "MEDIUM" | "HIGH";
}

interface InvestigationResult {
    incident_id: string;
    status: string;
    findings: Finding[];
    timeline: TimelineItem[];
    root_cause?: RootCause;
    recommendations: Recommendation[];
    markdown_report: string;
}

export default function RootSightApp() {
    const [title, setTitle] = useState("Database Host Connection Pool Starvation");
    const [description, setDescription] = useState("API endpoints reporting slow connections followed by gateway timeouts.");
    const [logs, setLogs] = useState("");
    const [stackTrace, setStackTrace] = useState("");
    const [metrics, setMetrics] = useState("");
    const [deploy, setDeploy] = useState("");

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<InvestigationResult | null>(null);
    const [activeTab, setActiveTab] = useState<"summary" | "timeline" | "findings" | "report">("summary");

    // Load sample data trigger
    const handleLoadSample = () => {
        setLogs(`2026-07-14T19:04:45 [INFO] Worker thread pools spawned.
2026-07-14T19:04:50 [WARN] Connection acquisition time at 654ms (exceeds threshold 500ms).
2026-07-14T19:04:55 [ERROR] Failed to obtain database connection from DataSource.
2026-07-14T19:05:00 [CRITICAL] Connection pool exceeded capacity. Wait queue length is 150.`);

        setStackTrace(`Exception in thread "main" java.sql.SQLTransientConnectionException: Connection is not available, request timed out after 30000ms.
\tat com.zaxxer.hikari.pool.HikariPool.createTimeoutException(HikariPool.java:696)
\tat com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:197)
\tat com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:162)
\tat org.hibernate.engine.jdbc.connections.internal.DatasourceConnectionProviderImpl.getConnection(DatasourceConnectionProviderImpl.java:122)`);

        setMetrics(JSON.stringify([
            { timestamp: "2026-07-14T19:00:00", cpu_percent: 15, memory_percent: 45, latency_ms: 120, error_rate: 0 },
            { timestamp: "2026-07-14T19:02:00", cpu_percent: 20, memory_percent: 48, latency_ms: 150, error_rate: 0 },
            { timestamp: "2026-07-14T19:04:00", cpu_percent: 85, memory_percent: 92, latency_ms: 850, error_rate: 12 },
            { timestamp: "2026-07-14T19:05:00", cpu_percent: 98, memory_percent: 95, latency_ms: 5000, error_rate: 64 },
        ], null, 2));

        setDeploy(JSON.stringify({
            filename: "deployment_prod.json",
            environment: "production",
            version: "v2.14.0-release",
            deployed_at: "2026-07-14T19:00:00",
            config_vars: {
                DB_MAX_POOL_SIZE: "5", // DRAMATICALLY LOWERED FROM 50
                TIMEOUT_MS: "30000"
            },
            previous_config_vars: {
                DB_MAX_POOL_SIZE: "50",
                TIMEOUT_MS: "30000"
            }
        }, null, 2));
    };

    const handleRunInvestigation = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        // Prepare payoad structures
        const payload = {
            title,
            description,
            logs: logs ? { filename: "server.log", content: logs } : undefined,
            stack_trace: stackTrace ? { filename: "stacktrace.txt", content: stackTrace } : undefined,
            metrics: metrics ? { filename: "metrics.json", data: JSON.parse(metrics) } : undefined,
            deployment: deploy ? JSON.parse(deploy) : undefined,
        };

        try {
            const response = await fetch("http://localhost:8000/api/v1/investigations/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.statusText}`);
            }

            const data = await response.json();
            setResult(data);
        } catch (err: any) {
            setError(err.message || "Failed to execute investigation workflow.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#070b13] text-slate-100 font-sans antialiased">
            {/* Top Navigation Frame */}
            <header className="border-b border-slate-800 bg-[#0c1221] px-6 py-4 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center font-bold text-white shadow-md shadow-cyan-500/20">
                        R
                    </div>
                    <div>
                        <h1 className="text-xl font-bold tracking-tight text-white flex items-center">
                            RootSight
                            <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-cyan-400 border border-indigo-500/30">
                                Agentic AI
                            </span>
                        </h1>
                        <p className="text-[10px] text-slate-400">Enterprise Incident Investigation Cockpit</p>
                    </div>
                </div>
                <div className="flex items-center space-x-4">
                    <button
                        onClick={handleLoadSample}
                        className="px-3 py-1.5 rounded text-xs font-medium border border-teal-500/30 hover:border-teal-500 bg-teal-500/10 text-teal-400 transition"
                    >
                        Load Sample Outage
                    </button>
                    <span className="w-3.5 h-3.5 rounded-full bg-emerald-500 animate-pulse block"></span>
                </div>
            </header>

            {/* Main Grid View */}
            <main className="max-w-[1600px] mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left Column: Upload Panels */}
                <section className="lg:col-span-4 space-y-6">
                    <div className="bg-[#0c1221] border border-slate-800 rounded-lg p-5 shadow-xl">
                        <h2 className="text-sm font-semibold tracking-wide uppercase text-slate-400 mb-4 flex items-center">
                            <span className="w-1.5 h-3 rounded-full bg-indigo-500 mr-2"></span>
                            Incident Inputs
                        </h2>
                        <form onSubmit={handleRunInvestigation} className="space-y-4">
                            <div>
                                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Incident Title</label>
                                <input
                                    type="text"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    className="w-full bg-[#11192e] border border-slate-700/60 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 transition"
                                    placeholder="Describe incident, eg: DB connection timeouts"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Symptoms / Context</label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    className="w-full bg-[#11192e] border border-slate-700/60 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 h-16 transition"
                                    placeholder="User reports, alert notifications, severity info..."
                                />
                            </div>

                            {/* Logs */}
                            <div>
                                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Application Logs (.log)</label>
                                <textarea
                                    value={logs}
                                    onChange={(e) => setLogs(e.target.value)}
                                    className="w-full bg-[#11192e] border border-slate-700/60 rounded px-3 py-2 text-xs font-mono text-cyan-300 focus:outline-none focus:border-indigo-500 h-24 transition"
                                    placeholder="Paste raw application log lines here"
                                />
                            </div>

                            {/* Stack Traces */}
                            <div>
                                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Stack Trace (.txt)</label>
                                <textarea
                                    value={stackTrace}
                                    onChange={(e) => setStackTrace(e.target.value)}
                                    className="w-full bg-[#11192e] border border-slate-700/60 rounded px-3 py-2 text-xs font-mono text-purple-300 focus:outline-none focus:border-indigo-500 h-24 transition"
                                    placeholder="Paste system dump / stack trace files"
                                />
                            </div>

                            {/* System Metrics */}
                            <div>
                                <label className="block text-xs font-semibold text-slate-400 mb-1.5">System Metrics (.json)</label>
                                <textarea
                                    value={metrics}
                                    onChange={(e) => setMetrics(e.target.value)}
                                    className="w-full bg-[#11192e] border border-slate-700/60 rounded px-3 py-2 text-xs font-mono text-orange-300 focus:outline-none focus:border-indigo-500 h-24 transition"
                                    placeholder="[{ 'timestamp': '...', 'cpu_percent': 70 }]"
                                />
                            </div>

                            {/* Deployment Meta */}
                            <div>
                                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Deployment Data (.json)</label>
                                <textarea
                                    value={deploy}
                                    onChange={(e) => setDeploy(e.target.value)}
                                    className="w-full bg-[#11192e] border border-slate-700/60 rounded px-3 py-2 text-xs font-mono text-teal-300 focus:outline-none focus:border-indigo-500 h-24 transition"
                                    placeholder="{ 'version': 'v1.0.0', 'config_vars': {...} }"
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-2.5 rounded bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-semibold text-sm shadow-lg shadow-indigo-600/20 active:translate-y-0.5 hover:shadow-indigo-500/40 disabled:opacity-50 transition"
                            >
                                {loading ? "Running Multi-Agent Workflow..." : "Orchestrate Investigation"}
                            </button>
                        </form>
                    </div>
                </section>

                {/* Right Column: Visualization & Reports tab */}
                <section className="lg:col-span-8 space-y-6">
                    {error && (
                        <div className="bg-red-500/10 border border-red-500/30 text-red-200 p-4 rounded-lg text-sm">
                            <strong>Workflow Exception:</strong> {error}
                        </div>
                    )}

                    {!result && !loading && (
                        <div className="border border-dashed border-slate-800 rounded-lg p-16 text-center bg-[#0c1221]/30">
                            <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4">
                                🔍
                            </div>
                            <h3 className="text-base font-semibold text-white">No active investigation loaded</h3>
                            <p className="text-xs text-slate-400 max-w-sm mx-auto mt-2">
                                Click "Load Sample Outage" and press "Orchestrate Investigation" to invoke the multi-agent LangGraph workflow.
                            </p>
                        </div>
                    )}

                    {loading && (
                        <div className="border border-slate-800 rounded-lg p-16 text-center bg-[#0c1221]">
                            <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin mx-auto mb-4"></div>
                            <h3 className="text-base font-semibold text-white">LangGraph Execution In Progress</h3>
                            <p className="text-xs text-slate-400 max-w-sm mx-auto mt-2">
                                Planner Agent coordinating Log, Stack Trace, Metrics, and Deployment modules...
                            </p>
                        </div>
                    )}

                    {result && (
                        <div className="bg-[#0c1221] border border-slate-800 rounded-lg shadow-xl overflow-hidden">
                            {/* Header result stats */}
                            <div className="bg-slate-900/60 border-b border-slate-800 p-5 flex flex-wrap items-center justify-between gap-4">
                                <div>
                                    <span className="text-[10px] tracking-wider font-bold text-indigo-400 uppercase">Analysis Complete</span>
                                    <h3 className="text-base font-semibold text-white mt-1">Incident Report: {title}</h3>
                                </div>
                                <div className="flex space-x-3 text-xs bg-slate-900 border border-slate-800 p-1.5 rounded">
                                    <span className="px-2 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded font-semibold">
                                        RCA: {result.root_cause?.mitigation_urgency || "MEDIUM"}
                                    </span>
                                    <span className="px-2 py-1 bg-slate-800 text-slate-400 rounded">
                                        Findings: {result.findings.length}
                                    </span>
                                </div>
                            </div>

                            {/* Tabs nav */}
                            <div className="flex border-b border-slate-800 px-4 bg-slate-900/30">
                                {(["summary", "timeline", "findings", "report"] as const).map((tab) => (
                                    <button
                                        key={tab}
                                        onClick={() => setActiveTab(tab)}
                                        className={`px-4 py-3 text-xs font-semibold uppercase tracking-wider border-b-2 transition ${activeTab === tab
                                                ? "border-cyan-400 text-cyan-400"
                                                : "border-transparent text-slate-400 hover:text-slate-200"
                                            }`}
                                    >
                                        {tab}
                                    </button>
                                ))}
                            </div>

                            {/* Tab Content Panels */}
                            <div className="p-6">
                                {/* 1. Summary Dashboard Tab */}
                                {activeTab === "summary" && (
                                    <div className="space-y-6">
                                        {result.root_cause && (
                                            <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-lg p-5">
                                                <span className="text-[10px] font-bold text-indigo-400 tracking-wider uppercase">Synthesized Root Cause</span>
                                                <h4 className="text-base font-bold text-white mt-1">{result.root_cause.primary_trigger}</h4>
                                                <p className="text-xs text-slate-300 mt-2">{result.root_cause.direct_cause}</p>

                                                <div className="mt-4 pt-4 border-t border-indigo-500/10">
                                                    <label className="text-[10px] font-bold text-indigo-400 tracking-wider uppercase block">5-Whys Diagnostic Chain</label>
                                                    <pre className="mt-1 text-xs text-indigo-200 overflow-x-auto whitespace-pre-wrap font-sans">
                                                        {result.root_cause.explanation}
                                                    </pre>
                                                </div>
                                            </div>
                                        )}

                                        {/* Recommendations action timeline */}
                                        <div>
                                            <h4 className="text-xs font-bold text-slate-400 tracking-wider uppercase mb-3">Remediation Action Plan</h4>
                                            <div className="space-y-4">
                                                {result.recommendations.map((rec, idx) => (
                                                    <div key={idx} className="border border-slate-800 bg-[#11192e] rounded p-4">
                                                        <div className="flex items-center justify-between">
                                                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-500/10 text-teal-400 border border-teal-500/20 uppercase">
                                                                {rec.action_type}
                                                            </span>
                                                            <span className="text-[10px] text-slate-400">Risk: <b className="text-orange-400">{rec.risk_level}</b></span>
                                                        </div>
                                                        <p className="text-xs text-slate-200 mt-2 font-medium">{rec.description}</p>
                                                        {rec.command_or_code && (
                                                            <pre className="mt-2 text-xs bg-black/40 border border-slate-900 rounded p-2.5 font-mono text-cyan-300 overflow-x-auto">
                                                                {rec.command_or_code}
                                                            </pre>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* 2. Timeline Tab */}
                                {activeTab === "timeline" && (
                                    <div className="space-y-6">
                                        <div className="relative border-l border-slate-800 pl-6 ml-4 space-y-6">
                                            {result.timeline.map((item, idx) => (
                                                <div key={idx} className="relative">
                                                    {/* Chronological dot */}
                                                    <div className={`absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full border-2 bg-[#0c1221] ${item.impact_level === "CRITICAL" ? "border-red-500" : item.impact_level === "WARNING" ? "border-warning-color border-orange-400" : "border-indigo-400"
                                                        }`} />

                                                    <div className="flex items-center space-x-2 text-[10px] text-slate-400">
                                                        <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                                                        <span>•</span>
                                                        <span className="uppercase text-cyan-400">{item.sources.join(", ")}</span>
                                                    </div>
                                                    <p className="text-xs font-semibold text-white mt-1">{item.description}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* 3. Agent Findings Tab */}
                                {activeTab === "findings" && (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {result.findings.map((f, idx) => (
                                            <div key={idx} className="border border-slate-800 bg-[#11192e]/40 rounded-lg p-4 flex flex-col justify-between">
                                                <div>
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-xs font-bold text-white">{f.agent_name}</span>
                                                        <span className={`text-[10px] px-2 py-0.5 rounded font-semibold ${f.severity === "CRITICAL" ? "bg-red-500/10 text-red-400 border border-red-500/20" : f.severity === "WARNING" ? "bg-orange-500/10 text-orange-400 border border-orange-500/20" : "bg-slate-800 text-slate-400"
                                                            }`}>
                                                            {f.severity}
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-slate-300 mt-2">{f.message}</p>
                                                </div>
                                                {f.evidence_snippet && (
                                                    <pre className="mt-3 text-[10px] bg-black/40 border border-slate-800/80 rounded p-2 overflow-x-auto text-slate-400 font-mono">
                                                        {f.evidence_snippet}
                                                    </pre>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* 4. Markdown Report Tab */}
                                {activeTab === "report" && (
                                    <div className="prose prose-invert max-w-none text-xs">
                                        <pre className="bg-[#11192e]/20 border border-slate-800 rounded-lg p-5 whitespace-pre-wrap font-mono text-cyan-200 overflow-x-auto">
                                            {result.markdown_report}
                                        </pre>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </section>
            </main>
        </div>
    );
}
