import React, { useState, useEffect, useRef } from 'react';
import {
  Rocket, Shield, ShieldCheck, ShieldAlert, RefreshCw, ChevronDown, ChevronUp,
  CheckCircle, XCircle, AlertTriangle, Clock, ExternalLink, RotateCcw,
  Terminal, Server, Package, Zap, Eye, Lock, Unlock
} from 'lucide-react';
import {
  Project,
  DeploymentPlatform,
  DeploymentPlan,
  DeploymentRecord,
  DeploymentState,
  DeploymentReadinessReport,
  ProjectStackDetection
} from '../types';
import {
  detectDeploymentStack,
  assessDeploymentReadiness,
  generateDeploymentPlan,
  approveDeploymentPlan,
  executeDeployment,
  getDeploymentStatus,
  rollbackDeployment,
  getDeploymentHistory
} from '../api/rogers';

// ─── Types ─────────────────────────────────────────────────────────────────

interface DeploymentPanelProps {
  project: Project;
  onRefreshProject: () => void;
}

type PanelView = 'overview' | 'plan' | 'monitor' | 'history';

const PLATFORM_META: Record<DeploymentPlatform, { label: string; icon: string; color: string; desc: string }> = {
  docker: { label: 'Docker', icon: '🐳', color: 'from-blue-600 to-cyan-600', desc: 'Self-hosted container. Runs anywhere Docker is available.' },
  local_container: { label: 'Local Container', icon: '📦', color: 'from-slate-600 to-blue-600', desc: 'Development container on localhost.' },
  render: { label: 'Render', icon: '⚡', color: 'from-purple-600 to-pink-600', desc: 'Full-stack cloud hosting with free tier and auto-deploy.' },
  vercel: { label: 'Vercel', icon: '▲', color: 'from-slate-700 to-slate-500', desc: 'Optimized for frontend SPAs and serverless functions.' },
  netlify: { label: 'Netlify', icon: '🌐', color: 'from-teal-600 to-green-600', desc: 'Global CDN for static and Jamstack deployments.' },
  railway: { label: 'Railway', icon: '🚂', color: 'from-violet-600 to-purple-600', desc: 'Full-stack app hosting with one-click GitHub deploys.' }
};

// ─── Helpers ────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { cls: string; label: string }> = {
    healthy: { cls: 'bg-emerald-900 text-emerald-300 border-emerald-700', label: 'HEALTHY' },
    pending: { cls: 'bg-slate-800 text-slate-400 border-slate-700', label: 'PENDING' },
    deploying: { cls: 'bg-blue-900 text-blue-300 border-blue-700 animate-pulse', label: 'DEPLOYING' },
    failed: { cls: 'bg-red-900 text-red-300 border-red-700', label: 'FAILED' },
    rolled_back: { cls: 'bg-amber-900 text-amber-300 border-amber-700', label: 'ROLLED BACK' },
    ready: { cls: 'bg-emerald-900 text-emerald-300 border-emerald-700', label: 'READY' },
    ready_with_warnings: { cls: 'bg-amber-900 text-amber-300 border-amber-700', label: 'READY (WARN)' },
    blocked: { cls: 'bg-red-900 text-red-300 border-red-700', label: 'BLOCKED' },
  };
  const s = map[status] ?? { cls: 'bg-slate-800 text-slate-400 border-slate-700', label: status.toUpperCase() };
  return <span className={`text-[10px] font-bold tracking-widest px-2 py-0.5 rounded border ${s.cls}`}>{s.label}</span>;
}

