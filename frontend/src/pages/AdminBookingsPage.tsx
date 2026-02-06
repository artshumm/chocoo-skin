import { useEffect, useState, useCallback } from "react";
import { getAllBookings, adminCancelBooking } from "../api/client";
import type { Booking } from "../types";
import { todayMinsk } from "../utils/timezone";

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

export default function AdminBookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [selectedDate, setSelectedDate] = useState(todayMinsk);

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
        <button className="date-nav-btn" onClick={goPrev}>&#8249;</button>
        <div className="date-nav-center">
          <span className="date-nav-label">{formatDateLabel(selectedDate)}</span>
          {!isToday && (
            <button className="date-nav-today" onClick={goToday}>Сегодня</button>
          )}
        </div>
        <button className="date-nav-btn" onClick={goNext}>&#8250;</button>
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
        <div className="modal-overlay" onClick={() => setSelectedBooking(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
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
              <div className="detail-value">{new Date(selectedBooking.created_at).toLocaleString("ru-RU")}</div>
            </div>

            <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
              {selectedBooking.status === "confirmed" && (
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
              )}
              <button className="btn btn-outline" onClick={() => setSelectedBooking(null)}>
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
