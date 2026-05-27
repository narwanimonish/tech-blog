import { FormEvent, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import {
  ApiClientError,
  deleteUser,
  getUser,
  listUsers,
  updateUser,
  updateUserRole,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Role, User } from "../types";

const ROLES: Role[] = ["admin", "writer", "reader"];

export function UsersPage() {
  const { token, isAdmin } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [viewedUser, setViewedUser] = useState<User | null>(null);
  const [viewLoading, setViewLoading] = useState(false);
  const [manageUserId, setManageUserId] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<Role>("reader");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadUsers() {
    if (!token) {
      return;
    }
    setUsers(await listUsers(token));
  }

  useEffect(() => {
    loadUsers().catch((err: unknown) => {
      setError(err instanceof ApiClientError ? err.message : "Failed to load users");
    });
  }, [token]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  async function handleViewUser(userId: string) {
    if (!token) {
      return;
    }
    setViewLoading(true);
    setError(null);
    try {
      setViewedUser(await getUser(token, userId));
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load user");
      setViewedUser(null);
    } finally {
      setViewLoading(false);
    }
  }

  async function handleStartManage(userId: string) {
    if (!token) {
      return;
    }
    setError(null);
    try {
      const user = await getUser(token, userId);
      setManageUserId(userId);
      setViewedUser(user);
      setEmail(user.email);
      setName(user.name ?? "");
      setRole(user.role);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load user for manage");
    }
  }

  async function handleUpdate(event: FormEvent) {
    event.preventDefault();
    if (!token || !manageUserId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await updateUser(token, manageUserId, {
        email: email.trim(),
        name: name.trim() || undefined,
      });
      setViewedUser(updated);
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to update user");
    } finally {
      setBusy(false);
    }
  }

  async function handleRoleChange() {
    if (!token || !manageUserId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await updateUserRole(token, manageUserId, role);
      setViewedUser(updated);
      setRole(updated.role);
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to change role");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(userId: string) {
    if (!token || !window.confirm("Delete this user from DynamoDB and Cognito?")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteUser(token, userId);
      if (manageUserId === userId) {
        setManageUserId(null);
      }
      if (viewedUser?.userId === userId) {
        setViewedUser(null);
      }
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to delete user");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      {error ? <div className="error">{error}</div> : null}

      <div className="card stack">
        <h2 style={{ margin: 0 }}>Users</h2>
        <p className="muted">Click a user to load them with GET /users/{"{userId}"}.</p>
        {users.map((user) => (
          <div
            key={user.userId}
            className={`list-item row list-item-clickable${
              viewedUser?.userId === user.userId ? " selected" : ""
            }`}
            style={{ justifyContent: "space-between" }}
            onClick={() => void handleViewUser(user.userId)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                void handleViewUser(user.userId);
              }
            }}
            role="button"
            tabIndex={0}
          >
            <div>
              <strong>{user.email}</strong>
              <div className="muted">
                {user.name ?? "No name"} · <span className="badge">{user.role}</span>
              </div>
            </div>
            <div className="row" onClick={(event) => event.stopPropagation()}>
              <button
                type="button"
                className="secondary"
                onClick={() => void handleStartManage(user.userId)}
              >
                Manage
              </button>
              {isAdmin ? (
                <button type="button" className="danger" onClick={() => void handleDelete(user.userId)}>
                  Delete
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {viewLoading ? (
        <div className="card">
          <p className="muted">Loading user…</p>
        </div>
      ) : null}

      {viewedUser && !viewLoading ? (
        <div className="card stack">
          <h3 style={{ margin: 0 }}>User details</h3>
          <p className="muted">Loaded via GET /users/{viewedUser.userId}</p>
          <dl className="detail-list">
            <dt>Email</dt>
            <dd>{viewedUser.email}</dd>
            <dt>Name</dt>
            <dd>{viewedUser.name ?? "—"}</dd>
            <dt>Role</dt>
            <dd>
              <span className="badge">{viewedUser.role}</span>
            </dd>
            <dt>User ID</dt>
            <dd>{viewedUser.userId}</dd>
          </dl>
        </div>
      ) : null}

      {manageUserId && viewedUser ? (
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
            <button type="submit" disabled={busy || !isAdmin}>
              Update profile
            </button>
          </form>

          {isAdmin ? (
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
          ) : (
            <p className="muted">Only admins can update profiles, change roles, or delete users.</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
