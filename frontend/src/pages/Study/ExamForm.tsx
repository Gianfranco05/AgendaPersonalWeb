import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { saveExam } from '../../hooks/useStudy';
import type { Exam, Subject } from '../../types';
import { toLocalDateString } from '../../utils/date';

const schema = z.object({
  subject_id: z.string().min(1, 'Elegí una materia'),
  title: z.string().min(1, 'El título es requerido'),
  exam_date: z.string().min(1, 'La fecha es requerida'),
  grade: z
    .union([z.number(), z.nan()])
    .optional()
    .refine((v) => v === undefined || Number.isNaN(v) || (v >= 0 && v <= 10), 'La nota debe estar entre 0 y 10'),
});

type FormData = z.infer<typeof schema>;

interface Props {
  exam: Exam | null;
  subjects: Subject[];
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-study focus:outline-none focus:ring-1 focus:ring-brand-study';
const errorCls = 'mt-1 text-xs text-red-500';

export default function ExamForm({ exam, subjects, onClose, onSaved }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      subject_id: subjects[0]?.id ?? '',
      title: '',
      exam_date: toLocalDateString(),
      grade: undefined,
    },
  });

  useEffect(() => {
    if (exam) {
      reset({
        subject_id: exam.subject_id,
        title: exam.title,
        exam_date: exam.exam_date,
        grade: exam.grade ?? undefined,
      });
    }
  }, [exam, reset]);

  async function onSubmit(data: FormData) {
    const grade = data.grade === undefined || Number.isNaN(data.grade) ? null : data.grade;
    await saveExam(exam, { ...data, grade });
    onSaved();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {exam ? 'Editar examen' : 'Nuevo examen'}
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
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Materia</label>
            <select {...register('subject_id')} className={inputCls}>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            {errors.subject_id && <p className={errorCls}>{errors.subject_id.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Título</label>
            <input {...register('title')} type="text" className={inputCls} placeholder="Primer parcial" />
            {errors.title && <p className={errorCls}>{errors.title.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Fecha</label>
              <input {...register('exam_date')} type="date" className={inputCls} />
              {errors.exam_date && <p className={errorCls}>{errors.exam_date.message}</p>}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                Nota (opcional, 0 a 10)
              </label>
              <input
                {...register('grade', { valueAsNumber: true })}
                type="number"
                step="0.1"
                min={0}
                max={10}
                className={inputCls}
                placeholder="8.5"
              />
              {errors.grade && <p className={errorCls}>{errors.grade.message}</p>}
            </div>
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
              className="rounded-lg bg-brand-study px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : exam ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
