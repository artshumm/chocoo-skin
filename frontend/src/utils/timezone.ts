/** Минск UTC+3 (Беларусь не переводит часы, DST нет) */
const MINSK_OFFSET_MS = 3 * 60 * 60 * 1000;

/** Текущее время в Минске как Date (UTC поля = Минск) */
export function nowMinsk(): Date {
  return new Date(Date.now() + MINSK_OFFSET_MS);
}

/** Сегодняшняя дата в Минске: "YYYY-MM-DD" */
export function todayMinsk(): string {
  const d = nowMinsk();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}

/** Дата N дней назад по Минску: "YYYY-MM-DD" */
export function daysAgoMinsk(n: number): string {
  const d = new Date(nowMinsk().getTime() - n * 24 * 60 * 60 * 1000);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}

/** Текущий месяц по Минску: "YYYY-MM" */
export function currentMonthMinsk(): string {
  const d = nowMinsk();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

/** Разница в мс между слотом (Минск) и текущим временем (Минск) */
export function msUntilSlotMinsk(slotDate: string, slotTime: string): number {
  const [y, m, d] = slotDate.split("-").map(Number);
  const [hh, mm] = slotTime.split(":").map(Number);
  // Слот в UTC: вычитаем 3 часа (Минск → UTC)
  const slotUtcMs = Date.UTC(y, m - 1, d, hh - 3, mm);
  return slotUtcMs - Date.now();
}
