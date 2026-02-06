import { useEffect, useMemo, useState } from "react";
import { getAllBookings, getExpenses, createExpense, deleteExpense } from "../api/client";
import type { Booking, Expense } from "../types";
import { todayMinsk, daysAgoMinsk, currentMonthMinsk } from "../utils/timezone";

const MONTH_NAMES = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
];

function formatMonthLabel(month: string): string {
  const [y, m] = month.split("-");
  return `${MONTH_NAMES[parseInt(m, 10) - 1]} ${y}`;
}

function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function formatMoney(n: number): string {
  return n.toLocaleString("ru-RU") + " BYN";
}

export default function StatsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedMonth, setSelectedMonth] = useState(currentMonthMinsk);

  // Expense form
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Load bookings once
  useEffect(() => {
    setLoading(true);
    getAllBookings()
      .then(setBookings)
      .catch(() => setError("Ошибка загрузки записей"))
      .finally(() => setLoading(false));
  }, []);

  // Load expenses when month changes
  useEffect(() => {
    getExpenses(selectedMonth)
      .then(setExpenses)
      .catch(() => setExpenses([]));
  }, [selectedMonth]);

  // Revenue calculations — memoized to avoid O(n)*9 on each render
  const revenueBookings = useMemo(
    () => bookings.filter((b) => b.status === "confirmed" || b.status === "completed"),
    [bookings],
  );

  const today = todayMinsk();
  const weekStart = daysAgoMinsk(6);
  const monthStart = daysAgoMinsk(29);

  const { todayBookings, todayRevenue, weekBookings, weekRevenue, monthBookings, monthRevenue } =
    useMemo(() => {
      const tb = revenueBookings.filter((b) => b.slot.date === today);
      const wb = revenueBookings.filter((b) => b.slot.date >= weekStart && b.slot.date <= today);
      const mb = revenueBookings.filter((b) => b.slot.date >= monthStart && b.slot.date <= today);
      return {
        todayBookings: tb,
        todayRevenue: tb.reduce((s, b) => s + b.service.price, 0),
        weekBookings: wb,
        weekRevenue: wb.reduce((s, b) => s + b.service.price, 0),
        monthBookings: mb,
        monthRevenue: mb.reduce((s, b) => s + b.service.price, 0),
      };
    }, [revenueBookings, today, weekStart, monthStart]);

  // Client stats for selected month
  const { totalClients, newClients, returningClients, monthCancelled, selectedMonthRevenue } =
    useMemo(() => {
      const monthClientBookings = revenueBookings.filter((b) => b.slot.date.startsWith(selectedMonth));
      const monthClientIds = new Set(monthClientBookings.map((b) => b.client.telegram_id));

      // First ever booking month per client
      const firstBookingMonth = new Map<number, string>();
      for (const b of revenueBookings) {
        const m = b.slot.date.slice(0, 7);
        const prev = firstBookingMonth.get(b.client.telegram_id);
        if (!prev || m < prev) firstBookingMonth.set(b.client.telegram_id, m);
      }

      const nc = [...monthClientIds].filter((id) => firstBookingMonth.get(id) === selectedMonth).length;
      const cancelled = bookings.filter(
        (b) => b.status === "cancelled" && b.slot.date.startsWith(selectedMonth),
      ).length;
      const smRevenue = monthClientBookings.reduce((s, b) => s + b.service.price, 0);

      return {
        totalClients: monthClientIds.size,
        newClients: nc,
        returningClients: monthClientIds.size - nc,
        monthCancelled: cancelled,
        selectedMonthRevenue: smRevenue,
      };
    }, [revenueBookings, bookings, selectedMonth]);

  // Expenses
  const expensesTotal = useMemo(() => expenses.reduce((s, e) => s + e.amount, 0), [expenses]);
  const netProfit = selectedMonthRevenue - expensesTotal;

  const handleAddExpense = async () => {
    const amount = parseFloat(newAmount);
    if (!newName.trim() || isNaN(amount) || amount <= 0) return;
    setSubmitting(true);
    setError("");
    try {
      const created = await createExpense(newName.trim(), amount, selectedMonth);
      setExpenses((prev) => [created, ...prev]);
      setNewName("");
      setNewAmount("");
      setShowForm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteExpense = async (id: number) => {
    if (!window.confirm("Удалить этот расход?")) return;
    try {
      await deleteExpense(id);
      setExpenses((prev) => prev.filter((e) => e.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    }
  };

  if (loading) return <div className="loading">Загрузка...</div>;

  return (
    <div className="page">
      <h2 className="section-title">Статистика</h2>

      {error && <div className="error-msg">{error}</div>}

      {/* Month navigation */}
      <div className="month-nav">
        <button onClick={() => setSelectedMonth(shiftMonth(selectedMonth, -1))}>&#8249;</button>
        <span>{formatMonthLabel(selectedMonth)}</span>
        <button onClick={() => setSelectedMonth(shiftMonth(selectedMonth, 1))}>&#8250;</button>
      </div>

      {/* Revenue cards */}
      <div className="stats-cards">
        <div className="stats-card">
          <div className="stats-card-label">Сегодня</div>
          <div className="stats-card-value">{formatMoney(todayRevenue)}</div>
          <div className="stats-card-count">{todayBookings.length} зап.</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-label">Неделя</div>
          <div className="stats-card-value">{formatMoney(weekRevenue)}</div>
          <div className="stats-card-count">{weekBookings.length} зап.</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-label">Месяц</div>
          <div className="stats-card-value">{formatMoney(monthRevenue)}</div>
          <div className="stats-card-count">{monthBookings.length} зап.</div>
        </div>
      </div>

      {/* Client stats */}
      <div className="section-title" style={{ marginTop: 4 }}>
        Клиенты за {formatMonthLabel(selectedMonth)}
      </div>
      <div className="stats-cards">
        <div className="stats-card">
          <div className="stats-card-label">Всего</div>
          <div className="stats-card-value">{totalClients}</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-label">Новые</div>
          <div className="stats-card-value">{newClients}</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-label">Постоянные</div>
          <div className="stats-card-value">{returningClients}</div>
        </div>
      </div>

      {/* Cancellations */}
      {monthCancelled > 0 && (
        <div className="stats-cancellations">
          Отмены за {formatMonthLabel(selectedMonth)}: <strong>{monthCancelled}</strong>
        </div>
      )}

      {/* Expenses section */}
      <div className="section-title" style={{ marginTop: 20 }}>
        Расходы за {formatMonthLabel(selectedMonth)}
      </div>

      {expenses.length === 0 && !showForm && (
        <div className="empty-state" style={{ padding: "16px 0" }}>Расходов пока нет</div>
      )}

      {expenses.map((exp) => (
        <div key={exp.id} className="expense-row">
          <div className="expense-info">
            <span className="expense-name">{exp.name}</span>
            <span className="expense-amount">{formatMoney(exp.amount)}</span>
          </div>
          <button className="expense-delete" onClick={() => handleDeleteExpense(exp.id)}>
            &#10005;
          </button>
        </div>
      ))}

      {expenses.length > 0 && (
        <div className="expense-total">
          Итого: <strong>{formatMoney(expensesTotal)}</strong>
        </div>
      )}

      {showForm ? (
        <div className="expense-form">
          <input
            className="expense-input"
            type="text"
            placeholder="Название"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <input
            className="expense-input"
            type="number"
            placeholder="Сумма"
            value={newAmount}
            onChange={(e) => setNewAmount(e.target.value)}
            inputMode="decimal"
          />
          <div className="expense-form-buttons">
            <button className="btn btn-sm" onClick={handleAddExpense} disabled={submitting}>
              {submitting ? "..." : "Сохранить"}
            </button>
            <button
              className="btn btn-sm btn-outline"
              onClick={() => { setShowForm(false); setNewName(""); setNewAmount(""); }}
            >
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <button className="btn btn-outline" style={{ marginTop: 8 }} onClick={() => setShowForm(true)}>
          + Добавить расход
        </button>
      )}

      {/* Net profit */}
      <div className={`stats-profit ${netProfit >= 0 ? "positive" : "negative"}`}>
        <div className="stats-profit-label">Чистая прибыль за {formatMonthLabel(selectedMonth)}</div>
        <div className="stats-profit-value">{formatMoney(netProfit)}</div>
      </div>
    </div>
  );
}
