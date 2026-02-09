import { lazy, Suspense, useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { useTelegram } from "./hooks/useTelegram";
import { authUser, setInitData } from "./api/client";
import type { User } from "./types";
import NavBar from "./components/NavBar";
import HomePage from "./pages/HomePage";
import BookingPage from "./pages/BookingPage";
import MyBookingsPage from "./pages/MyBookingsPage";
import ProfilePage from "./pages/ProfilePage";
// Admin-only pages — lazy loaded (code splitting)
const AdminBookingsPage = lazy(() => import("./pages/AdminBookingsPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const StatsPage = lazy(() => import("./pages/StatsPage"));
const AdminSettingsPage = lazy(() => import("./pages/AdminSettingsPage"));

const AdminFallback = <div className="loading">Загрузка...</div>;

export default function App() {
  const { telegramId, initData } = useTelegram();
  const [user, setUser] = useState<User | null>(null);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    // Устанавливаем initData для всех API запросов
    setInitData(initData);

    // Авторизация в фоне — НЕ блокирует рендер
    authUser()
      .then(setUser)
      .catch(() => setAuthError("Ошибка авторизации. Перезагрузите приложение."));
  }, [telegramId, initData]);

  if (authError) return <div className="error-msg">{authError}</div>;

  const isAdmin = user?.role === "admin";

  return (
    <>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/booking"
          element={user ? <BookingPage user={user} onUserUpdate={setUser} /> : <div className="loading">Загрузка...</div>}
        />
        <Route
          path="/my"
          element={isAdmin ? <Suspense fallback={AdminFallback}><AdminBookingsPage /></Suspense> : <MyBookingsPage />}
        />
        <Route
          path="/profile"
          element={user ? <ProfilePage user={user} onSave={setUser} isOnboarding={false} /> : <div className="loading">Загрузка...</div>}
        />
        {isAdmin && (
          <Route path="/admin" element={<Suspense fallback={AdminFallback}><AdminPage /></Suspense>} />
        )}
        {isAdmin && (
          <Route path="/stats" element={<Suspense fallback={AdminFallback}><StatsPage /></Suspense>} />
        )}
        {isAdmin && (
          <Route path="/settings" element={<Suspense fallback={AdminFallback}><AdminSettingsPage /></Suspense>} />
        )}
      </Routes>
      <NavBar isAdmin={isAdmin} />
    </>
  );
}
