import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchSubjects,
  createSubject,
  updateSubject,
  deleteSubject,
  fetchExams,
  createExam,
  updateExam,
  deleteExam,
  fetchStudySummary,
} from '../api/endpoints';
import type { Subject, Exam } from '../types';

const SUBJECTS_KEY = 'study/subjects';
const EXAMS_KEY = 'study/exams';
const SUMMARY_KEY = 'study/summary';

export function useSubjects() {
  return useApiSWR(SUBJECTS_KEY, fetchSubjects);
}

export function useExams(params?: Parameters<typeof fetchExams>[0]) {
  return useApiSWR([EXAMS_KEY, JSON.stringify(params ?? {})], () => fetchExams(params));
}

export function useStudySummary() {
  return useApiSWR(SUMMARY_KEY, fetchStudySummary);
}

/** Borrar una materia se lleva sus exámenes, así que se revalida todo junto. */
async function revalidate() {
  await Promise.all([
    globalMutate(SUBJECTS_KEY),
    globalMutate((key) => Array.isArray(key) && key[0] === EXAMS_KEY),
    globalMutate(SUMMARY_KEY),
  ]);
}

export async function saveSubject(subject: Subject | null, data: Partial<Subject>) {
  if (subject) {
    await updateSubject(subject.id, data);
  } else {
    await createSubject(data);
  }
  await revalidate();
}

export async function removeSubject(id: string) {
  await deleteSubject(id);
  await revalidate();
}

export async function saveExam(exam: Exam | null, data: Partial<Exam>) {
  if (exam) {
    await updateExam(exam.id, data);
  } else {
    await createExam(data);
  }
  await revalidate();
}

export async function removeExam(id: string) {
  await deleteExam(id);
  await revalidate();
}
