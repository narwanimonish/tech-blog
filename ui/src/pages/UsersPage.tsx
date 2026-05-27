import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ApiClientError, deleteUser, listUsers } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { User } from "../types";

export function UsersPage() {
  const { token, isAdmin, currentUser, loading } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token || !isAdmin) {
      return;
    }
    listUsers(token)
      .then(setUsers)
      .catch((err: unknown) => {
        setError(err instanceof ApiClientError ? err.message : "Failed to load users");
      });
  }, [token, isAdmin]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (!loading && !isAdmin && currentUser) {
    return <Navigate to={`/users/${currentUser.userId}`} replace />;
  }

  if (!isAdmin) {
    return (
      <div className="card">
        <p className="muted">Loading your profile…</p>
      </div>
    );
  }

  async function handleDelete(userId: string) {
    if (!token || !window.confirm("Delete this user from DynamoDB and Cognito?")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteUser(token, userId);
      setUsers(await listUsers(token));
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
        <p className="muted">Admin only — list of all users.</p>
        {users.map((user) => (
          <div key={user.userId} className="list-item row" style={{ justifyContent: "space-between" }}>
            <Link to={`/users/${user.userId}`} className="list-link">
              <strong>{user.email}</strong>
              <div className="muted">
                {user.name ?? "No name"} · <span className="badge">{user.role}</span>
              </div>
            </Link>
            <button
              type="button"
              className="danger"
              onClick={() => void handleDelete(user.userId)}
              disabled={busy}
            >
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
