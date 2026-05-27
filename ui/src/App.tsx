import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { PostDetailPage } from "./pages/PostDetailPage";
import { PostEditPage } from "./pages/PostEditPage";
import { PostsPage } from "./pages/PostsPage";
import { UserDetailPage } from "./pages/UserDetailPage";
import { UsersPage } from "./pages/UsersPage";
import { useAuth } from "./auth/AuthContext";

function ProtectedLayout() {
  const { token, loading } = useAuth();
  if (loading) {
    return (
      <div className="app-shell">
        <div className="card">Loading...</div>
      </div>
    );
  }
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <Layout />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Navigate to="/posts" replace />} />
        <Route path="/posts" element={<PostsPage />} />
        <Route path="/posts/:postId" element={<PostDetailPage />} />
        <Route path="/posts/:postId/edit" element={<PostEditPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/users/:userId" element={<UserDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/posts" replace />} />
    </Routes>
  );
}
