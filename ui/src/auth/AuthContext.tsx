import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { decodeJwtPayload, formatApiError, getUser, login as apiLogin } from "../api/client";
import type { Role, User } from "../types";

const TOKEN_KEY = "tech_blog_access_token";
const EMAIL_KEY = "tech_blog_email";
const USER_CACHE_KEY = "tech_blog_current_user";
const USER_CACHE_TTL_MS = 5 * 60 * 1000;

interface CachedUser {
  user: User;
  cachedAt: number;
}

function readCachedUser(sub: string): User | null {
  try {
    const raw = sessionStorage.getItem(USER_CACHE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as CachedUser;
    if (
      parsed.user?.userId !== sub ||
      Date.now() - parsed.cachedAt > USER_CACHE_TTL_MS
    ) {
      return null;
    }
    return parsed.user;
  } catch {
    return null;
  }
}

function writeCachedUser(user: User): void {
  const payload: CachedUser = { user, cachedAt: Date.now() };
  sessionStorage.setItem(USER_CACHE_KEY, JSON.stringify(payload));
}

function clearCachedUser(): void {
  sessionStorage.removeItem(USER_CACHE_KEY);
}

interface AuthContextValue {
  token: string | null;
  email: string | null;
  currentUser: User | null;
  profileError: string | null;
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
  const [profileError, setProfileError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(localStorage.getItem(TOKEN_KEY)));

  const refreshCurrentUser = useCallback(async () => {
    if (!token) {
      setCurrentUser(null);
      setProfileError(null);
      return;
    }

    const payload = decodeJwtPayload(token);
    const sub = typeof payload.sub === "string" ? payload.sub : null;
    if (!sub) {
      setCurrentUser(null);
      setProfileError("Signed in, but the session token is missing a user id.");
      return;
    }
    const cached = readCachedUser(sub);
    if (cached) {
      setCurrentUser(cached);
      setProfileError(null);
      return;
    }

    try {
      const user = await getUser(token, sub);
      writeCachedUser(user);
      setCurrentUser(user);
      setProfileError(null);
    } catch (err) {
      setCurrentUser(null);
      setProfileError(formatApiError(err, "Failed to load profile"));
    }
  }, [token]);

  useEffect(() => {
    if (!token) {
      setCurrentUser(null);
      setProfileError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    refreshCurrentUser().finally(() => setLoading(false));
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
    clearCachedUser();
    setToken(null);
    setEmail(null);
    setCurrentUser(null);
    setProfileError(null);
  }, []);

  const value = useMemo(
    () => ({
      token,
      email,
      currentUser,
      profileError,
      loading,
      login,
      logout,
      refreshCurrentUser,
      isAdmin: currentUser?.role === "admin",
      canManagePosts: canManagePostsForRole(currentUser?.role),
    }),
    [token, email, currentUser, profileError, loading, login, logout, refreshCurrentUser],
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
