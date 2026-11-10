import type { ProcessItem, Step } from '../types';

export function riskTone(level: string): 'ok' | 'warn' | 'danger' | 'idle' {
  if (level === 'low') return 'ok';
  if (level === 'medium') return 'warn';
  if (level === 'high') return 'danger';
  return 'idle';
}

export function scoreTone(score: number): 'ok' | 'warn' | 'danger' {
  if (score >= 70) return 'ok';
  if (score >= 55) return 'warn';
  return 'danger';
}

export function countHighRisk(process: ProcessItem): number {
  if (process.risk_summary) return process.risk_summary.high;
  return (process.steps || []).filter((step) => step.risk_level === 'high').length;
}

export function dominantRisk(steps: Step[]): 'low' | 'medium' | 'high' {
  if (steps.some((step) => step.risk_level === 'high')) return 'high';
  if (steps.some((step) => step.risk_level === 'medium')) return 'medium';
  return 'low';
}

export function runStepTone(status: string): 'ok' | 'warn' | 'danger' | 'idle' | 'active' {
  switch (status) {
    case 'ok':
      return 'ok';
    case 'retried':
      return 'warn';
    case 'failed':
      return 'danger';
    case 'skipped':
      return 'idle';
    case 'running':
      return 'active';
    default:
      return 'idle';
  }
}

export function runStatusTone(status: string): 'ok' | 'warn' | 'danger' | 'idle' | 'active' {
  switch (status) {
    case 'succeeded':
      return 'ok';
    case 'failed':
      return 'danger';
    case 'takeover':
      return 'warn';
    case 'running':
      return 'active';
    case 'queued':
      return 'warn';
    default:
      return 'idle';
  }
}
