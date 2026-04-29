/**
 * Top-of-page global navigation.
 *
 * Renders the StudySync brand, the three top-level links (Classes /
 * Discussion / Personal), and a logout button.
 */
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { auth } from "./firebase";
import { signOut } from "firebase/auth";
import "./Navbar.css";

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  // Helper to check if a path is active, ignoring nested class routes for global links
  const isActive = (path) => location.pathname === path;

  /**
   * Sign the user out of Firebase, clear cached identity, and bounce
   * back to the login page. Errors are logged but not surfaced to the
   * user.
   */
  const handleLogout = async () => {
    try {
      await signOut(auth);
      localStorage.removeItem("userEmail");
      navigate("/");
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
        {/* GLOBAL NAVIGATION ONLY */}
        <Link
          to="/home"
          className={`navbar-link ${isActive("/home") ? "active" : ""}`}
        >
          Classes
        </Link>
        <Link
          to="/inbox"
          className={`navbar-link ${isActive("/inbox") ? "active" : ""}`}
        >
          Discussion
        </Link>
        <Link
          to="/dashboard"
          className={`navbar-link ${isActive("/dashboard") ? "active" : ""}`}
        >
          Personal
        </Link>

        <button
          className="navbar-logout-btn"
          onClick={() => setShowLogoutModal(true)}
        >
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
          </svg>
        </button>
      </div>

      {showLogoutModal && (
        <div className="modal-overlay">
          <div className="modal-card logout-modal">
            <h3>Are you sure you want to log out?</h3>
            <div className="modal-actions">
              <button className="btn-subtle-link" onClick={() => setShowLogoutModal(false)}>Cancel</button>
              <button className="btn-submit logout-confirm" onClick={handleLogout}>Log out</button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;