import { FormEvent, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import {
  ApiClientError,
  createPost,
  deletePost,
  getPost,
  listPosts,
  updatePost,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Post } from "../types";

export function PostsPage() {
  const { token, canManagePosts } = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
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

  useEffect(() => {
    if (!token || !selectedId) {
      setSelectedPost(null);
      return;
    }
    getPost(token, selectedId)
      .then((post) => {
        setSelectedPost(post);
        setTitle(post.title);
        setBody(post.body);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiClientError ? err.message : "Failed to load post");
      });
  }, [token, selectedId]);

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

  async function handleUpdate() {
    if (!token || !selectedId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updatePost(token, selectedId, { title: title.trim(), body: body.trim() });
      await loadPosts();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to update post");
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
      if (selectedId === postId) {
        setSelectedId(null);
        setTitle("");
        setBody("");
      }
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
              <div>
                <strong>{post.title}</strong>
                <div className="muted">
                  {post.created_by} · {new Date(post.creation_time).toLocaleString()}
                </div>
              </div>
              <div className="row">
                <button type="button" className="secondary" onClick={() => setSelectedId(post.postId)}>
                  Edit
                </button>
                {canManagePosts ? (
                  <button type="button" className="danger" onClick={() => handleDelete(post.postId)}>
                    Delete
                  </button>
                ) : null}
              </div>
            </div>
            <p style={{ margin: 0 }}>{post.body}</p>
          </div>
        ))}
      </div>

      {canManagePosts ? (
        <div className="card stack">
          <h3 style={{ margin: 0 }}>{selectedPost ? "Edit post" : "Create post"}</h3>
          <form className="stack" onSubmit={selectedPost ? (event) => { event.preventDefault(); void handleUpdate(); } : handleCreate}>
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
                {selectedPost ? "Update post" : "Create post"}
              </button>
              {selectedPost ? (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    setSelectedId(null);
                    setTitle("");
                    setBody("");
                  }}
                >
                  Cancel edit
                </button>
              ) : null}
            </div>
          </form>
        </div>
      ) : (
        <p className="muted">Readers can view posts but cannot create or edit them.</p>
      )}
    </div>
  );
}
