import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react';
import { Pin, PinOff, Trash2, Palette } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import type { Note } from '../../types';

const MDEditor = lazy(() => import('@uiw/react-md-editor'));

const NOTE_COLORS = [
  '#7C3AED', '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
  '#EC4899', '#8B5CF6', '#06B6D4', '#84CC16', '#F97316',
];

interface NoteEditorProps {
  note: Note;
  onSave: (note: Note) => void | Promise<void>;
  onDelete: (id: string) => void;
  onColorChange: (id: string, color: string) => void;
}

// El padre monta este editor con `key={note.id}`: el estado local arranca de la
// nota recibida y se reinicia solo al cambiar de nota.
export default function NoteEditor({ note, onSave, onDelete, onColorChange }: NoteEditorProps) {
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.content);
  const [showColors, setShowColors] = useState(false);

  // Refs para que el autosave no dependa de `note`/`onSave`: cambian en cada
  // guardado (el padre reemplaza la nota) y, si fueran dependencias del
  // efecto, cada guardado programaba el siguiente: un PUT por segundo para siempre.
  const noteRef = useRef(note);
  noteRef.current = note;
  const onSaveRef = useRef(onSave);
  onSaveRef.current = onSave;
  const draftRef = useRef({ title, content });
  draftRef.current = { title, content };
  const savedRef = useRef({ title: note.title, content: note.content });
  const deletedRef = useRef(false);

  const flush = useCallback(() => {
    const draft = draftRef.current;
    const saved = savedRef.current;
    if (deletedRef.current || (draft.title === saved.title && draft.content === saved.content)) return;
    savedRef.current = { title: draft.title, content: draft.content };
    Promise.resolve(
      onSaveRef.current({ ...noteRef.current, ...draft, updated_at: new Date().toISOString() }),
    ).catch(() => {
      // Si falló, se vuelve a intentar con el próximo cambio.
      savedRef.current = saved;
    });
  }, []);

  useEffect(() => {
    const timer = setTimeout(flush, 1000);
    return () => clearTimeout(timer);
  }, [title, content, flush]);

  // Al cambiar de nota (o salir de la página) no se pierde lo editado en el último segundo.
  useEffect(() => flush, [flush]);

  function handleTogglePin() {
    // Con el título/contenido en edición: guardar `note` a secas pisaba lo escrito.
    savedRef.current = { title, content };
    onSave({ ...note, title, content, is_pinned: !note.is_pinned });
  }

  function handleDelete() {
    if (window.confirm('¿Eliminar esta nota?')) {
      deletedRef.current = true;
      onDelete(note.id);
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      {/* Toolbar */}
      <div
        className="flex items-center gap-2 border-b px-4 py-2"
        style={{ borderLeftColor: note.color, borderLeftWidth: '3px' }}
      >
        <button
          onClick={handleTogglePin}
          className="rounded p-1 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
          title={note.is_pinned ? 'Desfijar' : 'Fijar'}
        >
          {note.is_pinned ? <PinOff size={16} /> : <Pin size={16} />}
        </button>

        {/* Color picker */}
        <div className="relative">
          <button
            onClick={() => setShowColors(!showColors)}
            className="rounded p-1 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-slate-200"
            title="Color"
          >
            <Palette size={16} />
          </button>
          {showColors && (
            <div className="absolute left-0 top-full z-10 mt-1 flex gap-1 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 shadow-lg">
              {NOTE_COLORS.map((color) => (
                <button
                  key={color}
                  onClick={() => {
                    onColorChange(note.id, color);
                    setShowColors(false);
                  }}
                  className="h-6 w-6 rounded-full border-2 transition-transform hover:scale-110"
                  style={{
                    backgroundColor: color,
                    borderColor: note.color === color ? '#374151' : 'transparent',
                  }}
                />
              ))}
            </div>
          )}
        </div>

        <div className="flex-1" />

        <button
          onClick={handleDelete}
          className="rounded p-1 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
          title="Eliminar"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {/* Title */}
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Título de la nota"
        className="border-b border-gray-100 dark:border-slate-800 px-4 py-3 text-lg font-semibold text-gray-800 dark:text-slate-100 outline-none placeholder:text-gray-300"
      />

      {/* Editor */}
      <div className="flex-1 overflow-hidden" data-color-mode="light">
        <Suspense fallback={<LoadingSkeleton type="card" />}>
          <MDEditor
            value={content}
            onChange={(val) => setContent(val || '')}
            height="100%"
            preview="live"
            visibleDragbar={false}
          />
        </Suspense>
      </div>

      <div className="border-t border-gray-100 dark:border-slate-800 px-4 py-2">
        <span className="text-xs text-gray-400 dark:text-slate-500">
          Última edición: {new Date(note.updated_at).toLocaleString('es-AR')}
        </span>
      </div>
    </div>
  );
}
