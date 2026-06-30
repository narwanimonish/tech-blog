import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { email, currentUser, profileError, logout, loading, isAdmin } = useAuth();
  const profilePath = currentUser ? `/users/${currentUser.userId}` : "/users";

  const profileLine = loading
    ? "Loading profile..."
    : profileError
      ? `${email ?? "Signed in"} · profile unavailable`
      : `${email ?? "Signed in"} · role ${currentUser?.role ?? "unknown"}`;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <div className="brand-mark">TB</div>
          <h1>Tech Blog</h1>
          <p className="muted">
            {profileLine}
          </p>
        </div>
        <button type="button" className="secondary" onClick={logout}>
          Sign out
        </button>
      </header>

      {profileError ? <div className="error">{profileError}</div> : null}

      <nav className="nav">
        <NavLink to="/posts">Posts</NavLink>
        {isAdmin ? (
          <NavLink to="/users">Users</NavLink>
        ) : (
          <NavLink to={profilePath}>Profile</NavLink>
        )}
      </nav>

      <Outlet />
    </div>
  );
}
