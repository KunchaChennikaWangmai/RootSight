import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Upload as UploadIcon,
    File,
    X,
    CheckCircle2,
    AlertCircle,
    ChevronRight,
} from 'lucide-react';
import { investigationsApi } from '../services/api';
import type { IncidentPayload } from '../types';

type FileSlot = 'logs' | 'stack_trace' | 'metrics' | 'deployment';

interface SlotConfig {
    id: FileSlot;
    label: string;
    hint: string;
    accept: string;
    color: string;
    required?: boolean;
}

const FILE_SLOTS: SlotConfig[] = [
    {
        id: 'logs',
        label: 'Application Logs',
        hint: '.log — Server, application, or system logs',
        accept: '.log,.txt,text/plain',
        color: 'cyan',
        required: true,
    },
    {
        id: 'stack_trace',
        label: 'Stack Trace',
        hint: '.txt — Thread dump, crash traceback',
        accept: '.txt,text/plain',
        color: 'purple',
        required: true,
    },
    {
        id: 'metrics',
        label: 'System Metrics',
        hint: '.json — CPU, memory, latency time-series',
        accept: '.json,application/json',
        color: 'amber',
        required: true,
    },
    {
        id: 'deployment',
        label: 'Deployment Metadata',
        hint: '.json — Environment config, release version',
        accept: '.json,application/json',
        color: 'teal',
        required: true,
    },
];

const colorMap: Record<string, string> = {
    cyan: 'border-cyan-500/30 bg-cyan-500/5 hover:border-cyan-500/60',
    purple: 'border-purple-500/30 bg-purple-500/5 hover:border-purple-500/60',
    amber: 'border-amber-500/30 bg-amber-500/5 hover:border-amber-500/60',
    teal: 'border-teal-500/30 bg-teal-500/5 hover:border-teal-500/60',
};

const iconColorMap: Record<string, string> = {
    cyan: 'text-cyan-400',
    purple: 'text-purple-400',
    amber: 'text-amber-400',
    teal: 'text-teal-400',
};

