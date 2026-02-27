import { useState, useEffect } from "react";
import { auth } from "./firebase";
import { onAuthStateChanged, EmailAuthProvider, reauthenticateWithCredential, verifyBeforeUpdateEmail, updatePassword } from "firebase/auth";
import Navbar from "./Navbar";
import "./DashboardPage.css";

const DashboardPage = () => {
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editData, setEditData] = useState({ name: "", email: "", role: "", newPass: "", confirmPass: "", currentPass: "" });
  const [needsReauth, setNeedsReauth] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        try {
          const response = await fetch(`http://localhost:8000/user/${user.uid}`);
          const data = await response.json();
          setUserProfile(data);
          setEditData({ ...editData, name: data.full_name, email: data.email, role: data.role });
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
  
  // Check if we are changing sensitive fields
  const isChangingEmail = editData.email !== userProfile.email;
  const isChangingPass = editData.newPass !== "";

  try {
    // If sensitive changes are made but we haven't re-authenticated yet
    if ((isChangingEmail || isChangingPass) && !needsReauth) {
      setNeedsReauth(true); // This will show the password field in your UI
      return; 
    }

    // Perform Re-authentication using the password from your custom UI field
    if (needsReauth) {
      const credential = EmailAuthProvider.credential(user.email, editData.currentPass);
      await reauthenticateWithCredential(user, credential);
    }

    // 1. Update Password in Firebase
    if (isChangingPass) {
      if (editData.newPass !== editData.confirmPass) {
        throw new Error("New passwords do not match.");
      }
      await updatePassword(user, editData.newPass);
    }

    // 2. Trigger Email Verification in Firebase
    if (isChangingEmail) {
      await verifyBeforeUpdateEmail(user, editData.email);
      alert("Verification email sent! Please check your inbox to confirm the change.");
    }

    // 3. Update PostgreSQL (Keep the old email until they verify the new one)
    const response = await fetch(`http://localhost:8000/user/${user.uid}/update`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        firebase_uid: user.uid,
        email: userProfile.email, // Use current email to avoid login lockouts
        full_name: editData.name,
        role: editData.role,
      }),
    });

    if (response.ok) {
      setUserProfile({ ...userProfile, full_name: editData.name, role: editData.role });
      setShowModal(false);
      setNeedsReauth(false);
      setEditData({ ...editData, currentPass: "", newPass: "", confirmPass: "" });
    }
  } catch (err) {
    alert(err.message || "Failed to update profile.");
    // If re-auth fails, allow the user to try the password again
    if (err.code === 'auth/wrong-password') setNeedsReauth(true);
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

        {showModal && (
          <div className="modal-overlay">
            <div className="modal-card">
              <h3>Update Profile</h3>
              <form onSubmit={handleUpdate}>
                <div className="field"><label>Full Name</label><input type="text" value={editData.name} onChange={(e) => setEditData({...editData, name: e.target.value})} /></div>
                <div className="field"><label>Email Address</label><input type="email" value={editData.email} onChange={(e) => setEditData({...editData, email: e.target.value})} /></div>
                <div className="field">
                  <label>Role</label>
                  <select value={editData.role} onChange={(e) => setEditData({...editData, role: e.target.value})}>
                    <option value="Student">Student</option>
                    <option value="TA">Teaching Assistant</option>
                    <option value="Admin">Administrator</option>
                  </select>
                </div>

                <hr className="divider-line" />
                <div className="field"><label>New Password</label><input type="password" value={editData.newPass} onChange={(e) => setEditData({...editData, newPass: e.target.value})} /></div>
                {editData.newPass && (
                   <div className="field"><label>Confirm New Password</label><input type="password" value={editData.confirmPass} onChange={(e) => setEditData({...editData, confirmPass: e.target.value})} /></div>
                )}

                {needsReauth && (
                  <div className="reauth-box">
                    <p>Enter current password to confirm sensitive changes:</p>
                    <div className="field"><input type="password" placeholder="Current Password" value={editData.currentPass} onChange={(e) => setEditData({...editData, currentPass: e.target.value})} required /></div>
                  </div>
                )}

                <div className="modal-actions">
                  <button type="button" className="btn-subtle-link" onClick={() => {setShowModal(false); setNeedsReauth(false);}}>Cancel</button>
                  <button type="submit" className="btn-submit">{needsReauth ? "Confirm Changes" : "Save Changes"}</button>
                </div>
              </form>
            </div>
          </div>
        )}
        
        <hr className="divider-line" />
        <div className="dashboard-grid">
          <div className="card"><h3>Upcoming Meetings</h3><p className="tagline-sub">No meetings scheduled yet.</p></div>
          <div className="card"><h3>Study Stats</h3><p className="tagline-sub">Usage tracking coming soon.</p></div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;