import { vi } from 'vitest'
import { useLocation } from 'react-router-dom'
import { useToastStore } from '../store/toastStore'

/** Muestra la URL actual para comprobar que `?open=` se limpió. */
export function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname + location.search}</div>
}

export function toastMessages(): string[] {
  return useToastStore.getState().toasts.map((t) => t.message)
}

export function resetToasts() {
  useToastStore.setState({ toasts: [] })
}

/** jsdom no implementa scrollIntoView: lo reemplaza por un espía. */
export function stubScrollIntoView() {
  const spy = vi.fn()
  Element.prototype.scrollIntoView = spy
  return spy
}
