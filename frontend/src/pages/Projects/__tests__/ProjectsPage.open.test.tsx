import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts, stubScrollIntoView } from '../../../test/openParam'
import type { Project, ProjectTask } from '../../../types'

vi.mock('../../../hooks/useProjects', () => ({
  useProjects: vi.fn(),
  useProjectsSummary: vi.fn(() => ({ data: undefined })),
  useProjectTasks: vi.fn(),
  removeProject: vi.fn(),
  addProject: vi.fn(),
  editProject: vi.fn(),
  addTask: vi.fn(),
  editTask: vi.fn(),
  removeTask: vi.fn(),
}))

import { useProjects, useProjectTasks } from '../../../hooks/useProjects'
import ProjectsPage from '../ProjectsPage'

const project = (id: string, name: string): Project => ({ id, name, description: null, status: 'activo' }) as Project
const task = (id: string, project_id: string, title: string): ProjectTask =>
  ({ id, project_id, title, status: 'pendiente' }) as ProjectTask

function mockProjects(projects: Project[] | undefined, tasksByProject: Record<string, ProjectTask[] | undefined> = {}) {
  vi.mocked(useProjects).mockReturnValue({ data: projects, isLoading: projects === undefined, error: undefined } as never)
  vi.mocked(useProjectTasks).mockImplementation(((projectId: string | null) => ({
    data: projectId ? tasksByProject[projectId] : undefined,
    isLoading: projectId ? tasksByProject[projectId] === undefined : false,
  })) as never)
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <ProjectsPage />
      <LocationProbe />
    </>,
    { router: { initialEntries: [url] } },
  )
}

let scroll: ReturnType<typeof vi.fn>
beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
  scroll = stubScrollIntoView()
})

describe('ProjectsPage: ?open=<id>&entity=... desde el buscador', () => {
  it('entity=project abre el formulario del proyecto y limpia la URL', async () => {
    mockProjects([project('p1', 'Web'), project('p2', 'App móvil')])
    renderAt('/projects?open=p2&entity=project')

    expect(await screen.findByText('Editar proyecto')).toBeInTheDocument()
    expect(screen.getByDisplayValue('App móvil')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/projects$/))
    expect(toastMessages()).toEqual([])
  })

  it('entity=project_task selecciona el proyecto padre y resalta la tarea', async () => {
    mockProjects([project('p1', 'Web'), project('p2', 'App móvil')], {
      p2: [task('k1', 'p2', 'Diseñar login'), task('k2', 'p2', 'Publicar en tienda')],
    })
    renderAt('/projects?open=k2&entity=project_task&parent=p2')

    await waitFor(() => expect(screen.getByText('Publicar en tienda').closest('#item-k2')).toHaveClass('search-reveal'))
    expect(scroll).toHaveBeenCalled()
    expect(screen.queryByText('Editar proyecto')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/projects$/))
  })

  it('si la tarea ya no existe avisa y no hace scroll', async () => {
    mockProjects([project('p2', 'App móvil')], { p2: [task('k1', 'p2', 'Diseñar login')] })
    renderAt('/projects?open=borrada&entity=project_task&parent=p2')
    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(scroll).not.toHaveBeenCalled()
  })
})
