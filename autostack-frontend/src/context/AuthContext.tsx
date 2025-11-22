import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from "react";
import { API_BASE_URL } from "@/config";
import { clearTokens, loadTokens, saveTokens, StoredTokens } from "@/lib/auth-storage";

type AuthUser = {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string | null;
};

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  completeOAuth: (params: { provider: string | null; accessToken: string; refreshToken: string; expiresIn: number | null }) => Promise<void>;
  authorizedRequest: (path: string, init?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const ACCESS_TOKEN_SAFETY_MS = 5_000;
const DEFAULT_EXPIRY_SECONDS = 30 * 60;

const computeExpiresAt = (expiresIn: number | null | undefined) =>
  expiresIn ? Date.now() + expiresIn * 1000 : Date.now() + DEFAULT_EXPIRY_SECONDS * 1000;

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [tokens, setTokens] = useState<StoredTokens | null>(() => loadTokens());
  const [loading, setLoading] = useState(true);

  const persistTokens = useCallback((next: StoredTokens | null) => {
    setTokens(next);
    if (next) {
      saveTokens(next);
    } else {
      clearTokens();
    }
  }, []);

  const fetchSession = useCallback(
    async (accessToken: string) => {
      const response = await fetch(`${API_BASE_URL}/api/auth/session`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      if (!response.ok) {
        return false;
      }
      const data = await response.json();
      setUser(data.user);
      return true;
    },
    []
  );

  const refreshTokens = useCallback(async () => {
    if (!tokens) return null;
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshToken: tokens.refreshToken }),
      });
      if (!response.ok) {
        persistTokens(null);
        setUser(null);
        return null;
      }
      const data = await response.json();
      const newTokens: StoredTokens = {
        accessToken: data.accessToken,
        refreshToken: data.refreshToken ?? tokens.refreshToken,
        expiresAt: computeExpiresAt(data.expiresIn ?? null),
      };
      persistTokens(newTokens);
      setUser(data.user);
      return newTokens;
    } catch {
      persistTokens(null);
      setUser(null);
      return null;
    }
  }, [persistTokens, tokens]);

  const ensureValidAccessToken = useCallback(async () => {
    if (!tokens) return null;
    let currentTokens = tokens;
    if (currentTokens.expiresAt && Date.now() > currentTokens.expiresAt - ACCESS_TOKEN_SAFETY_MS) {
      const refreshed = await refreshTokens();
      if (!refreshed) {
        return null;
      }
      currentTokens = refreshed;
    }
    return currentTokens.accessToken;
  }, [refreshTokens, tokens]);

  const authorizedRequest = useCallback(
    async (path: string, init?: RequestInit) => {
      const buildUrl = (target: string) =>
        target.startsWith("http") ? target : `${API_BASE_URL}${target.startsWith("/") ? target : `/${target}`}`;

      const createRequest = (authToken: string) => {
        const headers = new Headers(init?.headers || undefined);
        if (!headers.has("Content-Type")) {
          headers.set("Content-Type", "application/json");
        }
        headers.set("Authorization", `Bearer ${authToken}`);
        return fetch(buildUrl(path), {
          ...init,
          headers,
        });
      };

      let token = await ensureValidAccessToken();
      if (!token) {
        throw new Error("Not authenticated");
      }
      let response = await createRequest(token);
      if (response.status === 401) {
        const refreshed = await refreshTokens();
        if (!refreshed) {
          throw new Error("Session expired");
          }
        response = await createRequest(refreshed.accessToken);
      }
      return response;
    },
    [ensureValidAccessToken, refreshTokens]
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error?.error?.message ?? "Unable to sign in");
      }
      const data = await response.json();
      const nextTokens: StoredTokens = {
        accessToken: data.accessToken,
        refreshToken: data.refreshToken,
        expiresAt: computeExpiresAt(data.expiresIn ?? null),
      };
      persistTokens(nextTokens);
      setUser(data.user);
    },
    [persistTokens]
  );

  const signup = useCallback(
    async (name: string, email: string, password: string) => {
      const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error?.error?.message ?? "Unable to create account");
      }
      const data = await response.json();
      const nextTokens: StoredTokens = {
        accessToken: data.accessToken,
        refreshToken: data.refreshToken,
        expiresAt: computeExpiresAt(data.expiresIn ?? null),
      };
      persistTokens(nextTokens);
      setUser(data.user);
    },
    [persistTokens]
  );

  const logout = useCallback(async () => {
    try {
      if (tokens?.refreshToken) {
        await fetch(`${API_BASE_URL}/api/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refreshToken: tokens.refreshToken }),
        });
      }
    } catch {
      // ignore logout failures
    } finally {
      persistTokens(null);
      setUser(null);
    }
  }, [persistTokens, tokens]);

  const completeOAuth = useCallback(
    async ({ provider, accessToken, refreshToken, expiresIn }: { provider: string | null; accessToken: string; refreshToken: string; expiresIn: number | null }) => {
      const tokenPayload: StoredTokens = {
        accessToken,
        refreshToken,
        expiresAt: computeExpiresAt(expiresIn),
      };
      persistTokens(tokenPayload);
      const ok = await fetchSession(accessToken);
      if (!ok) {
        const refreshed = await refreshTokens();
        if (!refreshed) {
          throw new Error(`Unable to finalize ${provider ?? "OAuth"} login`);
        }
      }
    },
    [fetchSession, persistTokens, refreshTokens]
  );

  useEffect(() => {
    let isMounted = true;
    const bootstrap = async () => {
      if (!tokens) {
        if (isMounted) setLoading(false);
        return;
      }
      const ok = await fetchSession(tokens.accessToken);
      if (!ok) {
        await refreshTokens();
      }
      if (isMounted) setLoading(false);
    };
    bootstrap();
    return () => {
      isMounted = false;
    };
  }, [fetchSession, refreshTokens, tokens]);

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      signup,
      logout,
      completeOAuth,
      authorizedRequest,
    }),
    [authorizedRequest, completeOAuth, loading, login, logout, signup, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuthContext = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext must be used within AuthProvider");
  }
  return ctx;
};

