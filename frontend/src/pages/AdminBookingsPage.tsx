import { useEffect, useState, useCallback } from "react";
import { getAllBookings, adminCancelBooking, getAllSlots, adminRescheduleBooking } from "../api/client";
import type { Booking, Slot } from "../types";
import { todayMinsk } from "../utils/timezone";
import { ChevronLeft, ChevronRight, CalendarClock } from "lucide-react";
import Calendar from "../components/Calendar";
import TimeGrid from "../components/TimeGrid";

const STATUS_LABELS: Record<string, string> = {
  confirmed: "Подтверждена",
  cancelled: "Отменена",
  completed: "Завершена",
  pending: "Ожидание",
};

/** Сдвинуть дату на N дней: "YYYY-MM-DD" → "YYYY-MM-DD" */
function shiftDate(dateStr: string, days: number): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + days));
  return `${dt.getUTCFullYear()}-${String(dt.getUTCMonth() + 1).padStart(2, "0")}-${String(dt.getUTCDate()).padStart(2, "0")}`;
}

/** Форматировать дату: "2026-02-06" → "6 февраля, пт" */
function formatDateLabel(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  const months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"];
  const days = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"];
  return `${d} ${months[dt.getUTCMonth()]}, ${days[dt.getUTCDay()]}`;
}

/** Конвертирует UTC datetime из backend в строку Минск (UTC+3) */
function formatCreatedAtMinsk(isoStr: string): string {
  const utcMs = new Date(isoStr + "Z").getTime();
  const minskMs = utcMs + 3 * 60 * 60 * 1000;
  const d = new Date(minskMs);
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const min = String(d.getUTCMinutes()).padStart(2, "0");
  return `${dd}.${mm}.${d.getUTCFullYear()} ${hh}:${min}`;
}

