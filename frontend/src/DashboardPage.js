import { useState, useEffect } from "react";
import { auth } from "./firebase";
import { onAuthStateChanged, updateEmail } from "firebase/auth";
import Navbar from "./Navbar";
import "./DashboardPage.css";

const DashboardPage = () => {
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editData, setEditData] = useState({ name: "", email: "", role: "" });

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        try {
          const response = await fetch(`http://localhost:8000/user/${user.uid}`);
          const data = await response.json();
          setUserProfile(data);
          setEditData({ name: data.full_name, email: data.email, role: data.role });
        } catch (err) {
          console.error("Error fetching profile:", err);
        }
      }
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleUpdate = async (e) => {
    e.preventDefault();
    const user = auth.currentUser;

    try {
      // 1. Update Firebase Email (if changed)
      if (editData.email !== userProfile.email) {
        await updateEmail(user, editData.email);
      }

      // 2. Update PostgreSQL Backend
      const response = await fetch(`http://localhost:8000/user/${user.uid}/update`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          firebase_uid: user.uid,
          email: editData.email,
          full_name: editData.name,
          role: editData.role,
        }),
      });

      if (response.ok) {
        setUserProfile({ ...userProfile, full_name: editData.name, email: editData.email, role: editData.role });
        setShowModal(false);
      }
    } catch (err) {
      alert(err.message || "Update failed. You may need to log in again to change your email.");
    }
  };

  if (loading) return <div className="page">Loading...</div>;

  return (
    <div className="dashboard-container">
      <Navbar />
      <div className="dashboard-content">
        <header className="dashboard-header">
          <h1 className="user-name-title">{userProfile?.full_name}</h1>
          <div className="info-bubbles">
            <div className="feature-pill"><div className="dot" />{userProfile?.email}</div>
            <div className="feature-pill"><div className="dot" />{userProfile?.role}</div>
            <div className="feature-pill"><div className="dot" />GCal: {userProfile?.gcal_connected ? "Connected" : "Not"}</div>
          </div>
          <button className="btn-subtle-link" onClick={() => setShowModal(true)}>
            Update personal info
          </button>
        </header>

        {/* MODAL OVERLAY */}
        {showModal && (
          <div className="modal-overlay">
            <div className="modal-card">
              <h3>Update Profile</h3>
              <form onSubmit={handleUpdate}>
                <div className="field">
                  <label>Full Name</label>
                  <input 
                    type="text" 
                    value={editData.name} 
                    onChange={(e) => setEditData({...editData, name: e.target.value})} 
                  />
                </div>
                <div className="field">
                  <label>Email Address</label>
                  <input 
                    type="email" 
                    value={editData.email} 
                    onChange={(e) => setEditData({...editData, email: e.target.value})} 
                  />
                </div>
                <div className="field">
                  <label>Role</label>
                  <select 
                    value={editData.role} 
                    onChange={(e) => setEditData({...editData, role: e.target.value})}
                  >
                    <option value="Student">Student</option>
                    <option value="TA">Teaching Assistant</option>
                    <option value="Admin">Administrator</option>
                  </select>
                </div>
                <div className="modal-actions">
                  <button type="button" className="btn-subtle-link" onClick={() => setShowModal(false)}>Cancel</button>
                  <button type="submit" className="btn-submit">Save Changes</button>
                </div>
              </form>
            </div>
          </div>
        )}
        <hr className="divider-line" />

      {/* Main App Content Grid */}
      <div className="dashboard-grid">
        <div className="card">
          <h3>Upcoming Meetings</h3>
          <p className="tagline-sub">No meetings scheduled yet.</p>
        </div>
        <div className="card">
          <h3>Study Stats</h3>
          <p className="tagline-sub">Usage tracking coming soon.</p>
        </div>
      </div>
    </div>
  </div>
);
};

export default DashboardPage;