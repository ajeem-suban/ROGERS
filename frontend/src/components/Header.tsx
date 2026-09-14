import React from 'react';
import { Terminal, Folder, Plus } from 'lucide-react';

interface HeaderProps {
  onNewProject?: () => void;
  onOpenProjectsDrawer?: () => void;
  activeProjectName?: string;
}

export const Header: React.FC<HeaderProps> = ({ 
  onNewProject, 
  onOpenProjectsDrawer,
  activeProjectName 
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-inner">
            <Terminal className="w-5 h-5" />
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
              ROGERS
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono font-medium">
                Slice 2
              </span>
            </span>
            <span className="hidden md:inline text-xs text-slate-400 font-mono">
              / Multi-Stage Orchestrator
            </span>
          </div>
        </div>

        {activeProjectName && (
          <div className="hidden lg:flex items-center space-x-2 text-xs font-medium text-slate-300 bg-slate-800/40 px-3 py-1 rounded-full border border-slate-700/50 truncate max-w-xs">
            <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
            <span className="truncate">{activeProjectName}</span>
          </div>
        )}

        <div className="flex items-center space-x-3">
          {onOpenProjectsDrawer && (
            <button
              onClick={onOpenProjectsDrawer}
              className="text-xs font-medium px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
              title="View all saved projects"
            >
              <Folder className="w-3.5 h-3.5 text-slate-400" />
              <span>Projects</span>
            </button>
          )}

          {onNewProject && (
            <button
              onClick={onNewProject}
              className="text-xs font-medium px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
              title="Start a new project"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
