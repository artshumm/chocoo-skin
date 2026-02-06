import { useState } from "react";
import { updateProfile } from "../api/client";
import type { User } from "../types";

interface Props {
  user: User;
  onSave: (updated: User) => void;
  isOnboarding: boolean;
}

const PHONE_PREFIX = "+375";

export default function ProfilePage({ user, onSave, isOnboarding }: Props) {
  const [name, setName] = useState(user.first_name || "");
  const [phone, setPhone] = useState(user.phone || PHONE_PREFIX);
  const [instagram, setInstagram] = useState(user.instagram || "");
  const [consent, setConsent] = useState(user.consent_given);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handlePhoneChange = (val: string) => {
    // Ensure +375 prefix is always present
    if (!val.startsWith(PHONE_PREFIX)) {
      val = PHONE_PREFIX + val.replace(/^\+?3?7?5?/, "");
    }
    // Only digits after prefix
    const afterPrefix = val.slice(PHONE_PREFIX.length).replace(/\D/g, "");
    setPhone(PHONE_PREFIX + afterPrefix.slice(0, 9));
  };

  const isPhoneValid = /^\+375\d{9}$/.test(phone);
  const canSave = name.trim().length > 0 && isPhoneValid && consent;

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
            placeholder="+375XXXXXXXXX"
            value={phone}
            onChange={(e) => handlePhoneChange(e.target.value)}
            maxLength={13}
            inputMode="tel"
          />
          {phone.length > 4 && !isPhoneValid && (
            <div className="profile-hint">Формат: +375XXXXXXXXX (9 цифр после +375)</div>
          )}
        </div>

        <div>
          <div className="profile-label">Instagram (необязательно)</div>
          <input
            className="profile-input"
            type="text"
            placeholder="@username"
            value={instagram}
            onChange={(e) => {
              let v = e.target.value.replace(/[^A-Za-z0-9_.@]/g, "");
              if (v && !v.startsWith("@")) v = "@" + v;
              setInstagram(v);
            }}
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
