import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { NavLink, Link } from 'react-router-dom';
import {
    LayoutDashboard,
    Upload,
    Activity,
    FileText,
    AlertTriangle,
    Zap,
} from 'lucide-react';

const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/upload', icon: Upload, label: 'Upload Incident' },
];

interface LayoutProps {
    children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
    return (
        <div className="flex min-h-screen bg-[#080b12] text-slate-300">
            {/* Sidebar */}
            <aside className="w-60 shrink-0 flex flex-col border-r border-slate-800 bg-[#0c1220]">
                {/* Logo */}
                <Link to="/" className="flex items-center gap-3 px-5 py-5 border-b border-slate-800 group">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/30 group-hover:shadow-indigo-500/50 transition-shadow">
                        <AlertTriangle className="w-4 h-4 text-white" />
                    </div>
                    <div>
                        <div className="text-sm font-bold text-white tracking-tight">RootSight</div>
                        <div className="text-[10px] text-slate-500 font-mono">Agentic AI</div>
                    </div>
                </Link>

                {/* Navigation */}
                <nav className="flex-1 px-3 py-4 space-y-1">
                    <div className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest px-2 mb-3">Workspace</div>
                    {navItems.map(({ path, icon: Icon, label }) => (
                        <NavLink
                            key={path}
                            to={path}
                            end={path === '/'}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all ${isActive
                                    ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                                }`
                            }
                        >
                            {({ isActive }) => (
                                <>
                                    <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : ''}`} />
                                    {label}
                                </>
                            )}
                        </NavLink>
                    ))}
                </nav>

                {/* Footer status */}
                <div className="px-4 py-4 border-t border-slate-800">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                        <Zap className="w-3.5 h-3.5 text-emerald-400" />
                        <span>LangGraph Ready</span>
                        <div className="ml-auto w-2 h-2 rounded-full bg-emerald-500 animate-pulse-slow" />
                    </div>
                </div>
            </aside>

            {/* Main content */}
            <main className="flex-1 flex flex-col min-w-0">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={window.location.pathname}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="flex-1 p-6 overflow-auto"
                    >
                        {children}
                    </motion.div>
                </AnimatePresence>
            </main>
        </div>
    );
}
