import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import {
  ApiClientError,
  deleteUser,
  getUser,
  updateUser,
  updateUserRole,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Role, User } from "../types";

const ROLES: Role[] = ["admin", "writer", "reader"];

export function UserDetailPage() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const { token, isAdmin, currentUser, loading: authLoading } = useAuth();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<Role>("reader");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token || !userId) {
      return;
    }
    setLoading(true);
    setError(null);
    getUser(token, userId)
      .then((loaded) => {
        setUser(loaded);
        setEmail(loaded.email);
        setName(loaded.name ?? "");
        setRole(loaded.role);
      })
      .catch((err: unknown) => {
        setUser(null);
        setError(err instanceof ApiClientError ? err.message : "Failed to load user");
      })
      .finally(() => setLoading(false));
  }, [token, userId]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (!authLoading && !isAdmin && currentUser && userId !== currentUser.userId) {
    return <Navigate to={`/users/${currentUser.userId}`} replace />;
  }

  if (!userId) {
    return <Navigate to="/users" replace />;
  }

  async function handleUpdate(event: FormEvent) {
    event.preventDefault();
    if (!token || !user) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await updateUser(token, user.userId, {
        email: email.trim(),
        name: name.trim() || undefined,
      });
      setUser(updated);
      setEmail(updated.email);
      setName(updated.name ?? "");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to update user");
    } finally {
      setBusy(false);
    }
  }

  async function handleRoleChange() {
    if (!token || !user) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await updateUserRole(token, user.userId, role);
      setUser(updated);
      setRole(updated.role);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to change role");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!token || !user || !window.confirm("Delete this user from DynamoDB and Cognito?")) {
      return;
    }
    setBusy(true);
    try {
      await deleteUser(token, user.userId);
      navigate("/users");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to delete user");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <Link to={isAdmin ? "/users" : `/users/${currentUser?.userId ?? userId}`} className="back-link">
        ← {isAdmin ? "Back to users" : "Back to profile"}
      </Link>

      {loading ? (
        <div className="card">
          <p className="muted">Loading user…</p>
        </div>
      ) : null}

      {error ? <div className="error">{error}</div> : null}

      {user && !loading ? (
        <>
          <div className="card stack">
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h2 style={{ margin: 0 }}>{isAdmin ? user.email : "My profile"}</h2>
                <p className="muted" style={{ margin: "8px 0 0" }}>
                  {user.name ?? "No name"} · <span className="badge">{user.role}</span>
                </p>
              </div>
              {isAdmin ? (
                <button type="button" className="danger" onClick={() => void handleDelete()} disabled={busy}>
                  Delete
                </button>
              ) : null}
            </div>
            <dl className="detail-list">
              <dt>User ID</dt>
              <dd>{user.userId}</dd>
              <dt>Email</dt>
              <dd>{user.email}</dd>
              <dt>Name</dt>
              <dd>{user.name ?? "—"}</dd>
              <dt>Role</dt>
              <dd>
                <span className="badge">{user.role}</span>
              </dd>
            </dl>
          </div>

          {isAdmin ? (
            <div className="card stack">
              <h3 style={{ margin: 0 }}>Manage user</h3>
              <form className="stack" onSubmit={handleUpdate}>
                <label>
                  Email
                  <input value={email} onChange={(event) => setEmail(event.target.value)} required />
                </label>
                <label>
                  Name
                  <input value={name} onChange={(event) => setName(event.target.value)} />
                </label>
                <button type="submit" disabled={busy}>
                  Update profile
                </button>
              </form>
              <div className="stack">
                <label>
                  Role
                  <select value={role} onChange={(event) => setRole(event.target.value as Role)}>
                    {ROLES.map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <button type="button" onClick={() => void handleRoleChange()} disabled={busy}>
                  Change role
                </button>
              </div>
            </div>
          ) : (
            <p className="muted">Only admins can edit or delete users.</p>
          )}
        </>
      ) : null}
    </div>
  );
}
