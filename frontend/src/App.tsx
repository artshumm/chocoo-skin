import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { useTelegram } from "./hooks/useTelegram";
import { authUser } from "./api/client";
import type { User } from "./types";
import NavBar from "./components/NavBar";
import HomePage from "./pages/HomePage";
import BookingPage from "./pages/BookingPage";
import MyBookingsPage from "./pages/MyBookingsPage";
import AdminPage from "./pages/AdminPage";
import StatsPage from "./pages/StatsPage";

export default function App() {
  const { telegramId, username, firstName } = useTelegram();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const id = telegramId || 0;
    if (id === 0) {
      // Не в Telegram — dev-режим с тестовым пользователем
      setUser({
        id: 0,
        telegram_id: 0,
        username: "dev",
        first_name: "Developer",
        role: "admin",
        created_at: new Date().toISOString(),
      });
      setLoading(false);
      return;
    }

    authUser(id, username, firstName)
      .then(setUser)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [telegramId, username, firstName]);

  if (loading) return <div className="loading">Загрузка...</div>;

  const isAdmin = user?.role === "admin";

  return (
    <>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/booking" element={<BookingPage telegramId={user?.telegram_id ?? 0} />} />
        <Route path="/my" element={<MyBookingsPage telegramId={user?.telegram_id ?? 0} />} />
        {isAdmin && <Route path="/admin" element={<AdminPage telegramId={user?.telegram_id ?? 0} />} />}
        {isAdmin && <Route path="/stats" element={<StatsPage telegramId={user?.telegram_id ?? 0} />} />}
      </Routes>
      <NavBar isAdmin={isAdmin} />
    </>
  );
}
