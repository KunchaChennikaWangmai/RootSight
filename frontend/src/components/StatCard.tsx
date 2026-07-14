import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { motion } from 'framer-motion';

interface StatCardProps {
    label: string;
    value: string | number;
    icon: LucideIcon;
    trend?: string;
    color?: 'indigo' | 'emerald' | 'amber' | 'red';
}

const colors = {
    indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
};

export default function StatCard({ label, value, icon: Icon, trend, color = 'indigo' }: StatCardProps) {
    return (
        <motion.div
            whileHover={{ scale: 1.02 }}
            className="glass-card p-5 flex items-start justify-between"
        >
            <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</p>
                <p className="text-3xl font-bold text-white mt-1 tracking-tight">{value}</p>
                {trend && <p className="text-xs text-slate-500 mt-1">{trend}</p>}
            </div>
            <div className={`p-2.5 rounded-lg border ${colors[color]}`}>
                <Icon className="w-5 h-5" />
            </div>
        </motion.div>
    );
}
