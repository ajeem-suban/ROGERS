import React, { useState } from 'react';
import { 
  Check, 
  Copy, 
  Layers, 
  Server, 
  Layout, 
  Database, 
  Cpu, 
  CheckSquare, 
  ListChecks, 
  ArrowRight, 
  Download,
  Share2,
  FileCode,
  Sliders
} from 'lucide-react';
import { Project, Blueprint } from '../types';
import { ScaffoldPanel } from './ScaffoldPanel';
import { StageInspector } from './StageInspector';

interface BlueprintViewProps {
  project: Project;
  onNewProject: () => void;
  onRunStage: (stageName: string, guidance?: string) => Promise<void>;
  onApproveStage: (stageName: string) => Promise<void>;
  onModifyStage: (stageName: string, modifications: Record<string, any>) => Promise<void>;
  isLoadingStage: boolean;
}

export const BlueprintView: React.FC<BlueprintViewProps> = ({ 
  project, 
  onNewProject,
  onRunStage,
  onApproveStage,
  onModifyStage,
  isLoadingStage,
}) => {
  const [activeTab, setActiveTab] = useState<'blueprint' | 'scaffold' | 'stages'>('blueprint');
  const [selectedStageName, setSelectedStageName] = useState<string>('research');
  const [copied, setCopied] = useState(false);
  const blueprint: Blueprint | undefined = project.blueprint ?? undefined;

  const handleCopyMarkdown = () => {
    if (!blueprint) return;
    const md = generateMarkdown(project.name, blueprint);
    navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJSON = () => {
    const blob = new Blob([JSON.stringify(project, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${project.name.toLowerCase().replace(/[^a-z0-9]/g, '_')}_blueprint.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const stages = project.stages || {};
  const currentStage = stages[selectedStageName] || {
    name: selectedStageName,
    label: selectedStageName,
    status: 'pending',
    updated_at: new Date().toISOString()
  };

  return (
    <div className="max-w-5xl mx-auto my-8 px-4 sm:px-6 pb-20">
      {/* Navigation Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-3 mb-6">
        <button
          onClick={() => setActiveTab('blueprint')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'blueprint'
              ? 'bg-indigo-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Technical Blueprint</span>
        </button>

        <button
          onClick={() => setActiveTab('stages')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'stages'
              ? 'bg-indigo-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Stage Inspector ({Object.keys(stages).length})</span>
        </button>

        <button
          onClick={() => setActiveTab('scaffold')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'scaffold'
              ? 'bg-emerald-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <FileCode className="w-3.5 h-3.5" />
          <span>Code Scaffolding</span>
        </button>
      </div>

      {/* Tab: Code Scaffolding */}
      {activeTab === 'scaffold' && (
        <ScaffoldPanel projectId={project.id} projectName={project.name} />
      )}

      {/* Tab: Stage Inspector */}
      {activeTab === 'stages' && (
        <div>
          {/* Stage Selector Pills */}
          <div className="flex flex-wrap gap-2 mb-6">
            {Object.entries(stages).map(([key, stg]) => (
              <button
                key={key}
                onClick={() => setSelectedStageName(key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all border ${
                  selectedStageName === key
                    ? 'bg-indigo-950/70 border-indigo-500 text-indigo-300 font-semibold'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {stg.label} ({stg.status})
              </button>
            ))}
          </div>

          <StageInspector
            stage={currentStage}
            onRun={(guidance) => onRunStage(selectedStageName, guidance)}
            onApprove={() => onApproveStage(selectedStageName)}
            onModify={(mods) => onModifyStage(selectedStageName, mods)}
            isLoading={isLoadingStage}
          />
        </div>
      )}

      {/* Tab: Unified Blueprint View */}
      {activeTab === 'blueprint' && blueprint && (
        <>
          {/* Top Header Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-8 shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
              <div>
                <div className="flex items-center space-x-2 text-xs font-mono text-indigo-400 uppercase tracking-widest font-semibold mb-1">
                  <span>PROJECT BLUEPRINT</span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {project.name}
                </h1>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={handleCopyMarkdown}
                  className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-medium border border-slate-700 transition-colors"
                  title="Copy formatted markdown"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                  <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
                </button>

                <button
                  onClick={handleDownloadJSON}
                  className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-medium border border-slate-700 transition-colors"
                  title="Export as JSON"
                >
                  <Download className="w-3.5 h-3.5 text-slate-400" />
                  <span>JSON</span>
                </button>

                <button
                  onClick={onNewProject}
                  className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors shadow-sm"
                >
                  <span>New Project</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Executive Summary */}
            <div className="mt-6">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-2">
                SUMMARY
              </h2>
              <p className="text-slate-200 text-sm sm:text-base leading-relaxed">
                {blueprint.summary}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left 2 Columns: Requirements & Development Tasks */}
            <div className="lg:col-span-2 space-y-8">
              {/* Requirements Section */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-7 shadow-lg">
                <div className="flex items-center space-x-2 text-sm font-bold uppercase tracking-wider text-slate-300 font-mono mb-4 pb-3 border-b border-slate-800">
                  <CheckSquare className="w-4 h-4 text-indigo-400" />
                  <span>REQUIREMENTS</span>
                </div>
                <ul className="space-y-3">
                  {blueprint.requirements.map((req, idx) => (
                    <li key={idx} className="flex items-start space-x-3 text-sm text-slate-300 leading-normal">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-2 shrink-0"></span>
                      <span>{req}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Development Tasks / Plan Section */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-7 shadow-lg">
                <div className="flex items-center space-x-2 text-sm font-bold uppercase tracking-wider text-slate-300 font-mono mb-4 pb-3 border-b border-slate-800">
                  <ListChecks className="w-4 h-4 text-emerald-400" />
                  <span>DEVELOPMENT PLAN</span>
                </div>
                <div className="space-y-4">
                  {blueprint.development_tasks.map((task, idx) => {
                    const priorityBadge = 
                      task.priority.toLowerCase() === 'high' 
                        ? 'bg-rose-950/60 text-rose-300 border-rose-800/60'
                        : task.priority.toLowerCase() === 'medium'
                        ? 'bg-amber-950/60 text-amber-300 border-amber-800/60'
                        : 'bg-slate-800 text-slate-300 border-slate-700';

                    return (
                      <div 
                        key={idx} 
                        className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/90 hover:border-slate-700/80 transition-all"
                      >
                        <div className="flex items-start justify-between gap-3 mb-1.5">
                          <div className="flex items-center space-x-2.5">
                            <span className="text-xs font-mono font-bold text-slate-500">
                              {String(idx + 1).padStart(2, '0')}
                            </span>
                            <h3 className="text-sm font-semibold text-slate-100">
                              {task.title}
                            </h3>
                          </div>
                          <span className={`text-[11px] font-mono font-medium px-2 py-0.5 rounded-md border uppercase shrink-0 ${priorityBadge}`}>
                            {task.priority}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 pl-6 leading-relaxed">
                          {task.description}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Right 1 Column: Tech Stack, Architecture & Next Steps */}
            <div className="space-y-8">
              {/* Tech Stack Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
                <div className="flex items-center space-x-2 text-sm font-bold uppercase tracking-wider text-slate-300 font-mono mb-4 pb-3 border-b border-slate-800">
                  <Layers className="w-4 h-4 text-indigo-400" />
                  <span>TECH STACK</span>
                </div>
                <div className="space-y-3.5">
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 mb-1">
                      <Layout className="w-3.5 h-3.5 text-blue-400" />
                      <span>Frontend</span>
                    </div>
                    <div className="text-xs text-slate-200 font-mono">
                      {blueprint.tech_stack.frontend}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 mb-1">
                      <Server className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Backend</span>
                    </div>
                    <div className="text-xs text-slate-200 font-mono">
                      {blueprint.tech_stack.backend}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 mb-1">
                      <Database className="w-3.5 h-3.5 text-amber-400" />
                      <span>Database</span>
                    </div>
                    <div className="text-xs text-slate-200 font-mono">
                      {blueprint.tech_stack.database}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 mb-1">
                      <Cpu className="w-3.5 h-3.5 text-purple-400" />
                      <span>AI / ML</span>
                    </div>
                    <div className="text-xs text-slate-200 font-mono">
                      {blueprint.tech_stack.ai}
                    </div>
                  </div>
                </div>
              </div>

              {/* Architecture Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
                <div className="flex items-center space-x-2 text-sm font-bold uppercase tracking-wider text-slate-300 font-mono mb-4 pb-3 border-b border-slate-800">
                  <Share2 className="w-4 h-4 text-purple-400" />
                  <span>ARCHITECTURE</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed mb-4">
                  {blueprint.architecture.description}
                </p>

                <div className="pt-3 border-t border-slate-800/80">
                  <span className="text-[11px] font-mono uppercase text-slate-400 font-semibold block mb-2">
                    Components
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {blueprint.architecture.components.map((comp, idx) => (
                      <span
                        key={idx}
                        className="text-[11px] px-2 py-1 rounded bg-slate-800/80 text-slate-300 border border-slate-700/60 font-mono"
                      >
                        {comp}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Next Steps Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
                <div className="flex items-center space-x-2 text-sm font-bold uppercase tracking-wider text-slate-300 font-mono mb-4 pb-3 border-b border-slate-800">
                  <ArrowRight className="w-4 h-4 text-indigo-400" />
                  <span>NEXT STEPS</span>
                </div>
                <ol className="space-y-2.5">
                  {blueprint.next_steps.map((step, idx) => (
                    <li key={idx} className="flex items-start space-x-2.5 text-xs text-slate-300 leading-relaxed">
                      <span className="text-indigo-400 font-mono font-bold shrink-0">{idx + 1}.</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

function generateMarkdown(projectName: string, bp: Blueprint): string {
  return `# PROJECT BLUEPRINT: ${projectName}

## SUMMARY
${bp.summary}

## REQUIREMENTS
${bp.requirements.map(r => `* ${r}`).join('\n')}

## TECH STACK
* **Frontend**: ${bp.tech_stack.frontend}
* **Backend**: ${bp.tech_stack.backend}
* **Database**: ${bp.tech_stack.database}
* **AI**: ${bp.tech_stack.ai}

## ARCHITECTURE
${bp.architecture.description}

### Components:
${bp.architecture.components.map(c => `* ${c}`).join('\n')}

## DEVELOPMENT PLAN
${bp.development_tasks.map((t, i) => `${i + 1}. **${t.title}** [${t.priority.toUpperCase()}]\n   ${t.description}`).join('\n\n')}

## NEXT STEPS
${bp.next_steps.map((s, i) => `${i + 1}. ${s}`).join('\n')}
`;
}
