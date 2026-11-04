import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, act, render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockAuthStore } from '../../../test/test-utils'
import OnboardingModal from '../OnboardingModal'
import SettingsPage from '../../../pages/Settings/SettingsPage'
import { useOnboardingStore } from '../../../store/onboardingStore'
import { CURRENT_ONBOARDING_VERSION, ONBOARDING_STEPS, needsOnboarding } from '../steps'
import { readOnboardingSeen, writeOnboardingSeen } from '../onboardingStorage'

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

let settingsData: unknown
const saveSettings = vi.fn()
vi.mock('../../../hooks/useSettings', () => ({
  useSettings: () => ({ data: settingsData, isLoading: false }),
  saveSettings: (...args: unknown[]) => saveSettings(...args),
  syncGoogle: vi.fn(),
  disconnectGoogle: vi.fn(),
}))
vi.mock('../../../pages/Settings/SessionsSection', () => ({ default: () => null }))
vi.mock('../../../pages/Settings/ReminderSection', () => ({ default: () => null }))

import { useAuthStore } from '../../../store/authStore'

const base = {
  currency: 'ARS',
  theme_color: 'violet',
  date_format: 'DD/MM/YYYY',
  google_calendar_id: 'primary',
  google_connected: false,
}

function resetStore() {
  useOnboardingStore.setState({ mode: null, dismissedFor: null })
}

describe('needsOnboarding', () => {
  it('no muestra con los ajustes todavía desconocidos', () => {
    expect(needsOnboarding(undefined, 0)).toBe(false)
    expect(needsOnboarding(null, 0)).toBe(false)
  })

  it('no muestra con un backend viejo (sin el campo)', () => {
    expect(needsOnboarding({}, 0)).toBe(false)
  })

  it('muestra cuando el server dice 0 y no hay respaldo local', () => {
    expect(needsOnboarding({ onboarding_version_seen: 0 }, 0)).toBe(true)
  })

  it('no muestra si el server ya dice la versión actual', () => {
    expect(needsOnboarding({ onboarding_version_seen: CURRENT_ONBOARDING_VERSION }, 0)).toBe(false)
  })

  it('el respaldo local alcanza aunque el server siga en 0', () => {
    expect(needsOnboarding({ onboarding_version_seen: 0 }, CURRENT_ONBOARDING_VERSION)).toBe(false)
  })

  it('una versión nueva vuelve a mostrarlo', () => {
    expect(needsOnboarding({ onboarding_version_seen: CURRENT_ONBOARDING_VERSION - 1 }, 0)).toBe(true)
  })
})

describe('onboardingStorage', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => vi.restoreAllMocks())

  it('guarda por usuario y nunca baja', () => {
    writeOnboardingSeen('u1', 2)
    writeOnboardingSeen('u1', 1)
    expect(readOnboardingSeen('u1')).toBe(2)
    expect(readOnboardingSeen('u2')).toBe(0)
  })

  it('un localStorage que tira excepción no rompe', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('bloqueado')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('bloqueado')
    })
    expect(() => writeOnboardingSeen('u1', 1)).not.toThrow()
    expect(readOnboardingSeen('u1')).toBe(0)
  })
})

