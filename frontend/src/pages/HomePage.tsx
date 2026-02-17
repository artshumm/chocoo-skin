import { useEffect, useState } from "react";
import { getSalonInfoCached, getFaqCached } from "../api/client";
import type { SalonInfo, FaqItem } from "../types";

export default function HomePage() {
  // Stale-while-revalidate: сначала из localStorage, потом обновляем из сети
  const [salonResult] = useState(() => getSalonInfoCached());
  const [faqResult] = useState(() => getFaqCached());

  const [salon, setSalon] = useState<SalonInfo | null>(salonResult.cached);
  const [faq, setFaq] = useState<FaqItem[]>(faqResult.cached ?? []);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    salonResult.fresh.then(setSalon).catch(() => {
      if (!salon) setError("Не удалось загрузить информацию о салоне");
    });
    faqResult.fresh.then(setFaq).catch(() => {});
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const handleRetry = () => {
    setError("");
    const retryResult = getSalonInfoCached();
    retryResult.fresh.then(setSalon).catch(() => setError("Не удалось загрузить информацию о салоне"));
    const retryFaq = getFaqCached();
    retryFaq.fresh.then(setFaq).catch(() => {});
  };

  if (error && !salon) return (
    <div className="error-retry">
      <div className="error-retry-msg">{error}</div>
      <button className="btn" onClick={handleRetry}>Попробовать снова</button>
    </div>
  );

  return (
    <div className="page">
      <div className="salon-card">
        <h1>{salon?.name ?? "Салон"}</h1>
        {salon?.description && <p className="description">{salon.description}</p>}
        {salon?.address && (
          <div className="info-row">
            <span className="label">Адрес:</span> {salon.address}
          </div>
        )}
        {salon?.phone && (
          <div className="info-row">
            <span className="label">Телефон:</span>{" "}
            <a href={`tel:${salon.phone}`}>{salon.phone}</a>
          </div>
        )}
        {salon?.working_hours_text && (
          <div className="info-row">
            <span className="label">Часы работы:</span> {salon.working_hours_text}
          </div>
        )}
        {salon?.instagram && (
          <div className="info-row">
            <span className="label">Instagram:</span>{" "}
            <a href={salon.instagram} target="_blank" rel="noopener noreferrer">
              {salon.instagram.includes("instagram.com/")
                ? "@" + salon.instagram.split("instagram.com/")[1].replace(/\/$/, "")
                : salon.instagram}
            </a>
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
