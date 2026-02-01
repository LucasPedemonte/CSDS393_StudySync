import { useState } from "react";
import "./LoginPage.css";

const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });
  const [focused, setFocused] = useState(null);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    alert(isLogin ? "Logging in..." : "Signing up...");
  };

  return (
    <div className="page">
      {/* Ambient blobs */}
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      {/* Left — Branding */}
      <div className="left-panel">
        <div className="brand-logo">
          <div className="logo-icon">
            <svg viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div className="brand-name">Study<span>Sync</span></div>
        </div>

        <h1 className="tagline">
          Learn together,<br />
          <span className="highlight">grow faster.</span>
        </h1>
        <p className="tagline-sub">
          A single workspace to sync notes, share materials, and collaborate with your study group — all in real time.
        </p>

        <div className="features">
          <div className="feature-pill"><div className="dot" />Shared Notebooks</div>
          <div className="feature-pill"><div className="dot" />Live Collaboration</div>
          <div className="feature-pill"><div className="dot" />Material Sharing</div>
          <div className="feature-pill"><div className="dot" />Study Groups</div>
        </div>
      </div>

      {/* Right — Auth Card */}
      <div className="right-panel">
        <div className="card">
          {/* Tabs */}
          <div className="tabs">
            <button className={`tab ${isLogin ? "active" : ""}`} onClick={() => setIsLogin(true)}>Sign In</button>
            <button className={`tab ${!isLogin ? "active" : ""}`} onClick={() => setIsLogin(false)}>Sign Up</button>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Name field — only on sign up */}
            {!isLogin && (
              <div className={`field ${focused === "name" ? "is-focused" : ""}`}>
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

            {/* Email */}
            <div className={`field ${focused === "email" ? "is-focused" : ""}`}>
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

            {/* Password */}
            <div className={`field ${focused === "password" ? "is-focused" : ""}`}>
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
                <button type="button" className="toggle-pw" onClick={() => setShowPassword(!showPassword)}>
                  {showPassword ? (
                    <svg viewBox="0 0 24 24">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Forgot (login only) */}
            {isLogin && (
              <div className="forgot">
                <a href="#">Forgot password?</a>
              </div>
            )}

            <button type="submit" className="btn-submit">
              {isLogin ? "Sign In" : "Create Account"}
            </button>
          </form>

          {/* Google sign-in */}
          <div className="divider">
            <div className="divider-line" />
            <span>or</span>
            <div className="divider-line" />
          </div>
          <button className="btn-google">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Continue with Google
          </button>

          {/* Footer toggle */}
          <div className="auth-footer">
            {isLogin ? (
              <>Don't have an account? <a onClick={() => setIsLogin(false)}>Sign up</a></>
            ) : (
              <>Already have an account? <a onClick={() => setIsLogin(true)}>Sign in</a></>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;