import { Link } from 'react-router-dom';
import { Undo2 } from 'lucide-react';

interface PublicFooterProps {
  className?: string;
}

/** Pie de página con los links legales. El "Botón de arrepentimiento" es
 *  obligatorio por la Res. 424/2020 en toda página del sitio, así que vive
 *  acá, junto a los demás links principales y con su mismo peso visual: no se
 *  puede esconder detrás de un menú ni achicar. */
export default function PublicFooter({ className = '' }: PublicFooterProps) {
  return (
    <footer
      className={`flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm ${className}`}
    >
      <Link
        to="/terms"
        className="text-gray-500 dark:text-slate-400 hover:text-brand-indigo hover:underline"
      >
        Términos y Condiciones
      </Link>
      <Link
        to="/privacy"
        className="text-gray-500 dark:text-slate-400 hover:text-brand-indigo hover:underline"
      >
        Política de Privacidad
      </Link>
      <Link
        to="/arrepentimiento"
        className="inline-flex items-center gap-1.5 font-medium text-brand-indigo hover:text-brand-indigo-hover hover:underline"
      >
        <Undo2 size={14} aria-hidden="true" />
        Botón de arrepentimiento
      </Link>
    </footer>
  );
}
