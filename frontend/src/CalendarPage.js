import Navbar from "./Navbar";
import "./LoginPage.css";

const CalendarPage = () => {
  return (
    <div className="page with-navbar">
      <Navbar />
      <div className="page-content">
        <div className="left-panel">
          <h1 className="tagline">
            Study <span className="highlight">Groups</span>
          </h1>
          <p className="tagline-sub">
            Manage your study groups and schedule
          </p>
        </div>
        <div className="right-panel">
          <div className="card">
            <h2 style={{ marginBottom: "12px" }}>Calendar / Study Groups</h2>
            <p style={{ color: "var(--text-secondary)" }}>
              Empty shell - ready for development
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalendarPage;
