import "./SchedulePage.css";
import { useEffect, useState, useCallback } from "react";
import { auth } from "./firebase";
import { useParams } from "react-router-dom";

const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:8000";
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

const loadGoogleScript = () =>
  new Promise((resolve, reject) => {
    if (window.google?.accounts?.oauth2) {
      resolve();
      return;
    }

    const existing = document.querySelector('script[data-google-identity="1"]');
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Could not load Google Identity script")));
      return;
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.dataset.googleIdentity = "1";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load Google Identity script"));
    document.body.appendChild(script);
  });

const getWeekRange = (date) => {
  const start = new Date(date);
  start.setHours(0, 0, 0, 0);
  start.setDate(start.getDate() - start.getDay());

  const end = new Date(start);
  end.setDate(end.getDate() + 7);

  return { start, end };
};

const formatHourLabel = (hour) =>
  new Date(2000, 0, 1, hour).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });

const normalizeSearchValue = (value) => value.trim().toLowerCase();

const toLocalDateTimeInputValue = (date) => {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  const hours = `${date.getHours()}`.padStart(2, "0");
  const minutes = `${date.getMinutes()}`.padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
};

const SchedulePage = () => {
  const { courseId } = useParams();
  const isClassScoped = Boolean(courseId);
  const [gcalConnected, setGcalConnected] = useState(false);
  const [classmates, setClassmates] = useState([]);
  const [selectedClassmates, setSelectedClassmates] = useState([]);
  const [calendarView, setCalendarView] = useState("mine");
  const [availabilityByEmail, setAvailabilityByEmail] = useState({});
  const [showScheduleMeetingModal, setShowScheduleMeetingModal] = useState(false);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [courses, setCourses] = useState([]);
  const [activeCourse, setActiveCourse] = useState(null);
  const [currentWeek, setCurrentWeek] = useState(new Date());
  const [compareSearchQuery, setCompareSearchQuery] = useState("");
  const [meetingSearchQuery, setMeetingSearchQuery] = useState("");
  const [upcomingSessions, setUpcomingSessions] = useState([]);

  const user = auth.currentUser;
  const userEmail = user?.email || "";

  const [meetingForm, setMeetingForm] = useState({
    title: "",
    startTime: "",
    endTime: "",
    courseId: courseId || "",
  });

  const getGoogleAccessToken = useCallback(async (prompt = "") => {
    if (!GOOGLE_CLIENT_ID) {
      throw new Error("Missing REACT_APP_GOOGLE_CLIENT_ID in frontend env");
    }

    await loadGoogleScript();

    return new Promise((resolve, reject) => {
      const tokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: "https://www.googleapis.com/auth/calendar.readonly",
        callback: (response) => {
          if (response?.access_token) {
            resolve(response.access_token);
            return;
          }
          reject(new Error(response?.error || "Google OAuth failed"));
        },
      });

      tokenClient.requestAccessToken({ prompt });
    });
  }, []);

  const fetchAvailability = useCallback(async (emails) => {
    if (!userEmail || emails.length === 0) {
      setAvailabilityByEmail({});
      return;
    }

    try {
      const { start, end } = getWeekRange(currentWeek);
      const params = new URLSearchParams({
        time_min: start.toISOString(),
        time_max: end.toISOString(),
      });
      emails.forEach((email) => params.append("user_emails", email));

      const response = await fetch(`${API_BASE}/availability?${params.toString()}`);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to load availability");
      }

      const data = await response.json();
      setAvailabilityByEmail(data.availability || {});
    } catch (error) {
      console.error("Error fetching availability:", error);
      setStatus(`Error: ${error.message}`);
    }
  }, [currentWeek, userEmail]);

  const syncGoogleCalendar = useCallback(async (prompt = "") => {
    if (!userEmail) return;

    setLoading(true);
    setStatus(prompt === "consent" ? "Connecting to Google Calendar..." : "Refreshing Google Calendar...");

    try {
      const token = await getGoogleAccessToken(prompt);
      const { start, end } = getWeekRange(currentWeek);

      const freeBusyResponse = await fetch("https://www.googleapis.com/calendar/v3/freeBusy", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          timeMin: start.toISOString(),
          timeMax: end.toISOString(),
          items: [{ id: "primary" }],
        }),
      });

      if (!freeBusyResponse.ok) {
        throw new Error("Failed to read Google Calendar busy times");
      }

      const freeBusyJson = await freeBusyResponse.json();
      const busySlots =
        freeBusyJson?.calendars?.primary?.busy?.map((slot) => ({
          starts_at: slot.start,
          ends_at: slot.end,
        })) || [];

      const backendResponse = await fetch(`${API_BASE}/availability/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_email: userEmail,
          starts_at: start.toISOString(),
          ends_at: end.toISOString(),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
          source: "google_calendar",
          busy_slots: busySlots,
        }),
      });

      if (!backendResponse.ok) {
        const error = await backendResponse.json();
        throw new Error(error.detail || "Failed to sync Google Calendar");
      }

      setGcalConnected(true);
      setStatus(`Synced ${busySlots.length} busy blocks from Google Calendar`);
      await fetchAvailability([userEmail, ...selectedClassmates]);
    } catch (error) {
      console.error("Error syncing Google Calendar:", error);
      setStatus(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [currentWeek, fetchAvailability, getGoogleAccessToken, selectedClassmates, userEmail]);

  const checkGcalConnection = useCallback(async () => {
    if (!userEmail) return;

    try {
      const response = await fetch(
        `${API_BASE}/availability/connected?user_email=${encodeURIComponent(userEmail)}`
      );
      if (!response.ok) {
        throw new Error("Failed to check Google Calendar status");
      }
      const data = await response.json();
      setGcalConnected(Boolean(data.connected));
    } catch (error) {
      console.error("Error checking GCal connection:", error);
    }
  }, [userEmail]);

  const fetchClassmates = useCallback(async () => {
    if (!user?.uid) return;

    try {
      const response = await fetch(`${API_BASE}/users/${user.uid}/courses`);
      if (response.ok) {
        const enrolledCourses = await response.json();
        const visibleCourses = isClassScoped
          ? enrolledCourses.filter((course) => course.id === parseInt(courseId, 10))
          : enrolledCourses;

        setCourses(visibleCourses);
        setActiveCourse(isClassScoped ? visibleCourses[0] || null : null);
        if (isClassScoped && visibleCourses.length > 0) {
          setMeetingForm((current) => ({
            ...current,
            courseId: `${visibleCourses[0].id}`,
          }));
        }

        const classmatesUrl = isClassScoped
          ? `${API_BASE}/courses/${courseId}/members`
          : `${API_BASE}/users`;
        const usersResponse = await fetch(classmatesUrl);
        if (!usersResponse.ok) {
          throw new Error("Failed to load classmates");
        }

        const users = await usersResponse.json();
        setClassmates(users.filter((u) => u.email !== userEmail));
      }
    } catch (error) {
      console.error("Error fetching classmates:", error);
    }
  }, [courseId, isClassScoped, user?.uid, userEmail]);

  const fetchUpcomingSessions = useCallback(async () => {
    if (!isClassScoped || !courseId || !userEmail) {
      setUpcomingSessions([]);
      return;
    }

    try {
      const rangeStart = new Date();
      const rangeEnd = new Date(rangeStart.getTime() + 14 * 24 * 60 * 60 * 1000);
      const params = new URLSearchParams({
        range_start: rangeStart.toISOString(),
        range_end: rangeEnd.toISOString(),
        requester_email: userEmail,
      });
      const response = await fetch(
        `${API_BASE}/study-sessions/course/${courseId}?${params.toString()}`
      );
      if (!response.ok) {
        throw new Error("Failed to load upcoming class sessions");
      }

      const sessions = await response.json();
      setUpcomingSessions(sessions);
    } catch (error) {
      console.error("Error fetching class sessions:", error);
    }
  }, [courseId, isClassScoped, userEmail]);

  const handleScheduleMeeting = async () => {
    if (!meetingForm.title || !meetingForm.startTime || !meetingForm.endTime || !meetingForm.courseId) {
      setStatus("Please fill in all required fields");
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/study-sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: meetingForm.title,
          course_id: parseInt(meetingForm.courseId, 10),
          session_type: selectedClassmates.length > 0 ? "group" : "solo",
          starts_at: new Date(meetingForm.startTime).toISOString(),
          ends_at: new Date(meetingForm.endTime).toISOString(),
          creator_email: userEmail,
          invitees: selectedClassmates,
        }),
      });

      if (response.ok) {
        setStatus(
          selectedClassmates.length > 0
            ? "Class session scheduled. It is now visible in StudySync for this class."
            : "Session scheduled to your StudySync calendar for this class."
        );
        setShowScheduleMeetingModal(false);
        setMeetingForm({
          title: "",
          startTime: "",
          endTime: "",
          courseId: courseId || "",
        });
        await fetchUpcomingSessions();
        setTimeout(() => setStatus(""), 3000);
      } else {
        const error = await response.json();
        setStatus(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error("Error scheduling meeting:", error);
      setStatus(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkGcalConnection();
    fetchClassmates();
    fetchUpcomingSessions();
  }, [checkGcalConnection, fetchClassmates, fetchUpcomingSessions]);

  useEffect(() => {
    if (!userEmail) return;
    fetchAvailability([userEmail, ...selectedClassmates]);
  }, [currentWeek, fetchAvailability, selectedClassmates, userEmail]);

  useEffect(() => {
    const validEmails = new Set(classmates.map((classmate) => classmate.email));
    setSelectedClassmates((current) => current.filter((email) => validEmails.has(email)));
  }, [classmates]);

  const getWeekDates = () => {
    const { start } = getWeekRange(currentWeek);
    return Array.from({ length: 7 }, (_, index) => {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      return date;
    });
  };

  const getBusyBlocks = (email) => availabilityByEmail[email] || [];

  const isBusyForEmails = (emails, date, hour) => {
    const slotStart = new Date(date);
    slotStart.setHours(hour, 0, 0, 0);
    const slotEnd = new Date(slotStart);
    slotEnd.setHours(hour + 1);

    return emails.some((email) =>
      getBusyBlocks(email).some((block) => {
        const busyStart = new Date(block.starts_at);
        const busyEnd = new Date(block.ends_at);
        return busyStart < slotEnd && busyEnd > slotStart;
      })
    );
  };

  const renderAvailabilityGrid = (emailsToCheck) => {
    const weekDates = getWeekDates();
    const hours = Array.from({ length: 14 }, (_, i) => i + 8);

    return (
      <div className="availability-grid">
        <div className="grid-header">
          <div className="time-header"></div>
          {weekDates.map((date) => (
            <div key={date.toDateString()} className="day-header">
              {date.toLocaleDateString("en-US", { weekday: "short", month: "numeric", day: "numeric" })}
            </div>
          ))}
        </div>
        {hours.map((hour) => (
          <div key={hour} className="grid-row">
            <div className="time-cell">{formatHourLabel(hour)}</div>
            {weekDates.map((date) => {
              const isFree = !isBusyForEmails(emailsToCheck, date, hour);
              return (
                <div
                  key={`${date.toDateString()}-${hour}`}
                  className={`time-slot ${isFree ? "free" : "busy"}`}
                  onClick={() => {
                    if (!isFree || calendarView !== "compare") return;

                    const startTime = new Date(date);
                    startTime.setHours(hour, 0, 0, 0);
                    const endTime = new Date(startTime);
                    endTime.setHours(hour + 1);

                    setMeetingForm((current) => ({
                      ...current,
                      startTime: toLocalDateTimeInputValue(startTime),
                      endTime: toLocalDateTimeInputValue(endTime),
                    }));
                    setShowScheduleMeetingModal(true);
                  }}
                  title={isFree ? "Free" : "Busy"}
                >
                  <span className="time-slot-label">{isFree ? "Free" : "Busy"}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    );
  };

  const compareEmails = [userEmail, ...selectedClassmates];
  const filteredCompareClassmates = classmates.filter((classmate) => {
    const query = normalizeSearchValue(compareSearchQuery);
    if (!query) return true;

    return [classmate.full_name, classmate.email].some((value) =>
      value?.toLowerCase().includes(query)
    );
  });
  const filteredMeetingClassmates = classmates.filter((classmate) => {
    const query = normalizeSearchValue(meetingSearchQuery);
    if (!query) return true;

    return [classmate.full_name, classmate.email].some((value) =>
      value?.toLowerCase().includes(query)
    );
  });

  return (
    <div className="schedule-page">
      <div className="schedule-container">
        <div className="calendar-section">
          <div className="calendar-controls">
            <div className="calendar-header">
              <h2>{isClassScoped ? "Class Schedule & Study Partners" : "Schedule & Find Study Partners"}</h2>
            </div>
            <div className="calendar-toolbar">
              <button
                className={`view-btn ${calendarView === "mine" ? "active" : ""}`}
                onClick={() => setCalendarView("mine")}
              >
                My Calendar
              </button>
              <button
                className={`view-btn ${calendarView === "compare" ? "active" : ""}`}
                onClick={() => setCalendarView("compare")}
              >
                Compare & Schedule
              </button>
              <button
                className="nav-btn"
                onClick={() => setCurrentWeek(new Date(currentWeek.getTime() - 7 * 24 * 60 * 60 * 1000))}
              >
                ← Prev Week
              </button>
              <button className="nav-btn" onClick={() => setCurrentWeek(new Date())}>
                This Week
              </button>
              <button
                className="nav-btn"
                onClick={() => setCurrentWeek(new Date(currentWeek.getTime() + 7 * 24 * 60 * 60 * 1000))}
              >
                Next Week →
              </button>
            </div>
          </div>

          <div className="calendar-view">
            {!gcalConnected ? (
              <div className="schedule-empty-state">
                <h3>Connect Google Calendar to Get Started</h3>
                <p>Connect your calendar to sync your busy times and compare schedules with classmates</p>
              </div>
            ) : calendarView === "mine" ? (
              <div className="schedule-panel">
                <h3>Your Availability This Week</h3>
                <p className="schedule-intro">
                  Green blocks mean you are open during that hour. Busy blocks reflect the Google Calendar events you synced for this week.
                </p>
                {renderAvailabilityGrid([userEmail])}
              </div>
            ) : (
              <div className="schedule-panel">
                <h3>Find Common Free Times</h3>
                <p className="schedule-intro">
                  {isClassScoped
                    ? "Pick classmates in this class to highlight hours where everyone selected is available."
                    : "Pick classmates below to highlight hours where everyone selected is available."}
                </p>
                <div className="compare-section">
                  <label>
                    {isClassScoped
                      ? `Select classmates in ${activeCourse?.course_code || "this class"}:`
                      : "Select classmates to compare calendars with:"}
                  </label>
                  <input
                    type="search"
                    className="classmate-search-input"
                    value={compareSearchQuery}
                    onChange={(e) => setCompareSearchQuery(e.target.value)}
                    placeholder="Search classmates by name or email"
                  />
                  <div className="compare-classmates">
                    {filteredCompareClassmates.length > 0 ? (
                      filteredCompareClassmates.map((classmate) => (
                        <label key={classmate.email} className="classmate-option">
                          <input
                            type="checkbox"
                            checked={selectedClassmates.includes(classmate.email)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedClassmates((current) => [...current, classmate.email]);
                              } else {
                                setSelectedClassmates((current) =>
                                  current.filter((email) => email !== classmate.email)
                                );
                              }
                            }}
                          />
                          <span>{classmate.full_name}</span>
                        </label>
                      ))
                    ) : (
                      <p className="classmate-search-empty">No classmates match that search.</p>
                    )}
                  </div>
                </div>
                {selectedClassmates.length > 0 ? (
                  <div className="compare-grid-wrap">
                    <p className="compare-note">
                      Green means everyone selected is free. Red means at least one person is busy.
                    </p>
                    {renderAvailabilityGrid(compareEmails)}
                  </div>
                ) : (
                  <p>Select classmates above to see common free times</p>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="sidebar">
          <div className="sidebar-card google-calendar-section">
            <div className="card-title">
              <svg className="card-icon" fill="currentColor" viewBox="0 0 24 24">
                <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c0 1.1.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z" />
              </svg>
              Google Calendar
            </div>
            {gcalConnected ? (
              <>
                <div className="connection-status status-connected">✓ Synced</div>
                <button onClick={() => syncGoogleCalendar("")} disabled={loading}>
                  {loading ? "Syncing..." : "Refresh This Week"}
                </button>
              </>
            ) : (
              <button onClick={() => syncGoogleCalendar("consent")} disabled={loading}>
                {loading ? "Connecting..." : "Connect Google Calendar"}
              </button>
            )}
          </div>

          <div className="sidebar-card">
            <div className="card-title">
              <svg className="card-icon" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z" />
              </svg>
              Quick Actions
            </div>
            <div className="quick-actions">
              <button className="action-btn" onClick={() => setShowScheduleMeetingModal(true)}>
                + Schedule Meeting
              </button>
            </div>
          </div>

          {isClassScoped && (
            <div className="sidebar-card">
              <div className="card-title">
                <svg className="card-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M7 2v2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2H7zm12 8H5v8h14v-8z" />
                </svg>
                Upcoming For This Class
              </div>
              {upcomingSessions.length > 0 ? (
                <div className="class-session-list">
                  {upcomingSessions.slice(0, 5).map((session) => (
                    <div key={session.id} className="class-session-item">
                      <div className="class-session-title">{session.title}</div>
                      <div className="class-session-meta">
                        {new Date(session.starts_at).toLocaleString([], {
                          month: "short",
                          day: "numeric",
                          hour: "numeric",
                          minute: "2-digit",
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="class-session-empty">No upcoming class sessions yet.</p>
              )}
            </div>
          )}

          {status && (
            <div
              className={`status-message ${
                status.includes("Error")
                  ? "status-error"
                  : status.includes("Synced") || status.includes("connected")
                    ? "status-success"
                    : "status-loading"
              }`}
            >
              {status}
            </div>
          )}
        </div>
      </div>

      {showScheduleMeetingModal && (
        <div className="modal-overlay" onClick={() => setShowScheduleMeetingModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>Schedule Study Meeting</h3>
                <p className="modal-subtitle">
                  Pick a time and create a StudySync session that classmates in this course can see.
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                aria-label="Close schedule meeting dialog"
                onClick={() => setShowScheduleMeetingModal(false)}
              >
                ×
              </button>
            </div>
            {status && (
              <div
                className={`status-message ${
                  status.includes("Error") ? "status-error" : "status-success"
                }`}
              >
                {status}
              </div>
            )}
            <div className="modal-section">
              <div className="modal-section-title">Meeting Details</div>
              <div className="form-group">
                <label>Meeting Title *</label>
                <input
                  type="text"
                  value={meetingForm.title}
                  onChange={(e) =>
                    setMeetingForm({ ...meetingForm, title: e.target.value })
                  }
                  placeholder="e.g., Midterm Study Group"
                />
              </div>
              {isClassScoped ? (
                <div className="form-group">
                  <label>Course</label>
                  <div className="locked-course-field">
                    {courses[0]
                      ? `${courses[0].course_code} - ${courses[0].name}`
                      : "Current class"}
                  </div>
                </div>
              ) : (
                <div className="form-group">
                  <label>Course *</label>
                  <select
                    value={meetingForm.courseId}
                    onChange={(e) =>
                      setMeetingForm({ ...meetingForm, courseId: e.target.value })
                    }
                  >
                    <option value="">Select a course</option>
                    {courses.map((course) => (
                      <option key={course.id} value={course.id}>
                        {course.course_code} - {course.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="form-row">
                <div className="form-group">
                  <label>Start Time *</label>
                  <input
                    type="datetime-local"
                    value={meetingForm.startTime}
                    onChange={(e) =>
                      setMeetingForm({ ...meetingForm, startTime: e.target.value })
                    }
                  />
                </div>
                <div className="form-group">
                  <label>End Time *</label>
                  <input
                    type="datetime-local"
                    value={meetingForm.endTime}
                    onChange={(e) =>
                      setMeetingForm({ ...meetingForm, endTime: e.target.value })
                    }
                  />
                </div>
              </div>
            </div>
            <div className="modal-section">
              <div className="modal-section-title">Invite Classmates</div>
              <div className="form-group">
                <label>Tag classmates (optional)</label>
                <input
                  type="search"
                  className="classmate-search-input"
                  value={meetingSearchQuery}
                  onChange={(e) => setMeetingSearchQuery(e.target.value)}
                  placeholder="Search classmates to tag in this session"
                />
                <p className="invite-help-text">
                  This only helps you plan the session in StudySync. It will not send Google Calendar invites.
                </p>
              </div>
              <div className="modal-classmate-list">
                {filteredMeetingClassmates.length > 0 ? (
                  filteredMeetingClassmates.map((classmate) => (
                    <label key={classmate.email} className="classmate-option">
                      <input
                        type="checkbox"
                        checked={selectedClassmates.includes(classmate.email)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedClassmates((current) => [...current, classmate.email]);
                          } else {
                            setSelectedClassmates((current) =>
                              current.filter((email) => email !== classmate.email)
                            );
                          }
                        }}
                      />
                      <span>{classmate.full_name}</span>
                    </label>
                  ))
                ) : (
                  <p className="classmate-search-empty">No classmates match that search.</p>
                )}
              </div>
              <div className="selected-attendees">
                <div className="selected-attendees-title">Selected invitees</div>
                <div className="attendee-list">
                  {selectedClassmates.length > 0 ? (
                    selectedClassmates.map((email) => (
                      <div key={email} className="attendee-tag">
                        {email}
                      </div>
                    ))
                  ) : (
                    <p className="classmate-search-empty">
                      No classmates selected. This session will still appear in the class schedule.
                    </p>
                  )}
                </div>
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn-subtle-link" onClick={() => setShowScheduleMeetingModal(false)}>
                Cancel
              </button>
              <button className="btn-submit" onClick={handleScheduleMeeting} disabled={loading}>
                {loading ? "Scheduling..." : "Schedule Meeting"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SchedulePage;
