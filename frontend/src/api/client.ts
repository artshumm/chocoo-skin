import type { Booking, Expense, FaqItem, SalonInfo, Service, Slot, User } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
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

// Users
export const authUser = (telegram_id: number, username?: string, first_name?: string) =>
  request<User>("/api/users/auth", {
    method: "POST",
    body: JSON.stringify({ telegram_id, username, first_name }),
  });

export const updateProfile = (telegram_id: number, first_name: string, phone: string, consent_given: boolean) =>
  request<User>(`/api/users/profile?telegram_id=${telegram_id}`, {
    method: "PATCH",
    body: JSON.stringify({ first_name, phone, consent_given }),
  });

// Services
export const getServices = () => request<Service[]>("/api/services/");

// Slots
export const getSlots = (date: string) =>
  request<Slot[]>(`/api/slots/?date=${date}`);

// Bookings
export const createBooking = (telegram_id: number, service_id: number, slot_id: number, remind_before_hours: number = 2) =>
  request<Booking>("/api/bookings/", {
    method: "POST",
    body: JSON.stringify({ telegram_id, service_id, slot_id, remind_before_hours }),
  });

export const getMyBookings = (telegram_id: number) =>
  request<Booking[]>(`/api/bookings/my?telegram_id=${telegram_id}`);

export const cancelBooking = (booking_id: number, telegram_id: number) =>
  request<Booking>(`/api/bookings/${booking_id}/cancel?telegram_id=${telegram_id}`, {
    method: "PATCH",
  });

// Admin
export const getAllSlots = (date: string, telegramId: number) =>
  request<Slot[]>(`/api/slots/all?date=${date}`, {
    headers: { "Content-Type": "application/json", "X-Telegram-Id": String(telegramId) },
  });

export const generateSlots = (
  date: string,
  telegramId: number,
  startHour = 8,
  startMinute = 30,
  endHour = 21,
  endMinute = 0,
) =>
  request<Slot[]>("/api/slots/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Telegram-Id": String(telegramId) },
    body: JSON.stringify({
      date,
      start_hour: startHour,
      start_minute: startMinute,
      end_hour: endHour,
      end_minute: endMinute,
      interval_minutes: 30,
    }),
  });

export const updateSlot = (slotId: number, status: string, telegramId: number) =>
  request<Slot>(`/api/slots/${slotId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-Telegram-Id": String(telegramId) },
    body: JSON.stringify({ status }),
  });

export const getAllBookings = (telegramId: number) =>
  request<Booking[]>("/api/bookings/all", {
    headers: { "Content-Type": "application/json", "X-Telegram-Id": String(telegramId) },
  });

// Expenses (Admin)
export const getExpenses = (month: string, telegramId: number) =>
  request<Expense[]>(`/api/expenses/?month=${month}`, {
    headers: { "Content-Type": "application/json", "X-Telegram-Id": String(telegramId) },
  });

export const createExpense = (name: string, amount: number, month: string, telegramId: number) =>
  request<Expense>("/api/expenses/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Telegram-Id": String(telegramId) },
    body: JSON.stringify({ name, amount, month }),
  });

export const deleteExpense = (expenseId: number, telegramId: number) =>
  request<{ ok: boolean }>(`/api/expenses/${expenseId}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json", "X-Telegram-Id": String(telegramId) },
  });
