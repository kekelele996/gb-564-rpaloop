import { create } from 'zustand';
import { authApi } from '../api/auth';
import { clearToken, getToken, setToken } from '../api/client';
import type { Role, User } from '../types';

interface AuthState {
  token: string;
  user: User | null;
  loading: boolean;
  error: string;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
  hydrate: () => Promise<void>;
  can: (...roles: Role[]) => boolean;
}

function readUser(): User | null {
  try {
    const raw = localStorage.getItem('rpaloop_user');
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: getToken(),
  user: readUser(),
  loading: false,
  error: '',
  async login(email, password) {
    set({ loading: true, error: '' });
    try {
      const result = await authApi.login(email, password);
      setToken(result.access_token);
      localStorage.setItem('rpaloop_user', JSON.stringify(result.user));
      set({ token: result.access_token, user: result.user, loading: false });
      return result.user;
    } catch (error) {
      const message = error instanceof Error ? error.message : '登录失败';
      set({ loading: false, error: message });
      throw error;
    }
  },
  logout() {
    clearToken();
    set({ token: '', user: null });
  },
  async hydrate() {
    if (!get().token) return;
    try {
      const result = await authApi.me();
      localStorage.setItem('rpaloop_user', JSON.stringify(result.user));
      set({ user: result.user });
    } catch {
      get().logout();
    }
  },
  can(...roles) {
    const role = get().user?.role;
    return Boolean(role && roles.includes(role));
  },
}));
