import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'

vi.mock('../FinanceWidget', () => ({ default: () => <div>FinanceWidget</div> }))
vi.mock('../NotesWidget', () => ({ default: () => <div>NotesWidget</div> }))
vi.mock('../TasksWidget', () => ({ default: () => <div>TasksWidget</div> }))
vi.mock('../EventsWidget', () => ({ default: () => <div>EventsWidget</div> }))
vi.mock('../InfraWidget', () => ({ default: () => <div>InfraWidget</div> }))

import DashboardPage from '../DashboardPage'

describe('DashboardPage', () => {
  it('renders without crashing with mocked widget data', () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('FinanceWidget')).toBeInTheDocument()
    expect(screen.getByText('NotesWidget')).toBeInTheDocument()
  })
})
