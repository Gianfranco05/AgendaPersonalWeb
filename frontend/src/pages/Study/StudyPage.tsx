import { useState } from 'react';
import { Plus, GraduationCap, CheckCircle2, TrendingUp, Trash2, Pencil } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import ModuleLockedNotice, { isPaymentRequiredError } from '../../components/ModuleLockedNotice';
import { useSubjects, useExams, useStudySummary, removeSubject, removeExam } from '../../hooks/useStudy';
import type { Subject, Exam, SubjectStatus } from '../../types';
import SubjectForm from './SubjectForm';
import ExamForm from './ExamForm';
import { useOpenParam } from '../../hooks/useOpenParam';

const STATUS_LABELS: Record<SubjectStatus, string> = {
  cursando: 'Cursando',
  aprobada: 'Aprobada',
  pendiente: 'Pendiente',
};

const STATUS_CLASSES: Record<SubjectStatus, string> = {
  cursando: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400',
  aprobada: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400',
  pendiente: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
};

function formatDate(value: string): string {
  const [year, month, day] = value.split('-');
  return `${day}/${month}/${year}`;
}

function daysUntil(value: string): number {
  const target = new Date(`${value}T00:00:00`).getTime();
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return Math.round((target - now.getTime()) / 86_400_000);
}

export default function StudyPage() {
  const { data: subjects, isLoading: subjectsLoading, error: subjectsError } = useSubjects();
  const { data: exams, isLoading: examsLoading, error: examsError } = useExams();
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useStudySummary();

  const [subjectModal, setSubjectModal] = useState<{ open: boolean; subject: Subject | null }>({
    open: false,
    subject: null,
  });
  const [examModal, setExamModal] = useState<{ open: boolean; exam: Exam | null }>({
    open: false,
    exam: null,
  });

  // Desde el buscador: `entity` distingue materia de examen (el examen trae su
  // materia en `parent`, pero alcanza con el id para encontrarlo).
  useOpenParam({
    ready: !subjectsLoading && !examsLoading && !subjectsError && !examsError,
    onOpen: ({ id, entity }) => {
      if (entity !== 'exam') {
        const subject = subjects?.find((s) => s.id === id);
        if (subject) {
          setSubjectModal({ open: true, subject });
          return true;
        }
      }
      if (entity !== 'subject') {
        const exam = exams?.find((e) => e.id === id);
        if (exam) {
          setExamModal({ open: true, exam });
          return true;
        }
      }
      return false;
    },
  });

  if (isPaymentRequiredError(subjectsError) || isPaymentRequiredError(examsError) || isPaymentRequiredError(summaryError)) {
    return <ModuleLockedNotice moduleName="Estudio" />;
  }

  async function handleDeleteSubject(subject: Subject) {
    if (!confirm(`Se borra "${subject.name}" y todos sus exámenes. ¿Seguro?`)) return;
    await removeSubject(subject.id);
  }

  async function handleDeleteExam(exam: Exam) {
    if (!confirm(`¿Borrar "${exam.title}"?`)) return;
    await removeExam(exam.id);
  }

  const subjectsById = new Map((subjects ?? []).map((s) => [s.id, s]));
  const upcoming = (exams ?? []).filter((e) => daysUntil(e.exam_date) >= 0).sort((a, b) => (a.exam_date > b.exam_date ? 1 : -1));
  const past = (exams ?? []).filter((e) => daysUntil(e.exam_date) < 0).sort((a, b) => (a.exam_date < b.exam_date ? 1 : -1));

  const isLoading = subjectsLoading || examsLoading || summaryLoading;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Estudio</h2>
        <button
          onClick={() => setSubjectModal({ open: true, subject: null })}
          className="flex items-center gap-2 rounded-lg bg-brand-study px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <Plus size={16} />
          Nueva materia
        </button>
      </div>

      {summaryLoading && !summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      ) : summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <GraduationCap size={16} className="text-brand-study" />
              Cursando
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-study">{summary.subjects_cursando}</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <CheckCircle2 size={16} className="text-emerald-500" />
              Aprobadas
            </div>
            <p className="mt-1 text-2xl font-bold text-emerald-500">{summary.subjects_aprobadas}</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <TrendingUp size={16} className="text-brand-study" />
              Promedio
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-study">{summary.average_grade ?? '—'}</p>
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Materias */}
        <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
            Materias
          </h3>
          {isLoading ? (
            <LoadingSkeleton type="widget" />
          ) : (subjects ?? []).length === 0 ? (
            <p className="mb-3 text-sm text-gray-500 dark:text-slate-400">Todavía no cargaste ninguna materia.</p>
          ) : (
            <ul className="space-y-2">
              {(subjects ?? []).map((s) => (
                <li key={s.id} className="flex items-center justify-between gap-2 rounded-lg px-1 py-1.5">
                  <div className="flex flex-1 items-center gap-3 overflow-hidden">
                    <span className="h-8 w-1 shrink-0 rounded-full" style={{ backgroundColor: s.color }} />
                    <div className="min-w-0">
                      <p className="truncate text-sm text-gray-800 dark:text-slate-100">{s.name}</p>
                      {s.professor && (
                        <p className="truncate text-xs text-gray-500 dark:text-slate-400">{s.professor}</p>
                      )}
                    </div>
                  </div>
                  <span className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-medium ${STATUS_CLASSES[s.status]}`}>
                    {STATUS_LABELS[s.status]}
                  </span>
                  <div className="flex shrink-0 gap-1">
                    <button
                      onClick={() => setSubjectModal({ open: true, subject: s })}
                      className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-study"
                      title="Editar"
                    >
                      <Pencil size={13} />
                    </button>
                    <button
                      onClick={() => handleDeleteSubject(s)}
                      className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                      title="Eliminar"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Próximos exámenes */}
        <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
              Próximos exámenes
            </h3>
            <button
              onClick={() => setExamModal({ open: true, exam: null })}
              disabled={(subjects ?? []).length === 0}
              className="text-xs font-medium text-brand-study hover:underline disabled:pointer-events-none disabled:opacity-50"
            >
              + Agregar
            </button>
          </div>
          {isLoading ? (
            <LoadingSkeleton type="widget" />
          ) : upcoming.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-slate-400">No tenés exámenes próximos.</p>
          ) : (
            <ul className="space-y-2">
              {upcoming.map((e) => {
                const dias = daysUntil(e.exam_date);
                return (
                  <li key={e.id} className="flex items-center justify-between gap-2 rounded-lg px-1 py-1.5">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-gray-800 dark:text-slate-100">{e.title}</p>
                      <p className="truncate text-xs text-gray-500 dark:text-slate-400">
                        {subjectsById.get(e.subject_id)?.name ?? 'Materia'} · {formatDate(e.exam_date)}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 text-xs font-semibold ${
                        dias <= 3 ? 'text-rose-500' : 'text-gray-500 dark:text-slate-400'
                      }`}
                    >
                      {dias === 0 ? 'Hoy' : `En ${dias}d`}
                    </span>
                    <button
                      onClick={() => handleDeleteExam(e)}
                      className="shrink-0 rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                      title="Eliminar"
                    >
                      <Trash2 size={13} />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      {past.length > 0 && (
        <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
            Rendidos
          </h3>
          <ul className="space-y-2">
            {past.map((e) => (
              <li key={e.id} className="flex items-center justify-between gap-2 rounded-lg px-1 py-1.5">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-gray-600 dark:text-slate-300">{e.title}</p>
                  <p className="truncate text-xs text-gray-500 dark:text-slate-400">
                    {subjectsById.get(e.subject_id)?.name ?? 'Materia'} · {formatDate(e.exam_date)}
                  </p>
                </div>
                <span className="shrink-0 text-sm font-semibold text-gray-800 dark:text-slate-100">
                  {e.grade ?? '—'}
                </span>
                <button
                  onClick={() => handleDeleteExam(e)}
                  className="shrink-0 rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                  title="Eliminar"
                >
                  <Trash2 size={13} />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {subjectModal.open && (
        <SubjectForm
          subject={subjectModal.subject}
          onClose={() => setSubjectModal({ open: false, subject: null })}
          onSaved={() => setSubjectModal({ open: false, subject: null })}
        />
      )}
      {examModal.open && (
        <ExamForm
          exam={examModal.exam}
          subjects={subjects ?? []}
          onClose={() => setExamModal({ open: false, exam: null })}
          onSaved={() => setExamModal({ open: false, exam: null })}
        />
      )}
    </div>
  );
}
