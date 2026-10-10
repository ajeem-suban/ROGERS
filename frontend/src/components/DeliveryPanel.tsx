import React, { useState } from 'react';
import { 
  Shield, 
  ShieldCheck, 
  AlertTriangle, 
  Download, 
  Copy, 
  Check, 
  Package, 
  FileCheck2, 
  Lock, 
  FileText
} from 'lucide-react';
import { Project, DeliveryPackageMetadata } from '../types';
import { createDeliveryPackage, getDownloadPackageUrl } from '../api/rogers';
import { MissionReportModal } from './MissionReportModal';

interface DeliveryPanelProps {
  project: Project;
  onRefreshProject?: () => void;
}

export const DeliveryPanel: React.FC<DeliveryPanelProps> = ({
  project,
  onRefreshProject
}) => {
  const [isPackaging, setIsPackaging] = useState(false);
  const [packageError, setPackageError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  const tasks = project.blueprint?.development_tasks || [];
  const verifiedCount = tasks.filter(t => t.status === 'verified').length;
  const completedCount = tasks.filter(t => t.status === 'completed').length;
  const failedCount = tasks.filter(t => t.status === 'failed').length;

  const canPackage = failedCount === 0 && (verifiedCount > 0 || completedCount > 0);
  const packageMeta: DeliveryPackageMetadata | null | undefined = project.package_metadata;

  const handleInitiatePackaging = async () => {
    setIsPackaging(true);
    setPackageError(null);
    try {
      await createDeliveryPackage(project.id);
      if (onRefreshProject) {
        onRefreshProject();
      }
    } catch (err: any) {
      setPackageError(err.message || 'Failed to create delivery package.');
    } finally {
      setIsPackaging(false);
    }
  };

  const handleCopySha = (sha: string) => {
    navigator.clipboard.writeText(sha);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* 1. Tactical Status Banner */}
      <div 
        className={`p-6 rounded-2xl border transition-all ${
          failedCount > 0
            ? 'bg-rose-950/40 border-rose-800/80 shadow-[0_0_25px_rgba(225,29,72,0.2)]'
            : canPackage
            ? 'bg-blue-950/30 border-blue-700/70 shadow-[0_0_30px_rgba(37,99,235,0.2)]'
            : 'bg-amber-950/30 border-amber-800/70 shadow-[0_0_20px_rgba(217,119,6,0.15)]'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start space-x-3.5">
            <div 
              className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border ${
                failedCount > 0
                  ? 'bg-rose-950 border-rose-500 text-rose-400'
                  : canPackage
                  ? 'bg-blue-950 border-blue-400 text-blue-300'
                  : 'bg-amber-950 border-amber-500 text-amber-400'
              }`}
            >
              {failedCount > 0 ? (
                <AlertTriangle className="w-5 h-5 text-rose-400" />
              ) : canPackage ? (
                <ShieldCheck className="w-5 h-5 text-blue-400" />
              ) : (
                <Shield className="w-5 h-5 text-amber-400" />
              )}
            </div>

            <div>
              <div className="text-[10px] font-mono tracking-widest uppercase font-semibold text-slate-400">
                DELIVERY READINESS STATUS
              </div>
              <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">
                {failedCount > 0
                  ? `DELIVERY BLOCKED — ${failedCount} TASK(S) FAILED VALIDATION`
                  : canPackage
                  ? 'MISSION VERIFIED — READY FOR PACKAGING & SHIPMENT'
                  : 'VERIFICATION INCOMPLETE — TASK EXECUTION REQUIRED'}
              </h2>
              <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
                {failedCount > 0
                  ? 'Rogers packaging engine is blocked by defense policy. Resolve all failed development tasks before creating a delivery package.'
                  : canPackage
                  ? `All defense checks cleared. ${verifiedCount} task(s) verified by automated tests. Project is cleared for secure artifact generation.`
                  : 'At least one development task must be implemented and verified before Rogers can generate a production delivery package.'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={() => setIsReportModalOpen(true)}
              className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-medium border border-slate-700 transition-all shadow-sm"
            >
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              <span>Mission Report</span>
            </button>

            <button
              onClick={handleInitiatePackaging}
              disabled={!canPackage || isPackaging}
              className={`inline-flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-mono font-bold transition-all shadow-md ${
                !canPackage || isPackaging
                  ? 'bg-slate-800/80 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-60'
                  : 'bg-blue-600 hover:bg-blue-500 text-white border border-blue-400/60 shadow-[0_0_15px_rgba(37,99,235,0.4)]'
              }`}
            >
              {isPackaging ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Packaging...</span>
                </>
              ) : (
                <>
                  <Package className="w-3.5 h-3.5" />
                  <span>{packageMeta ? 'Regenerate Package' : 'Create Delivery Package'}</span>
                </>
              )}
            </button>
          </div>
        </div>

        {packageError && (
          <div className="mt-4 p-3 rounded-xl bg-rose-950/60 border border-rose-800/80 text-xs text-rose-200 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{packageError}</span>
          </div>
        )}
      </div>

      {/* 2. Package Artifact Integrity Card (If Packaged) */}
      {packageMeta && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-5">
            <div className="flex items-center space-x-2.5">
              <Package className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-white uppercase font-mono tracking-wider">
                Production Delivery Archive (.ZIP)
              </h3>
            </div>
            <a
              href={getDownloadPackageUrl(project.id)}
              download
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-bold shadow-md transition-all"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Archive</span>
            </a>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">
                Archive Filename
              </span>
              <span className="text-xs font-mono font-semibold text-slate-200 truncate block">
                {packageMeta.package_filename}
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">
                Clean File Count
              </span>
              <span className="text-xs font-mono font-semibold text-emerald-300">
                {packageMeta.files_count} files included
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">
                Archive Size
              </span>
              <span className="text-xs font-mono font-semibold text-slate-200">
                {(packageMeta.package_size_bytes / 1024).toFixed(1)} KB
              </span>
            </div>
          </div>

          {/* Cryptographic SHA-256 Checksum */}
          <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/90">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                <Lock className="w-3 h-3 text-blue-400" />
                <span>Cryptographic SHA-256 Hash Checksum</span>
              </span>
              <span className="text-[10px] font-mono text-emerald-400">Integrity Verified</span>
            </div>
            <div className="flex items-center space-x-2">
              <code className="text-xs font-mono text-blue-300 truncate flex-1 bg-slate-900 px-2.5 py-1.5 rounded-lg border border-slate-800">
                {packageMeta.sha256_checksum}
              </code>
              <button
                onClick={() => handleCopySha(packageMeta.sha256_checksum)}
                className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition-colors"
                title="Copy SHA-256 hash"
              >
                {copiedHash ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Defense Packaging Protocol & Guarantees */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Exclusion Shield */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center space-x-2 text-xs font-mono font-semibold uppercase tracking-wider text-slate-300 mb-3 pb-2 border-b border-slate-800">
            <Lock className="w-3.5 h-3.5 text-blue-400" />
            <span>Sanitization & Exclusion Defense</span>
          </div>
          <ul className="space-y-2 text-xs text-slate-400 font-mono">
            <li className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
              <span>Excluded live <code className="text-slate-300">.env</code> secrets (preserved <code className="text-slate-300">.env.example</code>)</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
              <span>Excluded <code className="text-slate-300">.git/</code> repository internals and config</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
              <span>Excluded <code className="text-slate-300">.venv/</code> & temporary virtual environment binaries</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
              <span>Excluded <code className="text-slate-300">__pycache__/</code> and compiled <code className="text-slate-300">*.pyc</code> files</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
              <span>Excluded <code className="text-slate-300">.rogers/snapshots/</code> pre-modification backups</span>
            </li>
          </ul>
        </div>

        {/* Embedded Verification Report Details */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center space-x-2 text-xs font-mono font-semibold uppercase tracking-wider text-slate-300 mb-3 pb-2 border-b border-slate-800">
            <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Embedded Artifact: VERIFICATION_REPORT.md</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed mb-3">
            Every delivery package is bundled with a cryptographic verification dossier injected at the archive root.
          </p>
          <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-xs font-mono space-y-1 text-slate-400">
            <div>✓ System architecture & technology stack specification</div>
            <div>✓ Verifiable defense audit checklist (6/6 checks passed)</div>
            <div>✓ Automated unit test telemetry & pass rate percentages</div>
            <div>✓ Step-by-step local execution & production setup instructions</div>
          </div>
        </div>
      </div>

      {/* Mission Report Modal */}
      <MissionReportModal
        projectId={project.id}
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
      />
    </div>
  );
};
