import { useEffect, useState } from "react";
import {
  getSalonInfo,
  updateSalon,
  getAllServices,
  createService,
  updateService,
  deleteService,
  getFaq,
  createFaq,
  updateFaq,
  deleteFaq,
  reorderFaq,
} from "../api/client";
import type { FaqItem, SalonInfo, Service } from "../types";

// ── Salon Section ──

function SalonSection() {
  const [form, setForm] = useState<Partial<SalonInfo>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    getSalonInfo()
      .then((s) => {
        setForm(s);
      })
      .catch(() => setError("Ошибка загрузки"))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await updateSalon(form);
      setForm(updated);
      setSuccess("Сохранено");
      setTimeout(() => setSuccess(""), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="loading">Загрузка...</div>;

  return (
    <div className="cms-section">
      <h3 className="cms-section-title">Информация о салоне</h3>
      {error && <div className="error-msg">{error}</div>}
      {success && <div className="success-msg">{success}</div>}
      <div className="cms-form">
        {(
          [
            ["name", "Название"],
            ["description", "Описание"],
            ["address", "Адрес"],
            ["phone", "Телефон"],
            ["working_hours_text", "Часы работы"],
            ["instagram", "Instagram"],
            ["preparation_text", "Рекомендации по подготовке"],
          ] as const
        ).map(([key, label]) => (
          <div key={key} className="cms-field">
            <label className="cms-label">{label}</label>
            {key === "description" || key === "preparation_text" ? (
              <textarea
                className="cms-input cms-textarea"
                value={form[key] || ""}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                rows={key === "preparation_text" ? 6 : undefined}
              />
            ) : (
              <input
                className="cms-input"
                value={form[key] || ""}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            )}
          </div>
        ))}
        <button className="btn" onClick={handleSave} disabled={saving}>
          {saving ? "Сохраняем..." : "Сохранить"}
        </button>
      </div>
    </div>
  );
}

// ── Services Section ──

interface ServiceFormData {
  name: string;
  short_description: string;
  description: string;
  duration_minutes: number;
  price: number | string;
  is_active: boolean;
}

const emptyServiceForm: ServiceFormData = {
  name: "",
  short_description: "",
  description: "",
  duration_minutes: 30,
  price: "",
  is_active: true,
};

function ServicesSection() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ServiceFormData>(emptyServiceForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getAllServices()
      .then(setServices)
      .catch(() => setError("Ошибка загрузки услуг"))
      .finally(() => setLoading(false));
  }, []);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyServiceForm);
    setShowForm(true);
  };

  const openEdit = (s: Service) => {
    setEditingId(s.id);
    setForm({
      name: s.name,
      short_description: s.short_description,
      description: s.description,
      duration_minutes: s.duration_minutes,
      price: s.price,
      is_active: s.is_active,
    });
    setShowForm(true);
  };

  const handleSave = async () => {
    const price = typeof form.price === "string" ? parseFloat(form.price) : form.price;
    if (!form.name.trim() || isNaN(price) || price <= 0) {
      setError("Заполните название и цену");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const data = { ...form, price };
      if (editingId) {
        const updated = await updateService(editingId, data);
        setServices((prev) => prev.map((s) => (s.id === editingId ? updated : s)));
      } else {
        const created = await createService(data);
        setServices((prev) => [...prev, created]);
      }
      setShowForm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Деактивировать услугу?")) return;
    try {
      await deleteService(id);
      setServices((prev) => prev.map((s) => (s.id === id ? { ...s, is_active: false } : s)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    }
  };

  const handleReactivate = async (id: number) => {
    try {
      const updated = await updateService(id, { is_active: true });
      setServices((prev) => prev.map((s) => (s.id === id ? updated : s)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    }
  };

  if (loading) return <div className="loading">Загрузка...</div>;

  return (
    <div className="cms-section">
      <h3 className="cms-section-title">Услуги</h3>
      {error && <div className="error-msg">{error}</div>}

      {services.map((s) => (
        <div key={s.id} className={`cms-item ${!s.is_active ? "inactive" : ""}`}>
          <div className="cms-item-info">
            <div className="cms-item-name">
              {s.name}
              {!s.is_active && <span className="cms-badge-inactive">неактивна</span>}
            </div>
            <div className="cms-item-meta">
              {s.duration_minutes} мин &middot; {s.price} BYN
            </div>
          </div>
          <div className="cms-item-actions">
            <button className="cms-action-btn" onClick={() => openEdit(s)}>&#9998;</button>
            {s.is_active ? (
              <button className="cms-action-btn danger" onClick={() => handleDelete(s.id)}>&#10005;</button>
            ) : (
              <button className="cms-action-btn success" onClick={() => handleReactivate(s.id)}>&#10003;</button>
            )}
          </div>
        </div>
      ))}

      {showForm ? (
        <div className="cms-form" style={{ marginTop: 8 }}>
          <div className="cms-field">
            <label className="cms-label">Название</label>
            <input
              className="cms-input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div className="cms-field">
            <label className="cms-label">Краткое описание</label>
            <input
              className="cms-input"
              value={form.short_description}
              onChange={(e) => setForm({ ...form, short_description: e.target.value })}
            />
          </div>
          <div className="cms-field">
            <label className="cms-label">Описание</label>
            <textarea
              className="cms-input cms-textarea"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="cms-row">
            <div className="cms-field" style={{ flex: 1 }}>
              <label className="cms-label">Длительность (мин)</label>
              <input
                className="cms-input"
                type="number"
                value={form.duration_minutes}
                onChange={(e) => setForm({ ...form, duration_minutes: parseInt(e.target.value) || 30 })}
                inputMode="numeric"
              />
            </div>
            <div className="cms-field" style={{ flex: 1 }}>
              <label className="cms-label">Цена (BYN)</label>
              <input
                className="cms-input"
                type="number"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                inputMode="decimal"
              />
            </div>
          </div>
          <div className="cms-form-buttons">
            <button className="btn btn-sm" onClick={handleSave} disabled={saving}>
              {saving ? "..." : editingId ? "Сохранить" : "Создать"}
            </button>
            <button className="btn btn-sm btn-outline" onClick={() => setShowForm(false)}>
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <button className="btn btn-outline" style={{ marginTop: 8 }} onClick={openCreate}>
          + Добавить услугу
        </button>
      )}
    </div>
  );
}

// ── FAQ Section ──

function FaqSection() {
  const [items, setItems] = useState<FaqItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getFaq()
      .then(setItems)
      .catch(() => setError("Ошибка загрузки FAQ"))
      .finally(() => setLoading(false));
  }, []);

  const openCreate = () => {
    setEditingId(null);
    setQuestion("");
    setAnswer("");
    setShowForm(true);
  };

  const openEdit = (item: FaqItem) => {
    setEditingId(item.id);
    setQuestion(item.question);
    setAnswer(item.answer);
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!question.trim() || !answer.trim()) {
      setError("Заполните вопрос и ответ");
      return;
    }
    setSaving(true);
    setError("");
    try {
      if (editingId) {
        const updated = await updateFaq(editingId, { question, answer });
        setItems((prev) => prev.map((i) => (i.id === editingId ? updated : i)));
      } else {
        const created = await createFaq({ question, answer, order_index: items.length });
        setItems((prev) => [...prev, created]);
      }
      setShowForm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Удалить этот вопрос?")) return;
    try {
      await deleteFaq(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    }
  };

  const handleMove = async (index: number, direction: -1 | 1) => {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= items.length) return;

    const newItems = [...items];
    [newItems[index], newItems[newIndex]] = [newItems[newIndex], newItems[index]];
    setItems(newItems);

    try {
      await reorderFaq(newItems.map((i) => i.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сортировки");
      // Revert on error
      getFaq().then(setItems).catch(() => {});
    }
  };

  if (loading) return <div className="loading">Загрузка...</div>;

  return (
    <div className="cms-section">
      <h3 className="cms-section-title">FAQ</h3>
      {error && <div className="error-msg">{error}</div>}

      {items.map((item, idx) => (
        <div key={item.id} className="cms-item">
          <div className="cms-item-info" style={{ flex: 1 }}>
            <div className="cms-item-name">{item.question}</div>
            <div className="cms-item-meta">{item.answer.slice(0, 60)}{item.answer.length > 60 ? "..." : ""}</div>
          </div>
          <div className="cms-item-actions">
            <button
              className="cms-action-btn"
              onClick={() => handleMove(idx, -1)}
              disabled={idx === 0}
            >&#9650;</button>
            <button
              className="cms-action-btn"
              onClick={() => handleMove(idx, 1)}
              disabled={idx === items.length - 1}
            >&#9660;</button>
            <button className="cms-action-btn" onClick={() => openEdit(item)}>&#9998;</button>
            <button className="cms-action-btn danger" onClick={() => handleDelete(item.id)}>&#10005;</button>
          </div>
        </div>
      ))}

      {showForm ? (
        <div className="cms-form" style={{ marginTop: 8 }}>
          <div className="cms-field">
            <label className="cms-label">Вопрос</label>
            <input
              className="cms-input"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </div>
          <div className="cms-field">
            <label className="cms-label">Ответ</label>
            <textarea
              className="cms-input cms-textarea"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
            />
          </div>
          <div className="cms-form-buttons">
            <button className="btn btn-sm" onClick={handleSave} disabled={saving}>
              {saving ? "..." : editingId ? "Сохранить" : "Создать"}
            </button>
            <button className="btn btn-sm btn-outline" onClick={() => setShowForm(false)}>
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <button className="btn btn-outline" style={{ marginTop: 8 }} onClick={openCreate}>
          + Добавить вопрос
        </button>
      )}
    </div>
  );
}

// ── Main Page ──

export default function AdminSettingsPage() {
  return (
    <div className="page">
      <h2 className="section-title">Настройки</h2>
      <SalonSection />
      <ServicesSection />
      <FaqSection />
    </div>
  );
}
