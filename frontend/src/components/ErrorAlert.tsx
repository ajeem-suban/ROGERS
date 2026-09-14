import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorAlertProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({ message, onRetry }) => {
  return (
    <div className="max-w-2xl mx-auto my-8 p-6 rounded-xl bg-red-950/40 border border-red-800/60 shadow-lg text-slate-200">
      <div className="flex items-start space-x-3">
        <div className="p-2 rounded-lg bg-red-900/40 text-red-400 shrink-0">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <h3 className="text-base font-semibold text-red-200">
            ROGERS couldn't generate the blueprint.
          </h3>
          <div className="mt-2 text-sm text-red-300/90 font-mono bg-red-950/60 p-3 rounded-md border border-red-900/50 break-words">
            Reason: {message}
          </div>
          {onRetry && (
            <div className="mt-4">
              <button
                onClick={onRetry}
                className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-red-800/80 hover:bg-red-700 text-white text-sm font-medium transition-colors shadow-sm"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Try Again</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
