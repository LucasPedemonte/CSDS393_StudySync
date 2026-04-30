/**
 * Resource library for posting, voting on, and moderating class materials.
 */
import { useState, useEffect, useCallback } from "react";
import { auth } from "./firebase";
import { useParams } from "react-router-dom";
import "./LoginPage.css";
import "./ResourcesPage.css";
import API_BASE_URL from "./config";

const ResourcesPage = () => {
  const { courseId } = useParams();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    resource_link: "",
  });

  /** Load the current user profile used for resource actions. */
  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged(async (firebaseUser) => {
      if (firebaseUser) {
        try {
          const response = await fetch(
            `${API_BASE_URL}/user/${firebaseUser.uid}`,
          );
          if (response.ok) {
            const userData = await response.json();
            setCurrentUser({
              uid: firebaseUser.uid,
              email: firebaseUser.email,
              ...userData,
            });
          }
        } catch (err) {
          console.error("Error fetching user profile:", err);
        }
      }
    });

    return () => unsubscribe();
  }, []);

  /** Fetch the visible resource posts for the active course. */
  const fetchPosts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      if (courseId) {
        params.append("course_id", courseId);
      }
      if (currentUser?.uid) {
        params.append("current_user_uid", currentUser.uid);
      }
      const response = await fetch(
        `${API_BASE_URL}/posts?${params.toString()}`,
      );
      if (!response.ok) throw new Error("Failed to fetch posts");
      const data = await response.json();
      setPosts(data);
    } catch (err) {
      setError("Failed to load posts. Please try again.");
      console.error("Error fetching posts:", err);
    } finally {
      setLoading(false);
    }
  }, [courseId, currentUser?.uid]);

  /** Flag one post for TA or admin review. */
  const handleFlagPost = async (postId) => {
    if (!window.confirm("Are you sure you want to flag this post for review?"))
      return;
    try {
      const res = await fetch(`${API_BASE_URL}/posts/${postId}/flag`, {
        method: "POST",
      });
      if (res.ok) {
        alert("Post has been flagged for TA review.");
        // Optional: update local state to show it's flagged
        setPosts((prev) =>
          prev.map((p) => (p.id === postId ? { ...p, is_flagged: true } : p)),
        );
      }
    } catch (err) {
      console.error("Flagging failed", err);
    }
  };

  useEffect(() => {
    if (currentUser) {
      fetchPosts();
    }
  }, [currentUser, courseId, fetchPosts]);

  /** Update local form state while clearing stale validation errors. */
  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    setFormError(null);
  };

  /** Create one new resource post after client-side validation. */
  const handleCreatePost = async (e) => {
    e.preventDefault();

    if (!formData.title.trim()) {
      setFormError("Please enter a title for your post.");
      return;
    }
    if (
      formData.resource_link &&
      !/^https?:\/\//i.test(formData.resource_link.trim())
    ) {
      setFormError("Resource link must start with http:// or https://");
      return;
    }
    if (formData.description && formData.description.trim().length < 5) {
      setFormError("Description must be at least 5 characters if provided.");
      return;
    }
    setFormError(null);

    try {
      setIsSubmitting(true);
      const params = new URLSearchParams({
        course_id: courseId || 0,
        author_uid: currentUser.uid,
      });

      const response = await fetch(
        `${API_BASE_URL}/posts?${params.toString()}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: formData.title.trim(),
            description: formData.description.trim() || null,
            resource_link: formData.resource_link.trim() || null,
          }),
        },
      );

      if (!response.ok) throw new Error("Failed to create post");

      setFormData({ title: "", description: "", resource_link: "" });
      setShowForm(false);
      await fetchPosts();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  /** Apply an upvote, downvote, or neutral vote to a post. */
  const handleVote = async (postId, newVote) => {
    if (!currentUser) return;
    try {
      const response = await fetch(
        `${API_BASE_URL}/posts/${postId}/vote?user_uid=${currentUser.uid}&vote=${newVote}`,
        { method: "POST" },
      );
      if (!response.ok) throw new Error("Failed to update vote");
      setPosts((prevPosts) =>
        prevPosts.map((post) => {
          if (post.id === postId) {
            let score = post.score - (post.user_vote || 0) + newVote;
            return {
              ...post,
              score,
              user_vote: newVote,
            };
          }
          return post;
        }),
      );
    } catch (err) {
      console.error("Error updating vote:", err);
      await fetchPosts();
    }
  };

  /** Convert an ISO timestamp into a compact relative label. */
  const formatDate = (isoString) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  };

  /** Return the avatar initial for a post author. */
  const getInitial = (name) => {
    return name ? name.charAt(0).toUpperCase() : "?";
  };

  const handleDeletePost = async (postId) => {
    if (!window.confirm("Are you sure you want to delete this resource?"))
      return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/posts/${postId}?user_uid=${currentUser.uid}`,
        { method: "DELETE" },
      );
      if (!response.ok) throw new Error("Failed to delete post");
      await fetchPosts();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="resources-page">
      {/* Ambient blobs */}
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      <div className="resources-wrapper">
        <div className="resources-left">
          <h1 className="tagline">
            Resource <span className="highlight">Library</span>
          </h1>
          <p className="tagline-sub">
            Access shared materials and study resources
          </p>
        </div>

        <div className="resources-right">
          {/* Post Creation Form */}
          {currentUser && (
            <div className="post-creation-form">
              {!showForm ? (
                <button
                  onClick={() => setShowForm(true)}
                  style={{
                    width: "100%",
                    padding: "12px 16px",
                    background: "var(--navy-input)",
                    border: "1px solid var(--border)",
                    borderRadius: "10px",
                    color: "var(--text-placeholder)",
                    cursor: "pointer",
                    fontSize: "14px",
                    transition: "all 0.25s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.borderColor = "var(--teal)";
                    e.target.style.color = "var(--text-secondary)";
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.borderColor = "var(--border)";
                    e.target.style.color = "var(--text-placeholder)";
                  }}
                >
                  Share a resource...
                </button>
              ) : (
                <form onSubmit={handleCreatePost}>
                  <h3 className="form-title">Create New Post</h3>

                  <div className="form-field">
                    <label>Title *</label>
                    <input
                      type="text"
                      name="title"
                      placeholder="e.g., Calculus Study Guide"
                      value={formData.title}
                      onChange={handleFormChange}
                      maxLength={200}
                    />
                  </div>

                  <div className="form-field">
                    <label>Description</label>
                    <textarea
                      name="description"
                      placeholder="Describe the resource or add notes..."
                      value={formData.description}
                      onChange={handleFormChange}
                      maxLength={500}
                    />
                  </div>

                  <div className="form-field">
                    <label>Resource Link</label>
                    <input
                      type="url"
                      name="resource_link"
                      placeholder="https://example.com"
                      value={formData.resource_link}
                      onChange={handleFormChange}
                    />
                  </div>

                  {formError && (
                    <div className="error-message">{formError}</div>
                  )}

                  <div className="form-buttons">
                    <button
                      type="button"
                      onClick={() => {
                        setShowForm(false);
                        setFormData({
                          title: "",
                          description: "",
                          resource_link: "",
                        });
                        setFormError(null);
                      }}
                      className="btn-cancel"
                      disabled={isSubmitting}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="btn-post"
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? "Posting..." : "Post Resource"}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* Posts Feed */}
          {error && <div className="error-message">{error}</div>}

          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              Loading resources...
            </div>
          ) : posts.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📚</div>
              <h3 className="empty-state-title">No resources yet</h3>
              <p className="empty-state-text">
                Be the first to share a resource with the community!
              </p>
            </div>
          ) : (
            <div className="posts-feed">
              {posts.map((post) => (
                <div key={post.id} className="post-card">
                  <div className="post-upvote-section">
                    {/* Upvote Button */}
                    <button
                      className={`upvote-button ${post.user_vote === 1 ? "active-vote" : ""}`}
                      onClick={() =>
                        handleVote(post.id, post.user_vote === 1 ? 0 : 1)
                      }
                      title={post.user_vote === 1 ? "Remove upvote" : "Upvote"}
                      aria-label={
                        post.user_vote === 1 ? "Remove upvote" : "Upvote"
                      }
                    >
                      ▲
                    </button>

                    {/* Vote Count */}
                    <div
                      className={`upvote-count 
      ${post.score < 0 ? "negative-score" : ""} 
      ${post.user_vote !== 0 ? "active-highlight" : ""}`}
                    >
                      {post.score}
                    </div>

                    {/* Downvote Button */}
                    <button
                      className={`upvote-button ${post.user_vote === -1 ? "active-vote" : ""}`}
                      onClick={() =>
                        handleVote(post.id, post.user_vote === -1 ? 0 : -1)
                      }
                      title={
                        post.user_vote === -1 ? "Remove downvote" : "Downvote"
                      }
                      aria-label={
                        post.user_vote === -1 ? "Remove downvote" : "Downvote"
                      }
                    >
                      ▼
                    </button>
                  </div>

                  <div className="post-content">
                    <div className="post-header">
                      <div className="post-author-info">
                        <div className="author-avatar">
                          {getInitial(post.author_name)}
                        </div>
                        <div className="author-details">
                          <div className="author-name">{post.author_name}</div>
                          <span className={`author-role ${post.author_role}`}>
                            {post.author_role}
                          </span>
                        </div>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "12px",
                        }}
                      >
                        <div className="post-timestamp">
                          {formatDate(post.created_at)}
                        </div>
                        {/* ONLY SHOW FOR TA/ADMIN */}
                        {(currentUser?.role === "TA" ||
                          currentUser?.role === "Admin") && (
                          <button
                            onClick={() => handleDeletePost(post.id)}
                            className="icon-btn-outline delete-outline"
                            title="Delete Post"
                          >
                            🗑
                          </button>
                        )}

                        {/* FLAG CONTENT BUTTON */}
                        <button
                          onClick={() => handleFlagPost(post.id)}
                          className={`icon-btn-outline flag-outline ${post.is_flagged ? "active" : ""}`}
                          disabled={post.is_flagged}
                          title={
                            post.is_flagged
                              ? "Flagged for Review"
                              : "Flag Content"
                          }
                        >
                          {post.is_flagged ? "🚩" : "🏳"}
                        </button>
                      </div>
                    </div>

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
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResourcesPage;
