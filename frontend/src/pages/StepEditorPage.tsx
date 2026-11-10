import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { materialApi } from '../api/materials';
import { processApi } from '../api/processes';
import EmptyState from '../components/common/EmptyState';
import Panel from '../components/common/Panel';
import RiskBadge from '../components/common/RiskBadge';
import RunLaunchDialog from '../components/common/RunLaunchDialog';
import LocatorCandidateList from '../components/business/LocatorCandidateList';
import ProcessRail from '../components/business/ProcessRail';
import { MATTER_TYPE_LABELS, PROCESS_STATUS_LABELS, STEP_ACTION_LABELS } from '../constants/enums';
import { useAsync } from '../hooks/useAsync';
import { useAuthStore } from '../stores/auth';
import type { LocatorCandidate, Material, Step } from '../types';

interface DraftState {
  action: string;
  target_desc: string;
  locator_candidates: LocatorCandidate[];
  timeout_ms: number;
  max_retries: number;
  assert_rule: string;
  depends_on: number[];
}

function toDraft(step: Step): DraftState {
  return {
    action: step.action,
    target_desc: step.target_desc,
    locator_candidates: (step.locator_candidates || []).map((item) => ({ ...item })),
    timeout_ms: step.timeout_ms,
    max_retries: step.max_retries,
    assert_rule: step.assert_rule || '',
    depends_on: step.depends_on || [],
  };
}

