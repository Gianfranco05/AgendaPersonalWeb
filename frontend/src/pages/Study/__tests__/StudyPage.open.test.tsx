import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts } from '../../../test/openParam'
import type { Subject, Exam } from '../../../types'

vi.mock('../../../hooks/useStudy', () => ({
  useSubjects: vi.fn(),
  useExams: vi.fn(),
  useStudySummary: vi.fn(() => ({ data: undefined, isLoading: false })),
  removeSubject: vi.fn(),
  removeExam: vi.fn(),
  saveSubject: vi.fn(),
  saveExam: vi.fn(),
}))

import { useSubjects, useExams } from '../../../hooks/useStudy'
import StudyPage from '../StudyPage'

const subject = (id: string, name: string): Subject => ({ id, name, professor: null, color: '#3B82F6', status: 'cursando' })
const exam = (id: string, subject_id: string, title: string): Exam => ({
  id, subject_id, title, exam_date: '2030-05-20', grade: null, notes: null,
})

function mockData(subjects: Subject[] | undefined, exams: Exam[] | undefined) {
  vi.mocked(useSubjects).mockReturnValue({ data: subjects, isLoading: subjects === undefined, error: undefined } as never)
  vi.mocked(useExams).mockReturnValue({ data: exams, isLoading: exams === undefined, error: undefined } as never)
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <StudyPage />
      <LocationProbe />
    </>,
    { router: { initialEntries: [url] } },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
})

describe('StudyPage: ?open=<id>&entity=... desde el buscador', () => {
  it('entity=subject abre el formulario de la materia y limpia la URL', async () => {
    mockData([subject('s1', 'Álgebra'), subject('s2', 'Física')], [])
    renderAt('/study?open=s2&entity=subject')

    expect(await screen.findByText('Editar materia')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Física')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/study$/))
    expect(toastMessages()).toEqual([])
  })

  it('entity=exam abre el formulario del examen (con su materia como parent)', async () => {
    mockData([subject('s1', 'Álgebra'), subject('s2', 'Física')], [exam('e1', 's1', 'Parcial 1'), exam('e2', 's2', 'Final de Física')])
    renderAt('/study?open=e2&entity=exam&parent=s2')

    expect(await screen.findByText('Editar examen')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Final de Física')).toBeInTheDocument()
    expect(screen.queryByText('Editar materia')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/study$/))
  })

  it('espera a que carguen los exámenes antes de decidir que no existe', async () => {
    mockData([subject('s1', 'Álgebra')], undefined)
    const { rerender } = renderAt('/study?open=e1&entity=exam&parent=s1')
    expect(toastMessages()).toEqual([])
    mockData([subject('s1', 'Álgebra')], [exam('e1', 's1', 'Parcial 1')])
    rerender(<><StudyPage /><LocationProbe /></>)
    expect(await screen.findByText('Editar examen')).toBeInTheDocument()
  })

  it('si el examen ya no existe avisa y no abre ningún formulario', async () => {
    mockData([subject('s1', 'Álgebra')], [])
    renderAt('/study?open=e9&entity=exam&parent=s1')

    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(screen.queryByText('Editar examen')).not.toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/study$/)
  })
})
