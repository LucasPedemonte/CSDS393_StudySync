import Navbar from "./Navbar";
import "./LoginPage.css";

const ResourcesPage = () => {
  return (
    <div className="page with-navbar">
      <Navbar />
      <div className="page-content">
        <div className="left-panel">
          <h1 className="tagline">
            Resource <span className="highlight">Library</span>
          </h1>
          <p className="tagline-sub">
            Access shared materials and study resources
          </p>
        </div>
        <div className="right-panel">
          <div className="card">
            <h2 style={{ marginBottom: "12px" }}>Library / Resources</h2>
            <p style={{ color: "var(--text-secondary)" }}>
              Empty shell - ready for development
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResourcesPage;
