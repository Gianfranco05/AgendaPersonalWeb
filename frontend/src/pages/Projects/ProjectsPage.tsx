import { useState } from 'react';
import { FolderKanban, Plus, Pencil, Trash2, ChevronDown } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import ModuleLockedNotice, { isPaymentRequiredError } from '../../components/ModuleLockedNotice';
import { useProjects, useProjectsSummary, useProjectTasks, removeProject } from '../../hooks/useProjects';
import type { Project, ProjectStatus } from '../../types';
import ProjectForm from './ProjectForm';
import TaskBoard from './TaskBoard';
import { useOpenParam } from '../../hooks/useOpenParam';
import { revealItem } from '../../utils/reveal';

const STATUS_LABELS: Record<ProjectStatus, string> = {
  activo: 'Activo',
  pausado: 'Pausado',
  completado: 'Completado',
};

const STATUS_CLASSES: Record<ProjectStatus, string> = {
  activo: 'bg-rose-100 text-rose-600 dark:bg-rose-950 dark:text-rose-400',
  pausado: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  completado: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400',
};

export default function ProjectsPage() {
  const { data: projects, isLoading, error: projectsError } = useProjects();
  const { data: summary, error: summaryError } = useProjectsSummary();
  const [formOpen, setFormOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Desde el buscador: una tarea de proyecto se muestra expandiendo su proyecto.
  // Se pide también su lista (misma clave SWR que el tablero, sin request extra)
  // para saber si la tarea existe antes de buscarla en el DOM.
  const [openProjectId, setOpenProjectId] = useState<string | null>(null);
  const { data: openProjectTasks } = useProjectTasks(openProjectId);

  useOpenParam({
    ready: !isLoading && !projectsError,
    onOpen: ({ id, entity, parent }) => {
      if (entity !== 'project_task') {
        const target = projects?.find((p) => p.id === id);
        if (!target) return false;
        handleEdit(target);
        return true;
      }
      if (!parent || !projects?.some((p) => p.id === parent)) return false;
      if (openProjectId !== parent || expandedId !== parent) {
        setOpenProjectId(parent);
        setExpandedId(parent);
        return 'wait';
      }
      if (!openProjectTasks) return 'wait';
      if (!openProjectTasks.some((t) => t.id === id)) return false;
      return revealItem(id) || 'wait';
    },
  });

  const error = projectsError ?? summaryError;
  if (isPaymentRequiredError(error)) {
    return <ModuleLockedNotice moduleName="Gestión de Proyectos" />;
  }

  function handleNew() {
    setEditingProject(null);
    setFormOpen(true);
  }

  function handleEdit(project: Project) {
    setEditingProject(project);
    setFormOpen(true);
  }

  async function handleDelete(project: Project) {
    if (!confirm(`Se borra "${project.name}" y todas sus tareas. ¿Seguro?`)) return;
    await removeProject(project.id);
    if (expandedId === project.id) setExpandedId(null);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-2xl font-bold text-gray-800 dark:text-slate-100">
          <FolderKanban className="text-brand-projects" size={24} />
          Gestión de Proyectos
        </h2>
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-projects px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <Plus size={16} />
          Nuevo proyecto
        </button>
      </div>

      {isLoading ? (
        <LoadingSkeleton type="page" />
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
              <p className="text-sm text-gray-500 dark:text-slate-400">Proyectos activos</p>
              <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-slate-100">
                {summary?.projects_active ?? 0}
              </p>
            </div>
            <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
              <p className="text-sm text-gray-500 dark:text-slate-400">En progreso</p>
              <p className="mt-1 text-2xl font-bold text-indigo-500">{summary?.tasks_in_progress ?? 0}</p>
            </div>
            <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
              <p className="text-sm text-gray-500 dark:text-slate-400">Hechas</p>
              <p className="mt-1 text-2xl font-bold text-emerald-500">{summary?.tasks_done ?? 0}</p>
            </div>
          </div>

          {(projects ?? []).length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
              <FolderKanban size={48} className="text-gray-300 dark:text-slate-600" />
              <p className="text-sm text-gray-500 dark:text-slate-400">Todavía no creaste ningún proyecto</p>
              <button
                onClick={handleNew}
                className="flex items-center gap-2 rounded-lg bg-brand-projects px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
              >
                <Plus size={16} />
                Crear proyecto
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {(projects ?? []).map((project) => {
                const expanded = expandedId === project.id;
                return (
                  <div key={project.id} className="rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                      <button
                        onClick={() => setExpandedId(expanded ? null : project.id)}
                        className="flex flex-1 items-center gap-2 text-left"
                      >
                        <ChevronDown
                          size={16}
                          className={`shrink-0 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
                        />
                        <div className="min-w-0">
                          <p className="truncate font-medium text-gray-800 dark:text-slate-100">{project.name}</p>
                          {project.description ? (
                            <p className="truncate text-xs text-gray-500 dark:text-slate-400">
                              {project.description}
                            </p>
                          ) : null}
                        </div>
                      </button>
                      <span
                        className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-medium ${STATUS_CLASSES[project.status]}`}
                      >
                        {STATUS_LABELS[project.status]}
                      </span>
                      <div className="flex shrink-0 gap-1">
                        <button
                          onClick={() => handleEdit(project)}
                          className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-projects"
                          title="Editar"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(project)}
                          className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                          title="Eliminar"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    {expanded ? <TaskBoard projectId={project.id} /> : null}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {formOpen && <ProjectForm project={editingProject} onClose={() => setFormOpen(false)} />}
    </div>
  );
}
