import { useState } from "react";
import { updateProfile } from "../api/client";
import type { User } from "../types";
import { formatPhone, isPhoneValid, formatInstagram } from "../utils/validation";

interface Props {
  user: User;
  onSave: (updated: User) => void;
  isOnboarding: boolean;
}

export default function ProfilePage({ user, onSave, isOnboarding }: Props) {
  const [name, setName] = useState(user.first_name || "");
  const [phone, setPhone] = useState(user.phone || "+");
  const [instagram, setInstagram] = useState(user.instagram || "");
  const [consent, setConsent] = useState(user.consent_given);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const phoneValid = isPhoneValid(phone);
  const canSave = name.trim().length > 0 && phoneValid && consent;

  const handleSave = async () => {
    if (!canSave) return;
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const updated = await updateProfile(name.trim(), phone, true, instagram || null);
      setSuccess("Данные сохранены");
      onSave(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h2 className="section-title">
        {isOnboarding ? "Заполните данные" : "Профиль"}
      </h2>

      {error && <div className="error-msg">{error}</div>}
      {success && !isOnboarding && <div className="success-msg">{success}</div>}

      <div className="profile-form">
        <div>
          <div className="profile-label">Имя</div>
          <input
            className="profile-input"
            type="text"
            placeholder="Ваше имя"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={100}
          />
        </div>

        <div>
          <div className="profile-label">Телефон</div>
          <input
            className="profile-input"
            type="tel"
            placeholder="+XXXXXXXXXXX"
            value={phone}
            onChange={(e) => setPhone(formatPhone(e.target.value))}
            maxLength={16}
            inputMode="tel"
          />
          {phone.length > 4 && !phoneValid && (
            <div className="profile-hint">Формат: +XXXXXXXXXXX (7-15 цифр после +)</div>
          )}
        </div>

        <div>
          <div className="profile-label">Instagram (необязательно)</div>
          <input
            className="profile-input"
            type="text"
            placeholder="@username"
            value={instagram}
            onChange={(e) => setInstagram(formatInstagram(e.target.value))}
            maxLength={31}
          />
        </div>

        <label className="consent-label">
          <input
            className="consent-checkbox"
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
          <span>
            Я даю согласие на обработку персональных данных в целях оказания
            услуг и информирования о записи.
          </span>
        </label>

        <button className="btn" onClick={handleSave} disabled={!canSave || loading}>
          {loading ? "Сохраняем..." : "Сохранить"}
        </button>
      </div>
    </div>
  );
}
