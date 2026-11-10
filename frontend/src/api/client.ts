const BASE = '/api';
const TOKEN_KEY = 'rpaloop_token';

export class ApiError extends Error {
  status: number;
  code: string;
  detail?: string | null;

  constructor(status: number, code: string, message: string, detail?: string | null) {
    super(message);
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || '';
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem('rpaloop_user');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  if (options.body) headers['Content-Type'] = 'application/json';
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { ...options, headers });
  } catch (error) {
    throw new ApiError(0, 'NETWORK_ERROR', '后端不可达，请检查服务状态', String(error));
  }
  if (response.status === 401) {
    clearToken();
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login';
    }
    throw new ApiError(401, 'UNAUTHORIZED', '登录已过期，请重新登录');
  }
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const body = typeof payload === 'object' && payload ? payload : {};
    throw new ApiError(response.status, body.code || `HTTP_${response.status}`,
      body.message || '请求失败', body.detail ?? null);
  }
  return payload as T;
}

export const http = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
};

export async function downloadReport(runId: number, format: 'csv' | 'markdown'): Promise<void> {
  const token = getToken();
  const response = await fetch(`${BASE}/runs/${runId}/report?format=${format}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    let message = '报告导出失败';
    try {
      const body = await response.json();
      message = body.message || message;
    } catch {
      /* ignore */
    }
    throw new ApiError(response.status, 'REPORT_FAILED', message);
  }
  const blob = await response.blob();
  const disposition = response.headers.get('content-disposition') || '';
  const matched = disposition.match(/filename="?([^"]+)"?/);
  const filename = matched ? matched[1] : `report-${runId}.${format === 'csv' ? 'csv' : 'md'}`;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
