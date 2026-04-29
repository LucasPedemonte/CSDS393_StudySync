/**
 * - Global inbox (`isGlobal=true`, mounted at /inbox): every
 *   conversation the current user belongs to, across courses and DMs.
 * - Class chat (`isGlobal=false`, mounted at /class/:courseId/chat):
 *   the auto-provisioned course-wide group chat plus 1:1 DMs with
 *   classmates.
 */
import { useEffect, useState, useCallback} from "react";
import { onAuthStateChanged } from "firebase/auth";
import { useParams } from "react-router-dom";
import "./LoginPage.css";
import "./ChatPage.css";
import { auth } from "./firebase";

const ROLE_PRIORITY = {
  Admin: 0,
  TA: 1,
  Student: 2,
};

const ChatPage = ({ isGlobal = true }) => {
  const { courseId } = useParams();
  const [authUser, setAuthUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [sending, setSending] = useState(false);

  // Load current user + profile
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        setAuthUser(user);
        try {
          // 1. Load User Profile
          const profileRes = await fetch(
            `http://localhost:8000/user/${user.uid}`,
          );
          if (profileRes.ok) {
            const profileData = await profileRes.json();
            setUserProfile(profileData);
          }

          // 2. Logic Switch: Global Inbox vs. Class Roster
          if (isGlobal) {
            // GLOBAL VIEW: Fetch only active conversations from across all classes
            const inboxRes = await fetch(
              `http://localhost:8000/conversations/inbox/global?user_uid=${user.uid}`,
            );
            if (inboxRes.ok) {
              const activeConversations = await inboxRes.json();
              setUsers(activeConversations);
              if (activeConversations.length > 0)
                setSelectedUser(activeConversations[0]);
            }
          } else {
            // CLASS VIEW: Fetch all students/TAs in the system so you can start new chats
            const usersRes = await fetch("http://localhost:8000/users");
            if (usersRes.ok) {
              const allUsers = await usersRes.json();
              // Filter out yourself
              let filtered = allUsers.filter(
                (u) => u.firebase_uid !== user.uid,
              );

              // Create the Class Chat sentinel for this specific course
              const classChatEntry = {
                firebase_uid: `GROUP_${courseId}`, // Unique ID for this course group
                full_name: "Class Discussion",
                role: "Public Channel",
                is_group: true,
                course_id: courseId,
              };

              setUsers([classChatEntry, ...filtered]);
              setSelectedUser(classChatEntry); // Default to the class group chat
            }
          }
        } catch (err) {
          console.error("Error loading chat roster:", err);
        }
      }
      setLoading(false);
    });
    return () => unsubscribe();
  }, [isGlobal, courseId]);

  /**
   * Fetch the message history for the conversation between
   * `currentUser` and `otherUser` (or the course group chat if
   * `otherUser.is_group`). Course context comes from the conversation
   * itself when in the global inbox, falling back to the URL
   * `:courseId` on the class page.
   */
  const loadMessages = useCallback(async (currentUser, otherUser) => {
    if (!currentUser || !otherUser) return;
    try {
      const params = new URLSearchParams();
      params.append("user1", currentUser.uid);
      params.append("user2", otherUser.firebase_uid);
      params.append("is_group", otherUser.is_group || false);

      // Use the course ID from the user object (Global) OR the URL (Class Page)
      const activeCourseId = otherUser.course_id || courseId;
      if (activeCourseId) {
        params.append("course_id", activeCourseId);
      }

      const res = await fetch(
        `http://localhost:8000/messages?${params.toString()}`,
      );
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (err) {
      console.error("Error loading messages:", err);
    }
  }, [courseId]);

  // Initial + polling load of messages when selectedUser changes
  useEffect(() => {
    if (!authUser || !selectedUser) return;
    loadMessages(authUser, selectedUser);
    const interval = setInterval(() => {
      loadMessages(authUser, selectedUser);
    }, 3000);
    return () => clearInterval(interval);
  }, [authUser, selectedUser, loadMessages]);

  /**
   * Send the current draft message to the selected conversation.
   * Uses the conversation's own course id when present (so global
   * inbox replies stay in the right course thread); falls back to
   * the URL `:courseId` for class-page sends. For group chats the
   * receiver UID is the sentinel `"GROUP"`.
   */
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!authUser || !selectedUser || !newMessage.trim()) return;

    setSending(true);
    try {
      // Determine correct course context for the message
      const targetCourseId = selectedUser.course_id || courseId;

      const payload = {
        sender_uid: authUser.uid,
        content: newMessage.trim(),
        course_id: parseInt(targetCourseId || 0),
        receiver_uid: selectedUser.is_group
          ? "GROUP"
          : selectedUser.firebase_uid,
        is_group: selectedUser.is_group || false,
      };

      const res = await fetch("http://localhost:8000/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setNewMessage("");
        loadMessages(authUser, selectedUser);
      }
    } catch (err) {
      console.error("Error sending message:", err);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="page with-navbar">
        <div className="dm-page">
          <div className="dm-shell">
            <div className="dm-sidebar">
              <div className="dm-brand">
                <h1 className="tagline">
                  Discussion <span className="highlight">Forum</span>
                </h1>
                <p className="tagline-sub">Loading chat...</p>
              </div>
            </div>
            <div className="dm-main">
              <div className="dm-main-empty">Loading…</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page with-navbar">
      <div className="dm-page">
        <div className="dm-shell">
          <aside className="dm-sidebar">
            <div className="dm-sidebar-header">
              <h2 className="dm-sidebar-title">Messages</h2>
              {userProfile && (
                <p className="dm-sidebar-sub">
                  {userProfile.full_name} · {userProfile.role}
                </p>
              )}
            </div>

            <div className="dm-list-label">Active Conversations</div>
            <div className="dm-user-list">
              {users.length === 0 && (
                <p className="dm-empty-text">No active chats in this view.</p>
              )}
              {users.map((u) => {
                const isActive = selectedUser?.firebase_uid === u.firebase_uid;
                return (
                  <button
                    key={u.firebase_uid}
                    type="button"
                    className={`dm-user-row ${isActive ? "active" : ""}`}
                    onClick={() => setSelectedUser(u)}
                  >
                    <div className="dm-avatar">
                      {u.full_name?.charAt(0).toUpperCase() || "U"}
                    </div>
                    <div className="dm-user-meta">
                      {/* Name will now include (Course Code) from the backend */}
                      <div className="dm-user-name">{u.full_name}</div>
                      <div className="dm-user-role">
                        {u.role} {u.course_code ? `· ${u.course_code}` : ""}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </aside>

          <section className="dm-main">
            <header className="dm-main-header">
              {selectedUser && (
                <div className="dm-main-user">
                  <div className="dm-main-name">{selectedUser.full_name}</div>
                  <div className="dm-main-role">
                    {selectedUser.role}{" "}
                    {selectedUser.course_code
                      ? `· ${selectedUser.course_code}`
                      : ""}
                  </div>
                </div>
              )}
            </header>

            <div className="dm-messages">
              {messages.map((m) => {
                const isMe = m.sender_uid === authUser?.uid;
                return (
                  <div
                    key={m.id}
                    className={`dm-message-row ${isMe ? "me" : "them"}`}
                  >
                    {!isMe && selectedUser?.is_group && (
                      <span className="dm-sender-label">{m.sender_name}</span>
                    )}
                    <div className="dm-bubble">{m.content}</div>
                  </div>
                );
              })}
            </div>

            <form className="dm-input-bar" onSubmit={handleSendMessage}>
              <input
                type="text"
                placeholder="Message..."
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                disabled={!selectedUser || sending}
              />
              <button
                type="submit"
                className="btn-submit chat-send-btn"
                disabled={!newMessage.trim()}
              >
                Send
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
