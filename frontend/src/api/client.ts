import type { Booking, Expense, FaqItem, SalonInfo, ScheduleTemplate, Service, Slot, User } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "";

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

// Salon
export const getSalonInfo = () => request<SalonInfo>("/api/salon");
export const getFaq = () => request<FaqItem[]>("/api/faq");

// Users — данные берутся из initData на бэкенде
export const authUser = () =>
  request<User>("/api/users/auth", { method: "POST" });

export const updateProfile = (first_name: string, phone: string, consent_given: boolean) =>
  request<User>("/api/users/profile", {
    method: "PATCH",
    body: JSON.stringify({ first_name, phone, consent_given }),
  });

// Services
export const getServices = () => request<Service[]>("/api/services/");

// Slots
export const getSlots = (date: string) =>
  request<Slot[]>(`/api/slots/?date=${date}`);

// Bookings — telegram_id берётся из initData
export const createBooking = (service_id: number, slot_id: number, remind_before_hours: number = 2) =>
  request<Booking>("/api/bookings/", {
    method: "POST",
    body: JSON.stringify({ service_id, slot_id, remind_before_hours }),
  });

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
) =>
  request<Slot[]>("/api/slots/generate", {
    method: "POST",
    body: JSON.stringify({
      date,
      start_hour: startHour,
      start_minute: startMinute,
      end_hour: endHour,
      end_minute: endMinute,
      interval_minutes: 30,
    }),
  });

export const updateSlot = (slotId: number, status: string) =>
  request<Slot>(`/api/slots/${slotId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });

export const getAllBookings = () =>
  request<Booking[]>("/api/bookings/all");

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
