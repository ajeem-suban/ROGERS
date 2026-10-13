import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  GitCommit,
  GitPullRequest,
  CheckCircle2,
  AlertTriangle,
  Lock,
  RefreshCw,
  FolderGit2,
  FileCode,
  Shield,
  ShieldCheck,
  Clock,
  Send,
  Eye,
} from 'lucide-react';
import { Project, GitStatusResponse, GitDiffResponse, PublishingHistoryEntry } from '../types';
import {
  getGitStatus,
  initGitRepo,
  getGitDiff,
  commitGitChanges,
  addGitRemote,
  pushGitCommit,
  getPublishingHistory,
} from '../api/rogers';

interface GitPanelProps {
  project: Project;
  onRefreshProject?: () => void;
}

export const GitPanel: React.FC<GitPanelProps> = ({ project, onRefreshProject }) => {
  const [gitStatus, setGitStatus] = useState<GitStatusResponse | null>(null);
  const [diffData, setDiffData] = useState<GitDiffResponse | null>(null);
  const [history, setHistory] = useState<PublishingHistoryEntry[]>(project.publishing_history || []);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [commitMessage, setCommitMessage] = useState('');
  const [remoteName, setRemoteName] = useState('origin');
  const [remoteUrl, setRemoteUrl] = useState('');
  const [targetBranch, setTargetBranch] = useState('main');
  const [autoPublishEnabled, setAutoPublishEnabled] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [isDiffLoading, setIsDiffLoading] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [isPushing, setIsPushing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showDiffModal, setShowDiffModal] = useState(false);

  // Verification gate check
  const verifiedTasks = (project.blueprint?.development_tasks || []).filter((t) => t.status === 'verified').length;
  const failedTasks = (project.blueprint?.development_tasks || []).filter((t) => t.status === 'failed').length;
  const isVerifiedForPublishing = verifiedTasks > 0 && failedTasks === 0;

  useEffect(() => {
    loadStatus();
  }, [project.id]);

  const loadStatus = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const st = await getGitStatus(project.id);
      setGitStatus(st);
      if (st.branch) setTargetBranch(st.branch);
      // Auto-select clean changed files by default (excluding secret risk files)
      const safeFiles = st.changes.filter((c) => !c.has_secret_risk).map((c) => c.path);
      setSelectedFiles(safeFiles);

      const hist = await getPublishingHistory(project.id);
      setHistory(hist);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load Git status.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInitRepo = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const st = await initGitRepo(project.id, 'main');
      setGitStatus(st);
      setSuccessMessage('Successfully initialized Git repository on main branch.');
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to initialize Git repository.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewDiff = async () => {
    setIsDiffLoading(true);
    setErrorMessage(null);
    try {
      const d = await getGitDiff(project.id);
      setDiffData(d);
      setShowDiffModal(true);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load diff.');
    } finally {
      setIsDiffLoading(false);
    }
  };

  const handleToggleFileSelection = (path: string) => {
    if (selectedFiles.includes(path)) {
      setSelectedFiles(selectedFiles.filter((p) => p !== path));
    } else {
      setSelectedFiles([...selectedFiles, path]);
    }
  };

  const handleCommit = async () => {
    if (!commitMessage.trim()) {
      setErrorMessage('Please provide a meaningful commit message.');
      return;
    }
    if (selectedFiles.length === 0) {
      setErrorMessage('Please select at least one approved file to commit.');
      return;
    }

    setIsCommitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await commitGitChanges(project.id, commitMessage.trim(), selectedFiles);
      setSuccessMessage(`Commit created: ${res.commit_hash} (${res.files_committed.length} files)`);
      setCommitMessage('');
      await loadStatus();
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setErrorMessage(err.message || 'Commit failed.');
    } finally {
      setIsCommitting(false);
    }
  };

  const handleAddRemote = async () => {
    if (!remoteUrl.trim()) {
      setErrorMessage('Please enter a valid remote URL.');
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      await addGitRemote(project.id, remoteName.trim() || 'origin', remoteUrl.trim());
      setSuccessMessage(`Configured remote '${remoteName}' successfully.`);
      setRemoteUrl('');
      await loadStatus();
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to configure remote.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePush = async () => {
    if (!isVerifiedForPublishing) {
      setErrorMessage('Publishing blocked: All tasks must pass test verification before pushing.');
      return;
    }

    setIsPushing(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await pushGitCommit(
        project.id,
        remoteName.trim() || 'origin',
        targetBranch,
        autoPublishEnabled
      );
      if (res.success) {
        setSuccessMessage(`Published successfully to ${res.remote_name}/${res.branch_name}!`);
      } else {
        setErrorMessage(res.error_detail || 'Push rejected by remote. Local commit preserved.');
      }
      await loadStatus();
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setErrorMessage(err.message || 'Push operation failed. Local commit is preserved.');
    } finally {
      setIsPushing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Tactical Status & Repository Header */}
      <div className="p-6 rounded-2xl border bg-slate-900/90 border-slate-800 shadow-xl relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-blue-950 border border-blue-500/70 text-blue-300 flex items-center justify-center shrink-0">
              <FolderGit2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-mono tracking-widest uppercase font-semibold text-blue-400">
                  VERSION CONTROL & PUBLISHING
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              </div>
              <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">
                {gitStatus?.initialized ? `Repository: ${gitStatus.branch || 'main'}` : 'Git Repository Not Initialized'}
              </h2>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={loadStatus}
              disabled={isLoading}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>

            {!gitStatus?.initialized && (
              <button
                onClick={handleInitRepo}
                disabled={isLoading}
                className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-mono font-bold transition-all shadow-md"
              >
                <FolderGit2 className="w-3.5 h-3.5" />
                <span>Initialize Git</span>
              </button>
            )}
          </div>
        </div>

        {/* Status Metrics Bar */}
        {gitStatus?.initialized && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block">Current Branch</span>
              <span className="text-xs font-mono font-semibold text-blue-300 flex items-center space-x-1 mt-0.5">
                <GitBranch className="w-3 h-3 text-blue-400" />
                <span>{gitStatus.branch || 'None'}</span>
              </span>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block">HEAD Commit</span>
              <span className="text-xs font-mono font-semibold text-slate-200 flex items-center space-x-1 mt-0.5">
                <GitCommit className="w-3 h-3 text-emerald-400" />
                <span>{gitStatus.head_commit || 'Initial'}</span>
              </span>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block">Working State</span>
              <span className="text-xs font-mono font-semibold text-slate-200 mt-0.5 block">
                {gitStatus.is_clean ? (
                  <span className="text-emerald-400 flex items-center space-x-1">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>Clean</span>
                  </span>
                ) : (
                  <span className="text-amber-400 flex items-center space-x-1">
                    <AlertTriangle className="w-3 h-3" />
                    <span>{gitStatus.changes.length} change(s)</span>
                  </span>
                )}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block">Remote Sync</span>
              <span className="text-xs font-mono font-semibold text-slate-300 mt-0.5 block truncate">
                {gitStatus.remotes.length > 0 ? (
                  gitStatus.diverged ? (
                    <span className="text-rose-400">Diverged ({gitStatus.ahead_count}↑ {gitStatus.behind_count}↓)</span>
                  ) : (
                    <span className="text-blue-300">{gitStatus.ahead_count} ahead, {gitStatus.behind_count} behind</span>
                  )
                ) : (
                  <span className="text-slate-500">No remotes</span>
                )}
              </span>
            </div>
          </div>
        )}

        {/* Alert Notifications */}
        {errorMessage && (
          <div className="mt-4 p-3 rounded-xl bg-rose-950/60 border border-rose-800/80 text-xs text-rose-200 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-950/60 border border-emerald-800/80 text-xs text-emerald-200 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}
      </div>

      {/* 2. Verification Gate Banner */}
      <div
        className={`p-4 rounded-xl border flex items-center justify-between gap-4 ${
          isVerifiedForPublishing
            ? 'bg-blue-950/30 border-blue-700/60 text-blue-200'
            : 'bg-amber-950/30 border-amber-800/60 text-amber-200'
        }`}
      >
        <div className="flex items-center space-x-3">
          {isVerifiedForPublishing ? (
            <ShieldCheck className="w-5 h-5 text-blue-400 shrink-0" />
          ) : (
            <Shield className="w-5 h-5 text-amber-400 shrink-0" />
          )}
          <div className="text-xs">
            <span className="font-mono font-bold uppercase tracking-wider block">
              {isVerifiedForPublishing ? 'VERIFICATION GATE: CLEARED' : 'VERIFICATION GATE: RESTRICTED'}
            </span>
            <span className="text-slate-300">
              {isVerifiedForPublishing
                ? `${verifiedTasks} task(s) verified with automated test suites. Clear to push to GitHub.`
                : 'Project must have at least one verified development task passing automated tests before pushing.'}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <label className="flex items-center space-x-1.5 text-xs font-mono cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={autoPublishEnabled}
              onChange={(e) => setAutoPublishEnabled(e.target.checked)}
              disabled={!isVerifiedForPublishing}
              className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
            />
            <span>Auto-Publish Policy</span>
          </label>
        </div>
      </div>

      {/* 3. Staging & Commit Section */}
      {gitStatus?.initialized && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Changed Files & Selective Staging (Left 2 Columns) */}
          <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <FileCode className="w-4 h-4 text-blue-400" />
                <h3 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                  Selective File Staging ({selectedFiles.length}/{gitStatus.changes.length} Approved)
                </h3>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={handleViewDiff}
                  disabled={isDiffLoading || gitStatus.changes.length === 0}
                  className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono border border-slate-700"
                >
                  <Eye className="w-3 h-3 text-slate-400" />
                  <span>Preview Diff</span>
                </button>
              </div>
            </div>

            {gitStatus.changes.length === 0 ? (
              <div className="py-8 text-center text-xs font-mono text-slate-500">
                Working tree is clean. No unstaged or untracked changes.
              </div>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {gitStatus.changes.map((file) => (
                  <div
                    key={file.path}
                    className={`flex items-center justify-between p-2.5 rounded-xl border text-xs font-mono transition-all ${
                      file.has_secret_risk
                        ? 'bg-rose-950/40 border-rose-800/80 text-rose-300'
                        : selectedFiles.includes(file.path)
                        ? 'bg-slate-950/80 border-blue-500/60 text-slate-200'
                        : 'bg-slate-950/40 border-slate-800/80 text-slate-400'
                    }`}
                  >
                    <label className="flex items-center space-x-2.5 cursor-pointer flex-1 truncate">
                      <input
                        type="checkbox"
                        checked={selectedFiles.includes(file.path)}
                        onChange={() => handleToggleFileSelection(file.path)}
                        disabled={file.has_secret_risk}
                        className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0 disabled:opacity-40"
                      />
                      <span className="truncate">{file.path}</span>
                    </label>

                    <div className="flex items-center space-x-2 shrink-0">
                      {file.has_secret_risk ? (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-rose-950 border border-rose-700 text-rose-400 flex items-center space-x-1">
                          <Lock className="w-3 h-3" />
                          <span>BLOCKED (SECRET)</span>
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded text-[10px] uppercase bg-slate-800 text-slate-300 border border-slate-700">
                          {file.status}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Commit Message Box */}
            <div className="pt-3 border-t border-slate-800 space-y-3">
              <input
                type="text"
                placeholder="Commit message (e.g., feat: verify health probe and delivery packaging)"
                value={commitMessage}
                onChange={(e) => setCommitMessage(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />

              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-500">
                  ROGERS automatically guards against accidental credential commits.
                </span>

                <button
                  onClick={handleCommit}
                  disabled={isCommitting || selectedFiles.length === 0 || !commitMessage.trim()}
                  className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-mono font-bold transition-all shadow-md disabled:opacity-40"
                >
                  <GitCommit className="w-3.5 h-3.5" />
                  <span>{isCommitting ? 'Committing...' : 'Commit Approved Files'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Remote Configuration & Publishing (Right 1 Column) */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <GitPullRequest className="w-4 h-4 text-emerald-400" />
              <h3 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                Remote & Push Controls
              </h3>
            </div>

            {/* Configured Remotes */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-slate-400 uppercase block">Configured Remotes</span>
              {gitStatus.remotes.length === 0 ? (
                <div className="text-xs text-slate-500 font-mono">No remotes configured.</div>
              ) : (
                gitStatus.remotes.map((r) => (
                  <div key={r.name} className="p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-xs font-mono">
                    <div className="font-bold text-blue-300">{r.name}</div>
                    <div className="text-[10px] text-slate-400 truncate">{r.push_url}</div>
                  </div>
                ))
              )}
            </div>

            {/* Add Remote Form */}
            <div className="pt-2 border-t border-slate-800 space-y-2">
              <span className="text-[10px] font-mono text-slate-400 uppercase block">Add / Update Remote</span>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Remote (e.g. origin)"
                  value={remoteName}
                  onChange={(e) => setRemoteName(e.target.value)}
                  className="w-1/3 px-2 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200"
                />
                <input
                  type="text"
                  placeholder="https://github.com/user/repo.git"
                  value={remoteUrl}
                  onChange={(e) => setRemoteUrl(e.target.value)}
                  className="flex-1 px-2 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200"
                />
              </div>
              <button
                onClick={handleAddRemote}
                disabled={isLoading || !remoteUrl.trim()}
                className="w-full py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition-colors disabled:opacity-40"
              >
                Set Remote
              </button>
            </div>

            {/* Push Action */}
            <div className="pt-2 border-t border-slate-800 space-y-3">
              <button
                onClick={handlePush}
                disabled={isPushing || gitStatus.remotes.length === 0 || !isVerifiedForPublishing}
                className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-bold shadow-md transition-all flex items-center justify-center space-x-2 disabled:opacity-40"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isPushing ? 'Publishing...' : 'Push Verified Commits'}</span>
              </button>
              <span className="text-[10px] font-mono text-slate-500 block text-center">
                Uses Git Credential Manager / SSH securely.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 4. Publishing Audit Log History */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-3">
        <div className="flex items-center space-x-2 pb-2 border-b border-slate-800">
          <Clock className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
            Publishing Audit & History Log
          </h3>
        </div>

        {history.length === 0 ? (
          <div className="py-6 text-center text-xs font-mono text-slate-500">
            No publishing operations recorded yet.
          </div>
        ) : (
          <div className="space-y-2">
            {history.map((item) => (
              <div
                key={item.id}
                className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-xs font-mono flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-200">{item.commit_message}</span>
                    {item.commit_hash && (
                      <code className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-blue-300">
                        {item.commit_hash}
                      </code>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Branch: {item.branch} • {new Date(item.timestamp).toLocaleString()}
                  </div>
                  {item.error_detail && (
                    <div className="text-[10px] text-rose-400 mt-1">
                      Error: {item.error_detail}
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      item.push_status === 'pushed'
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : item.push_status === 'push_failed'
                        ? 'bg-rose-950 text-rose-300 border border-rose-800'
                        : 'bg-blue-950 text-blue-300 border border-blue-800'
                    }`}
                  >
                    {item.push_status.replace('_', ' ')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Diff Preview Modal */}
      {showDiffModal && diffData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-3xl rounded-2xl bg-[#0a0e17] border border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white font-mono uppercase">
                Git Diff Preview ({diffData.file_count} files)
              </h3>
              <button
                onClick={() => setShowDiffModal(false)}
                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono"
              >
                Close
              </button>
            </div>
            <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 max-h-96 overflow-y-auto whitespace-pre-wrap">
              {diffData.diff || 'No diff detected.'}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
