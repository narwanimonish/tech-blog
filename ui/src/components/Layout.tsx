import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { email, currentUser, logout, loading } = useAuth();

  return (
    <div className="app-shell">
      <header className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
        <div>
          <h1 style={{ margin: 0 }}>Tech Blog</h1>
          <p className="muted" style={{ margin: "4px 0 0" }}>
            {loading
              ? "Loading profile..."
              : `${email ?? "Signed in"} · role ${currentUser?.role ?? "unknown"}`}
          </p>
        </div>
        <button type="button" className="secondary" onClick={logout}>
          Sign out
        </button>
      </header>

      <nav className="nav">
        <NavLink to="/posts">Posts</NavLink>
        <NavLink to="/users">Users</NavLink>
      </nav>

      <Outlet />
    </div>
  );
}
