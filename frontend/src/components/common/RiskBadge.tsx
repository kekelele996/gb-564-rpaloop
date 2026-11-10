import { RISK_LEVEL_LABELS } from '../../constants/enums';
import type { RiskLevel } from '../../types';
import { riskTone } from '../../utils/risk';

export default function RiskBadge({ level, score }: { level: RiskLevel; score?: number }) {
  return (
    <span className={`chip ${riskTone(level)}`}>
      {RISK_LEVEL_LABELS[level]}
      {score !== undefined ? <b className="mono" style={{ fontWeight: 700 }}>{Math.round(score)}</b> : null}
    </span>
  );
}
