import { formatDuration } from '../../utils/format';
import { runStepTone } from '../../utils/risk';
import StatusLamp from '../common/StatusLamp';

export interface TimelineStep {
  seq: number;
  status?: string;
  target_desc: string;
  action: string;
  attempt?: number;
  duration_ms?: number;
  locator_used?: string;
  locator_strategy?: string;
  error_code?: string | null;
  error_message?: string;
  note?: string;
}

interface StepTimelineProps {
  steps: TimelineStep[];
  onSelect?: (step: TimelineStep) => void;
  selectedSeq?: number;
}

const STATUS_LABELS: Record<string, string> = {
  ok: '通过',
  retried: '重试通过',
  failed: '失败',
  skipped: '跳过',
  running: '执行中',
};

export default function StepTimeline({ steps, onSelect, selectedSeq }: StepTimelineProps) {
  if (!steps.length) {
    return <div className="empty-hint">暂无步骤记录</div>;
  }
  return (
    <div className="timeline">
      {steps.map((step) => {
        const tone = runStepTone(step.status || 'idle');
        return (
          <div
            key={step.seq}
            className="tl-item"
            style={{ cursor: onSelect ? 'pointer' : 'default' }}
            onClick={() => onSelect?.(step)}
          >
            <div className="tl-seq">{String(step.seq).padStart(2, '0')}</div>
            <div className="tl-track">
              <StatusLamp tone={tone} />
              <div className="tl-line" />
            </div>
            <div className="tl-body" style={selectedSeq === step.seq ? { background: 'oklch(0.812 0.148 78 / 0.06)' } : undefined}>
              <div className="tl-head">
                <span className="tl-title">{step.target_desc}</span>
                <span className="chip">{step.action}</span>
                {step.status ? <span className={`chip ${tone}`}>{STATUS_LABELS[step.status] || step.status}</span> : null}
                {step.attempt && step.attempt > 1 ? <span className="chip warn">attempt {step.attempt}</span> : null}
                {step.duration_ms !== undefined ? (
                  <span className="tiny faint mono">{formatDuration(step.duration_ms)}</span>
                ) : null}
              </div>
              {step.locator_used ? (
                <div className="tl-locator">
                  命中定位器 [{step.locator_strategy}] {step.locator_used}
                </div>
              ) : null}
              {step.error_code ? (
                <div className="tl-error">
                  {step.error_code} · {step.error_message}
                </div>
              ) : null}
              {step.note ? <div className="tiny muted">{step.note}</div> : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
