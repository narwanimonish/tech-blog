import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { formatApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { login, token, loading } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!loading && token) {
    return <Navigate to="/posts" replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(formatApiError(err, "Login failed. Check your credentials."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="card stack" style={{ maxWidth: 420, margin: "48px auto" }}>
        <h1>Tech Blog</h1>
        <p className="muted">Sign in with your Cognito email and password.</p>
        <form className="stack" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              autoComplete="username"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          {error ? <div className="error">{error}</div> : null}
          <button type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
