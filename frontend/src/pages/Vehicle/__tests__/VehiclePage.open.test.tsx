import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts, stubScrollIntoView } from '../../../test/openParam'
import type { Vehicle, MaintenanceRecord } from '../../../types'

vi.mock('../../../hooks/useVehicle', () => ({
  useVehicles: vi.fn(),
  useVehicleSummary: vi.fn(() => ({ data: undefined })),
  useVehicleRecords: vi.fn(),
  removeVehicle: vi.fn(),
  addVehicle: vi.fn(),
  editVehicle: vi.fn(),
  addRecord: vi.fn(),
  removeRecord: vi.fn(),
}))

import { useVehicles, useVehicleRecords } from '../../../hooks/useVehicle'
import VehiclePage from '../VehiclePage'

const vehicle = (id: string, name: string): Vehicle => ({ id, name, brand: null, model: null, plate: null })
const record = (id: string, vehicle_id: string, cost: number): MaintenanceRecord =>
  ({ id, vehicle_id, record_type: 'revision', record_date: '2026-09-10', cost, odometer_km: null, notes: null })

function mockVehicles(vehicles: Vehicle[] | undefined, recordsByVehicle: Record<string, MaintenanceRecord[] | undefined> = {}) {
  vi.mocked(useVehicles).mockReturnValue({ data: vehicles, isLoading: vehicles === undefined, error: undefined } as never)
  vi.mocked(useVehicleRecords).mockImplementation(((vehicleId: string | null) => ({
    data: vehicleId ? recordsByVehicle[vehicleId] : undefined,
    isLoading: vehicleId ? recordsByVehicle[vehicleId] === undefined : false,
  })) as never)
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <VehiclePage />
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

describe('VehiclePage: ?open=<id>&entity=... desde el buscador', () => {
  it('entity=vehicle abre el formulario del vehículo y limpia la URL', async () => {
    mockVehicles([vehicle('v1', 'Auto'), vehicle('v2', 'Moto')])
    renderAt('/vehicle?open=v2&entity=vehicle')

    expect(await screen.findByText('Editar vehículo')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Moto')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/vehicle$/))
    expect(toastMessages()).toEqual([])
  })

  it('entity=maintenance expande el vehículo y resalta el registro', async () => {
    mockVehicles([vehicle('v1', 'Auto'), vehicle('v2', 'Moto')], { v2: [record('r1', 'v2', 1500), record('r2', 'v2', 98765)] })
    renderAt('/vehicle?open=r2&entity=maintenance&parent=v2')

    await waitFor(() => expect(screen.getByText('$98.765').closest('#item-r2')).toHaveClass('search-reveal'))
    expect(scroll).toHaveBeenCalled()
    expect(screen.queryByText('Editar vehículo')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/vehicle$/))
  })

  it('si el registro ya no existe avisa', async () => {
    mockVehicles([vehicle('v2', 'Moto')], { v2: [record('r1', 'v2', 1500)] })
    renderAt('/vehicle?open=borrado&entity=maintenance&parent=v2')
    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(scroll).not.toHaveBeenCalled()
  })
})
