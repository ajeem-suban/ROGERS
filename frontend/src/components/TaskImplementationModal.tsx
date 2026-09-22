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
  ArrowRight
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

const IMPLEMENTATION_STEPS = [
  { id: 0, label: 'Reading project structure' },
  { id: 1, label: 'Inspecting relevant files' },
  { id: 2, label: 'Generating implementation' },
  { id: 3, label: 'Applying changes' },
  { id: 4, label: 'Running validation' },
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
  const [currentStep, setCurrentStep] = useState<number>(0);
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

  const handleStartImplementation = async () => {
    setMode('progress');
    setCurrentStep(0);
    setError(null);
    setRestoreMessage(null);

    // Visual step progression while backend runs
    const interval = setInterval(() => {
      setCurrentStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 700);

    try {
      const taskId = task.id || task.title;
      const res = await implementTask(projectId, taskId);
      clearInterval(interval);
      setCurrentStep(4);
      setResult(res);
      setMode('result');
      if (res.changes.length > 0) {
        setActiveDiffFile(res.changes[0].path);
      }
      onTaskUpdated();
    } catch (err: any) {
      clearInterval(interval);
      setError(err.message || 'Task implementation failed.');
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Code2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono font-semibold uppercase text-indigo-400">
                  Feature Implementation
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded uppercase border bg-slate-800 text-slate-300 border-slate-700">
                  {task.priority}
                </span>
              </div>
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                {task.title}
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* STATE 1: Confirmation */}
          {mode === 'confirm' && (
            <div className="space-y-6">
              <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800">
                <h3 className="text-xs font-mono font-semibold uppercase text-slate-400 mb-1">
                  Task Description
                </h3>
                <p className="text-sm text-slate-200 leading-relaxed">
                  {task.description}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-900/50">
                <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-indigo-300 font-mono mb-2">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" />
                  <span>Controlled Execution Guarantees</span>
                </div>
                <ul className="space-y-2 text-xs text-slate-300">
                  <li className="flex items-start space-x-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 shrink-0"></span>
                    <span><strong>Path Sandbox:</strong> Modifications are strictly isolated to the project directory.</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 shrink-0"></span>
                    <span><strong>Snapshot Backup:</strong> Automatic file backups are taken before modifying any files.</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 shrink-0"></span>
                    <span><strong>Safe Validation:</strong> Compiles and validates syntax before completing.</span>
                  </li>
                </ul>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 font-mono text-xs text-slate-400 flex items-center justify-between">
                <span>Target Project:</span>
                <span className="text-indigo-300">generated_projects/{projectSlug}/</span>
              </div>

              {restoreMessage && (
                <div className="p-3 rounded-lg bg-emerald-950/50 border border-emerald-800 text-emerald-300 text-xs">
                  {restoreMessage}
                </div>
              )}
            </div>
          )}

          {/* STATE 2: In-Progress Animation */}
          {mode === 'progress' && (
            <div className="py-6 space-y-6">
              <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
                <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                <div>
                  <h3 className="text-sm font-bold text-white">
                    ROGERS is implementing this task...
                  </h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">
                    Analyzing code and generating safe modifications
                  </p>
                </div>
              </div>

              <div className="space-y-3.5 pl-2">
                {IMPLEMENTATION_STEPS.map((step) => {
                  const isDone = currentStep > step.id;
                  const isCurrent = currentStep === step.id;

                  return (
                    <div
                      key={step.id}
                      className={`flex items-center space-x-3 text-xs font-mono transition-all ${
                        isCurrent
                          ? 'text-indigo-300 font-semibold'
                          : isDone
                          ? 'text-slate-300'
                          : 'text-slate-600'
                      }`}
                    >
                      {isDone ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      ) : isCurrent ? (
                        <div className="w-4 h-4 flex items-center justify-center shrink-0">
                          <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-ping absolute opacity-75"></span>
                          <span className="w-2 h-2 rounded-full bg-indigo-400 relative"></span>
                        </div>
                      ) : (
                        <span className="w-4 h-4 rounded-full border border-slate-700 shrink-0"></span>
                      )}
                      <span>{step.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* STATE 3: Results & Diff Viewer */}
          {mode === 'result' && (
            <div className="space-y-6">
              {error ? (
                <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-200 space-y-2">
                  <div className="flex items-center space-x-2 text-sm font-bold">
                    <AlertCircle className="w-4 h-4 text-rose-400" />
                    <span>Implementation Failed</span>
                  </div>
                  <p className="text-xs font-mono">{error}</p>
                </div>
              ) : result ? (
                <>
                  {/* Status Banner */}
                  <div className={`p-4 rounded-xl border flex items-center justify-between ${
                    result.status === 'success'
                      ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-200'
                      : 'bg-rose-950/40 border-rose-800/60 text-rose-200'
                  }`}>
                    <div className="flex items-center space-x-3">
                      {result.status === 'success' ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-rose-400" />
                      )}
                      <div>
                        <div className="text-sm font-bold capitalize">
                          Implementation {result.status}
                        </div>
                        <div className="text-xs text-slate-300 mt-0.5">
                          {result.summary}
                        </div>
                      </div>
                    </div>

                    <div className="text-xs font-mono px-3 py-1 rounded bg-slate-900 border border-slate-700">
                      {result.files_changed.length} file{result.files_changed.length === 1 ? '' : 's'} updated
                    </div>
                  </div>

                  {/* Validation Output */}
                  <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs font-mono space-y-1">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="flex items-center space-x-1.5">
                        <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                        <span>Validation Check:</span>
                        <code className="text-slate-200">{result.validation.command}</code>
                      </span>
                      <span className={result.validation.status === 'passed' ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                        {result.validation.status.toUpperCase()}
                      </span>
                    </div>
                    {result.validation.output && (
                      <p className="text-slate-400 text-[11px] pt-1">
                        {result.validation.output}
                      </p>
                    )}
                  </div>

                  {/* File Changes Tabs & Diff */}
                  {result.changes.length > 0 && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono uppercase text-slate-400 font-semibold">
                          File Changes
                        </span>
                        <div className="flex space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-[11px]">
                          <button
                            onClick={() => setDiffViewMode('after')}
                            className={`px-2.5 py-1 rounded ${diffViewMode === 'after' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                          >
                            New Code
                          </button>
                          {selectedChange?.before_content && (
                            <button
                              onClick={() => setDiffViewMode('before')}
                              className={`px-2.5 py-1 rounded ${diffViewMode === 'before' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                            >
                              Before
                            </button>
                          )}
                        </div>
                      </div>

                      {/* File selector pills */}
                      <div className="flex flex-wrap gap-2">
                        {result.changes.map((change) => (
                          <button
                            key={change.path}
                            onClick={() => setActiveDiffFile(change.path)}
                            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono border transition-colors ${
                              activeDiffFile === change.path
                                ? 'bg-slate-800 text-slate-100 border-indigo-500'
                                : 'bg-slate-950/60 text-slate-400 border-slate-800 hover:text-slate-200'
                            }`}
                          >
                            {change.operation === 'create' ? (
                              <FilePlus className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <FileEdit className="w-3.5 h-3.5 text-amber-400" />
                            )}
                            <span>{change.path}</span>
                          </button>
                        ))}
                      </div>

                      {/* Code Content Box */}
                      {selectedChange && (
                        <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden">
                          <div className="px-4 py-2 bg-slate-900 border-b border-slate-800 text-xs font-mono flex items-center justify-between text-slate-400">
                            <span>{selectedChange.path}</span>
                            <span className="capitalize text-[10px] px-2 py-0.5 rounded bg-slate-800">
                              {selectedChange.operation}
                            </span>
                          </div>
                          <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto max-h-72 leading-relaxed">
                            {diffViewMode === 'before' && selectedChange.before_content
                              ? selectedChange.before_content
                              : selectedChange.content}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : null}
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex items-center justify-between">
          <div>
            {result?.snapshot_id && (
              <button
                onClick={handleRestore}
                disabled={isRestoring}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-300 bg-rose-950/40 hover:bg-rose-900/50 border border-rose-800/60 transition-colors disabled:opacity-50"
                title="Rollback this task to the pre-modification snapshot"
              >
                <RotateCcw className={`w-3.5 h-3.5 ${isRestoring ? 'animate-spin' : ''}`} />
                <span>{isRestoring ? 'Restoring...' : 'Restore Backup'}</span>
              </button>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {mode === 'confirm' && (
              <>
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg text-xs text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleStartImplementation}
                  className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition-colors"
                >
                  <span>Implement Task</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </>
            )}

            {mode === 'result' && (
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
              >
                Back to Tasks
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
