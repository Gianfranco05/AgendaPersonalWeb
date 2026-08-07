import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

interface LegalLayoutProps {
  title: string;
  updatedAt: string;
  children: React.ReactNode;
}

/** Marco compartido de las páginas legales: son públicas, así que no pueden
 *  colgar del Layout de la app (que asume sesión iniciada). */
export default function LegalLayout({ title, updatedAt, children }: LegalLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 py-10 px-4">
      <div className="mx-auto max-w-3xl">
        <Link
          to="/login"
          className="mb-6 inline-flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 hover:text-brand-indigo"
        >
          <ArrowLeft size={16} />
          Volver
        </Link>

        <article className="rounded-xl bg-white dark:bg-slate-800 p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-gray-800 dark:text-slate-100">{title}</h1>
          <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
            Última actualización: {updatedAt}
          </p>

          <div className="mt-6 space-y-6 text-sm leading-relaxed text-gray-700 dark:text-slate-300 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-gray-800 dark:[&_h2]:text-slate-100 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1">
            {children}
          </div>
        </article>
      </div>
    </div>
  );
}
