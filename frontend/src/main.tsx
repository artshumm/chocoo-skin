import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App";

// Telegram WebApp init
window.Telegram?.WebApp?.ready();
window.Telegram?.WebApp?.expand();

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found");
}

createRoot(rootElement).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
);
