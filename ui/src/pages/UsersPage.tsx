import { useCallback, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { deleteUser, formatApiError, listUsers } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { PaginationBar } from "../components/PaginationBar";
import type { User } from "../types";

export function UsersPage() {
  const { token, isAdmin, currentUser, loading: authLoading } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [pageTokens, setPageTokens] = useState<(string | undefined)[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadPage = useCallback(
    async (targetPage: number) => {
      if (!token) {
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const nextToken = targetPage > 1 ? pageTokens[targetPage - 2] : undefined;
        const data = await listUsers(token, { nextToken });
        setUsers(data.items);
        setPage(targetPage);
        if (data.nextToken) {
          setPageTokens((previous) => {
            const next = [...previous];
            next[targetPage - 1] = data.nextToken;
            return next;
          });
          setPageCount((previous) => Math.max(previous, targetPage + 1));
        } else {
          setPageCount((previous) => Math.max(previous, targetPage));
        }
      } catch (err: unknown) {
        setError(formatApiError(err, "Failed to load users"));
      } finally {
        setLoading(false);
      }
    },
    [token, pageTokens],
  );

  useEffect(() => {
    if (!token || !isAdmin) {
      return;
    }
    void loadPage(1);
  }, [token, isAdmin]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (!authLoading && !isAdmin && currentUser) {
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
      await loadPage(page);
    } catch (err) {
      setError(formatApiError(err, "Failed to delete user"));
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
        {loading && users.length === 0 ? <p className="muted">Loading users…</p> : null}
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
              disabled={busy || loading}
            >
              Delete
            </button>
          </div>
        ))}
        <PaginationBar
          page={page}
          pageCount={pageCount}
          loading={loading}
          onPageChange={(targetPage) => void loadPage(targetPage)}
        />
      </div>
    </div>
  );
}
