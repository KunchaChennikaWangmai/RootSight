import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import AgentCard from '../components/AgentCard';
import { investigationsApi } from '../services/api';
import type { AgentProgressItem } from '../types';

// Agent manifest — ordered pipeline (matches orchestrator graph)
const AGENT_MANIFEST: Omit<AgentProgressItem, 'status'>[] = [
    { id: 'planner', name: 'Planner Agent', description: 'Assess inputs and schedule analysis modules' },
    { id: 'log_analysis', name: 'Log Analysis Agent', description: 'Parse logs with deterministic regex tools' },
    { id: 'stack_analysis', name: 'Stack Trace Agent', description: 'Identify crash frames (placeholder)' },
    { id: 'metrics_analysis', name: 'Metrics Agent', description: 'Detect Z-score anomalies (placeholder)' },
    { id: 'deployment_analysis', name: 'Deployment Agent', description: 'Diff config variables (placeholder)' },
    { id: 'correlation', name: 'Evidence Correlation', description: 'Build chronological evidence map' },
    { id: 'hypothesis', name: 'Hypothesis Agent', description: 'LLM root cause analysis with confidence score' },
    { id: 'report_generation', name: 'Report Agent', description: 'Compile structured JSON investigation report' },
];

const now = () => new Date().toLocaleTimeString();

function simulateProgress(
    items: AgentProgressItem[],
    setItems: React.Dispatch<React.SetStateAction<AgentProgressItem[]>>,
    onDone?: () => void
) {
    let idx = 0;
    // Planner + Log are active; stack/metrics/deploy are skipped
    const ACTIVE = new Set(['planner', 'log_analysis', 'correlation', 'hypothesis', 'report_generation']);

    const tick = () => {
        if (idx >= items.length) {
            onDone?.();
            return;
        }

        const current = items[idx];
        if (!ACTIVE.has(current.id)) {
            // Mark non-active agents as skipped immediately
            setItems((prev) =>
                prev.map((a) => (a.id === current.id ? { ...a, status: 'skipped' } : a))
            );
            idx++;
            setTimeout(tick, 50);
            return;
        }

        // Mark running
        const startTime = now();
        setItems((prev) =>
            prev.map((a) => (a.id === current.id ? { ...a, status: 'running', startedAt: startTime } : a))
        );

        // Simulate agent duration
        const delay = current.id === 'hypothesis' ? 2500 : 900;
        setTimeout(() => {
            const endTime = now();
            setItems((prev) =>
                prev.map((a) =>
                    a.id === current.id ? { ...a, status: 'completed', completedAt: endTime } : a
                )
            );
            idx++;
            setTimeout(tick, 300);
        }, delay);
    };

    setTimeout(tick, 400);
}

export default function ProgressPage() {
    const { id } = useParams<{ id: string }>();
    const [agents, setAgents] = useState<AgentProgressItem[]>(
        AGENT_MANIFEST.map((a) => ({ ...a, status: 'waiting' }))
    );
    const [done, setDone] = useState(false);

    useEffect(() => {
        simulateProgress(agents, setAgents, () => setDone(true));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const completedCount = agents.filter((a) => a.status === 'completed').length;
    const totalActive = agents.filter((a) => a.status !== 'skipped').length;

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3">
                <Link to="/" className="btn-ghost text-slate-500">
                    <ArrowLeft className="w-4 h-4" />
                </Link>
                <div>
                    <h1 className="text-2xl font-bold text-white">Investigation Progress</h1>
                    <p className="text-xs text-slate-500 font-mono mt-0.5 break-all">{id}</p>
                </div>
            </div>

            {/* Overall progress bar */}
            <div className="glass-card p-5 space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>LangGraph Execution Pipeline</span>
                    <span>{completedCount}/{totalActive} agents completed</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <motion.div
                        className="h-full bg-gradient-to-r from-indigo-500 to-cyan-400 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: totalActive > 0 ? `${(completedCount / totalActive) * 100}%` : '0%' }}
                        transition={{ duration: 0.5 }}
                    />
                </div>
            </div>

            {/* Agent cards */}
            <div className="space-y-3">
                {agents.map((agent, idx) => (
                    <AgentCard key={agent.id} agent={agent} index={idx} />
                ))}
            </div>

            {/* Done CTA */}
            {done && id && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-card p-5 flex items-center justify-between"
                >
                    <div>
                        <p className="text-sm font-semibold text-emerald-400">Investigation Complete</p>
                        <p className="text-xs text-slate-500">All agents finished. View the full report below.</p>
                    </div>
                    <Link to={`/report/${id}`} className="btn-primary">
                        View Report
                        <ExternalLink className="w-4 h-4" />
                    </Link>
                </motion.div>
            )}
        </div>
    );
}
