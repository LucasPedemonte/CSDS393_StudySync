import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { auth } from "./firebase";
import { onAuthStateChanged } from "firebase/auth";
import "./HomePage.css";

const HomePage = () => {
  const [courses, setCourses] = useState([]);
  const [userProfile, setUserProfile] = useState(null);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [courseCode, setCourseCode] = useState("");
  const [newCourseName, setNewCourseName] = useState("");
  const [newCourseCode, setNewCourseCode] = useState("");
  const navigate = useNavigate();

  // Fetch user profile to check for TA/Admin roles
  const fetchProfile = useCallback(async (firebase_uid) => {
    try {
      const response = await fetch(`http://localhost:8000/user/${firebase_uid}`);
      if (response.ok) {
        const data = await response.json();
        setUserProfile(data);
      }
    } catch (err) {
      console.error("Error fetching profile:", err);
    }
  }, []);

  const fetchUserCourses = useCallback(async (firebase_uid) => {
    if (!firebase_uid) return;
    try {
      const res = await axios.get(
        `http://localhost:8000/users/${firebase_uid}/courses`
      );
      setCourses(res.data);
    } catch (err) {
      console.error("Error fetching courses", err);
    }
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        fetchProfile(user.uid);
        fetchUserCourses(user.uid);
      }
    });
    return () => unsubscribe();
  }, [fetchUserCourses, fetchProfile]);

  const handleJoinCourse = async (e) => {
    e.preventDefault();
    const user = auth.currentUser;
    if (!user) return;

    try {
      await axios.post(
        `http://localhost:8000/courses/join?course_code=${courseCode}&firebase_uid=${user.uid}`
      );
      setCourseCode("");
      setShowJoinModal(false);
      fetchUserCourses(user.uid);
    } catch (err) {
      alert("Invalid course code or already enrolled.");
    }
  };

  const handleCreateCourse = async (e) => {
    e.preventDefault();
    const user = auth.currentUser;
    if (!user) return;

    try {
      await axios.post("http://localhost:8000/courses", {
        name: newCourseName,
        course_code: newCourseCode,
        owner_id: user.uid, // Use Firebase UID
      });
      setNewCourseName("");
      setNewCourseCode("");
      setShowCreateModal(false);
      fetchUserCourses(user.uid);
    } catch (err) {
      const errorMessage =
        err.response?.data?.detail || "Failed to create course.";
      alert(errorMessage);
      console.error("Course creation error:", err.response?.data);
    }
  };

  return (
    <div className="home-content">
      <header className="page-header">
        <h1 className="page-title">My Classes</h1>
        <div style={{ display: "flex", gap: "12px" }}>
          <button
            className="btn-primary"
            onClick={() => setShowJoinModal(true)}
          >
            + Join Class
          </button>

          {(userProfile?.role === "TA" || userProfile?.role === "Admin") && (
            <button
              className="btn-subtle"
              onClick={() => setShowCreateModal(true)}
            >
              + Create Class
            </button>
          )}
        </div>
      </header>

      <div className="home-grid">
        {courses.map((course) => (
          <div
            key={course.id}
            className="home-card"
            onClick={() => navigate(`/class/${course.id}/summary`)}
          >
            <div className="home-card-icon">{course.course_code[0]}</div>
            <h3 className="home-card-title">{course.name}</h3>
            <p className="home-card-description">{course.course_code}</p>
          </div>
        ))}

        {courses.length === 0 && (
          <div className="no-classes">
            <p>
              You haven't joined any classes yet. Use a code to get started!
            </p>
          </div>
        )}
      </div>

      {/* Join Class Modal */}
      {showJoinModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h2 className="brand-name">Join a New Class</h2>
            <p className="tagline-sub">Enter your class code below</p>
            <form onSubmit={handleJoinCourse}>
              <div className="field">
                <input
                  type="text"
                  placeholder="Enter Course Code (e.g. CSDS393)"
                  value={courseCode}
                  onChange={(e) => setCourseCode(e.target.value)}
                  required
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-subtle"
                  onClick={() => setShowJoinModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Join
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Class Modal */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h2 className="brand-name">Create Workspace</h2>
            <p className="tagline-sub">Set up a new class environment</p>
            <form onSubmit={handleCreateCourse}>
              <div className="field">
                <label>Course Name</label>
                <input
                  type="text"
                  placeholder="e.g. Data Science"
                  value={newCourseName}
                  onChange={(e) => setNewCourseName(e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label>Course Code</label>
                <input
                  type="text"
                  placeholder="e.g. CSDS393"
                  value={newCourseCode}
                  onChange={(e) => setNewCourseCode(e.target.value)}
                  required
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-subtle"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default HomePage;