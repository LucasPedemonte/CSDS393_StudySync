import { Link } from "react-router-dom";
import Navbar from "./Navbar";
import "./LoginPage.css";

const HomePage = () => {
  const cards = [
    {
      title: "Study Groups",
      description: "Manage your study groups and schedule",
      link: "/calendar",
      icon: "📅",
    },
    {
      title: "Discussion",
      description: "Connect and collaborate with your peers",
      link: "/chat",
      icon: "💬",
    },
    {
      title: "Library",
      description: "Access shared materials and study resources",
      link: "/resources",
      icon: "📚",
    },
    {
      title: "Personal",
      description: "Your study progress and personal workspace",
      link: "/dashboard",
      icon: "👤",
    },
  ];

  return (
    <div className="page with-navbar">
      <Navbar />
      {/* Ambient blobs */}
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      <div className="home-content">
        <div className="home-header">
          <h1 className="tagline">
            Welcome to <span className="highlight">StudySync</span>
          </h1>
          <p className="tagline-sub">
            Choose a section to get started
          </p>
        </div>

        <div className="home-grid">
          {cards.map((card) => (
            <Link
              key={card.link}
              to={card.link}
              className="home-card"
            >
              <div className="home-card-icon">{card.icon}</div>
              <h3 className="home-card-title">{card.title}</h3>
              <p className="home-card-description">{card.description}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

export default HomePage;