describe('OnboardingModal', () => {
  beforeEach(() => {
    localStorage.clear()
    resetStore()
    saveSettings.mockReset()
    saveSettings.mockResolvedValue(undefined)
    vi.mocked(useAuthStore).mockReturnValue(createMockAuthStore())
  })

  it('aparece con onboarding_version_seen = 0 y muestra Paso 1 de 4', () => {
    settingsData = { ...base, onboarding_version_seen: 0 }
    renderWithProviders(<OnboardingModal />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Paso 1 de 4')).toBeInTheDocument()
    expect(screen.getByText(ONBOARDING_STEPS[0].title)).toBeInTheDocument()
  })

  it('no aparece con la versión actual vista', () => {
    settingsData = { ...base, onboarding_version_seen: CURRENT_ONBOARDING_VERSION }
    renderWithProviders(<OnboardingModal />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('no aparece mientras los ajustes no se conocen ni con un backend viejo', () => {
    settingsData = undefined
    const { unmount } = renderWithProviders(<OnboardingModal />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    unmount()
    settingsData = { ...base }
    renderWithProviders(<OnboardingModal />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('no aparece si el respaldo local de ese usuario ya lo marca visto', () => {
    writeOnboardingSeen('1', CURRENT_ONBOARDING_VERSION)
    settingsData = { ...base, onboarding_version_seen: 0 }
    renderWithProviders(<OnboardingModal />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('Siguiente y Anterior navegan; Saltar solo en los pasos 1 a 3 y Anterior en 2 a 4', async () => {
    settingsData = { ...base, onboarding_version_seen: 0 }
    const user = userEvent.setup()
    renderWithProviders(<OnboardingModal />)
    expect(screen.queryByRole('button', { name: /anterior/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Saltar' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /siguiente/i }))
    expect(screen.getByText('Paso 2 de 4')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /siguiente/i }))
    expect(screen.getByText('Paso 3 de 4')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /anterior/i }))
    expect(screen.getByText('Paso 2 de 4')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /siguiente/i }))
    await user.click(screen.getByRole('button', { name: /siguiente/i }))
    expect(screen.getByText('Paso 4 de 4')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Saltar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /siguiente/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Empezar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /anterior/i })).toBeInTheDocument()
  })

  it('Saltar guarda el respaldo local y manda la versión al server', async () => {
    settingsData = { ...base, onboarding_version_seen: 0 }
    const user = userEvent.setup()
    renderWithProviders(<OnboardingModal />)
    await user.click(screen.getByRole('button', { name: 'Saltar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(saveSettings).toHaveBeenCalledWith({ onboarding_version_seen: CURRENT_ONBOARDING_VERSION })
    expect(readOnboardingSeen('1')).toBe(CURRENT_ONBOARDING_VERSION)
  })

  it('Empezar en el último paso cierra y lo registra', async () => {
    settingsData = { ...base, onboarding_version_seen: 0 }
    const user = userEvent.setup()
    renderWithProviders(<OnboardingModal />)
    for (let i = 0; i < 3; i++) await user.click(screen.getByRole('button', { name: /siguiente/i }))
    await user.click(screen.getByRole('button', { name: 'Empezar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(saveSettings).toHaveBeenCalledTimes(1)
    expect(readOnboardingSeen('1')).toBe(CURRENT_ONBOARDING_VERSION)
  })

  it('un error al guardar en el server se ignora y no reabre el modal', async () => {
    settingsData = { ...base, onboarding_version_seen: 0 }
    saveSettings.mockRejectedValue(new Error('500'))
    const user = userEvent.setup()
    renderWithProviders(<OnboardingModal />)
    await user.click(screen.getByRole('button', { name: 'Saltar' }))
    await act(async () => {})
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('Esc actúa como Saltar', async () => {
    settingsData = { ...base, onboarding_version_seen: 0 }
    const user = userEvent.setup()
    renderWithProviders(<OnboardingModal />)
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(saveSettings).toHaveBeenCalledWith({ onboarding_version_seen: CURRENT_ONBOARDING_VERSION })
  })

  it('el foco queda atrapado dentro del diálogo', async () => {
    settingsData = { ...base, onboarding_version_seen: 0 }
    const user = userEvent.setup()
    renderWithProviders(
      <>
        <button>afuera</button>
        <OnboardingModal />
      </>,
    )
    const dialog = screen.getByRole('dialog')
    for (let i = 0; i < 6; i++) {
      await user.tab()
      expect(dialog.contains(document.activeElement)).toBe(true)
    }
    await user.tab({ shift: true })
    expect(dialog.contains(document.activeElement)).toBe(true)
  })

  it('con localStorage roto igual se muestra y se puede cerrar', async () => {
    settingsData = { ...base, onboarding_version_seen: 0 }
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('bloqueado')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('bloqueado')
    })
    const user = userEvent.setup()
    // Sin ThemeProvider: ese contexto escribe en localStorage por su cuenta.
    try {
      render(<OnboardingModal />)
      expect(screen.getByRole('dialog')).toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Saltar' }))
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    } finally {
      vi.restoreAllMocks()
    }
  })

  it('el repaso desde Configuración abre en el paso 1 y no escribe nada', async () => {
    settingsData = { ...base, onboarding_version_seen: CURRENT_ONBOARDING_VERSION }
    const user = userEvent.setup()
    renderWithProviders(
      <>
        <SettingsPage />
        <OnboardingModal />
      </>,
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ver tutorial' }))
    expect(screen.getByText('Paso 1 de 4')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /siguiente/i }))
    await user.click(screen.getByRole('button', { name: 'Saltar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(saveSettings).not.toHaveBeenCalled()
    expect(readOnboardingSeen('1')).toBe(0)
  })
})
