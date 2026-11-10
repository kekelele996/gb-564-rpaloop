import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { boardApi } from '../api/board';
import EmptyState from '../components/common/EmptyState';
import Panel from '../components/common/Panel';
import StatusLamp from '../components/common/StatusLamp';
import StepTimeline from '../components/business/StepTimeline';
import { POLL_INTERVALS, RUN_STATUS_LABELS, RUN_TRIGGER_LABELS } from '../constants/enums';
import { usePolling } from '../hooks/usePolling';
import type { BoardSnapshot, RunItem } from '../types';
import { formatDateTime, formatPercent } from '../utils/format';
import { runStatusTone } from '../utils/risk';

export default function BoardPage() {
  const navigate = useNavigate();
  const [board, setBoard] = useState<BoardSnapshot | null>(null);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<string>('—');

  const load = useCallback(async () => {
    try {
      const snapshot = await boardApi.get();
      setBoard(snapshot);
      setError('');
      setLastUpdated(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
    } catch (err) {
      setError(err instanceof Error ? err.message : '看板加载失败');
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  usePolling(() => { void load(); }, POLL_INTERVALS.board, true);

  const stats = board?.stats;
  const activeRuns = board?.active ?? [];
  const queue = board?.queue ?? [];
  const failures = board?.recent_failures ?? [];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="crumb">ROBOT WATCH · 轮询 2s</div>
          <h1 className="page-title">机器人值守看板</h1>
          <p className="page-sub">
            苏州政务外包值守台 A2 的无人值守批次：队列、进行中步骤灯、异常接管与最近失败。
            页面每 2 秒轮询 /api/board，失败运行行会闪烁一次告警。
          </p>
        </div>
        <div className="head-meta">
          <span className="chip ok"><StatusLamp tone="active" />SU-BOT-01 在线</span>
          <span className="chip mono">刷新 {lastUpdated}</span>
        </div>
      </header>

      {error ? <div className="banner" style={{ marginBottom: 14 }}>{error}</div> : null}

      <div className="stat-row" style={{ marginBottom: 18 }}>
        <div className="stat-cell">
          <div className="stat-value">{stats?.total ?? '—'}</div>
          <div className="stat-label">近 60 次运行</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value green">{stats?.succeeded ?? '—'}</div>
          <div className="stat-label">成功</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value red">{stats?.failed ?? '—'}</div>
          <div className="stat-label">失败</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value amber">{stats?.takeover ?? '—'}</div>
          <div className="stat-label">待接管</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value amber">{stats?.queued ?? '—'}</div>
          <div className="stat-label">队列中</div>
        </div>
      </div>

      <div className="board-grid">
        <div className="stack">
          <Panel kicker="ACTIVE RUNS · 步骤灯" title={`进行中运行（${activeRuns.length}）`} tight>
            {activeRuns.length === 0 ? (
              <div className="panel-body">
                <EmptyState title="机器人当前空闲"
                  hint="在流程库选一个已发布流程，选择企业材料下发正式运行或干跑校验。" />
              </div>
            ) : activeRuns.map((run) => <ActiveRunCard key={run.id} run={run} navigate={navigate} />)}
          </Panel>

          <Panel kicker="RUN LEDGER" title="最近运行记录" tight>
            {board ? (
              <div className="rowlist">
                {(board.queue.length ? board.queue : []).concat(board.active, board.recent_failures)
                  .slice(0, 6).map((run) => (
                    <div key={run.id} className="rowitem clickable"
                      style={{ gridTemplateColumns: '1.3fr 1fr 0.9fr 0.8fr 0.8fr' }}
                      onClick={() => navigate(`/runs/${run.id}`)}>
                      <div>
                        <div className="row-title mono">{run.run_code}</div>
                        <div className="row-sub">{run.process_name} · {run.company_name}</div>
                      </div>
                      <div className="tiny muted">{RUN_TRIGGER_LABELS[run.trigger]} · {run.robot_name}</div>
                      <div>
                        <span className={`chip ${runStatusTone(run.status)}`}>
                          <StatusLamp tone={runStatusTone(run.status) as 'ok' | 'warn' | 'danger' | 'active' | 'idle'} />
                          {RUN_STATUS_LABELS[run.status]}
                        </span>
                      </div>
                      <div className="tiny mono muted">{run.success_steps}/{run.total_steps} 步</div>
                      <div className="tiny muted">{formatDateTime(run.started_at)}</div>
                    </div>
                  ))}
                {board.queue.length + board.active.length + board.recent_failures.length === 0 ? (
                  <div className="panel-body"><EmptyState title="还没有运行记录" hint="从流程库发起第一次干跑。" /></div>
                ) : null}
              </div>
            ) : <div className="panel-body muted">加载看板…</div>}
          </Panel>
        </div>

        <div className="stack">
          <Panel kicker="TAKEOVER QUEUE" title="异常接管提醒" tight>
            {failures.length === 0 ? (
              <div className="panel-body"><EmptyState title="没有待接管异常" hint="断言失败或超时的运行会出现在这里。" /></div>
            ) : failures.map((run) => (
              <div key={`fail-${run.id}`} className="queue-item flash"
                onClick={() => navigate(`/runs/${run.id}`)} style={{ cursor: 'pointer' }}>
                <StatusLamp tone="danger" />
                <div style={{ flex: 1 }}>
                  <div className="mono tiny">{run.run_code}</div>
                  <div className="tiny muted">{run.process_name} · {run.company_name}</div>
                </div>
                <span className="chip danger">失败</span>
              </div>
            ))}
          </Panel>

          <Panel kicker="ROBOT CONFIG" title="值守机器人" >
            <div className="stack">
              <div className="spread">
                <span className="tiny muted">机器人</span>
                <span className="mono">{board?.robot.name ?? 'SU-BOT-01'}</span>
              </div>
              <div className="spread">
                <span className="tiny muted">值守台</span>
                <span className="tiny">{board?.robot.station ?? '—'}</span>
              </div>
              <div className="spread">
                <span className="tiny muted">轮询间隔</span>
                <span className="mono">{board?.robot.poll_seconds ?? 2}s</span>
              </div>
              <div className="spread">
                <span className="tiny muted">执行模式</span>
                <span className="tiny">后端模拟执行器（Kahn 拓扑 + 幂等键）</span>
              </div>
              <div className="progress" style={{ marginTop: 4 }}>
                <div className="progress-fill" style={{
                  width: `${stats && stats.total ? Math.round((stats.succeeded / Math.max(stats.total, 1)) * 100) : 0}%`,
                }} />
              </div>
              <div className="tiny faint">近 60 次运行成功率 {stats ? formatPercent(stats.succeeded / Math.max(stats.total, 1)) : '—'}</div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function ActiveRunCard({ run, navigate }: { run: RunItem; navigate: (path: string) => void }) {
  const steps = run.progress?.steps ?? [];
  const total = run.progress?.total || run.total_steps || 0;
  const done = run.progress?.done || 0;
  const segments = Array.from({ length: total }, (_, index) => {
    const step = steps.find((item) => item.seq === index + 1);
    return step ? step.status : 'idle';
  });
  return (
    <div className={`board-run ${run.status === 'takeover' ? 'flash' : ''}`}>
      <div className="run-head">
        <StatusLamp tone={run.status === 'takeover' ? 'warn' : 'active'} />
        <div>
          <div className="run-code">{run.run_code}</div>
          <div className="run-meta">{run.process_name} · {run.company_name} · {run.robot_name}</div>
        </div>
        <div className="right flex align-center gap-8">
          <span className={`chip ${runStatusTone(run.status)}`}>{RUN_STATUS_LABELS[run.status]}</span>
          <button className="btn btn-sm" type="button" onClick={() => navigate(`/runs/${run.id}`)}>详情</button>
        </div>
      </div>
      <div className="board-steps">
        {segments.map((status, index) => (
          <div key={index} className={`seg ${status === 'retried' ? 'warn' : status}`}
            title={`步骤 ${index + 1}: ${status}`} />
        ))}
      </div>
      <div className="progress-meta">
        <span>进度 {done}/{total} · 触发 {RUN_TRIGGER_LABELS[run.trigger]}</span>
        <span>开始 {formatDateTime(run.started_at)}</span>
      </div>
      {steps.length ? (
        <div style={{ marginTop: 12 }}>
          <StepTimeline steps={steps.map((step) => ({
            seq: step.seq, status: step.status, target_desc: step.target_desc, action: step.action,
            attempt: step.attempt, duration_ms: step.duration_ms, locator_used: step.locator_used,
            error_code: step.error_code,
          }))} />
        </div>
      ) : null}
    </div>
  );
}
