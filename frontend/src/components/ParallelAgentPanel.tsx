import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Play, 
  Pause, 
  RotateCcw, 
  XCircle, 
  Lock, 
  Layers, 
  Cpu, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  FileText,
  Sliders
} from 'lucide-react';
import { 
  Project, 
  ParallelExecutionPlan, 
  ParallelMissionState, 
  ParallelMissionReport
} from '../types';
import { 
  getParallelPlan, 
  getParallelStatus, 
  startParallelMission, 
  pauseParallelMission, 
  resumeParallelMission, 
  cancelParallelMission, 
  getParallelReport 
} from '../api/rogers';

interface ParallelAgentPanelProps {
  project: Project;
  onRefreshProject?: () => void;
  onOpenTaskImplementation?: (taskId: string) => void;
}

export const ParallelAgentPanel: React.FC<ParallelAgentPanelProps> = ({ 
  project, 
  onRefreshProject,
  onOpenTaskImplementation
}) => {
  const [plan, setPlan] = useState<ParallelExecutionPlan | null>(null);
  const [state, setState] = useState<ParallelMissionState | null>(null);
  const [report, setReport] = useState<ParallelMissionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [concurrentLimit, setConcurrentLimit] = useState(3);
  const [showReportModal, setShowReportModal] = useState(false);

  const fetchTelemetry = async () => {
    try {
      setError(null);
      const [planData, stateData] = await Promise.all([
        getParallelPlan(project.id),
        getParallelStatus(project.id)
      ]);
      setPlan(planData);
      setState(stateData);
      if (stateData.config?.max_concurrent_agents) {
        setConcurrentLimit(stateData.config.max_concurrent_agents);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch parallel telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
  }, [project.id]);

  // Polling when parallel mission is running
  useEffect(() => {
    if (state?.status === 'running') {
      const interval = setInterval(async () => {
        try {
          const fresh = await getParallelStatus(project.id);
          setState(fresh);
          if (fresh.status !== 'running') {
            clearInterval(interval);
            if (onRefreshProject) onRefreshProject();
          }
        } catch (e) {
          console.error('Error polling parallel state:', e);
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [state?.status, project.id]);

  const handleStart = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await startParallelMission(project.id, concurrentLimit);
      setState(updated);
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err?.message || 'Failed to start parallel mission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handlePause = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await pauseParallelMission(project.id);
      setState(updated);
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err?.message || 'Failed to pause parallel mission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await resumeParallelMission(project.id);
      setState(updated);
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err?.message || 'Failed to resume parallel mission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm('Cancel the multi-agent parallel mission?')) return;
    setActionLoading(true);
    setError(null);
    try {
      const updated = await cancelParallelMission(project.id);
      setState(updated);
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err?.message || 'Failed to cancel parallel mission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleViewReport = async () => {
    try {
      const rep = await getParallelReport(project.id);
      setReport(rep);
      setShowReportModal(true);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch parallel report.');
    }
  };

  if (loading) {
    return (
      <div className="bg-[#0a0e17] border border-blue-900/30 rounded-2xl p-12 text-center shadow-2xl">
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="relative w-16 h-16">
            <div className="absolute inset-0 rounded-full border-4 border-blue-600/20 border-t-blue-500 animate-spin" />
            <Users className="w-8 h-8 text-blue-400 absolute inset-0 m-auto animate-pulse" />
          </div>
          <p className="text-slate-400 font-mono text-sm uppercase tracking-widest">
            Mobilizing Multi-Agent Squadron...
          </p>
        </div>
      </div>
    );
  }

  const missionStatus = state?.status || 'ready';
  const totalTasks = plan?.total_tasks || 0;
  const completedCount = state?.completed_task_ids.length || 0;
  const failedCount = state?.failed_task_ids.length || 0;
  const blockedCount = state?.blocked_task_ids.length || 0;
  const runningCount = state?.running_task_ids.length || 0;
  const progressPercent = totalTasks > 0 ? Math.round((completedCount / totalTasks) * 100) : 0;
  const lockedFilesList = Object.entries(state?.file_locks || {});

  const getAgentRoleBadge = (role: string) => {
    switch (role) {
      case 'researcher':
        return 'text-sky-300 bg-sky-950/70 border-sky-600/40';
      case 'architect':
        return 'text-purple-300 bg-purple-950/70 border-purple-600/40';
      case 'developer':
        return 'text-emerald-300 bg-emerald-950/70 border-emerald-600/40';
      case 'tester':
        return 'text-amber-300 bg-amber-950/70 border-amber-600/40';
      case 'reviewer':
        return 'text-red-300 bg-red-950/70 border-red-600/40';
      default:
        return 'text-blue-300 bg-blue-950/70 border-blue-600/40';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Squadron Controls */}
      <div className="bg-[#0a0e17] border border-blue-900/40 rounded-2xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        {/* Ambient Glow */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 rounded-full bg-blue-600/10 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-80 h-80 rounded-full bg-indigo-600/10 blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-blue-900/40">
          <div className="flex items-start space-x-4">
            <div className="relative w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-950 via-slate-900 to-indigo-950 border border-blue-600/50 p-2.5 flex items-center justify-center shadow-lg">
              <Users className="w-8 h-8 text-blue-400 drop-shadow-[0_0_8px_rgba(59,130,246,0.6)]" />
              {missionStatus === 'running' && (
                <span className="absolute -top-1 -right-1 flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500" />
                </span>
              )}
            </div>

            <div>
              <div className="flex items-center space-x-3 mb-1">
                <span className="text-xs font-mono text-blue-400 uppercase tracking-widest font-bold">
                  MULTI-AGENT PARALLEL EXECUTION
                </span>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider font-bold border ${
                  missionStatus === 'completed'
                    ? 'text-emerald-400 bg-emerald-950/60 border-emerald-500/40'
                    : missionStatus === 'running'
                    ? 'text-blue-400 bg-blue-950/60 border-blue-500/40 animate-pulse'
                    : missionStatus === 'paused'
                    ? 'text-amber-400 bg-amber-950/60 border-amber-500/40'
                    : 'text-indigo-400 bg-indigo-950/60 border-indigo-500/40'
                }`}>
                  STATUS: {missionStatus}
                </span>
              </div>
              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight flex items-center space-x-2">
                <span>Autonomous Agent Squadron</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1 max-w-xl">
                Distributes tasks across specialized agents with conflict-free file locking, dependency preservation, and concurrency caps.
              </p>
            </div>
          </div>

          {/* Action Command Bar */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Concurrency Selector */}
            <div className="flex items-center space-x-2 bg-slate-900/90 border border-blue-900/40 rounded-xl px-3 py-1.5">
              <Sliders className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-[11px] font-mono text-slate-300">Max Agents:</span>
              <select
                value={concurrentLimit}
                disabled={missionStatus === 'running'}
                onChange={(e) => setConcurrentLimit(Number(e.target.value))}
                className="bg-slate-800 text-blue-300 text-xs font-mono rounded px-2 py-0.5 border border-slate-700 outline-none"
              >
                <option value={1}>1 Agent</option>
                <option value={2}>2 Agents</option>
                <option value={3}>3 Agents (Default)</option>
                <option value={4}>4 Agents</option>
                <option value={5}>5 Agents</option>
              </select>
            </div>

            <button
              onClick={fetchTelemetry}
              disabled={actionLoading}
              className="p-2 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
              title="Refresh telemetry"
            >
              <RefreshCw className={`w-4 h-4 ${actionLoading ? 'animate-spin' : ''}`} />
            </button>

            {missionStatus === 'running' ? (
              <>
                <button
                  onClick={handlePause}
                  disabled={actionLoading}
                  className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-amber-600/90 hover:bg-amber-500 text-white font-semibold text-xs transition-all shadow-lg shadow-amber-900/30 border border-amber-400/40"
                >
                  <Pause className="w-4 h-4" />
                  <span>Pause</span>
                </button>
                <button
                  onClick={handleCancel}
                  disabled={actionLoading}
                  className="inline-flex items-center space-x-2 px-3 py-2.5 rounded-xl bg-red-950/60 hover:bg-red-900/80 text-red-300 font-semibold text-xs transition-all border border-red-700/60"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Abort</span>
                </button>
              </>
            ) : missionStatus === 'paused' || missionStatus === 'blocked' || missionStatus === 'failed' ? (
              <>
                <button
                  onClick={handleResume}
                  disabled={actionLoading}
                  className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-all shadow-lg shadow-blue-900/40 border border-blue-400/40"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Resume Parallel</span>
                </button>
                <button
                  onClick={handleCancel}
                  disabled={actionLoading}
                  className="inline-flex items-center space-x-2 px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition-all border border-slate-700"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Abort</span>
                </button>
              </>
            ) : (
              <button
                onClick={handleStart}
                disabled={actionLoading || Boolean(plan && !plan.is_valid) || missionStatus === 'completed'}
                className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs uppercase tracking-wider transition-all shadow-xl shadow-blue-900/50 border border-blue-400/40 disabled:opacity-50"
              >
                <Play className="w-4 h-4 fill-white" />
                <span>{missionStatus === 'completed' ? 'Parallel Complete' : 'Deploy Agents'}</span>
              </button>
            )}

            <button
              onClick={handleViewReport}
              className="inline-flex items-center space-x-1.5 px-3 py-2.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-blue-300 text-xs font-semibold border border-blue-900/40 transition-colors"
            >
              <FileText className="w-4 h-4" />
              <span>Report</span>
            </button>
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="mt-4 p-3.5 rounded-xl bg-red-950/70 border border-red-600/50 text-red-200 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 text-xs">
              Dismiss
            </button>
          </div>
        )}

        {/* Global Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-6">
          <div className="p-3 rounded-xl bg-slate-900/70 border border-blue-900/30">
            <div className="text-[10px] font-mono uppercase text-slate-400">Total Tasks</div>
            <div className="text-lg font-bold text-white mt-0.5">{totalTasks}</div>
          </div>
          <div className="p-3 rounded-xl bg-blue-950/40 border border-blue-800/40">
            <div className="text-[10px] font-mono uppercase text-blue-400">Active / In-Flight</div>
            <div className="text-lg font-bold text-blue-300 mt-0.5">{runningCount}</div>
          </div>
          <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-900/30">
            <div className="text-[10px] font-mono uppercase text-emerald-400">Verified</div>
            <div className="text-lg font-bold text-emerald-300 mt-0.5">{completedCount}</div>
          </div>
          <div className="p-3 rounded-xl bg-red-950/30 border border-red-900/30">
            <div className="text-[10px] font-mono uppercase text-red-400">Failed</div>
            <div className="text-lg font-bold text-red-300 mt-0.5">{failedCount}</div>
          </div>
          <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-900/30">
            <div className="text-[10px] font-mono uppercase text-amber-400">Prereq Blocked</div>
            <div className="text-lg font-bold text-amber-300 mt-0.5">{blockedCount}</div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-6 space-y-2">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="text-slate-400">PARALLEL SQUADRON PROGRESS</span>
            <span className="text-blue-400 font-bold">{progressPercent}%</span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-slate-950 overflow-hidden border border-slate-800">
            <div 
              className="h-full bg-gradient-to-r from-blue-600 via-indigo-500 to-emerald-500 transition-all duration-500 rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Active File Conflict Guard Banner */}
      {lockedFilesList.length > 0 && (
        <div className="bg-[#0a0e17] border border-amber-900/40 rounded-2xl p-4 shadow-lg flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-amber-950/60 border border-amber-600/40">
              <Lock className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <div className="text-xs font-bold text-amber-300 font-mono flex items-center space-x-2">
                <span>ACTIVE FILE-LOCK CONFLICT GUARD</span>
                <span className="text-[10px] bg-amber-900/40 px-2 py-0.5 rounded text-amber-200">
                  {lockedFilesList.length} files locked
                </span>
              </div>
              <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                Concurrent agents prevented from writing to identical target paths.
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5 max-w-md justify-end">
            {lockedFilesList.slice(0, 3).map(([f]) => (
              <span key={f} className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                {f.split('/').pop()}
              </span>
            ))}
            {lockedFilesList.length > 3 && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 text-slate-500">
                +{lockedFilesList.length - 3} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Live Agent Roster Cards */}
      <div className="bg-[#0a0e17] border border-blue-900/30 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-blue-900/30">
          <div className="flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-blue-400" />
            <h3 className="text-base font-bold text-white tracking-wide">
              Specialized Agent Squadron Roster
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {state?.agents.length || 0} registered agents
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {state?.agents.map((ag) => {
            const isBusy = ag.status === 'busy';
            return (
              <div 
                key={ag.agent_id}
                className={`p-4 rounded-xl border transition-all ${
                  isBusy 
                    ? 'bg-blue-950/40 border-blue-500 shadow-md shadow-blue-950/50' 
                    : 'bg-slate-900/40 border-slate-800 text-slate-300'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-white">{ag.name}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono uppercase font-semibold border ${getAgentRoleBadge(ag.role)}`}>
                        {ag.role}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1 line-clamp-1">{ag.specialization}</div>
                  </div>

                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-bold border ${
                    isBusy ? 'bg-blue-950 text-blue-400 border-blue-600/50 animate-pulse' : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}>
                    {ag.status}
                  </span>
                </div>

                {isBusy && ag.current_task_title && (
                  <div className="mt-3 p-2 rounded-lg bg-blue-900/30 border border-blue-700/40 text-[11px] font-mono text-blue-200">
                    <span className="text-blue-400 font-semibold">Active: </span>
                    {ag.current_task_title}
                  </div>
                )}

                <div className="mt-3 flex items-center justify-between text-[11px] font-mono text-slate-400 border-t border-slate-800/80 pt-2">
                  <span>Tasks Completed:</span>
                  <span className="font-bold text-slate-200">{ag.tasks_completed}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Parallel Batches & Task DAG */}
      <div className="bg-[#0a0e17] border border-blue-900/30 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-blue-900/30">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-blue-400" />
            <h3 className="text-base font-bold text-white tracking-wide">
              Parallel Execution Batches (DAG Layers)
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {plan?.parallel_batches.length || 0} parallel stages
          </span>
        </div>

        <div className="space-y-4">
          {plan?.parallel_batches.map((batch, batchIdx) => (
            <div key={batchIdx} className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-bold text-blue-400 uppercase">
                  Stage {batchIdx + 1} — {batch.length} Independent Tasks
                </span>
                <span className="text-slate-500">
                  Runs concurrently up to concurrency limit
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {batch.map((tid) => {
                  const isDone = state?.completed_task_ids.includes(tid);
                  const isFail = state?.failed_task_ids.includes(tid);
                  const isBlock = state?.blocked_task_ids.includes(tid);
                  const isRunning = state?.running_task_ids.includes(tid);
                  const taskItem = plan.tasks.find(tk => tk.task_id === tid);

                  return (
                    <div 
                      key={tid}
                      className={`p-3 rounded-lg border flex items-center justify-between ${
                        isRunning 
                          ? 'bg-blue-950/60 border-blue-500 animate-pulse'
                          : isDone 
                          ? 'bg-slate-900/70 border-emerald-900/40 text-slate-200' 
                          : isFail
                          ? 'bg-red-950/40 border-red-900/40 text-red-200'
                          : isBlock
                          ? 'bg-slate-900/30 border-amber-900/30 text-slate-500'
                          : 'bg-slate-900/40 border-slate-800 text-slate-300'
                      }`}
                    >
                      <div className="flex items-center space-x-2.5">
                        {isDone ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : isFail ? (
                          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                        ) : isRunning ? (
                          <div className="w-4 h-4 rounded-full border-2 border-blue-400 border-t-transparent animate-spin shrink-0" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border border-slate-700 flex items-center justify-center text-[9px] font-mono text-slate-500 shrink-0">
                            •
                          </div>
                        )}
                        <span className="text-xs font-medium line-clamp-1">{taskItem?.title || tid}</span>
                      </div>

                      {onOpenTaskImplementation && (
                        <button
                          onClick={() => onOpenTaskImplementation(tid)}
                          className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors shrink-0 ml-2"
                        >
                          Code
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Report Modal */}
      {showReportModal && report && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#0a0e17] border border-blue-900/60 rounded-2xl max-w-2xl w-full p-6 sm:p-8 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-blue-900/40">
              <div className="flex items-center space-x-3">
                <Users className="w-6 h-6 text-blue-400" />
                <h3 className="text-lg font-bold text-white tracking-wide">
                  Parallel Mission Report
                </h3>
              </div>
              <button 
                onClick={() => setShowReportModal(false)}
                className="text-slate-400 hover:text-white text-sm font-mono"
              >
                ✕ Close
              </button>
            </div>

            <div className="p-4 rounded-xl bg-blue-950/30 border border-blue-900/40 space-y-2">
              <div className="text-xs font-mono uppercase text-blue-400 font-bold">Squadron Debriefing</div>
              <div className="text-sm text-slate-200">{report.summary}</div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-[10px] font-mono text-slate-400">Total Tasks</div>
                <div className="text-lg font-bold text-white">{report.total_tasks}</div>
              </div>
              <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-900/40">
                <div className="text-[10px] font-mono text-emerald-400">Verified</div>
                <div className="text-lg font-bold text-emerald-300">{report.completed_count}</div>
              </div>
              <div className="p-3 rounded-lg bg-red-950/40 border border-red-900/40">
                <div className="text-[10px] font-mono text-red-400">Failed</div>
                <div className="text-lg font-bold text-red-300">{report.failed_count}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-[10px] font-mono text-slate-400">Concurrency</div>
                <div className="text-lg font-bold text-white">{report.concurrent_limit}x</div>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-800">
              <button
                onClick={() => setShowReportModal(false)}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors"
              >
                Close Debrief
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
