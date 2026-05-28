import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router-dom";
import { ApiClientError, deletePost, getPost } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Post } from "../types";
import { formatDate } from "../utils/format";

type PostDetailLocationState = {
  post?: Post;
};

export function PostDetailPage() {
  const { postId } = useParams<{ postId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { token, canManagePosts } = useAuth();
  const statePost = (location.state as PostDetailLocationState | null)?.post;
  const initialPost = statePost?.postId === postId ? statePost : null;
  const [post, setPost] = useState<Post | null>(initialPost);
  const [loading, setLoading] = useState(!initialPost);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token || !postId) {
      return;
    }
    if (initialPost) {
      return;
    }

    setLoading(true);
    setError(null);
    getPost(token, postId)
      .then(setPost)
      .catch((err: unknown) => {
        setPost(null);
        setError(err instanceof ApiClientError ? err.message : "Failed to load post");
      })
      .finally(() => setLoading(false));
  }, [token, postId, initialPost]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (!postId) {
    return <Navigate to="/posts" replace />;
  }

  async function handleDelete() {
    if (!token || !post || !window.confirm("Delete this post?")) {
      return;
    }
    setBusy(true);
    try {
      await deletePost(token, post.postId);
      navigate("/posts");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to delete post");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <Link to="/posts" className="back-link">
        ← Back to posts
      </Link>

      {loading ? (
        <div className="card">
          <p className="muted">Loading post…</p>
        </div>
      ) : null}

      {error ? <div className="error">{error}</div> : null}

      {post && !loading ? (
        <div className="card stack">
          <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <h2 style={{ margin: 0 }}>{post.title}</h2>
              <p className="muted" style={{ margin: "8px 0 0" }}>
                {post.created_by} · {formatDate(post.creation_time)}
              </p>
            </div>
            {canManagePosts ? (
              <div className="row">
                <Link to={`/posts/${post.postId}/edit`} className="button-link secondary">
                  Edit
                </Link>
                <button type="button" className="danger" onClick={() => void handleDelete()} disabled={busy}>
                  Delete
                </button>
              </div>
            ) : null}
          </div>
          <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{post.body}</p>
          <dl className="detail-list">
            <dt>Post ID</dt>
            <dd>{post.postId}</dd>
          </dl>
        </div>
      ) : null}
    </div>
  );
}
