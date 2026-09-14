import React from 'react';
import { 
  CheckCircle2, 
  Circle, 
  Loader2, 
  AlertCircle, 
  Edit3, 
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { StageData } from '../types';

interface StageStepperProps {
  stages: Record<string, StageData>;
  currentStageName: string;
  onSelectStage: (stageName: string) => void;
  onRunAll: () => void;
  isRunningAll: boolean;
}

const STAGE_ORDER = [
  { key: 'research', label: '1. Research' },
  { key: 'requirements', label: '2. Requirements' },
  { key: 'architecture', label: '3. Architecture' },
  { key: 'tech_stack', label: '4. Tech Stack' },
  { key: 'development', label: '5. Dev Tasks' },
];

export const StageStepper: React.FC<StageStepperProps> = ({
  stages,
  currentStageName,
  onSelectStage,
  onRunAll,
  isRunningAll,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-lg mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2 text-xs font-mono text-slate-400 uppercase tracking-wider font-semibold">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Orchestration Pipeline</span>
        </div>

        <button
          onClick={onRunAll}
          disabled={isRunningAll}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs font-medium border border-indigo-500/30 transition-all disabled:opacity-50"
          title="Automatically runs and approves all remaining stages"
        >
          {isRunningAll ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
          ) : (
            <ArrowRight className="w-3.5 h-3.5 text-indigo-400" />
          )}
          <span>{isRunningAll ? 'Running Pipeline...' : 'Auto-Run All Stages'}</span>
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
        {STAGE_ORDER.map(({ key, label }) => {
          const stage = stages[key] || { name: key, label, status: 'pending' };
          const isSelected = currentStageName === key;
          const status = stage.status;

          return (
            <button
              key={key}
              onClick={() => onSelectStage(key)}
              className={`flex flex-col p-3 rounded-xl border text-left transition-all relative ${
                isSelected
                  ? 'bg-indigo-950/60 border-indigo-500 ring-1 ring-indigo-500/50 shadow-md'
                  : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 hover:bg-slate-800/30'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-slate-200 truncate">
                  {label}
                </span>

                {status === 'approved' && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                )}
                {status === 'modified' && (
                  <Edit3 className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                )}
                {status === 'waiting_approval' && (
                  <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                )}
                {status === 'running' && (
                  <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin shrink-0" />
                )}
                {status === 'pending' && (
                  <Circle className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                )}
              </div>

              <span className={`text-[10px] font-mono capitalize truncate ${
                status === 'approved' ? 'text-emerald-400 font-medium' :
                status === 'modified' ? 'text-sky-400 font-medium' :
                status === 'waiting_approval' ? 'text-amber-400 font-semibold' :
                status === 'running' ? 'text-indigo-400 font-semibold' :
                'text-slate-500'
              }`}>
                {status.replace('_', ' ')}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
