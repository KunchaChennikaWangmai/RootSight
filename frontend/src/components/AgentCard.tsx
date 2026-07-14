import { motion } from 'framer-motion';
import { CheckCircle2, Loader2, Clock, XCircle, MinusCircle } from 'lucide-react';
import type { AgentProgressItem } from '../types';

interface AgentCardProps {
    agent: AgentProgressItem;
    index: number;
}

const statusConfig = {
    waiting: {
        icon: Clock,
        color: 'text-slate-500',
        bg: 'bg-slate-800 border-slate-700',
        label: 'Waiting',
        dot: 'bg-slate-600',
    },
    running: {
        icon: Loader2,
        color: 'text-indigo-400',
        bg: 'bg-indigo-500/10 border-indigo-500/30',
        label: 'Running…',
        dot: 'bg-indigo-500 animate-pulse',
    },
    completed: {
        icon: CheckCircle2,
        color: 'text-emerald-400',
        bg: 'bg-emerald-500/10 border-emerald-500/20',
        label: 'Completed',
        dot: 'bg-emerald-500',
    },
    error: {
        icon: XCircle,
        color: 'text-red-400',
        bg: 'bg-red-500/10 border-red-500/20',
        label: 'Error',
        dot: 'bg-red-500',
    },
    skipped: {
        icon: MinusCircle,
        color: 'text-slate-600',
        bg: 'bg-slate-900 border-slate-800',
        label: 'Skipped',
        dot: 'bg-slate-700',
    },
};

export default function AgentCard({ agent, index }: AgentCardProps) {
    const cfg = statusConfig[agent.status];
    const Icon = cfg.icon;

    return (
        <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.25, delay: index * 0.06 }}
            className={`relative border rounded-xl p-4 transition-all ${cfg.bg}`}
        >
            <div className="flex items-start gap-3">
                <div className={`mt-0.5 ${cfg.color}`}>
                    <Icon
                        className={`w-5 h-5 ${agent.status === 'running' ? 'animate-spin' : ''}`}
                    />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-white">{agent.name}</p>
                        <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">{agent.description}</p>
                    {(agent.startedAt || agent.completedAt) && (
                        <div className="mt-2 flex gap-3 text-[10px] font-mono text-slate-600">
                            {agent.startedAt && <span>Start: {agent.startedAt}</span>}
                            {agent.completedAt && <span>Done: {agent.completedAt}</span>}
                        </div>
                    )}
                </div>
                <div className={`text-xs font-semibold px-2 py-0.5 rounded ${cfg.color} ${cfg.bg}`}>
                    {cfg.label}
                </div>
            </div>

            {/* connector line below (not for last item) */}
            <div className="absolute left-[27px] -bottom-4 w-0.5 h-4 bg-slate-800" />
        </motion.div>
    );
}
