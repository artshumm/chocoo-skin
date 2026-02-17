import { NavLink } from "react-router-dom";
import { Home, CalendarPlus, ClipboardList, User as UserIcon, Settings, BarChart3, SlidersHorizontal } from "lucide-react";

interface Props {
  isAdmin: boolean;
}

export default function NavBar({ isAdmin }: Props) {
  return (
    <nav className="navbar">
      <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`} end>
        <span className="nav-icon"><Home size={20} strokeWidth={1.75} /></span>
        Главная
      </NavLink>
      <NavLink to="/booking" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon"><CalendarPlus size={20} strokeWidth={1.75} /></span>
        Запись
      </NavLink>
      <NavLink to="/my" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon"><ClipboardList size={20} strokeWidth={1.75} /></span>
        {isAdmin ? "Все записи" : "Мои записи"}
      </NavLink>
      <NavLink to="/profile" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon"><UserIcon size={20} strokeWidth={1.75} /></span>
        Профиль
      </NavLink>
      {isAdmin && (
        <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
          <span className="nav-icon"><Settings size={20} strokeWidth={1.75} /></span>
          Управление
        </NavLink>
      )}
      {isAdmin && (
        <NavLink to="/stats" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
          <span className="nav-icon"><BarChart3 size={20} strokeWidth={1.75} /></span>
          Стат.
        </NavLink>
      )}
      {isAdmin && (
        <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
          <span className="nav-icon"><SlidersHorizontal size={20} strokeWidth={1.75} /></span>
          CMS
        </NavLink>
      )}
    </nav>
  );
}
