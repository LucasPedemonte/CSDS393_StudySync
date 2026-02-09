import Navbar from "./Navbar";
import "./LoginPage.css";

const ChatPage = () => {
  return (
    <div className="page with-navbar">
      <Navbar />
      <div className="page-content">
        <div className="left-panel">
          <h1 className="tagline">
            Discussion <span className="highlight">Forum</span>
          </h1>
          <p className="tagline-sub">
            Connect and collaborate with your peers
          </p>
        </div>
        <div className="right-panel">
          <div className="card">
            <h2 style={{ marginBottom: "12px" }}>Discussion / Chat</h2>
            <p style={{ color: "var(--text-secondary)" }}>
              Empty shell - ready for development
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
