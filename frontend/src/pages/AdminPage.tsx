import { useEffect, useState } from "react";
import { getAllSlots, generateSlots, updateSlot, getAllBookings, adminCancelBooking, getScheduleTemplates } from "../api/client";
import type { Slot, Booking, ScheduleTemplate } from "../types";
import Calendar from "../components/Calendar";
import TimeGrid from "../components/TimeGrid";

/** 0=Sun, 6=Sat. Парсим YYYY-MM-DD без timezone-сдвига */
function getDayOfWeek(dateStr: string): number {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).getDay();
}

function getTemplateForDate(dateStr: string, templates: ScheduleTemplate[]): ScheduleTemplate | null {
  const dow = getDayOfWeek(dateStr);
  return templates.find(t => t.day_of_week === dow && t.is_active) || null;
}

const DEFAULT_START_H = 8, DEFAULT_START_M = 30, DEFAULT_END_H = 21, DEFAULT_END_M = 0, DEFAULT_INTERVAL = 20;

export default function AdminPage() {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [templates, setTemplates] = useState<ScheduleTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [togglingIds, setTogglingIds] = useState<Set<number>>(new Set());
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  useEffect(() => {
    getScheduleTemplates().then(setTemplates).catch(() => {});
  }, []);

  const loadSlots = async (date: string) => {
    try {
      const data = await getAllSlots(date);
      setSlots(data);
    } catch {
      setSlots([]);
    }
  };

  const loadBookings = async (date: string) => {
    try {
      const data = await getAllBookings(date);
      setBookings(data);
    } catch {
      setError("Не удалось загрузить записи");
    }
  };

  useEffect(() => {
    if (selectedDate) {
      loadSlots(selectedDate);
      loadBookings(selectedDate);
    }
  }, [selectedDate]);

  const handleGenerate = async () => {
    if (!selectedDate) return;
    const tpl = getTemplateForDate(selectedDate, templates);
    const startH = tpl ? parseInt(tpl.start_time.split(":")[0]) : DEFAULT_START_H;
    const startM = tpl ? parseInt(tpl.start_time.split(":")[1]) : DEFAULT_START_M;
    const endH = tpl ? parseInt(tpl.end_time.split(":")[0]) : DEFAULT_END_H;
    const endM = tpl ? parseInt(tpl.end_time.split(":")[1]) : DEFAULT_END_M;
    const interval = tpl ? tpl.interval_minutes : DEFAULT_INTERVAL;

    setLoading(true);
    setError("");
    try {
      await generateSlots(selectedDate, startH, startM, endH, endM, interval);
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
      await updateSlot(slot.id, newStatus);
    } catch (e) {
      setSlots((prev) => prev.map((s) => (s.id === slot.id ? { ...s, status: slot.status } : s)));
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setTogglingIds((prev) => { const next = new Set(prev); next.delete(slot.id); return next; });
    }
  };

  const handleAdminCancel = async (bookingId: number, clientName: string) => {
    if (!confirm(`Отменить запись клиента ${clientName}?`)) return;
    setCancellingId(bookingId);
    setError("");
    try {
      await adminCancelBooking(bookingId);
      setSuccess("Запись отменена");
      if (selectedDate) {
        await loadBookings(selectedDate);
        await loadSlots(selectedDate);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка отмены");
    } finally {
      setCancellingId(null);
    }
  };

  const dateBookings = bookings.filter((b) => b.status !== "cancelled");

  const tpl = selectedDate ? getTemplateForDate(selectedDate, templates) : null;
  const scheduleLabel = tpl
    ? `${tpl.start_time.slice(0, 5)}-${tpl.end_time.slice(0, 5)}`
    : `${DEFAULT_START_H}:${String(DEFAULT_START_M).padStart(2, "0")}-${DEFAULT_END_H}:${String(DEFAULT_END_M).padStart(2, "0")}`;

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
                {loading ? "Создаю..." : `Создать слоты (${scheduleLabel})`}
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
                  {b.status === "confirmed" && (
                    <button
                      className="btn btn-danger"
                      style={{ marginTop: 8, padding: "6px 12px", fontSize: 13 }}
                      disabled={cancellingId === b.id}
                      onClick={() => handleAdminCancel(b.id, b.client.first_name || b.client.username || "?")}
                    >
                      {cancellingId === b.id ? "Отмена..." : "Отменить запись"}
                    </button>
                  )}
                </div>
              ))}
            </>
          )}
        </>
      )}
    </div>
  );
}
