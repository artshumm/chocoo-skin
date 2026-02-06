import { NavLink } from "react-router-dom";

interface Props {
  isAdmin: boolean;
}

export default function NavBar({ isAdmin }: Props) {
  return (
    <nav className="navbar">
      <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`} end>
        <span className="nav-icon">&#127968;</span>
        Главная
      </NavLink>
      <NavLink to="/booking" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon">&#128197;</span>
        Запись
      </NavLink>
      <NavLink to="/my" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon">&#128203;</span>
        Мои записи
      </NavLink>
      {isAdmin && (
        <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
          <span className="nav-icon">&#9881;</span>
          Управление
        </NavLink>
      )}
      {isAdmin && (
        <NavLink to="/stats" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
          <span className="nav-icon">&#128202;</span>
          Стат.
        </NavLink>
      )}
    </nav>
  );
}
