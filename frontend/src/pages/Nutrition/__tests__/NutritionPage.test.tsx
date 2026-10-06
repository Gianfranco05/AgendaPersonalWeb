import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'

vi.mock('../../../hooks/useNutrition', () => ({
  useMeals: vi.fn(),
  removeMeal: vi.fn(),
}))
vi.mock('../MealForm', () => ({ default: () => <div>MealForm</div> }))

import { useMeals } from '../../../hooks/useNutrition'
import NutritionPage from '../NutritionPage'

const meal = (id: string, calories: number, protein_g: number) => ({
  id, date: '2026-10-06', meal_type: 'lunch' as const, name: `Comida ${id}`, calories, protein_g, carbs_g: 10.1, fat_g: 0.2,
})

beforeEach(() => {
  vi.clearAllMocks()
})

describe('NutritionPage', () => {
  it('los totales de hoy salen de las comidas listadas (no del resumen del servidor, que corta en UTC)', () => {
    vi.mocked(useMeals).mockReturnValue({
      data: [meal('a', 600, 40), meal('b', 250.5, 15)],
      isLoading: false, error: undefined, isValidating: false, mutate: vi.fn(),
    })
    renderWithProviders(<NutritionPage />)
    expect(screen.getByText('850.5')).toBeInTheDocument()
    expect(screen.getByText('55g')).toBeInTheDocument()
    // 10.1 + 10.1 y 0.2 + 0.2 sin ruido de coma flotante
    expect(screen.getByText('20.2g')).toBeInTheDocument()
    expect(screen.getByText('0.4g')).toBeInTheDocument()
  })

  it('sin comidas muestra ceros', () => {
    vi.mocked(useMeals).mockReturnValue({
      data: [], isLoading: false, error: undefined, isValidating: false, mutate: vi.fn(),
    })
    renderWithProviders(<NutritionPage />)
    expect(screen.getByText('Calorías hoy')).toBeInTheDocument()
    expect(screen.getAllByText('0g')).toHaveLength(3)
  })
})
