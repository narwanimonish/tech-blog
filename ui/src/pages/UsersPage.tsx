import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ApiClientError, deleteUser, listUsers } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { User } from "../types";

export function UsersPage() {
  const { token, isAdmin } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
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

  async function handleDelete(userId: string) {
    if (!token || !window.confirm("Delete this user from DynamoDB and Cognito?")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteUser(token, userId);
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
            <Link to={`/users/${user.userId}`} className="list-link">
              <strong>{user.email}</strong>
              <div className="muted">
                {user.name ?? "No name"} · <span className="badge">{user.role}</span>
              </div>
            </Link>
            {isAdmin ? (
              <button
                type="button"
                className="danger"
                onClick={() => void handleDelete(user.userId)}
                disabled={busy}
              >
                Delete
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
