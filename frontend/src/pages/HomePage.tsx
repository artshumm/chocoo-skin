import { useEffect, useState } from "react";
import { getSalonInfo, getFaq } from "../api/client";
import type { SalonInfo, FaqItem } from "../types";

export default function HomePage() {
  const [salon, setSalon] = useState<SalonInfo | null>(null);
  const [faq, setFaq] = useState<FaqItem[]>([]);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  useEffect(() => {
    getSalonInfo().then(setSalon);
    getFaq().then(setFaq);
  }, []);

  if (!salon) return <div className="loading">Загрузка...</div>;

  return (
    <div className="page">
      <div className="salon-card">
        <h1>{salon.name}</h1>
        {salon.description && <p className="description">{salon.description}</p>}
        {salon.address && (
          <div className="info-row">
            <span className="label">Адрес:</span> {salon.address}
          </div>
        )}
        {salon.phone && (
          <div className="info-row">
            <span className="label">Телефон:</span>{" "}
            <a href={`tel:${salon.phone}`}>{salon.phone}</a>
          </div>
        )}
        {salon.working_hours_text && (
          <div className="info-row">
            <span className="label">Часы работы:</span> {salon.working_hours_text}
          </div>
        )}
        {salon.instagram && (
          <div className="info-row">
            <span className="label">Instagram:</span>{" "}
            <a href={salon.instagram} target="_blank" rel="noopener noreferrer">@chocoo.skin</a>
          </div>
        )}
      </div>

      {faq.length > 0 && (
        <div className="faq-section">
          <h2>Частые вопросы</h2>
          {faq.map((item) => (
            <div
              key={item.id}
              className={`faq-item ${openFaq === item.id ? "open" : ""}`}
              onClick={() => setOpenFaq(openFaq === item.id ? null : item.id)}
            >
              <div className="faq-question">
                {item.question}
                <span className="faq-arrow">{openFaq === item.id ? "▲" : "▼"}</span>
              </div>
              {openFaq === item.id && (
                <div className="faq-answer">{item.answer}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
