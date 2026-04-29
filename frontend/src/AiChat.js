import { useState } from "react";
import { auth } from "./firebase";
import API_BASE_URL from "./config";
import "./AiChat.css";

const AiChat = () => {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    const userMessage = { role: "user", content: question };
    setMessages([...messages, userMessage]);
    setQuestion("");
    setLoading(true);

    try {
      const user = auth.currentUser;
      if (!user) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(`${API_BASE_URL}/ai-chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question,
          firebase_uid: user.uid,
        }),
      });

      if (!response.ok) {
        throw new Error("AI service unavailable");
      }

      const data = await response.json();
      const aiMessage = { role: "ai", content: data.answer };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error("AI chat error:", error);
      const errorMessage = {
        role: "ai",
        content: "Sorry, I'm having trouble responding right now. Make sure Ollama is running on the server.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-chat-container">
      <div className="ai-chat-header">
        <h2>AI Assistant</h2>
        <p>Get help with your courses, study sessions, and resources</p>
      </div>

      <div className="ai-chat-messages">
        {messages.length === 0 && (
          <div className="ai-chat-welcome">
            <h3>Welcome to StudySync AI Assistant</h3>
            <p>I can help you with:</p>
            <ul>
              <li>Finding course materials and resources</li>
              <li>Information about your enrolled courses</li>
              <li>Study session planning and scheduling</li>
              <li>General questions about the platform</li>
            </ul>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`ai-message ${msg.role}`}>
            <div className="message-label">{msg.role === 'user' ? 'You' : 'AI Assistant'}</div>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="ai-message ai">
            <div className="message-label">AI Assistant</div>
            <div className="message-content typing">Analyzing your question...</div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="ai-chat-input-form">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Type your question here..."
          disabled={loading}
          className="ai-chat-input"
        />
        <button type="submit" disabled={loading} className="ai-chat-submit">
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
};

export default AiChat;
