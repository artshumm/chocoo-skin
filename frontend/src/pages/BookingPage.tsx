import { useEffect, useReducer, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { getServicesCached, getSlots, createBooking, updateProfile } from "../api/client";
import type { Service, Slot, User } from "../types";
import Calendar from "../components/Calendar";
import TimeGrid from "../components/TimeGrid";
import { formatPhone, isPhoneValid, formatInstagram } from "../utils/validation";

interface Props {
  user: User;
  onUserUpdate: (u: User) => void;
}

interface RegState {
  show: boolean;
  name: string;
  phone: string;
  instagram: string;
  consent: boolean;
  loading: boolean;
  error: string;
}

type RegAction =
  | { type: "open"; name: string; phone: string; instagram: string; consent: boolean }
  | { type: "close" }
  | { type: "setName"; value: string }
  | { type: "setPhone"; value: string }
  | { type: "setInstagram"; value: string }
  | { type: "setConsent"; value: boolean }
  | { type: "submitStart" }
  | { type: "submitError"; error: string }
  | { type: "submitDone" };

function regReducer(state: RegState, action: RegAction): RegState {
  switch (action.type) {
    case "open":
      return { ...state, show: true, name: action.name, phone: action.phone, instagram: action.instagram, consent: action.consent, error: "", loading: false };
    case "close":
      return { ...state, show: false };
    case "setName":
      return { ...state, name: action.value };
    case "setPhone":
      return { ...state, phone: formatPhone(action.value) };
    case "setInstagram":
      return { ...state, instagram: formatInstagram(action.value) };
    case "setConsent":
      return { ...state, consent: action.value };
    case "submitStart":
      return { ...state, loading: true, error: "" };
    case "submitError":
      return { ...state, loading: false, error: action.error };
    case "submitDone":
      return { ...state, loading: false, show: false };
  }
}

const REMIND_OPTIONS = [
  { value: 1, label: "1ч" },
  { value: 2, label: "2ч" },
  { value: 3, label: "3ч" },
  { value: 6, label: "6ч" },
  { value: 12, label: "12ч" },
  { value: 24, label: "24ч" },
];

export default function BookingPage({ user, onUserUpdate }: Props) {
  const location = useLocation();
  const preSelectServiceId = (location.state as { serviceId?: number } | null)?.serviceId;

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

  const [reg, dispatchReg] = useReducer(regReducer, {
    show: false,
    name: user.first_name || "",
    phone: user.phone || "+",
    instagram: user.instagram || "",
    consent: user.consent_given,
    loading: false,
    error: "",
  });

  const regPhoneValid = isPhoneValid(reg.phone);
  const canSaveReg = reg.name.trim().length > 0 && regPhoneValid && reg.consent;

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
      dispatchReg({ type: "open", name: user.first_name || "", phone: user.phone || "+", instagram: user.instagram || "", consent: user.consent_given });
      return;
    }
    await doBook();
  };

  const handleRegistrationComplete = async () => {
    if (!canSaveReg) return;
    dispatchReg({ type: "submitStart" });
    try {
      const ig = reg.instagram.length > 1 ? reg.instagram : null;
      const updated = await updateProfile(reg.name.trim(), reg.phone, true, ig);
      onUserUpdate(updated);
      dispatchReg({ type: "submitDone" });
      await doBook();
    } catch (e) {
      dispatchReg({ type: "submitError", error: e instanceof Error ? e.message : "Ошибка сохранения" });
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
      {reg.show && (
        <div className="modal-overlay" onClick={() => dispatchReg({ type: "close" })}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">Для записи заполните данные</div>

            {reg.error && <div className="error-msg">{reg.error}</div>}

            <div className="profile-form">
              <div>
                <div className="profile-label">Имя</div>
                <input
                  className="profile-input"
                  type="text"
                  placeholder="Ваше имя"
                  value={reg.name}
                  onChange={(e) => dispatchReg({ type: "setName", value: e.target.value })}
                  maxLength={100}
                />
              </div>

              <div>
                <div className="profile-label">Телефон</div>
                <input
                  className="profile-input"
                  type="tel"
                  placeholder="+XXXXXXXXXXX"
                  value={reg.phone}
                  onChange={(e) => dispatchReg({ type: "setPhone", value: e.target.value })}
                  maxLength={16}
                  inputMode="tel"
                />
                {reg.phone.length > 4 && !regPhoneValid && (
                  <div className="profile-hint">Формат: +XXXXXXXXXXX (7-15 цифр после +)</div>
                )}
              </div>

              <div>
                <div className="profile-label">Instagram (необязательно)</div>
                <input
                  className="profile-input"
                  type="text"
                  placeholder="@username"
                  value={reg.instagram}
                  onChange={(e) => dispatchReg({ type: "setInstagram", value: e.target.value })}
                  maxLength={31}
                />
              </div>

              <label className="consent-label">
                <input
                  className="consent-checkbox"
                  type="checkbox"
                  checked={reg.consent}
                  onChange={(e) => dispatchReg({ type: "setConsent", value: e.target.checked })}
                />
                <span>
                  Я даю согласие на обработку персональных данных в целях оказания
                  услуг и информирования о записи.
                </span>
              </label>

              <button className="btn" onClick={handleRegistrationComplete} disabled={!canSaveReg || reg.loading}>
                {reg.loading ? "Сохраняем..." : "Сохранить и записаться"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
