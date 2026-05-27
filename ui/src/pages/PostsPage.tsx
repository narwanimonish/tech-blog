import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ApiClientError, createPost, deletePost, listPosts } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Post } from "../types";
import { formatDate } from "../utils/format";

export function PostsPage() {
  const { token, canManagePosts } = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadPosts() {
    if (!token) {
      return;
    }
    setPosts(await listPosts(token));
  }

  useEffect(() => {
    loadPosts().catch((err: unknown) => {
      setError(err instanceof ApiClientError ? err.message : "Failed to load posts");
    });
  }, [token]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!token) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createPost(token, { title: title.trim(), body: body.trim() });
      setTitle("");
      setBody("");
      await loadPosts();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to create post");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(postId: string) {
    if (!token || !window.confirm("Delete this post?")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deletePost(token, postId);
      await loadPosts();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to delete post");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      {error ? <div className="error">{error}</div> : null}

      <div className="card stack">
        <h2 style={{ margin: 0 }}>Posts</h2>
        {posts.length === 0 ? <p className="muted">No posts yet.</p> : null}
        {posts.map((post) => (
          <div key={post.postId} className="list-item stack">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <Link to={`/posts/${post.postId}`} className="list-link">
                <strong>{post.title}</strong>
                <div className="muted">
                  {post.created_by} · {formatDate(post.creation_time)}
                </div>
                <p style={{ margin: "8px 0 0", color: "#1f2933" }}>{post.body}</p>
              </Link>
              {canManagePosts ? (
                <div className="row">
                  <Link to={`/posts/${post.postId}/edit`} className="button-link secondary">
                    Edit
                  </Link>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => void handleDelete(post.postId)}
                    disabled={busy}
                  >
                    Delete
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {canManagePosts ? (
        <div className="card stack">
          <h3 style={{ margin: 0 }}>Create post</h3>
          <form className="stack" onSubmit={handleCreate}>
            <label>
              Title
              <input value={title} onChange={(event) => setTitle(event.target.value)} required />
            </label>
            <label>
              Body
              <textarea value={body} onChange={(event) => setBody(event.target.value)} required />
            </label>
            <button type="submit" disabled={busy}>
              Create post
            </button>
          </form>
        </div>
      ) : (
        <p className="muted">Readers can view posts but cannot create or edit them.</p>
      )}
    </div>
  );
}
