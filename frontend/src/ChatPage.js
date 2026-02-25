import { useEffect, useState } from "react";
import { onAuthStateChanged } from "firebase/auth";
import Navbar from "./Navbar";
import "./LoginPage.css";
import { useState, useEffect } from "react";
import { auth } from "./firebase";

const ChatPage = () => {
  const [users, setUsers] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const [showUserList, setShowUserList] = useState(true);
  const [groupName, setGroupName] = useState("");
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [creatingGroup, setCreatingGroup] = useState(false);

  const API_BASE = "http://localhost:8000";

  // Get current user and fetch data on mount
  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged(async (user) => {
      if (user) {
        try {
          const response = await fetch(`${API_BASE}/user/${user.uid}`);
          const data = await response.json();
          setCurrentUser(data);
          
          // Fetch all users and conversations
          await fetchAllUsers();
          await fetchConversations(data.user_id);
        } catch (error) {
          console.error("Error fetching user data:", error);
        }
      }
    });

    return unsubscribe;
  }, []);

  // Poll for messages when conversation is selected
  useEffect(() => {
    if (!selectedConversation) return;

    const fetchMessages = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/messages/${selectedConversation.conversation_id}`
        );
        const data = await response.json();
        setMessages(data);
      } catch (error) {
        console.error("Error fetching messages:", error);
      }
    };

    fetchMessages();
    const interval = setInterval(fetchMessages, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [selectedConversation]);

  const fetchAllUsers = async () => {
    try {
      const response = await fetch(`${API_BASE}/users`);
      const data = await response.json();
      setUsers(data.filter(u => u.user_id !== currentUser?.user_id));
    } catch (error) {
      console.error("Error fetching users:", error);
    }
  };

  const fetchConversations = async (userId) => {
    try {
      const response = await fetch(`${API_BASE}/conversations/${userId}`);
      const data = await response.json();
      setConversations(data);
    } catch (error) {
      console.error("Error fetching conversations:", error);
    }
  };

  const startConversation = async (otherUserId) => {
    try {
      const response = await fetch(
        `${API_BASE}/conversations/one-on-one/${currentUser.user_id}/${otherUserId}`,
        { method: "POST" }
      );
      const data = await response.json();
      
      // Refetch conversations to include the new one
      await fetchConversations(currentUser.user_id);
      
      // Find and select the conversation
      const conversations = await fetch(`${API_BASE}/conversations/${currentUser.user_id}`);
      const convData = await conversations.json();
      const selected = convData.find(c => c.conversation_id === data.conversation_id);
      if (selected) {
        setSelectedConversation(selected);
        setShowUserList(false);
      }
    } catch (error) {
      console.error("Error starting conversation:", error);
    }
  };

  const createGroupConversation = async () => {
    if (!groupName.trim() || selectedUsers.length === 0) {
      alert("Please enter a group name and select at least one user");
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/conversations/group?group_name=${groupName}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_ids: [currentUser.user_id, ...selectedUsers]
        })
      });
      const data = await response.json();
      
      // Refetch conversations
      await fetchConversations(currentUser.user_id);
      
      // Reset form
      setGroupName("");
      setSelectedUsers([]);
      setCreatingGroup(false);
      
      // Select the new group
      const conversations = await fetch(`${API_BASE}/conversations/${currentUser.user_id}`);
      const convData = await conversations.json();
      const selected = convData.find(c => c.conversation_id === data.conversation_id);
      if (selected) {
        setSelectedConversation(selected);
        setShowUserList(false);
      }
    } catch (error) {
      console.error("Error creating group:", error);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation) return;

    try {
      await fetch(`${API_BASE}/messages/${selectedConversation.conversation_id}?sender_id=${currentUser.user_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: newMessage })
      });
      
      setNewMessage("");
      
      // Fetch updated messages
      const response = await fetch(
        `${API_BASE}/messages/${selectedConversation.conversation_id}`
      );
      const data = await response.json();
      setMessages(data);
    } catch (error) {
      console.error("Error sending message:", error);
    }
  };

  const getConversationTitle = (conv) => {
    if (conv.is_group) return conv.group_name;
    const other = conv.participants.find(p => p.user_id !== currentUser?.user_id);
    return other?.full_name || "Unknown";
  };

  return (
    <div className="page with-navbar">
      <Navbar />
      <div className="page-content">
        <div className="left-panel">
          <h1 className="tagline">
            Discussion <span className="highlight">Forum</span>
          </h1>
          <p className="tagline-sub">
            Connect and collaborate with your peers
          </p>
        </div>
        <div className="right-panel">
          <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            {!selectedConversation ? (
              <>
                <h2 style={{ marginBottom: "16px" }}>Messaging</h2>
                
                <div style={{ flex: 1, overflowY: "auto", marginBottom: "16px" }}>
                  {conversations.length === 0 ? (
                    <p style={{ color: "var(--text-secondary)" }}>
                      No conversations yet. Start one below!
                    </p>
                  ) : (
                    conversations.map((conv) => (
                      <div
                        key={conv.conversation_id}
                        onClick={() => setSelectedConversation(conv)}
                        style={{
                          padding: "12px",
                          marginBottom: "8px",
                          backgroundColor: "var(--bg-tertiary)",
                          borderRadius: "8px",
                          cursor: "pointer",
                          transition: "background-color 0.2s"
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = "var(--bg-hover)"}
                        onMouseLeave={(e) => e.target.style.backgroundColor = "var(--bg-tertiary)"}
                      >
                        <strong>{getConversationTitle(conv)}</strong>
                        <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                          {conv.participants.map(p => p.full_name).join(", ")}
                        </p>
                      </div>
                    ))
                  )}
                </div>

                {creatingGroup ? (
                  <div style={{ marginBottom: "16px" }}>
                    <input
                      type="text"
                      placeholder="Group name"
                      value={groupName}
                      onChange={(e) => setGroupName(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "8px",
                        marginBottom: "8px",
                        borderRadius: "4px",
                        border: "1px solid var(--border-color)"
                      }}
                    />
                    <div style={{ maxHeight: "150px", overflowY: "auto", marginBottom: "8px" }}>
                      {users.map((user) => (
                        <label key={user.user_id} style={{ display: "flex", alignItems: "center", marginBottom: "8px" }}>
                          <input
                            type="checkbox"
                            checked={selectedUsers.includes(user.user_id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedUsers([...selectedUsers, user.user_id]);
                              } else {
                                setSelectedUsers(selectedUsers.filter(id => id !== user.user_id));
                              }
                            }}
                            style={{ marginRight: "8px" }}
                          />
                          {user.full_name}
                        </label>
                      ))}
                    </div>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button
                        onClick={createGroupConversation}
                        style={{
                          flex: 1,
                          padding: "8px",
                          backgroundColor: "var(--primary-color)",
                          color: "white",
                          border: "none",
                          borderRadius: "4px",
                          cursor: "pointer"
                        }}
                      >
                        Create
                      </button>
                      <button
                        onClick={() => {
                          setCreatingGroup(false);
                          setGroupName("");
                          setSelectedUsers([]);
                        }}
                        style={{
                          flex: 1,
                          padding: "8px",
                          backgroundColor: "var(--bg-tertiary)",
                          border: "1px solid var(--border-color)",
                          borderRadius: "4px",
                          cursor: "pointer"
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      onClick={() => setShowUserList(!showUserList)}
                      style={{
                        flex: 1,
                        padding: "8px",
                        backgroundColor: "var(--primary-color)",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer"
                      }}
                    >
                      {showUserList ? "Hide Users" : "Message User"}
                    </button>
                    <button
                      onClick={() => setCreatingGroup(true)}
                      style={{
                        flex: 1,
                        padding: "8px",
                        backgroundColor: "var(--secondary-color)",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer"
                      }}
                    >
                      Create Group
                    </button>
                  </div>
                )}

                {showUserList && !creatingGroup && (
                  <div style={{ marginTop: "12px", maxHeight: "200px", overflowY: "auto" }}>
                    {users.map((user) => (
                      <div
                        key={user.user_id}
                        onClick={() => startConversation(user.user_id)}
                        style={{
                          padding: "12px",
                          marginBottom: "8px",
                          backgroundColor: "var(--bg-tertiary)",
                          borderRadius: "8px",
                          cursor: "pointer",
                          transition: "background-color 0.2s"
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = "var(--bg-hover)"}
                        onMouseLeave={(e) => e.target.style.backgroundColor = "var(--bg-tertiary)"}
                      >
                        <strong>{user.full_name}</strong>
                        <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                          {user.role}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                  <h2>{getConversationTitle(selectedConversation)}</h2>
                  <button
                    onClick={() => setSelectedConversation(null)}
                    style={{
                      padding: "8px 16px",
                      backgroundColor: "var(--bg-tertiary)",
                      border: "1px solid var(--border-color)",
                      borderRadius: "4px",
                      cursor: "pointer"
                    }}
                  >
                    Back
                  </button>
                </div>

                <div
                  style={{
                    flex: 1,
                    overflowY: "auto",
                    marginBottom: "16px",
                    padding: "12px",
                    backgroundColor: "var(--bg-tertiary)",
                    borderRadius: "8px"
                  }}
                >
                  {messages.length === 0 ? (
                    <p style={{ color: "var(--text-secondary)" }}>No messages yet</p>
                  ) : (
                    messages.map((msg) => (
                      <div
                        key={msg.message_id}
                        style={{
                          marginBottom: "12px",
                          padding: "8px",
                          backgroundColor: msg.sender_id === currentUser?.user_id ? "var(--primary-color)" : "var(--bg-secondary)",
                          color: msg.sender_id === currentUser?.user_id ? "white" : "inherit",
                          borderRadius: "8px",
                          maxWidth: "80%",
                          marginLeft: msg.sender_id === currentUser?.user_id ? "auto" : "0"
                        }}
                      >
                        <strong>{msg.sender_name}</strong>
                        <p style={{ margin: "4px 0 0 0" }}>{msg.content}</p>
                        <p style={{ fontSize: "12px", marginTop: "4px", opacity: 0.7 }}>
                          {new Date(msg.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                    ))
                  )}
                </div>

                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="text"
                    placeholder="Type a message..."
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === "Enter") sendMessage();
                    }}
                    style={{
                      flex: 1,
                      padding: "8px",
                      borderRadius: "4px",
                      border: "1px solid var(--border-color)"
                    }}
                  />
                  <button
                    onClick={sendMessage}
                    style={{
                      padding: "8px 16px",
                      backgroundColor: "var(--primary-color)",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer"
                    }}
                  >
                    Send
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
