import { useState } from 'react';
import { Power, Loader2 } from 'lucide-react';
import apiClient from '../../api/client';

type Feedback = { type: 'success' | 'error'; message: string } | null;

export default function InfraWidget() {
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);

  function showFeedback(fb: Feedback) {
    setFeedback(fb);
    if (fb) {
      setTimeout(() => setFeedback(null), 5000);
    }
  }

  async function handleShutdown() {
    setLoading(true);
    showFeedback(null);
    try {
      const { data } = await apiClient.post('/api/v1/infra/shutdown');
      showFeedback({ type: 'success', message: data.message ?? 'Comando enviado' });
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? String((err as { response: { data: { detail: string } } }).response.data.detail)
          : 'Error de conexión';
      showFeedback({ type: 'error', message: msg });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card-interactive rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Infraestructura</h3>
        <Power size={18} className="text-gray-400 dark:text-slate-500" />
      </div>

      {feedback && (
        <div
          className={`mb-3 rounded-lg px-3 py-2 text-xs font-medium ${
            feedback.type === 'success'
              ? 'bg-emerald-50 text-emerald-700'
              : 'bg-rose-50 text-rose-700'
          }`}
        >
          {feedback.message}
        </div>
      )}

      <button
        type="button"
        disabled={loading}
        onClick={handleShutdown}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? (
          <Loader2 size={16} className="animate-spin" />
        ) : (
          <Power size={16} />
        )}
        {loading ? 'Apagando...' : 'Apagar Dream Machine'}
      </button>
    </div>
  );
}
