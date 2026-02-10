import Navbar from "./Navbar";
import "./LoginPage.css";

const DashboardPage = () => {
  return (
    <div className="page with-navbar">
      <Navbar />
      <div className="page-content">
        <div className="left-panel">
          <h1 className="tagline">
            Personal <span className="highlight">Dashboard</span>
          </h1>
          <p className="tagline-sub">
            Your study progress and personal workspace
          </p>
        </div>
        <div className="right-panel">
          <div className="card">
            <h2 style={{ marginBottom: "12px" }}>Personal Dashboard</h2>
            <p style={{ color: "var(--text-secondary)" }}>
              Empty shell - ready for development
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
