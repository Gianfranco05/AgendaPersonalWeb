import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { addVehicle, editVehicle } from '../../hooks/useVehicle';
import type { Vehicle } from '../../types';

const schema = z.object({
  name: z.string().min(1, 'El nombre es requerido').max(120),
  brand: z.string().max(80).optional(),
  model: z.string().max(80).optional(),
  plate: z.string().max(20).optional(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  vehicle: Vehicle | null;
  onClose: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-vehicle focus:outline-none focus:ring-1 focus:ring-brand-vehicle';
const errorCls = 'mt-1 text-xs text-red-500';

export default function VehicleForm({ vehicle, onClose }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', brand: '', model: '', plate: '' },
  });

  useEffect(() => {
    if (vehicle) {
      reset({
        name: vehicle.name,
        brand: vehicle.brand ?? '',
        model: vehicle.model ?? '',
        plate: vehicle.plate ?? '',
      });
    }
  }, [vehicle, reset]);

  async function onSubmit(data: FormData) {
    const payload: Partial<Vehicle> = {
      name: data.name.trim(),
      brand: data.brand?.trim() || null,
      model: data.model?.trim() || null,
      plate: data.plate?.trim() || null,
    };
    if (vehicle) {
      await editVehicle(vehicle.id, payload);
    } else {
      await addVehicle(payload);
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {vehicle ? 'Editar vehículo' : 'Nuevo vehículo'}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-slate-200"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-6 py-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Nombre</label>
            <input {...register('name')} type="text" className={inputCls} placeholder="Mi Auto" />
            {errors.name && <p className={errorCls}>{errors.name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                Marca (opcional)
              </label>
              <input {...register('brand')} type="text" className={inputCls} placeholder="Toyota" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                Modelo (opcional)
              </label>
              <input {...register('model')} type="text" className={inputCls} placeholder="Corolla" />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
              Patente (opcional)
            </label>
            <input {...register('plate')} type="text" className={inputCls} placeholder="AB123CD" />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-brand-vehicle px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : vehicle ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
