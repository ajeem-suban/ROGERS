import React, { useState, useEffect } from 'react';
import { 
  X, 
  Code2, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  RotateCcw, 
  ShieldCheck, 
  Terminal, 
  FilePlus, 
  FileEdit, 
  Shield,
  Activity,
  Check,
  AlertTriangle,
  Play
} from 'lucide-react';
import { DevelopmentTask, TaskImplementationResult, FileOperation } from '../types';
import { implementTask, restoreTask } from '../api/rogers';

interface TaskImplementationModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  projectName: string;
  task: DevelopmentTask | null;
  onTaskUpdated: () => void;
}

const MISSION_STEPS = [
  { id: 'RECON', label: 'RECON', desc: 'Inspect existing files' },
  { id: 'IMPLEMENT', label: 'IMPLEMENT', desc: 'Generate code' },
  { id: 'SECURE', label: 'SECURE', desc: 'Sandbox validation' },
  { id: 'SNAPSHOT', label: 'SNAPSHOT', desc: 'Backup files' },
  { id: 'VALIDATE', label: 'VALIDATE', desc: 'Static compilation' },
  { id: 'TEST', label: 'TEST', desc: 'Run automated tests' },
  { id: 'REPAIR', label: 'REPAIR', desc: 'Bounded AI repair' },
  { id: 'VERIFY', label: 'VERIFY', desc: 'Final verification' },
];

