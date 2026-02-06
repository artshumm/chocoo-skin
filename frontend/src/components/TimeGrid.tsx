import type { Slot } from "../types";

interface Props {
  slots: Slot[];
  selectedSlotId: number | null;
  onSelect: (slot: Slot) => void;
  mode?: "client" | "admin";
}

function formatTime(t: string): string {
  // "09:00:00" → "09:00"
  return t.slice(0, 5);
}

export default function TimeGrid({ slots, selectedSlotId, onSelect, mode = "client" }: Props) {
  if (slots.length === 0) {
    return <div className="empty-state">Нет слотов на эту дату</div>;
  }

  return (
    <div className="time-grid">
      {slots.map((slot) => {
        const isSelected = slot.id === selectedSlotId;

        if (mode === "admin") {
          const cls =
            slot.status === "available"
              ? "admin-available"
              : slot.status === "booked"
                ? "admin-booked"
                : "admin-blocked";
          return (
            <div
              key={slot.id}
              className={`time-chip ${cls}`}
              onClick={() => {
                if (slot.status !== "booked") onSelect(slot);
              }}
            >
              {formatTime(slot.start_time)}
            </div>
          );
        }

        // Client mode: only available slots are clickable
        const isAvailable = slot.status === "available";
        return (
          <div
            key={slot.id}
            className={`time-chip ${slot.status}${isSelected ? " selected" : ""}`}
            onClick={() => isAvailable && onSelect(slot)}
          >
            {formatTime(slot.start_time)}
          </div>
        );
      })}
    </div>
  );
}
