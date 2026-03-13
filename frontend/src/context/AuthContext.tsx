import {
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { authApi } from "@/api/client";
import { getStoredTokens, storeTokens, clearStoredTokens } from "@/api/tokens";
import { AuthContext, type AuthState } from "@/context/authTypes";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Listen for forced logout from API client (e.g. refresh token expired)
  useEffect(() => {
    function handleForceLogout() {
      setState({ user: null, isAuthenticated: false, isLoading: false });
    }
    window.addEventListener("auth:logout", handleForceLogout);
    return () => window.removeEventListener("auth:logout", handleForceLogout);
  }, []);

  // Initialize auth state from stored tokens
  useEffect(() => {
    let cancelled = false;

    async function init() {
      const stored = getStoredTokens();
      if (!stored?.access_token) {
        setState({ user: null, isAuthenticated: false, isLoading: false });
        return;
      }

      try {
        // authApi.getMe uses the request() function which handles token refresh
        const user = await authApi.getMe();
        if (!cancelled) {
          setState({ user, isAuthenticated: true, isLoading: false });
        }
      } catch {
        clearStoredTokens();
        if (!cancelled) {
          setState({ user: null, isAuthenticated: false, isLoading: false });
        }
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await authApi.login(email, password);
    storeTokens({
      access_token: data.access_token,
      refresh_token: data.refresh_token,
    });

    const user = await authApi.getMe();
    setState({ user, isAuthenticated: true, isLoading: false });
  }, []);

  const register = useCallback(
    async (email: string, name: string, password: string) => {
      const data = await authApi.register(email, name, password);
      storeTokens({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
      });

      const user = await authApi.getMe();
      setState({ user, isAuthenticated: true, isLoading: false });
    },
    []
  );

  const logout = useCallback(() => {
    clearStoredTokens();
    setState({ user: null, isAuthenticated: false, isLoading: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
