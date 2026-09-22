import React, { useState } from 'react';
import { Header } from './components/Header';
import { ProjectForm } from './components/ProjectForm';
import { StageStepper } from './components/StageStepper';
import { StageInspector } from './components/StageInspector';
import { BlueprintView } from './components/BlueprintView';
import { ProjectsDrawer } from './components/ProjectsDrawer';
import { ErrorAlert } from './components/ErrorAlert';
import { 
  createProject, 
  getProject, 
  runStage, 
  approveStage, 
  modifyStage, 
  runAllStages 
} from './api/rogers';
import { Project, StageData } from './types';

type ViewMode = 'form' | 'pipeline' | 'blueprint' | 'error';

export const App: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('form');
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [selectedStageName, setSelectedStageName] = useState<string>('research');
  const [isLoadingStage, setIsLoadingStage] = useState(false);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // 1. Start a New Project
  const handleStartProject = async (name: string, idea: string) => {
    setErrorMessage('');
    try {
      // Step A: Create project
      const created = await createProject({ name, idea });
      setCurrentProject(created);
      setSelectedStageName('research');
      setViewMode('pipeline');

      // Step B: Automatically trigger first stage (research)
      setIsLoadingStage(true);
      const firstStage = await runStage(created.id, 'research');
      const updatedStages = { ...(created.stages || {}), research: firstStage };
      setCurrentProject({
        ...created,
        current_stage: 'research',
        stages: updatedStages,
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to initialize project.');
      setViewMode('error');
    } finally {
      setIsLoadingStage(false);
    }
  };

  // 2. Select a stage to inspect
  const handleSelectStage = (stageName: string) => {
    setSelectedStageName(stageName);
  };

  // 3. Run or Regenerate a Stage
  const handleRunStage = async (stageName: string, guidance?: string) => {
    if (!currentProject) return;
    setIsLoadingStage(true);
    setErrorMessage('');
    try {
      const updatedStage = await runStage(currentProject.id, stageName, guidance);
      const updatedStages = { ...(currentProject.stages || {}), [stageName]: updatedStage };
      
      // Fetch latest project to get blueprint if generated
      const freshProject = await getProject(currentProject.id);
      setCurrentProject({
        ...freshProject,
        stages: updatedStages,
        current_stage: stageName,
      });

      if (freshProject.blueprint && stageName === 'development') {
        setViewMode('blueprint');
      }
    } catch (err: any) {
      setErrorMessage(err.message || `Failed to run stage '${stageName}'.`);
    } finally {
      setIsLoadingStage(false);
    }
  };

  // 4. Approve a Stage and advance
  const handleApproveStage = async (stageName: string) => {
    if (!currentProject) return;
    setIsLoadingStage(true);
    try {
      await approveStage(currentProject.id, stageName);
      const fresh = await getProject(currentProject.id);
      setCurrentProject(fresh);

      // Advance selection to next stage if available
      const stageKeys = ['research', 'requirements', 'architecture', 'tech_stack', 'development'];
      const currentIdx = stageKeys.indexOf(stageName);
      if (currentIdx < stageKeys.length - 1) {
        const nextStageName = stageKeys[currentIdx + 1];
        setSelectedStageName(nextStageName);
        // Automatically run the next stage!
        await runStage(currentProject.id, nextStageName);
        const refetched = await getProject(currentProject.id);
        setCurrentProject(refetched);
      } else {
        // All stages approved
        setViewMode('blueprint');
      }
    } catch (err: any) {
      setErrorMessage(err.message || `Failed to approve stage '${stageName}'.`);
    } finally {
      setIsLoadingStage(false);
    }
  };

  // 5. Modify a Stage
  const handleModifyStage = async (stageName: string, modifications: Record<string, any>) => {
    if (!currentProject) return;
    setIsLoadingStage(true);
    try {
      await modifyStage(currentProject.id, stageName, modifications);
      const fresh = await getProject(currentProject.id);
      setCurrentProject(fresh);
    } catch (err: any) {
      setErrorMessage(err.message || `Failed to save modifications.`);
    } finally {
      setIsLoadingStage(false);
    }
  };

  // 6. Run all stages automatically
  const handleRunAllStages = async () => {
    if (!currentProject) return;
    setIsRunningAll(true);
    setErrorMessage('');
    try {
      const completed = await runAllStages(currentProject.id);
      setCurrentProject(completed);
      setViewMode('blueprint');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed during automated pipeline execution.');
    } finally {
      setIsRunningAll(false);
    }
  };

  // Switch to project selected from drawer
  const handleSelectProjectFromDrawer = (p: Project) => {
    setCurrentProject(p);
    if (p.blueprint || p.status === 'completed') {
      setViewMode('blueprint');
    } else {
      setViewMode('pipeline');
      setSelectedStageName(p.current_stage || 'research');
    }
  };

  const handleResetToNew = () => {
    setCurrentProject(null);
    setErrorMessage('');
    setViewMode('form');
  };

  const currentStages = currentProject?.stages || {};
  const activeStageData: StageData = currentStages[selectedStageName] || {
    name: selectedStageName,
    label: selectedStageName,
    status: 'pending',
    updated_at: new Date().toISOString(),
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-600 selection:text-white">
      <Header 
        onNewProject={handleResetToNew}
        onOpenProjectsDrawer={() => setIsDrawerOpen(true)}
        activeProjectName={currentProject?.name}
      />

      <ProjectsDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onSelectProject={handleSelectProjectFromDrawer}
        currentProjectId={currentProject?.id}
      />

      <main className="flex-1 flex flex-col justify-start">
        {/* State A: Project Form */}
        {viewMode === 'form' && (
          <ProjectForm onSubmit={handleStartProject} isLoading={isLoadingStage} />
        )}

        {/* State B: Multi-Stage Pipeline */}
        {viewMode === 'pipeline' && currentProject && (
          <div className="max-w-5xl mx-auto w-full my-8 px-4 sm:px-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <span className="text-xs font-mono text-indigo-400 font-semibold uppercase">
                  ACTIVE ORCHESTRATION
                </span>
                <h1 className="text-2xl font-bold text-white tracking-tight">
                  {currentProject.name}
                </h1>
              </div>
              <button
                onClick={() => setViewMode('blueprint')}
                disabled={!currentProject.blueprint}
                className="text-xs font-medium px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 disabled:opacity-40 transition-colors"
              >
                View Full Blueprint
              </button>
            </div>

            <StageStepper
              stages={currentStages}
              currentStageName={selectedStageName}
              onSelectStage={handleSelectStage}
              onRunAll={handleRunAllStages}
              isRunningAll={isRunningAll}
            />

            <StageInspector
              stage={activeStageData}
              onRun={(guidance) => handleRunStage(selectedStageName, guidance)}
              onApprove={() => handleApproveStage(selectedStageName)}
              onModify={(mods) => handleModifyStage(selectedStageName, mods)}
              isLoading={isLoadingStage || isRunningAll}
            />
          </div>
        )}

        {/* State C: Blueprint & Scaffolding View */}
        {viewMode === 'blueprint' && currentProject && (
          <BlueprintView 
            project={currentProject} 
            onNewProject={handleResetToNew}
            onRunStage={handleRunStage}
            onApproveStage={handleApproveStage}
            onModifyStage={handleModifyStage}
            isLoadingStage={isLoadingStage}
            onRefreshProject={async () => {
              if (currentProject) {
                const fresh = await getProject(currentProject.id);
                setCurrentProject(fresh);
              }
            }}
          />
        )}

        {/* Error View */}
        {viewMode === 'error' && (
          <ErrorAlert 
            message={errorMessage} 
            onRetry={handleResetToNew} 
          />
        )}
      </main>

      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500 font-mono">
        ROGERS AI Project Orchestrator • Slice 2 (Multi-Stage & Scaffolding) • Free & Open-Source
      </footer>
    </div>
  );
};

export default App;