export default function UploadPage() {
    const navigate = useNavigate();
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [files, setFiles] = useState<Partial<Record<FileSlot, File>>>({});
    const [dragOver, setDragOver] = useState<FileSlot | null>(null);
    const [progress, setProgress] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleFileDrop = useCallback((slot: FileSlot, file: File) => {
        setFiles((prev) => ({ ...prev, [slot]: file }));
    }, []);

    const onDrop = useCallback(
        (slot: FileSlot) => (e: React.DragEvent) => {
            e.preventDefault();
            setDragOver(null);
            const file = e.dataTransfer.files[0];
            if (file) handleFileDrop(slot, file);
        },
        [handleFileDrop]
    );

    const readFile = (file: File): Promise<string> =>
        new Promise((res, rej) => {
            const reader = new FileReader();
            reader.onload = () => res(reader.result as string);
            reader.onerror = rej;
            reader.readAsText(file);
        });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim()) return;
        setError(null);

        // Pre-submission validation: ensure all 4 files are present
        const missingSlots = FILE_SLOTS.filter(slot => slot.required && !files[slot.id]);
        if (missingSlots.length > 0) {
            const errorMsg = `Validation Error: Please upload all four required files. Missing: ${missingSlots.map(s => s.label).join(', ')}`;
            setError(errorMsg);
            return;
        }

        setProgress(10);

        try {
            const payload: IncidentPayload = { title, description };

            if (files.logs) {
                setProgress(25);
                payload.logs = { filename: files.logs.name, content: await readFile(files.logs) };
            }
            if (files.stack_trace) {
                setProgress(40);
                payload.stack_trace = {
                    filename: files.stack_trace.name,
                    content: await readFile(files.stack_trace),
                };
            }
            if (files.metrics) {
                setProgress(55);
                const text = await readFile(files.metrics);
                payload.metrics = { filename: files.metrics.name, data: JSON.parse(text) };
            }
            if (files.deployment) {
                setProgress(70);
                const text = await readFile(files.deployment);
                const parsed = JSON.parse(text);
                // Schema alignment: ensure all fields match DeploymentArtifact exactly
                payload.deployment = {
                    filename: files.deployment.name,
                    environment: parsed.environment || 'production',
                    version: parsed.version || 'unknown',
                    config_vars: parsed.config_vars || {},
                    deployed_at: parsed.deployed_at || new Date().toISOString()
                };
            }

            // Log outgoing request payload in development mode
            if ((import.meta as any).env?.DEV) {
                console.log('[DEBUG] Outgoing IncidentPayload:', payload);
            }

            setProgress(85);
            const result = await investigationsApi.analyze(payload);
            setProgress(100);
            setTimeout(() => navigate(`/report/${result.incident_id}`), 400);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Investigation failed. Check backend.');
            setProgress(null);
        }
    };

    const isSubmitting = progress !== null && progress < 100;

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-white">Upload Incident</h1>
                <p className="text-sm text-slate-500 mt-0.5">
                    Upload your artifacts — the LangGraph workflow will analyze them automatically.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
                {/* Incident details */}
                <div className="glass-card p-5 space-y-4">
                    <h2 className="text-sm font-semibold text-slate-300">Incident Details</h2>
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 mb-1.5">
                            Incident Title <span className="text-red-400">*</span>
                        </label>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="e.g. API gateway timeouts in production"
                            className="input-base"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 mb-1.5">
                            Symptoms / Context
                        </label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Describe what users reported, when the issue started, which services are affected…"
                            className="input-base h-20 resize-none"
                        />
                    </div>
                </div>

                {/* File drop zones */}
                <div className="glass-card p-5 space-y-4">
                    <h2 className="text-sm font-semibold text-slate-300">Artifact Upload</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {FILE_SLOTS.map((slot) => {
                            const hasFile = !!files[slot.id];
                            const isDragging = dragOver === slot.id;
                            return (
                                <label
                                    key={slot.id}
                                    onDrop={onDrop(slot.id)}
                                    onDragOver={(e) => { e.preventDefault(); setDragOver(slot.id); }}
                                    onDragLeave={() => setDragOver(null)}
                                    className={`relative cursor-pointer border-2 border-dashed rounded-xl p-4 transition-all ${isDragging ? 'border-indigo-500 bg-indigo-500/10' : colorMap[slot.color]
                                        } ${hasFile ? 'border-solid' : ''}`}
                                >
                                    <input
                                        type="file"
                                        accept={slot.accept}
                                        className="sr-only"
                                        onChange={(e) => {
                                            const f = e.target.files?.[0];
                                            if (f) handleFileDrop(slot.id, f);
                                        }}
                                    />
                                    <div className="flex items-start gap-3">
                                        <div className={iconColorMap[slot.color]}>
                                            {hasFile ? (
                                                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                                            ) : (
                                                <File className="w-5 h-5" />
                                            )}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs font-semibold text-white">
                                                {slot.label}
                                                {slot.required && <span className="text-red-400 ml-1">*</span>}
                                            </p>
                                            {hasFile ? (
                                                <p className="text-[10px] text-emerald-400 font-mono truncate mt-0.5">
                                                    {files[slot.id]!.name}
                                                </p>
                                            ) : (
                                                <p className="text-[10px] text-slate-500 mt-0.5">{slot.hint}</p>
                                            )}
                                        </div>
                                        {hasFile && (
                                            <button
                                                type="button"
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    setFiles((prev) => { const n = { ...prev }; delete n[slot.id]; return n; });
                                                }}
                                                className="text-slate-600 hover:text-red-400 transition-colors"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        )}
                                    </div>
                                </label>
                            );
                        })}
                    </div>
                </div>

                {/* Selected Files Summary */}
                {Object.keys(files).length > 0 && (
                    <div className="glass-card p-4 space-y-2">
                        <h3 className="text-xs font-semibold text-slate-400">Selected Filenames</h3>
                        <ul className="text-xs space-y-1">
                            {FILE_SLOTS.map((slot) => {
                                const file = files[slot.id];
                                return file ? (
                                    <li key={slot.id} className="flex justify-between items-center text-slate-300">
                                        <span className="font-medium text-slate-400">{slot.label}:</span>
                                        <span className="font-mono text-emerald-400 bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/10 truncate max-w-[250px]">
                                            {file.name}
                                        </span>
                                    </li>
                                ) : (
                                    <li key={slot.id} className="flex justify-between items-center text-slate-500">
                                        <span>{slot.label}:</span>
                                        <span className="italic text-red-400/80">Missing</span>
                                    </li>
                                );
                            })}
                        </ul>
                    </div>
                )}

                {/* Progress bar */}
                <AnimatePresence>
                    {progress !== null && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="glass-card p-4 space-y-2"
                        >
                            <div className="flex justify-between text-xs text-slate-400">
                                <span>
                                    {progress < 100 ? 'Running multi-agent investigation…' : 'Analysis complete!'}
                                </span>
                                <span>{progress}%</span>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <motion.div
                                    className="h-full bg-gradient-to-r from-indigo-500 to-cyan-400 rounded-full"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${progress}%` }}
                                    transition={{ duration: 0.4 }}
                                />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Error */}
                {error && (
                    <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
                        <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                        {error}
                    </div>
                )}

                {/* Submit */}
                <button
                    type="submit"
                    disabled={!title || isSubmitting}
                    className="btn-primary w-full justify-center py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isSubmitting ? (
                        <>
                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Orchestrating Agents…
                        </>
                    ) : (
                        <>
                            <UploadIcon className="w-4 h-4" />
                            Start Investigation
                            <ChevronRight className="w-4 h-4" />
                        </>
                    )}
                </button>
            </form>
        </div>
    );
}
