import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchProjects,
  createProject,
  updateProject,
  deleteProject,
  fetchProjectTasks,
  createProjectTask,
  updateProjectTask,
  deleteProjectTask,
  fetchProjectsSummary,
} from '../api/endpoints';
import type { Project, ProjectTask } from '../types';

const PROJECTS_KEY = 'projects';
const SUMMARY_KEY = 'projects/summary';
// Sub-lista dependiente del proyecto padre, igual que `travel/items` por trip.
const tasksKey = (projectId: string) => ['projects/tasks', projectId] as const;

export function useProjects() {
  return useApiSWR(PROJECTS_KEY, fetchProjects);
}

export function useProjectsSummary() {
  return useApiSWR(SUMMARY_KEY, fetchProjectsSummary);
}

export function useProjectTasks(projectId: string | null) {
  return useApiSWR(
    projectId ? tasksKey(projectId) : null,
    projectId ? () => fetchProjectTasks(projectId) : null,
  );
}

/** Borrar un proyecto se lleva sus tareas, así que se revalida todo junto. */
async function revalidate(projectId?: string) {
  const tasks = [globalMutate(PROJECTS_KEY), globalMutate(SUMMARY_KEY)];
  if (projectId) tasks.push(globalMutate(tasksKey(projectId)));
  await Promise.all(tasks);
}

export async function addProject(input: Partial<Project>) {
  await createProject(input);
  await revalidate();
}

export async function editProject(id: string, input: Partial<Project>) {
  await updateProject(id, input);
  await revalidate();
}

export async function removeProject(id: string) {
  await deleteProject(id);
  await revalidate();
}

export async function addTask(input: Partial<ProjectTask>) {
  await createProjectTask(input);
  await revalidate(input.project_id);
}

export async function editTask(id: string, projectId: string, input: Partial<ProjectTask>) {
  await updateProjectTask(id, input);
  await revalidate(projectId);
}

export async function removeTask(id: string, projectId: string) {
  await deleteProjectTask(id);
  await revalidate(projectId);
}
