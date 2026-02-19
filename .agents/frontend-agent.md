# Frontend Agent — Chocoo Skin

## Role
Expert frontend developer for React + TypeScript Telegram Mini App.

## Tech Stack
- **Framework:** React 18 + TypeScript + Vite
- **TMA SDK:** @telegram-apps/sdk-react
- **Icons:** Lucide React (SVG, tree-shakeable)
- **Design:** Soft UI Evolution (custom CSS, no UI library)
- **Auth:** Telegram initData → `Authorization: tma <initData>`
- **Deploy:** Railway (static build)

## Skills (read before every task)
1. `.agents/skills/react-best-practices/SKILL.md` — React performance, re-render optimization, bundle size
2. `.agents/skills/typescript-expert/SKILL.md` — TypeScript patterns, type safety, strict mode
3. `.agents/skills/ui-ux-pro-max/SKILL.md` — Design system, Soft UI style, color palette, accessibility

## Project Structure
```
frontend/src/
  main.tsx           — Entry point, Telegram WebApp check
  App.tsx            — Auth flow, routing, React.lazy
  index.css          — Global styles (Soft UI Evolution design system)
  api/
    client.ts        — HTTP client, setInitData(), request()
    types.ts         — TypeScript interfaces (Slot, Booking, Service, etc.)
  components/
    NavBar.tsx       — Bottom navigation (Lucide icons)
    Calendar.tsx     — Date picker (UTC-based for Minsk timezone)
    TimeGrid.tsx     — Time slot selector (React.memo)
  pages/
    HomePage.tsx     — Salon info + FAQ (accordion)
    BookingPage.tsx  — Service → date → time → confirm flow
    MyBookingsPage.tsx — User bookings + cancel
    ProfilePage.tsx  — Phone, name, Instagram
    AdminPage.tsx    — Admin slot management
    AdminBookingsPage.tsx — Admin bookings by date
    AdminSettingsPage.tsx — CMS (salon, services, FAQ, schedule)
    StatsPage.tsx    — Revenue stats + expenses
  utils/
    timezone.ts      — nowMinsk(), todayMinsk(), msUntilSlotMinsk()
    cache.ts         — localStorage stale-while-revalidate (1h TTL)
```

## Key Patterns
- **Timezone:** ALL Date operations use UTC methods (getUTCFullYear, getUTCMonth, getUTCDate). Create dates with `Date.UTC()`. Never use local time methods.
- **Auth:** `client.ts:setInitData()` called once on load → all requests get `Authorization: tma <initData>` header
- **Caching:** localStorage with 1-hour TTL, stale-while-revalidate pattern
- **Code splitting:** React.lazy for all admin pages (AdminPage, AdminBookingsPage, AdminSettingsPage, StatsPage)
- **Icons:** Lucide React — `import { IconName } from "lucide-react"` — no emojis/HTML entities
- **CSS variables:** Telegram theme `var(--tg-theme-*)` + custom `var(--color-brand)`, `var(--shadow-*)`, `var(--border-soft)`
- **Validation:** Phone regex, Instagram regex (@username), amount limits — validate on frontend AND backend

## Design System (Soft UI Evolution)
- **Brand:** `#D4A574` (warm golden), `#F5E6D3` (light), `#8B6914` (dark)
- **Shadows:** `shadow-sm`, `shadow-md`, `shadow-lg`, `shadow-card` (soft, layered)
- **Borders:** `border-soft: 1px solid rgba(0,0,0,0.06)`
- **Radius:** 12px cards, 16px modals, 24px buttons
- **Animations:** slide-up (cards), shimmer (skeleton), scale 0.98 (buttons press)
- **Navbar:** Backdrop-blur glass effect with `@supports`

## Rules
1. Never use `getFullYear()`, `getMonth()`, `getDate()` — only `getUTCFullYear()`, `getUTCMonth()`, `getUTCDate()`
2. All icons from `lucide-react` — no emojis, no HTML entities
3. Use `React.memo` for list items and heavy components
4. Use `useMemo` for expensive filter/reduce chains
5. Always handle loading and error states
6. Validate inputs before API calls (phone, Instagram, amounts)
7. Run `cd frontend && npm run build` after changes (includes tsc type-check)
8. Preserve Telegram theme variables compatibility (`var(--tg-theme-*)`)
