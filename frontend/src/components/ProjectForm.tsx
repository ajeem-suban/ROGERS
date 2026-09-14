import React, { useState } from 'react';
import { ArrowRight, Sparkles, Lightbulb } from 'lucide-react';

interface ProjectFormProps {
  onSubmit: (name: string, idea: string) => void;
  isLoading: boolean;
}

const PRESETS = [
  {
    title: 'Tamil AI Document Intelligence',
    idea: 'Build an AI system that allows users to upload Tamil documents, extract text using OCR, search the documents using RAG, and ask questions about the uploaded content.',
  },
  {
    title: 'Fleet Route Optimization Platform',
    idea: 'Real-time GPS routing and battery optimization service for electric delivery vans.',
  },
];

export const ProjectForm: React.FC<ProjectFormProps> = ({ onSubmit, isLoading }) => {
  const [name, setName] = useState('');
  const [idea, setIdea] = useState('');
  const [validationError, setValidationError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError('');

    if (!name.trim()) {
      setValidationError('Please enter a project name.');
      return;
    }
    if (!idea.trim()) {
      setValidationError('Please describe your project idea.');
      return;
    }

    onSubmit(name.trim(), idea.trim());
  };

  const handleApplyPreset = (presetName: string, presetIdea: string) => {
    setName(presetName);
    setIdea(presetIdea);
    setValidationError('');
  };

  return (
    <div className="max-w-2xl mx-auto my-12 px-4">
      {/* Title & Subtitle */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-950/60 border border-indigo-800/60 text-indigo-400 text-xs font-mono mb-4">
          <Sparkles className="w-3.5 h-3.5" />
          <span>AI Project Orchestrator</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-3">
          Turn your project idea into a technical blueprint.
        </h1>
        <p className="text-slate-400 text-base max-w-lg mx-auto leading-relaxed">
          Provide your high-level concept. ROGERS will analyze requirements, architect the system, select the stack, and craft an actionable development plan.
        </p>
      </div>

      {/* Preset Quick Fill */}
      <div className="mb-6 bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
        <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
          <span>Quick Examples (Click to fill)</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.title}
              type="button"
              onClick={() => handleApplyPreset(preset.title, preset.idea)}
              className="text-xs text-left px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-750 transition-colors"
            >
              {preset.title}
            </button>
          ))}
        </div>
      </div>

      {/* Main Project Input Form */}
      <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-slate-950/50">
        {validationError && (
          <div className="mb-6 p-3.5 rounded-lg bg-red-950/50 border border-red-800/60 text-red-300 text-sm font-medium">
            {validationError}
          </div>
        )}

        {/* Project Name Input */}
        <div className="mb-6">
          <label htmlFor="projectName" className="block text-sm font-semibold text-slate-200 mb-2">
            Project Name
          </label>
          <input
            id="projectName"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Tamil AI Document Intelligence"
            disabled={isLoading}
            className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-700/80 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-sm font-sans"
          />
        </div>

        {/* Project Idea Input */}
        <div className="mb-8">
          <label htmlFor="projectIdea" className="block text-sm font-semibold text-slate-200 mb-2">
            Describe your project
          </label>
          <textarea
            id="projectIdea"
            rows={5}
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="Describe what you want to build, target users, key capabilities, or specific constraints..."
            disabled={isLoading}
            className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-700/80 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-sm font-sans leading-relaxed resize-y"
          />
        </div>

        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isLoading}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-sm font-semibold tracking-wide shadow-lg shadow-indigo-600/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <span>Start ROGERS</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};
