import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { useState, useCallback } from "react";
import "../index.css";
import App from "../App";
import DemoOverlay from "./DemoOverlay";

// Demo user IDs — must match backend DEMO_ADMIN_ID / dependency overrides
const DEMO_CLIENT_ID = 1000001;
const DEMO_ADMIN_ID = 1000002;

/**
 * Build a fake initData query string (mimics Telegram's WebApp.initData format).
 * The demo backend validates with SKIP_TELEGRAM_VALIDATION=true,
 * so a dummy hash is sufficient.
 */
function buildFakeInitData(
  userId: number,
  username: string,
  firstName: string
): string {
  const user = JSON.stringify({
    id: userId,
    username,
    first_name: firstName,
  });
  const authDate = Math.floor(Date.now() / 1000);
  return `user=${encodeURIComponent(user)}&auth_date=${authDate}&hash=demo_hash`;
}

/**
 * Install mock window.Telegram.WebApp BEFORE React renders.
 * This satisfies the App.tsx guard (`if (!window.Telegram?.WebApp)`)
 * and supplies initData consumed by client.ts `setInitData()`.
 */
function setupMockTelegram(
  userId: number,
  username: string,
  firstName: string
): void {
  const initData = buildFakeInitData(userId, username, firstName);

  (window as unknown as Record<string, unknown>).Telegram = {
    WebApp: {
      initData,
      initDataUnsafe: {
        user: { id: userId, username, first_name: firstName },
      },
      ready: () => {},
      expand: () => {},
      close: () => {},
      MainButton: {
        text: "",
        show: () => {},
        hide: () => {},
        onClick: () => {},
        offClick: () => {},
        showProgress: () => {},
        hideProgress: () => {},
      },
      themeParams: {},
      colorScheme: "light" as const,
    },
  };
}

// Initialize with client role by default
setupMockTelegram(DEMO_CLIENT_ID, "demo_client", "Клиент");

function DemoApp() {
  const [isAdmin, setIsAdmin] = useState(false);
  const [appKey, setAppKey] = useState(0); // Force full remount on role switch

  const switchRole = useCallback(() => {
    const newIsAdmin = !isAdmin;
    setIsAdmin(newIsAdmin);

    if (newIsAdmin) {
      setupMockTelegram(DEMO_ADMIN_ID, "demo_admin", "Админ");
    } else {
      setupMockTelegram(DEMO_CLIENT_ID, "demo_client", "Клиент");
    }

    // Flush stale-while-revalidate cache (keys prefixed with "cache_")
    Object.keys(localStorage).forEach((key) => {
      if (key.startsWith("cache_")) localStorage.removeItem(key);
    });

    setAppKey((prev) => prev + 1);
  }, [isAdmin]);

  const onPresetApplied = useCallback(() => {
    // Clear cache and remount after business preset change
    Object.keys(localStorage).forEach((key) => {
      if (key.startsWith("cache_")) localStorage.removeItem(key);
    });
    setAppKey((prev) => prev + 1);
  }, []);

  return (
    <>
      <DemoOverlay
        isAdmin={isAdmin}
        onSwitchRole={switchRole}
        onPresetApplied={onPresetApplied}
      />
      <App key={appKey} />
    </>
  );
}

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found");
}

createRoot(rootElement).render(
  <BrowserRouter>
    <DemoApp />
  </BrowserRouter>
);
