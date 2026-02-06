export interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  phone: string | null;
  instagram: string | null;
  consent_given: boolean;
  role: string;
  created_at: string;
}

export interface Service {
  id: number;
  name: string;
  short_description: string;
  description: string;
  duration_minutes: number;
  price: number;
  is_active: boolean;
}

export interface Slot {
  id: number;
  date: string;
  start_time: string;
  end_time: string;
  status: string;
}

export interface Booking {
  id: number;
  status: string;
  remind_before_hours: number;
  reminded: boolean;
  created_at: string;
  client: User;
  service: Service;
  slot: Slot;
}

export interface SalonInfo {
  name: string;
  description: string;
  address: string;
  phone: string;
  working_hours_text: string;
  instagram: string;
}

export interface FaqItem {
  id: number;
  question: string;
  answer: string;
  order_index: number;
}

export interface ScheduleTemplate {
  id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  interval_minutes: number;
  is_active: boolean;
}

export interface Expense {
  id: number;
  name: string;
  amount: number;
  month: string;
  created_at: string;
}
