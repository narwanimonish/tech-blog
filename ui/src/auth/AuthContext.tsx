import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { decodeJwtPayload, getUser, listUsers, login as apiLogin } from "../api/client";
import type { Role, User } from "../types";

const TOKEN_KEY = "tech_blog_access_token";
const EMAIL_KEY = "tech_blog_email";

interface AuthContextValue {
  token: string | null;
  email: string | null;
  currentUser: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshCurrentUser: () => Promise<void>;
  isAdmin: boolean;
  canManagePosts: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function canManagePostsForRole(role: Role | undefined): boolean {
  return role === "admin" || role === "writer";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [email, setEmail] = useState<string | null>(() => localStorage.getItem(EMAIL_KEY));
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(localStorage.getItem(TOKEN_KEY)));

  const refreshCurrentUser = useCallback(async () => {
    if (!token) {
      setCurrentUser(null);
      return;
    }

    const payload = decodeJwtPayload(token);
    const sub = typeof payload.sub === "string" ? payload.sub : null;
    if (sub) {
      try {
        setCurrentUser(await getUser(token, sub));
        return;
      } catch {
        // Fall back to scanning the user list below.
      }
    }

    const users = await listUsers(token);
    const match =
      users.find((user) => user.email === email) ??
      users.find((user) => user.userId === sub) ??
      null;
    setCurrentUser(match);
  }, [token, email]);

  useEffect(() => {
    if (!token) {
      setCurrentUser(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    refreshCurrentUser()
      .catch(() => setCurrentUser(null))
      .finally(() => setLoading(false));
  }, [token, refreshCurrentUser]);

  const login = useCallback(async (username: string, password: string) => {
    const response = await apiLogin(username, password);
    localStorage.setItem(TOKEN_KEY, response.accessToken);
    localStorage.setItem(EMAIL_KEY, username);
    setToken(response.accessToken);
    setEmail(username);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
    setToken(null);
    setEmail(null);
    setCurrentUser(null);
  }, []);

  const value = useMemo(
    () => ({
      token,
      email,
      currentUser,
      loading,
      login,
      logout,
      refreshCurrentUser,
      isAdmin: currentUser?.role === "admin",
      canManagePosts: canManagePostsForRole(currentUser?.role),
    }),
    [token, email, currentUser, loading, login, logout, refreshCurrentUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
