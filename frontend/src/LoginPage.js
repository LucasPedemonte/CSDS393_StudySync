import { useState } from "react";
import "./LoginPage.css";
import { useNavigate } from "react-router-dom";

import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  GoogleAuthProvider,
  signInWithPopup,
  sendPasswordResetEmail,
} from "firebase/auth";

import { auth } from "./firebase.js"; 

const LoginPage = () => {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);

  // --- NEW STATES FOR DATABASE SYNC ---
  const [showRoleSelection, setShowRoleSelection] = useState(false);
  const [tempUser, setTempUser] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });
  const [focused, setFocused] = useState(null);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // --- NEW SYNC FUNCTION ---
  const syncWithBackend = async (user, role, name) => {
    try {
      const response = await fetch("http://localhost:8000/sync-user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          firebase_uid: user.uid,
          email: user.email,
          full_name: name || user.displayName || "New User",
          role: role,
        }),
      });
      if (response.ok) {
        navigate("/home");
      } else {
        const data = await response.json();
        alert(data.detail || "Database sync failed.");
      }
    } catch (err) {
      console.error("Backend error:", err);
      alert("Could not connect to the server.");
    }
  };

 const handleSubmit = async (e) => {
  e.preventDefault();
  setErrorMessage(""); // Clear any old errors when trying again

  try {
    if (isLogin) {
      const userCred = await signInWithEmailAndPassword(auth, formData.email, formData.password);
      await syncWithBackend(userCred.user, "Student", formData.name);
    } else {
      const userCred = await createUserWithEmailAndPassword(auth, formData.email, formData.password);
      if (formData.name?.trim()) {
        await updateProfile(userCred.user, { displayName: formData.name.trim() });
      }
      setTempUser(userCred.user);
      setShowRoleSelection(true);
    }
  } catch (err) {
    console.error(err);
    const code = err?.code || "";

    // If they already exist in Firebase but Postgres failed last time:
    if (code === "auth/email-already-in-use" && !isLogin) {
      setErrorMessage("Account exists in Auth system. Please Sign In to sync your profile.");
      // Option: Automatically switch them to login after a delay or let them click
      return;
    }

    // Mapping the rest of your friendly errors to the state
    const friendly =
      code === "auth/invalid-credential" ? "Invalid email or password." :
      code === "auth/user-not-found" ? "No account found for that email." :
      code === "auth/wrong-password" ? "Wrong password." :
      code === "auth/email-already-in-use" ? "That email is already in use." :
      code === "auth/weak-password" ? "Password is too weak (try 6+ chars)." :
      err?.message || "Auth failed.";

    setErrorMessage(friendly);
  }
};

  const handleGoogle = async () => {
    try {
      const provider = new GoogleAuthProvider();
      const userCred = await signInWithPopup(auth, provider);
      // Trigger role selection for Google sign-in to ensure they are in PostgreSQL
      setTempUser(userCred.user);
      setShowRoleSelection(true);
    } catch (err) {
      console.error(err);
      alert(err?.message || "Google sign-in failed.");
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    if (!formData.email) {
      alert("Enter your email first, then click 'Forgot password?'.");
      return;
    }
    try {
      await sendPasswordResetEmail(auth, formData.email);
      alert("Password reset email sent!");
    } catch (err) {
      console.error(err);
      alert(err?.message || "Could not send reset email.");
    }
  };

  return (
    <div className="page">
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      <div className="left-panel">
        <div className="brand-logo">
          <div className="logo-icon">
            <svg viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div className="brand-name">
            Study<span>Sync</span>
          </div>
        </div>
        <h1 className="tagline">
          Learn together, <br />
          <span className="highlight">grow faster.</span>
        </h1>
        <p className="tagline-sub">
          A single workspace to sync notes, share materials, and collaborate.
        </p>
        <div className="features">
          <div className="feature-pill">
            <div className="dot" />
            Shared Notebooks
          </div>
          <div className="feature-pill">
            <div className="dot" />
            Live Collaboration
          </div>
          <div className="feature-pill">
            <div className="dot" />
            Material Sharing
          </div>
          <div className="feature-pill">
            <div className="dot" />
            Study Groups
          </div>
        </div>
      </div>

      <div className="right-panel">
        <div className="card">
          {!showRoleSelection ? (
            <>
              <div className="tabs">
                <button
                  type="button"
                  className={`tab ${isLogin ? "active" : ""}`}
                  onClick={() => setIsLogin(true)}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  className={`tab ${!isLogin ? "active" : ""}`}
                  onClick={() => setIsLogin(false)}
                >
                  Sign Up
                </button>
              </div>

              <form onSubmit={handleSubmit}>
                {!isLogin && (
                  <div
                    className={`field ${focused === "name" ? "is-focused" : ""}`}
                  >
                    <label>Full Name</label>
                    <div className="input-wrap">
                      <svg className="icon" viewBox="0 0 24 24">
                        <circle cx="12" cy="8" r="4" />
                        <path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
                      </svg>
                      <input
                        type="text"
                        name="name"
                        placeholder="Alex Johnson"
                        value={formData.name}
                        onChange={handleChange}
                        onFocus={() => setFocused("name")}
                        onBlur={() => setFocused(null)}
                      />
                    </div>
                  </div>
                )}
                <div
                  className={`field ${focused === "email" ? "is-focused" : ""}`}
                >
                  <label>Email</label>
                  <div className="input-wrap">
                    <svg className="icon" viewBox="0 0 24 24">
                      <rect x="2" y="4" width="20" height="16" rx="2" />
                      <path d="M22 7l-10 6L2 7" />
                    </svg>
                    <input
                      type="email"
                      name="email"
                      placeholder="you@university.edu"
                      value={formData.email}
                      onChange={handleChange}
                      onFocus={() => setFocused("email")}
                      onBlur={() => setFocused(null)}
                    />
                  </div>
                </div>
                <div
                  className={`field ${focused === "password" ? "is-focused" : ""}`}
                >
                  <label>Password</label>
                  <div className="input-wrap">
                    <svg className="icon" viewBox="0 0 24 24">
                      <rect x="3" y="11" width="18" height="11" rx="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                    <input
                      type={showPassword ? "text" : "password"}
                      name="password"
                      placeholder={isLogin ? "••••••••" : "Create a password"}
                      value={formData.password}
                      onChange={handleChange}
                      onFocus={() => setFocused("password")}
                      onBlur={() => setFocused(null)}
                    />
                  </div>
                </div>
                {isLogin && (
                  <div className="forgot">
                    <a href="#" onClick={handleForgotPassword}>
                      Forgot password?
                    </a>
                  </div>
                )}
                {errorMessage && (
                  <div
                    className="error-text"
                    style={{
                      color: "#ff4d4d",
                      fontSize: "0.85rem",
                      marginBottom: "15px",
                      textAlign: "center",
                      fontWeight: "500",
                    }}
                  >
                    {errorMessage}
                  </div>
                )}

                <button type="submit" className="btn-submit">
                  {isLogin ? "Sign In" : "Create Account"}
                </button>
              </form>

              <div className="divider">
                <div className="divider-line" />
                <span>or</span>
                <div className="divider-line" />
              </div>
              <button
                className="btn-google"
                type="button"
                onClick={handleGoogle}
              >
                Continue with Google
              </button>

              <div className="auth-footer">
                {isLogin ? (
                  <>
                    Don't have an account?{" "}
                    <a onClick={() => setIsLogin(false)}>Sign up</a>
                  </>
                ) : (
                  <>
                    Already have an account?{" "}
                    <a onClick={() => setIsLogin(true)}>Sign in</a>
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="role-selection">
              <h2 className="highlight">One Last Step!</h2>
              <p className="tagline-sub">
                Are you a Student, TA, or Administrator?
              </p>
              <div
                className="role-options"
                style={{
                  marginTop: "20px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                <button
                  className="feature-pill"
                  style={{
                    cursor: "pointer",
                    width: "100%",
                    justifyContent: "center",
                  }}
                  onClick={() =>
                    syncWithBackend(tempUser, "Student", formData.name)
                  }
                >
                  <div className="dot" /> Student
                </button>
                <button
                  className="feature-pill"
                  style={{
                    cursor: "pointer",
                    width: "100%",
                    justifyContent: "center",
                  }}
                  onClick={() => syncWithBackend(tempUser, "TA", formData.name)}
                >
                  <div className="dot" /> Teaching Assistant
                </button>
                <button
                  className="feature-pill"
                  style={{
                    cursor: "pointer",
                    width: "100%",
                    justifyContent: "center",
                  }}
                  onClick={() =>
                    syncWithBackend(tempUser, "Admin", formData.name)
                  }
                >
                  <div className="dot" /> Administrator
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;