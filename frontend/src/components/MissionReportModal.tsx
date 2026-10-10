import React, { useState, useEffect } from 'react';
import { 
  X, 
  Shield, 
  ShieldCheck, 
  CheckCircle2, 
  Download, 
  Copy, 
  Check, 
  Terminal, 
  FileCode, 
  Layers, 
  Lock, 
  FileText,
  AlertTriangle
} from 'lucide-react';
import { MissionReport } from '../types';
import { getMissionReport, getDownloadPackageUrl } from '../api/rogers';

interface MissionReportModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
}

export const MissionReportModal: React.FC<MissionReportModalProps> = ({
  projectId,
  isOpen,
  onClose
}) => {
  const [report, setReport] = useState<MissionReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadReport();
    }
  }, [isOpen, projectId]);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMissionReport(projectId);
      setReport(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load mission report');
    } finally {
      setLoading(false);
    }
  };

  const handleCopySha = (sha: string) => {
    navigator.clipboard.writeText(sha);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/80 backdrop-blur-md overflow-y-auto animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-4xl my-auto rounded-2xl border border-slate-700/80 bg-[#0a0e17] shadow-2xl overflow-hidden text-slate-100 font-sans"
        style={{
          boxShadow: '0 0 50px -12px rgba(30, 58, 138, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1)'
        }}
      >
        {/* Top Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full border border-blue-400/60 bg-blue-950/60 flex items-center justify-center shadow-inner">
              <Shield className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-mono tracking-widest uppercase font-semibold text-blue-400">
                  MISSION REPORT // STRATEGIC DOSSIER
                </span>
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              </div>
              <h2 className="text-base font-bold text-white tracking-tight">
                {report ? report.project_name : 'Loading Mission Telemetry...'}
              </h2>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {report?.package_metadata && (
              <a
                href={getDownloadPackageUrl(projectId)}
                download
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm transition-colors font-mono"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Archive</span>
              </a>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 max-h-[80vh] overflow-y-auto space-y-6">
          {loading && (
            <div className="py-20 text-center space-y-4">
              <div className="inline-block animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
              <p className="text-sm font-mono text-slate-400">Synthesizing mission verification report...</p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs flex items-center space-x-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {report && !loading && (
            <>
              {/* Executive Mission Banner */}
              <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 relative overflow-hidden">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                      MISSION IDENTIFIER
                    </span>
                    <div className="text-xs font-mono font-bold text-blue-300">
                      {report.project_id}
                    </div>
                    <div className="text-xs text-slate-400 mt-1 font-mono">
                      Timestamp: {new Date(report.generated_at).toLocaleString()}
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <div className="text-right">
                      <div className="text-[10px] font-mono text-slate-400 uppercase">
                        VERIFICATION STATUS
                      </div>
                      <div className="text-sm font-mono font-bold text-emerald-400 uppercase flex items-center justify-end space-x-1.5">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        <span>{report.verification_summary.status}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Grid 1: Stage Execution & Quality Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Pipeline Progression */}
                <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80">
                  <div className="flex items-center space-x-2 text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-3 pb-2 border-b border-slate-800">
                    <Layers className="w-3.5 h-3.5 text-blue-400" />
                    <span>Pipeline Progression Matrix</span>
                  </div>
                  <div className="space-y-2">
                    {Object.entries(report.stages_summary).map(([key, stg]) => (
                      <div key={key} className="flex items-center justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/60 text-xs">
                        <span className="font-medium text-slate-300">{stg.label}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">
                          {stg.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Automated Test Telemetry */}
                <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80">
                  <div className="flex items-center space-x-2 text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-3 pb-2 border-b border-slate-800">
                    <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Automated Test Suite Telemetry</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-center">
                      <div className="text-[10px] font-mono text-slate-400 uppercase">Tests Passed</div>
                      <div className="text-xl font-bold font-mono text-emerald-400">
                        {report.verification_summary.tests_passed} / {report.verification_summary.tests_discovered}
                      </div>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-center">
                      <div className="text-[10px] font-mono text-slate-400 uppercase">Pass Rate</div>
                      <div className="text-xl font-bold font-mono text-blue-400">
                        {report.verification_summary.pass_rate_percent.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-slate-400 font-mono space-y-1">
                    <div>• Verified Tasks: <span className="text-slate-200 font-bold">{report.verification_summary.verified_tasks}</span></div>
                    <div>• Failed Tasks: <span className="text-slate-200 font-bold">{report.verification_summary.failed_tasks}</span></div>
                    <div>• Pending Tasks: <span className="text-slate-200 font-bold">{report.verification_summary.pending_tasks}</span></div>
                  </div>
                </div>
              </div>

              {/* Grid 2: Defense Architecture & Package Integrity */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Security Guarantees */}
                <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80">
                  <div className="flex items-center space-x-2 text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-3 pb-2 border-b border-slate-800">
                    <Lock className="w-3.5 h-3.5 text-blue-400" />
                    <span>Verifiable Defense Checklist</span>
                  </div>
                  <div className="space-y-1.5 text-xs font-mono">
                    {Object.keys(report.security_audit).map((chk) => (
                      <div key={chk} className="flex items-center justify-between p-1.5 rounded bg-slate-950/40">
                        <span className="text-slate-300">{chk.replace(/_/g, ' ')}</span>
                        <span className="text-emerald-400 flex items-center space-x-1 text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>PASSED</span>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Package Integrity Hash */}
                <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80">
                  <div className="flex items-center space-x-2 text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-3 pb-2 border-b border-slate-800">
                    <FileCode className="w-3.5 h-3.5 text-amber-400" />
                    <span>Artifact Delivery Integrity</span>
                  </div>
                  {report.package_metadata ? (
                    <div className="space-y-2.5 text-xs font-mono">
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Package Archive</div>
                        <div className="text-slate-200 font-semibold">{report.package_metadata.package_filename}</div>
                      </div>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Archive Size</div>
                          <div className="text-slate-300">{(report.package_metadata.package_size_bytes / 1024).toFixed(1)} KB</div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Files Count</div>
                          <div className="text-slate-300">{report.package_metadata.files_count} files</div>
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase mb-0.5">SHA-256 Checksum</div>
                        <div className="flex items-center space-x-2 p-1.5 rounded bg-slate-950 border border-slate-800">
                          <code className="text-[10px] text-blue-300 truncate flex-1">
                            {report.package_metadata.sha256_checksum}
                          </code>
                          <button
                            onClick={() => handleCopySha(report.package_metadata!.sha256_checksum)}
                            className="p-1 rounded text-slate-400 hover:text-white transition-colors"
                            title="Copy SHA-256"
                          >
                            {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="py-6 text-center text-xs font-mono text-slate-500">
                      No delivery package generated yet.
                    </div>
                  )}
                </div>
              </div>

              {/* Recommended Next Steps */}
              <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80">
                <div className="flex items-center space-x-2 text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-3 pb-2 border-b border-slate-800">
                  <FileText className="w-3.5 h-3.5 text-blue-400" />
                  <span>Deployment Protocol & Recommended Next Steps</span>
                </div>
                <ul className="space-y-2">
                  {report.recommended_next_steps.map((step, idx) => (
                    <li key={idx} className="flex items-start space-x-2.5 text-xs text-slate-300">
                      <span className="w-4 h-4 rounded-full bg-blue-950 border border-blue-500/60 text-blue-300 flex items-center justify-center font-mono text-[10px] shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Captain America Motto Footer */}
              <div className="pt-2 pb-1 text-center border-t border-slate-800/80">
                <span className="text-[11px] font-mono tracking-widest text-slate-500 uppercase">
                  ROGERS MISSION CONTROL • "{report.tagline}"
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
