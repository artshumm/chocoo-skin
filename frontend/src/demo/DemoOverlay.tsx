import { useState, useEffect, useCallback } from "react";
import {
  Scissors,
  Sparkles,
  Heart,
  Stethoscope,
  Wrench,
  Droplets,
  Camera,
  GraduationCap,
  Monitor,
  Wind,
  ChevronDown,
  ChevronUp,
  Plus,
  Trash2,
  RotateCcw,
  UserCog,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import "./DemoOverlay.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DemoOverlayProps {
  isAdmin: boolean;
  onSwitchRole: () => void;
  onPresetApplied: () => void;
}

interface PresetConfig {
  key: string;
  label: string;
  Icon: LucideIcon;
}

interface CustomService {
  name: string;
  price: string;
  duration: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PRESETS: PresetConfig[] = [
  { key: "barbershop", label: "Барбершоп", Icon: Scissors },
  { key: "beauty", label: "Салон красоты", Icon: Sparkles },
  { key: "massage", label: "Массаж", Icon: Heart },
  { key: "dental", label: "Стоматология", Icon: Stethoscope },
  { key: "auto_service", label: "Автосервис", Icon: Wrench },
  { key: "car_wash", label: "Автомойка", Icon: Droplets },
  { key: "photo", label: "Фотостудия", Icon: Camera },
  { key: "tutor", label: "Репетитор", Icon: GraduationCap },
  { key: "gaming", label: "Комп. клуб", Icon: Monitor },
  { key: "hookah", label: "Кальянная", Icon: Wind },
];

const API_BASE = import.meta.env.VITE_API_URL || "";

const EMPTY_SERVICE: CustomService = { name: "", price: "", duration: "" };

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------

async function resetDemo(body: Record<string, unknown>): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/demo/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      (err as { detail?: string }).detail || "Reset failed"
    );
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DemoOverlay({
  isAdmin,
  onSwitchRole,
  onPresetApplied,
}: DemoOverlayProps) {
  const [expanded, setExpanded] = useState(false);
  const [activePreset, setActivePreset] = useState<string>("barbershop");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Custom business form state
  const [showCustom, setShowCustom] = useState(false);
  const [customName, setCustomName] = useState("");
  const [customAddress, setCustomAddress] = useState("");
  const [customServices, setCustomServices] = useState<CustomService[]>([
    { ...EMPTY_SERVICE },
  ]);

  // Add demo-mode class to body so content is offset below the bar
  useEffect(() => {
    document.body.classList.add("demo-mode");
    return () => {
      document.body.classList.remove("demo-mode");
    };
  }, []);

  // Auto-dismiss error after 3 seconds
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setError(""), 3000);
    return () => clearTimeout(timer);
  }, [error]);

  // ----- Preset click handler -----
  const handlePresetClick = useCallback(
    async (presetKey: string) => {
      if (loading) return;
      setLoading(true);
      setError("");
      try {
        await resetDemo({ preset: presetKey });
        setActivePreset(presetKey);
        setExpanded(false);
        setShowCustom(false);
        onPresetApplied();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка сброса");
      } finally {
        setLoading(false);
      }
    },
    [loading, onPresetApplied]
  );

  // ----- Custom form handlers -----
  const updateService = useCallback(
    (index: number, field: keyof CustomService, value: string) => {
      setCustomServices((prev) => {
        const next = [...prev];
        next[index] = { ...next[index], [field]: value };
        return next;
      });
    },
    []
  );

  const addService = useCallback(() => {
    setCustomServices((prev) => [...prev, { ...EMPTY_SERVICE }]);
  }, []);

  const removeService = useCallback((index: number) => {
    setCustomServices((prev) => {
      if (prev.length <= 1) return prev; // keep at least one row
      return prev.filter((_, i) => i !== index);
    });
  }, []);

  const handleCustomSubmit = useCallback(async () => {
    if (loading) return;
    if (!customName.trim()) {
      setError("Введите название бизнеса");
      return;
    }

    const validServices = customServices.filter(
      (s) => s.name.trim() && Number(s.price) > 0
    );
    if (validServices.length === 0) {
      setError("Добавьте хотя бы одну услугу с ценой");
      return;
    }

    setLoading(true);
    setError("");
    try {
      await resetDemo({
        custom: {
          name: customName.trim(),
          address: customAddress.trim() || undefined,
          services: validServices.map((s) => ({
            name: s.name.trim(),
            price: Number(s.price),
            duration_minutes: Number(s.duration) || 30,
          })),
        },
      });
      setActivePreset("custom");
      setExpanded(false);
      onPresetApplied();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка сброса");
    } finally {
      setLoading(false);
    }
  }, [loading, customName, customAddress, customServices, onPresetApplied]);

  // Find label for current preset
  const presetLabel =
    activePreset === "custom"
      ? customName || "Своё"
      : PRESETS.find((p) => p.key === activePreset)?.label ?? activePreset;

  return (
    <>
      {/* ---------- Top bar ---------- */}
      <div className="demo-bar">
        <span className="demo-badge">DEMO</span>
        <span className="demo-preset-name">{presetLabel}</span>

        <button
          type="button"
          className="demo-role-btn"
          onClick={onSwitchRole}
          aria-label={
            isAdmin ? "Переключить на клиента" : "Переключить на админа"
          }
        >
          <UserCog size={14} />
          {isAdmin ? "Админ" : "Клиент"}
        </button>

        <button
          type="button"
          className="demo-expand-btn"
          onClick={() => setExpanded((prev) => !prev)}
          aria-label={expanded ? "Свернуть панель" : "Развернуть панель"}
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* ---------- Expandable panel ---------- */}
      {expanded && (
        <div className="demo-panel">
          {/* Preset buttons grid */}
          <div className="demo-presets-grid">
            {PRESETS.map(({ key, label, Icon }) => (
              <button
                key={key}
                type="button"
                className={`demo-preset-btn${activePreset === key ? " active" : ""}`}
                disabled={loading}
                onClick={() => handlePresetClick(key)}
              >
                <Icon size={18} />
                {label}
              </button>
            ))}
          </div>

          {/* Custom business section */}
          <div className="demo-custom-section">
            {!showCustom ? (
              <button
                type="button"
                className="demo-custom-toggle"
                disabled={loading}
                onClick={() => setShowCustom(true)}
              >
                <Plus size={16} />
                Своё
              </button>
            ) : (
              <div className="demo-custom-form">
                <input
                  type="text"
                  placeholder="Название бизнеса"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  maxLength={60}
                />
                <input
                  type="text"
                  placeholder="Адрес (необязательно)"
                  value={customAddress}
                  onChange={(e) => setCustomAddress(e.target.value)}
                  maxLength={200}
                />

                {/* Service rows */}
                {customServices.map((svc, idx) => (
                  <div className="demo-service-row" key={idx}>
                    <input
                      type="text"
                      placeholder="Услуга"
                      value={svc.name}
                      onChange={(e) =>
                        updateService(idx, "name", e.target.value)
                      }
                      maxLength={60}
                    />
                    <input
                      type="number"
                      placeholder="Цена"
                      value={svc.price}
                      onChange={(e) =>
                        updateService(idx, "price", e.target.value)
                      }
                      min={0}
                      step={1}
                    />
                    <input
                      type="number"
                      placeholder="Мин"
                      value={svc.duration}
                      onChange={(e) =>
                        updateService(idx, "duration", e.target.value)
                      }
                      min={5}
                      max={480}
                      step={5}
                    />
                    <button
                      type="button"
                      className="demo-remove-service-btn"
                      onClick={() => removeService(idx)}
                      disabled={customServices.length <= 1}
                      aria-label="Удалить услугу"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}

                <button
                  type="button"
                  className="demo-add-service-btn"
                  onClick={addService}
                >
                  <Plus size={14} />
                  Добавить услугу
                </button>

                <button
                  type="button"
                  className="demo-custom-submit"
                  disabled={loading}
                  onClick={handleCustomSubmit}
                >
                  <RotateCcw
                    size={14}
                    style={{ display: "inline", verticalAlign: "middle", marginRight: 6 }}
                  />
                  Применить
                </button>
              </div>
            )}
          </div>

          {/* Loading / Error feedback */}
          {loading && <div className="demo-loading">Загрузка...</div>}
          {error && <div className="demo-error">{error}</div>}
        </div>
      )}
    </>
  );
}
