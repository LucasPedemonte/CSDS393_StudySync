import Navbar from "./Navbar";
import "./LoginPage.css";
import "./CalendarPage.css";
import { useEffect, useMemo, useState } from "react";
import { auth } from "./firebase";

const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:8000";
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

const CalendarPage = () => {
  const [groups, setGroups] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [groupName, setGroupName] = useState("");
  const [joinGroupId, setJoinGroupId] = useState("");
  const [syncStatus, setSyncStatus] = useState("");
  const [groupStatus, setGroupStatus] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [daysAhead, setDaysAhead] = useState(14);
  const [meetingMinutes, setMeetingMinutes] = useState(60);
  const [sessions, setSessions] = useState([]);
  const [sessionType, setSessionType] = useState("solo");
  const [sessionTitle, setSessionTitle] = useState("");
  const [sessionStart, setSessionStart] = useState("");
  const [sessionEnd, setSessionEnd] = useState("");
  const [sessionStatus, setSessionStatus] = useState("");
  const [currentMonth, setCurrentMonth] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });

  // Disable page scroll on this page
  useEffect(() => {
    document.body.classList.add("calendar-page");
    return () => {
      document.body.classList.remove("calendar-page");
    };
  }, []);
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().slice(0, 10));

  const user = auth.currentUser;
  const userEmail = user?.email || "";
  const canUseGoogle = Boolean(GOOGLE_CLIENT_ID);

  const selectedGroup = useMemo(
    () => groups.find((g) => String(g.id) === String(selectedGroupId)),
    [groups, selectedGroupId]
  );

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

  const getGoogleAccessToken = async () => {
    await loadGoogleScript();
    return new Promise((resolve, reject) => {
      const tokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: "https://www.googleapis.com/auth/calendar.readonly",
        callback: (response) => {
          if (response?.access_token) {
            resolve(response.access_token);
          } else {
            reject(new Error("Google OAuth failed"));
          }
        },
      });
      tokenClient.requestAccessToken({ prompt: "consent" });
    });
  };

  const fetchGroups = async () => {
    if (!userEmail) return;
    const response = await fetch(
      `${API_BASE}/study-groups?user_email=${encodeURIComponent(userEmail)}`
    );
    if (!response.ok) throw new Error("Failed to fetch groups");
    const data = await response.json();
    setGroups(data);
    if (!selectedGroupId && data.length > 0) {
      setSelectedGroupId(String(data[0].id));
    }
  };

  useEffect(() => {
    fetchGroups().catch((err) => setGroupStatus(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userEmail]);

  const createGroup = async () => {
    if (!groupName.trim()) return;
    setGroupStatus("Creating group...");
    try {
      const response = await fetch(`${API_BASE}/study-groups`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: groupName.trim(),
          user_email: userEmail,
        }),
      });
      if (!response.ok) throw new Error("Could not create group");
      const created = await response.json();
      await fetchGroups();
      setSelectedGroupId(String(created.id));
      setGroupName("");
      setGroupStatus("Group created.");
    } catch (err) {
      setGroupStatus(err.message || "Failed creating group");
    }
  };

  const joinGroup = async () => {
    const id = Number(joinGroupId);
    if (!id) return;
    setGroupStatus("Joining group...");
    try {
      const response = await fetch(`${API_BASE}/study-groups/${id}/join`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_email: userEmail }),
      });
      if (!response.ok) throw new Error("Could not join group");
      await fetchGroups();
      setSelectedGroupId(String(id));
      setJoinGroupId("");
      setGroupStatus("Joined group.");
    } catch (err) {
      setGroupStatus(err.message || "Failed joining group");
    }
  };

  const syncGoogleBusyTimes = async () => {
    if (!userEmail) return;
    setSyncStatus("Connecting to Google Calendar...");
    try {
      if (!canUseGoogle) {
        throw new Error("Missing REACT_APP_GOOGLE_CLIENT_ID in frontend env");
      }
      const token = await getGoogleAccessToken();
      const now = new Date();
      const end = new Date(now.getTime() + daysAhead * 24 * 60 * 60 * 1000);

      const freeBusyResponse = await fetch(
        "https://www.googleapis.com/calendar/v3/freeBusy",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            timeMin: now.toISOString(),
            timeMax: end.toISOString(),
            items: [{ id: "primary" }],
          }),
        }
      );
      if (!freeBusyResponse.ok) throw new Error("Failed to read Google Calendar busy times");
      const freeBusyJson = await freeBusyResponse.json();
      const busy =
        freeBusyJson?.calendars?.primary?.busy?.map((slot) => ({
          starts_at: slot.start,
          ends_at: slot.end,
        })) || [];

      const backendResponse = await fetch(`${API_BASE}/availability/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_email: userEmail,
          starts_at: now.toISOString(),
          ends_at: end.toISOString(),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
          source: "google_calendar",
          busy_slots: busy,
        }),
      });
      if (!backendResponse.ok) throw new Error("Failed to sync busy times to backend");
      const result = await backendResponse.json();
      setSyncStatus(`Synced ${result.inserted_busy_blocks} busy blocks (no event details stored).`);
    } catch (err) {
      setSyncStatus(err.message || "Calendar sync failed");
    }
  };

  const loadSuggestions = async () => {
    if (!selectedGroupId) return;
    setLoadingSuggestions(true);
    try {
      const start = new Date();
      const end = new Date(start.getTime() + daysAhead * 24 * 60 * 60 * 1000);
      const params = new URLSearchParams({
        range_start: start.toISOString(),
        range_end: end.toISOString(),
        duration_minutes: String(meetingMinutes),
        slot_minutes: "30",
        day_start_hour: "8",
        day_end_hour: "22",
        min_available_members: "1",
        user_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      });
      const response = await fetch(
        `${API_BASE}/study-groups/${selectedGroupId}/suggestions?${params.toString()}`
      );
      if (!response.ok) throw new Error("Failed to load suggestions");
      const data = await response.json();
      setSuggestions(data.suggestions || []);
    } catch (err) {
      setSyncStatus(err.message || "Could not load suggestions");
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const fmt = (iso) =>
    new Date(iso).toLocaleString([], {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });

  const dayKey = (date) => date.toISOString().slice(0, 10);

  const suggestionsByDay = useMemo(() => {
    const map = {};
    suggestions.forEach((slot) => {
      const key = dayKey(new Date(slot.starts_at));
      map[key] = (map[key] || 0) + 1;
    });
    return map;
  }, [suggestions]);

  const selectedDaySuggestions = useMemo(
    () => suggestions.filter((slot) => dayKey(new Date(slot.starts_at)) === selectedDate),
    [suggestions, selectedDate]
  );

  const sessionsByDay = useMemo(() => {
    const map = {};
    sessions.forEach((s) => {
      const key = dayKey(new Date(s.starts_at));
      map[key] = (map[key] || 0) + 1;
    });
    return map;
  }, [sessions]);

  const selectedDaySessions = useMemo(
    () => sessions.filter((s) => dayKey(new Date(s.starts_at)) === selectedDate),
    [sessions, selectedDate]
  );

  const calendarCells = useMemo(() => {
    const firstDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
    const startWeekday = firstDay.getDay();
    const gridStart = new Date(firstDay);
    gridStart.setDate(firstDay.getDate() - startWeekday);
    const cells = [];
    for (let i = 0; i < 42; i += 1) {
      const cellDate = new Date(gridStart);
      cellDate.setDate(gridStart.getDate() + i);
      cells.push({
        key: dayKey(cellDate),
        date: cellDate,
        inMonth: cellDate.getMonth() === currentMonth.getMonth(),
      });
    }
    return cells;
  }, [currentMonth]);

  const monthLabel = currentMonth.toLocaleDateString([], { month: "long", year: "numeric" });

  const loadSessions = async () => {
    if (!userEmail) return;
    const first = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
    const start = new Date(first);
    start.setDate(first.getDate() - first.getDay());
    const end = new Date(start);
    end.setDate(start.getDate() + 42);

    const params = new URLSearchParams({
      user_email: userEmail,
      range_start: start.toISOString(),
      range_end: end.toISOString(),
    });
    const response = await fetch(`${API_BASE}/study-sessions?${params.toString()}`);
    if (!response.ok) throw new Error("Failed to load study sessions");
    const data = await response.json();
    setSessions(data);
  };

  useEffect(() => {
    loadSessions().catch((err) => setSessionStatus(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userEmail, currentMonth]);

  const toInputDateTime = (d) => {
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(
      d.getMinutes()
    )}`;
  };

  const createStudySession = async () => {
    if (!userEmail) return;
    if (!sessionTitle.trim() || !sessionStart || !sessionEnd) {
      setSessionStatus("Please provide title, start time, and end time.");
      return;
    }
    if (sessionType === "group" && !selectedGroupId) {
      setSessionStatus("Select a group for group study sessions.");
      return;
    }

    setSessionStatus("Creating session...");
    try {
      const response = await fetch(`${API_BASE}/study-sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          creator_email: userEmail,
          session_type: sessionType,
          title: sessionTitle.trim(),
          starts_at: new Date(sessionStart).toISOString(),
          ends_at: new Date(sessionEnd).toISOString(),
          group_id: sessionType === "group" ? Number(selectedGroupId) : null,
        }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to create session");
      }
      const created = await response.json();
      setSessionStatus("Session created.");
      setSessionTitle("");
      const nextStart = new Date(new Date(created.starts_at).getTime() + 60 * 60 * 1000);
      const nextEnd = new Date(new Date(created.starts_at).getTime() + 2 * 60 * 60 * 1000);
      setSessionStart(toInputDateTime(nextStart));
      setSessionEnd(toInputDateTime(nextEnd));
      await loadSessions();
    } catch (err) {
      setSessionStatus(err.message || "Failed creating session");
    }
  };

  return (
    <div className="page with-navbar">
      <Navbar />
      <div className="calendar-layout">
        <div className="calendar-main">
          <div className="month-nav">
            <button
              className="month-nav-btn"
              type="button"
              onClick={() =>
                setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1))
              }
            >
              Prev
            </button>
            <div className="month-title">{monthLabel}</div>
            <button
              className="month-nav-btn"
              type="button"
              onClick={() =>
                setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1))
              }
            >
              Next
            </button>
          </div>

          <div className="calendar-grid">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
              <div key={d} className="calendar-dow">
                {d}
              </div>
            ))}
            {calendarCells.map((cell) => {
              const sessionCount = sessionsByDay[cell.key] || 0;
              const suggestionCount = suggestionsByDay[cell.key] || 0;
              const isSelected = selectedDate === cell.key;
              const className = [
                "calendar-day",
                cell.inMonth ? "" : "outside",
                isSelected ? "selected" : "",
              ]
                .join(" ")
                .trim();
              return (
                <button
                  key={cell.key}
                  type="button"
                  onClick={() => setSelectedDate(cell.key)}
                  className={className}
                >
                  <div className="calendar-day-num">{cell.date.getDate()}</div>
                  <div className="calendar-day-slots">
                    {sessionCount > 0
                      ? `${sessionCount} session${sessionCount > 1 ? "s" : ""}`
                      : suggestionCount > 0
                      ? `${suggestionCount} slot${suggestionCount > 1 ? "s" : ""}`
                      : " "}
                  </div>
                </button>
              );
            })}
          </div>

          <p className="calendar-day-summary">
            {selectedDaySuggestions.length > 0
              ? `${selectedDaySuggestions.length} suggested slot(s) on ${new Date(selectedDate).toLocaleDateString()}.`
              : `No meetings suggested yet for ${new Date(selectedDate).toLocaleDateString()}.`}
          </p>
        </div>

        <div className="calendar-sidebar">
          <div>
            <h2 style={{ marginBottom: "12px" }}>Calendar / Study Groups</h2>
            <p style={{ color: "var(--text-secondary)", marginBottom: "16px" }}>
              Privacy mode: only busy/free blocks are synced. Event titles and details are never stored.
            </p>

            <div className="sidebar-section">
              <label>Create Study Session</label>
              <div className="mode-toggle">
                <button
                  type="button"
                  className={`mode-btn ${sessionType === "solo" ? "active" : ""}`}
                  onClick={() => setSessionType("solo")}
                >
                  Solo Study Session
                </button>
                <button
                  type="button"
                  className={`mode-btn ${sessionType === "group" ? "active" : ""}`}
                  onClick={() => setSessionType("group")}
                >
                  Group Study Session
                </button>
              </div>
              <div className="sidebar-row">
                <input
                  type="text"
                  placeholder={sessionType === "group" ? "Group session title" : "Solo session title"}
                  value={sessionTitle}
                  onChange={(e) => setSessionTitle(e.target.value)}
                  className="sidebar-input"
                />
              </div>
              <div className="sidebar-row">
                <input
                  type="datetime-local"
                  value={sessionStart}
                  onChange={(e) => setSessionStart(e.target.value)}
                  className="sidebar-input"
                />
              </div>
              <div className="sidebar-row">
                <input
                  type="datetime-local"
                  value={sessionEnd}
                  onChange={(e) => setSessionEnd(e.target.value)}
                  className="sidebar-input"
                />
              </div>
              {sessionType === "group" && (
                <p style={{ color: "var(--text-secondary)", marginTop: "6px" }}>
                  Group sessions use the selected group above.
                </p>
              )}
              <div className="sidebar-row">
                <button className="btn-submit" type="button" onClick={createStudySession}>
                  Create
                </button>
              </div>
              {sessionStatus && (
                <p style={{ color: "var(--text-secondary)", marginTop: "6px" }}>{sessionStatus}</p>
              )}
            </div>

            <div className="sidebar-section">
              <label>Signed in as</label>
              <div style={{ marginTop: "6px", color: "var(--text-secondary)" }}>
                {userEmail || "No user"}
              </div>
            </div>

            <div className="sidebar-section">
              <label>Create a Study Group</label>
              <div className="sidebar-row">
                <input
                  type="text"
                  placeholder="e.g., CSDS 393 Midterm Prep"
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  className="sidebar-input"
                />
                <button className="btn-submit" type="button" onClick={createGroup}>
                  Create
                </button>
              </div>
            </div>

            <div className="sidebar-section">
              <label>Join by Group ID</label>
              <div className="sidebar-row">
                <input
                  type="number"
                  placeholder="Group ID"
                  value={joinGroupId}
                  onChange={(e) => setJoinGroupId(e.target.value)}
                  className="sidebar-input"
                />
                <button className="btn-submit" type="button" onClick={joinGroup}>
                  Join
                </button>
              </div>
            </div>

            <div className="sidebar-section">
              <label>Your Groups</label>
              <select
                value={selectedGroupId}
                onChange={(e) => setSelectedGroupId(e.target.value)}
                className="sidebar-select"
              >
                <option value="">Select a group</option>
                {groups.map((group) => (
                  <option key={group.id} value={group.id}>
                    #{group.id} - {group.name}
                  </option>
                ))}
              </select>
              {selectedGroup && (
                <p style={{ color: "var(--text-secondary)", marginTop: "6px" }}>
                  Selected: {selectedGroup.name} (ID: {selectedGroup.id})
                </p>
              )}
            </div>

            <div className="sidebar-section">
              <label>Sync Window (Days Ahead)</label>
              <input
                type="number"
                min="1"
                max="60"
                value={daysAhead}
                onChange={(e) => setDaysAhead(Number(e.target.value) || 14)}
                className="sidebar-input"
              />
            </div>

            <div className="sidebar-section">
              <label>Meeting Duration (Minutes)</label>
              <input
                type="number"
                min="15"
                max="240"
                step="15"
                value={meetingMinutes}
                onChange={(e) => setMeetingMinutes(Number(e.target.value) || 60)}
                className="sidebar-input"
              />
            </div>

            <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
              <button className="btn-google" type="button" onClick={syncGoogleBusyTimes}>
                Sync Busy Times from Google
              </button>
              <button className="btn-submit" type="button" onClick={loadSuggestions} disabled={!selectedGroupId || loadingSuggestions}>
                {loadingSuggestions ? "Loading..." : "Find Best Meeting Times"}
              </button>
            </div>

            {groupStatus && (
              <p style={{ color: "var(--text-secondary)", marginBottom: "8px" }}>{groupStatus}</p>
            )}
            {syncStatus && (
              <p style={{ color: "var(--text-secondary)", marginBottom: "12px" }}>{syncStatus}</p>
            )}

            <div style={{ marginBottom: "16px" }}>
              <h3 style={{ marginBottom: "8px" }}>Sessions On Selected Day</h3>
              {selectedDaySessions.length === 0 ? (
                <p style={{ color: "var(--text-secondary)" }}>No sessions created for this day yet.</p>
              ) : (
                <div className="suggestion-list">
                  {selectedDaySessions.map((session, idx) => (
                    <div key={`${session.id || idx}-${session.starts_at}`} className="suggestion-item">
                      <div style={{ fontWeight: 700 }}>{session.title}</div>
                      <div style={{ color: "var(--text-secondary)", marginTop: "2px" }}>
                        {fmt(session.starts_at)} - {fmt(session.ends_at)}
                      </div>
                      <div style={{ color: "var(--text-secondary)", marginTop: "2px" }}>
                        {session.session_type === "group" ? "Group Session" : "Solo Session"}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <h3 style={{ marginBottom: "8px" }}>Suggested Slots</h3>
              {selectedDaySuggestions.length === 0 ? (
                <p style={{ color: "var(--text-secondary)" }}>
                  No suggestions for this day. Sync your busy times and click "Find Best Meeting Times".
                </p>
              ) : (
                <div className="suggestion-list">
                  {selectedDaySuggestions.map((slot, idx) => (
                    <div key={`${slot.starts_at}-${idx}`} className="suggestion-item">
                      <div style={{ fontWeight: 700 }}>
                        {fmt(slot.starts_at)} - {fmt(slot.ends_at)}
                      </div>
                      <div style={{ color: "var(--text-secondary)", marginTop: "2px" }}>
                        {slot.available_count}/{slot.total_members} members available
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalendarPage;
