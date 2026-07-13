import { useState } from 'react';
import { Plus } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useEvents, addEvent, editEvent, removeEvent } from '../../hooks/useEvents';
import type { CalendarEvent } from '../../types';
import CalendarGrid from './CalendarGrid';
import EventList from './EventList';
import EventForm from './EventForm';

export default function EventsPage() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth());
  const [showForm, setShowForm] = useState(false);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);

  const { data: events, isLoading, mutate } = useEvents();

  function handlePrevMonth() {
    if (month === 0) { setYear((y) => y - 1); setMonth(11); }
    else setMonth((m) => m - 1);
  }

  function handleNextMonth() {
    if (month === 11) { setYear((y) => y + 1); setMonth(0); }
    else setMonth((m) => m + 1);
  }

  function handleDayClick() {
    setEditingEvent(null);
    setShowForm(true);
  }

  function handleEdit(event: CalendarEvent) {
    setEditingEvent(event);
    setShowForm(true);
  }

  async function handleDelete(id: string) {
    await removeEvent(id);
    await mutate();
  }

  async function handleSave(data: Omit<CalendarEvent, 'id'>, id?: string) {
    if (id) {
      await editEvent(id, data);
    } else {
      await addEvent(data);
    }
    await mutate();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Eventos</h2>
        <button
          onClick={() => { setEditingEvent(null); setShowForm(true); }}
          className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
        >
          <Plus size={16} />
          Nuevo evento
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <LoadingSkeleton type="card" />
          </div>
          <LoadingSkeleton type="card" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <CalendarGrid
              year={year}
              month={month}
              events={events ?? []}
              onPrevMonth={handlePrevMonth}
              onNextMonth={handleNextMonth}
              onDayClick={handleDayClick}
            />
          </div>
          <EventList
            events={events ?? []}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        </div>
      )}

      {showForm && (
        <EventForm
          event={editingEvent}
          onClose={() => { setShowForm(false); setEditingEvent(null); }}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
