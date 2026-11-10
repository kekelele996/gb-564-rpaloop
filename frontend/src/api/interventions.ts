import { http } from './client';
import type { InterventionItem, RunItem } from '../types';

export const interventionApi = {
  list: (params: { status?: string; reason?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.reason) query.set('reason', params.reason);
    return http.get<{ total: number; items: InterventionItem[] }>(`/interventions?${query.toString()}`);
  },
  resolve: (id: number, action: string, resolution = '') =>
    http.post<{ intervention: InterventionItem; run: RunItem; resumed: boolean }>(
      `/interventions/${id}/resolve`, { action, resolution }),
};
