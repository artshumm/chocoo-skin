import { useState } from "react";
import { nowMinsk } from "../utils/timezone";

interface Props {
  selectedDate: string | null;
  onSelect: (date: string) => void;
}

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

function formatDate(d: Date): string {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function getMonthName(month: number): string {
  const names = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
  ];
  return names[month];
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
}

/** Build list of months to display: current + next if 14-day window crosses boundary */
function getMonthsToShow(today: Date, maxDate: Date): { year: number; month: number }[] {
  const months: { year: number; month: number }[] = [];
  months.push({ year: today.getUTCFullYear(), month: today.getUTCMonth() });

  if (
    maxDate.getUTCFullYear() > today.getUTCFullYear() ||
    maxDate.getUTCMonth() > today.getUTCMonth()
  ) {
    months.push({ year: maxDate.getUTCFullYear(), month: maxDate.getUTCMonth() });
  }

  return months;
}

export default function Calendar({ selectedDate, onSelect }: Props) {
  // Используем время Минска (UTC+3), а не локальное время браузера
  const mn = nowMinsk();
  const todayReal = new Date(Date.UTC(mn.getUTCFullYear(), mn.getUTCMonth(), mn.getUTCDate()));

  const maxDate = new Date(todayReal.getTime() + 13 * 24 * 60 * 60 * 1000); // 14 days

  const monthsToShow = getMonthsToShow(todayReal, maxDate);

  // Track which month is visible (index into monthsToShow)
  const [visibleIdx, setVisibleIdx] = useState(0);
  const current = monthsToShow[visibleIdx];

  const daysInMonth = getDaysInMonth(current.year, current.month);
  // Monday-based weekday of the 1st (0=Mon, 6=Sun)
  const firstWeekday = (new Date(Date.UTC(current.year, current.month, 1)).getUTCDay() + 6) % 7;

  const emptyCells = Array(firstWeekday).fill(null);

  const days: Date[] = [];
  for (let d = 1; d <= daysInMonth; d++) {
    days.push(new Date(Date.UTC(current.year, current.month, d)));
  }

  const todayStr = formatDate(todayReal);
  const maxStr = formatDate(maxDate);

  return (
    <div className="calendar">
      <div className="calendar-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        {monthsToShow.length > 1 && visibleIdx > 0 ? (
          <span style={{ cursor: "pointer", padding: "0 8px" }} onClick={() => setVisibleIdx(visibleIdx - 1)}>‹</span>
        ) : (
          <span style={{ width: 24 }} />
        )}
        <span>{getMonthName(current.month)} {current.year}</span>
        {monthsToShow.length > 1 && visibleIdx < monthsToShow.length - 1 ? (
          <span style={{ cursor: "pointer", padding: "0 8px" }} onClick={() => setVisibleIdx(visibleIdx + 1)}>›</span>
        ) : (
          <span style={{ width: 24 }} />
        )}
      </div>

      <div className="calendar-weekdays">
        {WEEKDAYS.map((w) => (
          <span key={w}>{w}</span>
        ))}
      </div>

      <div className="calendar-grid">
        {emptyCells.map((_, i) => (
          <div key={`e${current.month}-${i}`} className="calendar-day empty" />
        ))}
        {days.map((d) => {
          const dateStr = formatDate(d);
          const isToday = dateStr === todayStr;
          const isSelected = dateStr === selectedDate;
          const isSunday = d.getUTCDay() === 0;
          const isActive = dateStr >= todayStr && dateStr <= maxStr && !isSunday;

          return (
            <div
              key={dateStr}
              className={`calendar-day${isSelected ? " selected" : ""}${isToday ? " today" : ""}${!isActive ? " disabled" : ""}`}
              onClick={() => isActive && onSelect(dateStr)}
            >
              {d.getUTCDate()}
            </div>
          );
        })}
      </div>
    </div>
  );
}
