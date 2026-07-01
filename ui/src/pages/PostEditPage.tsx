import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { formatApiError, getPost, updatePost } from "../api/client";
import type { Post } from "../types";
import { useAuth } from "../auth/AuthContext";

export function PostEditPage() {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();
  const { token, canManagePosts, canManagePost } = useAuth();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token || !postId) {
      return;
    }
    getPost(token, postId)
      .then((loaded) => {
        setPost(loaded);
        setTitle(loaded.title);
        setBody(loaded.body);
      })
      .catch((err: unknown) => {
        setError(formatApiError(err, "Failed to load post"));
      })
      .finally(() => setLoading(false));
  }, [token, postId]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (!canManagePosts) {
    return <Navigate to={postId ? `/posts/${postId}` : "/posts"} replace />;
  }

  if (post && !canManagePost(post)) {
    return <Navigate to={`/posts/${postId}`} replace />;
  }

  if (!postId) {
    return <Navigate to="/posts" replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!token) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updatePost(token, postId, { title: title.trim(), body: body.trim() });
      navigate(`/posts/${postId}`);
    } catch (err) {
      setError(formatApiError(err, "Failed to update post"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <Link to={`/posts/${postId}`} className="back-link">
        ← Back to post
      </Link>

      <div className="card stack">
        <h2 style={{ margin: 0 }}>Edit post</h2>
        {loading ? <p className="muted">Loading…</p> : null}
        {error ? <div className="error">{error}</div> : null}
        {!loading ? (
          <form className="stack" onSubmit={handleSubmit}>
            <label>
              Title
              <input value={title} onChange={(event) => setTitle(event.target.value)} required />
            </label>
            <label>
              Body
              <textarea value={body} onChange={(event) => setBody(event.target.value)} required />
            </label>
            <div className="row">
              <button type="submit" disabled={busy}>
                Save changes
              </button>
              <Link to={`/posts/${postId}`} className="button-link secondary">
                Cancel
              </Link>
            </div>
          </form>
        ) : null}
      </div>
    </div>
  );
}
