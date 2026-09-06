import { useState } from 'react';
import { Car, Plus, Pencil, Trash2, ChevronDown } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import TemplateLocked, { isPaymentRequired } from '../../components/TemplateLocked';
import { useVehicles, useVehicleSummary, removeVehicle } from '../../hooks/useVehicle';
import type { Vehicle } from '../../types';
import VehicleForm from './VehicleForm';
import MaintenanceRecords from './MaintenanceRecords';

export default function VehiclePage() {
  const { data: vehicles, isLoading, error: vehiclesError } = useVehicles();
  const { data: summary, error: summaryError } = useVehicleSummary();
  const [formOpen, setFormOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState<Vehicle | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const error = vehiclesError ?? summaryError;
  if (isPaymentRequired(error)) {
    return <TemplateLocked title="Vehículo y Mantenimiento" />;
  }

  function handleNew() {
    setEditingVehicle(null);
    setFormOpen(true);
  }

  function handleEdit(vehicle: Vehicle) {
    setEditingVehicle(vehicle);
    setFormOpen(true);
  }

  async function handleDelete(vehicle: Vehicle) {
    if (!confirm(`Se borra "${vehicle.name}" y todo su historial. ¿Seguro?`)) return;
    await removeVehicle(vehicle.id);
    if (expandedId === vehicle.id) setExpandedId(null);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-2xl font-bold text-gray-800 dark:text-slate-100">
          <Car className="text-brand-vehicle" size={24} />
          Vehículo y Mantenimiento
        </h2>
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-vehicle px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <Plus size={16} />
          Nuevo vehículo
        </button>
      </div>

      {isLoading ? (
        <LoadingSkeleton type="page" />
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
              <p className="text-sm text-gray-500 dark:text-slate-400">Vehículos</p>
              <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-slate-100">
                {summary?.vehicles_total ?? 0}
              </p>
            </div>
            <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
              <p className="text-sm text-gray-500 dark:text-slate-400">Registros</p>
              <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-slate-100">
                {summary?.records_total ?? 0}
              </p>
            </div>
            <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
              <p className="text-sm text-gray-500 dark:text-slate-400">Gastado</p>
              <p className="mt-1 text-2xl font-bold text-brand-vehicle">
                ${(summary?.total_spent ?? 0).toLocaleString('es-AR')}
              </p>
            </div>
          </div>

          {(vehicles ?? []).length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
              <Car size={48} className="text-gray-300 dark:text-slate-600" />
              <p className="text-sm text-gray-500 dark:text-slate-400">Todavía no cargaste ningún vehículo</p>
              <button
                onClick={handleNew}
                className="flex items-center gap-2 rounded-lg bg-brand-vehicle px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
              >
                <Plus size={16} />
                Agregar vehículo
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {(vehicles ?? []).map((vehicle) => {
                const expanded = expandedId === vehicle.id;
                return (
                  <div key={vehicle.id} className="rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                      <button
                        onClick={() => setExpandedId(expanded ? null : vehicle.id)}
                        className="flex flex-1 items-center gap-2 text-left"
                      >
                        <ChevronDown
                          size={16}
                          className={`shrink-0 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
                        />
                        <div className="min-w-0">
                          <p className="truncate font-medium text-gray-800 dark:text-slate-100">{vehicle.name}</p>
                          {vehicle.brand || vehicle.model ? (
                            <p className="text-xs text-gray-500 dark:text-slate-400">
                              {[vehicle.brand, vehicle.model].filter(Boolean).join(' ')}
                            </p>
                          ) : null}
                        </div>
                      </button>
                      {vehicle.plate ? (
                        <span className="shrink-0 text-xs text-gray-500 dark:text-slate-400">{vehicle.plate}</span>
                      ) : null}
                      <div className="flex shrink-0 gap-1">
                        <button
                          onClick={() => handleEdit(vehicle)}
                          className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-vehicle"
                          title="Editar"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(vehicle)}
                          className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                          title="Eliminar"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    {expanded ? <MaintenanceRecords vehicleId={vehicle.id} /> : null}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {formOpen && <VehicleForm vehicle={editingVehicle} onClose={() => setFormOpen(false)} />}
    </div>
  );
}
