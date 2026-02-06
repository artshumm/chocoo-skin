import { useEffect, useState } from "react";
import { getAllSlots, generateSlots, updateSlot, getAllBookings } from "../api/client";
import type { Slot, Booking } from "../types";
import Calendar from "../components/Calendar";
import TimeGrid from "../components/TimeGrid";

interface Props {
  telegramId: number;
}

export default function AdminPage({ telegramId }: Props) {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadSlots = async (date: string) => {
    try {
      const data = await getAllSlots(date, telegramId);
      setSlots(data);
    } catch {
      setSlots([]);
    }
  };

  const loadBookings = async () => {
    try {
      const data = await getAllBookings(telegramId);
      setBookings(data);
    } catch {
      setBookings([]);
    }
  };

  useEffect(() => {
    if (selectedDate) {
      loadSlots(selectedDate);
    }
  }, [selectedDate]);

  useEffect(() => {
    loadBookings();
  }, []);

  const handleGenerate = async () => {
    if (!selectedDate) return;
    setLoading(true);
    setError("");
    try {
      await generateSlots(selectedDate, telegramId);
      setSuccess(`Слоты на ${selectedDate} созданы`);
      await loadSlots(selectedDate);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setLoading(false);
    }
  };

  const handleSlotToggle = async (slot: Slot) => {
    if (slot.status === "booked") return;
    const newStatus = slot.status === "available" ? "blocked" : "available";
    try {
      await updateSlot(slot.id, newStatus, telegramId);
      if (selectedDate) await loadSlots(selectedDate);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    }
  };

  // Filter bookings for selected date
  const dateBookings = bookings.filter(
    (b) => b.slot.date === selectedDate && b.status !== "cancelled"
  );

  return (
    <div className="page">
      <h2 className="section-title">Управление</h2>

      {error && <div className="error-msg">{error}</div>}
      {success && <div className="success-msg">{success}</div>}

      <Calendar selectedDate={selectedDate} onSelect={(d) => { setSelectedDate(d); setSuccess(""); setError(""); }} />

      {selectedDate && (
        <>
          <div className="admin-legend">
            <span><span className="legend-dot green" /> Свободен</span>
            <span><span className="legend-dot blue" /> Занят</span>
            <span><span className="legend-dot red" /> Заблокирован</span>
          </div>

          {slots.length === 0 ? (
            <div style={{ textAlign: "center", marginBottom: 16 }}>
              <div className="empty-state" style={{ padding: "20px 0" }}>
                Слоты на {selectedDate} не созданы
              </div>
              <button className="btn" onClick={handleGenerate} disabled={loading}>
                {loading ? "Создаю..." : "Создать слоты (9:00-21:00)"}
              </button>
            </div>
          ) : (
            <TimeGrid
              slots={slots}
              selectedSlotId={null}
              onSelect={handleSlotToggle}
              mode="admin"
            />
          )}

          {dateBookings.length > 0 && (
            <>
              <div className="section-title" style={{ marginTop: 16 }}>
                Записи на {selectedDate}
              </div>
              {dateBookings.map((b) => (
                <div key={b.id} className="booking-card">
                  <div className="booking-header">
                    <span className="booking-service">
                      {b.client.first_name || b.client.username || `ID ${b.client.telegram_id}`}
                    </span>
                    <span className={`booking-status ${b.status}`}>
                      {b.status === "confirmed" ? "Подтверждена" : b.status}
                    </span>
                  </div>
                  <div className="booking-datetime">
                    {b.service.name} · {b.slot.start_time.slice(0, 5)} - {b.slot.end_time.slice(0, 5)}
                  </div>
                </div>
              ))}
            </>
          )}
        </>
      )}
    </div>
  );
}
