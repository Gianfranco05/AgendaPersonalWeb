import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchVehicles,
  createVehicle,
  updateVehicle,
  deleteVehicle,
  fetchMaintenanceRecords,
  createMaintenanceRecord,
  deleteMaintenanceRecord,
  fetchVehicleSummary,
} from '../api/endpoints';
import type { MaintenanceRecord, Vehicle } from '../types';

const VEHICLES_KEY = 'vehicle/vehicles';
const SUMMARY_KEY = 'vehicle/summary';
// Sub-lista dependiente del vehículo padre, igual que `travel/items` por trip.
const recordsKey = (vehicleId: string) => ['vehicle/records', vehicleId] as const;

export function useVehicles() {
  return useApiSWR(VEHICLES_KEY, fetchVehicles);
}

export function useVehicleSummary() {
  return useApiSWR(SUMMARY_KEY, fetchVehicleSummary);
}

export function useVehicleRecords(vehicleId: string | null) {
  return useApiSWR(
    vehicleId ? recordsKey(vehicleId) : null,
    vehicleId ? () => fetchMaintenanceRecords(vehicleId) : null,
  );
}

/** Borrar un vehículo se lleva su historial, así que se revalida todo junto. */
async function revalidate(vehicleId?: string) {
  const tasks = [globalMutate(VEHICLES_KEY), globalMutate(SUMMARY_KEY)];
  if (vehicleId) tasks.push(globalMutate(recordsKey(vehicleId)));
  await Promise.all(tasks);
}

export async function addVehicle(input: Partial<Vehicle>) {
  await createVehicle(input);
  await revalidate();
}

export async function editVehicle(id: string, input: Partial<Vehicle>) {
  await updateVehicle(id, input);
  await revalidate();
}

export async function removeVehicle(id: string) {
  await deleteVehicle(id);
  await revalidate();
}

export async function addRecord(input: Partial<MaintenanceRecord>) {
  await createMaintenanceRecord(input);
  await revalidate(input.vehicle_id);
}

export async function removeRecord(id: string, vehicleId: string) {
  await deleteMaintenanceRecord(id);
  await revalidate(vehicleId);
}
