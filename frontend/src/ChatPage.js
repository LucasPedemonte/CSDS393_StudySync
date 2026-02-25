import { useEffect, useState } from "react";
import { onAuthStateChanged } from "firebase/auth";
import Navbar from "./Navbar";
import "./LoginPage.css";
import "./ChatPage.css";
import { auth } from "./firebase";

const ROLE_PRIORITY = {
  Admin: 0,
  TA: 1,
  Student: 2,
};

const ChatPage = () => {
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
          const profileRes = await fetch(`http://localhost:8000/user/${user.uid}`);
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
            // Exclude current user and sort by role priority then name
            const filtered = allUsers
              .filter((u) => u.firebase_uid !== user.uid)
              .sort((a, b) => {
                const roleA = ROLE_PRIORITY[a.role] ?? 99;
                const roleB = ROLE_PRIORITY[b.role] ?? 99;
                if (roleA !== roleB) return roleA - roleB;
                return (a.full_name || "").localeCompare(b.full_name || "");
              });
            setUsers(filtered);
            if (filtered.length > 0) {
              setSelectedUser(filtered[0]);
            }
          }
        } catch (err) {
          console.error("Error loading users for chat:", err);
        }
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // Fetch messages between authUser and selectedUser
  const loadMessages = async (currentUser, otherUser) => {
    if (!currentUser || !otherUser) return;
    try {
      const res = await fetch(
        `http://localhost:8000/messages?user1=${currentUser.uid}&user2=${otherUser.firebase_uid}`
      );
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      } else {
        const text = await res.text();
        console.error("Failed to load messages:", res.status, text);
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
  }, [authUser, selectedUser]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!authUser || !selectedUser || !newMessage.trim()) return;

    setSending(true);
    try {
      const res = await fetch("http://localhost:8000/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sender_uid: authUser.uid,
          receiver_uid: selectedUser.firebase_uid,
          content: newMessage.trim(),
        }),
      });

      if (res.ok) {
        setNewMessage("");
        // Refresh messages after sending
        loadMessages(authUser, selectedUser);
      } else {
        const text = await res.text();
        console.error("Failed to send message:", res.status, text);
        alert("Could not send message (status " + res.status + "). Check backend logs.");
      }
    } catch (err) {
      console.error("Error sending message:", err);
      alert("Network error sending message. Is the backend running on port 8000?");
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="page with-navbar">
        <Navbar />
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
      <Navbar />
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
                      <div className="dm-main-name">{selectedUser.full_name}</div>
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
