import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockAuthStore } from '../../test/test-utils'
import Layout from '../Layout'

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

import { useAuthStore } from '../../store/authStore'

describe('Layout', () => {
  it('renders all nav items', () => {
    vi.mocked(useAuthStore).mockReturnValue(createMockAuthStore())
    renderWithProviders(<Layout />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Finanzas')).toBeInTheDocument()
    expect(screen.getByText('Eventos')).toBeInTheDocument()
    expect(screen.getByText('Metas')).toBeInTheDocument()
    expect(screen.getByText('Notas')).toBeInTheDocument()
    expect(screen.getByText('Tareas')).toBeInTheDocument()
    expect(screen.getByText('Configuración')).toBeInTheDocument()
  })

  it('shows user initials and name', () => {
    vi.mocked(useAuthStore).mockReturnValue(
      createMockAuthStore({
        user: {
          id: '1',
          email: 'gf@test.com',
          full_name: 'Gianfranco Ferraro',
          terms_accepted_version: '1.0',
          current_terms_version: '1.0',
          age_confirmed: true,
        },
      }),
    )
    renderWithProviders(<Layout />)
    expect(screen.getByText('GF')).toBeInTheDocument()
    expect(screen.getByText('Gianfranco Ferraro')).toBeInTheDocument()
  })

  it('shows fallback for null user', () => {
    vi.mocked(useAuthStore).mockReturnValue(
      createMockAuthStore({ user: null, isAuthenticated: false }),
    )
    renderWithProviders(<Layout />)
    expect(screen.getByText('U')).toBeInTheDocument()
    expect(screen.getByText('Usuario')).toBeInTheDocument()
  })
  describe('buscador global', () => {
    it('Ctrl+K abre la paleta y Esc la cierra devolviendo el foco', async () => {
      vi.mocked(useAuthStore).mockReturnValue(createMockAuthStore())
      const user = userEvent.setup()
      renderWithProviders(<Layout />)
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

      const trigger = screen.getAllByRole('button', { name: 'Buscar' })[0]
      trigger.focus()
      const prevented = !fireEvent.keyDown(document, { key: 'k', ctrlKey: true })
      expect(prevented).toBe(true) // evita que el navegador enfoque su barra
      expect(await screen.findByRole('dialog')).toBeInTheDocument()
      expect(screen.getByRole('combobox')).toHaveFocus()

      await user.keyboard('{Escape}')
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(trigger).toHaveFocus()
    })

    it('Cmd+K también abre la paleta, aun escribiendo en un input', async () => {
      vi.mocked(useAuthStore).mockReturnValue(createMockAuthStore())
      renderWithProviders(
        <>
          <input aria-label="otro" />
          <Layout />
        </>,
      )
      screen.getByLabelText('otro').focus()
      fireEvent.keyDown(screen.getByLabelText('otro'), { key: 'K', metaKey: true })
      expect(await screen.findByRole('dialog')).toBeInTheDocument()
    })

    it('la tecla k sola no abre nada y el botón Buscar sí', async () => {
      vi.mocked(useAuthStore).mockReturnValue(createMockAuthStore())
      const user = userEvent.setup()
      renderWithProviders(<Layout />)
      fireEvent.keyDown(document, { key: 'k' })
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      await user.click(screen.getAllByRole('button', { name: 'Buscar' })[0])
      expect(await screen.findByRole('dialog')).toBeInTheDocument()
    })
  })
})
