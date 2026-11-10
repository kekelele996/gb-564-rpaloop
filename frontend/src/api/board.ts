import { http } from './client';
import type { BoardSnapshot } from '../types';

export const boardApi = {
  get: () => http.get<BoardSnapshot>('/board'),
};
