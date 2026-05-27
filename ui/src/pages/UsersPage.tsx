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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
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

  useEffect(() => {
    if (!token || !selectedId) {
      setSelectedUser(null);
      return;
    }
    getUser(token, selectedId)
      .then((user) => {
        setSelectedUser(user);
        setEmail(user.email);
        setName(user.name ?? "");
        setRole(user.role);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiClientError ? err.message : "Failed to load user");
      });
  }, [token, selectedId]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  async function handleUpdate(event: FormEvent) {
    event.preventDefault();
    if (!token || !selectedId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updateUser(token, selectedId, {
        email: email.trim(),
        name: name.trim() || undefined,
      });
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to update user");
    } finally {
      setBusy(false);
    }
  }

  async function handleRoleChange() {
    if (!token || !selectedId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updateUserRole(token, selectedId, role);
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
      if (selectedId === userId) {
        setSelectedId(null);
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
        {users.map((user) => (
          <div key={user.userId} className="list-item row" style={{ justifyContent: "space-between" }}>
            <div>
              <strong>{user.email}</strong>
              <div className="muted">
                {user.name ?? "No name"} · <span className="badge">{user.role}</span>
              </div>
            </div>
            <div className="row">
              <button type="button" className="secondary" onClick={() => setSelectedId(user.userId)}>
                Manage
              </button>
              {isAdmin ? (
                <button type="button" className="danger" onClick={() => handleDelete(user.userId)}>
                  Delete
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {selectedUser ? (
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