export default function AdminBookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [selectedDate, setSelectedDate] = useState(todayMinsk);
  const [rescheduling, setRescheduling] = useState(false);
  const [rescheduleDate, setRescheduleDate] = useState<string | null>(null);
  const [rescheduleSlots, setRescheduleSlots] = useState<Slot[]>([]);
  const [rescheduleSlotId, setRescheduleSlotId] = useState<number | null>(null);
  const [rescheduleSlotsLoading, setRescheduleSlotsLoading] = useState(false);
  const [reschedulingId, setReschedulingId] = useState<number | null>(null);

  const today = todayMinsk();

  const load = useCallback((date: string) => {
    setLoading(true);
    setError("");
    getAllBookings(date, "confirmed")
      .then(setBookings)
      .catch(() => setError("Не удалось загрузить записи"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load(selectedDate);
  }, [selectedDate, load]);

  const handleCancel = async (bookingId: number, clientName: string) => {
    if (!confirm(`Отменить запись клиента ${clientName}?`)) return;
    setCancellingId(bookingId);
    setError("");
    try {
      await adminCancelBooking(bookingId);
      setSelectedBooking(null);
      load(selectedDate);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка отмены");
    } finally {
      setCancellingId(null);
    }
  };

  // Load available slots when reschedule date changes
  useEffect(() => {
    if (!rescheduleDate) {
      setRescheduleSlots([]);
      setRescheduleSlotId(null);
      return;
    }
    setRescheduleSlotsLoading(true);
    setRescheduleSlotId(null);
    getAllSlots(rescheduleDate)
      .then((slots) => setRescheduleSlots(slots.filter((s) => s.status === "available")))
      .catch(() => setRescheduleSlots([]))
      .finally(() => setRescheduleSlotsLoading(false));
  }, [rescheduleDate]);

  const handleReschedule = async (bookingId: number, newSlotId: number) => {
    setReschedulingId(bookingId);
    setError("");
    try {
      await adminRescheduleBooking(bookingId, newSlotId);
      setSelectedBooking(null);
      resetRescheduleState();
      load(selectedDate);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка переноса");
    } finally {
      setReschedulingId(null);
    }
  };

  const resetRescheduleState = () => {
    setRescheduling(false);
    setRescheduleDate(null);
    setRescheduleSlots([]);
    setRescheduleSlotId(null);
    setRescheduleSlotsLoading(false);
  };

  // Sort by slot time ascending
  const sorted = [...bookings].sort((a, b) =>
    a.slot.start_time.localeCompare(b.slot.start_time)
  );

  if (loading) return <div className="loading">Загрузка...</div>;

  const goPrev = () => setSelectedDate((d) => shiftDate(d, -1));
  const goNext = () => setSelectedDate((d) => shiftDate(d, 1));
  const goToday = () => setSelectedDate(today);
  const isToday = selectedDate === today;

  return (
    <div className="page">
      <div className="date-nav">
        <button className="date-nav-btn" onClick={goPrev}><ChevronLeft size={20} /></button>
        <div className="date-nav-center">
          <span className="date-nav-label">{formatDateLabel(selectedDate)}</span>
          {!isToday && (
            <button className="date-nav-today" onClick={goToday}>Сегодня</button>
          )}
        </div>
        <button className="date-nav-btn" onClick={goNext}><ChevronRight size={20} /></button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {sorted.length === 0 && (
        <div className="empty-state">Нет записей на эту дату</div>
      )}

      {sorted.map((b) => {
        const clientName = b.client.first_name || b.client.username || `ID ${b.client.telegram_id}`;
        return (
          <div
            key={b.id}
            className="booking-card"
            style={{ cursor: "pointer" }}
            onClick={() => setSelectedBooking(b)}
          >
            <div className="booking-header">
              <span className="booking-service">{clientName}</span>
              <span className={`booking-status ${b.status}`}>
                {STATUS_LABELS[b.status] || b.status}
              </span>
            </div>
            <div className="booking-datetime">
              {b.service.name} · {b.slot.start_time.slice(0, 5)} - {b.slot.end_time.slice(0, 5)}
            </div>
          </div>
        );
      })}

      {/* Модалка деталей записи */}
      {selectedBooking && (
        <div className="modal-overlay" onClick={() => { setSelectedBooking(null); resetRescheduleState(); }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            {rescheduling ? (
              <>
                <div className="modal-title">Перенос записи</div>
                <div className="detail-section">
                  <div className="detail-label">Текущее время</div>
                  <div className="detail-value">
                    {selectedBooking.slot.date}, {selectedBooking.slot.start_time.slice(0, 5)} — {selectedBooking.slot.end_time.slice(0, 5)}
                  </div>
                </div>

                <div style={{ marginTop: 12 }}>
                  <div className="detail-label" style={{ marginBottom: 8 }}>Выберите новую дату</div>
                  <Calendar
                    selectedDate={rescheduleDate}
                    onSelect={(date) => setRescheduleDate(date)}
                  />
                </div>

                {rescheduleDate && (
                  <div style={{ marginTop: 12 }}>
                    <div className="detail-label" style={{ marginBottom: 8 }}>Выберите время</div>
                    {rescheduleSlotsLoading ? (
                      <div className="loading">Загрузка слотов...</div>
                    ) : rescheduleSlots.length === 0 ? (
                      <div className="empty-state">Нет свободных слотов</div>
                    ) : (
                      <TimeGrid
                        slots={rescheduleSlots}
                        selectedSlotId={rescheduleSlotId}
                        onSelect={(slot) => setRescheduleSlotId(slot.id)}
                      />
                    )}
                  </div>
                )}

                <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
                  {rescheduleSlotId && (
                    <button
                      className="btn btn-primary"
                      disabled={reschedulingId === selectedBooking.id}
                      onClick={() => handleReschedule(selectedBooking.id, rescheduleSlotId)}
                    >
                      {reschedulingId === selectedBooking.id
                        ? "Перенос..."
                        : `Перенести на ${rescheduleSlots.find((s) => s.id === rescheduleSlotId)?.start_time.slice(0, 5) ?? ""}`}
                    </button>
                  )}
                  <button className="btn btn-outline" onClick={resetRescheduleState}>
                    Назад
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="modal-title">Детали записи</div>

                <div className="detail-section">
                  <div className="detail-label">Клиент</div>
                  <div className="detail-value">
                    {selectedBooking.client.first_name || "—"}
                    {selectedBooking.client.username && ` (@${selectedBooking.client.username})`}
                  </div>
                </div>

                <div className="detail-section">
                  <div className="detail-label">Telegram ID</div>
                  <div className="detail-value">{selectedBooking.client.telegram_id}</div>
                </div>

                <div className="detail-section">
                  <div className="detail-label">Телефон</div>
                  <div className="detail-value">
                    {selectedBooking.client.phone ? (
                      <a href={`tel:${selectedBooking.client.phone}`}>{selectedBooking.client.phone}</a>
                    ) : "—"}
                  </div>
                </div>

                <div className="detail-section">
                  <div className="detail-label">Instagram</div>
                  <div className="detail-value">
                    {selectedBooking.client.instagram ? (
                      <a href={`https://instagram.com/${selectedBooking.client.instagram.replace("@", "")}`} target="_blank" rel="noopener noreferrer">
                        {selectedBooking.client.instagram}
                      </a>
                    ) : "—"}
                  </div>
                </div>

                <div className="detail-section">
                  <div className="detail-label">Услуга</div>
                  <div className="detail-value">{selectedBooking.service.name}</div>
                </div>

                <div className="detail-section">
                  <div className="detail-label">Длительность</div>
                  <div className="detail-value">{selectedBooking.service.duration_minutes} мин</div>
                </div>

                <div className="detail-section">
                  <div className="detail-label">Цена</div>
                  <div className="detail-value">{selectedBooking.service.price} BYN</div>
                </div>

                <div className="detail-section">
                  <div className="detail-label">Дата и время</div>
                  <div className="detail-value">
                    {selectedBooking.slot.date}, {selectedBooking.slot.start_time.slice(0, 5)} — {selectedBooking.slot.end_time.slice(0, 5)}
                  </div>
                </div>

                <div className="detail-section">
                  <div className="detail-label">Статус</div>
                  <div className="detail-value">
                    <span className={`booking-status ${selectedBooking.status}`}>
                      {STATUS_LABELS[selectedBooking.status] || selectedBooking.status}
                    </span>
                  </div>
                </div>

                <div className="detail-section">
                  <div className="detail-label">Создана</div>
                  <div className="detail-value">{formatCreatedAtMinsk(selectedBooking.created_at)}</div>
                </div>

                <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
                  {selectedBooking.status === "confirmed" && (
                    <>
                      <button
                        className="btn btn-primary"
                        onClick={() => setRescheduling(true)}
                      >
                        <CalendarClock size={16} style={{ marginRight: 4, verticalAlign: "middle" }} />
                        Перенести
                      </button>
                      <button
                        className="btn btn-danger"
                        disabled={cancellingId === selectedBooking.id}
                        onClick={() =>
                          handleCancel(
                            selectedBooking.id,
                            selectedBooking.client.first_name || selectedBooking.client.username || "?"
                          )
                        }
                      >
                        {cancellingId === selectedBooking.id ? "Отмена..." : "Отменить запись"}
                      </button>
                    </>
                  )}
                  <button className="btn btn-outline" onClick={() => { setSelectedBooking(null); resetRescheduleState(); }}>
                    Закрыть
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
