import { useState, useEffect } from "react";
import { NavLink, useParams, useNavigate } from "react-router-dom";
import { auth } from "./firebase";
import "./ClassHeader.css";

const ClassHeader = () => {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const [showDropdown, setShowDropdown] = useState(false);
  const [courses, setCourses] = useState([]);
  const [currentCourse, setCurrentCourse] = useState(null);

  // Fetch user's courses for the dropdown
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const user = auth.currentUser;
        if (!user) return;

        const response = await fetch(`http://localhost:8000/users/${user.uid}/courses`);
        if (response.ok) {
          const data = await response.json();
          setCourses(data);
          
          // Find current course
          const current = data.find((c) => c.id === parseInt(courseId));
          if (current) {
            setCurrentCourse(current);
          }
        }
      } catch (err) {
        console.error("Error fetching courses for dropdown:", err);
      }
    };

    if (courseId) {
      fetchCourses();
    }
  }, [courseId]);

  const handleCourseSwitch = (newCourseId) => {
    // Navigate to summary page of the new course
    navigate(`/class/${newCourseId}/summary`);
    setShowDropdown(false);
  };

  return (
    <div className="class-header-container">
      {/* Class Title with Dropdown */}
      <div className="class-header-top">
        <div className="class-title-with-dropdown">
          <h2 className="class-title">
            {currentCourse?.name || "Course"}
          </h2>
          <button
            className="dropdown-trigger"
            onClick={() => setShowDropdown(!showDropdown)}
            title="Switch classes"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

          {/* Dropdown Menu */}
          {showDropdown && (
            <div className="class-dropdown">
              <div className="dropdown-label">Switch Class</div>
              {courses.length > 0 ? (
                <div className="dropdown-list">
                  {courses.map((course) => (
                    <button
                      key={course.id}
                      className={`dropdown-item ${
                        course.id === currentCourse?.id ? "active" : ""
                      }`}
                      onClick={() => handleCourseSwitch(course.id)}
                    >
                      <span className="course-icon">
                        {course.course_code[0]}
                      </span>
                      <div className="course-info">
                        <div className="course-name">{course.name}</div>
                        <div className="course-code">{course.course_code}</div>
                      </div>
                      {course.id === currentCourse?.id && (
                        <span className="check-mark">✓</span>
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="dropdown-empty">No classes found</div>
              )}
            </div>
          )}
        </div>

        {/* Course Code and Quick Info */}
        <div className="class-quick-info">
          <span className="course-code-badge">{currentCourse?.course_code}</span>
        </div>
      </div>

      {/* Secondary Navigation (Tabs) */}
      <nav className="secondary-navbar">
        <NavLink
          to={`/class/${courseId}/summary`}
          className={({ isActive }) => `sec-nav-link ${isActive ? "active" : ""}`}
        >
          Summary
        </NavLink>
        <NavLink
          to={`/class/${courseId}/resources`}
          className={({ isActive }) => `sec-nav-link ${isActive ? "active" : ""}`}
        >
          Library
        </NavLink>
        <NavLink
          to={`/class/${courseId}/chat`}
          className={({ isActive }) => `sec-nav-link ${isActive ? "active" : ""}`}
        >
          Chat
        </NavLink>
        <NavLink
          to={`/class/${courseId}/schedule`}
          className={({ isActive }) => `sec-nav-link ${isActive ? "active" : ""}`}
        >
          Study Sessions
        </NavLink>
      </nav>
    </div>
  );
};

export default ClassHeader;
