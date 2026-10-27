import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useOnboardingStore } from '../../store/onboardingStore';
import { useSettings, saveSettings } from '../../hooks/useSettings';
import { CURRENT_ONBOARDING_VERSION, ONBOARDING_STEPS, needsOnboarding } from './steps';
import { readOnboardingSeen, writeOnboardingSeen } from './onboardingStorage';

const FOCUSABLE =
  'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Tutorial de bienvenida (4 pasos). Se monta una vez en Layout: se abre solo
 * cuando `needsOnboarding` da true, y "Ver tutorial" en Configuración lo abre
 * en modo repaso (no escribe nada). Va en un portal a `document.body` porque
 * un ancestro con `transform` atraparía el `fixed`.
 */
export default function OnboardingModal() {
  const { user } = useAuthStore();
  const userId = user?.id ?? null;
  const { data: settings } = useSettings();
  const mode = useOnboardingStore((s) => s.mode);
  const dismissedFor = useOnboardingStore((s) => s.dismissedFor);
  const openWelcome = useOnboardingStore((s) => s.openWelcome);
  const close = useOnboardingStore((s) => s.close);

  const [step, setStep] = useState(0);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  // Apertura automática: solo con los ajustes conocidos y sin haberlo cerrado ya.
  useEffect(() => {
    if (mode !== null || !userId || dismissedFor === userId) return;
    if (needsOnboarding(settings, readOnboardingSeen(userId))) openWelcome();
  }, [mode, userId, dismissedFor, settings, openWelcome]);

  useEffect(() => {
    if (mode !== null) setStep(0);
  }, [mode]);

  const last = step === ONBOARDING_STEPS.length - 1;

  const finish = useCallback(() => {
    if (mode === 'welcome') {
      // Primero el respaldo local; después el server. Un error del PUT se
      // ignora: el local evita que reaparezca en este navegador.
      writeOnboardingSeen(userId, CURRENT_ONBOARDING_VERSION);
      saveSettings({ onboarding_version_seen: CURRENT_ONBOARDING_VERSION }).catch(() => {});
    }
    close(userId);
  }, [mode, userId, close]);

  // Foco: entra al diálogo y vuelve a donde estaba al cerrar.
  useEffect(() => {
    if (mode === null) return;
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    return () => previouslyFocused.current?.focus?.();
  }, [mode]);

  useEffect(() => {
    if (mode === null) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        finish();
        return;
      }
      if (e.key !== 'Tab' || !dialogRef.current) return;
      const items = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (items.length === 0) return;
      const first = items[0];
      const lastEl = items[items.length - 1];
      const active = document.activeElement;
      if (!dialogRef.current.contains(active)) {
        e.preventDefault();
        first.focus();
      } else if (e.shiftKey && active === first) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && active === lastEl) {
        e.preventDefault();
        first.focus();
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [mode, finish]);

  if (mode === null) return null;

  const current = ONBOARDING_STEPS[step];
  const Icon = current.icon;
  const total = ONBOARDING_STEPS.length;

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-800"
      >
        <p aria-live="polite" className="text-xs font-medium text-gray-500 dark:text-slate-400">
          Paso {step + 1} de {total}
        </p>

        <div className="mt-6 flex flex-col items-center text-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-brand-indigo/10 text-brand-indigo">
            <Icon size={40} aria-hidden="true" />
          </div>
          <h2
            id="onboarding-title"
            className="mt-5 text-xl font-bold text-gray-800 dark:text-slate-100"
          >
            {current.title}
          </h2>
          <div className="mt-2 space-y-1 text-sm text-gray-600 dark:text-slate-300">
            {current.body.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
        </div>

        <div className="mt-6 flex justify-center gap-1.5" aria-hidden="true">
          {ONBOARDING_STEPS.map((s, i) => (
            <span
              key={s.title}
              className={`h-1.5 rounded-full transition-all ${
                i === step ? 'w-6 bg-brand-indigo' : 'w-1.5 bg-gray-300 dark:bg-slate-600'
              }`}
            />
          ))}
        </div>

        <div className="mt-6 flex items-center justify-between gap-2">
          <div className="flex min-w-[5rem] items-center">
            {!last && (
              <button
                type="button"
                onClick={finish}
                className="rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 dark:text-slate-400 dark:hover:bg-slate-700"
              >
                Saltar
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            {step > 0 && (
              <button
                type="button"
                onClick={() => setStep((s) => s - 1)}
                className="flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700/50"
              >
                <ChevronLeft size={16} aria-hidden="true" />
                Anterior
              </button>
            )}
            {last ? (
              <button
                type="button"
                onClick={finish}
                className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white hover:bg-brand-charcoal-hover"
              >
                Empezar
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setStep((s) => s + 1)}
                className="flex items-center gap-1 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white hover:bg-brand-charcoal-hover"
              >
                Siguiente
                <ChevronRight size={16} aria-hidden="true" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
