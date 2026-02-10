import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { getServicesCached, getSlots, createBooking, updateProfile } from "../api/client";
import type { Service, Slot, User } from "../types";
import Calendar from "../components/Calendar";
import TimeGrid from "../components/TimeGrid";

interface Props {
  user: User;
  onUserUpdate: (u: User) => void;
}

export default function BookingPage({ user, onUserUpdate }: Props) {
  const location = useLocation();

  // Pre-select service from "Записаться снова" navigation
  const preSelectServiceId = (location.state as { serviceId?: number } | null)?.serviceId;

  // Stale-while-revalidate: мгновенно показываем кешированные услуги
  const [servicesResult] = useState(() => getServicesCached());
  const [services, setServices] = useState<Service[]>(servicesResult.cached ?? []);
  const [selectedService, setSelectedService] = useState<Service | null>(() => {
    if (preSelectServiceId && servicesResult.cached) {
      return servicesResult.cached.find((s) => s.id === preSelectServiceId) ?? null;
    }
    return null;
  });
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [remindHours, setRemindHours] = useState(2);
  const bookBtnRef = useRef<HTMLButtonElement>(null);

  // Registration modal state
  const [showRegModal, setShowRegModal] = useState(false);
  const [regName, setRegName] = useState(user.first_name || "");
  const [regPhone, setRegPhone] = useState(user.phone || "+");
  const [regInstagram, setRegInstagram] = useState(user.instagram || "");
  const [regConsent, setRegConsent] = useState(user.consent_given);
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState("");

  const REMIND_OPTIONS = [
    { value: 1, label: "1ч" },
    { value: 2, label: "2ч" },
    { value: 3, label: "3ч" },
    { value: 6, label: "6ч" },
    { value: 12, label: "12ч" },
    { value: 24, label: "24ч" },
  ];

  // Обновляем услуги из сети в фоне
  useEffect(() => {
    servicesResult.fresh
      .then((list) => {
        setServices(list);
        if (preSelectServiceId && !selectedService) {
          const found = list.find((s) => s.id === preSelectServiceId);
          if (found) setSelectedService(found);
        }
      })
      .catch(() => {
        if (services.length === 0) setError("Не удалось загрузить услуги");
      });
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selectedDate) return;
    setSelectedSlot(null);
    setSlotsLoading(true);
    getSlots(selectedDate)
      .then(setSlots)
      .catch(() => setError("Не удалось загрузить слоты"))
      .finally(() => setSlotsLoading(false));
  }, [selectedDate]);

  // Auto-scroll to book button when slot is selected
  useEffect(() => {
    if (selectedSlot && bookBtnRef.current) {
      const timer = setTimeout(() => {
        bookBtnRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [selectedSlot]);

  const doBook = async () => {
    if (!selectedService || !selectedSlot) return;
    setLoading(true);
    setError("");
    try {
      await createBooking(selectedService.id, selectedSlot.id, remindHours);
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

  const needsRegistration = !user.consent_given || !user.phone;

  const handleBook = async () => {
    if (!selectedService || !selectedSlot) return;
    if (needsRegistration) {
      setShowRegModal(true);
      return;
    }
    await doBook();
  };

  const handlePhoneChange = (val: string) => {
    if (!val.startsWith("+")) val = "+" + val.replace(/^\+*/, "");
    const digits = val.slice(1).replace(/\D/g, "");
    setRegPhone("+" + digits.slice(0, 15));
  };

  const isPhoneValid = /^\+\d{7,15}$/.test(regPhone);
  const canSaveReg = regName.trim().length > 0 && isPhoneValid && regConsent;

  const handleInstagramChange = (val: string) => {
    // Auto-add @ and allow only Latin, digits, dots, underscores
    if (!val.startsWith("@")) val = "@" + val.replace(/^@*/, "");
    setRegInstagram(val.replace(/[^@A-Za-z0-9_.]/g, "").slice(0, 31));
  };

  const handleRegistrationComplete = async () => {
    if (!canSaveReg) return;
    setRegLoading(true);
    setRegError("");
    try {
      const ig = regInstagram.length > 1 ? regInstagram : null;
      const updated = await updateProfile(regName.trim(), regPhone, true, ig);
      onUserUpdate(updated);
      setShowRegModal(false);
      await doBook();
    } catch (e) {
      setRegError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setRegLoading(false);
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
            {s.short_description && (
              <div className="short-desc">{s.short_description}</div>
            )}
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
          {slotsLoading ? (
            <div className="loading">Загрузка слотов...</div>
          ) : (
            <TimeGrid
              slots={slots}
              selectedSlotId={selectedSlot?.id ?? null}
              onSelect={setSelectedSlot}
            />
          )}
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

      {/* Модал регистрации */}
      {showRegModal && (
        <div className="modal-overlay" onClick={() => setShowRegModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">Для записи заполните данные</div>

            {regError && <div className="error-msg">{regError}</div>}

            <div className="profile-form">
              <div>
                <div className="profile-label">Имя</div>
                <input
                  className="profile-input"
                  type="text"
                  placeholder="Ваше имя"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  maxLength={100}
                />
              </div>

              <div>
                <div className="profile-label">Телефон</div>
                <input
                  className="profile-input"
                  type="tel"
                  placeholder="+XXXXXXXXXXX"
                  value={regPhone}
                  onChange={(e) => handlePhoneChange(e.target.value)}
                  maxLength={16}
                  inputMode="tel"
                />
                {regPhone.length > 4 && !isPhoneValid && (
                  <div className="profile-hint">Формат: +XXXXXXXXXXX (7-15 цифр после +)</div>
                )}
              </div>

              <div>
                <div className="profile-label">Instagram (необязательно)</div>
                <input
                  className="profile-input"
                  type="text"
                  placeholder="@username"
                  value={regInstagram}
                  onChange={(e) => handleInstagramChange(e.target.value)}
                  maxLength={31}
                />
              </div>

              <label className="consent-label">
                <input
                  className="consent-checkbox"
                  type="checkbox"
                  checked={regConsent}
                  onChange={(e) => setRegConsent(e.target.checked)}
                />
                <span>
                  Я даю согласие на обработку персональных данных в целях оказания
                  услуг и информирования о записи.
                </span>
              </label>

              <button className="btn" onClick={handleRegistrationComplete} disabled={!canSaveReg || regLoading}>
                {regLoading ? "Сохраняем..." : "Сохранить и записаться"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
