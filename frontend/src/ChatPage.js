import { useEffect, useState } from "react";
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
          const profileRes = await fetch(
            `http://localhost:8000/user/${user.uid}`,
          );
          if (profileRes.ok) {
            const profileData = await profileRes.json();
            setUserProfile(profileData);
          }
        } catch (err) {
          console.error("Error loading user profile for chat:", err);
        }

        // Load all users for roster
        try {
          const usersRes = await fetch("http://localhost:8000/users");
          if (usersRes.ok) {
            const allUsers = await usersRes.json();
            let filtered = allUsers.filter((u) => u.firebase_uid !== user.uid);

            // ADD THE CLASS CHAT LOGIC HERE
            if (!isGlobal && courseId) {
              const classChatEntry = {
                firebase_uid: "CLASS_GROUP_ID", // Sentinel ID
                full_name: "Class Discussion",
                role: "Public Channel",
                is_group: true,
                course_id: courseId,
              };
              setUsers([classChatEntry, ...filtered]); // Put it at the top
              setSelectedUser(classChatEntry); // Default to class chat
            } else {
              setUsers(filtered);
              if (filtered.length > 0) setSelectedUser(filtered[0]);
            }
          }
        } catch (err) {
          console.error(err);
        }
      }
      setLoading(false);
    });
    return () => unsubscribe();
  }, [isGlobal, courseId]);

  // Fetch messages between authUser and selectedUser (scoped to course if not global)
  const loadMessages = async (currentUser, otherUser) => {
  if (!currentUser || !otherUser) return;
  try {
    const params = new URLSearchParams();
    params.append("user1", currentUser.uid);
    params.append("user2", otherUser.firebase_uid);
    params.append("is_group", otherUser.is_group || false); // Add this!
    if (!isGlobal && courseId) {
      params.append("course_id", courseId);
    }

    const res = await fetch(`http://localhost:8000/messages?${params.toString()}`);
    if (res.ok) {
      const data = await res.json();
      setMessages(data);
    }
  } catch (err) {
    console.error("Error loading messages:", err);
  }
};

  // Initial + polling load of messages when selectedUser changes
  useEffect(() => {
    if (!authUser || !selectedUser) return;

    // Initial load
    loadMessages(authUser, selectedUser);

    // Poll every few seconds
    const interval = setInterval(() => {
      loadMessages(authUser, selectedUser);
    }, 3000);

    return () => clearInterval(interval);
  }, [authUser, selectedUser, isGlobal, courseId]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (
      !authUser ||
      !selectedUser ||
      !selectedUser.firebase_uid ||
      !newMessage.trim()
    )
      return;

    setSending(true);
    try {
      const payload = {
        sender_uid: authUser.uid,
        content: newMessage.trim(),
        course_id: parseInt(courseId || 0),
        // If group is selected, handle receiver_uid differently on backend
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
      } else {
        const errorData = await res.json();
        console.error("Failed to send message:", errorData);
        alert(`Error: ${errorData.detail || "Could not send message"}`);
      }
    } catch (err) {
      console.error("Error sending message:", err);
      alert("Network error sending message.");
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
          {/* Left sidebar like Instagram user list + profile */}
          <aside className="dm-sidebar">
            <div className="dm-sidebar-header">
              <h2 className="dm-sidebar-title">Messages</h2>
              {userProfile && (
                <p className="dm-sidebar-sub">
                  {userProfile.full_name} · {userProfile.role}
                </p>
              )}
            </div>

            <div className="dm-list-label">Chats</div>
            <div className="dm-user-list">
              {users.length === 0 && (
                <p className="dm-empty-text">No other users yet.</p>
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
                      {u.full_name
                        ?.split(" ")
                        .map((part) => part[0])
                        .join("")
                        .slice(0, 2)
                        .toUpperCase() || "U"}
                    </div>
                    <div className="dm-user-meta">
                      <div className="dm-user-name">{u.full_name}</div>
                      <div className="dm-user-role">{u.role}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </aside>

          {/* Right main chat pane */}
          <section className="dm-main">
            <header className="dm-main-header">
              {selectedUser ? (
                <>
                  <div className="dm-main-user">
                    <div className="dm-avatar dm-avatar-sm">
                      {selectedUser.full_name
                        ?.split(" ")
                        .map((part) => part[0])
                        .join("")
                        .slice(0, 2)
                        .toUpperCase() || "U"}
                    </div>
                    <div>
                      <div className="dm-main-name">
                        {selectedUser.full_name}
                      </div>
                      <div className="dm-main-role">{selectedUser.role}</div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="dm-main-empty">
                  Select a user from the left to start a conversation.
                </div>
              )}
            </header>

            {/* Messages scroll area */}
            <div className="dm-messages">
              {selectedUser && messages.length === 0 && (
                <p className="dm-empty-text">No messages yet. Say hi!</p>
              )}
              {messages.map((m) => {
                const isMe = m.sender_uid === authUser?.uid;
                return (
                  <div
                    key={m.id}
                    className={`dm-message-row ${isMe ? "me" : "them"}`}
                  >
                    {/* Show sender name for everyone else in a group context */}
                    {!isMe && selectedUser?.is_group && (
                      <span className="dm-sender-label">{m.sender_name}</span>
                    )}
                    <div className="dm-bubble">{m.content}</div>
                  </div>
                );
              })}
            </div>

            {/* Input bar pinned to bottom, full width of chat column */}
            <form className="dm-input-bar" onSubmit={handleSendMessage}>
              <input
                type="text"
                placeholder={
                  selectedUser
                    ? "Message..."
                    : "Select a user from the left to start messaging"
                }
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                disabled={!selectedUser || sending}
              />
              <button
                type="submit"
                className="btn-submit dm-send-btn"
                disabled={!selectedUser || sending || !newMessage.trim()}
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
