import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { useTelegram } from "./hooks/useTelegram";
import { authUser, setInitData } from "./api/client";
import type { User } from "./types";
import NavBar from "./components/NavBar";
import HomePage from "./pages/HomePage";
import BookingPage from "./pages/BookingPage";
import MyBookingsPage from "./pages/MyBookingsPage";
import ProfilePage from "./pages/ProfilePage";
import AdminPage from "./pages/AdminPage";
import StatsPage from "./pages/StatsPage";

export default function App() {
  const { telegramId, initData } = useTelegram();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Устанавливаем initData для всех API запросов
    setInitData(initData);

    // Авторизация через бэкенд (данные извлекаются из initData)
    authUser()
      .then(setUser)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [telegramId, initData]);

  if (loading) return <div className="loading">Загрузка...</div>;

  const isAdmin = user?.role === "admin";

  return (
    <>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/booking" element={<BookingPage user={user!} onUserUpdate={setUser} />} />
        <Route path="/my" element={<MyBookingsPage />} />
        <Route
          path="/profile"
          element={user ? <ProfilePage user={user} onSave={setUser} isOnboarding={false} /> : null}
        />
        {isAdmin && <Route path="/admin" element={<AdminPage />} />}
        {isAdmin && <Route path="/stats" element={<StatsPage />} />}
      </Routes>
      <NavBar isAdmin={isAdmin} />
    </>
  );
}
