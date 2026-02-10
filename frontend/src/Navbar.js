import { Link, useLocation } from "react-router-dom";
import "./Navbar.css";

const Navbar = () => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/home" className="navbar-logo">
          Study<span>Sync</span>
        </Link>
      </div>
      <div className="navbar-links">
        <Link
          to="/calendar"
          className={`navbar-link ${isActive("/calendar") ? "active" : ""}`}
        >
          Study Groups
        </Link>
        <Link
          to="/chat"
          className={`navbar-link ${isActive("/chat") ? "active" : ""}`}
        >
          Discussion
        </Link>
        <Link
          to="/resources"
          className={`navbar-link ${isActive("/resources") ? "active" : ""}`}
        >
          Library
        </Link>
        <Link
          to="/dashboard"
          className={`navbar-link ${isActive("/dashboard") ? "active" : ""}`}
        >
          Personal
        </Link>
      </div>
    </nav>
  );
};

export default Navbar;
