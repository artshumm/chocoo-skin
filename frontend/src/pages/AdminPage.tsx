import { useEffect, useState } from "react";
import { getAllSlots, generateSlots, updateSlot, getAllBookings } from "../api/client";
import type { Slot, Booking } from "../types";
import Calendar from "../components/Calendar";
import TimeGrid from "../components/TimeGrid";

interface Props {
  telegramId: number;
}

/** 0=Sun, 6=Sat. Парсим YYYY-MM-DD без timezone-сдвига */
function getDayOfWeek(dateStr: string): number {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).getDay();
}

function getScheduleForDate(dateStr: string) {
  const dow = getDayOfWeek(dateStr);
  if (dow === 0) return { isSunday: true, label: "", startHour: 0, startMinute: 0, endHour: 0, endMinute: 0 };
  if (dow === 6) return { isSunday: false, label: "8:30-16:00", startHour: 8, startMinute: 30, endHour: 16, endMinute: 0 };
  return { isSunday: false, label: "8:30-21:00", startHour: 8, startMinute: 30, endHour: 21, endMinute: 0 };
}

export default function AdminPage({ telegramId }: Props) {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [togglingIds, setTogglingIds] = useState<Set<number>>(new Set());

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
    const schedule = getScheduleForDate(selectedDate);
    if (schedule.isSunday) return;

    setLoading(true);
    setError("");
    try {
      await generateSlots(
        selectedDate,
        telegramId,
        schedule.startHour,
        schedule.startMinute,
        schedule.endHour,
        schedule.endMinute,
      );
      setSuccess(`Слоты на ${selectedDate} созданы`);
      await loadSlots(selectedDate);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setLoading(false);
    }
  };

  const handleSlotToggle = async (slot: Slot) => {
    if (slot.status === "booked" || togglingIds.has(slot.id)) return;
    const newStatus = slot.status === "available" ? "blocked" : "available";
    setTogglingIds((prev) => new Set(prev).add(slot.id));
    setSlots((prev) => prev.map((s) => (s.id === slot.id ? { ...s, status: newStatus } : s)));
    try {
      await updateSlot(slot.id, newStatus, telegramId);
    } catch (e) {
      setSlots((prev) => prev.map((s) => (s.id === slot.id ? { ...s, status: slot.status } : s)));
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setTogglingIds((prev) => { const next = new Set(prev); next.delete(slot.id); return next; });
    }
  };

  // Filter bookings for selected date
  const dateBookings = bookings.filter(
    (b) => b.slot.date === selectedDate && b.status !== "cancelled"
  );

  const schedule = selectedDate ? getScheduleForDate(selectedDate) : null;

  return (
    <div className="page">
      <h2 className="section-title">Управление</h2>

      {error && <div className="error-msg">{error}</div>}
      {success && <div className="success-msg">{success}</div>}

      <Calendar selectedDate={selectedDate} onSelect={(d) => { setSelectedDate(d); setSuccess(""); setError(""); }} />

      {selectedDate && schedule && (
        <>
          <div className="admin-legend">
            <span><span className="legend-dot green" /> Свободен</span>
            <span><span className="legend-dot blue" /> Занят</span>
            <span><span className="legend-dot red" /> Заблокирован</span>
          </div>

          {schedule.isSunday ? (
            <div className="empty-state" style={{ padding: "20px 0", textAlign: "center" }}>
              Воскресенье — выходной день
            </div>
          ) : slots.length === 0 ? (
            <div style={{ textAlign: "center", marginBottom: 16 }}>
              <div className="empty-state" style={{ padding: "20px 0" }}>
                Слоты на {selectedDate} не созданы
              </div>
              <button className="btn" onClick={handleGenerate} disabled={loading}>
                {loading ? "Создаю..." : `Создать слоты (${schedule.label})`}
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
                      {b.status === "confirmed" ? "Подтверждена" : b.status === "completed" ? "Завершена" : b.status}
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
