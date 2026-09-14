import React, { useState } from 'react';
import { 
  FolderPlus, 
  FileCode, 
  Check, 
  Copy, 
  Loader2, 
  Terminal,
  FileText
} from 'lucide-react';
import { ScaffoldResponse } from '../types';
import { scaffoldProject } from '../api/rogers';

interface ScaffoldPanelProps {
  projectId: string;
  projectName?: string;
}

export const ScaffoldPanel: React.FC<ScaffoldPanelProps> = ({ projectId }) => {
  const [loading, setLoading] = useState(false);
  const [scaffoldData, setScaffoldData] = useState<ScaffoldResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerateScaffolding = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await scaffoldProject(projectId);
      setScaffoldData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to generate project files.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyPath = () => {
    if (scaffoldData?.project_dir) {
      navigator.clipboard.writeText(scaffoldData.project_dir);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-7 shadow-xl mb-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 font-semibold uppercase tracking-wider mb-1">
            <FileCode className="w-4 h-4" />
            <span>PROJECT SCAFFOLDING</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Generate Physical Project Files
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Turn this approved blueprint into a runnable codebase on your disk.
          </p>
        </div>

        {!scaffoldData && (
          <button
            onClick={handleGenerateScaffolding}
            disabled={loading}
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/20 transition-all disabled:opacity-50 shrink-0"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FolderPlus className="w-4 h-4" />
            )}
            <span>{loading ? 'Generating Codebase...' : 'Generate Project Files'}</span>
          </button>
        )}
      </div>

      {error && (
        <div className="mt-4 p-3 rounded-lg bg-rose-950/50 border border-rose-800 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {scaffoldData && (
        <div className="mt-5 space-y-4">
          <div className="p-4 rounded-xl bg-slate-950/80 border border-emerald-900/40">
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-xs font-mono font-semibold text-emerald-400">
                Project Directory Created:
              </span>
              <button
                onClick={handleCopyPath}
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition-colors"
                title="Copy directory path"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied' : 'Copy Path'}</span>
              </button>
            </div>
            <div className="font-mono text-xs text-slate-200 bg-slate-900 p-2.5 rounded border border-slate-800 break-all select-all">
              {scaffoldData.project_dir}
            </div>
          </div>

          <div>
            <span className="text-xs font-mono uppercase text-slate-400 font-semibold block mb-2">
              Files Scaffolded ({scaffoldData.files_created.length})
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
              {scaffoldData.files_created.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center space-x-2 text-xs font-mono p-2 rounded bg-slate-950/60 border border-slate-800/80 text-slate-300"
                >
                  <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                  <span className="truncate">{file}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-800/50 border border-slate-700/60 text-xs text-slate-300 flex items-start space-x-2.5">
            <Terminal className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-white">Next Step:</span> Open terminal in{' '}
              <code className="bg-slate-900 px-1 py-0.5 rounded text-emerald-300">{scaffoldData.project_dir}</code> and run{' '}
              <code className="bg-slate-900 px-1 py-0.5 rounded text-indigo-300">docker-compose up -d</code> to launch your project!
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
