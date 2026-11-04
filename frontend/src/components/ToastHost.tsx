import { useToastStore } from '../store/toastStore';

/** Avisos cortos (p. ej. "Ese elemento ya no existe"). Se monta una vez en el Layout. */
export default function ToastHost() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);
  if (toasts.length === 0) return null;
  return (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-4 z-[70] flex flex-col items-center gap-2 px-4"
      role="status"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <button
          key={t.id}
          type="button"
          onClick={() => dismiss(t.id)}
          className="pointer-events-auto animate-fade-in rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white shadow-lg"
        >
          {t.message}
        </button>
      ))}
    </div>
  );
}
