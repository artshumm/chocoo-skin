import { useEffect, useState } from "react";
import { getMyBookings, cancelBooking } from "../api/client";
import type { Booking } from "../types";

interface Props {
  telegramId: number;
}

const STATUS_LABELS: Record<string, string> = {
  confirmed: "Подтверждена",
  cancelled: "Отменена",
  completed: "Завершена",
  pending: "Ожидание",
};

export default function MyBookingsPage({ telegramId }: Props) {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    getMyBookings(telegramId)
      .then(setBookings)
      .finally(() => setLoading(false));
  };

  useEffect(load, [telegramId]);

  const handleCancel = async (id: number) => {
    try {
      await cancelBooking(id, telegramId);
      load();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Ошибка");
    }
  };

  if (loading) return <div className="loading">Загрузка...</div>;

  return (
    <div className="page">
      <h2 className="section-title">Мои записи</h2>

      {bookings.length === 0 && <div className="empty-state">У вас пока нет записей</div>}

      {bookings.map((b) => (
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
            <button
              className="btn btn-danger btn-sm"
              onClick={() => handleCancel(b.id)}
            >
              Отменить
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
