import { Compass, Repeat, PiggyBank, LayoutGrid, type LucideIcon } from 'lucide-react';
import type { Settings } from '../../types';

// Subir este número vuelve a mostrar el tutorial una vez a todos los usuarios.
export const CURRENT_ONBOARDING_VERSION = 1;

export interface OnboardingStep {
  title: string;
  body: string[];
  icon: LucideIcon;
}

export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    title: 'Tu Inicio',
    body: [
      'Tu día de un vistazo en el Dashboard.',
      'Desde el menú lateral entrás a cada sección.',
    ],
    icon: Compass,
  },
  {
    title: 'Hábitos',
    body: ['Marcá tus hábitos cada día, mirá tus rachas y sumá metas para lo que querés lograr.'],
    icon: Repeat,
  },
  {
    title: 'Finanzas e Inversiones',
    body: ['Registrá ingresos y gastos, armá presupuestos y seguí tus inversiones y tu patrimonio.'],
    icon: PiggyBank,
  },
  {
    title: 'Tareas, notas y tu espacio',
    body: [
      'Organizá tareas, notas y eventos.',
      'En Módulos activás plantillas para estudio, viajes, proyectos y más.',
    ],
    icon: LayoutGrid,
  },
];

/**
 * Regla única para decidir si se muestra el tutorial de bienvenida.
 *
 * - `settings` indefinido: todavía no se sabe qué vio el usuario, no se muestra a ciegas.
 * - sin `onboarding_version_seen` (backend viejo): se trata como visto; si no, aparecería
 *   en cada carga sin poder guardarse.
 * - si no, vale el mayor entre lo que dice el server y el respaldo local de este usuario.
 */
export function needsOnboarding(
  settings: Pick<Settings, 'onboarding_version_seen'> | undefined | null,
  localSeen: number,
): boolean {
  if (!settings) return false;
  const server = settings.onboarding_version_seen;
  if (typeof server !== 'number') return false;
  return Math.max(server, localSeen) < CURRENT_ONBOARDING_VERSION;
}
