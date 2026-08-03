import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import api, { getTokens, setTokens } from '../lib/api';

const AuthContext = createContext(null);

const USER_KEY = 'nominate_user';

function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY)) || null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser);
  const [loading, setLoading] = useState(Boolean(getTokens()));

  const storeSession = useCallback((data) => {
    setTokens({ access_token: data.access_token, refresh_token: data.refresh_token });
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    setTokens(null);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  useEffect(() => {
    window.addEventListener('nominate:logout', logout);
    return () => window.removeEventListener('nominate:logout', logout);
  }, [logout]);

  // Revalidate the stored session on load (also refreshes has_profile).
  useEffect(() => {
    if (!getTokens()) {
      setLoading(false);
      return;
    }
    api
      .get('/auth/me')
      .then(({ data }) => {
        localStorage.setItem(USER_KEY, JSON.stringify(data.user));
        setUser(data.user);
      })
      .catch((err) => {
        // The stored token references a user that no longer exists (e.g. the
        // database was reset) — clear the dead session instead of trusting it.
        if ([401, 404].includes(err.response?.status)) logout();
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(
    async (email, password) => {
      const { data } = await api.post('/auth/login', { email, password });
      return storeSession(data);
    },
    [storeSession],
  );

  const signup = useCallback(
    async (username, email, password) => {
      const { data } = await api.post('/auth/signup', { username, email, password });
      return storeSession(data);
    },
    [storeSession],
  );

  const googleSignIn = useCallback(
    async (credential) => {
      const { data } = await api.post('/auth/google', { credential });
      return storeSession(data);
    },
    [storeSession],
  );

  const markProfileComplete = useCallback(() => {
    setUser((current) => {
      if (!current) return current;
      const updated = { ...current, has_profile: true };
      localStorage.setItem(USER_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  const patchUser = useCallback((fields) => {
    setUser((current) => {
      if (!current) return current;
      const updated = { ...current, ...fields };
      localStorage.setItem(USER_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, signup, googleSignIn, logout, markProfileComplete, patchUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
