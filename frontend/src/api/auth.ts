import { http } from './client';
import type { User } from '../types';

export interface LoginResult {
  access_token: string;
  token_type: string;
  user: User;
}

export const authApi = {
  login: (email: string, password: string) =>
    http.post<LoginResult>('/auth/login', { email, password }),
  me: () => http.get<{ user: User }>('/auth/me'),
};
