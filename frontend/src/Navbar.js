import { useState } from "react"; // Added useState
import { Link, useLocation, useNavigate } from "react-router-dom"; // Added useNavigate
import { auth } from "./firebase"; // Import auth
import { signOut } from "firebase/auth"; // Import signOut
import "./Navbar.css";

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  const isActive = (path) => location.pathname === path;

const handleLogout = async () => {
  try {
    await signOut(auth);
    // Clear any potential cached user data
    localStorage.removeItem("userEmail"); 
    navigate("/login");
  } catch (error) {
    console.error("Logout failed:", error);
  }
};

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

        {/* Logout Trigger */}
        <button
          className="navbar-logout-btn"
          onClick={() => setShowLogoutModal(true)}
        >
          <svg
            viewBox="0 0 24 24"
            width="24"
            height="24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
          </svg>
        </button>
      </div>

      {/* Logout Overlay */}
      {showLogoutModal && (
        <div className="modal-overlay">
          <div className="modal-card logout-modal">
            <h3>Are you sure you want to log out?</h3>
            <div className="modal-actions">
              <button
                className="btn-subtle-link"
                onClick={() => setShowLogoutModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn-submit logout-confirm"
                onClick={handleLogout}
              >
                Log out
              </button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