export default function StepEditorPage() {
  const { processId } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const canEdit = user?.role === 'admin' || user?.role === 'engineer';
  const { data, loading, error, reload } = useAsync(
    () => processApi.detail(Number(processId)), [processId]);
  const materialsState = useAsync(() => materialApi.list(), []);
  const [selectedSeq, setSelectedSeq] = useState<number>(1);
  const [draft, setDraft] = useState<DraftState | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [launchOpen, setLaunchOpen] = useState(false);

  const steps = data?.steps ?? [];
  const selectedStep = useMemo(
    () => steps.find((step) => step.seq === selectedSeq) || steps[0],
    [steps, selectedSeq],
  );

  useEffect(() => {
    if (selectedStep) {
      setSelectedSeq(selectedStep.seq);
      setDraft(toDraft(selectedStep));
    }
  }, [selectedStep?.id, selectedStep?.seq, data?.id]);

  const recommended = useMemo(() => {
    if (!selectedStep) return '';
    const scores = selectedStep.locator_scores || [];
    if (!scores.length) return '';
    return [...scores].sort((a, b) => b.score - a.score)[0].selector;
  }, [selectedStep]);

  const setField = <K extends keyof DraftState>(key: K, value: DraftState[K]) => {
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const save = async () => {
    if (!draft || !selectedStep) return;
    setBusy(true);
    setMessage('');
    try {
      await processApi.updateStep(Number(processId), selectedStep.id, {
        ...draft,
        assert_rule: draft.assert_rule || '',
      });
      setMessage(`步骤 ${selectedStep.seq} 已保存，定位器稳健分已按新候选重算`);
      reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '保存失败');
    } finally {
      setBusy(false);
    }
  };

  const rescore = async () => {
    setBusy(true);
    setMessage('');
    try {
      const result = await processApi.rescore(Number(processId));
      const high = result.high_risk_steps || [];
      setMessage(high.length
        ? `评分完成：高风险步骤 ${high.join(', ')}（建议改为主文本定位器）`
        : '评分完成：当前没有高风险步骤');
      reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '重新评分失败');
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    setBusy(true);
    try {
      const result = await processApi.publish(Number(processId), '编辑器发布');
      setMessage(`已发布 v${result.process.version}；归档版本 ${result.process.archived_versions.join(',') || '无'}`);
      reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '发布失败');
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="page"><div className="panel-body muted">加载流程…</div></div>;
  if (error || !data) {
    return (
      <div className="page">
        <div className="banner">{error || '流程不存在'}</div>
        <button className="btn" type="button" style={{ marginTop: 14 }} onClick={() => navigate('/processes')}>
          返回流程库
        </button>
      </div>
    );
  }

  const materials: Material[] = materialsState.data?.items ?? [];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="crumb">
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigate('/processes')}
              style={{ marginRight: 8 }}>← 流程库</button>
            {MATTER_TYPE_LABELS[data.matter_type]} / 步骤编辑器
          </div>
          <h1 className="page-title">{data.name}</h1>
          <p className="page-sub mono">
            v{data.version} · {PROCESS_STATUS_LABELS[data.status]} · {data.step_count} 步 ·
            {data.owner} · 归档版本 {data.archived_versions.join(',') || '无'}
          </p>
        </div>
        <div className="head-meta">
          {data.risk_summary ? (
            <>
              <span className="chip danger">高风险 {data.risk_summary.high}</span>
              <span className="chip warn">中风险 {data.risk_summary.medium}</span>
              <span className="chip ok">低风险 {data.risk_summary.low}</span>
            </>
          ) : null}
          <button className="btn btn-sm" type="button" onClick={rescore} disabled={!canEdit || busy}>
            重新评分
          </button>
          {canEdit ? (
            <button className="btn btn-primary btn-sm" type="button" onClick={() => setLaunchOpen(true)}>
              干跑校验
            </button>
          ) : null}
          {user?.role === 'admin' ? (
            <button className="btn btn-sm" type="button" onClick={publish} disabled={busy}>
              发布新版本
            </button>
          ) : null}
        </div>
      </header>

      {message ? <div className="banner warn" style={{ marginBottom: 14 }}>{message}</div> : null}

      <div className="studio">
        <ProcessRail steps={steps} selectedSeq={selectedSeq}
          onSelect={(seq) => setSelectedSeq(seq)} title="STEPS · 灯列"
          foot={canEdit ? '点击步骤编辑定位器与断言' : '审计只读：不可编辑'} />

        <div className="stack">
          {!selectedStep || !draft ? (
            <Panel><EmptyState title="流程没有步骤" hint="通过录制 JSON 导入步骤后再配置。" /></Panel>
          ) : (
            <>
              <Panel kicker={`STEP ${String(selectedStep.seq).padStart(2, '0')} · ${STEP_ACTION_LABELS[selectedStep.action]}`}
                title={selectedStep.target_desc}
                actions={<>
                  <RiskBadge level={selectedStep.risk_level} score={selectedStep.robustness_score} />
                  <span className="chip mono">timeout {draft.timeout_ms}ms</span>
                  <span className="chip mono">retries {draft.max_retries}</span>
                </>}>
                <div className="stack">
                  {selectedStep.risk_reason ? (
                    <div className={`banner ${selectedStep.risk_level === 'high' ? '' : 'warn'}`}>
                      算法 A 结论：{selectedStep.risk_reason}
                    </div>
                  ) : null}
                  <div className="flex gap-12" style={{ flexWrap: 'wrap' }}>
                    <label className="field" style={{ flex: 1, minWidth: 180 }}>
                      <span className="field-label">动作</span>
                      <select className="select" value={draft.action} disabled={!canEdit}
                        onChange={(event) => setField('action', event.target.value)}>
                        {Object.entries(STEP_ACTION_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}（{value}）</option>
                        ))}
                      </select>
                    </label>
                    <label className="field" style={{ flex: 2.4, minWidth: 260 }}>
                      <span className="field-label">目标描述</span>
                      <input className="input" value={draft.target_desc} disabled={!canEdit}
                        onChange={(event) => setField('target_desc', event.target.value)} />
                    </label>
                  </div>
                  <div className="flex gap-12" style={{ flexWrap: 'wrap' }}>
                    <label className="field" style={{ flex: 1, minWidth: 150 }}>
                      <span className="field-label">超时（ms）</span>
                      <input className="input mono" type="number" value={draft.timeout_ms} disabled={!canEdit}
                        onChange={(event) => setField('timeout_ms', Number(event.target.value))} />
                    </label>
                    <label className="field" style={{ flex: 1, minWidth: 150 }}>
                      <span className="field-label">最大重试</span>
                      <input className="input mono" type="number" value={draft.max_retries} disabled={!canEdit}
                        onChange={(event) => setField('max_retries', Number(event.target.value))} />
                    </label>
                    <label className="field" style={{ flex: 2.2, minWidth: 240 }}>
                      <span className="field-label">断言规则（assert_rule）</span>
                      <input className="input mono" value={draft.assert_rule} disabled={!canEdit}
                        placeholder="如 attachment:审计报告 exists / credit_code_valid"
                        onChange={(event) => setField('assert_rule', event.target.value)} />
                    </label>
                  </div>
                  <div className="flex gap-8" style={{ justifyContent: 'flex-end' }}>
                    <button className="btn btn-ghost btn-sm" type="button"
                      onClick={() => setDraft(toDraft(selectedStep))} disabled={!canEdit}>还原本步</button>
                    <button className="btn btn-primary btn-sm" type="button" onClick={save}
                      disabled={!canEdit || busy}>
                      {busy ? '保存中…' : '保存并重算评分'}
                    </button>
                  </div>
                  {!canEdit ? <div className="tiny faint">审计只读角色：字段仅展示，不可修改。</div> : null}
                </div>
              </Panel>

              <Panel kicker="ALGORITHM A · LOCATOR ROBUSTNESS"
                title="定位器候选与稳健分"
                actions={<span className="tiny faint">score = 100·(0.45·hit + 0.20·attempt + 0.20·(1-risk) + 0.15·specificity)</span>}>
                <LocatorCandidateList
                  candidates={draft.locator_candidates}
                  scores={selectedStep.locator_scores}
                  recommended={recommended}
                  editable={canEdit}
                  onChange={(next) => setField('locator_candidates', next)}
                  onPromote={(index) => {
                    const next = [...draft.locator_candidates];
                    const [item] = next.splice(index, 1);
                    setField('locator_candidates', [item, ...next]);
                  }}
                />
                {selectedStep.locator_scores?.length ? (
                  <div className="metric-row" style={{ marginTop: 12 }}>
                    算法推荐主定位器：
                    <span className="mono" style={{ color: 'var(--green)' }}>
                      {[...(selectedStep.locator_scores || [])].sort((a, b) => b.score - a.score)[0].selector}
                    </span>
                  </div>
                ) : null}
              </Panel>
            </>
          )}
        </div>
      </div>

      {launchOpen ? (
        <RunLaunchDialog process={data} materials={materials} onClose={() => setLaunchOpen(false)} />
      ) : null}
    </div>
  );
}
