import "./LoginPage.css"; // reuse your theme styles

const HomePage = () => {
  return (
    <div className="page">
      {/* Ambient blobs */}
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      <div className="left-panel">
        <h1 className="tagline">
          Welcome to <span className="highlight">StudySync</span>
        </h1>
        <p className="tagline-sub">
          You’re logged in
        </p>

        <div className="features">
          <div className="feature-pill">
            <div className="dot" />
            Create a study group
          </div>
          <div className="feature-pill">
            <div className="dot" />
            Share notes
          </div>
          <div className="feature-pill">
            <div className="dot" />
            Collaborate live
          </div>
        </div>
      </div>

      <div className="right-panel">
        <div className="card">
          <h2 style={{ marginBottom: "12px" }}>Home</h2>
          <p style={{ color: "var(--text-secondary)" }}>
            placeholder home page
          </p>
        </div>
      </div>
    </div>
  );
};

export default HomePage;