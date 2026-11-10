export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (num: number) => String(num).padStart(2, '0');
  return `${date.getMonth() + 1}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

/** 仅日期（YYYY-MM-DD）按本地日历显示，避免 date-only 被当 UTC 后显示 08:00:00。 */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const datePart = value.slice(0, 10);
  if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
    const [year, month, day] = datePart.split('-');
    return `${year}/${month}/${day}`;
  }
  return formatDateTime(value);
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function shortDigest(value: string | null | undefined, size = 10): string {
  if (!value) return '—';
  return value.slice(0, size);
}

export function maskCode(code: string | null | undefined): string {
  if (!code) return '—';
  if (code.length < 8) return code;
  return `${code.slice(0, 6)}····${code.slice(-4)}`;
}
