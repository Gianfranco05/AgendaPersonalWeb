import { useEffect, useState, useCallback, useRef } from 'react';
import { Plus } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { fetchNotes, createNote, updateNote, deleteNote, exportNotesJson } from '../../api/endpoints';
import type { Note } from '../../types';
import NotesSidebar from './NotesSidebar';
import NoteEditor from './NoteEditor';
import { parseServerTimestamp } from '../../utils/date';

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  // Solo importa en pantallas chicas (en md+ se ven lista y editor a la vez).
  const [mobileView, setMobileView] = useState<'list' | 'editor'>('list');
  // El editor guarda lo pendiente al desmontarse: si la nota se borró desde la
  // lista justo después de tipear, ese último guardado la recreaba (o daba 404).
  const deletedIdsRef = useRef<Set<string>>(new Set());

  async function handleExport() {
    setExporting(true);
    try {
      const blob = await exportNotesJson();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'notas.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  const loadNotes = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchNotes();
      setNotes(data);
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
    } finally {
      // Si falla la carga no se queda en el esqueleto para siempre.
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    loadNotes();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedNote = notes.find((n) => n.id === selectedId) || null;

  function handleNew() {
    const newNote: Note = {
      id: `temp-${Date.now()}`,
      title: 'Nueva nota',
      content: '',
      is_pinned: false,
      is_archived: false,
      color: '#7C3AED',
      tags: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    setNotes((prev) => [newNote, ...prev]);
    setSelectedId(newNote.id);
    setMobileView('editor');
  }

  function handleSelect(id: string) {
    setSelectedId(id);
    setMobileView('editor');
  }

  async function handleSave(note: Note) {
    if (deletedIdsRef.current.has(note.id)) return;
    if (note.id.startsWith('temp-')) {
      const created = await createNote({
        title: note.title,
        content: note.content,
        is_pinned: note.is_pinned,
        is_archived: note.is_archived,
        color: note.color,
        tags: note.tags,
      });
      setNotes((prev) => prev.map((n) => (n.id === note.id ? created : n)));
      setSelectedId(created.id);
    } else {
      await updateNote(note.id, {
        title: note.title,
        content: note.content,
        is_pinned: note.is_pinned,
        is_archived: note.is_archived,
        color: note.color,
        tags: note.tags,
      });
      setNotes((prev) => prev.map((n) => (n.id === note.id ? note : n)));
    }
  }

  async function handleDelete(id: string) {
    deletedIdsRef.current.add(id);
    if (!id.startsWith('temp-')) {
      try {
        await deleteNote(id);
      } catch (err) {
        // No se borró: la nota sigue viva y tiene que poder guardarse.
        deletedIdsRef.current.delete(id);
        throw err;
      }
    }
    setNotes((prev) => prev.filter((n) => n.id !== id));
    if (selectedId === id) {
      setSelectedId(null);
      setMobileView('list');
    }
  }

  async function handlePin(id: string) {
    const target = notes.find((n) => n.id === id);
    if (!target) return;
    const isPinned = !target.is_pinned;
    setNotes((prev) => prev.map((n) => (n.id === id ? { ...n, is_pinned: isPinned } : n)));
    // Antes solo cambiaba el estado local: fijar desde la lista una nota que
    // no estaba abierta en el editor se perdía al recargar.
    if (!id.startsWith('temp-')) {
      await updateNote(id, { is_pinned: isPinned });
    }
  }

  function handleColorChange(id: string, color: string) {
    setNotes((prev) => prev.map((n) => (n.id === id ? { ...n, color } : n)));
  }

  const allTags = Array.from(new Map(
    notes.flatMap((n) => n.tags).map((t) => [t.id, t])
  ).values());

  const filteredNotes = notes
    .filter((n) => {
      if (search) {
        const q = search.toLowerCase();
        const matchesTitle = n.title.toLowerCase().includes(q);
        const matchesTag = n.tags.some((t) => t.name.toLowerCase().includes(q));
        if (!matchesTitle && !matchesTag) return false;
      }
      if (activeTag && !n.tags.some((t) => t.id === activeTag)) return false;
      return true;
    })
    .sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1;
      return parseServerTimestamp(b.updated_at).getTime() - parseServerTimestamp(a.updated_at).getTime();
    });

  return (
    <div className="flex h-[calc(100vh-5rem)] gap-0 overflow-hidden rounded-xl bg-white dark:bg-slate-800 shadow-sm">
      {/* Sidebar */}
      <NotesSidebar
        notes={filteredNotes}
        tags={allTags}
        selectedId={selectedId}
        search={search}
        activeTag={activeTag}
        loading={loading}
        exporting={exporting}
        hiddenOnMobile={mobileView === 'editor'}
        onSelect={handleSelect}
        onSearchChange={setSearch}
        onTagSelect={setActiveTag}
        onPin={handlePin}
        onDelete={handleDelete}
        onNew={handleNew}
        onExport={handleExport}
      />

      {/* Editor */}
      <div className={`min-w-0 flex-1 flex-col ${mobileView === 'list' ? 'hidden md:flex' : 'flex'}`}>
        {loading ? (
          <div className="flex flex-1 items-center justify-center p-8">
            <LoadingSkeleton type="card" />
          </div>
        ) : selectedNote ? (
          <NoteEditor
            key={selectedNote.id}
            note={selectedNote}
            onBack={() => setMobileView('list')}
            onSave={handleSave}
            onDelete={handleDelete}
            onColorChange={handleColorChange}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <div className="text-center">
              <p className="text-gray-400 dark:text-slate-500">Seleccioná una nota o creá una nueva</p>
              <button
                onClick={handleNew}
                className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-indigo hover:underline"
              >
                <Plus size={14} />
                Crear nota
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
