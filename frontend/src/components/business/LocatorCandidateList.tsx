import type { LocatorCandidate, LocatorScore } from '../../types';
import { scoreTone } from '../../utils/risk';

interface Props {
  candidates: LocatorCandidate[];
  scores?: LocatorScore[];
  recommended?: string;
  editable?: boolean;
  onChange?: (candidates: LocatorCandidate[]) => void;
  onPromote?: (index: number) => void;
}

const STRATEGY_LABELS: Record<string, string> = {
  id: 'ID',
  css: 'CSS',
  text: '文本',
  xpath: 'XPath',
  role: '无障碍',
};

export default function LocatorCandidateList({
  candidates, scores, recommended, editable, onChange, onPromote,
}: Props) {
  const scoreMap = new Map((scores || []).map((item) => [item.selector, item]));

  const update = (index: number, patch: Partial<LocatorCandidate>) => {
    if (!onChange) return;
    const next = candidates.map((item, idx) => (idx === index ? { ...item, ...patch } : item));
    onChange(next);
  };

  const remove = (index: number) => {
    if (!onChange) return;
    onChange(candidates.filter((_, idx) => idx !== index));
  };

  const add = () => {
    if (!onChange) return;
    onChange([...candidates, { strategy: 'text', selector: '', desc: '新增备选定位器' }]);
  };

  if (!candidates.length) {
    return <div className="empty-hint">该步骤暂无定位器候选</div>;
  }

  return (
    <div className="locator-list">
      {candidates.map((candidate, index) => {
        const score = scoreMap.get(candidate.selector);
        const tone = score ? scoreTone(score.score) : 'warn';
        const isPrimary = index === 0;
        const risky = (score?.dynamic_risk || 0) >= 0.8;
        return (
          <div key={`${candidate.selector}-${index}`}
            className={`locator-item ${isPrimary ? 'primary' : ''} ${risky ? 'risky' : ''}`}>
            <div className="locator-head">
              <span className={`chip ${isPrimary ? 'warn' : ''}`}>{isPrimary ? '主定位器' : `备选 ${index}`}</span>
              <span className="chip">{STRATEGY_LABELS[candidate.strategy] || candidate.strategy}</span>
              {recommended === candidate.selector ? <span className="chip ok">算法推荐</span> : null}
              {risky ? <span className="chip danger">动态风险</span> : null}
              {score ? (
                <span className={`locator-score`} style={{ color: `var(--${tone === 'danger' ? 'red' : tone === 'warn' ? 'amber' : 'green'})` }}>
                  {Math.round(score.score)}
                </span>
              ) : null}
            </div>
            {editable ? (
              <div className="stack" style={{ marginTop: 8, gap: 8 }}>
                <input className="input mono" value={candidate.selector}
                  placeholder="选择器（css / xpath / 文本）"
                  onChange={(event) => update(index, { selector: event.target.value })} />
                <div className="flex gap-8">
                  <select className="select" style={{ width: 130 }} value={candidate.strategy}
                    onChange={(event) => update(index, { strategy: event.target.value })}>
                    <option value="css">CSS</option>
                    <option value="xpath">XPath</option>
                    <option value="text">文本</option>
                    <option value="id">ID</option>
                    <option value="role">无障碍</option>
                  </select>
                  <input className="input" value={candidate.desc} placeholder="说明"
                    onChange={(event) => update(index, { desc: event.target.value })} />
                  <button className="btn btn-ghost btn-sm" type="button" onClick={() => onPromote?.(index)}
                    disabled={isPrimary}>设为主</button>
                  <button className="btn btn-danger btn-sm" type="button" onClick={() => remove(index)}
                    disabled={candidates.length <= 1}>删除</button>
                </div>
              </div>
            ) : (
              <div className="locator-selector" style={{ marginTop: 6 }}>{candidate.selector}</div>
            )}
            <div className="locator-desc" style={{ marginTop: 4 }}>{candidate.desc}</div>
            {score ? (
              <>
                <div className="bar">
                  <div className="bar-fill" style={{
                    width: `${Math.max(2, Math.min(100, score.score))}%`,
                    background: tone === 'danger' ? 'var(--red)' : tone === 'warn' ? 'var(--amber)' : 'var(--green)',
                  }} />
                </div>
                <div className="metric-row">
                  <span>命中率 <b>{(score.hit_rate * 100).toFixed(0)}%</b></span>
                  <span>平均尝试 <b>{score.avg_attempts.toFixed(2)}</b></span>
                  <span>特异度 <b>{score.specificity.toFixed(2)}</b></span>
                  <span>动态风险 <b>{score.dynamic_risk.toFixed(1)}</b></span>
                  <span>样本 <b>{score.samples}</b></span>
                  {score.dynamic_flags.length ? <span style={{ color: 'var(--red)' }}>动态片段 {score.dynamic_flags.join('/')}</span> : null}
                </div>
              </>
            ) : (
              <div className="metric-row"><span>暂无历史命中记录（score=50, reason=no_history）</span></div>
            )}
          </div>
        );
      })}
      {editable ? (
        <button className="btn btn-ghost btn-sm" type="button" onClick={add}
          disabled={candidates.length >= 6}>+ 新增备选定位器（上限 6）</button>
      ) : null}
    </div>
  );
}
