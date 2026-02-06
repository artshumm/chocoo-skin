declare global {
  interface Window {
    Telegram: {
      WebApp: {
        initData: string;
        initDataUnsafe: {
          user?: {
            id: number;
            username?: string;
            first_name?: string;
          };
        };
        ready: () => void;
        expand: () => void;
        close: () => void;
        MainButton: {
          text: string;
          show: () => void;
          hide: () => void;
          onClick: (cb: () => void) => void;
          offClick: (cb: () => void) => void;
          showProgress: () => void;
          hideProgress: () => void;
        };
        themeParams: {
          bg_color?: string;
          text_color?: string;
          hint_color?: string;
          button_color?: string;
          button_text_color?: string;
        };
        colorScheme: "light" | "dark";
      };
    };
  }
}

export function useTelegram() {
  const tg = window.Telegram?.WebApp;

  const user = tg?.initDataUnsafe?.user;

  return {
    tg,
    user,
    telegramId: user?.id ?? 0,
    username: user?.username,
    firstName: user?.first_name,
    initData: tg?.initData ?? "",
    colorScheme: tg?.colorScheme ?? "light",
  };
}
