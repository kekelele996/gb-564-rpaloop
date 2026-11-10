import type { Step } from '../../types';
import { riskTone } from '../../utils/risk';

interface ProcessRailProps {
  steps: Step[];
  selectedSeq?: number;
  onSelect?: (seq: number) => void;
  title?: string;
  foot?: string;
}

export default function ProcessRail({ steps, selectedSeq, onSelect, title, foot }: ProcessRailProps) {
  return (
    <aside className="rail">
      <div className="rail-strip">
        <div className="rail-perf">
          <span /><span /><span /><span /><span /><span /><span /><span />
        </div>
        <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--line-soft)' }}>
          <div className="panel-kicker">{title || 'PROCESS RAIL'}</div>
          <div className="tiny muted" style={{ marginTop: 4 }}>{steps.length} 步 · 定位器灯列</div>
        </div>
        {steps.map((step) => (
          <div
            key={step.id}
            className={`rail-step ${selectedSeq === step.seq ? 'selected' : ''}`}
            onClick={() => onSelect?.(step.seq)}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => { if (event.key === 'Enter') onSelect?.(step.seq); }}
          >
            <span className={`lamp ${riskTone(step.risk_level)}`} />
            <span>
              <span className="rail-seq">{String(step.seq).padStart(2, '0')} · {step.action}</span>
              <span className="rail-text" style={{ display: 'block' }}>{step.target_desc}</span>
            </span>
          </div>
        ))}
        <div className="rail-foot">{foot || '琥珀=中风险 · 红=高风险'}</div>
      </div>
    </aside>
  );
}
