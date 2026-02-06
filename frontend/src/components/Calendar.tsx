import { useState } from "react";

interface Props {
  selectedDate: string | null;
  onSelect: (date: string) => void;
}

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
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
  return new Date(year, month + 1, 0).getDate();
}

/** Build list of months to display: current + next if 14-day window crosses boundary */
function getMonthsToShow(today: Date, maxDate: Date): { year: number; month: number }[] {
  const months: { year: number; month: number }[] = [];
  months.push({ year: today.getFullYear(), month: today.getMonth() });

  if (
    maxDate.getFullYear() > today.getFullYear() ||
    maxDate.getMonth() > today.getMonth()
  ) {
    months.push({ year: maxDate.getFullYear(), month: maxDate.getMonth() });
  }

  return months;
}

export default function Calendar({ selectedDate, onSelect }: Props) {
  const todayReal = new Date();
  todayReal.setHours(0, 0, 0, 0);

  const maxDate = new Date(todayReal);
  maxDate.setDate(todayReal.getDate() + 13); // 14 days: today + 13

  const monthsToShow = getMonthsToShow(todayReal, maxDate);

  // Track which month is visible (index into monthsToShow)
  const [visibleIdx, setVisibleIdx] = useState(0);
  const current = monthsToShow[visibleIdx];

  const daysInMonth = getDaysInMonth(current.year, current.month);
  // Monday-based weekday of the 1st (0=Mon, 6=Sun)
  const firstWeekday = (new Date(current.year, current.month, 1).getDay() + 6) % 7;

  const emptyCells = Array(firstWeekday).fill(null);

  const days: Date[] = [];
  for (let d = 1; d <= daysInMonth; d++) {
    days.push(new Date(current.year, current.month, d));
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
          const isSunday = d.getDay() === 0;
          const isActive = dateStr >= todayStr && dateStr <= maxStr && !isSunday;

          return (
            <div
              key={dateStr}
              className={`calendar-day${isSelected ? " selected" : ""}${isToday ? " today" : ""}${!isActive ? " disabled" : ""}`}
              onClick={() => isActive && onSelect(dateStr)}
            >
              {d.getDate()}
            </div>
          );
        })}
      </div>
    </div>
  );
}