function ReadinessGauge({ score, status }: { score: number; status: string }) {
  const color = status === 'ready' ? 'stroke-emerald-400' : status === 'ready_with_warnings' ? 'stroke-amber-400' : 'stroke-red-400';
  const r = 36;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <div className="flex flex-col items-center">
      <svg width="90" height="90" viewBox="0 0 90 90">
        <circle cx="45" cy="45" r={r} fill="none" stroke="#1e293b" strokeWidth="8" />
        <circle cx="45" cy="45" r={r} fill="none" className={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`} strokeDashoffset={circ / 4}
          style={{ transition: 'stroke-dasharray 0.6s ease' }} />
        <text x="45" y="49" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">{score}</text>
      </svg>
      <span className="text-xs text-slate-400 mt-1 uppercase tracking-wide">Readiness</span>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function DeploymentPanel({ project, onRefreshProject }: DeploymentPanelProps) {
  const [view, setView] = useState<PanelView>('overview');
  const [state, setState] = useState<DeploymentState | null>(null);
  const [stack, setStack] = useState<ProjectStackDetection | null>(null);
  const [readiness, setReadiness] = useState<DeploymentReadinessReport | null>(null);
  const [plan, setPlan] = useState<DeploymentPlan | null>(null);
  const [history, setHistory] = useState<DeploymentRecord[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<DeploymentPlatform>('docker');
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approverName, setApproverName] = useState('Commander');
  const [expandedConfig, setExpandedConfig] = useState<string | null>(null);
  const [expandedLogs, setExpandedLogs] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadStatus();
  }, [project.id]);

  useEffect(() => {
    if (expandedLogs && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [state?.active_deployment?.logs, expandedLogs]);

  async function loadStatus() {
    setLoading(true);
    setError(null);
    try {
      const s = await getDeploymentStatus(project.id);
      setState(s);
      setStack(s.stack ?? null);
      setReadiness(s.readiness ?? null);
      setPlan(s.current_plan ?? null);
      const h = await getDeploymentHistory(project.id);
      setHistory(h);
    } catch (e: any) {
      setError(e.message || 'Failed to load deployment state');
    } finally {
      setLoading(false);
    }
  }

  async function handleDetectStack() {
    setActionLoading('detect');
    setError(null);
    try {
      const s = await detectDeploymentStack(project.id);
      setStack(s);
    } catch (e: any) { setError(e.message); }
    finally { setActionLoading(null); }
  }

  async function handleAssessReadiness() {
    setActionLoading('readiness');
    setError(null);
    try {
      const r = await assessDeploymentReadiness(project.id);
      setReadiness(r);
    } catch (e: any) { setError(e.message); }
    finally { setActionLoading(null); }
  }

  async function handleGeneratePlan() {
    setActionLoading('plan');
    setError(null);
    try {
      const p = await generateDeploymentPlan(project.id, selectedPlatform);
      setPlan(p);
      setView('plan');
    } catch (e: any) { setError(e.message); }
    finally { setActionLoading(null); }
  }

  async function handleApprovePlan() {
    if (!plan) return;
    setActionLoading('approve');
    setError(null);
    try {
      const approved = await approveDeploymentPlan(project.id, approverName);
      setPlan(approved);
    } catch (e: any) { setError(e.message); }
    finally { setActionLoading(null); }
  }

  async function handleDeploy() {
    setActionLoading('deploy');
    setError(null);
    try {
      const record = await executeDeployment(project.id, false);
      const s = await getDeploymentStatus(project.id);
      setState(s);
      setHistory([record, ...history]);
      setView('monitor');
    } catch (e: any) { setError(e.message); }
    finally { setActionLoading(null); }
  }

  async function handleRollback(deploymentId?: string) {
    setActionLoading('rollback_' + (deploymentId || 'latest'));
    setError(null);
    try {
      const record = await rollbackDeployment(project.id, deploymentId);
      const h = await getDeploymentHistory(project.id);
      setHistory(h);
      const s = await getDeploymentStatus(project.id);
      setState(s);
      setView('monitor');
    } catch (e: any) { setError(e.message); }
    finally { setActionLoading(null); }
  }

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center shadow-lg">
            <Rocket className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-wide">Deployment Command Center</h2>
            <p className="text-xs text-slate-400">Intelligent Deployment Automation · Slice 9</p>
          </div>
        </div>
        <button
          onClick={loadStatus}
          disabled={loading}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-950 border border-red-700 text-red-300 text-xs flex items-center space-x-2">
          <XCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Sub-nav */}
      <div className="flex items-center space-x-1.5 border-b border-slate-800 pb-3">
        {(['overview', 'plan', 'monitor', 'history'] as PanelView[]).map(v => (
          <button key={v} onClick={() => setView(v)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${view === v ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}>
            {v === 'overview' ? '🔍 Overview' : v === 'plan' ? '📋 Mission Plan' : v === 'monitor' ? '📡 Live Monitor' : '📜 History'}
          </button>
        ))}
      </div>

      {/* ── Overview Tab ── */}
      {view === 'overview' && (
        <div className="space-y-5">
          {/* Stack Detection + Readiness side by side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Stack Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Server className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm font-semibold text-white">Stack Detection</span>
                </div>
                <button onClick={handleDetectStack} disabled={actionLoading === 'detect'}
                  className="text-xs px-2 py-1 rounded-lg bg-cyan-900 hover:bg-cyan-800 text-cyan-300 transition-all">
                  {actionLoading === 'detect' ? 'Scanning...' : 'Scan'}
                </button>
              </div>
              {stack ? (
                <div className="space-y-2 text-xs">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-slate-800 rounded-lg p-2">
                      <span className="text-slate-400 block">Language</span>
                      <span className="text-white font-semibold capitalize">{stack.language}</span>
                    </div>
                    <div className="bg-slate-800 rounded-lg p-2">
                      <span className="text-slate-400 block">Framework</span>
                      <span className="text-white font-semibold capitalize">{stack.framework}</span>
                    </div>
                    <div className="bg-slate-800 rounded-lg p-2">
                      <span className="text-slate-400 block">Port</span>
                      <span className="text-cyan-300 font-semibold">{stack.default_port}</span>
                    </div>
                    <div className="bg-slate-800 rounded-lg p-2">
                      <span className="text-slate-400 block">Package Mgr</span>
                      <span className="text-white font-semibold">{stack.package_manager}</span>
                    </div>
                  </div>
                  {stack.build_command && (
                    <div className="bg-slate-800 rounded-lg p-2">
                      <span className="text-slate-400 block mb-1">Build Command</span>
                      <code className="text-green-300 text-[10px] font-mono">{stack.build_command}</code>
                    </div>
                  )}
                  {stack.start_command && (
                    <div className="bg-slate-800 rounded-lg p-2">
                      <span className="text-slate-400 block mb-1">Start Command</span>
                      <code className="text-blue-300 text-[10px] font-mono">{stack.start_command}</code>
                    </div>
                  )}
                  {stack.detected_configs.length > 0 && (
                    <div className="text-slate-400">
                      Found: {stack.detected_configs.map(c => <code key={c} className="text-xs text-slate-300 bg-slate-800 px-1 rounded mr-1">{c}</code>)}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">Run scan to detect project stack.</p>
              )}
            </div>

            {/* Readiness Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm font-semibold text-white">Readiness Check</span>
                </div>
                <button onClick={handleAssessReadiness} disabled={actionLoading === 'readiness'}
                  className="text-xs px-2 py-1 rounded-lg bg-emerald-900 hover:bg-emerald-800 text-emerald-300 transition-all">
                  {actionLoading === 'readiness' ? 'Evaluating...' : 'Evaluate'}
                </button>
              </div>
              {readiness ? (
                <div className="space-y-2">
                  <div className="flex items-center space-x-4">
                    <ReadinessGauge score={readiness.score} status={readiness.overall_status} />
                    <div className="space-y-1 flex-1">
                      <StatusBadge status={readiness.overall_status} />
                      {readiness.blockers.length > 0 && (
                        <div className="mt-2">
                          {readiness.blockers.map((b, i) => (
                            <div key={i} className="text-[10px] text-red-300 flex items-start space-x-1 mt-1">
                              <XCircle className="w-3 h-3 mt-0.5 shrink-0 text-red-500" />
                              <span>{b}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="space-y-1">
                    {readiness.checks.map(c => (
                      <div key={c.id} className="flex items-center justify-between text-xs py-1 border-b border-slate-800">
                        <span className="text-slate-300">{c.title}</span>
                        {c.status === 'pass' ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                          : c.status === 'warning' ? <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                          : <XCircle className="w-3.5 h-3.5 text-red-400" />}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">Run evaluation to check deployment readiness.</p>
              )}
            </div>
          </div>

          {/* Platform Selector */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center space-x-2">
              <Package className="w-4 h-4 text-blue-400" />
              <span className="text-sm font-semibold text-white">Target Platform</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {(Object.entries(PLATFORM_META) as [DeploymentPlatform, typeof PLATFORM_META[DeploymentPlatform]][]).map(([key, meta]) => (
                <button key={key} onClick={() => setSelectedPlatform(key)}
                  className={`p-3 rounded-xl border text-left transition-all ${selectedPlatform === key
                    ? 'border-blue-500 bg-gradient-to-br ' + meta.color + ' bg-opacity-20'
                    : 'border-slate-700 bg-slate-800 hover:border-slate-600'}`}>
                  <div className="text-lg mb-1">{meta.icon}</div>
                  <div className="text-xs font-bold text-white">{meta.label}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5 leading-tight">{meta.desc}</div>
                </button>
              ))}
            </div>
            <button
              onClick={handleGeneratePlan}
              disabled={actionLoading === 'plan'}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-sm font-semibold transition-all shadow-lg disabled:opacity-50"
            >
              {actionLoading === 'plan' ? '⚙️ Generating Plan...' : `📋 Generate ${PLATFORM_META[selectedPlatform].label} Deployment Plan`}
            </button>
          </div>
        </div>
      )}

      {/* ── Plan Tab ── */}
      {view === 'plan' && (
        <div className="space-y-4">
          {!plan ? (
            <div className="text-center py-12 text-slate-500">
              <Package className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No deployment plan generated yet.</p>
              <button onClick={() => setView('overview')} className="mt-3 text-xs text-blue-400 hover:text-blue-300">← Go to Overview</button>
            </div>
          ) : (
            <>
              {/* Plan Summary */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-2xl">{PLATFORM_META[plan.platform]?.icon}</span>
                      <div>
                        <span className="text-sm font-bold text-white">{PLATFORM_META[plan.platform]?.label} Deployment Plan</span>
                        <span className="ml-2 text-xs text-slate-500">#{plan.plan_id}</span>
                      </div>
                    </div>
                    <div className="mt-1 flex items-center space-x-2">
                      <StatusBadge status={plan.is_approved ? 'ready' : 'pending'} />
                      {plan.is_approved && <span className="text-xs text-emerald-400">✓ Approved by {plan.approved_by}</span>}
                    </div>
                  </div>
                  <div className="text-right text-xs text-slate-400">
                    <div>Port: <span className="text-white">{plan.target_port}</span></div>
                    <div>Health: <code className="text-cyan-300">{plan.health_check_path}</code></div>
                  </div>
                </div>

                {/* Build & Start commands */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {plan.build_command && (
                    <div className="bg-slate-800 rounded-lg p-2">
                      <span className="text-slate-400 text-xs block mb-1">Build Command</span>
                      <code className="text-green-300 text-[11px] font-mono">{plan.build_command}</code>
                    </div>
                  )}
                  {plan.start_command && (
                    <div className="bg-slate-800 rounded-lg p-2">
                      <span className="text-slate-400 text-xs block mb-1">Start Command</span>
                      <code className="text-blue-300 text-[11px] font-mono">{plan.start_command}</code>
                    </div>
                  )}
                </div>

                {/* Steps */}
                <div>
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Mission Steps</span>
                  <ol className="mt-2 space-y-1">
                    {plan.steps.map((step, i) => (
                      <li key={i} className="flex items-start space-x-2 text-xs text-slate-300">
                        <span className="text-blue-400 font-bold shrink-0">{i + 1}.</span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>

                {/* Risks */}
                {plan.risks.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-amber-400 uppercase tracking-wide">⚠ Risk Advisories</span>
                    <ul className="mt-2 space-y-1">
                      {plan.risks.map((r, i) => (
                        <li key={i} className="flex items-start space-x-2 text-xs text-amber-300">
                          <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Generated Config Files */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Generated Configuration Files</span>
                {plan.generated_configs.map(cfg => (
                  <div key={cfg.filename} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                    <button
                      onClick={() => setExpandedConfig(expandedConfig === cfg.filename ? null : cfg.filename)}
                      className="w-full flex items-center justify-between p-3 hover:bg-slate-800 transition-all"
                    >
                      <div className="flex items-center space-x-2">
                        <Terminal className="w-4 h-4 text-slate-400" />
                        <code className="text-sm font-mono text-cyan-300">{cfg.filename}</code>
                        <span className="text-xs text-slate-500">({cfg.file_type})</span>
                      </div>
                      {expandedConfig === cfg.filename ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </button>
                    {expandedConfig === cfg.filename && (
                      <pre className="p-4 text-[11px] font-mono text-slate-300 bg-slate-950 border-t border-slate-800 overflow-x-auto leading-relaxed max-h-72 overflow-y-auto">
                        {cfg.content}
                      </pre>
                    )}
                  </div>
                ))}
              </div>

              {/* Human Approval Gate */}
              {!plan.is_approved && (
                <div className="bg-gradient-to-br from-amber-950 to-orange-950 border border-amber-700 rounded-xl p-4 space-y-3">
                  <div className="flex items-center space-x-2">
                    <Lock className="w-5 h-5 text-amber-400" />
                    <span className="text-sm font-bold text-amber-300">Mandatory Human Approval Required</span>
                  </div>
                  <p className="text-xs text-amber-200">
                    This deployment cannot execute until an authorized commander explicitly approves this mission plan. Review all generated configs and confirm all steps above.
                  </p>
                  <div className="flex items-center space-x-2">
                    <input
                      value={approverName}
                      onChange={e => setApproverName(e.target.value)}
                      placeholder="Approver name..."
                      className="flex-1 px-3 py-2 rounded-lg bg-amber-900/50 border border-amber-700 text-amber-100 text-xs placeholder-amber-700 focus:outline-none focus:border-amber-500"
                    />
                    <button
                      onClick={handleApprovePlan}
                      disabled={actionLoading === 'approve' || !approverName.trim()}
                      className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-all disabled:opacity-50 flex items-center space-x-1"
                    >
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>{actionLoading === 'approve' ? 'Approving...' : 'Authorize'}</span>
                    </button>
                  </div>
                </div>
              )}

              {plan.is_approved && (
                <div className="bg-gradient-to-br from-blue-950 to-cyan-950 border border-blue-700 rounded-xl p-4 space-y-3">
                  <div className="flex items-center space-x-2">
                    <Unlock className="w-5 h-5 text-blue-400" />
                    <span className="text-sm font-bold text-blue-300">Plan Authorized — Ready to Launch</span>
                  </div>
                  <p className="text-xs text-blue-200">
                    Approved by <strong>{plan.approved_by}</strong> at {plan.approved_at ? new Date(plan.approved_at).toLocaleString() : '—'}.
                    Pre-deployment snapshots will be captured automatically.
                  </p>
                  <button
                    onClick={handleDeploy}
                    disabled={actionLoading === 'deploy'}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-sm font-bold transition-all shadow-lg disabled:opacity-50 flex items-center justify-center space-x-2"
                  >
                    <Rocket className="w-4 h-4" />
                    <span>{actionLoading === 'deploy' ? '🚀 Deploying...' : '🚀 Execute Deployment'}</span>
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Live Monitor Tab ── */}
      {view === 'monitor' && (
        <div className="space-y-4">
          {!state?.active_deployment ? (
            <div className="text-center py-12 text-slate-500">
              <Server className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No active deployment yet.</p>
            </div>
          ) : (
            <>
              {/* Status Hero */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <StatusBadge status={state.active_deployment.status} />
                      <span className="text-xs text-slate-400">{PLATFORM_META[state.active_deployment.platform]?.icon} {PLATFORM_META[state.active_deployment.platform]?.label}</span>
                    </div>
                    {state.active_deployment.deployment_url && (
                      <a href={state.active_deployment.deployment_url} target="_blank" rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center space-x-1.5 text-sm text-cyan-400 hover:text-cyan-300 font-mono">
                        <ExternalLink className="w-3.5 h-3.5" />
                        <span>{state.active_deployment.deployment_url}</span>
                      </a>
                    )}
                  </div>
                  <div className="text-right text-xs text-slate-400 space-y-1">
                    <div>Health: <span className={state.active_deployment.health_status === 'passing' ? 'text-emerald-400' : 'text-red-400'}>{state.active_deployment.health_status}</span></div>
                    <div>Duration: <span className="text-white">{state.active_deployment.duration_seconds.toFixed(1)}s</span></div>
                    <div>ID: <code className="text-slate-300 text-[10px]">{state.active_deployment.deployment_id}</code></div>
                  </div>
                </div>

                {state.active_deployment.health_message && (
                  <div className="bg-emerald-950 border border-emerald-800 rounded-lg p-2 text-xs text-emerald-300 flex items-center space-x-2">
                    <CheckCircle className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                    <span>{state.active_deployment.health_message}</span>
                  </div>
                )}
              </div>

              {/* Deployment Logs */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedLogs(!expandedLogs)}
                  className="w-full flex items-center justify-between p-3 hover:bg-slate-800 transition-all"
                >
                  <div className="flex items-center space-x-2">
                    <Terminal className="w-4 h-4 text-green-400" />
                    <span className="text-xs font-semibold text-white">Deployment Logs ({state.active_deployment.logs.length} lines)</span>
                  </div>
                  {expandedLogs ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </button>
                {expandedLogs && (
                  <div className="bg-slate-950 border-t border-slate-800 p-4 max-h-80 overflow-y-auto font-mono text-[11px] leading-6 space-y-0.5">
                    {state.active_deployment.logs.map((log, i) => (
                      <div key={i} className={`${
                        log.includes('[ERROR]') ? 'text-red-400' :
                        log.includes('[SUCCESS]') ? 'text-emerald-400' :
                        log.includes('[HEALTH]') ? 'text-cyan-400' :
                        log.includes('[APPROVAL]') ? 'text-amber-400' :
                        log.includes('[SNAPSHOT]') ? 'text-purple-400' :
                        'text-slate-300'
                      }`}>{log}</div>
                    ))}
                    <div ref={logsEndRef} />
                  </div>
                )}
              </div>

              {/* Rollback button */}
              {state.active_deployment.snapshot_id && state.active_deployment.status !== 'rolled_back' && (
                <button
                  onClick={() => handleRollback(state.active_deployment?.deployment_id)}
                  disabled={!!actionLoading}
                  className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-amber-900/40 hover:bg-amber-900/60 border border-amber-700 text-amber-300 text-xs font-semibold transition-all"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Rollback to Pre-Deployment Snapshot</span>
                </button>
              )}
            </>
          )}
        </div>
      )}

      {/* ── History Tab ── */}
      {view === 'history' && (
        <div className="space-y-3">
          {history.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <Clock className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No deployment history yet.</p>
            </div>
          ) : (
            history.map(rec => (
              <div key={rec.deployment_id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{PLATFORM_META[rec.platform]?.icon}</span>
                    <div>
                      <div className="flex items-center space-x-2">
                        <StatusBadge status={rec.status} />
                        <span className="text-xs text-slate-400">{PLATFORM_META[rec.platform]?.label}</span>
                      </div>
                      <code className="text-[10px] text-slate-500">{rec.deployment_id}</code>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {rec.deployment_url && (
                      <a href={rec.deployment_url} target="_blank" rel="noopener noreferrer"
                        className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center space-x-1">
                        <ExternalLink className="w-3 h-3" />
                        <span>Open</span>
                      </a>
                    )}
                    {rec.snapshot_id && rec.status !== 'rolled_back' && (
                      <button
                        onClick={() => handleRollback(rec.deployment_id)}
                        disabled={!!actionLoading}
                        className="text-xs px-2 py-1 rounded-lg bg-amber-900/40 hover:bg-amber-900/60 border border-amber-800 text-amber-300 flex items-center space-x-1 transition-all"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>Rollback</span>
                      </button>
                    )}
                  </div>
                </div>
                <div className="text-xs text-slate-400 flex space-x-4">
                  <span>Health: <span className={rec.health_status === 'passing' ? 'text-emerald-400' : 'text-slate-300'}>{rec.health_status}</span></span>
                  <span>Duration: {rec.duration_seconds.toFixed(1)}s</span>
                  <span>At: {new Date(rec.created_at).toLocaleString()}</span>
                </div>
                {rec.error_message && (
                  <div className="text-xs text-red-300 bg-red-950 border border-red-800 rounded p-2">{rec.error_message}</div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
