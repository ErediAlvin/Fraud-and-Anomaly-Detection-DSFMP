/**
 * DSFMP Fraud Detection — Auth Context
 *
 * Provides authentication state (user, tokens, loading) to the entire app
 * via React Context. Exposes login, verify2FA, and logout actions.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import {
  api,
  storeTokens,
  clearTokens,
  getStoredTokens,
} from '../lib/api';

// ── Types ──────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: string;
  phone?: string | null;
  avatarUrl?: string | null;
  twoFaEnabled: boolean;
}

export function getDesignatedRouteForRole(role?: string): string {
  switch (role) {
    case 'fraud_analyst':
      return '/alerts';
    case 'supervisor':
      return '/cases';
    case 'county_officer':
      return '/beneficiaries';
    case 'school_admin':
      return '/procedures';
    case 'system_admin':
      return '/settings';
    default:
      return '/dashboard';
  }
}

interface LoginPayload {
  email: string;
  password: string;
  role?: string;
}

interface LoginResult {
  requires2Fa: boolean;
  tempToken?: string;
  user?: AuthUser;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** Step 1: email + password login. Returns whether 2FA is required. */
  login: (payload: LoginPayload) => Promise<LoginResult>;
  /** Step 2: verify the TOTP code with the temp token from step 1. */
  verify2FA: (tempToken: string, otpCode: string) => Promise<AuthUser>;
  /** Log out — blacklist token on server, clear local storage. */
  logout: () => Promise<void>;
}

// ── Context ────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ───────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount, check if we have stored tokens and validate them
  useEffect(() => {
    const tokens = getStoredTokens();
    if (!tokens?.accessToken) {
      setIsLoading(false);
      return;
    }

    // Validate token by fetching current user info via /health
    // or a lightweight endpoint. For now we decode from stored user.
    const storedUser = localStorage.getItem('dsfmp_user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        clearTokens();
        localStorage.removeItem('dsfmp_user');
      }
    }
    setIsLoading(false);
  }, []);

  // ── Login ──
  const login = useCallback(async (payload: LoginPayload): Promise<LoginResult> => {
    const body: Record<string, any> = {
      email: payload.email,
      password: payload.password,
    };
    if (payload.role) {
      body.role = payload.role;
    }
    const data = await api.post<any>('/auth/login', body);

    // Backend uses snake_case, but also has serialization_alias for camelCase
    const requires2Fa = data.requires_2fa ?? data.requires2Fa ?? false;
    const tempToken = data.temp_token ?? data.tempToken;

    if (requires2Fa) {
      return { requires2Fa: true, tempToken };
    }

    // No 2FA — we got full tokens
    const accessToken = data.access_token ?? data.accessToken;
    const refreshToken = data.refresh_token ?? data.refreshToken;

    storeTokens({ accessToken, refreshToken });

    const authUser: AuthUser = data.user;
    setUser(authUser);
    localStorage.setItem('dsfmp_user', JSON.stringify(authUser));

    return { requires2Fa: false, user: authUser };
  }, []);

  // ── Verify 2FA ──
  const verify2FA = useCallback(async (tempToken: string, otpCode: string): Promise<AuthUser> => {
    const data = await api.post<any>('/auth/verify-2fa', {
      temp_token: tempToken,
      otp_code: otpCode,
    });

    const accessToken = data.access_token ?? data.accessToken;
    const refreshToken = data.refresh_token ?? data.refreshToken;

    storeTokens({ accessToken, refreshToken });

    const authUser: AuthUser = data.user;
    setUser(authUser);
    localStorage.setItem('dsfmp_user', JSON.stringify(authUser));
    return authUser;
  }, []);

  // ── Logout ──
  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Even if server-side logout fails, clear locally
    }
    setUser(null);
    clearTokens();
    localStorage.removeItem('dsfmp_user');
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        verify2FA,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ───────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
