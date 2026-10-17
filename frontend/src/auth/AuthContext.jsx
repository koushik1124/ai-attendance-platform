import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../api/client';

const TOKEN_KEY = 'attendance_access_token';
const USER_KEY = 'attendance_user';
const AuthContext = createContext(null);

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(readUser);
  const [loading, setLoading] = useState(Boolean(token));

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const request = useCallback(async (path, options = {}) => {
    try {
      return await apiRequest(path, { ...options, token });
    } catch (error) {
      if (error.status === 401) logout();
      throw error;
    }
  }, [logout, token]);

  useEffect(() => {
    let active = true;
    if (!token) {
      setLoading(false);
      return () => { active = false; };
    }
    apiRequest('/api/v1/auth/me', { token })
      .then((profile) => {
        if (!active) return;
        setUser(profile);
        localStorage.setItem(USER_KEY, JSON.stringify(profile));
      })
      .catch(() => {
        if (active) logout();
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [logout, token]);

  const login = useCallback(async (email, password) => {
    const result = await apiRequest('/api/v1/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    localStorage.setItem(TOKEN_KEY, result.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(result.user));
    setToken(result.access_token);
    setUser(result.user);
    return result.user;
  }, []);

  const value = useMemo(() => ({
    token,
    user,
    loading,
    login,
    logout,
    request,
  }), [loading, login, logout, request, token, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
