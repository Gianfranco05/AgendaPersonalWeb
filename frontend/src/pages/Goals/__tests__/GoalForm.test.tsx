import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import GoalForm from '../GoalForm'
import type { Goal } from '../../../types'

const habit: Goal = {
  id: 'h1',
  title: 'Leer',
  description: null,
  goal_type: 'binary',
  target_value: 1,
  current_value: 0,
  unit: null,
  end_date: null,
  color: '#7C3AED',
  icon: 'fa-bullseye',
  is_completed: false,
  reminder_enabled: true,
  reminder_time: '07:30',
}

function renderHabit(goal: Goal | null, initialType: 'binary' | 'metric' = 'binary') {
  const onSave = vi.fn().mockResolvedValue(undefined)
  renderWithProviders(
    <GoalForm goal={goal} onClose={vi.fn()} onSave={onSave} initialType={initialType} lockType />,
  )
  return onSave
}

describe('GoalForm: aviso por hábito', () => {
  it('un hábito nuevo trae el aviso encendido y sin hora propia', async () => {
    const onSave = renderHabit(null)
    expect(screen.getByLabelText(/recordarme si no lo marqué/i)).toBeChecked()
    expect(screen.getByLabelText(/hora propia/i)).toHaveValue('')
    fireEvent.change(screen.getByPlaceholderText(/leer 12 libros/i), { target: { value: 'Tomar agua' } })
    fireEvent.click(screen.getByRole('button', { name: 'Crear' }))
    await waitFor(() => expect(onSave).toHaveBeenCalled())
    expect(onSave.mock.calls[0][0]).toMatchObject({ reminder_enabled: true, reminder_time: null })
  })

  it('manda la hora propia y la edición la carga', async () => {
    const onSave = renderHabit(habit)
    expect(screen.getByLabelText(/hora propia/i)).toHaveValue('07:30')
    fireEvent.change(screen.getByLabelText(/hora propia/i), { target: { value: '22:15' } })
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    await waitFor(() => expect(onSave).toHaveBeenCalled())
    expect(onSave.mock.calls[0][0]).toMatchObject({ reminder_enabled: true, reminder_time: '22:15' })
    expect(onSave.mock.calls[0][1]).toBe('h1')
  })

  it('vaciar la hora propia manda null (vuelve a la hora general)', async () => {
    const onSave = renderHabit(habit)
    fireEvent.change(screen.getByLabelText(/hora propia/i), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    await waitFor(() => expect(onSave).toHaveBeenCalled())
    expect(onSave.mock.calls[0][0].reminder_time).toBeNull()
  })

  it('desmarcar excluye el hábito y deshabilita la hora propia', async () => {
    const onSave = renderHabit(habit)
    fireEvent.click(screen.getByLabelText(/recordarme si no lo marqué/i))
    expect(screen.getByLabelText(/hora propia/i)).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    await waitFor(() => expect(onSave).toHaveBeenCalled())
    expect(onSave.mock.calls[0][0]).toMatchObject({ reminder_enabled: false })
  })

  it('los hábitos métricos también lo muestran', () => {
    renderHabit(null, 'metric')
    expect(screen.getByLabelText(/recordarme si no lo marqué/i)).toBeInTheDocument()
  })

  it('una meta numérica no muestra los campos ni los manda', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    renderWithProviders(<GoalForm goal={null} onClose={vi.fn()} onSave={onSave} initialType="progress" />)
    expect(screen.queryByLabelText(/recordarme si no lo marqué/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/hora propia/i)).not.toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText(/leer 12 libros/i), { target: { value: 'Correr 100 km' } })
    fireEvent.change(screen.getByPlaceholderText('100'), { target: { value: '100' } })
    fireEvent.click(screen.getByRole('button', { name: 'Crear' }))
    await waitFor(() => expect(onSave).toHaveBeenCalled())
    expect('reminder_time' in onSave.mock.calls[0][0]).toBe(false)
    expect('reminder_enabled' in onSave.mock.calls[0][0]).toBe(false)
  })
})
