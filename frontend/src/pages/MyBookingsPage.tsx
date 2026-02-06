import { useEffect, useState } from "react";
import { getMyBookings, cancelBooking } from "../api/client";
import type { Booking } from "../types";
import { msUntilSlotMinsk } from "../utils/timezone";

const STATUS_LABELS: Record<string, string> = {
  confirmed: "Подтверждена",
  cancelled: "Отменена",
  completed: "Завершена",
  pending: "Ожидание",
};

const CANCEL_MIN_HOURS = 10;

/** Можно ли отменить запись (>= 10 часов до начала, время по Минску) */
function canCancel(slotDate: string, slotTime: string): boolean {
  return msUntilSlotMinsk(slotDate, slotTime) >= CANCEL_MIN_HOURS * 60 * 60 * 1000;
}

export default function MyBookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    getMyBookings()
      .then(setBookings)
      .catch(() => setError("Не удалось загрузить записи"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCancel = async (id: number) => {
    if (!window.confirm("Вы уверены, что хотите отменить запись?")) return;
    setError("");
    try {
      await cancelBooking(id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка отмены записи");
    }
  };

  if (loading) return <div className="loading">Загрузка...</div>;

  return (
    <div className="page">
      <h2 className="section-title">Мои записи</h2>

      {error && <div className="error-msg">{error}</div>}

      {bookings.length === 0 && <div className="empty-state">У вас пока нет записей</div>}

      {bookings.map((b) => {
        const cancelAllowed = b.status === "confirmed" && canCancel(b.slot.date, b.slot.start_time);

        return (
          <div key={b.id} className="booking-card">
            <div className="booking-header">
              <span className="booking-service">{b.service.name}</span>
              <span className={`booking-status ${b.status}`}>
                {STATUS_LABELS[b.status] || b.status}
              </span>
            </div>
            <div className="booking-datetime">
              {b.slot.date} · {b.slot.start_time.slice(0, 5)} - {b.slot.end_time.slice(0, 5)}
            </div>
            {b.status === "confirmed" && (
              cancelAllowed ? (
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handleCancel(b.id)}
                >
                  Отменить
                </button>
              ) : (
                <div className="cancel-note">
                  Отмена невозможна менее чем за {CANCEL_MIN_HOURS} ч.
                </div>
              )
            )}
          </div>
        );
      })}
    </div>
  );
}
