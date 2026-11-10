import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { interventionApi } from '../api/interventions';
import EmptyState from '../components/common/EmptyState';
import Panel from '../components/common/Panel';
import StatusLamp from '../components/common/StatusLamp';
import {
  INTERVENTION_ACTIONS, INTERVENTION_REASON_LABELS, INTERVENTION_STATUS_LABELS, POLL_INTERVALS,
} from '../constants/enums';
import { usePolling } from '../hooks/usePolling';
import { useAuthStore } from '../stores/auth';
import type { InterventionItem } from '../types';
import { formatDateTime } from '../utils/format';

const STATUS_OPTIONS = [
  { value: '', label: '全部工单' },
  { value: 'open', label: '待接管' },
  { value: 'resolved', label: '已解决' },
  { value: 'skipped', label: '已跳过' },
  { value: 'aborted', label: '已终止' },
];

export default function InterventionPage() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const canResolve = user?.role === 'admin' || user?.role === 'engineer';
  const [status, setStatus] = useState('');
  const [items, setItems] = useState<InterventionItem[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [active, setActive] = useState<InterventionItem | null>(null);
  const [action, setAction] = useState('retry');
  const [resolution, setResolution] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await interventionApi.list(status ? { status } : {});
      setItems(data.items);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '接管队列加载失败');
    }
  }, [status]);

  useEffect(() => { void load(); }, [load]);
  usePolling(() => { void load(); }, POLL_INTERVALS.interventions, true);

  const openCount = items.filter((item) => item.status === 'open').length;
  const resolvedCount = items.filter((item) => item.status === 'resolved').length;

  const submit = async () => {
    if (!active) return;
    setBusy(true);
    setMessage('');
    try {
      const result = await interventionApi.resolve(active.id, action, resolution);
      setMessage(result.resumed
        ? `工单 ${active.code} 已处理，运行 ${result.run.run_code} 已续跑`
        : `工单 ${active.code} 已终止运行`);
      setActive(null);
      setResolution('');
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '接管处理失败');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="crumb">EXCEPTION TAKEOVER · 轮询 3s</div>
          <h1 className="page-title">异常接管队列</h1>
          <p className="page-sub">
            断言失败 / 定位漂移 / 超时会被执行器挂起为 takeover，并在此生成工单。
            值守操作员可重试、改定位器、跳过或终止；审计只读角色查看与导出报告，接管请求返回 403。
          </p>
        </div>
        <div className="head-meta">
          <select className="select" style={{ width: 150 }} value={status}
            onChange={(event) => setStatus(event.target.value)}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <span className="chip warn">待接管 {openCount}</span>
        </div>
      </header>

      <div className="stat-row" style={{ marginBottom: 18 }}>
        <div className="stat-cell">
          <div className="stat-value">{items.length}</div>
          <div className="stat-label">当前筛选工单</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value amber">{openCount}</div>
          <div className="stat-label">待接管</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value green">{resolvedCount}</div>
          <div className="stat-label">已解决并续跑</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value mono" style={{ fontSize: 15, paddingTop: 8 }}>
            {canResolve ? 'engineer/admin' : 'viewer 只读'}
          </div>
          <div className="stat-label">当前处置权限</div>
        </div>
      </div>

      {!canResolve ? (
        <div className="banner warn" style={{ marginBottom: 14 }}>
          审计只读角色：可以查看工单与导出执行报告，接管处置按钮已隐藏（直接调用接口返回 403）。
        </div>
      ) : null}
      {message ? <div className="banner warn" style={{ marginBottom: 14 }}>{message}</div> : null}
      {error ? <div className="banner" style={{ marginBottom: 14 }}>{error}</div> : null}

      <Panel kicker="TAKEOVER TICKETS" title="接管工单" tight>
        {items.length === 0 ? (
          <div className="panel-body">
            <EmptyState title="没有符合条件的接管工单"
              hint="运行断言失败时会自动生成工单；也可以在运行详情页查看并处置。" />
          </div>
        ) : (
          <div className="rowlist">
            {items.map((item) => (
              <div key={item.id} className="rowitem"
                style={{ gridTemplateColumns: '1.15fr 0.9fr 0.7fr 1.6fr 1.3fr' }}>
                <div>
                  <div className="row-title mono">{item.code}</div>
                  <div className="row-sub">{formatDateTime(item.created_at)} · {item.process_name}</div>
                </div>
                <div>
                  <span className="chip warn">{INTERVENTION_REASON_LABELS[item.reason] || item.reason}</span>
                  <div className="tiny muted" style={{ marginTop: 4 }}>{item.company_name}</div>
                </div>
                <div>
                  <span className={`chip ${item.status === 'open' ? 'warn' : item.status === 'resolved' ? 'ok' : 'idle'}`}>
                    <StatusLamp tone={item.status === 'open' ? 'warn' : item.status === 'resolved' ? 'ok' : 'idle'} />
                    {INTERVENTION_STATUS_LABELS[item.status] || item.status}
                  </span>
                </div>
                <div>
                  <div className="tiny">步骤 {item.step_seq ?? '—'} · {item.step_target}</div>
                  <div className="tiny muted" style={{ marginTop: 3 }}>{item.detail}</div>
                </div>
                <div className="flex gap-8" style={{ justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                  <button className="btn btn-sm" type="button"
                    onClick={() => navigate(`/runs/${item.run_id}`)}>查看运行</button>
                  {item.status === 'open' && canResolve ? (
                    <button className="btn btn-primary btn-sm" type="button"
                      onClick={() => { setActive(item); setAction('retry'); setResolution(''); }}>
                      接管处置
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {active ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="panel modal">
            <header className="panel-head">
              <div>
                <div className="panel-kicker">TAKEOVER · {active.code}</div>
                <div className="panel-title">{active.process_name} · 步骤 {active.step_seq}</div>
              </div>
              <button className="btn btn-ghost btn-sm right" type="button"
                onClick={() => setActive(null)}>关闭</button>
            </header>
            <div className="modal-body">
              <div className="tiny muted">{active.detail}</div>
              <label className="field">
                <span className="field-label">处置动作</span>
                <select className="select" value={action}
                  onChange={(event) => setAction(event.target.value)}>
                  {INTERVENTION_ACTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label} — {option.hint}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field-label">处置说明（写入审计日志）</span>
                <textarea className="textarea" value={resolution}
                  placeholder="如：企业已补传审计报告，人工核验后放行本步骤"
                  onChange={(event) => setResolution(event.target.value)} />
              </label>
              <div className="banner warn">重试/改定位器会从断点续跑：已成功且幂等键一致的步骤自动跳过。</div>
            </div>
            <div className="modal-foot">
              <button className="btn btn-ghost" type="button" onClick={() => setActive(null)}>取消</button>
              <button className="btn btn-primary" type="button" onClick={submit} disabled={busy}>
                {busy ? '处理中…' : '确认处置'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
