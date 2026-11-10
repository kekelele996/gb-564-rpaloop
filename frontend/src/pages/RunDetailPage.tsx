import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { downloadReport } from '../api/client';
import { interventionApi } from '../api/interventions';
import { processApi } from '../api/processes';
import { runApi } from '../api/runs';
import EmptyState from '../components/common/EmptyState';
import Panel from '../components/common/Panel';
import StatusLamp from '../components/common/StatusLamp';
import StepTimeline from '../components/business/StepTimeline';
import LocatorCandidateList from '../components/business/LocatorCandidateList';
import {
  INTERVENTION_ACTIONS, INTERVENTION_REASON_LABELS, INTERVENTION_STATUS_LABELS,
  POLL_INTERVALS, RUN_STATUS_LABELS, RUN_STEP_STATUS_LABELS, RUN_TRIGGER_LABELS,
} from '../constants/enums';
import { usePolling } from '../hooks/usePolling';
import { useAuthStore } from '../stores/auth';
import type { ProcessItem, RunItem } from '../types';
import { formatDateTime, formatDuration, shortDigest } from '../utils/format';
import { runStatusTone } from '../utils/risk';

export default function RunDetailPage() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const canResolve = user?.role === 'admin' || user?.role === 'engineer';
  const [run, setRun] = useState<RunItem | null>(null);
  const [process, setProcess] = useState<ProcessItem | null>(null);
  const [selectedSeq, setSelectedSeq] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const detail = await runApi.detail(Number(runId));
      setRun(detail);
      setError('');
      if (!process || process.id !== detail.process_id) {
        try {
          setProcess(await processApi.detail(detail.process_id));
        } catch { /* 流程详情失败不影响运行详情 */ }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '运行详情加载失败');
    }
  }, [runId, process]);

  useEffect(() => { void load(); }, [runId]); // eslint-disable-line react-hooks/exhaustive-deps
  const active = run ? ['queued', 'running', 'takeover'].includes(run.status) : false;
  usePolling(() => { void load(); }, POLL_INTERVALS.run, active);

  const selectedRunStep = useMemo(
    () => run?.run_steps?.find((item) => item.seq === selectedSeq) || run?.run_steps?.find((item) => item.status === 'failed'),
    [run, selectedSeq],
  );
  const selectedStep = useMemo(
    () => process?.steps?.find((step) => step.id === selectedRunStep?.step_id),
    [process, selectedRunStep],
  );

  const resolve = async (interventionId: number, action: string) => {
    setBusy(true);
    setMessage('');
    try {
      const result = await interventionApi.resolve(interventionId, action, '');
      setMessage(result.resumed ? `已${action === 'retry' ? '重试' : '处理'}并续跑：${result.run.run_code}` : '已终止运行');
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '接管处理失败');
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    setBusy(true);
    try {
      await runApi.cancel(Number(runId), '值守台手动取消');
      setMessage('运行已取消');
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '取消失败');
    } finally {
      setBusy(false);
    }
  };

  const exportReport = async (format: 'csv' | 'markdown') => {
    try {
      await downloadReport(Number(runId), format);
      setMessage(`已导出 ${format === 'csv' ? 'CSV' : 'Markdown'} 执行报告`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '导出失败');
    }
  };

  if (!run) {
    return <div className="page">{error ? <div className="banner">{error}</div> : <div className="muted">加载运行详情…</div>}</div>;
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="crumb">
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigate('/board')}
              style={{ marginRight: 8 }}>← 值守看板</button>
            RUN DETAIL
          </div>
          <h1 className="page-title mono">{run.run_code}</h1>
          <p className="page-sub">
            {run.process_name} v{run.process_version} · {run.company_name} · {run.credit_code} ·
            触发 {RUN_TRIGGER_LABELS[run.trigger]} · {run.robot_name}
          </p>
        </div>
        <div className="head-meta">
          <span className={`chip ${runStatusTone(run.status)}`}>
            <StatusLamp tone={runStatusTone(run.status) as 'ok' | 'warn' | 'danger' | 'active' | 'idle'} />
            {RUN_STATUS_LABELS[run.status]}
          </span>
          <button className="btn btn-sm" type="button" onClick={() => exportReport('markdown')}>导出 Markdown</button>
          <button className="btn btn-sm" type="button" onClick={() => exportReport('csv')}>导出 CSV</button>
          {canResolve && active ? (
            <button className="btn btn-danger btn-sm" type="button" onClick={cancel} disabled={busy}>取消运行</button>
          ) : null}
        </div>
      </header>

      {message ? <div className="banner warn" style={{ marginBottom: 14 }}>{message}</div> : null}

      <div className="stat-row" style={{ marginBottom: 18 }}>
        <div className="stat-cell">
          <div className="stat-value green">{run.success_steps}</div>
          <div className="stat-label">成功步骤 / {run.total_steps}</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value amber">{run.retry_count}</div>
          <div className="stat-label">重试次数</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value">{run.attempt_count}</div>
          <div className="stat-label">执行轮次（含续跑）</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value">{run.skipped_steps.length}</div>
          <div className="stat-label">断点续跑跳过</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value mono" style={{ fontSize: 16, paddingTop: 8 }}>{formatDateTime(run.started_at)}</div>
          <div className="stat-label">开始时间</div>
        </div>
      </div>

      <div className="board-grid">
        <div className="stack">
          <Panel kicker="STEP TIMELINE · DAG" title="步骤执行时间线"
            actions={<span className="tiny faint mono">拓扑序列 {run.execution_sequence.join('→')}</span>}>
            <StepTimeline
              steps={(run.run_steps || []).map((item) => ({
                seq: item.seq, status: item.status, target_desc: item.target_desc, action: item.action,
                attempt: item.attempt, duration_ms: item.duration_ms, locator_used: item.locator_used,
                locator_strategy: item.locator_strategy, error_code: item.error_code,
                error_message: item.error_message, note: item.note,
              }))}
              selectedSeq={selectedRunStep?.seq}
              onSelect={(step) => setSelectedSeq(step.seq)}
            />
            {run.run_steps?.length === 0 ? (
              <EmptyState title="尚无步骤记录" hint="运行刚入队，等待 Celery worker 消费。" />
            ) : null}
          </Panel>

          <Panel kicker="EXECUTION LOG" title="执行日志" actions={
            <button className="btn btn-ghost btn-sm" type="button" onClick={() => load()}>刷新</button>
          }>
            <pre className="console">{run.log_text || '(worker 尚未写入日志)'}</pre>
          </Panel>
        </div>

        <div className="stack">
          <Panel kicker="LOCATOR HIT" title={selectedRunStep ? `步骤 ${selectedRunStep.seq} · 定位器命中` : '定位器命中'}>
            {selectedRunStep && selectedStep ? (
              <div className="stack">
                <div className="spread">
                  <span className="tiny muted">命中定位器</span>
                  <span className="mono tiny" style={{ color: 'var(--amber)', overflowWrap: 'anywhere', textAlign: 'right' }}>
                    [{selectedRunStep.locator_strategy}] {selectedRunStep.locator_used}
                  </span>
                </div>
                <div className="spread">
                  <span className="tiny muted">幂等键（sha256 前 16 位）</span>
                  <span className="mono tiny">{shortDigest(selectedRunStep.idempotency_key, 16)}</span>
                </div>
                <div className="spread">
                  <span className="tiny muted">输出摘要</span>
                  <span className="mono tiny">{shortDigest(selectedRunStep.output_digest, 16)}</span>
                </div>
                <div className="spread">
                  <span className="tiny muted">耗时 / 状态</span>
                  <span className="tiny">{formatDuration(selectedRunStep.duration_ms)} ·
                    <span className={`chip ${selectedRunStep.status === 'failed' ? 'danger' : selectedRunStep.status === 'retried' ? 'warn' : 'ok'}`}
                      style={{ marginLeft: 8 }}>{RUN_STEP_STATUS_LABELS[selectedRunStep.status]}</span>
                  </span>
                </div>
                {selectedRunStep.error_code ? (
                  <div className="banner">{selectedRunStep.error_code} · {selectedRunStep.error_message}</div>
                ) : null}
                <div className="panel-kicker" style={{ marginTop: 6 }}>该步骤全部定位器候选</div>
                <LocatorCandidateList candidates={selectedStep.locator_candidates}
                  scores={selectedStep.locator_scores}
                  recommended={[...(selectedStep.locator_scores || [])].sort((a, b) => b.score - a.score)[0]?.selector} />
              </div>
            ) : (
              <EmptyState title="选择左侧任一步骤" hint="查看该步骤命中的定位器、幂等键与稳健分。" />
            )}
          </Panel>

          <Panel kicker="INTERVENTIONS" title="接管记录" tight>
            {(run.interventions || []).length === 0 ? (
              <div className="panel-body"><EmptyState title="本次运行没有接管工单" hint="断言失败或定位漂移会生成工单。" /></div>
            ) : (run.interventions || []).map((item) => (
              <div key={item.id} className="queue-item" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 8 }}>
                <div className="flex align-center gap-8">
                  <StatusLamp tone={item.status === 'open' ? 'warn' : item.status === 'resolved' ? 'ok' : 'idle'} />
                  <span className="mono tiny">{item.code}</span>
                  <span className="chip warn">{INTERVENTION_REASON_LABELS[item.reason] || item.reason}</span>
                  <span className={`chip ${item.status === 'open' ? 'warn' : item.status === 'resolved' ? 'ok' : 'idle'}`}>
                    {INTERVENTION_STATUS_LABELS[item.status] || item.status}
                  </span>
                </div>
                <div className="tiny muted">{item.detail}</div>
                {item.resolution ? <div className="tiny">处置：{item.resolution} · {item.resolved_by}</div> : null}
                {item.status === 'open' && canResolve ? (
                  <div className="flex gap-8" style={{ flexWrap: 'wrap' }}>
                    {INTERVENTION_ACTIONS.filter((action) => action.value !== 'abort').map((action) => (
                      <button key={action.value} className="btn btn-sm"
                        type="button" disabled={busy}
                        onClick={() => resolve(item.id, action.value)}>
                        {action.label}
                      </button>
                    ))}
                    <button className="btn btn-danger btn-sm" type="button" disabled={busy}
                      onClick={() => resolve(item.id, 'abort')}>终止</button>
                  </div>
                ) : null}
                {item.status === 'open' && !canResolve ? (
                  <div className="tiny faint">审计只读角色：接管处置需要值守操作员权限（403）。</div>
                ) : null}
              </div>
            ))}
          </Panel>
        </div>
      </div>
    </div>
  );
}
