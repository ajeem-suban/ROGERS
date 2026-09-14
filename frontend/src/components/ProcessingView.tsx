import React, { useEffect, useState } from 'react';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';

interface ProcessingViewProps {
  projectName: string;
}

interface Step {
  id: number;
  label: string;
}

const STAGES: Step[] = [
  { id: 0, label: 'Understanding project idea' },
  { id: 1, label: 'Generating requirements' },
  { id: 2, label: 'Designing architecture' },
  { id: 3, label: 'Selecting technology' },
  { id: 4, label: 'Creating development plan' },
];

export const ProcessingView: React.FC<ProcessingViewProps> = ({ projectName }) => {
  const [currentStep, setCurrentStep] = useState<number>(0);

  useEffect(() => {
    // Progress through visual steps smoothly while waiting for backend
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < STAGES.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 900);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-xl mx-auto my-16 px-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
        <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-slate-800">
          <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              ROGERS is thinking...
            </h2>
            <p className="text-xs text-slate-400 font-mono mt-0.5 truncate max-w-sm">
              Analyzing "{projectName}"
            </p>
          </div>
        </div>

        {/* Step Progress List */}
        <div className="space-y-4">
          {STAGES.map((stage) => {
            const isDone = currentStep > stage.id;
            const isCurrent = currentStep === stage.id;

            return (
              <div
                key={stage.id}
                className={`flex items-center space-x-3 text-sm transition-all duration-300 ${
                  isCurrent
                    ? 'text-indigo-200 font-semibold'
                    : isDone
                    ? 'text-slate-300'
                    : 'text-slate-500'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : isCurrent ? (
                  <div className="w-4 h-4 flex items-center justify-center shrink-0">
                    <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-ping absolute opacity-75"></span>
                    <span className="w-2 h-2 rounded-full bg-indigo-400 relative"></span>
                  </div>
                ) : (
                  <Circle className="w-4 h-4 text-slate-600 shrink-0" />
                )}

                <span className={isCurrent ? 'tracking-wide' : ''}>
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>

        <div className="mt-8 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
          <span>Synthesizing structured blueprint</span>
          <span className="text-indigo-400">Step {Math.min(currentStep + 1, 5)}/5</span>
        </div>
      </div>
    </div>
  );
};
