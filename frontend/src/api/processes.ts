import { http } from './client';
import type { LocatorCandidate, ProcessItem } from '../types';

export const processApi = {
  list: () => http.get<{ total: number; items: ProcessItem[] }>('/processes'),
  detail: (id: number) => http.get<ProcessItem>(`/processes/${id}`),
  updateStep: (processId: number, stepId: number, payload: Record<string, unknown>) =>
    http.put<{ step: unknown; score: unknown }>(`/processes/${processId}/steps/${stepId}`, payload),
  rescore: (processId: number) =>
    http.post<{ process_id: number; high_risk_steps: number[] }>(`/processes/${processId}/rescore`),
  publish: (processId: number, note = '') =>
    http.post<{ process: ProcessItem; note: string }>(`/processes/${processId}/publish`, { note }),
  archive: (processId: number, note = '') =>
    http.post<{ process: ProcessItem; note: string }>(`/processes/${processId}/archive`, { note }),
  dryRun: (processId: number, materialId: number) =>
    http.post<{ id: number; run_code: string }>(`/processes/${processId}/dry-run`, {
      process_id: processId,
      material_id: materialId,
      trigger: 'dry_run',
    }),
};

export interface StepUpdatePayload {
  action?: string;
  target_desc?: string;
  locator_candidates?: LocatorCandidate[];
  timeout_ms?: number;
  max_retries?: number;
  assert_rule?: string;
  depends_on?: number[];
}
