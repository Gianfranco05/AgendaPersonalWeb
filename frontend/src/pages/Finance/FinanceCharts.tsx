import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useTheme } from '../../context/ThemeContext';
import type { Transaction } from '../../types';

const COLORS = ['#0f172a', '#10B981', '#F59E0B', '#EF4444', '#3B82F6', '#EC4899', '#6366f1', '#14B8A6'];

interface FinanceChartsProps {
  transactions: Transaction[];
  loading: boolean;
}

export default function FinanceCharts({ transactions, loading }: FinanceChartsProps) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#2c3237' : '#f0f0f0';
  const axisColor = isDark ? '#94a3b8' : '#64748b';
  const tooltipStyle = isDark
    ? { backgroundColor: '#1b2126', border: '1px solid #2c3237', borderRadius: 8, color: '#e2e8f0' }
    : undefined;

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <LoadingSkeleton type="card" />
        <LoadingSkeleton type="card" />
      </div>
    );
  }

  // Spending by category (expenses only)
  const expensesByCategory: Record<string, number> = {};
  transactions
    .filter((t) => t.type === 'expense')
    .forEach((t) => {
      const cat = t.category_name || 'Sin categoría';
      expensesByCategory[cat] = (expensesByCategory[cat] || 0) + t.amount;
    });

  const pieData = Object.entries(expensesByCategory).map(([name, value]) => ({
    name,
    value,
  }));

  // Monthly income vs expense (last 6 months)
  const months: Record<string, { income: number; expense: number }> = {};
  const now = new Date();
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = d.toLocaleDateString('es-AR', { month: 'short', year: '2-digit' });
    months[key] = { income: 0, expense: 0 };
  }

  transactions.forEach((t) => {
    const d = new Date(t.transaction_date);
    const key = d.toLocaleDateString('es-AR', { month: 'short', year: '2-digit' });
    if (months[key]) {
      if (t.type === 'income') months[key].income += t.amount;
      else months[key].expense += t.amount;
    }
  });

  const barData = Object.entries(months).map(([name, values]) => ({
    name,
    Ingresos: values.income,
    Egresos: values.expense,
  }));

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Pie Chart */}
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
                {pieData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
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

      {/* Bar Chart */}
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
