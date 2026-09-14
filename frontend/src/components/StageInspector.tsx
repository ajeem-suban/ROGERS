import React, { useState } from 'react';
import { 
  Check, 
  Edit3, 
  RefreshCw, 
  Play, 
  Save, 
  X,
  Server,
  Database,
  Cpu,
  Layout
} from 'lucide-react';
import { StageData } from '../types';

interface StageInspectorProps {
  stage: StageData;
  onRun: (guidance?: string) => Promise<void>;
  onApprove: () => Promise<void>;
  onModify: (modifications: Record<string, any>) => Promise<void>;
  isLoading: boolean;
}

export const StageInspector: React.FC<StageInspectorProps> = ({
  stage,
  onRun,
  onApprove,
  onModify,
  isLoading,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<Record<string, any>>({});
  const [guidance, setGuidance] = useState('');
  const [showGuidanceInput, setShowGuidanceInput] = useState(false);

  const output = stage.user_modifications || stage.output || {};

  const handleStartEdit = () => {
    setEditData(JSON.parse(JSON.stringify(output)));
    setIsEditing(true);
  };

  const handleSaveEdit = async () => {
    await onModify(editData);
    setIsEditing(false);
  };

  const handleRegenerate = async () => {
    await onRun(guidance.trim() || undefined);
    setGuidance('');
    setShowGuidanceInput(false);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-8">
      {/* Header with Title and Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2 text-xs font-mono text-indigo-400 font-semibold uppercase tracking-wider mb-1">
            <span>STAGE INSPECTOR</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            {stage.label}
          </h2>
        </div>

        <div className="flex items-center space-x-2">
          {/* Action: Run / Re-run */}
          {stage.status === 'pending' ? (
            <button
              onClick={() => onRun()}
              disabled={isLoading}
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Run Stage</span>
            </button>
          ) : (
            <>
              {/* Regenerate Button */}
              <button
                onClick={() => setShowGuidanceInput(!showGuidanceInput)}
                disabled={isLoading}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition-colors disabled:opacity-50"
                title="Regenerate this stage with optional feedback"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${isLoading ? 'animate-spin' : ''}`} />
                <span>Regenerate</span>
              </button>

              {/* Modify Button */}
              {!isEditing && (
                <button
                  onClick={handleStartEdit}
                  disabled={isLoading}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition-colors disabled:opacity-50"
                  title="Manually edit decisions in this stage"
                >
                  <Edit3 className="w-3.5 h-3.5 text-sky-400" />
                  <span>Modify</span>
                </button>
              )}

              {/* Approve Button */}
              {stage.status !== 'approved' && (
                <button
                  onClick={onApprove}
                  disabled={isLoading}
                  className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Approve Stage</span>
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Optional Guidance Prompt Drawer */}
      {showGuidanceInput && (
        <div className="my-4 p-4 rounded-xl bg-slate-950/80 border border-indigo-900/60 shadow-inner">
          <label className="block text-xs font-semibold text-slate-300 mb-2">
            Add Guidance for Stage Regeneration
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={guidance}
              onChange={(e) => setGuidance(e.target.value)}
              placeholder="e.g. Optimize for edge deployment and local SQLite database..."
              className="flex-1 px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 text-xs placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              onClick={handleRegenerate}
              disabled={isLoading}
              className="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors disabled:opacity-50"
            >
              Regenerate Now
            </button>
            <button
              onClick={() => setShowGuidanceInput(false)}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Stage Content View / Edit Mode */}
      <div className="mt-6">
        {stage.status === 'pending' ? (
          <div className="text-center py-12 text-slate-500 text-sm font-mono">
            This stage has not run yet. Click "Run Stage" or "Auto-Run All" above.
          </div>
        ) : isEditing ? (
          /* Inline Editing Interface */
          <div className="space-y-4 bg-slate-950/60 p-5 rounded-xl border border-sky-900/50">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <span className="text-xs font-mono font-semibold text-sky-400 uppercase">
                Editing Stage Decisions
              </span>
              <div className="flex space-x-2">
                <button
                  onClick={handleSaveEdit}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Modifications</span>
                </button>
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-3 py-1.5 rounded-md bg-slate-800 text-slate-300 text-xs"
                >
                  Cancel
                </button>
              </div>
            </div>

            {/* Render editable fields depending on stage */}
            {stage.name === 'tech_stack' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1 font-semibold">Frontend</label>
                  <input
                    type="text"
                    value={editData.frontend || ''}
                    onChange={(e) => setEditData({ ...editData, frontend: e.target.value })}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-semibold">Backend</label>
                  <input
                    type="text"
                    value={editData.backend || ''}
                    onChange={(e) => setEditData({ ...editData, backend: e.target.value })}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-semibold">Database</label>
                  <input
                    type="text"
                    value={editData.database || ''}
                    onChange={(e) => setEditData({ ...editData, database: e.target.value })}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-semibold">AI / ML</label>
                  <input
                    type="text"
                    value={editData.ai || ''}
                    onChange={(e) => setEditData({ ...editData, ai: e.target.value })}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-slate-100"
                  />
                </div>
              </div>
            )}

            {stage.name !== 'tech_stack' && (
              <div>
                <label className="block text-slate-400 mb-1 font-semibold text-xs">
                  Raw JSON Output
                </label>
                <textarea
                  rows={8}
                  value={JSON.stringify(editData, null, 2)}
                  onChange={(e) => {
                    try {
                      setEditData(JSON.parse(e.target.value));
                    } catch {}
                  }}
                  className="w-full p-3 font-mono text-xs rounded bg-slate-900 border border-slate-700 text-slate-200"
                />
              </div>
            )}
          </div>
        ) : (
          /* Render Formatted Output */
          <div className="space-y-6">
            {stage.name === 'research' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <h3 className="text-xs font-mono uppercase text-slate-400 font-bold mb-2">
                    Executive Analysis
                  </h3>
                  <p className="text-sm text-slate-200 leading-relaxed">
                    {output.summary}
                  </p>
                </div>

                {output.key_challenges && (
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                    <h3 className="text-xs font-mono uppercase text-slate-400 font-bold mb-2">
                      Key Technical Challenges
                    </h3>
                    <ul className="space-y-2">
                      {output.key_challenges.map((c: string, idx: number) => (
                        <li key={idx} className="flex items-start space-x-2 text-xs text-slate-300">
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0"></span>
                          <span>{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {stage.name === 'requirements' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <h3 className="text-xs font-mono uppercase text-slate-400 font-bold mb-3">
                    Functional Requirements
                  </h3>
                  <ul className="space-y-2.5">
                    {(output.functional_requirements || []).map((r: string, idx: number) => (
                      <li key={idx} className="flex items-start space-x-2.5 text-xs text-slate-300">
                        <span className="text-indigo-400 font-mono font-bold shrink-0">{idx + 1}.</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {output.non_functional_requirements && (
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                    <h3 className="text-xs font-mono uppercase text-slate-400 font-bold mb-3">
                      Non-Functional Specifications
                    </h3>
                    <ul className="space-y-2">
                      {output.non_functional_requirements.map((r: string, idx: number) => (
                        <li key={idx} className="flex items-start space-x-2 text-xs text-slate-300">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {stage.name === 'tech_stack' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 mb-1">
                    <Layout className="w-4 h-4 text-blue-400" />
                    <span>Frontend</span>
                  </div>
                  <div className="text-sm font-mono text-slate-100">{output.frontend}</div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 mb-1">
                    <Server className="w-4 h-4 text-emerald-400" />
                    <span>Backend</span>
                  </div>
                  <div className="text-sm font-mono text-slate-100">{output.backend}</div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 mb-1">
                    <Database className="w-4 h-4 text-amber-400" />
                    <span>Database</span>
                  </div>
                  <div className="text-sm font-mono text-slate-100">{output.database}</div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 mb-1">
                    <Cpu className="w-4 h-4 text-purple-400" />
                    <span>AI / ML</span>
                  </div>
                  <div className="text-sm font-mono text-slate-100">{output.ai}</div>
                </div>
              </div>
            )}

            {stage.name === 'architecture' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <h3 className="text-xs font-mono uppercase text-slate-400 font-bold mb-2">
                    Architecture Description
                  </h3>
                  <p className="text-sm text-slate-200 leading-relaxed">
                    {output.description}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <h3 className="text-xs font-mono uppercase text-slate-400 font-bold mb-3">
                    Component Topology
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {(output.components || []).map((comp: string, idx: number) => (
                      <span
                        key={idx}
                        className="text-xs px-2.5 py-1.5 rounded-lg bg-slate-800 text-slate-200 border border-slate-700 font-mono"
                      >
                        {comp}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {stage.name === 'development' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <h3 className="text-xs font-mono uppercase text-slate-400 font-bold mb-3">
                    Development Tasks & Sprints
                  </h3>
                  <div className="space-y-3">
                    {(output.tasks || []).map((task: any, idx: number) => (
                      <div key={idx} className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 flex items-start justify-between gap-3">
                        <div>
                          <div className="text-xs font-semibold text-slate-100 mb-1">
                            {task.title}
                          </div>
                          <div className="text-[11px] text-slate-400">
                            {task.description}
                          </div>
                        </div>
                        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-slate-700 text-slate-300 shrink-0">
                          {task.priority}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
