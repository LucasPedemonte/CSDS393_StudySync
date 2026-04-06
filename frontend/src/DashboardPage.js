import { useState, useEffect, useCallback } from "react";
import { auth } from "./firebase";
import {
  onAuthStateChanged,
  EmailAuthProvider,
  reauthenticateWithCredential,
  verifyBeforeUpdateEmail,
  updatePassword,
} from "firebase/auth";
import { useParams } from "react-router-dom";
import "./DashboardPage.css";

const API_BASE = "http://localhost:8000";

const DashboardPage = ({ isClassScoped = false }) => {
  const { courseId } = useParams();
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editData, setEditData] = useState({
    name: "",
    email: "",
    role: "",
    newPass: "",
    confirmPass: "",
    currentPass: "",
  });
  const [needsReauth, setNeedsReauth] = useState(false);
  const [flaggedPosts, setFlaggedPosts] = useState([]);
  const [classSummary, setClassSummary] = useState({
    upcomingSessions: [],
    completedHours: 0,
    completedSessions: 0,
  });
  const [classSummaryLoading, setClassSummaryLoading] = useState(false);

  const fetchProfile = useCallback(async (firebase_uid) => {
    try {
      const response = await fetch(
        `${API_BASE}/user/${firebase_uid}`,
      );
      if (response.ok) {
        const data = await response.json();
        setUserProfile(data);
        setEditData((prev) => ({
          ...prev,
          name: data.full_name,
          email: data.email,
          role: data.role,
        }));
      }
    } catch (err) {
      console.error("Error fetching profile:", err);
    }
  }, []);

  const fetchFlaggedPosts = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/posts/flagged`);
      if (res.ok) {
        const data = await res.json();
        setFlaggedPosts(data);
      }
    } catch (err) {
      console.error("Error fetching flagged posts:", err);
    }
  }, []);

  const fetchClassSummary = useCallback(async () => {
    if (!isClassScoped || !courseId || !userProfile?.email) {
      setClassSummary({
        upcomingSessions: [],
        completedHours: 0,
        completedSessions: 0,
      });
      return;
    }

    setClassSummaryLoading(true);
    try {
      const params = new URLSearchParams({
        requester_email: userProfile.email,
      });
      const response = await fetch(
        `${API_BASE}/study-sessions/course/${courseId}/summary?${params.toString()}`,
      );

      if (!response.ok) {
        throw new Error("Failed to load class dashboard summary");
      }

      const data = await response.json();
      setClassSummary({
        upcomingSessions: data.upcoming_sessions || [],
        completedHours: data.completed_hours || 0,
        completedSessions: data.completed_sessions || 0,
      });
    } catch (err) {
      console.error("Error fetching class dashboard summary:", err);
      setClassSummary({
        upcomingSessions: [],
        completedHours: 0,
        completedSessions: 0,
      });
    } finally {
      setClassSummaryLoading(false);
    }
  }, [courseId, isClassScoped, userProfile?.email]);

  const formatSessionTime = (startsAt, endsAt) => {
    const start = new Date(startsAt);
    const end = new Date(endsAt);
    const dayLabel = start.toLocaleDateString([], {
      month: "short",
      day: "numeric",
      weekday: "short",
    });
    const timeLabel = `${start.toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    })} - ${end.toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    })}`;

    return `${dayLabel} • ${timeLabel}`;
  };

  const handleDismissFlag = async (postId) => {
    try {
      const res = await fetch(
        `${API_BASE}/posts/${postId}/dismiss-flag`,
        {
          method: "POST",
        },
      );
      if (res.ok) {
        setFlaggedPosts((prev) => prev.filter((p) => p.id !== postId));
      }
    } catch (err) {
      console.error("Dismiss failed", err);
    }
  };

  const handleDeletePost = async (postId) => {
    if (
      !window.confirm("Are you sure you want to delete this flagged content?")
    )
      return;
    try {
      const res = await fetch(
        `${API_BASE}/posts/${postId}?user_uid=${userProfile.firebase_uid}`,
        { method: "DELETE" },
      );
      if (res.ok) {
        setFlaggedPosts((prev) => prev.filter((p) => p.id !== postId));
      }
    } catch (err) {
      console.error("Delete failed", err);
    }
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        await fetchProfile(user.uid);
      }
      setLoading(false);
    });
    return () => unsubscribe();
  }, [fetchProfile]);

  useEffect(() => {
    if (
      userProfile &&
      (userProfile.role === "TA" || userProfile.role === "Admin")
    ) {
      fetchFlaggedPosts();
    }
  }, [userProfile, fetchFlaggedPosts]);

  useEffect(() => {
    fetchClassSummary();
  }, [fetchClassSummary]);

  const handleUpdate = async (e) => {
    e.preventDefault();
    const user = auth.currentUser;
    const isChangingEmail = editData.email !== userProfile.email;
    const isChangingPass = editData.newPass !== "";

    try {
      if ((isChangingEmail || isChangingPass) && !needsReauth) {
        setNeedsReauth(true);
        return;
      }
      if (needsReauth) {
        const credential = EmailAuthProvider.credential(
          user.email,
          editData.currentPass,
        );
        await reauthenticateWithCredential(user, credential);
      }
      if (isChangingPass) {
        if (editData.newPass !== editData.confirmPass)
          throw new Error("Passwords do not match.");
        await updatePassword(user, editData.newPass);
      }
      if (isChangingEmail) {
        await verifyBeforeUpdateEmail(user, editData.email);
        alert("Verification email sent!");
      }

      const response = await fetch(
        `${API_BASE}/user/${user.uid}/update`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            firebase_uid: user.uid,
            email: userProfile.email,
            full_name: editData.name,
            role: editData.role,
          }),
        },
      );

      if (response.ok) {
        setUserProfile({
          ...userProfile,
          full_name: editData.name,
          role: editData.role,
        });
        setShowModal(false);
        setNeedsReauth(false);
      }
    } catch (err) {
      alert(err.message || "Failed to update profile.");
      if (err.code === "auth/wrong-password") setNeedsReauth(true);
    }
  };

  if (loading) return <div className="page">Loading...</div>;

  const pageTitle = isClassScoped ? "Class Dashboard" : userProfile?.full_name;

  return (
    <div className="dashboard-container">
      <div className="dashboard-content">
        <header className="dashboard-header">
          <h1 className="page-title">{pageTitle}</h1>
          {!isClassScoped && (
            <>
              <div className="info-bubbles">
                <div className="feature-pill">
                  <div className="dot" />
                  {userProfile?.email}
                </div>
                <div className="feature-pill">
                  <div className="dot" />
                  {userProfile?.role}
                </div>
                <div className="feature-pill">
                  <div className="dot" />
                  GCal: {userProfile?.gcal_connected ? "Connected" : "Not"}
                </div>
              </div>
              <button className="btn-subtle" onClick={() => setShowModal(true)}>
                Update personal info
              </button>
            </>
          )}
        </header>

        {/* MODERATION SECTION */}
        {flaggedPosts.length > 0 &&
          (userProfile?.role === "TA" || userProfile?.role === "Admin") && (
            <div className="moderation-alert-box">
              <div className="mod-alert-header">
                <h3>
                  ⚠️ Urgent: {flaggedPosts.length} Flagged Posts Need Review
                </h3>
              </div>
              <div className="moderation-container">
                {flaggedPosts.map((post) => (
                  <div key={post.id} className="flagged-post-wrapper">
                    <div className="flagged-post-card">
                      <div className="post-header">
                        <div className="post-author-info">
                          <div className="author-avatar">
                            {post.author_name
                              ? post.author_name.charAt(0).toUpperCase()
                              : "?"}
                          </div>
                          <div className="author-details">
                            <div className="author-name">
                              {post.author_name}
                            </div>
                            <span className={`author-role ${post.author_role}`}>
                              {post.author_role}
                            </span>
                          </div>
                        </div>
                        <div className="post-timestamp">
                          {new Date(post.created_at).toLocaleDateString()}
                        </div>
                      </div>

                      <div className="post-content">
                        <h3 className="post-title">{post.title}</h3>
                        {post.description && (
                          <p className="post-description">{post.description}</p>
                        )}
                        {post.resource_link && (
                          <a
                            href={post.resource_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="post-resource-link"
                          >
                            🔗 {post.resource_link}
                          </a>
                        )}
                      </div>

                      {/* Action Row centered within the card */}
                      <div className="moderation-actions-footer">
                        <button
                          className="btn-subtle dismiss-btn"
                          onClick={() => handleDismissFlag(post.id)}
                        >
                          Dismiss Flag
                        </button>
                        <button
                          className="btn-primary delete-btn"
                          onClick={() => handleDeletePost(post.id)}
                        >
                          Delete Post
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        {/* UPDATE PROFILE MODAL */}
        {showModal && !isClassScoped && (
          <div className="modal-overlay">
            <div className="modal-card">
              <h3>Update Profile</h3>
              <form onSubmit={handleUpdate}>
                <div className="field">
                  <label>Full Name</label>
                  <input
                    type="text"
                    value={editData.name}
                    onChange={(e) =>
                      setEditData({ ...editData, name: e.target.value })
                    }
                  />
                </div>
                <div className="field">
                  <label>Role</label>
                  <select
                    value={editData.role}
                    onChange={(e) =>
                      setEditData({ ...editData, role: e.target.value })
                    }
                  >
                    <option value="Student">Student</option>
                    <option value="TA">Teaching Assistant</option>
                    <option value="Admin">Administrator</option>
                  </select>
                </div>

                <hr className="divider-line" />
                <div className="field">
                  <label>New Password</label>
                  <input
                    type="password"
                    value={editData.newPass}
                    onChange={(e) =>
                      setEditData({ ...editData, newPass: e.target.value })
                    }
                  />
                </div>
                {editData.newPass && (
                  <div className="field">
                    <label>Confirm New Password</label>
                    <input
                      type="password"
                      value={editData.confirmPass}
                      onChange={(e) =>
                        setEditData({
                          ...editData,
                          confirmPass: e.target.value,
                        })
                      }
                    />
                  </div>
                )}

                {needsReauth && (
                  <div className="reauth-box">
                    <p>Enter current password to confirm changes:</p>
                    <div className="field">
                      <input
                        type="password"
                        placeholder="Current Password"
                        value={editData.currentPass}
                        onChange={(e) =>
                          setEditData({
                            ...editData,
                            currentPass: e.target.value,
                          })
                        }
                        required
                      />
                    </div>
                  </div>
                )}

                <div className="modal-actions">
                  <button
                    type="button"
                    className="btn-subtle"
                    onClick={() => {
                      setShowModal(false);
                      setNeedsReauth(false);
                    }}
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary">
                    {needsReauth ? "Confirm Changes" : "Save Changes"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        <div className="dashboard-grid">
          <div className="card">
            <h3>Upcoming Meetings</h3>
            {isClassScoped ? (
              classSummaryLoading ? (
                <p className="tagline-sub">Loading upcoming meetings...</p>
              ) : classSummary.upcomingSessions.length > 0 ? (
                <div className="dashboard-session-list">
                  {classSummary.upcomingSessions.map((session) => (
                    <div key={session.id} className="dashboard-session-item">
                      <div className="dashboard-session-title">{session.title}</div>
                      <div className="dashboard-session-meta">
                        {formatSessionTime(session.starts_at, session.ends_at)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="tagline-sub">No upcoming meetings for this course yet.</p>
              )
            ) : (
              <p className="tagline-sub">No meetings scheduled yet.</p>
            )}
          </div>
          <div className="card">
            <h3>Study Stats</h3>
            {isClassScoped ? (
              classSummaryLoading ? (
                <p className="tagline-sub">Loading study stats...</p>
              ) : (
                <div className="study-stat-block">
                  <div className="study-stat-value">
                    {classSummary.completedHours.toFixed(1)} hours
                  </div>
                  <p className="tagline-sub">
                    Completed so far in this course across {classSummary.completedSessions} session
                    {classSummary.completedSessions === 1 ? "" : "s"}.
                  </p>
                </div>
              )
            ) : (
              <p className="tagline-sub">Usage tracking coming soon.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
