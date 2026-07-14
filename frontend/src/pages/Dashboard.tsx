import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    Activity,
    Upload,
    Search,
    Plus,
    CheckCircle2,
    Clock,
    AlertTriangle,
    TrendingUp,
    ChevronRight,
} from 'lucide-react';
import StatCard from '../components/StatCard';
import { investigationsApi } from '../services/api';
import type { InvestigationListItem } from '../types';

const statusBadge = (status: string) => {
    if (status === 'COMPLETED') return <span className="badge-success">{status}</span>;
    if (status === 'IN_PROGRESS') return <span className="badge-info">IN PROGRESS</span>;
    return <span className="badge-warning">{status}</span>;
};

export default function DashboardPage() {
    const [investigations, setInvestigations] = useState<InvestigationListItem[]>([]);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        investigationsApi
            .list()
            .then(setInvestigations)
            .catch(() => setInvestigations([]))
            .finally(() => setLoading(false));
    }, []);

    const filtered = investigations.filter((inv) =>
        inv.title?.toLowerCase().includes(search.toLowerCase()) ||
        inv.incident_id.includes(search)
    );

    return (
        <div className="space-y-6 max-w-screen-xl">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white tracking-tight">Investigation Dashboard</h1>
                    <p className="text-sm text-slate-500 mt-0.5">Agentic AI-powered incident root cause analysis</p>
                </div>
                <Link to="/upload" className="btn-primary">
                    <Plus className="w-4 h-4" />
                    New Investigation
                </Link>
            </div>

            {/* Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    label="Total Investigations"
                    value={investigations.length}
                    icon={Activity}
                    trend="All time"
                    color="indigo"
                />
                <StatCard
                    label="Completed"
                    value={investigations.filter((i) => i.status === 'COMPLETED').length}
                    icon={CheckCircle2}
                    color="emerald"
                />
                <StatCard
                    label="In Progress"
                    value={investigations.filter((i) => i.status === 'IN_PROGRESS').length}
                    icon={Clock}
                    color="amber"
                />
                <StatCard
                    label="Avg. Findings"
                    value={
                        investigations.length > 0
                            ? Math.round(
                                investigations.reduce((s, i) => s + i.findings_count, 0) /
                                investigations.length
                            )
                            : 0
                    }
                    icon={TrendingUp}
                    color="red"
                />
            </div>

            {/* Investigations table */}
            <div className="glass-card overflow-hidden">
                <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-800">
                    <h2 className="text-sm font-semibold text-white flex-1">Recent Investigations</h2>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                        <input
                            type="text"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder="Search investigations…"
                            className="input-base pl-8 h-8 w-56 text-xs"
                        />
                    </div>
                </div>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-3">
                        <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
                        <p className="text-sm text-slate-500">Loading investigations…</p>
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-3">
                        <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center">
                            <AlertTriangle className="w-6 h-6 text-slate-600" />
                        </div>
                        <p className="text-sm font-semibold text-slate-400">No investigations yet</p>
                        <p className="text-xs text-slate-600">Upload incident artifacts to start an investigation.</p>
                        <Link to="/upload" className="btn-primary mt-2">
                            <Upload className="w-4 h-4" /> Upload Incident
                        </Link>
                    </div>
                ) : (
                    <div className="divide-y divide-slate-800/80">
                        {filtered.map((inv, i) => (
                            <motion.div
                                key={inv.incident_id}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: i * 0.04 }}
                                className="flex items-center gap-4 px-5 py-4 hover:bg-slate-800/30 transition-colors group"
                            >
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-semibold text-white truncate">
                                        {inv.title || 'Untitled Incident'}
                                    </p>
                                    <p className="text-xs text-slate-600 font-mono mt-0.5">{inv.incident_id}</p>
                                </div>
                                <div className="flex items-center gap-4 text-xs text-slate-500">
                                    <span>{inv.findings_count} findings</span>
                                    <span>{inv.recommendations_count} actions</span>
                                    {statusBadge(inv.status)}
                                </div>
                                <Link
                                    to={`/report/${inv.incident_id}`}
                                    className="p-1.5 rounded text-slate-600 hover:text-white hover:bg-slate-700 opacity-0 group-hover:opacity-100 transition-all"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </Link>
                            </motion.div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
