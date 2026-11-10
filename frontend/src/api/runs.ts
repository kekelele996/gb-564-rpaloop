import { http } from './client';
import type { RunItem } from '../types';

export const runApi = {
  list: (params: { status?: string; process_id?: number; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.process_id) query.set('process_id', String(params.process_id));
    query.set('limit', String(params.limit ?? 50));
    return http.get<{ total: number; items: RunItem[] }>(`/runs?${query.toString()}`);
  },
  detail: (id: number) => http.get<RunItem>(`/runs/${id}`),
  create: (processId: number, materialId: number, trigger = 'manual') =>
    http.post<RunItem>('/runs', { process_id: processId, material_id: materialId, trigger }),
  cancel: (id: number, note = '') => http.post<RunItem>(`/runs/${id}/cancel`, { note }),
};