export const TaskImplementationModal: React.FC<TaskImplementationModalProps> = ({
  isOpen,
  onClose,
  projectId,
  projectName,
  task,
  onTaskUpdated,
}) => {
  const [mode, setMode] = useState<'confirm' | 'progress' | 'result'>('confirm');
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);
  const [progressPercent, setProgressPercent] = useState<number>(10);
  const [currentStageLabel, setCurrentStageLabel] = useState<string>('RECON');
  const [result, setResult] = useState<TaskImplementationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeDiffFile, setActiveDiffFile] = useState<string | null>(null);
  const [diffViewMode, setDiffViewMode] = useState<'after' | 'before' | 'split'>('after');
  const [isRestoring, setIsRestoring] = useState(false);
  const [restoreMessage, setRestoreMessage] = useState<string | null>(null);

  useEffect(() => {
    if (task) {
      if (task.implementation_result) {
        setResult(task.implementation_result);
        setMode('result');
        if (task.implementation_result.changes.length > 0) {
          setActiveDiffFile(task.implementation_result.changes[0].path);
        }
      } else {
        setMode('confirm');
        setResult(null);
      }
      setError(null);
      setRestoreMessage(null);
    }
  }, [task, isOpen]);

  if (!isOpen || !task) return null;

  const handleStartMission = async () => {
    setMode('progress');
    setActiveStepIndex(0);
    setProgressPercent(12);
    setCurrentStageLabel('RECON');
    setError(null);
    setRestoreMessage(null);

    // Realistic telemetry stepper during async backend execution
    const interval = setInterval(() => {
      setActiveStepIndex((prev) => {
        const next = prev + 1;
        if (next === 1) {
          setProgressPercent(28);
          setCurrentStageLabel('IMPLEMENTING');
        } else if (next === 2) {
          setProgressPercent(45);
          setCurrentStageLabel('SECURING');
        } else if (next === 3) {
          setProgressPercent(60);
          setCurrentStageLabel('SNAPSHOT');
        } else if (next === 4) {
          setProgressPercent(75);
          setCurrentStageLabel('VALIDATING');
        } else if (next === 5) {
          setProgressPercent(88);
          setCurrentStageLabel('TESTING');
        }
        return next < 5 ? next : prev;
      });
    }, 800);

    try {
      const taskId = task.id || task.title;
      const res = await implementTask(projectId, taskId);
      clearInterval(interval);
      setResult(res);

      if (res.verified) {
        setActiveStepIndex(7);
        setProgressPercent(100);
        setCurrentStageLabel('VERIFIED');
      } else if (res.status === 'success' || res.status === 'completed') {
        setActiveStepIndex(7);
        setProgressPercent(100);
        setCurrentStageLabel('COMPLETED');
      } else {
        setProgressPercent(85);
        setCurrentStageLabel('FAILED');
      }

      setMode('result');
      if (res.changes.length > 0) {
        setActiveDiffFile(res.changes[0].path);
      }
      onTaskUpdated();
    } catch (err: any) {
      clearInterval(interval);
      setError(err.message || 'Mission execution failed.');
      setMode('result');
      onTaskUpdated();
    }
  };

  const handleRestore = async () => {
    if (!window.confirm('Are you sure you want to revert changes from the snapshot backup?')) return;
    setIsRestoring(true);
    setRestoreMessage(null);
    try {
      const taskId = task.id || task.title;
      const res = await restoreTask(projectId, taskId);
      setRestoreMessage(res.message);
      setResult(null);
      setMode('confirm');
      onTaskUpdated();
    } catch (err: any) {
      setError(err.message || 'Failed to restore snapshot.');
    } finally {
      setIsRestoring(false);
    }
  };

  const projectSlug = projectName.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-');
  const selectedChange: FileOperation | undefined = result?.changes.find(c => c.path === activeDiffFile);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#050811]/90 backdrop-blur-md p-4 overflow-y-auto">
      <div className="bg-[#0a0e17] border border-blue-900/40 rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-[0_0_50px_rgba(30,58,138,0.25)] overflow-hidden">
        
        {/* Top Mission Accent Bar (Red, White, Blue) */}
        <div className="h-1 w-full bg-gradient-to-r from-red-600 via-slate-200 to-blue-600"></div>

        {/* Modal Header */}
        <div className="p-5 border-b border-blue-950/60 bg-[#0d1322] flex items-center justify-between">
          <div className="flex items-center space-x-3.5">
            {/* Concentric Shield Icon Accent */}
            <div className="relative w-10 h-10 rounded-full bg-blue-950 border border-blue-500/40 flex items-center justify-center shadow-[0_0_12px_rgba(59,130,246,0.3)]">
              <div className="w-7 h-7 rounded-full border border-red-500/50 flex items-center justify-center">
                <span className="text-white text-xs font-black">★</span>
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono font-bold tracking-widest uppercase text-blue-400">
                  🛡️ MISSION CONTROL
                </span>
                <span className="text-slate-500 text-xs">/</span>
                <span className="text-[11px] font-mono text-slate-300 font-semibold uppercase tracking-wider">
                  FEATURE IMPLEMENTATION
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded uppercase border bg-blue-950/80 text-blue-300 border-blue-800">
                  {task.priority} PRIORITY
                </span>
              </div>
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight mt-0.5">
                {task.title}
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Target Repository Strip */}
        <div className="px-6 py-2 bg-[#070b14] border-b border-slate-800/60 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center space-x-2 text-slate-400">
            <span className="text-slate-500">TARGET:</span>
            <span className="text-blue-300 font-medium bg-blue-950/40 px-2 py-0.5 rounded border border-blue-900/40">
              generated_projects/{projectSlug}/
            </span>
          </div>
          <div className="flex items-center space-x-3 text-slate-400">
            <span className="flex items-center space-x-1.5 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-[11px]">SANDBOX PROTECTED</span>
            </span>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* STATE 1: MISSION BRIEFING (Confirm Mode) */}
          {mode === 'confirm' && (
            <div className="space-y-6">
              {/* Tactical Briefing Box */}
              <div className="p-5 rounded-xl bg-[#0d1322] border border-blue-900/50 shadow-inner">
                <div className="flex items-center space-x-2 text-xs font-mono font-bold tracking-wider uppercase text-blue-400 mb-3 pb-2 border-b border-blue-950">
                  <span>🛡️ MISSION BRIEFING</span>
                </div>
                
                <div className="space-y-3.5 text-sm">
                  <div>
                    <span className="text-xs font-mono uppercase text-slate-400 font-bold block mb-1">
                      OBJECTIVE
                    </span>
                    <p className="text-slate-200 leading-relaxed font-sans">
                      {task.description}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                    <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
                      <span className="text-[11px] font-mono uppercase text-slate-400 font-semibold block mb-1">
                        VALIDATION PIPELINE
                      </span>
                      <p className="text-xs text-slate-300 font-mono">
                        ✓ Python Bytecode Compilation (compileall)<br />
                        ✓ Automated Test Verification (pytest)
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
                      <span className="text-[11px] font-mono uppercase text-slate-400 font-semibold block mb-1">
                        BOUNDED REPAIR LOOP
                      </span>
                      <p className="text-xs text-slate-300 font-mono">
                        ✓ Max 3 Automated Repair Attempts<br />
                        ✓ Root-cause diagnosis & targeted patches
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Security Guarantees Panel */}
              <div className="p-4 rounded-xl bg-[#090d18] border border-slate-800/80">
                <div className="flex items-center space-x-2 text-xs font-mono font-bold tracking-wider uppercase text-emerald-400 mb-3">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>🛡️ DEFENSE ARCHITECTURE CHECKS</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs font-mono text-slate-300">
                  <div className="flex items-center space-x-2">
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Project root locked</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Path traversal blocked</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>.git access blocked</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Pre-modification snapshot</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Arbitrary shell blocked</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Allowlisted validation only</span>
                  </div>
                </div>
              </div>

              {restoreMessage && (
                <div className="p-3.5 rounded-xl bg-blue-950/60 border border-blue-800/60 text-blue-200 text-xs font-mono flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0" />
                  <span>{restoreMessage}</span>
                </div>
              )}
            </div>
          )}

          {/* STATE 2: LIVE MISSION PROGRESSION */}
          {mode === 'progress' && (
            <div className="py-6 flex flex-col items-center justify-center space-y-8">
              
              {/* Shield Circular Progress Indicator */}
              <div className="relative w-44 h-44 flex items-center justify-center">
                {/* Outer Ring (Red Shield Accent) */}
                <div className="absolute inset-0 rounded-full border-4 border-red-600/80 animate-[spin_10s_linear_infinite] shadow-[0_0_20px_rgba(220,38,38,0.4)]"></div>
                {/* Middle Ring (Silver/White Armor Accent) */}
                <div className="absolute inset-2.5 rounded-full border-2 border-slate-300/60"></div>
                {/* Inner Ring (Command Blue) */}
                <div className="absolute inset-5 rounded-full border-4 border-blue-600/90 shadow-inner"></div>
                {/* Center Core */}
                <div className="absolute inset-8 rounded-full bg-[#0a0e17] flex flex-col items-center justify-center text-center p-2">
                  <span className="text-white text-base font-black tracking-widest">★</span>
                  <span className="text-2xl font-black font-mono text-white tracking-tight mt-0.5">
                    {progressPercent}%
                  </span>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-blue-400 mt-0.5">
                    {currentStageLabel}
                  </span>
                </div>
              </div>

              {/* Mission Execution Stepper */}
              <div className="w-full max-w-2xl">
                <div className="flex items-center justify-between gap-1 overflow-x-auto pb-2">
                  {MISSION_STEPS.map((s, idx) => {
                    const isDone = idx < activeStepIndex;
                    const isActive = idx === activeStepIndex;
                    return (
                      <div key={s.id} className="flex flex-col items-center min-w-[70px]">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-mono font-bold transition-all ${
                          isDone 
                            ? 'bg-emerald-950 border border-emerald-500 text-emerald-400' 
                            : isActive 
                            ? 'bg-blue-950 border-2 border-blue-400 text-blue-200 ring-2 ring-blue-500/40 animate-pulse'
                            : 'bg-slate-900 border border-slate-800 text-slate-500'
                        }`}>
                          {isDone ? '✓' : isActive ? '◉' : '○'}
                        </div>
                        <span className={`text-[10px] font-mono font-bold tracking-wider uppercase mt-1.5 ${
                          isActive ? 'text-blue-300' : isDone ? 'text-emerald-400' : 'text-slate-500'
                        }`}>
                          {s.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="text-center space-y-1">
                <p className="text-sm font-semibold text-slate-200">
                  Executing autonomous mission pipeline...
                </p>
                <p className="text-xs font-mono text-slate-400">
                  Sandboxed environment active • Pre-modification backup engaged
                </p>
              </div>
            </div>
          )}

          {/* STATE 3: MISSION RESULTS & INSPECTION */}
          {mode === 'result' && (
            <div className="space-y-6">
              
              {/* Mission Outcome Banner */}
              {result && (
                <div className={`p-4 rounded-xl border flex items-center justify-between ${
                  result.verified
                    ? 'bg-blue-950/60 border-blue-600/70 shadow-[0_0_25px_rgba(59,130,246,0.25)]'
                    : result.status === 'success' || result.status === 'completed'
                    ? 'bg-emerald-950/60 border-emerald-700/60'
                    : 'bg-rose-950/60 border-rose-800/70'
                }`}>
                  <div className="flex items-center space-x-3.5">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-base ${
                      result.verified
                        ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(59,130,246,0.6)]'
                        : result.status === 'success' || result.status === 'completed'
                        ? 'bg-emerald-600 text-white'
                        : 'bg-rose-600 text-white'
                    }`}>
                      {result.verified ? '★' : result.status === 'success' ? '✓' : '✕'}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                          {result.verified 
                            ? '🛡️ MISSION VERIFIED — FEATURE OPERATIONAL' 
                            : result.status === 'success' || result.status === 'completed'
                            ? 'MISSION COMPLETED (TESTS NOT AVAILABLE)' 
                            : '⚠ MISSION INTERRUPTED — VERIFICATION FAILED'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 mt-0.5">
                        {result.summary}
                      </p>
                    </div>
                  </div>

                  {result.verified && (
                    <div className="hidden sm:block text-right font-mono">
                      <span className="text-[10px] text-blue-300 uppercase tracking-widest block font-bold">
                        MISSION TAGLINE
                      </span>
                      <span className="text-xs font-bold text-white tracking-wider">
                        “I Can Do This All Day.”
                      </span>
                    </div>
                  )}
                </div>
              )}

              {error && (
                <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-200 text-xs font-mono">
                  <div className="flex items-center space-x-2 font-bold mb-1">
                    <AlertCircle className="w-4 h-4 text-rose-400" />
                    <span>EXECUTION ERROR</span>
                  </div>
                  <p>{error}</p>
                </div>
              )}

              {/* Automated Test Report Section */}
              {result?.test_result && (
                <div className="p-4 rounded-xl bg-[#090d18] border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs font-mono font-bold tracking-wider uppercase">
                    <div className="flex items-center space-x-2 text-slate-200">
                      <Activity className="w-4 h-4 text-blue-400" />
                      <span>🧪 AUTOMATED TEST REPORT</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${
                      result.test_result.status === 'passed'
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-700'
                        : result.test_result.status === 'failed'
                        ? 'bg-rose-950 text-rose-300 border-rose-700'
                        : 'bg-slate-800 text-slate-300 border-slate-700'
                    }`}>
                      STATUS: {result.test_result.status.toUpperCase()}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center text-xs font-mono">
                    <div className="p-2.5 rounded bg-slate-950/80 border border-slate-800/80">
                      <span className="text-slate-400 text-[10px] block">TOTAL TESTS</span>
                      <span className="text-lg font-bold text-white">{result.test_result.tests_total}</span>
                    </div>
                    <div className="p-2.5 rounded bg-emerald-950/30 border border-emerald-900/40">
                      <span className="text-emerald-400 text-[10px] block">PASSED</span>
                      <span className="text-lg font-bold text-emerald-300">{result.test_result.tests_passed}</span>
                    </div>
                    <div className="p-2.5 rounded bg-rose-950/30 border border-rose-900/40">
                      <span className="text-rose-400 text-[10px] block">FAILED</span>
                      <span className="text-lg font-bold text-rose-300">{result.test_result.tests_failed}</span>
                    </div>
                    <div className="p-2.5 rounded bg-slate-950/80 border border-slate-800/80">
                      <span className="text-slate-400 text-[10px] block">SKIPPED</span>
                      <span className="text-lg font-bold text-slate-300">{result.test_result.tests_skipped}</span>
                    </div>
                    <div className="p-2.5 rounded bg-slate-950/80 border border-slate-800/80">
                      <span className="text-slate-400 text-[10px] block">DURATION</span>
                      <span className="text-lg font-bold text-white">{result.test_result.duration_seconds}s</span>
                    </div>
                  </div>

                  {result.test_result.failure_summary && (
                    <div className="p-3 rounded bg-rose-950/40 border border-rose-900/50 text-xs font-mono text-rose-300">
                      <span className="font-bold block mb-1">FAILURES DETECTED:</span>
                      <p>{result.test_result.failure_summary}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Bounded Repair Attempts History (if any occurred) */}
              {result && result.repair_attempts && result.repair_attempts.length > 0 && (
                <div className="p-4 rounded-xl bg-[#090d18] border border-amber-900/40 space-y-3">
                  <div className="flex items-center space-x-2 text-xs font-mono font-bold tracking-wider uppercase text-amber-400 pb-2 border-b border-amber-950">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span>BOUNDED AI REPAIR LOG ({result.repair_attempts.length}/3 ATTEMPTS)</span>
                  </div>
                  <div className="space-y-2">
                    {result.repair_attempts.map((att, idx) => (
                      <div key={idx} className="p-3 rounded bg-slate-950/90 border border-slate-800 text-xs font-mono space-y-1">
                        <div className="flex items-center justify-between text-slate-300 font-bold">
                          <span>Attempt {att.attempt_number}/3: {att.summary}</span>
                          <span className={att.test_result.status === 'passed' ? 'text-emerald-400' : 'text-rose-400'}>
                            {att.test_result.status.toUpperCase()}
                          </span>
                        </div>
                        {att.failure_analysis && (
                          <p className="text-slate-400 text-[11px]">
                            Diagnosis: {att.failure_analysis.root_cause} (Confidence: {Math.round(att.failure_analysis.confidence * 100)}%)
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Mission Execution Log */}
              {result?.mission_logs && result.mission_logs.length > 0 && (
                <div className="p-4 rounded-xl bg-[#070b14] border border-slate-800 space-y-2 font-mono text-xs">
                  <div className="flex items-center space-x-2 text-slate-400 font-bold uppercase text-[11px] pb-1 border-b border-slate-800">
                    <Terminal className="w-3.5 h-3.5 text-blue-400" />
                    <span>CHRONOLOGICAL MISSION LOG</span>
                  </div>
                  <div className="max-h-36 overflow-y-auto space-y-1 pr-2">
                    {result.mission_logs.map((l, i) => (
                      <div key={i} className="flex items-start space-x-2 text-[11px] leading-relaxed">
                        <span className="text-slate-500 shrink-0">{l.timestamp}</span>
                        <span className={`px-1 rounded text-[10px] uppercase font-bold shrink-0 ${
                          l.level === 'success' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/50' :
                          l.level === 'error' ? 'bg-rose-950 text-rose-300 border border-rose-800/50' :
                          l.level === 'warning' ? 'bg-amber-950 text-amber-300 border border-amber-800/50' :
                          'bg-blue-950 text-blue-300 border border-blue-900/50'
                        }`}>
                          {l.stage}
                        </span>
                        <span className={l.level === 'error' ? 'text-rose-300' : l.level === 'success' ? 'text-emerald-300' : 'text-slate-300'}>
                          {l.message}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Code Changes Diff Review */}
              {result && result.changes.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-xs font-mono font-bold tracking-wider uppercase text-slate-300">
                      <Code2 className="w-4 h-4 text-blue-400" />
                      <span>🛡️ CHANGE REVIEW — MISSION PATCH ({result.changes.length} FILES)</span>
                    </div>

                    {/* Diff View Mode Selector */}
                    <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-[11px] font-mono">
                      <button
                        onClick={() => setDiffViewMode('after')}
                        className={`px-2.5 py-1 rounded-md transition-colors ${
                          diffViewMode === 'after' ? 'bg-blue-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                        }`}
                      >
                        Updated
                      </button>
                      <button
                        onClick={() => setDiffViewMode('before')}
                        className={`px-2.5 py-1 rounded-md transition-colors ${
                          diffViewMode === 'before' ? 'bg-blue-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                        }`}
                      >
                        Original
                      </button>
                    </div>
                  </div>

                  {/* File Tabs */}
                  <div className="flex items-center space-x-2 overflow-x-auto pb-1 text-xs font-mono">
                    {result.changes.map((c) => (
                      <button
                        key={c.path}
                        onClick={() => setActiveDiffFile(c.path)}
                        className={`px-3 py-1.5 rounded-lg border flex items-center space-x-1.5 transition-all shrink-0 ${
                          activeDiffFile === c.path
                            ? 'bg-blue-950/80 border-blue-500 text-blue-200 shadow-sm'
                            : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                        }`}
                      >
                        {c.operation === 'create' ? (
                          <FilePlus className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <FileEdit className="w-3.5 h-3.5 text-amber-400" />
                        )}
                        <span>{c.path.split('/').pop()}</span>
                      </button>
                    ))}
                  </div>

                  {/* Active Diff File Preview */}
                  {selectedChange && (
                    <div className="rounded-xl border border-slate-800 bg-[#070b14] overflow-hidden">
                      <div className="px-4 py-2 bg-slate-950 border-b border-slate-800 flex items-center justify-between text-xs font-mono">
                        <span className="text-slate-300 font-medium">{selectedChange.path}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                          selectedChange.operation === 'create'
                            ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                            : 'bg-amber-950/60 text-amber-300 border-amber-800'
                        }`}>
                          {selectedChange.operation}
                        </span>
                      </div>
                      <div className="max-h-72 overflow-y-auto p-4 font-mono text-xs text-slate-300 leading-relaxed bg-[#050811]">
                        <pre>
                          {diffViewMode === 'before'
                            ? selectedChange.before_content || '(File was created in this mission)'
                            : selectedChange.content}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Snapshot Backup & Rollback Section */}
              {result?.snapshot_id && (
                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center space-x-2 text-slate-400">
                    <RotateCcw className="w-4 h-4 text-amber-400" />
                    <span>Pre-modification snapshot created:</span>
                    <span className="text-slate-200 font-bold bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      {result.snapshot_id}
                    </span>
                  </div>
                  <button
                    onClick={handleRestore}
                    disabled={isRestoring}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-950/50 hover:bg-amber-900/60 text-amber-300 border border-amber-800/60 transition-colors disabled:opacity-50"
                  >
                    {isRestoring ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <RotateCcw className="w-3.5 h-3.5" />
                    )}
                    <span>Revert to Snapshot</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="p-5 border-t border-slate-800/80 bg-[#0d1322] flex items-center justify-between">
          <div className="text-xs font-mono text-slate-500">
            {mode === 'confirm' ? (
              <span>Human confirmation required before execution.</span>
            ) : mode === 'progress' ? (
              <span>Executing autonomous mission pipeline...</span>
            ) : (
              <span>Review file diff and test reports above.</span>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {mode === 'confirm' && (
              <>
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleStartMission}
                  className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-mono font-bold tracking-wider transition-all shadow-[0_0_15px_rgba(37,99,235,0.4)]"
                >
                  <Shield className="w-4 h-4" />
                  <span>LAUNCH MISSION</span>
                </button>
              </>
            )}

            {mode === 'progress' && (
              <button
                disabled
                className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-blue-900/50 text-blue-300 text-xs font-mono opacity-80 cursor-wait"
              >
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>MISSION ACTIVE...</span>
              </button>
            )}

            {mode === 'result' && (
              <>
                {result?.status === 'failed' && (
                  <button
                    onClick={handleStartMission}
                    className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-mono font-bold transition-all"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Retry Mission</span>
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-mono transition-colors"
                >
                  Close Mission Control
                </button>
              </>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
