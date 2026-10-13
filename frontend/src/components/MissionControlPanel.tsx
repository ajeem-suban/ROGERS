import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Play, 
  Pause, 
  RotateCcw, 
  XCircle, 
  CheckCircle2, 
  AlertTriangle, 
  FileText, 
  GitFork, 
  RefreshCw
} from 'lucide-react';
import { 
  Project, 
  ExecutionPlan, 
  MissionState, 
  MissionExecutionReport
} from '../types';
import { 
  getMissionPlan, 
  getMissionStatus, 
  startMission, 
  pauseMission, 
  resumeMission, 
  cancelMission, 
  getMissionExecutionReport 
} from '../api/rogers';

interface MissionControlPanelProps {
  project: Project;
  onRefreshProject?: () => void;
  onOpenTaskImplementation?: (taskId: string) => void;
}

export const MissionControlPanel: React.FC<MissionControlPanelProps> = ({ 
  project, 
  onRefreshProject,
  onOpenTaskImplementation
}) => {
  const [plan, setPlan] = useState<ExecutionPlan | null>(null);
  const [missionState, setMissionState] = useState<MissionState | null>(null);
  const [report, setReport] = useState<MissionExecutionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showReportModal, setShowReportModal] = useState(false);

  const fetchMissionTelemetry = async () => {
    try {
      setError(null);
      const [planData, stateData] = await Promise.all([
        getMissionPlan(project.id),
        getMissionStatus(project.id)
      ]);
      setPlan(planData);
      setMissionState(stateData);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch mission telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMissionTelemetry();
  }, [project.id]);

  // Polling when running
  useEffect(() => {
    if (missionState?.status === 'running') {
      const interval = setInterval(async () => {
        try {
          const freshState = await getMissionStatus(project.id);
          setMissionState(freshState);
          if (freshState.status !== 'running') {
            clearInterval(interval);
            if (onRefreshProject) onRefreshProject();
          }
        } catch (e) {
          console.error('Error polling mission state:', e);
        }
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [missionState?.status, project.id]);

  const handleStart = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await startMission(project.id);
      setMissionState(updated);
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err?.message || 'Failed to start mission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handlePause = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await pauseMission(project.id);
      setMissionState(updated);
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err?.message || 'Failed to pause mission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await resumeMission(project.id);
      setMissionState(updated);
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err?.message || 'Failed to resume mission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel the autonomous mission?')) return;
    setActionLoading(true);
    setError(null);
    try {
      const updated = await cancelMission(project.id);
      setMissionState(updated);
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err?.message || 'Failed to cancel mission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleViewReport = async () => {
    try {
      const rep = await getMissionExecutionReport(project.id);
      setReport(rep);
      setShowReportModal(true);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch mission report.');
    }
  };

  if (loading) {
    return (
      <div className="bg-[#0a0e17] border border-blue-900/30 rounded-2xl p-12 text-center shadow-2xl">
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="relative w-16 h-16">
            <div className="absolute inset-0 rounded-full border-4 border-blue-600/20 border-t-blue-500 animate-spin" />
            <div className="absolute inset-2 rounded-full border-4 border-red-600/20 border-b-red-500 animate-spin" style={{ animationDirection: 'reverse' }} />
            <Shield className="w-8 h-8 text-blue-400 absolute inset-0 m-auto animate-pulse" />
          </div>
          <p className="text-slate-400 font-mono text-sm uppercase tracking-widest">
            Synchronizing Mission Coordinates...
          </p>
        </div>
      </div>
    );
  }

  const status = missionState?.status || 'ready';
  const totalTasks = plan?.total_tasks || 0;
  const completedCount = missionState?.completed_task_ids.length || 0;
  const failedCount = missionState?.failed_task_ids.length || 0;
  const blockedCount = missionState?.blocked_task_ids.length || 0;
  const progressPercent = totalTasks > 0 ? Math.round((completedCount / totalTasks) * 100) : 0;

  const getStatusColor = (st: string) => {
    switch (st) {
      case 'completed':
        return 'text-emerald-400 bg-emerald-950/60 border-emerald-500/40';
      case 'running':
        return 'text-blue-400 bg-blue-950/60 border-blue-500/40 animate-pulse';
      case 'paused':
        return 'text-amber-400 bg-amber-950/60 border-amber-500/40';
      case 'blocked':
        return 'text-orange-400 bg-orange-950/60 border-orange-500/40';
      case 'failed':
        return 'text-red-400 bg-red-950/60 border-red-500/40';
      case 'cancelled':
        return 'text-slate-400 bg-slate-900/80 border-slate-700/60';
      default:
        return 'text-indigo-400 bg-indigo-950/60 border-indigo-500/40';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Mission Control Header */}
      <div className="bg-[#0a0e17] border border-blue-900/40 rounded-2xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        {/* Subtle Shield Ambient Glow */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 rounded-full bg-blue-600/10 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-80 h-80 rounded-full bg-red-600/10 blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-blue-900/40">
          <div className="flex items-start space-x-4">
            {/* Captain America Shield Badge */}
            <div className="relative w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-950 via-slate-900 to-red-950 border border-blue-700/50 p-2.5 flex items-center justify-center shadow-lg">
              <Shield className="w-8 h-8 text-blue-400 drop-shadow-[0_0_8px_rgba(59,130,246,0.6)]" />
              {status === 'running' && (
                <span className="absolute -top-1 -right-1 flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
                </span>
              )}
            </div>

            <div>
              <div className="flex items-center space-x-3 mb-1">
                <span className="text-xs font-mono text-blue-400 uppercase tracking-widest font-bold">
                  AUTONOMOUS MISSION CONTROL
                </span>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider font-bold border ${getStatusColor(status)}`}>
                  STATUS: {status}
                </span>
              </div>
              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight flex items-center space-x-2">
                <span>Multi-Task Autonomous Execution</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1 max-w-xl">
                Executes the roadmap sequentially in strict dependency order with automated testing, bounded repair, and safe checkpointing.
              </p>
            </div>
          </div>

          {/* Action Command Bar */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={fetchMissionTelemetry}
              disabled={actionLoading}
              className="p-2 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
              title="Refresh telemetry"
            >
              <RefreshCw className={`w-4 h-4 ${actionLoading ? 'animate-spin' : ''}`} />
            </button>

            {status === 'running' ? (
              <>
                <button
                  onClick={handlePause}
                  disabled={actionLoading}
                  className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-amber-600/90 hover:bg-amber-500 text-white font-semibold text-xs transition-all shadow-lg shadow-amber-900/30 border border-amber-400/40"
                >
                  <Pause className="w-4 h-4" />
                  <span>Pause Mission</span>
                </button>
                <button
                  onClick={handleCancel}
                  disabled={actionLoading}
                  className="inline-flex items-center space-x-2 px-3 py-2.5 rounded-xl bg-red-950/60 hover:bg-red-900/80 text-red-300 font-semibold text-xs transition-all border border-red-700/60"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Cancel</span>
                </button>
              </>
            ) : status === 'paused' || status === 'blocked' || status === 'failed' ? (
              <>
                <button
                  onClick={handleResume}
                  disabled={actionLoading || Boolean(plan && !plan.is_valid)}
                  className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-all shadow-lg shadow-blue-900/40 border border-blue-400/40"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Resume Mission</span>
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
                disabled={actionLoading || (plan && !plan.is_valid) || status === 'completed'}
                className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs uppercase tracking-wider transition-all shadow-xl shadow-blue-900/50 border border-blue-400/40 disabled:opacity-50"
              >
                <Play className="w-4 h-4 fill-white" />
                <span>{status === 'completed' ? 'Mission Finished' : 'Engage Mission'}</span>
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

        {/* Error notification banner */}
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

        {/* Dependency Validation Alert */}
        {plan && !plan.is_valid && (
          <div className="mt-4 p-4 rounded-xl bg-amber-950/70 border border-amber-600/50 text-amber-200 text-xs space-y-1.5">
            <div className="flex items-center space-x-2 font-bold text-amber-300">
              <AlertTriangle className="w-4 h-4" />
              <span>Dependency Validation Failed: Roadmap Execution Blocked</span>
            </div>
            <ul className="list-disc list-inside space-y-0.5 text-amber-200/90 font-mono text-[11px] pl-2">
              {plan.validation_errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Mission Telemetry Progress Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          <div className="p-3.5 rounded-xl bg-slate-900/70 border border-blue-900/30">
            <div className="text-[10px] font-mono uppercase text-slate-400">Total Objectives</div>
            <div className="text-xl font-bold text-white mt-0.5">{totalTasks}</div>
          </div>
          <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-900/30">
            <div className="text-[10px] font-mono uppercase text-emerald-400">Verified & Passed</div>
            <div className="text-xl font-bold text-emerald-300 mt-0.5">{completedCount}</div>
          </div>
          <div className="p-3.5 rounded-xl bg-red-950/30 border border-red-900/30">
            <div className="text-[10px] font-mono uppercase text-red-400">Failed / Errors</div>
            <div className="text-xl font-bold text-red-300 mt-0.5">{failedCount}</div>
          </div>
          <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-900/30">
            <div className="text-[10px] font-mono uppercase text-amber-400">Blocked By Prereq</div>
            <div className="text-xl font-bold text-amber-300 mt-0.5">{blockedCount}</div>
          </div>
        </div>

        {/* Global Progress Bar */}
        <div className="mt-6 space-y-2">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="text-slate-400">MISSION COMPLETION TRAJECTORY</span>
            <span className="text-blue-400 font-bold">{progressPercent}%</span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-slate-950 overflow-hidden border border-slate-800">
            <div 
              className="h-full bg-gradient-to-r from-blue-600 via-indigo-500 to-emerald-500 transition-all duration-500 rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Active Task Indicator */}
        {missionState?.current_task_title && (
          <div className="mt-6 p-4 rounded-xl bg-blue-950/40 border border-blue-700/50 flex items-center justify-between animate-pulse">
            <div className="flex items-center space-x-3">
              <div className="w-2.5 h-2.5 rounded-full bg-blue-400 animate-ping" />
              <div>
                <div className="text-[10px] font-mono text-blue-400 uppercase font-semibold">Active Objective In Progress</div>
                <div className="text-sm font-bold text-white">{missionState.current_task_title}</div>
              </div>
            </div>
            <div className="text-xs font-mono text-blue-300 uppercase tracking-widest bg-blue-900/50 px-2.5 py-1 rounded-md border border-blue-600/40">
              IMPLEMENTING & TESTING
            </div>
          </div>
        )}
      </div>

      {/* Task Roadmap & Dependency Sequence */}
      <div className="bg-[#0a0e17] border border-blue-900/30 rounded-2xl p-6 shadow-xl">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-blue-900/30">
          <div className="flex items-center space-x-2">
            <GitFork className="w-4 h-4 text-blue-400" />
            <h3 className="text-base font-bold text-white tracking-wide">
              Sequential Execution Pipeline (DAG Order)
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {plan?.execution_order.length || 0} scheduled tasks
          </span>
        </div>

        <div className="space-y-3">
          {plan?.tasks.map((t, idx) => {
            const isCompleted = missionState?.completed_task_ids.includes(t.task_id);
            const isFailed = missionState?.failed_task_ids.includes(t.task_id);
            const isBlocked = missionState?.blocked_task_ids.includes(t.task_id);
            const isCurrent = missionState?.current_task_id === t.task_id;
            const progress = missionState?.tasks_progress[t.task_id];

            return (
              <div 
                key={t.task_id}
                className={`p-4 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                  isCurrent
                    ? 'bg-blue-950/50 border-blue-500 shadow-md shadow-blue-950/50'
                    : isCompleted
                    ? 'bg-slate-900/60 border-emerald-900/40 text-slate-300'
                    : isFailed
                    ? 'bg-red-950/40 border-red-800/60 text-red-200'
                    : isBlocked
                    ? 'bg-slate-900/40 border-amber-900/30 opacity-75'
                    : 'bg-slate-900/40 border-slate-800/80 text-slate-400'
                }`}
              >
                <div className="flex items-start space-x-3.5">
                  <div className="mt-0.5 shrink-0">
                    {isCompleted ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    ) : isFailed ? (
                      <AlertTriangle className="w-5 h-5 text-red-400" />
                    ) : isCurrent ? (
                      <div className="w-5 h-5 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
                    ) : isBlocked ? (
                      <Pause className="w-5 h-5 text-amber-400" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border border-slate-700 flex items-center justify-center text-[10px] font-mono text-slate-500">
                        {idx + 1}
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-white">
                        {t.title}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                        {t.task_id}
                      </span>
                      {t.priority && (
                        <span className="text-[10px] font-mono uppercase text-indigo-300 bg-indigo-950/60 px-1.5 py-0.5 rounded border border-indigo-900/40">
                          {t.priority}
                        </span>
                      )}
                    </div>

                    {/* Dependencies info */}
                    <div className="flex flex-wrap items-center gap-2 mt-2 text-xs font-mono text-slate-400">
                      {t.depends_on && t.depends_on.length > 0 ? (
                        <>
                          <span className="text-slate-500">Prerequisites:</span>
                          {t.depends_on.map((dep) => (
                            <span 
                              key={dep} 
                              className={`px-1.5 py-0.5 rounded text-[10px] border ${
                                missionState?.completed_task_ids.includes(dep)
                                  ? 'bg-emerald-950/40 border-emerald-800/40 text-emerald-400'
                                  : 'bg-slate-800 border-slate-700 text-slate-400'
                              }`}
                            >
                              {dep}
                            </span>
                          ))}
                        </>
                      ) : (
                        <span className="text-slate-600 italic">No prerequisites (root task)</span>
                      )}
                    </div>

                    {/* Progress verification summary */}
                    {progress && (
                      <div className="mt-2 text-[11px] font-mono flex items-center space-x-3 text-slate-300">
                        {progress.tests_total > 0 && (
                          <span className="text-emerald-400">
                            Tests Passed: {progress.tests_passed}/{progress.tests_total}
                          </span>
                        )}
                        {progress.repair_attempts_count > 0 && (
                          <span className="text-amber-400">
                            Repairs: {progress.repair_attempts_count}/3
                          </span>
                        )}
                        {progress.snapshot_id && (
                          <span className="text-blue-400">
                            Snapshot: {progress.snapshot_id}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Right action button */}
                <div className="flex items-center space-x-2 shrink-0">
                  {onOpenTaskImplementation && (
                    <button
                      onClick={() => onOpenTaskImplementation(t.task_id)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs font-mono transition-colors border border-slate-700"
                    >
                      Inspect Code
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Report Modal */}
      {showReportModal && report && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#0a0e17] border border-blue-900/60 rounded-2xl max-w-2xl w-full p-6 sm:p-8 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-blue-900/40">
              <div className="flex items-center space-x-3">
                <Shield className="w-6 h-6 text-blue-400" />
                <h3 className="text-lg font-bold text-white tracking-wide">
                  Mission Execution Report
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
              <div className="text-xs font-mono uppercase text-blue-400 font-bold">Executive Summary</div>
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
                <div className="text-[10px] font-mono text-slate-400">Duration</div>
                <div className="text-lg font-bold text-white">{report.duration_seconds}s</div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs font-mono uppercase text-slate-400">Task Audit Trail</div>
              <div className="space-y-1.5 max-h-60 overflow-y-auto">
                {report.tasks.map((task) => (
                  <div key={task.task_id} className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs flex justify-between items-center">
                    <span className="font-semibold text-slate-200">{task.title}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold ${
                      task.verified ? 'bg-emerald-950 text-emerald-400' : 'bg-red-950 text-red-400'
                    }`}>
                      {task.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-800">
              <button
                onClick={() => setShowReportModal(false)}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors"
              >
                Close Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
