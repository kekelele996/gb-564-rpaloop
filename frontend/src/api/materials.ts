import { http } from './client';
import type { Material } from '../types';

export interface CreditCheck {
  material_id: number;
  company_name: string;
  credit_code: string;
  valid: boolean;
  reason: string;
  can_declare: boolean;
  missing_flags: string[];
}

export const materialApi = {
  list: (onlyInvalid = false) =>
    http.get<{ total: number; invalid: number; items: Material[] }>(
      `/materials${onlyInvalid ? '?only_invalid=true' : ''}`),
  creditCheck: (id: number) => http.get<CreditCheck>(`/materials/${id}/credit-check`),
};
