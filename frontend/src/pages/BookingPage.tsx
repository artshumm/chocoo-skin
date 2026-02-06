import { useEffect, useRef, useState } from "react";
import { getServices, getSlots, createBooking } from "../api/client";
import type { Service, Slot } from "../types";
import Calendar from "../components/Calendar";
import TimeGrid from "../components/TimeGrid";

interface Props {
  telegramId: number;
}

export default function BookingPage({ telegramId }: Props) {
  const [services, setServices] = useState<Service[]>([]);
  const [selectedService, setSelectedService] = useState<Service | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [remindHours, setRemindHours] = useState(2);
  const bookBtnRef = useRef<HTMLButtonElement>(null);

  const REMIND_OPTIONS = [
    { value: 1, label: "1ч" },
    { value: 2, label: "2ч" },
    { value: 3, label: "3ч" },
    { value: 6, label: "6ч" },
    { value: 12, label: "12ч" },
    { value: 24, label: "24ч" },
  ];

  useEffect(() => {
    getServices().then(setServices);
  }, []);

  useEffect(() => {
    if (!selectedDate) return;
    setSelectedSlot(null);
    getSlots(selectedDate).then(setSlots);
  }, [selectedDate]);

  // Auto-scroll to book button when slot is selected
  useEffect(() => {
    if (selectedSlot && bookBtnRef.current) {
      setTimeout(() => {
        bookBtnRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 100);
    }
  }, [selectedSlot]);

  const handleBook = async () => {
    if (!selectedService || !selectedSlot) return;
    setLoading(true);
    setError("");
    try {
      await createBooking(telegramId, selectedService.id, selectedSlot.id, remindHours);
      setSuccess(`Вы записаны на ${selectedDate} в ${selectedSlot.start_time.slice(0, 5)}`);
      setSelectedSlot(null);
      setSelectedService(null);
      setSelectedDate(null);
      setSlots([]);
      setRemindHours(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка записи");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h2 className="section-title">Запись</h2>

      {error && <div className="error-msg">{error}</div>}
      {success && <div className="success-msg">{success}</div>}

      {/* Шаг 1: Услуга */}
      <div className="section-title">1. Выберите услугу</div>
      <div className="service-list">
        {services.map((s) => (
          <div
            key={s.id}
            className={`service-card${selectedService?.id === s.id ? " selected" : ""}`}
            onClick={() => {
              setSelectedService(s);
              setSuccess("");
            }}
          >
            <div className="name">{s.name}</div>
            <div className="meta">
              {s.duration_minutes} мин · {s.price} BYN
            </div>
          </div>
        ))}
        {services.length === 0 && <div className="empty-state">Услуги пока не добавлены</div>}
      </div>

      {/* Шаг 2: Дата */}
      {selectedService && (
        <>
          <div className="section-title">2. Выберите дату</div>
          <Calendar selectedDate={selectedDate} onSelect={setSelectedDate} />
        </>
      )}

      {/* Шаг 3: Время */}
      {selectedDate && (
        <>
          <div className="section-title">3. Выберите время</div>
          <TimeGrid
            slots={slots}
            selectedSlotId={selectedSlot?.id ?? null}
            onSelect={setSelectedSlot}
          />
        </>
      )}

      {/* Шаг 4: Напоминание */}
      {selectedSlot && (
        <>
          <div className="section-title">4. Напоминание</div>
          <div className="remind-grid">
            {REMIND_OPTIONS.map((opt) => (
              <div
                key={opt.value}
                className={`remind-chip${remindHours === opt.value ? " selected" : ""}`}
                onClick={() => setRemindHours(opt.value)}
              >
                {opt.label}
              </div>
            ))}
          </div>
        </>
      )}

      {/* Кнопка */}
      {selectedSlot && (
        <button ref={bookBtnRef} className="btn" onClick={handleBook} disabled={loading}>
          {loading ? "Записываем..." : `Записаться на ${selectedSlot.start_time.slice(0, 5)}`}
        </button>
      )}
    </div>
  );
}
