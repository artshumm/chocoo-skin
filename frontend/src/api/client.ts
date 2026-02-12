import type { Booking, Expense, FaqItem, SalonInfo, ScheduleTemplate, Service, Slot, User } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "";

// Валидация: в production VITE_API_URL обязателен
if (import.meta.env.PROD && !API_BASE) {
  throw new Error("VITE_API_URL environment variable is required in production");
}

/** Глобальный initData — устанавливается из App.tsx при загрузке */
let _initData = "";

export function setInitData(initData: string) {
  _initData = initData;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Добавляем Authorization с initData для всех запросов
  if (_initData) {
    headers["Authorization"] = `tma ${_initData}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "Ошибка сервера");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Stale-while-revalidate cache (TTL: 1 hour) ---
const CACHE_TTL_MS = 60 * 60 * 1000;

function cachedGet<T>(path: string, cacheKey: string): { cached: T | null; fresh: Promise<T> } {
  let cached: T | null = null;
  try {
    const raw = localStorage.getItem(cacheKey);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed._ts && Date.now() - parsed._ts < CACHE_TTL_MS) {
        cached = parsed.data as T;
      } else if (!parsed._ts) {
        // Old format (no TTL) — use as-is, will be replaced on fresh fetch
        cached = parsed as T;
      }
    }
  } catch { /* ignore corrupt cache */ }
  const fresh = request<T>(path).then((data) => {
    localStorage.setItem(cacheKey, JSON.stringify({ data, _ts: Date.now() }));
    return data;
  });
  return { cached, fresh };
}

// Salon (cached for instant load)
export const getSalonInfoCached = () => cachedGet<SalonInfo>("/api/salon", "cache_salon");
export const getFaqCached = () => cachedGet<FaqItem[]>("/api/faq", "cache_faq");

// Salon (direct — for admin CMS)
export const getSalonInfo = () => request<SalonInfo>("/api/salon");
export const getFaq = () => request<FaqItem[]>("/api/faq");

// Users — данные берутся из initData на бэкенде
export const authUser = () =>
  request<User>("/api/users/auth", { method: "POST" });

export const updateProfile = (first_name: string, phone: string, consent_given: boolean, instagram?: string | null) =>
  request<User>("/api/users/profile", {
    method: "PATCH",
    body: JSON.stringify({ first_name, phone, consent_given, instagram: instagram || null }),
  });

// Services (cached for instant load on BookingPage)
export const getServicesCached = () => cachedGet<Service[]>("/api/services/", "cache_services");
export const getServices = () => request<Service[]>("/api/services/");

// Slots
export const getSlots = (date: string) =>
  request<Slot[]>(`/api/slots/?date=${date}`);

// Slot availability (cached 5 min for calendar badges)
const AVAIL_CACHE_TTL_MS = 5 * 60 * 1000;

export function getSlotAvailabilityCached(from: string, to: string) {
  const cacheKey = `cache_avail_${from}_${to}`;
  const path = `/api/slots/availability?from=${from}&to=${to}`;
  let cached: Record<string, number> | null = null;
  try {
    const raw = localStorage.getItem(cacheKey);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed._ts && Date.now() - parsed._ts < AVAIL_CACHE_TTL_MS) {
        cached = parsed.data as Record<string, number>;
      }
    }
  } catch { /* ignore */ }
  const fresh = request<Record<string, number>>(path).then((data) => {
    localStorage.setItem(cacheKey, JSON.stringify({ data, _ts: Date.now() }));
    return data;
  });
  return { cached, fresh };
}

export const getSlotAvailability = (from: string, to: string) =>
  request<Record<string, number>>(`/api/slots/availability?from=${from}&to=${to}`);

// Bookings — telegram_id берётся из initData
export const createBooking = (service_id: number, slot_id: number, remind_before_hours: number = 2) =>
  request<Booking>("/api/bookings/", {
    method: "POST",
    body: JSON.stringify({ service_id, slot_id, remind_before_hours }),
  });

export const getMyBookingsCached = () => cachedGet<Booking[]>("/api/bookings/my", "cache_my_bookings");

export const getMyBookings = () =>
  request<Booking[]>("/api/bookings/my");

export const cancelBooking = (bookingId: number) =>
  request<Booking>(`/api/bookings/${bookingId}/cancel`, {
    method: "PATCH",
  });

// Admin — идентификация через initData
export const getAllSlots = (date: string) =>
  request<Slot[]>(`/api/slots/all?date=${date}`);

export const generateSlots = (
  date: string,
  startHour = 8,
  startMinute = 30,
  endHour = 21,
  endMinute = 0,
  intervalMinutes = 20,
) =>
  request<Slot[]>("/api/slots/generate", {
    method: "POST",
    body: JSON.stringify({
      date,
      start_hour: startHour,
      start_minute: startMinute,
      end_hour: endHour,
      end_minute: endMinute,
      interval_minutes: intervalMinutes,
    }),
  });

export const updateSlot = (slotId: number, status: string) =>
  request<Slot>(`/api/slots/${slotId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });

export const getAllBookings = (date?: string, status?: string, limit?: number) => {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (status) params.set("status", status);
  if (limit) params.set("limit", String(limit));
  const qs = params.toString();
  return request<Booking[]>(`/api/bookings/all${qs ? `?${qs}` : ""}`);
};

export const adminCancelBooking = (bookingId: number) =>
  request<Booking>(`/api/bookings/${bookingId}/admin-cancel`, {
    method: "PATCH",
  });

// Expenses (Admin)
export const getExpenses = (month: string) =>
  request<Expense[]>(`/api/expenses/?month=${month}`);

export const createExpense = (name: string, amount: number, month: string) =>
  request<Expense>("/api/expenses/", {
    method: "POST",
    body: JSON.stringify({ name, amount, month }),
  });

export const deleteExpense = (expenseId: number) =>
  request<void>(`/api/expenses/${expenseId}`, {
    method: "DELETE",
  });

// Admin CMS — Salon
export const updateSalon = (data: Partial<SalonInfo>) =>
  request<SalonInfo>("/api/salon", {
    method: "PATCH",
    body: JSON.stringify(data),
  });

// Admin CMS — Services
export const getAllServices = () => request<Service[]>("/api/services/all");

export const createService = (data: {
  name: string;
  short_description?: string;
  description?: string;
  duration_minutes?: number;
  price: number;
  is_active?: boolean;
}) =>
  request<Service>("/api/services/", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateService = (id: number, data: Partial<Service>) =>
  request<Service>(`/api/services/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteService = (id: number) =>
  request<void>(`/api/services/${id}`, { method: "DELETE" });

// Admin CMS — FAQ
export const createFaq = (data: { question: string; answer: string; order_index?: number }) =>
  request<FaqItem>("/api/faq", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateFaq = (id: number, data: Partial<FaqItem>) =>
  request<FaqItem>(`/api/faq/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteFaq = (id: number) =>
  request<void>(`/api/faq/${id}`, { method: "DELETE" });

export const reorderFaq = (ids: number[]) =>
  request<FaqItem[]>("/api/faq/reorder", {
    method: "PUT",
    body: JSON.stringify({ ids }),
  });

// Admin CMS — Schedule Templates
export const getScheduleTemplates = () =>
  request<ScheduleTemplate[]>("/api/schedule-templates/");

export const upsertScheduleTemplates = (templates: Omit<ScheduleTemplate, "id">[]) =>
  request<ScheduleTemplate[]>("/api/schedule-templates/", {
    method: "PUT",
    body: JSON.stringify({ templates }),
  });
