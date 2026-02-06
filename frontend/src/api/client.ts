import type { Booking, Expense, FaqItem, SalonInfo, Service, Slot, User } from "../types";

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

// Expenses (Admin)
export const getExpenses = (month: string) =>
  request<Expense[]>(`/api/expenses/?month=${month}`);

export const createExpense = (name: string, amount: number, month: string) =>
  request<Expense>("/api/expenses/", {
    method: "POST",
    body: JSON.stringify({ name, amount, month }),
  });

export const deleteExpense = (expenseId: number) =>
  request<{ ok: boolean }>(`/api/expenses/${expenseId}`, {
    method: "DELETE",
  });
