import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useTheme } from '../../context/ThemeContext';
import { useFinanceReports } from '../../hooks/useFinance';

const FALLBACK_COLORS = ['#0f172a', '#10B981', '#F59E0B', '#EF4444', '#3B82F6', '#EC4899', '#6366f1', '#14B8A6'];

/**
 * Gastos por categoría + ingresos/egresos de los últimos 6 meses.
 *
 * Los datos vienen agregados por el backend (/api/v1/finance/reports) sobre
 * todo el historial. Antes se calculaban en el cliente con la página de
 * transacciones visible (máximo 20), así que con más movimientos los
 * gráficos mentían; y como la API no devuelve category_name, en modo real
 * todo caía en "Sin categoría".
 */
export default function FinanceCharts() {
  const { data: reports, isLoading } = useFinanceReports();
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#2c3237' : '#f0f0f0';
  const axisColor = isDark ? '#94a3b8' : '#64748b';
  const tooltipStyle = isDark
    ? { backgroundColor: '#1b2126', border: '1px solid #2c3237', borderRadius: 8, color: '#e2e8f0' }
    : undefined;

  if (isLoading && !reports) {
    return (
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <LoadingSkeleton type="card" />
        <LoadingSkeleton type="card" />
      </div>
    );
  }

  const pieData = (reports?.by_category ?? []).map((c) => ({ name: c.name, value: c.total, color: c.color }));
  const barData = (reports?.monthly ?? []).map((m) => ({
    // T12:00 evita que la zona horaria corra "2026-09-01" al 31 de agosto.
    name: new Date(`${m.month}T12:00:00`).toLocaleDateString('es-AR', { month: 'short', year: '2-digit' }),
    Ingresos: m.income,
    Egresos: m.expense,
  }));

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-gray-700 dark:text-slate-200">Gastos por categoría</h3>
        {pieData.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-400 dark:text-slate-500">Sin datos de gastos</p>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                dataKey="value"
              >
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.color || FALLBACK_COLORS[i % FALLBACK_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(_value: unknown) => `$${Number(_value).toLocaleString('es-AR')}`}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-gray-700 dark:text-slate-200">Ingresos vs Egresos (6 meses)</h3>
        {barData.every((d) => d.Ingresos === 0 && d.Egresos === 0) ? (
          <p className="py-8 text-center text-sm text-gray-400 dark:text-slate-500">Sin datos mensuales</p>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: axisColor }} stroke={gridColor} />
              <YAxis tick={{ fontSize: 11, fill: axisColor }} stroke={gridColor} />
              <Tooltip
                cursor={{ fill: isDark ? '#ffffff10' : '#00000008' }}
                contentStyle={tooltipStyle}
                formatter={(_value: unknown) => `$${Number(_value).toLocaleString('es-AR')}`}
              />
              <Legend />
              <Bar dataKey="Ingresos" fill="#10B981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Egresos" fill="#F43F5E" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
