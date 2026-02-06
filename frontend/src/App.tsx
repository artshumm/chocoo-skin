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
import AdminSettingsPage from "./pages/AdminSettingsPage";

export default function App() {
  const { telegramId, initData } = useTelegram();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    // Устанавливаем initData для всех API запросов
    setInitData(initData);

    // Авторизация через бэкенд (данные извлекаются из initData)
    authUser()
      .then(setUser)
      .catch(() => setAuthError("Ошибка авторизации. Перезагрузите приложение."))
      .finally(() => setLoading(false));
  }, [telegramId, initData]);

  if (loading) return <div className="loading">Загрузка...</div>;
  if (authError) return <div className="error-msg">{authError}</div>;

  const isAdmin = user?.role === "admin";

  return (
    <>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/booking" element={user ? <BookingPage user={user} onUserUpdate={setUser} /> : null} />
        <Route path="/my" element={<MyBookingsPage />} />
        <Route
          path="/profile"
          element={user ? <ProfilePage user={user} onSave={setUser} isOnboarding={false} /> : null}
        />
        {isAdmin && <Route path="/admin" element={<AdminPage />} />}
        {isAdmin && <Route path="/stats" element={<StatsPage />} />}
        {isAdmin && <Route path="/settings" element={<AdminSettingsPage />} />}
      </Routes>
      <NavBar isAdmin={isAdmin} />
    </>
  );
}
